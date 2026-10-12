"""Detached visible state and action receipts for the concrete simulator adapter."""

from copy import deepcopy

from tft_mcp.action_helpers import (
    board_locations, bench_locations, owned_locations, native_price, shop_offer_name,
)
from tft_mcp.errors import SessionError


def action_snapshot(player):
    return {"units": [(location, freeze_unit(unit)) for location, unit in owned_locations(player)],
            "items": list(player.item_bench), "gold": player.gold}


def unit_changes(before, after):
    return [{"location": location, "before": old, "after": new}
            for (location, old), (_, new) in zip(before["units"], after["units"], strict=True) if old != new]


def item_changes(before, after):
    return [{"slot": slot, "before": old, "after": new}
            for slot, (old, new) in enumerate(zip(before["items"], after["items"], strict=True)) if old != new]


def freeze_unit(champion):
    """Copy only visible unit fields, without traversing combat references."""
    if champion is None:
        return None
    return {"champion": champion.name, "stars": champion.stars,
            "items": list(champion.items), "chosen": champion.chosen, "cost": champion.cost,
            "kayn_form": getattr(champion, "kayn_form", None),
            "traits": list(champion.origin), "target_dummy": champion.target_dummy,
            "sandguard_overlord_coordinates": deepcopy(getattr(champion, "sandguard_overlord_coordinates", []))}


def freeze_player(player, round_number):
    """Detached post-combat records for later own-state inspection tools."""
    return deepcopy({
        "board": [[freeze_unit(champion) for champion in column] for column in player.board],
        "bench": [freeze_unit(champion) for champion in player.bench],
        "shop": list(player.shop), "shop_champions": [freeze_unit(champion) for champion in player.shop_champions],
        "items": list(player.item_bench),
        "num_units_in_play": player.num_units_in_play, "max_units": player.max_units,
        "economy": {key: getattr(player, key) for key in
                    ("gold", "level", "exp", "health", "win_streak", "loss_streak", "max_units",
                     "refresh_cost", "exp_cost", "level_costs", "max_level")},
        "traits": {"composition": player.team_composition, "tiers": player.team_tiers},
        "round": round_number, "player_round": player.round,
    })



def board_slots(snapshot, occupied_only=False):
    return [{"location": location, "unit": unit} for location, unit in board_locations(snapshot["board"])
            if not occupied_only or unit is not None]


def bench_slots(snapshot, occupied_only=False):
    return [{"location": location, "unit": unit} for location, unit in bench_locations(snapshot["bench"])
            if not occupied_only or unit is not None]


def inventory_slots(snapshot, occupied_only=False):
    return [{"slot": slot, "item": item} for slot, item in enumerate(snapshot["items"])
            if not occupied_only or item is not None]


def trait_records(traits, active_only=False):
    return [{"trait_id": key, "count": count, "tier": traits["tiers"][key]}
            for key, count in sorted(traits["composition"].items()) if not active_only or count != 0]


def shop_slots(snapshot):
    """Project native prices and check stored offers before publishing them."""
    slots = []
    for slot, (offer, unit) in enumerate(zip(snapshot["shop"], snapshot["shop_champions"], strict=True)):
        expected_offer = shop_offer_name(unit["champion"], unit["chosen"]) if unit else None
        if offer != expected_offer:
            raise SessionError("internal_error", "Stored shop offer is inconsistent.", {"category": "shop", "slot": slot})
        price = native_price(unit["cost"], unit["stars"]) if unit else None
        slots.append({"slot": slot, "unit": unit, "purchase_cost": price})
    return slots


def decision_snapshot(snapshot, status):
    """Project one detached own-state record, omitting empty owned slots."""
    economy = {key: snapshot["economy"][key] for key in
               ("gold", "health", "level", "exp", "max_units", "win_streak", "loss_streak",
                "refresh_cost", "exp_cost", "max_level")}
    economy["num_units_in_play"] = snapshot["num_units_in_play"]
    economy["next_level_cost"] = (snapshot["economy"]["level_costs"][economy["level"]]
                                  if economy["level"] < economy["max_level"] else None)
    return {"status": status, "snapshot_round": snapshot["round"], "economy": economy,
            "board": board_slots(snapshot, occupied_only=True),
            "bench": bench_slots(snapshot, occupied_only=True),
            "shop": shop_slots(snapshot),
            "items": inventory_slots(snapshot, occupied_only=True),
            "traits": trait_records(snapshot["traits"], active_only=True)}
