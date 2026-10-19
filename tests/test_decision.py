"""Observation reads and process-owned MCP gameplay."""
import json
import pickle

import jsonschema
import pytest

from support import (board, capture_committed_state, client, install_units,
                     memory_client, session_fixture, assert_committed_state_unchanged)
from tft_mcp.session import GameSession, SessionError
from tft_mcp.tools import TOOLS
from tft_mcp.tool_schemas import OBSERVATION_SCHEMA
from tft_mcp.transport import seed_configuration


def test_opening_observation_includes_text_and_mask(tmp_path):
    session = session_fixture(tmp_path)
    player = install_units(session, bench=[(3, 'garen', 1, [])], board=[((6, 3), 'vayne', 1, [])])
    player.item_bench[7] = 'bf_sword'
    before = capture_committed_state(session)
    decision = session.get_decision()
    assert_committed_state_unchanged(session, before)
    jsonschema.validate(decision, OBSERVATION_SCHEMA)
    assert decision['start_turn'] is True and decision['terminal'] is False
    assert '6,3 vayne' in decision['text']
    assert '3 garen' in decision['text']
    assert '7 bf_sword' in decision['text']
    assert any(command['action_type'] == 0 for command in decision['mask'])
    decision['text'] += ' mutated'
    assert 'mutated' not in session.get_decision()['text']


def test_move_observation_is_the_simulator_delta(tmp_path):
    session = session_fixture(tmp_path)
    player = install_units(session, board=[((0, 0), 'garen', 1, []), ((3, 1), 'vayne', 1, [])])
    from Simulator.encoding.token.action import ActionToken
    session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
    opening = session.get_decision()
    assert opening['text'].startswith('round ')
    assert 'traits' in opening['text'].splitlines()
    move = next(command for command in opening['mask']
                if command['action_type'] == 5 and command['x1'] < 28 and command['x2'] < 28
                and command['x1'] != command['x2'])
    result = session.move_unit(source={'kind': 'board', 'x': move['x1'] // 4, 'y': move['x1'] % 4},
                               target={'kind': 'board', 'x': move['x2'] // 4, 'y': move['x2'] % 4})
    headers = [line for line in result['text'].splitlines() if line and not line.startswith(' ')]
    assert [line for line in headers if not line.startswith('actions ')] == ['action succeeded', 'board']
    assert result['text'] == session.game.llm_observe('player_0')['text']
    assert session.get_decision()['text'] == result['text']
    before = session.get_decision()
    with pytest.raises(SessionError) as error:
        session.sell_unit(location={'kind': 'bench', 'slot': 8})
    assert error.value.code == 'masked' and str(error.value) == 'The action failed.'
    assert session.get_decision() == before


def test_idle_decision_rejects_without_a_game(tmp_path):
    session = GameSession(tmp_path / 'audit.jsonl', tmp_path / 'native')
    with pytest.raises(SessionError, match='Start a game') as error:
        session.get_decision()
    assert error.value.code == 'no_game'


@pytest.mark.parametrize('mode', ['full', 'single_player'])
def test_bench_board_swap_reports_changed_traits(tmp_path, mode):
    from Simulator.encoding.token.action import ActionToken
    session = GameSession(tmp_path / 'audit.jsonl', tmp_path / 'native')
    session.start_game(0, mode)
    player = install_units(session, board=[((0, 0), 'garen', 1, [])],
                           bench=[(0, 'yasuo', 1, [])])
    with session.simulator_scope():
        player.update_team_tiers()
        session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
        vars(getattr(session.game, 'view', session.game)).pop('_llm_caches', None)
    opening = session.get_decision()
    assert 'traits' in opening['text'].splitlines()
    result = session.move_unit(source={'kind': 'bench', 'slot': 0},
                               target={'kind': 'board', 'x': 0, 'y': 0})
    assert 'traits' in result['text'].splitlines()
    assert 'exile' in result['text']
    assert session.get_decision() == result
    assert session.game.player_manager.player_states['player_0'].board[0][0].name == 'yasuo'


@pytest.mark.parametrize('mode', ['full', 'single_player'])
def test_duplicator_board_merge_reports_changed_unit_count(tmp_path, mode):
    from Simulator.encoding.token.action import ActionToken
    session = GameSession(tmp_path / 'audit.jsonl', tmp_path / 'native')
    session.start_game(0, mode)
    player = install_units(session, board=[((0, 0), 'yasuo', 1, []), ((1, 0), 'yasuo', 1, [])])
    player.item_bench[0] = 'champion_duplicator'
    with session.simulator_scope():
        session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
        vars(getattr(session.game, 'view', session.game)).pop('_llm_caches', None)
    assert 'units_in_play 2' in session.get_decision()['text']
    result = session.equip_item(item_slot=0, target={'kind': 'board', 'x': 0, 'y': 0})
    assert 'units_in_play 1' in result['text']
    assert session.game.player_manager.player_states['player_0'].num_units_in_play == 1
    assert session.get_decision() == result


@pytest.mark.parametrize('environment', [
    {}, *[{'TFT_MCP_SEED': seed} for seed in
          ('', '-1', '1.0', 'true', '2147483648', ' 0', '٠', '9' * 5000)],
])
def test_invalid_seed_configuration(environment):
    with pytest.raises(ValueError):
        seed_configuration(environment)


def test_seed_configuration_accepts_canonical_range_and_long_leading_zeroes():
    for raw, expected in [('0', 0), ('0001', 1), ('2147483647', 2147483647),
                          ('0' * 5000, 0), ('0' * 5000 + '2147483647', 2147483647)]:
        assert seed_configuration({'TFT_MCP_SEED': raw}) == expected


@pytest.mark.anyio
async def test_invalid_configuration_does_not_construct_session(monkeypatch):
    from tft_mcp import transport
    monkeypatch.delenv('TFT_MCP_SEED', raising=False)
    def forbidden(*args):
        pytest.fail('Invalid configuration constructed a simulator session')
    monkeypatch.setattr(transport, 'GameSession', forbidden)
    with pytest.raises(ValueError):
        await transport.serve()


@pytest.mark.anyio
async def test_action_families_follow_the_mask(tmp_path):
    session = session_fixture(tmp_path)
    player = install_units(session, bench=[(0, 'garen', 1, [])], offer='vayne')
    player.item_bench[0] = 'bf_sword'
    from Simulator.encoding.token.action import ActionToken
    session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
    async with memory_client(session) as sdk:
        schemas = {tool.name: tool.outputSchema for tool in (await sdk.list_tools()).tools}
        assert set(schemas) == {tool.name for tool in TOOLS} and len(schemas) == len(TOOLS)
        for name in ('start_game', 'close_game', 'get_game_status', 'get_shop', 'get_trait_champions'):
            before = pickle.dumps(session.game)
            error = await sdk.call_tool(name, {})
            assert error.isError and error.structuredContent['code'] == 'invalid_input'
            assert pickle.dumps(session.game) == before
        for name, arguments in [
            ('buy_unit', {'shop_slot': 0}),
            ('move_unit', {'source': {'kind': 'bench', 'slot': 0}, 'target': board(3, 0)}),
            ('equip_item', {'item_slot': 0, 'target': board(3, 0)}),
            ('refresh_shop', {}), ('buy_xp', {}),
        ]:
            result = await sdk.call_tool(name, arguments)
            assert not result.isError, result.structuredContent
            data = result.structuredContent
            jsonschema.validate(data, schemas[name])
            assert data['text'].startswith('action succeeded') and data['start_turn'] is False
            assert data == session.get_decision()
        masked = await sdk.call_tool('sell_unit', {'location': {'kind': 'bench', 'slot': 8}})
        assert masked.isError and masked.structuredContent['code'] == 'masked'
        result = await sdk.call_tool('end_turn', {})
        assert not result.isError
        jsonschema.validate(result.structuredContent, schemas['end_turn'])
        assert result.structuredContent['start_turn'] is True
        assert result.structuredContent == session.get_decision()


@pytest.mark.anyio
@pytest.mark.parametrize('failure', ['projection', 'schema'])
async def test_post_action_observation_failure_rolls_back(tmp_path, monkeypatch, failure):
    session = session_fixture(tmp_path)
    install_units(session, offer='garen')
    async with memory_client(session) as sdk:
        before = capture_committed_state(session)
        original = GameSession._public_observation
        def invalid(self, step_result=None):
            if failure == 'projection':
                raise RuntimeError('Injected observation failure')
            return {**original(self, step_result), 'unexpected': True}
        with monkeypatch.context() as patch:
            patch.setattr(GameSession, '_public_observation', invalid)
            result = await sdk.call_tool('buy_unit', {'shop_slot': 0})
        assert result.isError and result.structuredContent['code'] == 'internal_error'
        audit = session.audit_path.read_bytes()
        assert audit.startswith(before['logs'][0])
        added = [json.loads(line) for line in audit[len(before['logs'][0]):].splitlines()]
        assert len(added) == 1 and added[0]['event'] == 'tool_error'
        before['logs'] = (audit, before['logs'][1])
        assert_committed_state_unchanged(session, before)
        retry = await sdk.call_tool('buy_unit', {'shop_slot': 0})
        assert not retry.isError
        assert retry.structuredContent['text'].startswith('action succeeded')
        assert session.game.actions_taken['player_0'] == 1


@pytest.mark.anyio
async def test_production_full_lobby_snapshot_and_shutdown(tmp_path):
    async with client(tmp_path, TFT_MCP_SEED='0') as sdk:
        tools = {tool.name: tool for tool in (await sdk.list_tools()).tools}
        assert set(tools) == {tool.name for tool in TOOLS}
        initialized = await sdk.initialize()
        assert 'A seeded game already runs' in initialized.instructions[:800]
        assert '15-action' in initialized.instructions[:800]
        first = await sdk.call_tool('get_decision', {})
        assert not first.isError and first.structuredContent['start_turn'] is True
        decision = first.structuredContent
        for _ in range(40):
            result = await sdk.call_tool('end_turn', {})
            assert not result.isError, result.structuredContent
            decision = result.structuredContent
            jsonschema.validate(decision, tools['end_turn'].outputSchema)
            if decision['terminal']:
                break
        assert decision['terminal'] is True
        assert (await sdk.call_tool('get_decision', {})).structuredContent == decision
        terminal = await sdk.call_tool('buy_xp', {})
        assert terminal.isError and terminal.structuredContent['code'] == 'game_terminal'
        players = (await sdk.call_tool('get_players', {})).structuredContent['players']
        assert sorted(row['placement'] for row in players) == list(range(1, 9))
    records = [json.loads(line) for line in (tmp_path / 'audit.jsonl').read_text().splitlines()]
    assert records[0]['event'] == 'process_start' and records[0]['seed'] == 0
    starts = [row for row in records if row['event'] == 'game_started']
    assert len(starts) == 1 and starts[0]['seed'] == 0
    assert records[-1]['event'] == 'game_closed'
    assert records[-1]['outcome']['lobby_complete'] is True
