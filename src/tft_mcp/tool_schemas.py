"""Shared strict MCP record schemas, independent of runtime and simulator state."""

OUTCOME_SCHEMA = {
    "type": ["object", "null"],
    "properties": {
        "controlled_placement": {"type": ["integer", "null"], "minimum": 1, "maximum": 8},
        "lobby_complete": {"type": "boolean"}, "reason": {"type": "string"},
    },
    "required": ["controlled_placement", "lobby_complete", "reason"],
    "additionalProperties": False,
}


STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "state": {"type": "string", "enum": ["idle", "running", "terminal"]},
        "game_id": {"type": ["string", "null"]},
        "controlled_player_id": {"type": ["string", "null"]},
        "round": {"type": ["integer", "null"]},
        "planning_budget": {
            "type": ["object", "null"],
            "properties": {"capacity": {"type": "integer", "const": 14},
                           "remaining": {"type": "integer", "minimum": 0, "maximum": 14}},
            "required": ["capacity", "remaining"], "additionalProperties": False,
        },
        "outcome": OUTCOME_SCHEMA,
    },
    "required": ["state", "game_id", "controlled_player_id", "round", "planning_budget", "outcome"],
    "additionalProperties": False,
}


EMPTY_INPUT = {"type": "object", "properties": {}, "additionalProperties": False}


CHAMPION_SUMMARY = {"type": "object", "properties": {
    "champion_id": {"type": "string"}, "cost": {"type": "integer"},
    "traits": {"type": "array", "items": {"type": "string"}}},
    "required": ["champion_id", "cost", "traits"], "additionalProperties": False}


CHAMPION_PROPERTIES = dict(CHAMPION_SUMMARY["properties"], **{
    "star_costs": {"type": "array", "items": {"type": "object", "properties": {
        "stars": {"type": "integer", "enum": [1, 2, 3]}, "gold": {"type": "integer"}},
        "required": ["stars", "gold"], "additionalProperties": False}},
    "base_stats": {"type": "object"}, "rule_parameters": {"type": "object"},
    "special_attributes": {"type": "object", "properties": {
        "chosen": {"type": "object", "properties": {
            "eligible_traits": {"type": "array", "items": {"type": "string"}},
            "bonus": {"type": ["object", "null"], "properties": {
                "stat": {"type": "string"}, "value": {"type": "number"}},
                "required": ["stat", "value"], "additionalProperties": False}},
            "required": ["eligible_traits", "bonus"], "additionalProperties": False},
        "kayn_forms": {"type": "array", "items": {"type": "string"}}},
        "required": ["chosen", "kayn_forms"], "additionalProperties": False},
    "description": {"type": "null"}, "ability_description": {"type": "null"},
    "unavailable_fields": {"type": "array", "items": {"type": "string"}},
})


TRAIT_SUMMARY = {"type": "object", "properties": {
    "trait_id": {"type": "string"}, "thresholds": {"type": "array", "items": {"type": "integer"}}},
    "required": ["trait_id", "thresholds"], "additionalProperties": False}


TRAIT_PROPERTIES = dict(TRAIT_SUMMARY["properties"], **{
    "activation": {"type": "string", "enum": ["minimum", "exact"]}, "effects": {"type": "object"},
    "champion_ids": {"type": "array", "items": {"type": "string"}}, "chosen_eligible": {"type": "boolean"},
    "description": {"type": "null"}, "unavailable_fields": {"type": "array", "items": {"type": "string"}},
})


ITEM_SUMMARY_SCHEMA = {
    "type": "object", "properties": {
        "item_id": {"type": "string"},
        "kind": {"type": "string", "enum": ["component", "equipment", "consumable"]},
        "craftable": {"type": "boolean"}},
    "required": ["item_id", "kind", "craftable"], "additionalProperties": False,
}


COMPONENT_PAIR_SCHEMA = {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2}


ITEM_SCHEMA = {
    "type": "object", "properties": {
        **ITEM_SUMMARY_SCHEMA["properties"],
        "base_stats": {"type": "object"}, "effects": {"type": "object"},
        "recipe": {**COMPONENT_PAIR_SCHEMA, "type": ["array", "null"]},
        "builds_into": {"type": "array", "items": {
            "type": "object", "properties": {"item_id": {"type": "string"}, "components": COMPONENT_PAIR_SCHEMA},
            "required": ["item_id", "components"], "additionalProperties": False}},
        "granted_trait": {"type": ["string", "null"]},
        "constraints": {"type": "array", "items": {"type": "string"}},
        "description": {"type": "null"},
        "unavailable_fields": {"type": "array", "items": {"const": "description"}, "minItems": 1, "maxItems": 1}},
    "required": ["item_id", "kind", "craftable", "base_stats", "effects", "recipe", "builds_into",
                 "granted_trait", "constraints", "description", "unavailable_fields"],
    "additionalProperties": False,
}


UNIT_SCHEMA = {
    "type": ["object", "null"], "properties": {
        "champion": {"type": "string"}, "stars": {"type": "integer", "minimum": 1, "maximum": 4},
        "items": {"type": "array", "items": {"type": "string"}},
        "chosen": {"anyOf": [{"const": False}, {"type": "string"}]},
        "cost": {"type": "integer"}, "kayn_form": {"type": ["string", "null"]},
        "traits": {"type": "array", "items": {"type": "string"}},
        "target_dummy": {"type": "boolean"},
        "sandguard_overlord_coordinates": {"type": "array", "items": {
            "type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}}},
    "required": ["champion", "stars", "items", "chosen", "cost", "kayn_form", "traits", "target_dummy", "sandguard_overlord_coordinates"],
    "additionalProperties": False,
}


PLAYER_INPUT = {"type": "object", "properties": {"player_id": {"type": "string"}}, "additionalProperties": False}


PLAYER_PROPERTIES = {"game_id": {"type": "string"}, "player_id": {"type": "string"}, "round": {"type": "integer"}}


BOARD_PROPERTIES = {**PLAYER_PROPERTIES,
    "slots": {"type": "array", "minItems": 28, "maxItems": 28, "items": {
        "type": "object", "properties": {
            "location": {"type": "object", "properties": {
                "kind": {"const": "board"}, "x": {"type": "integer", "minimum": 0, "maximum": 6},
                "y": {"type": "integer", "minimum": 0, "maximum": 3}},
                "required": ["kind", "x", "y"], "additionalProperties": False}, "unit": UNIT_SCHEMA},
        "required": ["location", "unit"], "additionalProperties": False}},
    "num_units_in_play": {"type": "integer"}, "max_units": {"type": "integer"}}


BENCH_PROPERTIES = {**PLAYER_PROPERTIES, "slots": {"type": "array", "minItems": 9, "maxItems": 9, "items": {
    "type": "object", "properties": {"location": {"type": "object", "properties": {
        "kind": {"const": "bench"}, "slot": {"type": "integer", "minimum": 0, "maximum": 8}},
        "required": ["kind", "slot"], "additionalProperties": False}, "unit": UNIT_SCHEMA},
    "required": ["location", "unit"], "additionalProperties": False}}}


SHOP_PROPERTIES = {**PLAYER_PROPERTIES, "slots": {"type": "array", "minItems": 5, "maxItems": 5, "items": {
    "type": "object", "properties": {"slot": {"type": "integer", "minimum": 0, "maximum": 4},
        "unit": UNIT_SCHEMA, "purchase_cost": {"type": ["integer", "null"]}},
    "required": ["slot", "unit", "purchase_cost"], "additionalProperties": False}}}


REFRESH_PROPERTIES = {"gold_spent": {"type": "integer"}, "slots": SHOP_PROPERTIES["slots"], "status": STATUS_SCHEMA}


XP_PROPERTIES = {**{key: {"type": "integer"} for key in
    ("gold_spent", "xp_before", "xp", "level_before", "level", "unit_capacity")}, "status": STATUS_SCHEMA}


INVENTORY_PROPERTIES = {**PLAYER_PROPERTIES, "slots": {"type": "array", "minItems": 10, "maxItems": 10, "items": {
    "type": "object", "properties": {"slot": {"type": "integer", "minimum": 0, "maximum": 9},
        "item": {"type": ["string", "null"]}}, "required": ["slot", "item"], "additionalProperties": False}}}


ECONOMY_PROPERTIES = {**PLAYER_PROPERTIES, **{key: {"type": "integer"} for key in ("gold", "health", "level", "exp")},
    "planning_budget": STATUS_SCHEMA["properties"]["planning_budget"]}


OWN_TRAIT_PROPERTIES = {**PLAYER_PROPERTIES, "traits": {"type": "array", "items": {
    "type": "object", "properties": {"trait_id": {"type": "string"}, "count": {"type": "integer"}, "tier": {"type": "integer"}},
    "required": ["trait_id", "count", "tier"], "additionalProperties": False}}}


PUBLIC_PLAYER_PROPERTIES = {
    "player_id": {"type": "string"}, "controlled": {"type": "boolean"},
    "status": {"enum": ["alive", "eliminated", "winner"]},
    "health": {"type": ["integer", "null"]}, "level": {"type": ["integer", "null"]},
    "placement": {"type": ["integer", "null"], "minimum": 1, "maximum": 8},
}


LOCATION_SCHEMA = {"type": "object", "properties": {
    "kind": {"type": "string", "enum": ["board", "bench"]},
    "x": {"type": "integer", "minimum": 0, "maximum": 6},
    "y": {"type": "integer", "minimum": 0, "maximum": 3},
    "slot": {"type": "integer", "minimum": 0, "maximum": 8},
}, "description": "JSON object: board uses kind,x,y; bench uses kind,slot.", "oneOf": [
    BOARD_PROPERTIES["slots"]["items"]["properties"]["location"],
    BENCH_PROPERTIES["slots"]["items"]["properties"]["location"],
]}


UNIT_CHANGE_SCHEMA = {"type": "object", "properties": {
    "location": LOCATION_SCHEMA, "before": UNIT_SCHEMA, "after": UNIT_SCHEMA},
    "required": ["location", "before", "after"], "additionalProperties": False}


ITEM_CHANGE_SCHEMA = {"type": "object", "properties": {
    "slot": {"type": "integer", "minimum": 0, "maximum": 9},
    "before": {"type": ["string", "null"]}, "after": {"type": ["string", "null"]}},
    "required": ["slot", "before", "after"], "additionalProperties": False}


BUY_PROPERTIES = {
    "shop_slot": {"type": "integer", "minimum": 0, "maximum": 4},
    "purchased": {**UNIT_SCHEMA, "type": "object"},
    "gold_spent": {"type": "integer", "minimum": 0},
    "unit_changes": {"type": "array", "items": UNIT_CHANGE_SCHEMA},
    "item_changes": {"type": "array", "items": ITEM_CHANGE_SCHEMA}, "status": STATUS_SCHEMA,
}


SELL_PROPERTIES = {
    "location": LOCATION_SCHEMA, "sold": {**UNIT_SCHEMA, "type": "object"},
    "gold_gained": {"type": "integer", "minimum": 0},
    "returned_items": {"type": "array", "items": {"type": "string"}},
    "dropped_items": {"type": "array", "items": {"type": "string"}},
    "unit_changes": {"type": "array", "items": UNIT_CHANGE_SCHEMA}, "status": STATUS_SCHEMA,
}


MOVE_PROPERTIES = {"source": LOCATION_SCHEMA, "target": LOCATION_SCHEMA,
                   "unit_changes": {"type": "array", "items": UNIT_CHANGE_SCHEMA}, "status": STATUS_SCHEMA}


EQUIP_PROPERTIES = {"item_slot": {"type": "integer", "minimum": 0, "maximum": 9},
                    "item_id": {"type": "string"}, "target": LOCATION_SCHEMA,
                    "unit_changes": {"type": "array", "items": UNIT_CHANGE_SCHEMA},
                    "item_changes": {"type": "array", "items": ITEM_CHANGE_SCHEMA},
                    "kayn_form": {"type": ["string", "null"]}, "status": STATUS_SCHEMA}


DECISION_PROPERTIES = {
    "status": STATUS_SCHEMA, "snapshot_round": {"type": "integer"},
    "economy": {"type": "object", "properties": {
        **{key: {"type": "integer"} for key in
           ("gold", "health", "level", "exp", "max_units", "num_units_in_play", "win_streak",
            "loss_streak", "refresh_cost", "exp_cost", "max_level")},
        "next_level_cost": {"type": ["integer", "null"]}},
        "required": ["gold", "health", "level", "exp", "max_units", "num_units_in_play", "win_streak",
                     "loss_streak", "refresh_cost", "exp_cost", "max_level", "next_level_cost"],
        "additionalProperties": False},
    "board": {**BOARD_PROPERTIES["slots"], "minItems": 0},
    "bench": {**BENCH_PROPERTIES["slots"], "minItems": 0},
    "shop": SHOP_PROPERTIES["slots"],
    "items": {**INVENTORY_PROPERTIES["slots"], "minItems": 0},
    "traits": OWN_TRAIT_PROPERTIES["traits"],
}


DECISION_SCHEMA = {"type": "object", "properties": DECISION_PROPERTIES,
                   "required": list(DECISION_PROPERTIES), "additionalProperties": False}
