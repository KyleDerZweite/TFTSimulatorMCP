import jsonschema
import pytest

from tft_mcp.comp_index import (
    CompIndex, MIN_COMP_GAMES, OFFICIAL_CSV_SHA256, OFFICIAL_EXAMPLE_COMP,
    OFFICIAL_EXAMPLE_GAMES, OFFICIAL_PLAYER_ROWS, OFFICIAL_STORED_COMPS, OFFICIAL_STORED_TRAIT_ROWS,
    OFFICIAL_ITEM_BUILDS, OFFICIAL_STORED_ITEM_BUILDS, OFFICIAL_TRAIT_ROWS, OFFICIAL_UNIQUE_COMPS,
    build_boards, default_database_path, rounded_ratio,
)
from tft_mcp.errors import SessionError
from tft_mcp.tool_calls import validate_arguments
from tft_mcp.tool_schemas import CHAMPION_ITEMS_OUTPUT, COMP_CHAMPION_OUTPUT, COMP_TRAIT_OUTPUT


def board(units, traits, placements):
    return [{'placement': placement, 'units': units, 'traits': traits} for placement in placements]


def index_of(tmp_path):
    boards = board(['Ahri', 'Lulu'], {'Mage': 3}, [1] * 8 + [8, 8])
    boards += board(['Ahri', 'Lulu', 'Veigar'], {'Mage': 3}, [1, 1])
    boards += board(['Ahri', 'Lulu', 'Veigar'], {'Mage': 6}, [1, 1])
    boards += board(['Ahri', 'Zed'], {'Mage': 3}, [1, 1, 1, 8, 8, 8])
    boards += board(['Ahri', 'Veigar', 'Zed'], {'Mage': 3}, [1, 1, 1, 1])
    boards += board(['Zed'], {'Mage': 3}, [1, 1, 1, 1])
    path = tmp_path / 'comps.sqlite'
    build_boards(boards, path)
    return CompIndex(path)


def test_ratio_rounds_half_up():
    assert rounded_ratio(2, 3, 4) == 0.6667
    assert rounded_ratio(1, 3, 4) == 0.3333
    assert rounded_ratio(10, 3, 2) == 3.33


def test_champion_query_ranks_supersets_by_exact_win_rate(tmp_path):
    index = index_of(tmp_path)
    result = index.search_comps_by_champions(['ahri', 'Lulu'], 10)
    assert result['champions'] == ['Ahri', 'Lulu']
    assert result['win_definition'] == 'top4' and 'min_games' not in result
    assert [comp['champions'] for comp in result['comps']] == [
        ['Ahri', 'Lulu', 'Veigar'],
        ['Ahri', 'Lulu'],
    ]
    capped = result['comps'][0]
    assert capped['games'] == 4 and capped['top4'] == 4 and capped['win_rate'] == 1.0
    assert capped['avg_placement'] == 1.0
    wide = result['comps'][1]
    assert wide['games'] == 10 and wide['top4'] == 8 and wide['win_rate'] == 0.8
    assert wide['avg_placement'] == 2.4
    jsonschema.validate(result, COMP_CHAMPION_OUTPUT)
    assert index.search_comps_by_champions(['Ahri'], 1)['comps'][0]['champions'] == [
        'Ahri', 'Lulu', 'Veigar']
    both = index.search_comps_by_champions(['Ahri', 'Lulu'], 10)
    assert [comp['champions'] for comp in both['comps']] == [
        ['Ahri', 'Lulu', 'Veigar'],
        ['Ahri', 'Lulu'],
    ]


def test_equal_win_rates_prefer_more_games_then_alphabetical_names(tmp_path):
    index = index_of(tmp_path)
    result = index.search_comps_by_champions(['Ahri'], 2)
    assert [comp['champions'] for comp in result['comps']] == [
        ['Ahri', 'Lulu', 'Veigar'],
        ['Ahri', 'Veigar', 'Zed'],
    ]
    assert all(comp['win_rate'] == 1.0 and comp['games'] == 4 for comp in result['comps'])


def test_trait_level_is_the_exact_unit_count(tmp_path):
    index = index_of(tmp_path)
    result = index.search_comps_by_trait('mage', 3, 10)
    assert result['trait'] == 'Mage' and result['level'] == 3
    assert [comp['champions'] for comp in result['comps']] == [
        ['Ahri', 'Veigar', 'Zed'],
        ['Zed'],
        ['Ahri', 'Lulu', 'Veigar'],
        ['Ahri', 'Lulu'],
        ['Ahri', 'Zed'],
    ]
    veigar = result['comps'][2]
    assert veigar['games'] == 2 and veigar['top4'] == 2
    jsonschema.validate(result, COMP_TRAIT_OUTPUT)
    six = index.search_comps_by_trait('Mage', 6, 10)
    assert [comp['champions'] for comp in six['comps']] == [['Ahri', 'Lulu', 'Veigar']]
    assert six['comps'][0]['games'] == 2
    assert index.search_comps_by_trait('Mage', 9, 10)['comps'] == []


def test_repeated_queries_return_the_same_result(tmp_path):
    index = index_of(tmp_path)
    first = index.search_comps_by_champions(['Ahri'], 5)
    second = index.search_comps_by_champions([' Ahri '], 5)
    assert first == second
    assert index.search_comps_by_trait('Mage', 3, 5) == index.search_comps_by_trait(
        'Mage', 3, 5)


def test_unknown_names_and_duplicates_are_errors(tmp_path):
    index = index_of(tmp_path)
    with pytest.raises(SessionError) as caught:
        index.search_comps_by_champions(['Ahri', 'Nope'], 1)
    assert caught.value.code == 'unknown_champion'
    assert caught.value.details == {'champions': ['Nope']}
    with pytest.raises(SessionError) as caught:
        index.search_comps_by_champions(['Ahri', 'ahri'], 1)
    assert caught.value.code == 'invalid_input'
    with pytest.raises(SessionError) as caught:
        index.search_comps_by_trait('Blacksmith', 2, 1)
    assert caught.value.code == 'unknown_trait'
    assert caught.value.details == {'trait': 'Blacksmith'}


def test_comp_argument_shapes():
    cases = [
        ('search_comps_by_champions', {}),
        ('search_comps_by_champions', {'champions': [], 'limit': 1}),
        ('search_comps_by_champions', {'champions': ['Ahri'], 'limit': 0}),
        ('search_comps_by_champions', {'champions': ['Ahri'], 'limit': True}),
        ('search_comps_by_champions', {'champions': ['Ahri'], 'limit': 1, 'min_games': 0}),
        ('search_comps_by_champions', {'champions': [''], 'limit': 1}),
        ('search_comps_by_champions', {'champions': ['Ahri'], 'limit': 1, 'extra': 1}),
        ('search_comps_by_trait', {'trait': 'Mage', 'limit': 1}),
        ('search_comps_by_trait', {'trait': 'Mage', 'level': True, 'limit': 1}),
        ('search_comps_by_trait', {'trait': 'Mage', 'level': 15, 'limit': 1}),
        ('search_comps_by_trait', {'trait': '', 'level': 3, 'limit': 1}),
        ('search_comps_by_trait', {'trait': 'Mage', 'level': 3, 'limit': 51}),
        ('search_comps_by_trait', {'trait': 'Mage', 'level': 0, 'limit': 50, 'min_games': 20}),
        ('search_champion_items', {}),
        ('search_champion_items', {'champion': ''}),
        ('search_champion_items', {'champion': 'Ahri', 'items': ['', 'Chain Vest']}),
        ('search_champion_items', {'champion': 'Ahri', 'items': ['Chain Vest', 'Needlessly Large Rod', 'Tear of the Goddess']}),
        ('search_champion_items', {'champion': 'Ahri', 'extra': 1}),
    ]
    for name, arguments in cases:
        with pytest.raises(SessionError) as caught:
            validate_arguments(name, arguments)
        assert caught.value.code == 'invalid_input'
    validate_arguments('search_comps_by_champions', {'champions': ['Ahri'], 'limit': 1})
    validate_arguments('search_comps_by_trait', {'trait': 'Mage', 'level': 0, 'limit': 50})
    validate_arguments('search_champion_items', {'champion': 'Ahri'})
    validate_arguments('search_champion_items', {'champion': 'Ahri', 'items': ['Chain Vest', 'chain_vest']})


def test_index_drops_comps_and_trait_levels_below_100_games(tmp_path):
    boards = [{'placement': 1, 'units': ['Ahri'], 'traits': {'Mage': 3}} for _ in range(100)]
    boards += [{'placement': 1, 'units': ['Ahri'], 'traits': {'Mage': 6}} for _ in range(50)]
    boards += [{'placement': 1, 'units': ['Zed'], 'traits': {'Mage': 3}} for _ in range(99)]
    path = tmp_path / 'cutoff.sqlite'
    build_boards(boards, path, minimum_games=MIN_COMP_GAMES)
    index = CompIndex(path)
    assert [comp['champions'] for comp in index.search_comps_by_champions(['Ahri'], 5)['comps']] == [['Ahri']]
    assert index.search_comps_by_champions(['Ahri'], 5)['comps'][0]['games'] == 150
    assert index.search_comps_by_champions(['Zed'], 5)['comps'] == []
    assert [comp['champions'] for comp in index.search_comps_by_trait('Mage', 3, 5)['comps']] == [['Ahri']]
    assert index.search_comps_by_trait('Mage', 6, 5)['comps'] == []


def _ahri(items, stars, placements):
    return [{'placement': placement, 'units': {'Ahri': {'items': items, 'stars': stars}}, 'traits': {}}
            for placement in placements]


def test_item_builds_rank_by_win_rate_and_ignore_order_and_stars(tmp_path):
    boards = _ahri([23], 1, [1, 1])
    boards += _ahri([23], 3, [1, 1])
    boards += _ahri([33, 23], 2, [1] * 8 + [8, 8])
    boards += _ahri([5, 5], 2, [1, 1, 1, 1])
    path = tmp_path / 'items.sqlite'
    build_boards(boards, path)
    index = CompIndex(path)
    result = index.search_champion_items(' ahri ')
    assert result['champion'] == 'Ahri' and result['items'] == []
    assert [build['items'] for build in result['builds']] == [
        ['Chain Vest', 'Chain Vest'],
        ["Guinsoo's Rageblade"],
        ["Guinsoo's Rageblade", "Rabadon's Deathcap"],
    ]
    assert [build['item_ids'] for build in result['builds']] == [
        ['chain_vest', 'chain_vest'],
        ['guinsoos_rageblade'],
        ['guinsoos_rageblade', 'rabadons_deathcap'],
    ]
    guinsoo = result['builds'][1]
    assert guinsoo['games'] == 4 and guinsoo['top4'] == 4 and guinsoo['win_rate'] == 1.0
    paired = result['builds'][2]
    assert paired['games'] == 10 and paired['top4'] == 8 and paired['win_rate'] == 0.8
    jsonschema.validate(result, CHAMPION_ITEMS_OUTPUT)
    filtered = index.search_champion_items('Ahri', ['guinsoos_rageblade'])
    assert filtered['items'] == ["Guinsoo's Rageblade"]
    assert [build['items'] for build in filtered['builds']] == [
        ["Guinsoo's Rageblade"],
        ["Guinsoo's Rageblade", "Rabadon's Deathcap"],
    ]
    both = index.search_champion_items('Ahri', ["Guinsoo's Rageblade", 'rabadons_deathcap'])
    assert [build['items'] for build in both['builds']] == [
        ["Guinsoo's Rageblade", "Rabadon's Deathcap"]]
    doubled = index.search_champion_items('Ahri', ['Chain Vest', 'chain_vest'])
    assert [build['items'] for build in doubled['builds']] == [['Chain Vest', 'Chain Vest']]
    one = index.search_champion_items('Ahri', ['Chain Vest'])
    assert [build['items'] for build in one['builds']] == [['Chain Vest', 'Chain Vest']]
    assert index.search_champion_items('Ahri') == index.search_champion_items('Ahri', [])
    with pytest.raises(SessionError) as caught:
        index.search_champion_items('Ahri', ['spatula_of_doom'])
    assert caught.value.code == 'unknown_item'
    with pytest.raises(SessionError) as caught:
        index.search_champion_items('Nope')
    assert caught.value.code == 'unknown_champion'


def test_item_builds_drop_combinations_below_100_boards(tmp_path):
    boards = _ahri([23], 1, [1] * 100)
    boards += _ahri([5], 1, [1] * 99)
    path = tmp_path / 'item-cutoff.sqlite'
    build_boards(boards, path, minimum_games=MIN_COMP_GAMES)
    index = CompIndex(path)
    result = index.search_champion_items('Ahri')
    assert [build['items'] for build in result['builds']] == [["Guinsoo's Rageblade"]]
    assert result['builds'][0]['games'] == 100


def test_missing_database_is_a_structured_error(tmp_path):
    with pytest.raises(SessionError) as caught:
        CompIndex(tmp_path / 'missing.sqlite')
    assert caught.value.code == 'comp_index_unavailable'


@pytest.mark.anyio
async def test_comp_tools_do_not_change_the_game(tmp_path):
    import pickle

    from support import memory_client, started_session

    session = started_session(tmp_path)
    before = pickle.dumps(session.game)
    async with memory_client(session) as sdk:
        result = await sdk.call_tool('search_comps_by_champions', {'champions': ['ahri'], 'limit': 2})
        assert not result.isError, result.structuredContent
        data = result.structuredContent
        jsonschema.validate(data, COMP_CHAMPION_OUTPUT)
        assert data['champions'] == ['Ahri'] and len(data['comps']) == 2
        assert all('Ahri' in comp['champions'] and comp['games'] >= MIN_COMP_GAMES for comp in data['comps'])
        trait = await sdk.call_tool('search_comps_by_trait', {'trait': 'cultist', 'level': 9, 'limit': 1})
        assert not trait.isError, trait.structuredContent
        jsonschema.validate(trait.structuredContent, COMP_TRAIT_OUTPUT)
        assert trait.structuredContent['trait'] == 'Cultist'
        items = await sdk.call_tool('search_champion_items', {'champion': 'ahri', 'items': ['guinsoos_rageblade']})
        assert not items.isError, items.structuredContent
        jsonschema.validate(items.structuredContent, CHAMPION_ITEMS_OUTPUT)
        assert items.structuredContent['champion'] == 'Ahri'
        assert items.structuredContent['items'] == ["Guinsoo's Rageblade"]
        assert items.structuredContent['builds']
        assert all(comp['games'] >= MIN_COMP_GAMES and "Guinsoo's Rageblade" in comp['items']
                   for comp in items.structuredContent['builds'])
        error = await sdk.call_tool('search_comps_by_champions', {'champions': ['NoSuch'], 'limit': 1})
        assert error.isError and error.structuredContent['code'] == 'unknown_champion'
        assert pickle.dumps(session.game) == before


def test_recorded_challenger_index_matches_the_extract():
    index = CompIndex(default_database_path())
    assert index.meta['csv_sha256'] == OFFICIAL_CSV_SHA256
    assert int(index.meta['player_rows']) == OFFICIAL_PLAYER_ROWS
    assert int(index.meta['top4_rows']) == OFFICIAL_PLAYER_ROWS // 2
    assert int(index.meta['source_comps']) == OFFICIAL_UNIQUE_COMPS
    assert int(index.meta['source_trait_rows']) == OFFICIAL_TRAIT_ROWS
    assert int(index.meta['unique_comps']) == OFFICIAL_STORED_COMPS
    assert int(index.meta['trait_rows']) == OFFICIAL_STORED_TRAIT_ROWS
    assert int(index.meta['source_item_builds']) == OFFICIAL_ITEM_BUILDS
    assert int(index.meta['item_builds']) == OFFICIAL_STORED_ITEM_BUILDS
    assert int(index.meta['min_games']) == MIN_COMP_GAMES
    assert index.connection.execute('SELECT MIN(games) FROM item_builds').fetchone()[0] >= MIN_COMP_GAMES
    assert index.meta['win_definition'] == 'top4'
    assert index.connection.execute('SELECT MIN(games) FROM comps').fetchone()[0] >= MIN_COMP_GAMES
    assert index.connection.execute('SELECT MIN(games) FROM comp_trait').fetchone()[0] >= MIN_COMP_GAMES
    mask = 0
    for name in OFFICIAL_EXAMPLE_COMP:
        mask |= 1 << index.bit_of[name]
    row = index.connection.execute('SELECT games FROM comps WHERE mask = ?', (mask,)).fetchone()
    assert row['games'] == OFFICIAL_EXAMPLE_GAMES
    ranked = index.search_comps_by_champions(list(OFFICIAL_EXAMPLE_COMP), 5)
    assert ranked['comps']
    assert all(set(OFFICIAL_EXAMPLE_COMP) <= set(comp['champions']) for comp in ranked['comps'])
    rates = [comp['top4'] / comp['games'] for comp in ranked['comps']]
    assert rates == sorted(rates, reverse=True)
    cultist = index.search_comps_by_trait('Cultist', 9, 3)
    assert cultist['trait'] == 'Cultist' and cultist['level'] == 9
    assert len(cultist['comps']) == 3
    assert all(comp['games'] >= MIN_COMP_GAMES for comp in cultist['comps'])
    gloves = index.search_champion_items('Yone', ['thieves_gloves'])
    assert gloves['items'] == ["Thief's Gloves"]
    assert gloves['builds']
    assert all("Thief's Gloves" in build['items'] and 'thieves_gloves' in build['item_ids']
               and build['games'] >= MIN_COMP_GAMES for build in gloves['builds'])
    rates = [build['top4'] / build['games'] for build in gloves['builds']]
    assert rates == sorted(rates, reverse=True)
    jsonschema.validate(gloves, CHAMPION_ITEMS_OUTPUT)
    jsonschema.validate(ranked, COMP_CHAMPION_OUTPUT)
    jsonschema.validate(cultist, COMP_TRAIT_OUTPUT)
