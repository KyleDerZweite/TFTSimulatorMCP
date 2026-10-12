import pytest

from support import client, INSPECTION_TOOLS


@pytest.mark.anyio
async def test_board_discovery_and_seeded_coordinates(tmp_path):
    async with client(tmp_path) as sdk:
        tools = {tool.name: tool for tool in (await sdk.list_tools()).tools}
        assert tools['get_board'].inputSchema['additionalProperties'] is False
        decision = (await sdk.call_tool('get_decision')).structuredContent
        result = await sdk.call_tool('get_board', {})
        assert not result.isError
        board = result.structuredContent
        assert set(board) == {'game_id', 'player_id', 'round', 'slots', 'num_units_in_play', 'max_units'}
        assert board['game_id'] == decision['status']['game_id']
        assert board['player_id'] == 'player_0' and board['round'] == 1
        assert len(board['slots']) == 28
        assert board['slots'][0]['location'] == {'kind': 'board', 'x': 0, 'y': 0}
        assert board['slots'][27]['location'] == {'kind': 'board', 'x': 6, 'y': 3}
        assert all(slot['unit'] is None for slot in board['slots'])
        assert decision['board'] == [] and decision['bench'] == [] and decision['items'] == []


@pytest.mark.anyio
async def test_decision_uses_native_offers_economy_and_stored_traits(tmp_path):
    from tft_mcp.session import GameSession
    from Simulator.game.pool_stats import cost_star_values
    reference = GameSession(tmp_path / 'reference.jsonl', tmp_path / 'reference-native')
    reference.start_game(0)
    player = reference.game.player_manager.player_states['player_0']
    async with client(tmp_path) as sdk:
        result = await sdk.call_tool('get_decision')
        assert not result.isError
        decision = result.structuredContent
        assert len(decision['shop']) == 5
        actual = [(slot['unit']['champion'], slot['unit']['stars'], slot['purchase_cost'])
                  if slot['unit'] else None for slot in decision['shop']]
        expected = [(unit.name, unit.stars, cost_star_values[unit.cost - 1][unit.stars - 1])
                    if unit else None for unit in player.shop_champions]
        assert actual == expected
        assert [slot['slot'] for slot in decision['shop']] == list(range(5))
        for key in ('gold', 'health', 'level', 'exp'):
            assert decision['economy'][key] == getattr(player, key)
        assert decision['status']['planning_budget'] == {'capacity': 14, 'remaining': 14}
        assert decision['traits'] == [
            {'trait_id': key, 'count': player.team_composition[key], 'tier': player.team_tiers[key]}
            for key in sorted(player.team_composition) if player.team_composition[key]]
        after = (await sdk.call_tool('end_turn')).structuredContent
        assert after['status']['round'] == after['snapshot_round'] == 2
    reference.close_game()


@pytest.mark.anyio
async def test_inspection_errors_are_strict_and_restart_clears_state(tmp_path):
    async with client(tmp_path) as sdk:
        tools = {tool.name: tool for tool in (await sdk.list_tools()).tools}
        assert set(INSPECTION_TOOLS) <= tools.keys()
        initial = (await sdk.call_tool('get_decision')).structuredContent
        for name in INSPECTION_TOOLS:
            assert tools[name].inputSchema['additionalProperties'] is False
            assert tools[name].outputSchema['additionalProperties'] is False
            result = await sdk.call_tool(name, {'extra': True})
            assert result.isError and result.structuredContent['code'] == 'invalid_input'
        for value in (None, True, 1, [], {}):
            result = await sdk.call_tool('get_board', {'player_id': value})
            assert result.isError and result.structuredContent['code'] == 'invalid_input'
        for value in ('unknown', ''):
            result = await sdk.call_tool('get_board', {'player_id': value})
            assert result.isError and result.structuredContent['code'] == 'invalid_player'
            assert result.structuredContent['details']['supported_ids'] == [f'player_{i}' for i in range(8)]
        assert (await sdk.call_tool('get_decision')).structuredContent == initial
        await sdk.call_tool('end_turn')
    async with client(tmp_path) as sdk:
        fresh = (await sdk.call_tool('get_decision')).structuredContent
        assert fresh['status']['game_id'] != initial['status']['game_id']
        assert fresh['status']['round'] == 1
        assert fresh['status']['planning_budget'] == {'capacity': 14, 'remaining': 14}
        assert fresh['bench'] == fresh['board'] == fresh['items'] == []


@pytest.mark.anyio
async def test_terminal_inspection_retains_elimination_round(tmp_path):
    async with client(tmp_path) as sdk:
        for _ in range(30):
            decision = (await sdk.call_tool('end_turn')).structuredContent
            if decision['status']['state'] == 'terminal':
                break
        assert decision['status']['state'] == 'terminal'
        own = {}
        for name in INSPECTION_TOOLS:
            result = await sdk.call_tool(name)
            assert not result.isError, result.structuredContent
            own[name] = result.structuredContent
            assert (await sdk.call_tool(name)).structuredContent == own[name]
        assert own['get_decision'] == decision
        assert decision['economy']['health'] <= 0
        assert decision['status']['planning_budget'] is None
        assert own['get_board']['round'] == decision['snapshot_round'] < decision['status']['round']


@pytest.mark.anyio
async def test_failed_inspection_audit_preserves_game_and_allows_retry(tmp_path):
    async with client(tmp_path) as sdk:
        decision = (await sdk.call_tool('get_decision')).structuredContent
        board = (await sdk.call_tool('get_board')).structuredContent
        audit = tmp_path / 'audit.jsonl'
        saved = audit.read_bytes()
        audit.unlink()
        audit.mkdir()
        failed = await sdk.call_tool('get_board')
        assert failed.isError and failed.structuredContent['code'] == 'log_unavailable'
        audit.rmdir()
        audit.write_bytes(saved)
        assert (await sdk.call_tool('get_board')).structuredContent == board
        assert (await sdk.call_tool('get_decision')).structuredContent == decision
