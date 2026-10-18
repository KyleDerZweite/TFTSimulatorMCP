"""Equipment commands follow the simulator mask."""
import pytest

from support import capture_committed_state, session_fixture, assert_committed_state_unchanged
from tft_mcp.session import SessionError


def test_empty_item_equip_is_masked(tmp_path):
    session = session_fixture(tmp_path)
    before = capture_committed_state(session)
    with pytest.raises(SessionError) as error:
        session.equip_item(item_slot=0, target={'kind': 'bench', 'slot': 0})
    assert error.value.code == 'masked'
    assert_committed_state_unchanged(session, before)
