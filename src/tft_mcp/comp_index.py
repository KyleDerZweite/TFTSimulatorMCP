"""Set 4 Challenger final-board comp index.

A comp is one exact set of champion names. Win rate is the share of those
boards with placement 1 through 4. Trait level is the recorded unit count.
The official index keeps lists, trait levels, and per-champion item
combinations with at least 100 boards. Queries read the SQLite aggregate;
they do not scan the CSV.
"""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from decimal import Decimal, ROUND_HALF_UP

from tft_mcp.errors import SessionError


SCHEMA_VERSION = '3'
SOURCE = 'set4-fates-challenger-euw'
WIN_DEFINITION = 'top4'
MIN_COMP_GAMES = 100
MAX_LIMIT = 50
MAX_LEVEL = 14
MAX_CHAMPIONS = 58

OFFICIAL_CSV_SHA256 = 'df73994ce6172fd810846c92b66c099db488b5af12b27521a6e63fff18882f4e'
OFFICIAL_PLAYER_ROWS = 748928
OFFICIAL_PER_PLACEMENT = 93616
OFFICIAL_UNIQUE_COMPS = 245797
OFFICIAL_TRAIT_ROWS = 2768060
OFFICIAL_CHAMPIONS = 58
OFFICIAL_TRAITS = 26
OFFICIAL_STORED_COMPS = 682
OFFICIAL_STORED_TRAIT_ROWS = 5994
OFFICIAL_ITEM_BUILDS = 219522
OFFICIAL_STORED_ITEM_BUILDS = 4352
OFFICIAL_EXAMPLE_COMP = ('Irelia', 'Janna', 'Lux', 'Morgana', 'Pyke', 'Shen', 'Talon', 'Yone')
OFFICIAL_EXAMPLE_GAMES = 6684

# Riot Fates item id to the installed simulator id. Four recorded names differ:
# Aspect of Dusk, Mage's Hat, Elderwood Sprout, and Thief's Gloves.
SIMULATOR_ITEM_IDS = {
    1: 'bf_sword', 2: 'recurve_bow', 3: 'needlessly_large_rod', 4: 'tear_of_the_goddess',
    5: 'chain_vest', 6: 'negatron_cloak', 7: 'giants_belt', 8: 'spatula',
    9: 'sparring_gloves', 11: 'deathblade', 12: 'giant_slayer', 13: 'hextech_gunblade',
    14: 'spear_of_shojin', 15: 'guardian_angel', 16: 'bloodthirster', 17: 'zekes_herald',
    18: 'sword_of_the_divine', 19: 'infinity_edge', 22: 'rapid_firecannon',
    23: 'guinsoos_rageblade', 24: 'statikk_shiv', 25: 'titans_resolve', 26: 'runaans_hurricane',
    27: 'zzrot_portal', 28: 'duelists_zeal', 29: 'last_whisper', 33: 'rabadons_deathcap',
    34: 'ludens_echo', 35: 'locket_of_the_iron_solari', 36: 'ionic_spark',
    37: 'morellonomicon', 38: 'mantle_of_dusk', 39: 'jeweled_gauntlet', 44: 'blue_buff',
    45: 'frozen_heart', 46: 'chalice_of_power', 47: 'redemption', 48: 'mages_cap',
    49: 'hand_of_justice', 55: 'bramble_vest', 56: 'gargoyle_stoneplate', 57: 'sunfire_cape',
    58: 'vanguards_cuirass', 59: 'shroud_of_stillness', 66: 'dragons_claw', 67: 'zephyr',
    68: 'elderwood_heirloom', 69: 'quicksilver', 77: 'warmogs_armor', 78: 'warlords_banner',
    79: 'trap_claw', 88: 'force_of_nature', 89: 'youmuus_ghostblade', 99: 'thieves_gloves',
}

CHAMPION_SQL = '''
SELECT mask, games, top4, placement_sum
FROM comps
WHERE (mask & ?) = ?
ORDER BY (top4 * 1.0 / games) DESC, games DESC, id ASC
LIMIT ?
'''

TRAIT_SQL = '''
SELECT comps.mask, ranked.games, ranked.top4, ranked.placement_sum
FROM (
    SELECT comp_id, games, top4, placement_sum
    FROM comp_trait
    WHERE trait_id = ? AND level = ?
    ORDER BY (top4 * 1.0 / games) DESC, games DESC, comp_id ASC
    LIMIT ?
) AS ranked
JOIN comps ON comps.id = ranked.comp_id
ORDER BY (ranked.top4 * 1.0 / ranked.games) DESC, ranked.games DESC, ranked.comp_id ASC
'''


def repository_root():
    return Path(__file__).resolve().parents[2]


def repository_database_path():
    return repository_root() / 'data' / 'set4' / 'player-results' / 'comps.sqlite'


def packaged_database_path():
    return Path(__file__).resolve().parent / 'data' / 'comps.sqlite'


def default_csv_path():
    return repository_root() / 'data' / 'set4' / 'player-results' / 'kaggle' / 'TFT_set4_euw_challanger_games.csv'


def default_items_path():
    return repository_root() / 'data' / 'set4' / 'riot' / 'items.json'


def default_database_path():
    override = os.environ.get('TFT_MCP_COMP_DB')
    if override:
        return Path(override)
    for path in (repository_database_path(), packaged_database_path()):
        if path.is_file():
            return path
    return repository_database_path()


def normalize_name(value):
    return ''.join(character for character in value.casefold() if character.isalnum())


def rounded_ratio(numerator, denominator, places):
    quantum = Decimal(1).scaleb(-places)
    return float((Decimal(numerator) / Decimal(denominator)).quantize(quantum, rounding=ROUND_HALF_UP))


def load_item_catalog():
    """Riot display names for the Fates item ids, paired with simulator ids."""
    rows = json.loads(default_items_path().read_text())
    catalog = {}
    for row in rows:
        item_id = row['id']
        simulator_id = SIMULATOR_ITEM_IDS.get(item_id)
        if type(item_id) is not int or simulator_id is None or item_id in catalog:
            raise ValueError(f'Fates item {item_id} has no simulator id.')
        catalog[item_id] = (row['name'], simulator_id)
    if set(catalog) != set(SIMULATOR_ITEM_IDS):
        raise ValueError('The Fates item list does not match the simulator id map.')
    return catalog


def _item_tuple(raw):
    if type(raw) is not list or len(raw) > 3:
        raise ValueError('A champion recorded an unreadable item list.')
    return tuple(sorted(int(item) for item in raw))


def _pad_items(items):
    return (0,) * (3 - len(items)) + tuple(items)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def parse_recorded_board(row):
    try:
        units = json.loads(row['units'].replace("'", '"'))
        traits = json.loads(row['traits'].replace("'", '"'))
        placement = int(row['placement'])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Unreadable board in match {row.get('match_id')}.") from error
    if type(units) is not dict or type(traits) is not dict or not 1 <= placement <= 8:
        raise ValueError(f"Unreadable board in match {row.get('match_id')}.")
    names = tuple(sys.intern(name) for name in sorted(units))
    parsed_traits = tuple(sorted(
        (sys.intern(name), int(level)) for name, level in traits.items()))
    try:
        builds = tuple(
            (name, _item_tuple(units[name]['items'])) for name in names)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Unreadable board in match {row.get('match_id')}.") from error
    return names, parsed_traits, placement, builds


def aggregate(records):
    comp_stats = {}
    trait_stats = {}
    item_stats = {}
    for names, traits, placement, builds in records:
        _accumulate(comp_stats, trait_stats, names, traits, placement)
        for champion, items in builds:
            _accumulate_build(item_stats, champion, items, placement)
    return comp_stats, trait_stats, item_stats


def _accumulate(comp_stats, trait_stats, names, traits, placement):
    slot = comp_stats.get(names)
    if slot is None:
        slot = [0, 0, 0]
        comp_stats[names] = slot
    slot[0] += 1
    slot[1] += placement <= 4
    slot[2] += placement
    for trait, level in traits:
        key = (names, trait, level)
        trait_slot = trait_stats.get(key)
        if trait_slot is None:
            trait_slot = [0, 0, 0]
            trait_stats[key] = trait_slot
        trait_slot[0] += 1
        trait_slot[1] += placement <= 4
        trait_slot[2] += placement
    return comp_stats, trait_stats


def _accumulate_build(item_stats, champion, items, placement):
    slot = item_stats.get((champion, items))
    if slot is None:
        slot = [0, 0, 0]
        item_stats[(champion, items)] = slot
    slot[0] += 1
    slot[1] += placement <= 4
    slot[2] += placement


def iter_csv(csv_path):
    with open(csv_path, newline='') as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            yield parse_recorded_board(row)
            if index % 100000 == 0:
                print(f'indexed {index} boards', file=sys.stderr)


def board_record(board):
    units = board['units']
    if isinstance(units, dict):
        names = tuple(sorted(units))
        builds = tuple(sorted(
            (name, _item_tuple(units[name].get('items', []) if isinstance(units[name], dict) else units[name]))
            for name in names))
    else:
        names = tuple(sorted(units))
        builds = tuple((name, ()) for name in names)
    traits = tuple(sorted((name, int(level)) for name, level in board['traits'].items()))
    return names, traits, int(board['placement']), builds


def retain_frequent(comp_stats, trait_stats, minimum):
    """Keep champion lists and trait levels with at least `minimum` boards."""
    comps = {names: slot for names, slot in comp_stats.items() if slot[0] >= minimum}
    traits = {
        key: slot for key, slot in trait_stats.items()
        if key[0] in comps and slot[0] >= minimum
    }
    return comps, traits


def retain_item_builds(item_stats, minimum):
    """Keep per-champion item combinations with at least `minimum` boards."""
    return {key: slot for key, slot in item_stats.items() if slot[0] >= minimum}


def build_boards(boards, db_path, minimum_games=1):
    """Write an index from explicit boards. Each board has placement, units and traits."""
    raw_comps, raw_traits, raw_items = aggregate(board_record(board) for board in boards)
    comp_stats, trait_stats = retain_frequent(raw_comps, raw_traits, minimum_games)
    item_stats = retain_item_builds(raw_items, minimum_games)
    meta = {
        'schema_version': SCHEMA_VERSION,
        'player_rows': str(len(boards)),
        'top4_rows': str(sum(slot[1] for slot in raw_comps.values())),
        'unique_comps': str(len(comp_stats)),
        'trait_rows': str(len(trait_stats)),
        'min_games': str(minimum_games),
        'csv_sha256': '',
        'win_definition': WIN_DEFINITION,
    }
    write_index(comp_stats, trait_stats, db_path, meta, raw_comps, raw_traits, item_stats)
    return meta


def build_database(csv_path, db_path):
    """Aggregate the pinned Challenger CSV into a SQLite comp index."""
    csv_path = Path(csv_path)
    digest = file_sha256(csv_path)
    if digest != OFFICIAL_CSV_SHA256:
        raise ValueError(f'CSV sha256 {digest} does not match the pinned Challenger extract.')
    placements = [0] * 9
    comp_stats = {}
    trait_stats = {}
    item_stats = {}
    for names, traits, placement, builds in iter_csv(csv_path):
        placements[placement] += 1
        _accumulate(comp_stats, trait_stats, names, traits, placement)
        for champion, items in builds:
            _accumulate_build(item_stats, champion, items, placement)
    if sum(placements) != OFFICIAL_PLAYER_ROWS or any(
            placements[place] != OFFICIAL_PER_PLACEMENT for place in range(1, 9)):
        raise ValueError('Placement totals do not match the pinned Challenger extract.')
    if len(comp_stats) != OFFICIAL_UNIQUE_COMPS or len(trait_stats) != OFFICIAL_TRAIT_ROWS:
        raise ValueError(
            f'Aggregate size {len(comp_stats)} comps and {len(trait_stats)} trait rows '
            'does not match the pinned Challenger extract.')
    champion_names = {name for names in comp_stats for name in names}
    trait_names = {trait for (_names, trait, _level) in trait_stats}
    if len(champion_names) != OFFICIAL_CHAMPIONS or len(trait_names) != OFFICIAL_TRAITS:
        raise ValueError('Roster size does not match the pinned Challenger extract.')
    for (_names, _trait, level) in trait_stats:
        if not 0 <= level <= MAX_LEVEL:
            raise ValueError(f'Trait level {level} is outside 0..{MAX_LEVEL}.')
    example = comp_stats.get(OFFICIAL_EXAMPLE_COMP)
    if example is None or example[0] != OFFICIAL_EXAMPLE_GAMES:
        raise ValueError('The known Irelia sharpshooter board count changed.')
    top4_rows = sum(slot[1] for slot in comp_stats.values())
    if top4_rows != OFFICIAL_PLAYER_ROWS // 2:
        raise ValueError('Top-4 total is not half of the player rows.')
    stored_comps, stored_traits = retain_frequent(comp_stats, trait_stats, MIN_COMP_GAMES)
    if len(stored_comps) != OFFICIAL_STORED_COMPS or len(stored_traits) != OFFICIAL_STORED_TRAIT_ROWS:
        raise ValueError(
            f'Stored aggregate {len(stored_comps)} comps and {len(stored_traits)} trait rows '
            f'does not match the {MIN_COMP_GAMES}-game cutoff.')
    if len({name for names in stored_comps for name in names}) != OFFICIAL_CHAMPIONS:
        raise ValueError('A champion has no list with at least 100 boards.')
    if len({trait for (_names, trait, _level) in stored_traits}) != OFFICIAL_TRAITS:
        raise ValueError('A trait has no level with at least 100 boards.')
    if len(item_stats) != OFFICIAL_ITEM_BUILDS:
        raise ValueError(
            f'{len(item_stats)} item builds does not match the pinned Challenger extract.')
    catalog = load_item_catalog()
    stored_items = retain_item_builds(item_stats, MIN_COMP_GAMES)
    if len(stored_items) != OFFICIAL_STORED_ITEM_BUILDS:
        raise ValueError(
            f'{len(stored_items)} stored item builds does not match the {MIN_COMP_GAMES}-board cutoff.')
    for (_champion, items) in stored_items:
        for item in items:
            if item not in catalog:
                raise ValueError(f'Item {item} is not in the Fates item list.')
    if len({champion for champion, _items in stored_items}) != OFFICIAL_CHAMPIONS:
        raise ValueError('A champion has no item combination with at least 100 boards.')
    meta = {
        'schema_version': SCHEMA_VERSION,
        'player_rows': str(OFFICIAL_PLAYER_ROWS),
        'top4_rows': str(top4_rows),
        'source_comps': str(OFFICIAL_UNIQUE_COMPS),
        'source_trait_rows': str(OFFICIAL_TRAIT_ROWS),
        'unique_comps': str(OFFICIAL_STORED_COMPS),
        'trait_rows': str(OFFICIAL_STORED_TRAIT_ROWS),
        'source_item_builds': str(OFFICIAL_ITEM_BUILDS),
        'item_builds': str(OFFICIAL_STORED_ITEM_BUILDS),
        'min_games': str(MIN_COMP_GAMES),
        'csv_sha256': digest,
        'win_definition': WIN_DEFINITION,
    }
    write_index(stored_comps, stored_traits, db_path, meta, comp_stats, trait_stats, stored_items)
    return meta


def write_index(comp_stats, trait_stats, db_path, meta, roster_comps=None, roster_traits=None,
                item_builds=None):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = db_path.with_name(db_path.name + '.tmp')
    temporary.unlink(missing_ok=True)
    ordered = sorted(comp_stats)
    comp_ids = {names: index for index, names in enumerate(ordered, start=1)}
    roster_comps = comp_stats if roster_comps is None else roster_comps
    roster_traits = trait_stats if roster_traits is None else roster_traits
    item_builds = {} if item_builds is None else item_builds
    catalog = load_item_catalog()
    champion_names = sorted({name for names in roster_comps for name in names})
    trait_names = sorted({trait for (_names, trait, _level) in roster_traits})
    _reject_ambiguous_names(champion_names, 'Champion')
    _reject_ambiguous_names(trait_names, 'Trait')
    bit_of = {name: index for index, name in enumerate(champion_names)}
    trait_ids = {name: index for index, name in enumerate(trait_names, start=1)}
    connection = sqlite3.connect(temporary)
    try:
        connection.isolation_level = None
        connection.execute('PRAGMA journal_mode = OFF')
        connection.execute('PRAGMA synchronous = OFF')
        connection.execute('BEGIN')
        connection.execute('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        connection.execute(
            'CREATE TABLE champions (bit INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)')
        connection.execute(
            'CREATE TABLE traits (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)')
        connection.execute(
            '''CREATE TABLE comps (
                id INTEGER PRIMARY KEY,
                mask INTEGER NOT NULL UNIQUE,
                games INTEGER NOT NULL,
                top4 INTEGER NOT NULL,
                placement_sum INTEGER NOT NULL)''')
        connection.execute(
            '''CREATE TABLE comp_trait (
                trait_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                comp_id INTEGER NOT NULL,
                games INTEGER NOT NULL,
                top4 INTEGER NOT NULL,
                placement_sum INTEGER NOT NULL,
                PRIMARY KEY (trait_id, level, comp_id))''')
        connection.executemany(
            'INSERT INTO meta (key, value) VALUES (?, ?)', tuple(meta.items()))
        connection.executemany(
            'INSERT INTO champions (bit, name) VALUES (?, ?)',
            tuple(enumerate(champion_names)))
        connection.executemany(
            'INSERT INTO traits (id, name) VALUES (?, ?)',
            tuple(enumerate(trait_names, start=1)))
        connection.executemany(
            'INSERT INTO comps (id, mask, games, top4, placement_sum) VALUES (?, ?, ?, ?, ?)',
            (
                (comp_ids[names], _mask(names, bit_of), games, top4, placement_sum)
                for names, (games, top4, placement_sum) in comp_stats.items()
            ))
        batch = []
        for (names, trait, level), (games, top4, placement_sum) in trait_stats.items():
            batch.append((trait_ids[trait], level, comp_ids[names], games, top4, placement_sum))
            if len(batch) == 50000:
                connection.executemany(
                    '''INSERT INTO comp_trait
                       (trait_id, level, comp_id, games, top4, placement_sum)
                       VALUES (?, ?, ?, ?, ?, ?)''', batch)
                batch.clear()
        if batch:
            connection.executemany(
                '''INSERT INTO comp_trait
                   (trait_id, level, comp_id, games, top4, placement_sum)
                   VALUES (?, ?, ?, ?, ?, ?)''', batch)
        connection.execute('CREATE INDEX idx_comps_games ON comps(games)')
        connection.execute(
            'CREATE INDEX idx_comp_trait_rank ON comp_trait(trait_id, level, games)')
        connection.execute(
            '''CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                simulator_id TEXT NOT NULL UNIQUE)''')
        connection.execute(
            '''CREATE TABLE item_builds (
                champion TEXT NOT NULL,
                item_a INTEGER NOT NULL,
                item_b INTEGER NOT NULL,
                item_c INTEGER NOT NULL,
                games INTEGER NOT NULL,
                top4 INTEGER NOT NULL,
                placement_sum INTEGER NOT NULL,
                PRIMARY KEY (champion, item_a, item_b, item_c))''')
        connection.executemany(
            'INSERT INTO items (id, name, simulator_id) VALUES (?, ?, ?)',
            tuple((item_id, name, simulator_id) for item_id, (name, simulator_id) in sorted(catalog.items())))
        item_rows = []
        for (champion, items), (games, top4, placement_sum) in item_builds.items():
            for item in items:
                if item not in catalog:
                    raise ValueError(f'Item {item} is not in the Fates item list.')
            item_a, item_b, item_c = _pad_items(items)
            item_rows.append((champion, item_a, item_b, item_c, games, top4, placement_sum))
        connection.executemany(
            '''INSERT INTO item_builds
               (champion, item_a, item_b, item_c, games, top4, placement_sum)
               VALUES (?, ?, ?, ?, ?, ?, ?)''', item_rows)
        connection.execute('CREATE INDEX idx_item_builds_champion ON item_builds(champion)')
        connection.execute('COMMIT')
        connection.execute('ANALYZE')
        connection.close()
        connection = None
        os.replace(temporary, db_path)
    except Exception:
        if connection is not None:
            connection.close()
        temporary.unlink(missing_ok=True)
        raise


def _reject_ambiguous_names(names, label):
    seen = {}
    for name in names:
        key = normalize_name(name)
        if not key or key in seen:
            raise ValueError(f'{label} name {name!r} is empty or ambiguous after normalization.')
        seen[key] = name


def _mask(names, bit_of):
    mask = 0
    for name in names:
        mask |= 1 << bit_of[name]
    return mask


class CompIndex:
    """Read-only queries over one built comp index."""

    def __init__(self, path):
        self.path = Path(path)
        self.connection = _connect_readonly(self.path)
        self.meta = {
            row['key']: row['value']
            for row in self.connection.execute('SELECT key, value FROM meta')}
        champions = list(self.connection.execute(
            'SELECT bit, name FROM champions ORDER BY bit'))
        self.bit_of = {row['name']: row['bit'] for row in champions}
        self.bits = [(row['bit'], row['name']) for row in champions]
        self.champions_by_norm = {}
        for row in champions:
            key = normalize_name(row['name'])
            if key in self.champions_by_norm:
                raise SessionError('internal_error', 'Champion names are ambiguous.',
                                   {'name': row['name']})
            self.champions_by_norm[key] = row['name']
        self.traits_by_norm = {}
        self.trait_ids = {}
        for row in self.connection.execute('SELECT id, name FROM traits ORDER BY id'):
            key = normalize_name(row['name'])
            if key in self.traits_by_norm:
                raise SessionError('internal_error', 'Trait names are ambiguous.',
                                   {'name': row['name']})
            self.traits_by_norm[key] = row['name']
            self.trait_ids[row['name']] = row['id']
        self.item_names = {}
        self.item_simulator_ids = {}
        self.items_by_norm = {}
        for row in self.connection.execute('SELECT id, name, simulator_id FROM items ORDER BY id'):
            self.item_names[row['id']] = row['name']
            self.item_simulator_ids[row['id']] = row['simulator_id']
            for key in (normalize_name(row['name']), normalize_name(row['simulator_id'])):
                current = self.items_by_norm.get(key)
                if current is None:
                    self.items_by_norm[key] = row['id']
                elif current != row['id']:
                    raise SessionError('internal_error', 'Item names are ambiguous.',
                                       {'name': row['name']})

    def search_comps_by_champions(self, champions, limit):
        _check_bounds(limit)
        if type(champions) is not list or not champions or len(champions) > MAX_CHAMPIONS:
            raise SessionError('invalid_input', 'Invalid argument value.',
                               {'field': 'champions', 'value': champions})
        resolved = []
        unknown = []
        seen = set()
        for raw in champions:
            if type(raw) is not str:
                raise SessionError('invalid_input', 'Invalid argument value.',
                                   {'field': 'champions', 'value': champions})
            canonical = self.champions_by_norm.get(normalize_name(raw.strip()))
            if canonical is None:
                unknown.append(raw)
                continue
            if canonical in seen:
                raise SessionError('invalid_input', 'Duplicate champion.',
                                   {'field': 'champions', 'value': raw})
            seen.add(canonical)
            resolved.append(canonical)
        if unknown:
            label = ', '.join(unknown)
            raise SessionError('unknown_champion', f'Unknown champion: {label}.',
                               {'champions': unknown})
        required = 0
        for name in resolved:
            required |= 1 << self.bit_of[name]
        rows = self.connection.execute(CHAMPION_SQL, (required, required, limit))
        return _query_result(resolved, limit, rows, self.bits)

    def search_comps_by_trait(self, trait, level, limit):
        _check_bounds(limit)
        if type(trait) is not str:
            raise SessionError('invalid_input', 'Invalid argument value.',
                               {'field': 'trait', 'value': trait})
        canonical = self.traits_by_norm.get(normalize_name(trait.strip()))
        if canonical is None:
            raise SessionError('unknown_trait', f'Unknown trait: {trait}.', {'trait': trait})
        if type(level) is not int or not 0 <= level <= MAX_LEVEL:
            raise SessionError('invalid_input', 'Invalid argument value.',
                               {'field': 'level', 'value': level})
        rows = self.connection.execute(
            TRAIT_SQL, (self.trait_ids[canonical], level, limit))
        result = _query_result(None, limit, rows, self.bits)
        result['trait'] = canonical
        result['level'] = level
        return result

    def search_champion_items(self, champion, items=None):
        if type(champion) is not str:
            raise SessionError('invalid_input', 'Invalid argument value.',
                               {'field': 'champion', 'value': champion})
        canonical = self.champions_by_norm.get(normalize_name(champion.strip()))
        if canonical is None:
            raise SessionError('unknown_champion', f'Unknown champion: {champion}.',
                               {'champions': [champion]})
        if items is None:
            items = []
        if type(items) is not list or len(items) > 2:
            raise SessionError('invalid_input', 'Invalid argument value.',
                               {'field': 'items', 'value': items})
        required = []
        required_names = []
        for raw in items:
            if type(raw) is not str or not raw.strip():
                raise SessionError('invalid_input', 'Invalid argument value.',
                                   {'field': 'items', 'value': items})
            item_id = self.items_by_norm.get(normalize_name(raw.strip()))
            if item_id is None:
                raise SessionError('unknown_item', f'Unknown item: {raw}.', {'item': raw})
            required.append(item_id)
            required_names.append(self.item_names[item_id])
        rows = self.connection.execute(
            '''SELECT item_a, item_b, item_c, games, top4, placement_sum
               FROM item_builds WHERE champion = ?''', (canonical,))
        builds = []
        for row in rows:
            owned = [item for item in (row['item_a'], row['item_b'], row['item_c']) if item]
            if not _multiset_contains(owned, required):
                continue
            named = sorted(
                ((self.item_names[item], self.item_simulator_ids[item]) for item in owned),
                key=lambda pair: (pair[0], pair[1]))
            games = row['games']
            top4 = row['top4']
            builds.append({
                'items': [name for name, _simulator_id in named],
                'item_ids': [simulator_id for _name, simulator_id in named],
                'games': games,
                'top4': top4,
                'win_rate': rounded_ratio(top4, games, 4),
                'avg_placement': rounded_ratio(row['placement_sum'], games, 2),
            })
        builds.sort(key=lambda build: (
            -build['top4'] / build['games'], -build['games'], build['items'], build['item_ids']))
        return {
            'source': SOURCE,
            'champion': canonical,
            'items': required_names,
            'win_definition': WIN_DEFINITION,
            'builds': builds,
        }


def _multiset_contains(owned, required):
    available = {}
    for item in owned:
        available[item] = available.get(item, 0) + 1
    for item in required:
        count = available.get(item, 0)
        if count == 0:
            return False
        available[item] = count - 1
    return True


def _check_bounds(limit):
    if type(limit) is not int or not 1 <= limit <= MAX_LIMIT:
        raise SessionError('invalid_input', 'Invalid argument value.',
                           {'field': 'limit', 'value': limit})


def _query_result(champions, limit, rows, bits):
    result = {
        'source': SOURCE,
        'limit': limit,
        'win_definition': WIN_DEFINITION,
        'comps': [_comp_record(row, bits) for row in rows],
    }
    if champions is not None:
        result['champions'] = champions
    return result


def _comp_record(row, bits):
    games = row['games']
    top4 = row['top4']
    return {
        'champions': [name for bit, name in bits if row['mask'] & (1 << bit)],
        'games': games,
        'top4': top4,
        'win_rate': rounded_ratio(top4, games, 4),
        'avg_placement': rounded_ratio(row['placement_sum'], games, 2),
    }


def _connect_readonly(path):
    path = Path(path)
    if not path.is_file():
        raise SessionError('comp_index_unavailable', 'Comp index database is not built.',
                           {'path': str(path)})
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True,
                                     check_same_thread=False)
    except sqlite3.Error as error:
        raise SessionError('comp_index_unavailable', 'Comp index database cannot be opened.',
                           {'path': str(path), 'error': str(error)}) from error
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only = ON')
    try:
        version = connection.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    except sqlite3.Error as error:
        connection.close()
        raise SessionError('comp_index_unavailable', 'Comp index schema is unsupported.',
                           {'path': str(path), 'error': str(error)}) from error
    if version is None or version['value'] != SCHEMA_VERSION:
        connection.close()
        raise SessionError('comp_index_unavailable', 'Comp index schema is unsupported.',
                           {'path': str(path)})
    return connection


_cached = None
_cached_path = None


def get_index():
    global _cached, _cached_path
    path = default_database_path().resolve()
    if _cached is None or _cached_path != path:
        _cached = CompIndex(path)
        _cached_path = path
    return _cached


def main(argv=None):
    parser = argparse.ArgumentParser(description='Build the Set 4 Challenger comp index.')
    parser.add_argument('--csv', type=Path, default=default_csv_path())
    parser.add_argument('--database', type=Path, default=repository_database_path())
    args = parser.parse_args(argv)
    try:
        meta = build_database(args.csv, args.database)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"wrote {args.database} ({args.database.stat().st_size} bytes)")
    print(' '.join(f'{key}={value}' for key, value in sorted(meta.items())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
