import json
import os
from pathlib import Path
import sys

import jsonschema
import pytest

from support import client, memory_client, started_session
from tft_mcp.errors import SessionError
from tft_mcp.session import GameSession
from tft_mcp.tool_schemas import STATUS_SCHEMA


@pytest.mark.anyio
async def test_production_discovery_and_running_game(tmp_path):
    async with client(tmp_path) as sdk:
        tools = (await sdk.list_tools()).tools
        assert len(tools) == 20
        assert {tool.name for tool in tools} == {
            'get_decision', 'get_board', 'get_players', 'search_champions',
            'get_champion', 'get_champion_pool', 'search_traits', 'get_trait', 'search_items', 'get_item',
            'search_comps_by_champions', 'search_comps_by_trait', 'search_champion_items',
            'buy_unit', 'sell_unit', 'move_unit', 'equip_item', 'refresh_shop', 'buy_xp', 'end_turn'}
        decision = (await sdk.call_tool('get_decision', {})).structuredContent
        assert decision['start_turn'] is True and decision['terminal'] is False
        assert decision['text'].startswith('round 1\n')
        assert any(command['action_type'] == 0 for command in decision['mask'])


@pytest.mark.anyio
async def test_strict_inputs_omitted_tools_and_process_restart(tmp_path):
    identities = []
    for _ in range(2):
        async with client(tmp_path, TFT_MCP_SEED='2147483647') as sdk:
            initial = (await sdk.call_tool('get_decision', {})).structuredContent
            identities.append((await sdk.call_tool('get_players', {})).structuredContent['game_id'])
            for name, arguments in [
                ('start_game', {'seed': 0}), ('close_game', {}), ('get_game_status', {}),
                ('get_shop', {}), ('get_bench', {}), ('get_items', {}), ('get_economy', {}),
                ('get_traits', {}), ('get_round', {}), ('get_trait_champions', {'trait_id': 'ninja'}),
                ('get_decision', {'extra': 1}), ('end_turn', {'extra': 1}),
            ]:
                error = await sdk.call_tool(name, arguments)
                assert error.isError
                assert set(error.structuredContent) == {'code', 'message', 'details'}
                assert error.structuredContent['code'] == 'invalid_input'
                assert (await sdk.call_tool('get_decision', {})).structuredContent == initial
    assert identities[0] != identities[1]
    records = [json.loads(line) for line in (tmp_path / 'audit.jsonl').read_text().splitlines()]
    assert len([row for row in records if row['event'] == 'game_started']) == 2
    closed = [row for row in records if row['event'] == 'game_closed']
    assert len(closed) == 2 and all(row['outcome']['reason'] == 'closed_incomplete' for row in closed)


@pytest.mark.anyio
async def test_bootstrap_reexec_records_fixed_hash_and_reproducibility(tmp_path):
    import subprocess
    expected = subprocess.check_output([sys.executable, '-c', 'print(hash("tft-mcp"))'],
                                      env={**os.environ, 'PYTHONHASHSEED': '0'}, text=True).strip()
    for hash_seed in ['random', '42', '0']:
        async with client(tmp_path, PYTHONHASHSEED=hash_seed, TFT_MCP_SEED='123') as sdk:
            assert not (await sdk.call_tool('get_decision', {})).isError
    records = [json.loads(line) for line in (tmp_path / 'audit.jsonl').read_text().splitlines()]
    starts = [row for row in records if row['event'] == 'game_started']
    assert len(starts) == 3
    for server_id in {row['server_id'] for row in records}:
        rows = [row for row in records if row['server_id'] == server_id]
        sequences = [row['sequence'] for row in rows]
        assert sequences == sorted(set(sequences))
        events = [row['event'] for row in rows]
        assert events.index('process_start') < events.index('game_started') < events.index('tool_request')
    for row in starts:
        assert row['hash_seed'] == '0' and str(row['hash_probe']) == expected
        assert row['seed'] == row['baseline_seed'] == 123
        assert row['baseline'] == 'Simulator.generators.default_agent.Default_Agent(False)'
        from Simulator.simulators.tft_simulator import TFT_Simulator
        assert row['simulator']['environment_name'] == TFT_Simulator.metadata['name']
        assert row['simulator']['revision'] and len(row['simulator']['source_sha256']) == 64
        assert row['configuration']['num_players'] == 8
        assert row['runtime']['python']
        assert set(row['runtime']['dependencies']) == {'numpy', 'PettingZoo', 'gymnasium', 'mcp'}
        assert all(row['runtime']['dependencies'].values())


@pytest.mark.anyio
@pytest.mark.parametrize('environment', [
    {'TFT_MCP_AUDIT_PATH': '/proc/tft-mcp-audit.jsonl'},
    {'TFT_MCP_NATIVE_LOG_DIR': '/proc/tft-mcp-native'},
])
async def test_startup_log_failure_does_not_expose_session(tmp_path, environment):
    with pytest.raises(ExceptionGroup):
        async with client(tmp_path, **environment):
            pytest.fail('Startup failure exposed an MCP session')
    audit = tmp_path / 'audit.jsonl'
    if audit.exists():
        records = [json.loads(line) for line in audit.read_text().splitlines()]
        assert not any(row['event'] == 'game_started' for row in records)


def test_failed_close_keeps_game_active(tmp_path):
    session = started_session(tmp_path)
    started = session.get_game_status()
    saved = session.audit_path.read_bytes()
    session.audit_path.unlink()
    session.audit_path.mkdir()
    with pytest.raises(SessionError) as error:
        session.close_game()
    assert error.value.code == 'log_unavailable'
    session.audit_path.rmdir()
    session.audit_path.write_bytes(saved)
    assert session.get_game_status() == started
    assert session.close_game()['status']['state'] == 'idle'


@pytest.mark.anyio
@pytest.mark.parametrize('tool,arguments', [('buy_unit', {'shop_slot': 0}), ('end_turn', {})])
async def test_invalid_output_rolls_back_before_sdk_error(tmp_path, monkeypatch, tool, arguments):
    import pickle
    session = started_session(tmp_path)
    session.game.player_manager.player_states['player_0'].gold = 100
    async with memory_client(session) as sdk:
        status = (await sdk.call_tool('get_decision')).structuredContent
        committed = session.game
        graph = pickle.dumps(committed)
        native_log = (session.native_dir / 'log.txt').read_bytes()
        accepted_audit = session.audit_path.read_bytes()
        method = getattr(GameSession, tool)
        def invalid(current, *args, **kwargs):
            return {**method(current, *args, **kwargs), 'unexpected': True}
        with monkeypatch.context() as patch:
            patch.setattr(GameSession, tool, invalid)
            result = await sdk.call_tool(tool, arguments)
        assert result.isError and result.structuredContent['code'] == 'internal_error'
        assert result.structuredContent['message'] == 'Tool output does not match its schema.'
        assert session.game is committed and pickle.dumps(session.game) == graph
        assert (session.native_dir / 'log.txt').read_bytes() == native_log
        audit = session.audit_path.read_bytes()
        added = [json.loads(line) for line in audit[len(accepted_audit):].splitlines()]
        assert audit.startswith(accepted_audit) and len(added) == 1 and added[0]['event'] == 'tool_error'
        assert added[0]['result'] == result.structuredContent
        assert (await sdk.call_tool('get_decision')).structuredContent == status
        retry = await sdk.call_tool(tool, arguments)
        assert not retry.isError
        current = retry.structuredContent
        if tool == 'end_turn':
            assert current['start_turn'] is True and 'round 2' in current['text'].splitlines()
            assert current['text'].startswith('action succeeded\n')
        else:
            assert current['text'].startswith('action succeeded') and current['start_turn'] is False
            assert session.game.player_manager.player_states['player_0'].shop_champions[0] is None


@pytest.mark.parametrize('operation', ['start', 'close'])
def test_native_lifecycle_output_validation_rollback(tmp_path, operation):
    session = GameSession(tmp_path / 'audit.jsonl', tmp_path / 'native')
    if operation == 'close':
        session.start_game(0)
    initial = session.get_game_status()
    committed = session.game
    with pytest.raises(SessionError) as error:
        with session.lifecycle_transaction():
            if operation == 'start':
                result = session.start_game(0)
            else:
                result = session.close_game()['status']
            jsonschema.validate({**result, 'unexpected': True}, STATUS_SCHEMA)
    assert error.value.code == 'internal_error'
    assert 'Additional properties' in error.value.details['error']
    assert session.game is committed and session.get_game_status() == initial
    if operation == 'start':
        assert session.start_game(0)['state'] == 'running'
    else:
        assert session.close_game()['status']['state'] == 'idle'


def test_protocol_stdout_is_json_and_malformed_envelopes_are_native_errors(tmp_path):
    import select
    import subprocess
    environment = dict(os.environ, TFT_MCP_SEED='0', TFT_MCP_AUDIT_PATH=str(tmp_path / 'audit.jsonl'),
                       TFT_MCP_NATIVE_LOG_DIR=str(tmp_path / 'native'), TFT_MCP_STREAM_LOG='off')
    environment.pop('APPIMAGE', None)
    command = os.environ.get('TFT_MCP_TEST_COMMAND')
    if command:
        environment.pop('PYTHONPATH', None)
        arguments = [command]
    else:
        environment['PYTHONPATH'] = str(Path(__file__).parents[1] / 'src')
        arguments = [sys.executable, '-m', 'tft_mcp']
    with (tmp_path / 'stderr.log').open('w') as diagnostics:
        process = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=diagnostics, env=environment, cwd=tmp_path, text=True)
        def request(payload):
            process.stdin.write(json.dumps(payload) + '\n')
            process.stdin.flush()
            assert select.select([process.stdout], [], [], 15)[0], 'No protocol response'
            return json.loads(process.stdout.readline())
        try:
            initialized = request({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2024-11-05', 'capabilities': {},
                'clientInfo': {'name': 'stdout-acceptance', 'version': '1'}}})
            assert initialized['id'] == 1
            process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
            process.stdin.flush()
            malformed = request({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {
                'name': 'get_decision', 'arguments': []}})
            assert malformed['error']['code'] == -32602
            decision = request({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
                'name': 'get_decision', 'arguments': {}}})
            content = decision['result']['structuredContent']
            assert content['start_turn'] is True and content['text'].startswith('round 1\n')
        finally:
            process.stdin.close()
            process.wait(timeout=15)
            process.stdout.close()
        assert process.returncode == 0
    records = [json.loads(line) for line in (tmp_path / 'audit.jsonl').read_text().splitlines()]
    assert records[-1]['event'] == 'game_closed'
