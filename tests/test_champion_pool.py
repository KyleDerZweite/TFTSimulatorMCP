import jsonschema
import pytest

from support import client, started_session


def _clear_armies(session):
    with session.simulator_scope():
        for player in session.game.player_manager.player_states.values():
            player.board = [[None] * 4 for _ in range(7)]
            player.bench = [None] * 9


def test_pool_uses_visible_units_and_leaves_the_pool_unchanged(tmp_path):
    from Simulator.battle.champion import champion
    from Simulator.game import pool_stats

    session = started_session(tmp_path)
    own = session.game.player_manager.player_states['player_0']
    other = session.game.player_manager.player_states['player_1']
    _clear_armies(session)
    with session.simulator_scope():
        own.shop[0] = 'yasuo'
        own.shop_champions[0] = champion('yasuo')
        other.shop[0] = 'yasuo'
        other.shop_champions[0] = champion('yasuo')
        other.bench[0] = champion('yasuo')
    size = pool_stats.COST_1['yasuo']
    pools = {name: dict(getattr(session.game.pool_obj, name))
             for name in ('COST_1', 'COST_2', 'COST_3', 'COST_4', 'COST_5')}
    baseline = session.get_champion_pool('yasuo')
    assert baseline == {
        'game_id': session.game_id, 'round': session.game.game_round.current_round,
        'champion_id': 'yasuo', 'pool_size': size, 'visible_copies': 0, 'remaining': size}
    assert session.get_champion_pool('yasuo') == baseline
    assert {name: dict(getattr(session.game.pool_obj, name))
            for name in pools} == pools

    with session.simulator_scope():
        own.bench[0] = champion('yasuo')
        own.board[0][0] = champion('yasuo', stars=2)
        own.board[1][0] = champion('yasuo', target_dummy=True)
        chosen = champion('yasuo', chosen='exile')
        assert chosen.stars == 2
        other.board[2][1] = chosen
        other.board[3][0] = champion('azir', stars=4)
    held = session.get_champion_pool('yasuo')
    assert held['visible_copies'] == 7
    assert held['remaining'] == size - 7
    azir_size = pool_stats.COST_5['azir']
    azir = session.get_champion_pool('azir')
    assert azir['pool_size'] == azir_size
    assert azir['visible_copies'] == 27
    assert azir['remaining'] == 0

    session.terminal_snapshot = {'bench': [{'champion': 'yasuo', 'stars': 3}]}
    with session.simulator_scope():
        session.game.player_manager.kill_player('player_1')
    after_opponent = session.get_champion_pool('yasuo')
    assert after_opponent['visible_copies'] == 4
    assert after_opponent['remaining'] == size - 4
    with session.simulator_scope():
        session.game.player_manager.kill_player('player_0')
    eliminated = session.get_champion_pool('yasuo')
    assert eliminated['visible_copies'] == 0
    assert eliminated['remaining'] == size
    assert session.terminal_snapshot == {'bench': [{'champion': 'yasuo', 'stars': 3}]}


@pytest.mark.anyio
async def test_pool_tool_is_a_pure_exact_read(tmp_path):
    async with client(tmp_path) as session:
        tools = {tool.name: tool for tool in (await session.list_tools()).tools}
        tool = tools['get_champion_pool']
        assert tool.inputSchema['additionalProperties'] is False
        assert tool.inputSchema['required'] == ['champion_id']
        before = (await session.call_tool('get_decision', {})).structuredContent
        result = await session.call_tool('get_champion_pool', {'champion_id': 'yasuo'})
        assert not result.isError
        data = result.structuredContent
        jsonschema.validate(data, tool.outputSchema)
        assert data['remaining'] == max(0, data['pool_size'] - data['visible_copies'])
        assert (await session.call_tool('get_decision', {})).structuredContent == before
        for arguments in ({}, {'champion_id': None}, {'champion_id': 1},
                          {'champion_id': 'yasuo', 'extra': 1}):
            error = await session.call_tool('get_champion_pool', arguments)
            assert error.isError
            assert error.structuredContent['code'] == 'invalid_input'
        error = await session.call_tool('get_champion_pool', {'champion_id': 'Kayn'})
        assert error.isError
        assert error.structuredContent == {
            'code': 'unknown_champion', 'message': 'Unknown champion: Kayn.',
            'details': {'champion_id': 'Kayn'}}
        assert (await session.call_tool('get_decision', {})).structuredContent == before
