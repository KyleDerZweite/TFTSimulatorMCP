"""Production SDK acceptance with preserved calls and exact gameplay replay."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from support import client


ACTIONS = {'buy_unit', 'sell_unit', 'move_unit', 'equip_item', 'refresh_shop', 'buy_xp', 'end_turn'}
READS = ('get_decision', 'get_board', 'get_players')
CATALOGS = {'search_champions', 'get_champion', 'search_traits', 'get_trait',
            'search_items', 'get_item'}
TOOLS = ACTIONS | set(READS) | CATALOGS | {
    'get_champion_pool', 'search_comps_by_champions', 'search_comps_by_trait',
    'search_champion_items'}


async def call(sdk, transcript, name, arguments=None, error=None):
    arguments = deepcopy(arguments or {})
    result = await sdk.call_tool(name, arguments)
    data = deepcopy(result.structuredContent)
    transcript.append({'tool': name, 'arguments': arguments,
                       'result': data, 'is_error': bool(result.isError)})
    assert bool(result.isError) == (error is not None), transcript[-1]
    if error:
        assert data['code'] == error
        assert data['message'] and isinstance(data['details'], dict)
    return data


def validate_audit(path, transcript):
    records = [json.loads(line) for line in (path / 'audit.jsonl').read_text().splitlines()]
    assert records and all(isinstance(record, dict) for record in records)
    assert len({record['server_id'] for record in records}) == 1
    assert [record['sequence'] for record in records] == list(range(1, len(records) + 1))
    assert [record['event'] for record in records[:3]] == ['process_start', 'start_candidate', 'game_started']
    assert records[0]['seed'] == 0
    assert records[2]['seed'] == 0
    index = 3
    for expected in transcript:
        record = records[index]
        assert record['tool'] == expected['tool']
        assert record['arguments'] == expected['arguments']
        if expected['is_error']:
            assert record['event'] == 'tool_error'
            assert record['is_error'] is True
            assert record['result'] == expected['result']
            index += 1
            continue
        assert record['event'] == 'tool_request'
        index += 1
        between = []
        while records[index]['event'] != 'tool_result':
            between.append(records[index])
            assert records[index]['event'] in {'progression', 'lobby_complete'}
            index += 1
        result = records[index]
        assert result['tool'] == expected['tool']
        assert result['is_error'] is False and result['result'] == expected['result']
        if expected['tool'] in ACTIONS:
            assert between and any(event['event'] == 'progression' for event in between)
            assert len({event['game_id'] for event in between}) == 1
            assert all(event['event'] in {'progression', 'lobby_complete'} for event in between)
        else:
            assert not between
        index += 1
    # The production server closes an active game after stdin closes.
    assert [record['event'] for record in records[index:]] == ['game_closed']
    for record in records:
        if 'native_log_dir' in record:
            directory = Path(record['native_log_dir']).resolve()
            assert directory.is_relative_to((path / 'native').resolve())
            assert directory.is_dir() and (directory / 'log.txt').is_file()
    (path / 'sdk-transcript.json').write_text(json.dumps(transcript, indent=2))
    return records


@pytest.mark.anyio
async def test_production_incomplete_shutdown_and_restart(tmp_path):
    initial = None
    identities = []
    for name in ('actual', 'fresh'):
        path = tmp_path / name
        path.mkdir()
        transcript = []
        async with client(path) as sdk:
            state = await checkpoint(sdk, transcript)
            identities.append(state['get_players']['game_id'])
            if initial is None:
                initial = comparable(state)
            else:
                assert comparable(state) == initial
        events = validate_audit(path, transcript)
        closed = events[-1]
        assert closed['game_id'] == identities[-1]
        assert closed['outcome'] == {'controlled_placement': None, 'lobby_complete': False,
                                     'reason': 'closed_incomplete'}
    assert identities[0] != identities[1]


def comparable(data):
    """Copy responses and replace only generated game identity fields."""
    if isinstance(data, dict):
        return {key: '<game>' if key in {'game_id', 'closed_game_id'} and value is not None
                else comparable(value) for key, value in data.items()}
    if isinstance(data, list):
        return [comparable(value) for value in data]
    return deepcopy(data)


async def checkpoint(sdk, transcript, order=READS):
    result = {name: await call(sdk, transcript, name) for name in order}
    decision = result['get_decision']
    assert set(decision) == {'reward', 'start_turn', 'terminal', 'mask', 'text'}
    assert isinstance(decision['mask'], list)
    assert decision['text']
    assert result['get_board']['game_id'] == result['get_players']['game_id']
    assert result['get_board']['player_id'] == 'player_0'
    assert len(result['get_board']['slots']) == 28
    assert len(result['get_players']['players']) == 8
    living = next((row['player_id'] for row in result['get_players']['players']
                   if not row['controlled'] and row['status'] == 'alive'), None)
    if living:
        result['get_board_opponent'] = await call(sdk, transcript, 'get_board', {'player_id': living})
        assert result['get_board_opponent']['player_id'] == living
    return result


async def rules(sdk, transcript):
    champions = await call(sdk, transcript, 'search_champions')
    assert champions['champions']
    selected = champions['champions'][0]
    champion = await call(sdk, transcript, 'get_champion', {'champion_id': selected['champion_id']})
    assert champion['champion_id'] == selected['champion_id']
    assert champion['cost'] == selected['cost'] and champion['traits'] == selected['traits']
    assert champion['base_stats'] and champion['rule_parameters']
    traits = await call(sdk, transcript, 'search_traits')
    assert traits['traits']
    selected = traits['traits'][0]
    trait = await call(sdk, transcript, 'get_trait', {'trait_id': selected['trait_id']})
    assert trait['thresholds'] == selected['thresholds']
    members = await call(sdk, transcript, 'search_champions', {'trait_id': selected['trait_id']})
    assert [row['champion_id'] for row in members['champions']] == trait['champion_ids']
    assert all(selected['trait_id'] in row['traits'] for row in members['champions'])
    items = await call(sdk, transcript, 'search_items', {'kind': 'component'})
    assert items['items']
    selected = items['items'][0]
    item = await call(sdk, transcript, 'get_item', {'item_id': selected['item_id']})
    assert all(item[key] == selected[key] for key in ('item_id', 'kind', 'craftable'))
    assert item['base_stats'] and item['builds_into']
    return [champions, champion, traits, trait, members, items, item]


def location_from_flat(index):
    if index >= 28:
        return {'kind': 'bench', 'slot': index - 28}
    return {'kind': 'board', 'x': index // 4, 'y': index % 4}


def commands(state, action_type):
    return [command for command in state['get_decision']['mask'] if command['action_type'] == action_type]


def check_action(name, arguments, result, before, after):
    assert set(result) == {'reward', 'start_turn', 'terminal', 'mask', 'text'}
    assert result == after['get_decision']
    if name == 'end_turn':
        assert result['start_turn'] or result['terminal']
        assert result['text']
        if not result['terminal']:
            assert after['get_board']['round'] > before['get_board']['round']
        return
    assert result['text'].startswith('action succeeded') and result['start_turn'] is False
    assert after['get_board']['round'] == before['get_board']['round']
    if name == 'buy_unit':
        assert any(command['action_type'] == 3 and command['x1'] == arguments['shop_slot']
                   for command in before['get_decision']['mask'])
    elif name == 'move_unit':
        assert arguments['source'] != arguments['target']
    elif name == 'equip_item':
        assert any(command['action_type'] == 6 and command['x2'] == arguments['item_slot']
                   for command in before['get_decision']['mask'])


async def original_actions(sdk, transcript, tape, receipts, states):
    state = states[-1]

    async def action(name, arguments=None):
        nonlocal state
        arguments = deepcopy(arguments or {})
        tape.append({'tool': name, 'arguments': arguments})
        receipt = await call(sdk, transcript, name, arguments)
        after = await checkpoint(sdk, transcript)
        check_action(name, arguments, receipt, state, after)
        receipts.append(receipt)
        states.append(after)
        state = after

    def take(kind):
        return commands(state, kind)

    await action('end_turn')
    bought = take(3)[0]
    await action('buy_unit', {'shop_slot': bought['x1']})
    moved = take(5)[0]
    await action('move_unit', {'source': location_from_flat(moved['x1']),
                               'target': location_from_flat(moved['x2'])})
    sold = take(4)[0]
    await action('sell_unit', {'location': location_from_flat(sold['x1'])})
    await action('refresh_shop')
    await action('buy_xp')
    equipped = False
    for _ in range(40):
        if take(6):
            chosen = take(6)[0]
            await action('equip_item', {'item_slot': chosen['x2'], 'target': location_from_flat(chosen['x1'])})
            equipped = True
            break
        await action('end_turn')
        if state['get_decision']['terminal']:
            break
    assert equipped, tape
    assert ACTIONS <= {entry['tool'] for entry in tape}
    for _ in range(48):
        if state['get_decision']['terminal']:
            break
        await action('end_turn')
    assert state['get_decision']['terminal'] is True, tape


def check_start_identity(record):
    import hashlib
    from importlib import metadata
    import os
    import sys
    import Simulator
    from Simulator import config
    from Simulator.simulators.tft_simulator import TFT_Simulator

    root = Path(Simulator.__file__).resolve().parent
    digest = hashlib.sha256()
    for source in sorted(root.rglob('*.py')):
        digest.update(str(source.relative_to(root)).encode())
        digest.update(source.read_bytes())
    assert record['simulator']['source_sha256'] == digest.hexdigest()
    provenance = metadata.distribution('tft-simulator').read_text('direct_url.json')
    if provenance and 'vcs_info' in json.loads(provenance):
        assert record['simulator']['revision'] == json.loads(provenance)['vcs_info']['commit_id']
    elif os.environ.get('TFT_MCP_SIMULATOR_REVISION'):
        assert record['simulator']['revision'] == os.environ['TFT_MCP_SIMULATOR_REVISION']
    else:
        assert record['simulator']['revision'] == 'sha256:' + digest.hexdigest()
    assert record['simulator']['environment_name'] == TFT_Simulator.metadata['name']
    assert record['simulator']['distribution_version'] == metadata.version('tft-simulator')
    assert record['seed'] == record['baseline_seed'] == 0
    assert record['baseline'] == 'Simulator.generators.default_agent.Default_Agent(False)'
    assert record['controlled_player_id'] == 'player_0'
    assert record['hash_seed'] == '0' and record['hash_probe'] == hash('tft-mcp')
    assert record['runtime'] == {'python': sys.version, 'implementation': sys.implementation.name,
        'dependencies': {name: metadata.version(name) for name in ('numpy', 'PettingZoo', 'gymnasium', 'mcp')}}
    defaults = {}
    for key, value in vars(config).items():
        if key.isupper():
            try:
                defaults[key] = json.loads(json.dumps(value))
            except (TypeError, ValueError):
                pass
    assert record['configuration'] == {
        'mode': 'full',
        'num_players': 8, 'max_actions_per_round': 15, 'reward_type': 'winloss',
        'render_mode': None, 'render_path': 'Games', 'multi_step_position': False,
        'preset_battle': False, 'step_until_units_placed': False,
        'observation_class': 'Simulator.encoding.token.basic_observation.ObservationToken',
        'action_class': 'Simulator.encoding.token.action.ActionToken', 'simulator_defaults': defaults}


@pytest.mark.anyio
async def test_production_full_game_exact_tape_three_process_replay(tmp_path):
    import jsonschema

    tape, accepted = [], []
    for run in range(3):
        path = tmp_path / str(run)
        path.mkdir()
        transcript, receipts, states = [], [], []
        try:
            async with client(path) as sdk:
                schemas = {tool.name: tool.outputSchema for tool in (await sdk.list_tools()).tools}
                assert set(schemas) == TOOLS
                catalog = await rules(sdk, transcript)
                await call(sdk, transcript, 'get_champion_pool', {'champion_id': 'garen'})
                comps = await call(sdk, transcript, 'search_comps_by_champions',
                                   {'champions': ['Ahri'], 'limit': 1})
                assert comps['champions'] == ['Ahri'] and comps['comps']
                assert 'Ahri' in comps['comps'][0]['champions']
                trait_comps = await call(sdk, transcript, 'search_comps_by_trait',
                                         {'trait': 'Cultist', 'level': 9, 'limit': 1})
                assert trait_comps['trait'] == 'Cultist' and trait_comps['level'] == 9
                assert trait_comps['comps']
                item_builds = await call(sdk, transcript, 'search_champion_items',
                                         {'champion': 'Ahri', 'items': ['guinsoos_rageblade']})
                assert item_builds['champion'] == 'Ahri'
                assert item_builds['items'] == ["Guinsoo's Rageblade"]
                assert item_builds['builds']
                assert "Guinsoo's Rageblade" in item_builds['builds'][0]['items']
                rule_requests = [(entry['tool'], entry['arguments']) for entry in transcript]
                states.append(await checkpoint(sdk, transcript))
                if run == 0:
                    await original_actions(sdk, transcript, tape, receipts, states)
                else:
                    for index, action in enumerate(tape):
                        before = states[-1]
                        if run == 2 and index % 3 == 1:
                            assert await checkpoint(sdk, transcript, tuple(reversed(READS))) == before
                            for name, arguments in reversed(rule_requests):
                                await call(sdk, transcript, name, arguments)
                            assert await rules(sdk, transcript) == catalog
                        if run == 2 and action['tool'] == 'move_unit':
                            arguments = {'source': action['arguments']['source'],
                                         'target': action['arguments']['source']}
                            await call(sdk, transcript, 'move_unit', arguments, error='masked')
                            assert await checkpoint(sdk, transcript) == before
                        receipt = await call(sdk, transcript, action['tool'], action['arguments'])
                        after = await checkpoint(sdk, transcript)
                        check_action(action['tool'], action['arguments'], receipt, before, after)
                        assert comparable(receipt) == comparable(accepted[0]['receipts'][index])
                        assert comparable(after) == comparable(accepted[0]['states'][index + 1])
                        receipts.append(receipt)
                        states.append(after)
                decision = states[-1]['get_decision']
                assert decision['terminal'] is True
                players = states[-1]['get_players']['players']
                outcome = {'controlled_placement': next(row['placement'] for row in players if row['controlled']),
                           'lobby_complete': True, 'reason': 'lobby_complete'}
                assert 1 <= outcome['controlled_placement'] <= 8
                assert sorted(row['placement'] for row in players) == list(range(1, 9))
                assert sum(row['status'] == 'winner' for row in players) == 1
                assert all(row['status'] != 'alive' for row in players)
                assert next(row['placement'] for row in players if row['controlled']) == outcome['controlled_placement']
                if outcome['controlled_placement'] != 1:
                    from support import observation_round
                    live_round = observation_round(decision['text'])
                    assert states[-1]['get_board']['round'] < live_round
                eliminated = next(row['player_id'] for row in players
                                  if not row['controlled'] and row['status'] == 'eliminated')
                await call(sdk, transcript, 'get_board', {'player_id': eliminated}, error='player_eliminated')
                for _ in range(2):
                    assert await checkpoint(sdk, transcript) == states[-1]
                for action in tape:
                    await call(sdk, transcript, action['tool'], action['arguments'], error='game_terminal')
                assert await checkpoint(sdk, transcript) == states[-1]
        finally:
            for name, data in [('sdk-transcript', transcript), ('action-tape', tape),
                               ('receipts', receipts), ('checkpoints', states)]:
                (path / (name + '.json')).write_text(json.dumps(data, indent=2))
        events = validate_audit(path, transcript)
        assert [{'tool': entry['tool'], 'arguments': entry['arguments']} for entry in transcript
                if entry['tool'] in ACTIONS and not entry['is_error']] == tape
        for entry in transcript:
            if not entry['is_error']:
                jsonschema.validate(entry['result'], schemas[entry['tool']])
        assert {entry['tool'] for entry in transcript if not entry['is_error']} == TOOLS
        starts = [event for event in events if event['event'] == 'game_started']
        assert len(starts) == 1
        check_start_identity(starts[0])
        complete = [event for event in events if event['event'] == 'lobby_complete']
        assert len(complete) == 1 and complete[0]['outcome'] == outcome
        assert complete[0]['placements'] == {row['player_id']: row['placement'] for row in players}
        closes = [event for event in events if event['event'] == 'game_closed']
        assert len(closes) == 1 and closes[0]['outcome'] == outcome
        # Keep encounter order and every repeated native action. Only transport IDs and paths vary.
        progression = [{key: event[key] for key in ('player_id', 'round', 'kind', 'action', 'placements')}
                       for event in events if event['event'] == 'progression']
        assert {event['player_id'] for event in progression} == {f'player_{index}' for index in range(8)}
        evidence = {'receipts': comparable(receipts), 'states': comparable(states),
                    'catalog': catalog, 'progression': progression,
                    'start': {key: value for key, value in starts[0].items()
                              if key not in {'game_id', 'native_log_dir', 'server_id', 'sequence'}},
                    'outcome': outcome, 'placements': complete[0]['placements']}
        accepted.append(evidence)
        assert evidence == accepted[0]
    assert len({json.loads((tmp_path / str(run) / 'audit.jsonl').read_text().splitlines()[0])['server_id']
                for run in range(3)}) == 3


@pytest.mark.anyio
async def test_fifteenth_legal_move_resolves_the_round(tmp_path):
    transcript = []
    async with client(tmp_path) as sdk:
        await call(sdk, transcript, 'end_turn')
        initial = await checkpoint(sdk, transcript)
        moved = commands(initial, 5)[0]
        source = location_from_flat(moved['x1'])
        target = location_from_flat(moved['x2'])
        before = initial
        for _ in range(14):
            arguments = {'source': source, 'target': target}
            receipt = await call(sdk, transcript, 'move_unit', arguments)
            after = await checkpoint(sdk, transcript)
            check_action('move_unit', arguments, receipt, before, after)
            assert after['get_board']['round'] == initial['get_board']['round']
            source, target = target, source
            before = after
        resolving = await call(sdk, transcript, 'move_unit', {'source': source, 'target': target})
        from support import observation_round
        assert resolving['start_turn'] is True and resolving['text'].startswith('action succeeded\n')
        assert observation_round(resolving['text']) > initial['get_board']['round']
    events = validate_audit(tmp_path, transcript)
    assert not any(event['event'] == 'tool_error' for event in events)


@pytest.mark.anyio
async def test_production_unavailable_audit_preserves_external_error_and_recovers(tmp_path):
    transcript, external_errors = [], []
    async with client(tmp_path) as sdk:
        await call(sdk, transcript, 'end_turn')
        before = await checkpoint(sdk, transcript)
        audit = tmp_path / 'audit.jsonl'
        saved = audit.read_bytes()
        native = {str(path): path.read_bytes() for path in (tmp_path / 'native').rglob('*') if path.is_file()}
        audit.unlink()
        audit.mkdir()
        try:
            await call(sdk, external_errors, 'buy_unit', {'shop_slot': 0}, error='log_unavailable')
            assert audit.is_dir() and not list(audit.iterdir())
            assert all(Path(path).read_bytes() == data for path, data in native.items())
        finally:
            audit.rmdir()
            audit.write_bytes(saved)
            (tmp_path / 'external-sdk-errors.json').write_text(json.dumps(external_errors, indent=2))
        assert audit.read_bytes() == saved
        assert await checkpoint(sdk, transcript) == before
        purchased = await call(sdk, transcript, 'buy_unit', {'shop_slot': 0})
        assert purchased['text'].startswith('action succeeded') and purchased['start_turn'] is False
        assert purchased != before['get_decision']
    validate_audit(tmp_path, transcript)


def test_production_requires_explicit_seed(tmp_path):
    import os
    import subprocess
    import sys

    environment = dict(os.environ)
    environment.pop('APPIMAGE', None)
    environment.pop('TFT_MCP_SEED', None)
    command = os.environ.get('TFT_MCP_TEST_COMMAND')
    if command:
        environment.pop('PYTHONPATH', None)
        arguments = [command]
    else:
        environment['PYTHONPATH'] = str(Path(__file__).parents[1] / 'src')
        arguments = [sys.executable, '-m', 'tft_mcp']
    result = subprocess.run(arguments, env=environment, cwd=tmp_path,
                            input='', capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert result.stdout == ''
    assert 'TFT_MCP_SEED requires decimal digits in 0..2147483647.' in result.stderr
