"""The single concrete gameplay tool set."""

from mcp.types import Tool

from tft_mcp.tool_schemas import (
    EMPTY_INPUT, CHAMPION_SUMMARY, CHAMPION_PROPERTIES, TRAIT_SUMMARY,
    TRAIT_PROPERTIES, ITEM_SUMMARY_SCHEMA, ITEM_SCHEMA, PLAYER_INPUT,
    BOARD_PROPERTIES, REFRESH_PROPERTIES, XP_PROPERTIES,
    PUBLIC_PLAYER_PROPERTIES, LOCATION_SCHEMA, BUY_PROPERTIES,
    SELL_PROPERTIES, MOVE_PROPERTIES, EQUIP_PROPERTIES, DECISION_SCHEMA,
)


ACTION_TOOLS = {"buy_unit", "sell_unit", "move_unit", "equip_item", "refresh_shop", "buy_xp", "end_turn"}


def action_schema(properties):
    return {"type": "object", "properties": {
        "receipt": {"type": "object", "properties": properties,
                    "required": list(properties), "additionalProperties": False},
        "decision": DECISION_SCHEMA},
        "required": ["receipt", "decision"], "additionalProperties": False}


TOOLS = [
    Tool(name="end_turn", description="Finish planning, run combat and return the next decision or completed lobby.",
         inputSchema=EMPTY_INPUT, outputSchema=DECISION_SCHEMA),
    Tool(name="search_champions", description="Search installed champion IDs, optionally filtered by cost and intrinsic trait.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string", "default": ""},
            "cost": {"type": "integer", "minimum": 1, "maximum": 5}, "trait_id": {"type": "string"}}, "additionalProperties": False},
        outputSchema={"type": "object", "properties": {"champions": {"type": "array", "items": CHAMPION_SUMMARY}},
            "required": ["champions"], "additionalProperties": False}),
    Tool(name="get_champion", description="Read an exact champion ID: raw stats, ability parameters, star prices and Chosen metadata. Text descriptions are unavailable.",
        inputSchema={"type": "object", "properties": {"champion_id": {"type": "string"}}, "required": ["champion_id"], "additionalProperties": False},
        outputSchema={"type": "object", "properties": CHAMPION_PROPERTIES, "required": list(CHAMPION_PROPERTIES), "additionalProperties": False}),
    Tool(name="search_traits", description="Search installed trait IDs and activation thresholds.",
             inputSchema={"type": "object", "properties": {"query": {"type": "string", "default": ""}}, "additionalProperties": False},
             outputSchema={"type": "object", "properties": {"traits": {"type": "array", "items": TRAIT_SUMMARY}}, "required": ["traits"], "additionalProperties": False}),
    Tool(name="get_trait", description="Read an exact trait ID: thresholds, raw effects and champion membership. Ninja activation is exact. Text descriptions are unavailable.",
             inputSchema={"type": "object", "properties": {"trait_id": {"type": "string"}}, "required": ["trait_id"], "additionalProperties": False},
             outputSchema={"type": "object", "properties": TRAIT_PROPERTIES, "required": list(TRAIT_PROPERTIES), "additionalProperties": False}),
    Tool(name="search_items", description="Search installed item IDs, optionally filtered by component, equipment or consumable.",
             inputSchema={"type": "object", "properties": {
                 "query": {"type": "string", "default": ""},
                 "kind": {"type": "string", "enum": ["component", "equipment", "consumable"]}},
                 "additionalProperties": False},
             outputSchema={"type": "object", "properties": {"items": {"type": "array", "items": ITEM_SUMMARY_SCHEMA}},
                           "required": ["items"], "additionalProperties": False}),
    Tool(name="get_item", description="Read an exact item ID: raw effects, recipes and native constraints. Text descriptions are unavailable.",
             inputSchema={"type": "object", "properties": {"item_id": {"type": "string"}},
                          "required": ["item_id"], "additionalProperties": False}, outputSchema=ITEM_SCHEMA),
    Tool(name="get_board", description="Scout a living opponent by player_id. Omission returns your board. Removed opponents return player_eliminated.",
        inputSchema=PLAYER_INPUT, outputSchema={"type": "object", "properties": BOARD_PROPERTIES,
        "required": list(BOARD_PROPERTIES), "additionalProperties": False}),
    Tool(name="refresh_shop", description="Buy one shop refresh at the current cost. Returns receipt and updated decision.",
             inputSchema=EMPTY_INPUT, outputSchema=action_schema(REFRESH_PROPERTIES)),
    Tool(name="buy_xp", description="Buy one experience increment at the current cost. Returns receipt and updated decision.",
             inputSchema=EMPTY_INPUT, outputSchema=action_schema(XP_PROPERTIES)),
    Tool(name="get_players", description="Read all eight player IDs, public health, level and final placements.",
        inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": {
            "game_id": {"type": "string"}, "players": {"type": "array", "items": {
                "type": "object", "properties": PUBLIC_PLAYER_PROPERTIES,
                "required": list(PUBLIC_PLAYER_PROPERTIES), "additionalProperties": False}}},
            "required": ["game_id", "players"], "additionalProperties": False}),
    Tool(name="equip_item", description="Assign inventory item_slot 0..9 to an owned unit. Unsafe native combinations reject. Returns receipt and updated decision.",
             inputSchema={"type": "object", "properties": {"item_slot": EQUIP_PROPERTIES["item_slot"], "target": LOCATION_SCHEMA},
                          "required": ["item_slot", "target"], "additionalProperties": False},
             outputSchema=action_schema(EQUIP_PROPERTIES)),
    Tool(name="buy_unit", description="Buy shop_slot 0..4, including supported native merges. Returns receipt and updated decision.",
             inputSchema={"type": "object", "properties": {"shop_slot": BUY_PROPERTIES["shop_slot"]},
                          "required": ["shop_slot"], "additionalProperties": False},
             outputSchema=action_schema(BUY_PROPERTIES)),
    Tool(name="move_unit", description="Move or swap an owned unit. Bench-to-bench and same-location moves are unsupported. Returns receipt and updated decision.",
             inputSchema={"type": "object", "properties": {"source": LOCATION_SCHEMA, "target": LOCATION_SCHEMA},
                          "required": ["source", "target"], "additionalProperties": False},
             outputSchema=action_schema(MOVE_PROPERTIES)),
    Tool(name="sell_unit", description="Sell an owned board or bench unit. Bench item overflow drops the equipment set. Returns receipt and updated decision.",
             inputSchema={"type": "object", "properties": {"location": LOCATION_SCHEMA},
                          "required": ["location"], "additionalProperties": False},
             outputSchema=action_schema(SELL_PROPERTIES)),
    Tool(name="get_decision",
        description="Read status, economy, occupied own board/bench/items, all shop offers and nonzero traits. Empty slots are omitted; indices stay exact.",
        inputSchema=EMPTY_INPUT, outputSchema=DECISION_SCHEMA),
]
