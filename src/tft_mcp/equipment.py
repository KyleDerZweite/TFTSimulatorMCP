"""JSON shape for an equip. Game legality is the simulator mask."""

from tft_mcp.action_helpers import validate_location
from tft_mcp.errors import SessionError


def validate_equip_arguments(arguments):
    if set(arguments) != {"item_slot", "target"} or type(arguments.get("item_slot")) is not int or not 0 <= arguments["item_slot"] <= 9:
        raise SessionError("invalid_input", "equip_item requires exactly item_slot 0..9 and target.")
    validate_location(arguments["target"], "target")
