"""One serialized, validated and audited MCP call path for GameSession."""

import json

import anyio
import jsonschema
from mcp.types import CallToolResult, TextContent

from tft_mcp.errors import SessionError
from tft_mcp.session import GameSession
from tft_mcp.tools import ACTION_TOOLS, profile_tools


def validate_arguments(name, arguments):
    if name == "equip_item":
        from tft_mcp.equipment import validate_equip_arguments
        validate_equip_arguments(arguments)
    elif name == "buy_unit":
        from tft_mcp.action_helpers import validate_buy_arguments
        validate_buy_arguments(arguments)
    elif name == "move_unit":
        from tft_mcp.movement import validate_move_arguments
        validate_move_arguments(arguments)
    elif name == "sell_unit":
        from tft_mcp.action_helpers import validate_sell_arguments
        validate_sell_arguments(arguments)
    elif name == "start_game":
        if set(arguments) != {"seed"} or type(arguments.get("seed")) is not int or not 0 <= arguments["seed"] <= 2147483647:
            raise SessionError("invalid_input", "start_game requires only seed, an integer from 0 through 2147483647.",
                               {"tool": name})
    elif name in {"get_decision", "get_game_status", "close_game", "end_turn", "refresh_shop", "buy_xp", "get_bench", "get_shop", "get_items", "get_economy", "get_round", "get_players"}:
        if arguments:
            raise SessionError("invalid_input", f"{name} takes no arguments.", {"tool": name})
    elif name in {"get_board", "get_traits"}:
        validate_catalog_arguments(arguments, {"player_id"})
    elif name == "search_traits":
        validate_catalog_arguments(arguments, {"query"})
    elif name in {"get_trait", "get_trait_champions"}:
        validate_catalog_arguments(arguments, {"trait_id"}, {"trait_id"})
    elif name == "get_champion":
        validate_catalog_arguments(arguments, {"champion_id"}, {"champion_id"})
    elif name == "search_champions":
        validate_catalog_arguments(arguments, {"query", "cost", "trait_id"})

    elif name in {"search_items", "get_item"}:
        allowed = {"query", "kind"} if name == "search_items" else {"item_id"}
        for field in arguments:
            if field not in allowed:
                raise SessionError("invalid_input", "Unknown argument.", {"field": field, "value": arguments[field]})
        if name == "get_item" and "item_id" not in arguments:
            raise SessionError("invalid_input", "item_id is required.", {"field": "item_id", "value": None})
        for field, value in arguments.items():
            if type(value) is not str or (field == "kind" and value not in {"component", "equipment", "consumable"}):
                raise SessionError("invalid_input", f"Invalid {field}.", {"field": field, "value": value})
    else:
        raise SessionError("invalid_input", "Unknown tool.", {"tool": name})


def validate_catalog_arguments(arguments, allowed, required=()):
    for field in sorted(set(arguments) - allowed):
        raise SessionError("invalid_input", "Unknown argument.", {"field": field, "value": arguments[field]})
    for field in sorted(required):
        if field not in arguments:
            raise SessionError("invalid_input", "Missing required argument.", {"field": field, "value": None})
    for field, value in arguments.items():
        valid = type(value) is int and 1 <= value <= 5 if field == "cost" else type(value) is str
        if not valid:
            raise SessionError("invalid_input", "Invalid argument value.", {"field": field, "value": value})


class ToolCalls:
    """Own protocol serialization outside the transaction's copied game graph."""

    def __init__(self, session: GameSession, profile):
        self.session = session
        self.profile = profile
        self.tools = profile_tools(profile)
        self.available = {tool.name: tool for tool in self.tools}
        self.lock = anyio.Lock()

    async def list_tools(self):
        return self.tools

    async def call_tool(self, name, arguments):
        session, profile, available = self.session, self.profile, self.available
        async with self.lock:
            try:
                if name not in available:
                    raise SessionError("invalid_input", "Tool is unavailable in this profile.", {"tool": name, "profile": profile})
                validate_arguments(name, arguments)
                with session.lifecycle_transaction():
                    session.record("tool_request", tool=name, arguments=arguments, game_id=session.game_id)
                    if name == "start_game":
                        result = session.start_game(arguments["seed"])
                    elif name == "get_decision":
                        result = session.get_decision()
                    elif name == "get_game_status":
                        result = session.get_game_status()
                    elif name == "refresh_shop":
                        result = session.refresh_shop(**arguments)
                    elif name == "buy_xp":
                        result = session.buy_xp(**arguments)
                    elif name == "equip_item":
                        result = session.equip_item(**arguments)
                    elif name == "buy_unit":
                        result = session.buy_unit(**arguments)
                    elif name == "move_unit":
                        result = session.move_unit(**arguments)
                    elif name == "sell_unit":
                        result = session.sell_unit(**arguments)
                    elif name == "end_turn":
                        result = session.end_turn()

                    elif name == "get_players":
                        result = session.get_players()
                    elif name == "get_round":
                        result = session.get_round()
                    elif name == "get_traits":
                        result = session.get_traits(**arguments)
                    elif name == "get_economy":
                        result = session.get_economy()
                    elif name == "get_items":
                        result = session.get_items()
                    elif name == "get_shop":
                        result = session.get_shop()
                    elif name == "get_bench":
                        result = session.get_bench()
                    elif name == "get_board":
                        result = session.get_board(**arguments)
                    elif name == "search_traits":
                        result = session.search_traits(**arguments)
                    elif name == "get_trait":
                        result = session.get_trait(**arguments)
                    elif name == "get_trait_champions":
                        result = session.get_trait_champions(**arguments)
                    elif name == "get_champion":
                        result = session.get_champion(**arguments)
                    elif name == "search_champions":
                        result = session.search_champions(**arguments)

                    elif name == "search_items":
                        result = session.search_items(**arguments)
                    elif name == "get_item":
                        result = session.get_item(arguments["item_id"])
                    elif name == "close_game":
                        result = session.close_game()
                    else:
                        raise SessionError("internal_error", "Registered tool has no session operation.", {"tool": name})
                    if profile == "compact" and name in ACTION_TOOLS:
                        decision = session.get_decision()
                        result = decision if name == "end_turn" else {"receipt": result, "decision": decision}
                    schema = available[name].outputSchema
                    try:
                        jsonschema.validate(result, schema)
                    except jsonschema.ValidationError as error:
                        raise SessionError("internal_error", "Tool output does not match its schema.", {
                            "tool": name, "path": list(error.absolute_path), "error": error.message,
                        }) from error
                    session.record("tool_result", tool=name, result=result, is_error=False)
                return result
            except SessionError as error:
                result = error.result()
            except Exception as error:
                result = SessionError("internal_error", "Unexpected server failure.", {"error": str(error)}).result()
            try:
                session.record("tool_error", tool=name, arguments=arguments, result=result, is_error=True)
            except SessionError as log_error:
                result = log_error.result()
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                                  structuredContent=result, isError=True)
