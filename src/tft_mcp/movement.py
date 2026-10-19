"""JSON shape for a move. Game legality is the simulator mask."""

from tft_mcp.action_helpers import validate_location
from tft_mcp.errors import SessionError


def validate_move_arguments(arguments):
    if set(arguments) != {"source", "target"}:
        raise SessionError("invalid_input", "move_unit requires exactly source and target.")
    for field in ("source", "target"):
        validate_location(arguments[field], field)
