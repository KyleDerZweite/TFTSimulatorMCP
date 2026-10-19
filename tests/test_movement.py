"""Movement commands follow the simulator mask."""
import pytest

from support import capture_committed_state, session_fixture, assert_committed_state_unchanged
from tft_mcp.session import SessionError


def test_same_location_move_is_masked(tmp_path):
    session = session_fixture(tmp_path)
    before = capture_committed_state(session)
    location = {'kind': 'board', 'x': 0, 'y': 0}
    with pytest.raises(SessionError) as error:
        session.move_unit(source=location, target=location)
    assert error.value.code == 'masked'
    assert_committed_state_unchanged(session, before)


def test_invalid_move_shape_is_rejected_before_the_simulator(tmp_path):
    session = session_fixture(tmp_path)
    before = capture_committed_state(session)
    with pytest.raises(SessionError) as error:
        session.game  # keep the session open for the following call
        from tft_mcp.movement import validate_move_arguments
        validate_move_arguments({'source': {'kind': 'board', 'x': 0, 'y': 0}})
    assert error.value.code == 'invalid_input'
    assert_committed_state_unchanged(session, before)
