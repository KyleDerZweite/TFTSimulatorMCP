"""Native purchase/sale contracts and postconditions, without session ownership."""

from copy import deepcopy

from tft_mcp.action_helpers import (
    action_price, catalog_entry, check_copy_change, location_flat, location_unit,
    merge_inventory, owned_locations, real_items, shop_offer_name,
)
from tft_mcp.errors import SessionError
from tft_mcp.state import freeze_unit


def purchase_contract(player, slot):
    unit = player.shop_champions[slot]
    if unit is None:
        if player.shop[slot] is not None:
            raise SessionError("internal_error", "Stored shop offer is inconsistent.", {"shop_slot": slot})
        raise SessionError("empty_slot", "Select an occupied shop slot.", {"shop_slot": slot})
    purchased = freeze_unit(unit)
    if player.shop[slot] != shop_offer_name(unit.name, unit.chosen):
        raise SessionError("internal_error", "Stored shop offer is inconsistent.", {"shop_slot": slot})
    price = action_price(unit)
    if player.gold < price:
        raise SessionError("insufficient_gold", "The offer costs more gold than is available.",
                           {"shop_slot": slot, "required": price, "available": player.gold, "resource": "gold"})
    trace = {"contributors": [], "board_phases": []}
    expected_items = merge_inventory(player, unit, trace)
    if any(trace["board_phases"][:-1]):
        raise SessionError("unsupported_action", "Native cascading purchases cannot safely reposition an early board contributor.",
                           {"reason": "early_board_merge_cascade", "shop_slot": slot})
    if all(player.bench):
        entry = catalog_entry(player, unit.name, unit.stars)
        if entry is None or entry["num"] != 2:
            raise SessionError("capacity_exceeded", "The bench is full and this offer cannot merge.",
                               {"shop_slot": slot, "resource": "bench", "required": 1, "available": 0})
    return {"action": [3, slot, 0], "shop_slot": slot, "purchased": purchased,
            "price": price, "expected_items": expected_items}


def check_purchase(player, contract, before, after):
    slot, price = contract["shop_slot"], contract["price"]
    if (player.shop[slot] is not None or player.shop_champions[slot] is not None
            or player.gold != before["gold"] - price or after["items"] != contract["expected_items"]):
        raise SessionError("internal_error", "Purchase postconditions failed.", {"shop_slot": slot})
    check_copy_change(before, after, contract["purchased"], 1)
    return {"shop_slot": slot, "purchased": contract["purchased"], "gold_spent": price}


def sale_contract(player, location):
    unit = location_unit(player, location)
    if unit is None:
        raise SessionError("empty_slot", "Select an occupied owned location.", {"location": location})
    sold = freeze_unit(unit)
    price = action_price(unit)
    entry = catalog_entry(player, unit.name, unit.stars)
    count = sum(1 for _, owned in owned_locations(player)
                if owned and owned.name == unit.name and owned.stars == unit.stars)
    if entry is None or entry["num"] != count:
        raise SessionError("internal_error", "Owned units do not match the native catalog.", {"location": location})
    equipment = real_items(unit)
    available = player.item_bench.count(None)
    if location["kind"] == "board" and len(equipment) > available:
        raise SessionError("capacity_exceeded", "Board equipment cannot fit in inventory.",
                           {"location": location, "resource": "items", "required": len(equipment), "available": available})
    returned = equipment if len(equipment) <= available else []
    dropped = [] if returned == equipment else equipment
    return {"action": [4, location_flat(location), 0], "location": deepcopy(location), "sold": sold,
            "price": price, "returned_items": returned, "dropped_items": dropped}


def check_sale(player, contract, before, after):
    location, sold, price = contract["location"], contract["sold"], contract["price"]
    expected_items = list(before["items"])
    for item in contract["returned_items"]:
        expected_items[expected_items.index(None)] = item
    if (location_unit(player, location) is not None or player.gold != before["gold"] + price
            or after["items"] != expected_items):
        raise SessionError("internal_error", "Sale postconditions failed.", {"location": location})
    check_copy_change(before, after, sold, -1)
    if location["kind"] == "board" and sold["champion"] == "azir":
        if any(player.board[x][y] is not None for x, y in sold["sandguard_overlord_coordinates"]):
            raise SessionError("internal_error", "Azir sandguard removal failed.", {"location": location})
    return {"location": location, "sold": sold, "gold_gained": price,
            "returned_items": contract["returned_items"], "dropped_items": contract["dropped_items"]}
