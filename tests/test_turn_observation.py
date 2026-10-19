"""Turn-resolution observations from end_turn and the final planning action."""

import pytest

from support import observation_round, started_session


def test_end_turn_returns_the_changed_position(tmp_path):
    session = started_session(tmp_path)
    session.get_decision()
    before = visible_position(session)
    result = session.end_turn()
    assert_turn_resolution(session, before, result)


@pytest.mark.parametrize('tool', [
    'end_turn', 'refresh_shop', 'buy_xp', 'buy_unit', 'sell_unit', 'move_unit', 'equip_item',
])
def test_last_planning_action_returns_the_turn_resolution(tmp_path, tool):
    session = started_session(tmp_path)
    if tool == 'equip_item':
        from Simulator.encoding.token.action import ActionToken
        player = session.game.player_manager.player_states['player_0']
        player.item_bench[0] = 'bf_sword'
        session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
    session.get_decision()
    for _ in range(14):
        passed = session._controlled([0, 0, 0], 'pass')
        assert passed['start_turn'] is False
    assert session.get_game_status()['planning_budget'] == {'capacity': 15, 'remaining': 1}
    before = visible_position(session)
    result = perform(session, tool)
    assert_turn_resolution(session, before, result)


def assert_turn_resolution(session, before, result):
    assert result['start_turn'] is True and result['terminal'] is False
    assert observation_round(result['text']) == 2
    assert result['text'] == expected_resolution(before, visible_position(session))
    assert session.get_decision()['text'] == result['text']
    assert session.game.llm_observe('player_0')['text'] == result['text']


def perform(session, tool):
    if tool == 'end_turn':
        return session.end_turn()
    if tool == 'refresh_shop':
        return session.refresh_shop()
    if tool == 'buy_xp':
        return session.buy_xp()
    command = legal_command(session, {'buy_unit': 3, 'sell_unit': 4, 'move_unit': 5, 'equip_item': 6}[tool])
    if tool == 'buy_unit':
        return session.buy_unit(shop_slot=command[1])
    if tool == 'sell_unit':
        return session.sell_unit(location=location_from_flat(command[1]))
    if tool == 'move_unit':
        return session.move_unit(source=location_from_flat(command[1]), target=location_from_flat(command[2]))
    return session.equip_item(target=location_from_flat(command[1]), item_slot=command[2])


def legal_command(session, action_type):
    from Simulator.encoding.llm_observation import legal_commands
    commands = legal_commands(session.game.player_manager.action_handlers['player_0'])
    return next(command for command in commands if command[0] == action_type)


def location_from_flat(index):
    if index >= 28:
        return {'kind': 'bench', 'slot': index - 28}
    return {'kind': 'board', 'x': index // 4, 'y': index % 4}


def visible_position(session):
    from Simulator.encoding.llm_observation import _ALL, _opponent_block, _section
    env = session.game
    player = env.player_manager.player_states['player_0']
    own = {key: _section(env, player, 'player_0', key) for key in _ALL}
    opponents = [(seat, _opponent_block(env, seat)) for seat in env.possible_agents if seat != 'player_0']
    return own, opponents


def expected_resolution(before, after):
    from Simulator.encoding.llm_observation import _ALL
    own_before, opponents_before = before
    own_after, opponents_after = after
    parts = ['action succeeded']
    for key in _ALL:
        if own_after[key] != own_before.get(key):
            parts.append(own_after[key])
    previous = dict(opponents_before)
    changed = [block for seat, block in opponents_after if previous.get(seat) != block]
    if changed:
        parts.append('opponents\n' + '\n'.join(changed))
    return '\n'.join(parts)
