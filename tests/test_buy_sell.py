"""Shop and sale commands follow the simulator mask."""
import pytest

from support import capture_committed_state, session_fixture, assert_committed_state_unchanged
from tft_mcp.session import SessionError
from Simulator.encoding.token.action import ActionToken


def _refresh_mask(session):
    player = session.game.player_manager.player_states['player_0']
    session.game.player_manager.action_handlers['player_0'] = ActionToken(player)
    return player


def test_masked_sale_leaves_the_game_unchanged(tmp_path):
    session = session_fixture(tmp_path)
    before = capture_committed_state(session)
    with pytest.raises(SessionError) as error:
        session.sell_unit(location={'kind': 'bench', 'slot': 8})
    assert error.value.code == 'masked'
    assert error.value.details['action'] == {'action_type': 4, 'x1': 36, 'x2': 0}
    assert_committed_state_unchanged(session, before)


def test_legal_buy_returns_the_next_mask_without_text(tmp_path):
    session = session_fixture(tmp_path)
    _refresh_mask(session)
    result = session.buy_unit(shop_slot=0)
    player = session.game.player_manager.player_states['player_0']
    assert result['start_turn'] is False and result['text'].startswith('action succeeded')
    assert result['mask']
    assert player.shop_champions[0] is None
    assert session.get_decision() == result
