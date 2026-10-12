"""Native movement validation and postconditions, without session ownership."""

from copy import deepcopy
from tft_mcp.errors import SessionError
from tft_mcp.action_helpers import copy_weights, azir_guard_coordinates, location_flat, location_unit, owned_locations, validate_location
from tft_mcp.state import freeze_unit


def validate_move_arguments(arguments):
    if set(arguments) != {"source", "target"}:
        raise SessionError("invalid_input", "move_unit requires exactly source and target.")
    for field in ("source", "target"):
        validate_location(arguments[field], field)


def movement_contract(player, source, target):
    details = {"source": source, "target": target}
    if source == target or source["kind"] == target["kind"] == "bench":
        raise SessionError("unsupported_action", "Same-location and bench-to-bench movement are unsupported.",
                           {**details, "reason": "no_op" if source == target else "bench_to_bench"})
    unit, displaced = location_unit(player, source), location_unit(player, target)
    cross = source["kind"] != target["kind"]
    board_unit = unit if source["kind"] == "board" else displaced
    if cross and board_unit and (board_unit.target_dummy or board_unit.name == "sandguard"):
        raise SessionError("unsupported_action", "Board dummies cannot leave the board.", {**details, "reason": "dummy_unit"})
    if source["kind"] == "bench" and displaced is None and player.num_units_in_play >= player.max_units:
        raise SessionError("capacity_exceeded", "The board has no regular-unit capacity.",
                           {**details, "resource": "board", "required": 1,
                            "available": max(0, player.max_units - player.num_units_in_play)})
    if source["kind"] == "board" and target["kind"] == "bench" and displaced and any(
            slot is None for slot in player.bench[:target["slot"]]):
        raise SessionError("unsupported_action", "An earlier bench vacancy prevents this directed swap.",
                           {**details, "reason": "earlier_bench_vacancy"})
    locations = owned_locations(player)
    regular_count = sum(owned is not None and not owned.target_dummy and owned.name != "sandguard"
                        for location, owned in locations if location["kind"] == "board")
    if player.num_units_in_play != regular_count:
        raise SessionError("internal_error", "Native regular-unit count is inconsistent.")
    guards = {}
    linked = set()
    for location, owned in locations:
        if owned and owned.name == "azir" and location["kind"] == "board":
            coords = azir_guard_coordinates(player, owned, "Azir guard linkage is inconsistent.")
            if any(tuple(c) in linked or not player.board[c[0]][c[1]].target_dummy for c in coords):
                raise SessionError("internal_error", "Azir guard ownership is inconsistent.")
            linked.update(map(tuple, coords))
            guards[id(owned)] = [(deepcopy(c), player.board[c[0]][c[1]]) for c in coords]
    incoming = unit if source["kind"] == "bench" else displaced if cross else None
    outgoing = board_unit if cross else None
    removed = guards.get(id(outgoing), [])
    if incoming and incoming.name == "azir":
        occupied = sum(owned is not None for column in player.board for owned in column)
        available = 28 - occupied - (1 if board_unit is None else 0) + len(removed)
        if available < 2:
            raise SessionError("capacity_exceeded", "Azir entry requires two free guard cells.",
                               {**details, "resource": "sandguard_cells", "required": 2, "available": available})
    destination = source
    if source["kind"] == "bench" and displaced:
        destination = {"kind": "bench", "slot": next(i for i, owned in enumerate(player.bench) if owned is None or i == source["slot"])}
    count_delta = (1 if source["kind"] == "bench" else -1) if cross and displaced is None else 0
    return {"source": deepcopy(source), "target": deepcopy(target), "unit": unit, "displaced": displaced,
            "destination": destination, "locations": locations, "guards": guards, "removed": removed,
            "incoming": incoming, "outgoing": outgoing, "count": player.num_units_in_play + count_delta,
            "records": [(owned, freeze_unit(owned)) for _, owned in locations if owned],
            "shop": deepcopy(player.shop), "offers": deepcopy([freeze_unit(u) for u in player.shop_champions]),
            "catalog": deepcopy(player.triple_catalog), "capacity": player.max_units,
            "traits": deepcopy((player.team_composition, player.team_tiers)),
            "overlords": [(owned, owned.overlord) for _, owned in locations if owned and owned.name == "azir"]}


def check_movement(player, movement, before, after):
    def failed():
        raise SessionError("internal_error", "Native movement postconditions failed.")
    source, target = movement["source"], movement["target"]
    expected = {location_flat(location): unit for location, unit in movement["locations"]}
    expected[location_flat(source)] = None
    expected[location_flat(target)] = movement["unit"]
    if movement["displaced"]:
        expected[location_flat(movement["destination"])] = movement["displaced"]
    for coord, _ in movement["removed"]:
        expected[coord[0] * 4 + coord[1]] = None
    incoming = movement["incoming"]
    if incoming and incoming.name == "azir":
        coords = incoming.sandguard_overlord_coordinates
        if not incoming.overlord or len(coords) != 2 or len({tuple(c) for c in coords}) != 2:
            failed()
        for coord in coords:
            if (type(coord) is not list or len(coord) != 2 or any(type(v) is not int for v in coord)
                    or not 0 <= coord[0] <= 6 or not 0 <= coord[1] <= 3):
                failed()
            flat = coord[0] * 4 + coord[1]
            guard = player.board[coord[0]][coord[1]]
            if (expected[flat] is not None or guard is None or guard.name != "sandguard" or not guard.target_dummy
                    or any(guard is owned for _, owned in movement["locations"])):
                failed()
            expected[flat] = guard
    for location, actual in owned_locations(player):
        if actual is not expected[location_flat(location)]:
            failed()
    for owned, record in movement["records"]:
        actual = freeze_unit(owned)
        record = dict(record)
        if owned.name == "azir" and (id(owned) in movement["guards"] or owned is incoming):
            actual.pop("sandguard_overlord_coordinates")
            record.pop("sandguard_overlord_coordinates")
        if actual != record:
            failed()
    for azir_id, guards in movement["guards"].items():
        azir = next(owned for owned, _ in movement["records"] if id(owned) == azir_id)
        if azir is movement["outgoing"]:
            if azir.overlord or azir.sandguard_overlord_coordinates != [coord for coord, _ in guards]:
                failed()
        else:
            actual_coords = [tuple(location[key] for key in ("x", "y")) for location, owned in owned_locations(player)
                             if location["kind"] == "board" and any(owned is guard for _, guard in guards)]
            if not azir.overlord or sorted(map(tuple, azir.sandguard_overlord_coordinates)) != sorted(actual_coords):
                failed()
    for owned, overlord in movement["overlords"]:
        expected_overlord = True if owned is incoming else False if owned is movement["outgoing"] else overlord
        if owned.overlord != expected_overlord:
            failed()
    for location in (target, movement["destination"] if movement["displaced"] else None):
        if location is not None:
            owned = location_unit(player, location)
            coords = (location["x"], location["y"]) if location["kind"] == "board" else (location["slot"], -1)
            if (owned.x, owned.y) != coords:
                failed()
    gloves = sorted((location["x"], location["y"]) if location["kind"] == "board" else (location["slot"], -1)
                    for location, owned in owned_locations(player) if owned and owned.items and owned.items[0] == "thieves_gloves")
    if (source["kind"] == target["kind"] == "board"
            and (player.team_composition, player.team_tiers) != movement["traits"]):
        failed()
    if (sorted(map(tuple, player.thieves_gloves_loc)) != gloves or copy_weights(before) != copy_weights(after)
            or before["items"] != after["items"] or before["gold"] != after["gold"]
            or player.num_units_in_play != movement["count"] or player.max_units != movement["capacity"]
            or player.shop != movement["shop"] or [freeze_unit(u) for u in player.shop_champions] != movement["offers"]
            or player.triple_catalog != movement["catalog"]):
        failed()
