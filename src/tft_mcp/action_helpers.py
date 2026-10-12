"""Canonical locations and native purchase, sale and merge validation."""

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


def location_unit(player, location):
    return (player.board[location["x"]][location["y"]] if location["kind"] == "board"
            else player.bench[location["slot"]])


def location_flat(location):
    return location["x"] * 4 + location["y"] if location["kind"] == "board" else 28 + location["slot"]


def board_locations(board):
    return [({"kind": "board", "x": x, "y": y}, unit)
            for x, column in enumerate(board) for y, unit in enumerate(column)]


def bench_locations(bench):
    return [({"kind": "bench", "slot": slot}, unit) for slot, unit in enumerate(bench)]


def owned_locations(player):
    return board_locations(player.board) + bench_locations(player.bench)


def azir_guard_coordinates(player, unit, error_message):
    coords = unit.sandguard_overlord_coordinates
    if (not unit.overlord or len(coords) != 2 or len({tuple(c) for c in coords}) != 2
            or any(type(c) is not list or len(c) != 2 or any(type(v) is not int for v in c)
                   or not 0 <= c[0] <= 6 or not 0 <= c[1] <= 3
                   or player.board[c[0]][c[1]] is None or player.board[c[0]][c[1]].name != "sandguard" for c in coords)):
        raise SessionError("internal_error", error_message)
    return coords


def shop_offer_name(champion_id, chosen):
    return f"{champion_id}_{chosen}_c" if chosen else champion_id


def native_price(cost, stars):
    from Simulator.game.pool_stats import cost_star_values

    return cost_star_values[cost - 1][stars - 1]


def action_price(unit):
    from Simulator.battle.stats import BASE_CHAMPION_LIST, COST
    if unit.target_dummy or unit.name == "sandguard":
        raise SessionError("unsupported_action", "Dummy units cannot be purchased or sold.", {"reason": "dummy_unit"})
    if unit.name not in BASE_CHAMPION_LIST:
        raise SessionError("internal_error", "Unit is absent from the installed champion catalog.", {"champion": unit.name})
    if type(unit.cost) is not int or type(unit.stars) is not int or not 1 <= unit.cost <= 5 or not 1 <= unit.stars <= 3:
        raise SessionError("unsupported_action", "Unit has no supported native action price.", {"reason": "price_range", "champion": unit.name})
    if unit.cost != COST[unit.name]:
        raise SessionError("internal_error", "Unit cost differs from the installed champion definition.", {"champion": unit.name})
    return native_price(unit.cost, unit.stars)


def catalog_entry(player, name, stars):
    entries = [entry for entry in player.triple_catalog if entry["name"] == name and entry["level"] == stars]
    if len(entries) > 1 or (entries and (type(entries[0]["num"]) is not int or not 1 <= entries[0]["num"] <= 2)):
        raise SessionError("internal_error", "Native triple catalog is inconsistent.", {"champion": name, "stars": stars})
    return entries[0] if entries else None


def real_items(unit):
    return ["thieves_gloves"] if unit.items and unit.items[0] == "thieves_gloves" else list(unit.items)


def merge_inventory(player, incoming, trace=None):
    """Check native bench returns before board returns across reachable merges."""
    inventory = list(player.item_bench)
    stars, chosen = incoming.stars, incoming.chosen
    visited = set()
    while True:
        if stars in visited or not 1 <= stars <= 3:
            raise SessionError("unsupported_action", "Native promotion is outside supported action stars.",
                               {"reason": "promotion_range", "champion": incoming.name})
        visited.add(stars)
        entry = catalog_entry(player, incoming.name, stars)
        bench = [unit for unit in player.bench if unit and unit.name == incoming.name and unit.stars == stars]
        board = [unit for column in player.board for unit in column if unit and unit.name == incoming.name and unit.stars == stars]
        contributors = bench + board
        if len(contributors) != (entry["num"] if entry else 0):
            raise SessionError("internal_error", "Native catalog does not match owned contributors.",
                               {"champion": incoming.name, "stars": stars})
        if entry is None or entry["num"] != 2:
            if trace is not None:
                trace["stars"], trace["chosen"] = stars, chosen
            return inventory
        if trace is not None:
            trace["contributors"].extend(contributors)
            trace["board_phases"].append(bool(board))
        for unit in contributors:
            equipment = real_items(unit)
            available = inventory.count(None)
            if len(equipment) > available:
                if unit in board:
                    raise SessionError("capacity_exceeded", "Merge board equipment cannot fit in inventory.",
                                       {"resource": "items", "required": len(equipment), "available": available,
                                        "location": {"kind": "board", "x": unit.x, "y": unit.y}})
                continue
            for item in equipment:
                inventory[inventory.index(None)] = item
        promoted = 3 if chosen else stars + 1
        chosen = False
        for unit in contributors:
            if unit.chosen:
                chosen = unit.chosen
        if promoted <= stars:
            raise SessionError("unsupported_action", "Native promotion does not progress.", {"reason": "promotion_cycle"})
        stars = promoted


def copy_weights(snapshot):
    weights = {}
    for _, unit in snapshot["units"]:
        if unit and not unit["target_dummy"] and unit["champion"] != "sandguard":
            weights[unit["champion"]] = weights.get(unit["champion"], 0) + 3 ** (unit["stars"] - 1)
    return weights


def check_copy_change(before, after, unit, direction):
    expected = copy_weights(before)
    name = unit["champion"]
    expected[name] = expected.get(name, 0) + direction * 3 ** (unit["stars"] - 1)
    expected = {name: count for name, count in expected.items() if count}
    if copy_weights(after) != expected:
        raise SessionError("internal_error", "Native action did not preserve expected owned copies.", {"champion": name})
