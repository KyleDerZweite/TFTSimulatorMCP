"""The single concrete gameplay tool set."""

from mcp.types import Tool

from tft_mcp.tool_schemas import (
    EMPTY_INPUT, CHAMPION_SUMMARY, CHAMPION_PROPERTIES, TRAIT_SUMMARY,
    TRAIT_PROPERTIES, ITEM_SUMMARY_SCHEMA, ITEM_SCHEMA, PLAYER_INPUT, POOL_PROPERTIES,
    BOARD_PROPERTIES, PUBLIC_PLAYER_PROPERTIES, LOCATION_SCHEMA, OBSERVATION_SCHEMA,
    COMP_CHAMPION_INPUT, COMP_CHAMPION_OUTPUT, COMP_TRAIT_INPUT, COMP_TRAIT_OUTPUT,
    CHAMPION_ITEMS_INPUT, CHAMPION_ITEMS_OUTPUT, LAST_FIGHT_PROPERTIES,
)


ACTION_TOOLS = {"buy_unit", "sell_unit", "move_unit", "equip_item", "refresh_shop", "buy_xp", "end_turn"}


TOOLS = [
    Tool(name="end_turn", description="Pass the rest of this planning phase. Returns the next observation. Read it before another tool call. text reports success and every section that changed, including opponent boards and traits when those changed.",
         inputSchema=EMPTY_INPUT, outputSchema=OBSERVATION_SCHEMA),
    Tool(name="search_champions", description="Search installed champion IDs, optionally filtered by cost and intrinsic trait.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string", "default": ""},
            "cost": {"type": "integer", "minimum": 1, "maximum": 5}, "trait_id": {"type": "string"}}, "additionalProperties": False},
        outputSchema={"type": "object", "properties": {"champions": {"type": "array", "items": CHAMPION_SUMMARY}},
            "required": ["champions"], "additionalProperties": False}),
    Tool(name="get_champion", description="Read an exact champion ID: raw stats, ability parameters, star prices and Chosen metadata. Text descriptions are unavailable.",
        inputSchema={"type": "object", "properties": {"champion_id": {"type": "string"}}, "required": ["champion_id"], "additionalProperties": False},
        outputSchema={"type": "object", "properties": CHAMPION_PROPERTIES, "required": list(CHAMPION_PROPERTIES), "additionalProperties": False}),
    Tool(name="get_champion_pool", description="Read the most copies of an exact champion ID that can remain in the pool. Subtracts your board, your bench, and living opponents' boards. One star counts as 1 copy, and each further star multiplies that by 3. Shop offers stay in the pool until bought. Opponent benches and shops stay hidden, so the true pool can be lower.",
        inputSchema={"type": "object", "properties": {"champion_id": {"type": "string"}}, "required": ["champion_id"], "additionalProperties": False},
        outputSchema={"type": "object", "properties": POOL_PROPERTIES, "required": list(POOL_PROPERTIES), "additionalProperties": False}),
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
    Tool(name="search_comps_by_champions",
         description="Return up to limit Set 4 Challenger EUW final boards that include every named champion, highest top-4 rate first. A comp is the exact set of champion names on a final board, at any star level. Win rate is the share of those boards that finished in placements 1 through 4. The index keeps lists that appear on at least 100 final boards. Ties break toward more games, then alphabetical champion lists. Names accept the recorded spelling or the simulator id, such as Ahri or ahri. Boards are pooled across patches 10.19 through 11.1. This read spends nothing.",
         inputSchema=COMP_CHAMPION_INPUT, outputSchema=COMP_CHAMPION_OUTPUT),
    Tool(name="search_comps_by_trait",
         description="Return up to limit Set 4 Challenger EUW final boards whose recorded unit count for the trait equals level, highest top-4 rate first. Level is that count, such as 6 for six Cultists. The rate uses boards with that exact count. The index keeps a trait level when at least 100 boards of that champion list recorded it. Ties break toward more games, then alphabetical champion lists. Trait names accept the recorded spelling or the simulator id, such as Mage or mage. Boards are pooled across patches 10.19 through 11.1. This read spends nothing.",
         inputSchema=COMP_TRAIT_INPUT, outputSchema=COMP_TRAIT_OUTPUT),
    Tool(name="search_champion_items",
         description="Return every item combination recorded on this champion on at least 100 Set 4 Challenger EUW final boards, highest top-4 rate first. Pass one or two items to keep only combinations that include them. A combination is the exact multiset of items on that champion, at any star level; order on the unit does not matter. Win rate is the share of those boards that finished in placements 1 through 4. Ties break toward more games, then alphabetical item names. Names accept the recorded item name or the simulator id, such as Guinsoo's Rageblade or guinsoos_rageblade. Boards are pooled across patches 10.19 through 11.1. This read spends nothing.",
         inputSchema=CHAMPION_ITEMS_INPUT, outputSchema=CHAMPION_ITEMS_OUTPUT),
    Tool(name="get_board", description="Scout a living opponent by player_id. Omission returns your board. Removed opponents return player_eliminated.",
        inputSchema=PLAYER_INPUT, outputSchema={"type": "object", "properties": BOARD_PROPERTIES,
        "required": list(BOARD_PROPERTIES), "additionalProperties": False}),
    Tool(name="refresh_shop", description="Refresh the shop when the mask allows it. Returns the observation. Read it before another tool call. text reports success and only sections that changed.",
             inputSchema=EMPTY_INPUT, outputSchema=OBSERVATION_SCHEMA),
    Tool(name="buy_xp", description="Buy one experience increment when the mask allows it. Returns the observation. Read it before another tool call. text reports success and only sections that changed.",
             inputSchema=EMPTY_INPUT, outputSchema=OBSERVATION_SCHEMA),
    Tool(name="get_players", description="Read all eight player IDs, public health, level and final placements.",
        inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": {
            "game_id": {"type": "string"}, "players": {"type": "array", "items": {
                "type": "object", "properties": PUBLIC_PLAYER_PROPERTIES,
                "required": list(PUBLIC_PLAYER_PROPERTIES), "additionalProperties": False}}},
            "required": ["game_id", "players"], "additionalProperties": False}),
    Tool(name="equip_item", description="Equip inventory item_slot 0..9 onto an owned unit when the mask allows it. Returns the observation. Read it before another tool call. text reports success and only sections that changed.",
             inputSchema={"type": "object", "properties": {"item_slot": {"type": "integer", "minimum": 0, "maximum": 9}, "target": LOCATION_SCHEMA},
                          "required": ["item_slot", "target"], "additionalProperties": False},
             outputSchema=OBSERVATION_SCHEMA),
    Tool(name="buy_unit", description="Buy shop_slot 0..4 when the mask allows it. Returns the observation. Read it before another tool call. text reports success and only sections that changed.",
             inputSchema={"type": "object", "properties": {"shop_slot": {"type": "integer", "minimum": 0, "maximum": 4}},
                          "required": ["shop_slot"], "additionalProperties": False},
             outputSchema=OBSERVATION_SCHEMA),
    Tool(name="move_unit", description="Move an owned unit when the mask allows it. Returns the observation. Read it before another tool call. text reports success and only sections that changed.",
             inputSchema={"type": "object", "properties": {"source": LOCATION_SCHEMA, "target": LOCATION_SCHEMA},
                          "required": ["source", "target"], "additionalProperties": False},
             outputSchema=OBSERVATION_SCHEMA),
    Tool(name="sell_unit", description="Sell an owned unit when the mask allows it. Returns the observation. Read it before another tool call. text reports success and only sections that changed.",
             inputSchema={"type": "object", "properties": {"location": LOCATION_SCHEMA},
                          "required": ["location"], "additionalProperties": False},
             outputSchema=OBSERVATION_SCHEMA),
    Tool(name="get_decision",
        description="Read the current observation before choosing an action. The first read returns the full visible position, including opponent boards and traits. A later read repeats the last delivered observation.",
        inputSchema=EMPTY_INPUT, outputSchema=OBSERVATION_SCHEMA),
]


SINGLE_PLAYER_DESCRIPTIONS = {
    "end_turn": "Pass the rest of this planning phase and run this round's fight. Returns the next observation. Read it before another tool call. reward 1 means the fight was won. A lost fight ends the game with terminal true. get_last_fight shows what you fought.",
    "get_decision": "Read the current observation before choosing an action. The first read returns the full visible position. A later read repeats the last delivered observation.",
    "get_champion_pool": "Read the most copies of an exact champion ID that can remain in the pool. Subtracts your board and bench. Generated enemies use a separate pool. One star counts as 1 copy, and each further star multiplies that by 3. Shop offers stay in the pool until bought.",
}


SINGLE_PLAYER_TOOLS = [
    tool.model_copy(update={"description": SINGLE_PLAYER_DESCRIPTIONS[tool.name]})
    if tool.name in SINGLE_PLAYER_DESCRIPTIONS else tool
    for tool in TOOLS if tool.name not in {"get_players", "get_board"}
] + [
    Tool(name="get_last_fight",
         description="Read the fight that just ran: its round, kind (minion for PvE, combat for a generated board), whether you won, and the generated enemy's level, occupied board slots and active traits. Before the first fight kind is none. A PvE fight has no enemy board. This read spends nothing.",
         inputSchema=EMPTY_INPUT, outputSchema={"type": "object", "properties": LAST_FIGHT_PROPERTIES,
             "required": list(LAST_FIGHT_PROPERTIES), "additionalProperties": False}),
]


def tools_for(mode):
    return SINGLE_PLAYER_TOOLS if mode == "single_player" else TOOLS
