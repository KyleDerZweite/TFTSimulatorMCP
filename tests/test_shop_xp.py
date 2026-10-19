"""Refresh and experience commands follow the simulator mask."""
import pytest

from support import capture_committed_state, session_fixture, assert_committed_state_unchanged
from tft_mcp.session import SessionError
from Simulator.encoding.token.action import ActionToken


def test_refresh_and_experience_return_a_mask(tmp_path):
    session = session_fixture(tmp_path)
    player = session.game.player_manager.player_states['player_0']
    player.gold = 100
    session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
    refreshed = session.refresh_shop()
    assert refreshed['text'].startswith('action succeeded') and refreshed['mask']
    assert session.game.actions_taken['player_0'] == 1
    gained = session.buy_xp()
    assert gained['start_turn'] is False
    assert session.game.actions_taken['player_0'] == 2


def test_refresh_without_gold_is_masked(tmp_path):
    session = session_fixture(tmp_path)
    player = session.game.player_manager.player_states['player_0']
    player.gold = 0
    session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
    before = capture_committed_state(session)
    with pytest.raises(SessionError) as error:
        session.refresh_shop()
    assert error.value.code == 'masked'
    assert_committed_state_unchanged(session, before)
