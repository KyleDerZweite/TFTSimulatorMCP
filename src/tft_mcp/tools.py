"""Explicit gameplay tools and their default/compact discovery profiles."""

from mcp.types import Tool

from tft_mcp.tool_schemas import (
    OUTCOME_SCHEMA,
    STATUS_SCHEMA,
    EMPTY_INPUT,
    CHAMPION_SUMMARY,
    CHAMPION_PROPERTIES,
    TRAIT_SUMMARY,
    TRAIT_PROPERTIES,
    ITEM_SUMMARY_SCHEMA,
    ITEM_SCHEMA,
    PLAYER_INPUT,
    BOARD_PROPERTIES,
    BENCH_PROPERTIES,
    SHOP_PROPERTIES,
    REFRESH_PROPERTIES,
    XP_PROPERTIES,
    INVENTORY_PROPERTIES,
    ECONOMY_PROPERTIES,
    OWN_TRAIT_PROPERTIES,
    PUBLIC_PLAYER_PROPERTIES,
    LOCATION_SCHEMA,
    BUY_PROPERTIES,
    SELL_PROPERTIES,
    MOVE_PROPERTIES,
    EQUIP_PROPERTIES,
    DECISION_SCHEMA,
)


TOOLS = [
    Tool(name="end_turn", description="End planning explicitly and return the next decision or completed lobby.",
         inputSchema=EMPTY_INPUT, outputSchema=STATUS_SCHEMA),
    Tool(name="start_game", description="Start one seeded eight-player game with player_0 controlled. Close an active game first.",
         inputSchema={"type": "object", "properties": {
             "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647}},
             "required": ["seed"], "additionalProperties": False}, outputSchema=STATUS_SCHEMA),
    Tool(name="get_game_status", description="Inspect lifecycle status without advancing the game.",
         inputSchema=EMPTY_INPUT, outputSchema=STATUS_SCHEMA),
    Tool(name="close_game", description="Close the current game and return its outcome and idle status. Closing idle is idempotent.",
         inputSchema=EMPTY_INPUT, outputSchema={
             "type": "object", "properties": {
                 "closed_game_id": {"type": ["string", "null"]},
                 "outcome": OUTCOME_SCHEMA, "status": STATUS_SCHEMA},
             "required": ["closed_game_id", "outcome", "status"], "additionalProperties": False}),
]


TOOLS.append(Tool(name="search_champions", description="Search canonical installed simulator champion IDs with optional cost and intrinsic trait filters. Works without a game.",
    inputSchema={"type": "object", "properties": {"query": {"type": "string", "default": ""},
        "cost": {"type": "integer", "minimum": 1, "maximum": 5}, "trait_id": {"type": "string"}}, "additionalProperties": False},
    outputSchema={"type": "object", "properties": {"champions": {"type": "array", "items": CHAMPION_SUMMARY}},
        "required": ["champions"], "additionalProperties": False}))


TOOLS.append(Tool(name="get_champion", description="Read raw installed simulator champion definitions, star gold costs and Chosen metadata. Descriptions unavailable; stats are not dynamically adjusted.",
    inputSchema={"type": "object", "properties": {"champion_id": {"type": "string"}}, "required": ["champion_id"], "additionalProperties": False},
    outputSchema={"type": "object", "properties": CHAMPION_PROPERTIES, "required": list(CHAMPION_PROPERTIES), "additionalProperties": False}))


TOOLS.extend([
    Tool(name="search_traits", description="Search canonical installed simulator trait IDs and activation thresholds without a game.",
         inputSchema={"type": "object", "properties": {"query": {"type": "string", "default": ""}}, "additionalProperties": False},
         outputSchema={"type": "object", "properties": {"traits": {"type": "array", "items": TRAIT_SUMMARY}}, "required": ["traits"], "additionalProperties": False}),
    Tool(name="get_trait", description="Read installed simulator trait thresholds, raw effect parameters and intrinsic champion membership. Ninja activation is exact; descriptions unavailable.",
         inputSchema={"type": "object", "properties": {"trait_id": {"type": "string"}}, "required": ["trait_id"], "additionalProperties": False},
         outputSchema={"type": "object", "properties": TRAIT_PROPERTIES, "required": list(TRAIT_PROPERTIES), "additionalProperties": False}),
    Tool(name="get_trait_champions", description="List canonical champions with an intrinsic installed simulator trait, without item or Chosen counts.",
         inputSchema={"type": "object", "properties": {"trait_id": {"type": "string"}}, "required": ["trait_id"], "additionalProperties": False},
         outputSchema={"type": "object", "properties": {"trait_id": {"type": "string"}, "champions": {"type": "array", "items": CHAMPION_SUMMARY}}, "required": ["trait_id", "champions"], "additionalProperties": False}),
])


TOOLS.extend([
    Tool(name="search_items", description="Search static installed simulator item IDs by case-insensitive substring and optional kind, without a game.",
         inputSchema={"type": "object", "properties": {
             "query": {"type": "string", "default": ""},
             "kind": {"type": "string", "enum": ["component", "equipment", "consumable"]}},
             "additionalProperties": False},
         outputSchema={"type": "object", "properties": {"items": {"type": "array", "items": ITEM_SUMMARY_SCHEMA}},
                       "required": ["items"], "additionalProperties": False}),
    Tool(name="get_item", description="Inspect an exact canonical installed simulator item ID, raw effects, recipes and simulator constraints. Official description is unavailable.",
         inputSchema={"type": "object", "properties": {"item_id": {"type": "string"}},
                      "required": ["item_id"], "additionalProperties": False}, outputSchema=ITEM_SCHEMA),
])


TOOLS.append(Tool(name="get_board", description="Inspect own or a known living opponent board. Omitted player_id selects player_0. Removed opponents return player_eliminated. Boards use local x=0..6 left-to-right, y=0..3 bottom-to-top coordinates. Terminal round is the retained own snapshot round.",
    inputSchema=PLAYER_INPUT, outputSchema={"type": "object", "properties": BOARD_PROPERTIES,
    "required": list(BOARD_PROPERTIES), "additionalProperties": False}))


TOOLS.append(Tool(name="get_bench", description="Inspect all own reserve slots, indexed 0..8. Terminal round is the retained own snapshot round.",
    inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": BENCH_PROPERTIES,
    "required": list(BENCH_PROPERTIES), "additionalProperties": False}))


TOOLS.append(Tool(name="get_shop", description="Inspect all own shop offers and native purchase prices, indexed 0..4. Terminal round is the retained own snapshot round.",
    inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": SHOP_PROPERTIES,
    "required": list(SHOP_PROPERTIES), "additionalProperties": False}))


TOOLS.extend([
    Tool(name="refresh_shop", description="Buy one native shop refresh using the current cost. Repeated offers are valid. Consumes one planning action.",
         inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": REFRESH_PROPERTIES,
         "required": list(REFRESH_PROPERTIES), "additionalProperties": False}),
    Tool(name="buy_xp", description="Buy one native experience increment using the current cost and level cap. Returns actual level and capacity progression. Consumes one planning action.",
         inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": XP_PROPERTIES,
         "required": list(XP_PROPERTIES), "additionalProperties": False}),
])


TOOLS.append(Tool(name="get_items", description="Inspect all own loose inventory items, indexed 0..9. Terminal round is the retained own snapshot round.",
    inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": INVENTORY_PROPERTIES,
    "required": list(INVENTORY_PROPERTIES), "additionalProperties": False}))


TOOLS.append(Tool(name="get_economy", description="Inspect own gold, health, level, experience and the shared planning budget. Terminal budget is null and round is the retained own snapshot round.",
    inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": ECONOMY_PROPERTIES,
    "required": list(ECONOMY_PROPERTIES), "additionalProperties": False}))


TOOLS.append(Tool(name="get_traits", description="Inspect own or a known living opponent stored trait counts and tiers without recomputation. Omitted player_id selects player_0; removed opponents return player_eliminated. Terminal round is the retained own snapshot round.",
    inputSchema=PLAYER_INPUT, outputSchema={"type": "object", "properties": OWN_TRAIT_PROPERTIES,
    "required": list(OWN_TRAIT_PROPERTIES), "additionalProperties": False}))


TOOLS.append(Tool(name="get_round", description="Inspect the current installed simulator round. Terminal returns the final completed-lobby round, which can differ from retained own category rounds.",
    inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": {
        "game_id": {"type": "string"}, "round": {"type": "integer"}},
        "required": ["game_id", "round"], "additionalProperties": False}))


TOOLS.append(Tool(name="get_players", description="List stable initial player IDs and public health, level and native placement. Removed players retain public final status until close.",
    inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": {
        "game_id": {"type": "string"}, "players": {"type": "array", "items": {
            "type": "object", "properties": PUBLIC_PLAYER_PROPERTIES,
            "required": list(PUBLIC_PLAYER_PROPERTIES), "additionalProperties": False}}},
        "required": ["game_id", "players"], "additionalProperties": False}))


TOOLS.extend([
    Tool(name="equip_item", description="Assign one inventory item at slot 0..9 to one owned board or bench unit. Native recipes, direct gloves and safe consumables consume one action without combat. Unsupported: component glove pair, additions/remover/reforger on gloves, trait reforge, unsafe trait removal and bench Kayn tokens. Kayn forms expose literal board effects, not guaranteed combat transformation.",
         inputSchema={"type": "object", "properties": {"item_slot": EQUIP_PROPERTIES["item_slot"], "target": LOCATION_SCHEMA},
                      "required": ["item_slot", "target"], "additionalProperties": False},
         outputSchema={"type": "object", "properties": EQUIP_PROPERTIES, "required": list(EQUIP_PROPERTIES), "additionalProperties": False}),
    Tool(name="buy_unit", description="Buy one own shop offer at slot 0..4 using installed native prices and merges. Full-bench merges are supported. Consume one planning action and return at the same round without combat.",
         inputSchema={"type": "object", "properties": {"shop_slot": BUY_PROPERTIES["shop_slot"]},
                      "required": ["shop_slot"], "additionalProperties": False},
         outputSchema={"type": "object", "properties": BUY_PROPERTIES, "required": list(BUY_PROPERTIES), "additionalProperties": False}),
    Tool(name="move_unit", description="Move one owned unit using board x=0..6,y=0..3 or bench slot=0..8. Native supported swaps consume one action. Bench-to-board displacement uses the first bench vacancy. Same-location and bench-to-bench movement are unsupported.",
         inputSchema={"type": "object", "properties": {"source": LOCATION_SCHEMA, "target": LOCATION_SCHEMA},
                      "required": ["source", "target"], "additionalProperties": False},
         outputSchema={"type": "object", "properties": MOVE_PROPERTIES, "required": list(MOVE_PROPERTIES), "additionalProperties": False}),
    Tool(name="sell_unit", description="Sell one owned board or bench unit. Board equipment needs inventory capacity; bench overflow drops the complete real equipment set. Thieves gloves return only the glove. Consume one planning action without combat.",
         inputSchema={"type": "object", "properties": {"location": LOCATION_SCHEMA},
                      "required": ["location"], "additionalProperties": False},
         outputSchema={"type": "object", "properties": SELL_PROPERTIES, "required": list(SELL_PROPERTIES), "additionalProperties": False}),
])


TOOLS.append(Tool(name="get_decision",
    description="Read one compact own decision: status, economy, occupied board/bench/items, shop and nonzero stored traits. Empty owned slots are omitted; indices remain exact. snapshot_round retains the own round after elimination; status.round is the lobby round. Does not advance play.",
    inputSchema=EMPTY_INPUT, outputSchema=DECISION_SCHEMA))


ACTION_TOOLS = {"buy_unit", "sell_unit", "move_unit", "equip_item", "refresh_shop", "buy_xp", "end_turn"}


COMPACT_TOOLS = ACTION_TOOLS | {"get_decision", "get_board", "get_players", "search_champions",
    "get_champion", "search_traits", "get_trait", "search_items", "get_item"}


def profile_tools(profile):
    if profile == "default":
        return TOOLS
    tools = []
    for tool in TOOLS:
        if tool.name not in COMPACT_TOOLS:
            continue
        updates = {}
        if tool.name == "end_turn":
            updates = {"outputSchema": DECISION_SCHEMA,
                       "description": "Finish planning, run combat and return the next decision or completed lobby. Continue until status.state is terminal."}
        elif tool.name in ACTION_TOOLS:
            updates = {"outputSchema": {"type": "object", "properties": {
                "receipt": tool.outputSchema, "decision": DECISION_SCHEMA},
                "required": ["receipt", "decision"], "additionalProperties": False},
                "description": tool.description + " Returns receipt and current decision; use those exact slots for the next action."}
        tools.append(tool.model_copy(update=updates))
    return tools
