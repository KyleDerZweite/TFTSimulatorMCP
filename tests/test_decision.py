"""Real-session snapshots and automatic process-owned MCP gameplay."""
import json
import pickle

import jsonschema
import pytest

from support import (bench, board, capture_committed_state, client, install_units,
                     memory_client, session_fixture, assert_committed_state_unchanged)
from tft_mcp.session import GameSession, SessionError
from tft_mcp.tools import TOOLS
from tft_mcp.tool_schemas import DECISION_SCHEMA
from tft_mcp.transport import seed_configuration


def test_decision_one_freeze_pure_detached_and_native_economy(tmp_path, monkeypatch):
    import tft_mcp.session as module

    session = session_fixture(tmp_path)
    player = install_units(session, bench=[(3, 'garen', 1, [])], board=[((6, 3), 'vayne', 1, [])])
    player.item_bench[7] = 'bf_sword'
    player.refresh_cost, player.exp_cost = 3, 5
    before = capture_committed_state(session)
    original = module.freeze_player
    calls = []
    def counted(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(module, 'freeze_player', counted)
    decision = session.get_decision()
    assert calls == [1]
    assert_committed_state_unchanged(session, before)
    jsonschema.validate(decision, DECISION_SCHEMA)
    assert decision['board'][0]['location'] == board(6, 3)
    assert decision['bench'][0]['location'] == bench(3)
    assert decision['items'] == [{'slot': 7, 'item': 'bf_sword'}]
    assert decision['shop'] == session.get_shop()['slots']
    assert decision['economy']['refresh_cost'] == 3
    assert decision['economy']['exp_cost'] == 5
    assert decision['economy']['next_level_cost'] == player.level_costs[player.level]
    assert all(row['count'] != 0 for row in decision['traits'])
    decision['board'][0]['unit']['items'].append('invented')
    assert session.get_decision()['board'][0]['unit']['items'] == []
    player.level = player.max_level
    assert session.get_decision()['economy']['next_level_cost'] is None


def test_idle_and_corrupt_shop_decisions_reject_without_mutation(tmp_path):
    session = GameSession(tmp_path / 'audit.jsonl', tmp_path / 'native')
    with pytest.raises(SessionError, match='Start a game') as error:
        session.get_decision()
    assert error.value.code == 'no_game'
    session.start_game(0)
    session.game.player_manager.player_states['player_0'].shop[0] = 'invented'
    before = capture_committed_state(session)
    with pytest.raises(SessionError) as error:
        session.get_decision()
    assert error.value.code == 'internal_error'
    assert_committed_state_unchanged(session, before)


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
async def test_action_families_and_strict_omitted_tools(tmp_path):
    session = session_fixture(tmp_path)
    player = install_units(session, bench=[(0, 'garen', 1, [])], offer='vayne')
    player.item_bench[0] = 'bf_sword'
    async with memory_client(session) as sdk:
        schemas = {tool.name: tool.outputSchema for tool in (await sdk.list_tools()).tools}
        assert set(schemas) == {tool.name for tool in TOOLS} and len(schemas) == 16
        for name in ('start_game', 'close_game', 'get_game_status', 'get_shop', 'get_trait_champions'):
            before = pickle.dumps(session.game)
            error = await sdk.call_tool(name, {})
            assert error.isError and error.structuredContent['code'] == 'invalid_input'
            assert pickle.dumps(session.game) == before
        for name, arguments in [
            ('buy_unit', {'shop_slot': 0}),
            ('move_unit', {'source': bench(0), 'target': board(3, 0)}),
            ('equip_item', {'item_slot': 0, 'target': board(3, 0)}),
            ('sell_unit', {'location': bench(1)}),
            ('refresh_shop', {}), ('buy_xp', {}),
        ]:
            result = await sdk.call_tool(name, arguments)
            assert not result.isError, result
            data = result.structuredContent
            jsonschema.validate(data, schemas[name])
            assert data['receipt']['status'] == data['decision']['status']
            assert data['decision'] == session.get_decision()
        result = await sdk.call_tool('end_turn', {})
        assert not result.isError
        jsonschema.validate(result.structuredContent, schemas['end_turn'])
        assert result.structuredContent == session.get_decision()


@pytest.mark.anyio
@pytest.mark.parametrize('failure', ['projection', 'schema'])
async def test_post_action_decision_failure_rolls_back(tmp_path, monkeypatch, failure):
    session = session_fixture(tmp_path)
    install_units(session, offer='garen')
    async with memory_client(session) as sdk:
        before = capture_committed_state(session)
        original = session.get_decision
        def invalid():
            if failure == 'projection':
                raise RuntimeError('Injected decision projection failure')
            return {**original(), 'unexpected': True}
        with monkeypatch.context() as patch:
            patch.setattr(session, 'get_decision', invalid)
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
        assert retry.structuredContent['decision']['status']['planning_budget']['remaining'] == 13


@pytest.mark.anyio
async def test_production_full_lobby_snapshot_and_shutdown(tmp_path):
    async with client(tmp_path, TFT_MCP_SEED='0') as sdk:
        tools = {tool.name: tool for tool in (await sdk.list_tools()).tools}
        assert set(tools) == {tool.name for tool in TOOLS}
        initialized = await sdk.initialize()
        assert 'A seeded game already runs' in initialized.instructions[:512]
        assert '14 actions' in initialized.instructions[:512]
        first = await sdk.call_tool('get_decision', {})
        assert not first.isError and first.structuredContent['status']['state'] == 'running'
        decision = first.structuredContent
        for _ in range(40):
            result = await sdk.call_tool('end_turn', {})
            assert not result.isError
            decision = result.structuredContent
            jsonschema.validate(decision, tools['end_turn'].outputSchema)
            if decision['status']['state'] == 'terminal':
                break
        assert decision['status']['state'] == 'terminal'
        assert decision['status']['outcome']['lobby_complete'] is True
        assert decision['snapshot_round'] < decision['status']['round']
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
    assert records[-1]['outcome'] == decision['status']['outcome']
