"""Native equipment validation and postconditions, without session ownership."""

from copy import deepcopy
from tft_mcp.errors import SessionError
from tft_mcp.action_helpers import azir_guard_coordinates, check_copy_change, location_flat, location_unit, merge_inventory, owned_locations, validate_location
from tft_mcp.state import freeze_unit


def validate_equip_arguments(arguments):
    if set(arguments) != {"item_slot", "target"} or type(arguments.get("item_slot")) is not int or not 0 <= arguments["item_slot"] <= 9:
        raise SessionError("invalid_input", "equip_item requires exactly item_slot 0..9 and target.")
    validate_location(arguments["target"], "target")


def equipment_contract(player, slot, target):
    from Simulator.battle import item_stats
    unit, item = location_unit(player, target), player.item_bench[slot]
    if item is None:
        raise SessionError("empty_slot", "Select an occupied inventory slot.", {"item_slot": slot})
    if unit is None:
        raise SessionError("empty_slot", "Select an occupied owned target.", {"target": target})
    from Simulator.battle.stats import BASE_CHAMPION_LIST, COST
    if unit.target_dummy or unit.name == "sandguard":
        raise SessionError("unsupported_action", "Dummy units cannot receive equipment.", {"reason": "dummy_unit"})
    if unit.name not in BASE_CHAMPION_LIST or unit.cost != COST[unit.name] or type(unit.stars) is not int or not 1 <= unit.stars <= 4:
        raise SessionError("internal_error", "Equipment target differs from installed champion definitions.")
    if item not in item_stats.items or any(i not in item_stats.items for i in unit.items):
        raise SessionError("internal_error", "Unknown installed item identifier.")
    from collections import Counter
    from Simulator.battle.origin_class_stats import origin_class
    check_equipment_catalog(player)
    equipment, origin = list(unit.items), list(unit.origin)
    mode = item
    categories = []
    incoming = None
    merged_items = None
    trace = {"contributors": [], "board_phases": []}
    if item == "champion_duplicator":
        if not COST[unit.name]:
            raise SessionError("unsupported_action", "Zero-cost units cannot be duplicated.", {"reason": "zero_cost"})
        if all(player.bench):
            raise SessionError("capacity_exceeded", "Duplicator requires a genuine bench vacancy.",
                               {"resource": "bench", "required": 1, "available": 0})
        from types import SimpleNamespace
        # Constructor metadata only. Native construction runs once inside controlled_action.
        incoming = SimpleNamespace(name=unit.name, cost=COST[unit.name], stars=2 if unit.chosen else 1,
                                   chosen=unit.chosen, kayn_form=unit.kayn_form, target_dummy=False,
                                   items=[], origin=list(origin_class[unit.name]), sandguard_overlord_coordinates=[])
        merged_items = merge_inventory(player, incoming, trace)
        if any(trace["board_phases"][:-1]):
            raise SessionError("unsupported_action", "Native cascading duplication cannot safely reposition an early board contributor.",
                               {"reason": "early_board_duplicate_cascade"})
        trace["guards"] = [tuple(c) for u in trace["contributors"] if u.name == "azir"
                           for c in getattr(u, "sandguard_overlord_coordinates", [])]
        expected = equipment
    elif item in {"kayn_rhast", "kayn_shadowassassin"}:
        if unit.name != "kayn":
            raise SessionError("incompatible_item", "Form tokens require Kayn.")
        if target["kind"] != "board":
            raise SessionError("unsupported_action", "Native bench Kayn form writes the wrong field.", {"reason": "bench_kayn_form"})
        expected = equipment
    elif item in {"magnetic_remover", "reforger"}:
        if "thieves_gloves" in equipment:
            raise SessionError("unsupported_action", "Native glove removal or reforge leaves unsafe tracking.", {"reason": "glove_tracking"})
        if not equipment:
            raise SessionError("incompatible_item", "The consumable requires equipped items.")
        grants = [trait for equipped in equipment for trait, name in item_stats.trait_items.items() if name == equipped]
        if item == "reforger" and grants:
            raise SessionError("unsupported_action", "Native trait reforge retains the granted origin.", {"reason": "trait_reforge"})
        intrinsic = origin_class[unit.name]
        if grants and (origin[:len(intrinsic)] != intrinsic or Counter(origin[len(intrinsic):]) != Counter(grants)):
            raise SessionError("unsupported_action", "Trait removal would delete an unsafe origin suffix.", {"reason": "trait_origin_suffix"})
        available = player.item_bench.count(None)
        if len(equipment) > available:
            raise SessionError("capacity_exceeded", "Consumable output requires inventory vacancies before consumption.",
                               {"resource": "items", "required": len(equipment), "available": available})
        if item == "reforger":
            for equipped in equipment:
                if equipped == "spatula":
                    categories.append(["spatula"])
                elif equipped in item_stats.starting_items:
                    categories.append([i for i in item_stats.starting_items[:8] if i != equipped])
                elif equipped in item_stats.thieves_gloves_items:
                    categories.append([i for i in item_stats.thieves_gloves_items if i != equipped])
                else:
                    raise SessionError("internal_error", "Equipped item has no safe native reforge category.")
        expected = []
        if grants:
            origin = list(intrinsic)
    elif item == "thieves_gloves":
        if equipment:
            raise SessionError("incompatible_item", "Direct thieves gloves requires empty equipment.")
        expected = [item]
    else:
        mode = "ordinary"
        if "thieves_gloves" in equipment:
            raise SessionError("unsupported_action", "Existing thieves gloves cannot receive ordinary equipment.", {"reason": "glove_equipment"})
        combining = bool(equipment and equipment[-1] in item_stats.basic_items and item in item_stats.basic_items)
        if len(equipment) >= 3 and not (len(equipment) == 3 and combining):
            raise SessionError("capacity_exceeded", "The unit has no equipment capacity.",
                               {"resource": "equipment", "required": 1, "available": 0})
        expected = list(equipment)
        result = item
        if combining:
            result = next((name for name, parts in item_stats.item_builds.items()
                           if sorted(parts) == sorted([equipment[-1], item])), None)
            if result is None:
                raise SessionError("incompatible_item", "No installed component recipe exists.")
            if result == "thieves_gloves":
                raise SessionError("unsupported_action", "Native component gloves combination has stale num_items.", {"reason": "glove_combination"})
            expected[-1] = result
        elif expected and expected[-1] in item_stats.basic_items and item not in item_stats.basic_items:
            expected.insert(len(expected) - 1, item)
        else:
            expected.append(item)
        grant = next((trait for trait, name in item_stats.trait_items.items() if name == result), None)
        if grant:
            if grant in origin:
                raise SessionError("incompatible_item", "The target already has the granted trait.")
            origin.append(grant)
    return {"item": item, "slot": slot, "target": deepcopy(target), "equipment": expected, "mode": mode, "categories": categories,
            "incoming": freeze_unit(incoming), "merged_items": merged_items, "trace": trace,
            "owned": owned_locations(player), "chosen": player.chosen,
            "original_equipment": equipment, "origin": origin, "origin_changed": origin != unit.origin, "shop": deepcopy(player.shop),
            "offers": [freeze_unit(u) for u in player.shop_champions], "catalog": deepcopy(player.triple_catalog),
            "capacity": player.max_units, "count": player.num_units_in_play,
            "gloves": deepcopy(player.thieves_gloves_loc), "form": player.kayn_form,
            "traits": deepcopy((player.team_composition, player.team_tiers))}


def check_equipment(player, contract, before, after):
    from Simulator.battle import item_stats
    expected = deepcopy(before)
    slot, target, mode = contract["slot"], contract["target"], contract["mode"]
    expected["items"][slot] = None
    record = expected["units"][location_flat(target)][1]
    record["items"] = contract["equipment"]
    record["traits"] = contract["origin"]
    gloves = contract["gloves"]
    catalog, count, form = contract["catalog"], contract["count"], contract["form"]
    if mode == "champion_duplicator":
        check_copy_change(before, after, contract["incoming"], 1)
        check_equipment_catalog(player)
        contributors = contract["trace"]["contributors"]
        removed = {id(u) for u in contributors}
        removed_guards = set(contract["trace"]["guards"])
        survivors = [(loc, u) for loc, u in contract["owned"] if u and id(u) not in removed
                     and not (loc["kind"] == "board" and (loc["x"], loc["y"]) in removed_guards)]
        for loc, u in survivors:
            if location_unit(player, loc) is not u or freeze_unit(u) != before["units"][location_flat(loc)][1]:
                raise SessionError("internal_error", "Duplicator changed a surviving owned unit.")
        new_units = [(loc, u) for loc, u in owned_locations(player) if u and not u.target_dummy
                     and all(u is not old for _, old in survivors)]
        if len(new_units) != 1:
            raise SessionError("internal_error", "Duplicator did not create exactly one native result unit.")
        loc, result = new_units[0]
        result_record = freeze_unit(result)
        result_record["sandguard_overlord_coordinates"] = []
        wanted = dict(contract["incoming"])
        if contributors:
            wanted.update(stars=contract["trace"]["stars"], chosen=contract["trace"]["chosen"], kayn_form=None)
        if result_record != wanted:
            raise SessionError("internal_error", "Duplicator result differs from its native constructor and promotion.")
        allowed_guards = {tuple(c) for c in result.sandguard_overlord_coordinates} if loc["kind"] == "board" and result.name == "azir" else set()
        surviving_flats = {location_flat(loc) for loc, _ in survivors}
        for pos, u in owned_locations(player):
            if u and u.target_dummy and location_flat(pos) not in surviving_flats:
                if pos["kind"] != "board" or (pos["x"], pos["y"]) not in allowed_guards:
                    raise SessionError("internal_error", "Duplicator created an unrelated guard.")
        wanted_chosen = result.chosen or contract["chosen"]
        if player.chosen != wanted_chosen:
            raise SessionError("internal_error", "Duplicator Chosen ownership is inconsistent.")
        expected["units"] = after["units"]
        expected["items"] = list(contract["merged_items"])
        expected["items"][slot] = None
        catalog = player.triple_catalog
        count = sum(u is not None and not u.target_dummy and u.name != "sandguard" for col in player.board for u in col)
        gloves = [[loc["x"], loc["y"]] if loc["kind"] == "board" else [loc["slot"], -1]
                  for loc, u in owned_locations(player) if u and u.items and u.items[0] == "thieves_gloves"]
    elif mode in {"kayn_rhast", "kayn_shadowassassin"}:
        form = contract["item"]
        expected["items"] = [None if i in {"kayn_rhast", "kayn_shadowassassin"} else i for i in before["items"]]
        for loc, unit in expected["units"]:
            if loc["kind"] == "board" and unit and unit["champion"] == "kayn":
                unit["kayn_form"] = form
    elif mode == "thieves_gloves":
        actual = location_unit(player, target).items
        if (len(actual) != 3 or actual[0] != "thieves_gloves" or len(set(actual[1:])) != 2
                or any(i not in item_stats.thieves_gloves_items for i in actual[1:])):
            raise SessionError("internal_error", "Native gloves draw failed.")
        record["items"] = list(actual)
        gloves = gloves + [[target["x"], target["y"]] if target["kind"] == "board" else [target["slot"], -1]]
    elif mode in {"magnetic_remover", "reforger"}:
        inventory = list(before["items"])
        for index, item in enumerate(contract["original_equipment"]):
            vacancy = inventory.index(None)
            replacement = after["items"][vacancy]
            if mode == "reforger":
                if replacement not in contract["categories"][index]:
                    raise SessionError("internal_error", "Native reforge output has an invalid category.")
                item = replacement
            inventory[vacancy] = item
        inventory[slot] = None
        expected["items"] = inventory
    board_changed = before["units"][:28] != after["units"][:28]
    recomputed_traits = contract["origin_changed"] or (mode == "champion_duplicator" and board_changed)
    if recomputed_traits:
        # Native trait assignment updates tiers before inserting the incoming equipment.
        override = (target, contract["original_equipment"]) if mode == "ordinary" else None
        expected_traits = equipment_native_traits(player, override)
    else:
        expected_traits = contract["traits"]
    if (player.team_composition, player.team_tiers) != expected_traits:
        raise SessionError("internal_error", "Native equipment trait postconditions failed.")
    if mode != "champion_duplicator" and player.chosen != contract["chosen"]:
        raise SessionError("internal_error", "Equipment changed unrelated Chosen ownership.")
    if (after != expected or player.shop != contract["shop"]
            or [freeze_unit(u) for u in player.shop_champions] != contract["offers"]
            or player.triple_catalog != catalog or player.max_units != contract["capacity"]
            or player.num_units_in_play != count or sorted(map(tuple, player.thieves_gloves_loc)) != sorted(map(tuple, gloves))
            or player.kayn_form != form):
        raise SessionError("internal_error", "Native equipment postconditions failed.")


def check_equipment_catalog(player):
    from collections import Counter
    units = [(loc, u) for loc, u in owned_locations(player) if u and not u.target_dummy and u.name != "sandguard"]
    counts = Counter((u.name, u.stars) for _, u in units)
    if any(type(e.get("level")) is not int or not 1 <= e["level"] <= 4
           or type(e.get("num")) is not int or not 1 <= e["num"] <= 2 for e in player.triple_catalog):
        raise SessionError("internal_error", "Native triple catalog has impossible levels or counts.")
    entries = {(e["name"], e["level"]): e["num"] for e in player.triple_catalog}
    if len(entries) != len(player.triple_catalog) or entries != counts or any(n > 2 for n in counts.values()):
        raise SessionError("internal_error", "Native triple catalog differs from owned regular units.")
    linked = set()
    for loc, u in units:
        if loc["kind"] == "board" and u.name == "azir":
            coords = azir_guard_coordinates(player, u, "Duplicator requires consistent Azir guard linkage.")
            if any(not player.board[c[0]][c[1]].target_dummy for c in coords):
                raise SessionError("internal_error", "Duplicator requires consistent Azir guard linkage.")
            if linked.intersection(map(tuple, coords)):
                raise SessionError("internal_error", "Duplicator requires distinct Azir guard ownership.")
            linked.update(map(tuple, coords))


def equipment_native_traits(player, equipment_override=None):
    """Read native counts on a detached shallow view without changing caches or module bindings."""
    from copy import copy
    from Simulator.battle.origin_class_stats import tiers
    view = copy(player)
    view.team_composition = dict.fromkeys(player.team_composition, 0)
    if equipment_override is not None:
        location, equipment = equipment_override
        if location["kind"] == "board":
            view.board = [list(column) for column in player.board]
            unit = copy(location_unit(player, location))
            unit.items = list(equipment)
            view.board[location["x"]][location["y"]] = unit
    view.team_origin_class()
    if player.chosen in view.team_composition:
        view.team_composition[player.chosen] += 1
    expected_tiers = {trait: sum(count >= threshold for threshold in tiers[trait])
                      for trait, count in view.team_composition.items()}
    return view.team_composition, expected_tiers
