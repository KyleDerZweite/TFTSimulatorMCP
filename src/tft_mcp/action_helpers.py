"""JSON shapes for shop and sale arguments. Game legality is the simulator mask."""

from tft_mcp.errors import SessionError


def validate_buy_arguments(arguments):
    if set(arguments) != {"shop_slot"} or type(arguments.get("shop_slot")) is not int or not 0 <= arguments["shop_slot"] <= 4:
        raise SessionError("invalid_input", "buy_unit requires only shop_slot, an integer from 0 through 4.", {"field": "shop_slot"})


def validate_sell_arguments(arguments):
    location = arguments.get("location")
    if set(arguments) != {"location"} or type(location) is not dict:
        raise SessionError("invalid_input", "sell_unit requires only a board or bench location.", {"field": "location"})
    validate_location(location, "location")


def validate_location(location, field):
    if type(location) is not dict:
        raise SessionError("invalid_input", 'Use a JSON object: {"kind":"board","x":3,"y":0} or {"kind":"bench","slot":0}.', {"field": field})
    kind = location.get("kind")
    fields = {"kind", "x", "y"} if kind == "board" else {"kind", "slot"} if kind == "bench" else set()
    bounds = {"x": 6, "y": 3} if kind == "board" else {"slot": 8}
    if not fields or set(location) != fields or any(type(location.get(key)) is not int or not 0 <= location[key] <= bound for key, bound in bounds.items()):
        raise SessionError("invalid_input", "Use exact board x=0..6,y=0..3 or bench slot=0..8 coordinates.", {"field": field})
