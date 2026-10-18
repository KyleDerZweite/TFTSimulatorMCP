"""One serialized, validated and audited MCP call path for GameSession."""

import json

import anyio
import jsonschema
from mcp.types import CallToolResult, TextContent

from tft_mcp.comp_index import MAX_CHAMPIONS, MAX_LEVEL, MAX_LIMIT
from tft_mcp.errors import SessionError
from tft_mcp.session import GameSession
from tft_mcp.stream_log import StreamLog
from tft_mcp.tools import tools_for


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
    elif name in {"get_decision", "end_turn", "refresh_shop", "buy_xp", "get_players", "get_last_fight"}:
        if arguments:
            raise SessionError("invalid_input", f"{name} takes no arguments.", {"tool": name})
    elif name == "get_board":
        validate_catalog_arguments(arguments, {"player_id"})
    elif name == "search_traits":
        validate_catalog_arguments(arguments, {"query"})
    elif name == "get_trait":
        validate_catalog_arguments(arguments, {"trait_id"}, {"trait_id"})
    elif name in {"get_champion", "get_champion_pool"}:
        validate_catalog_arguments(arguments, {"champion_id"}, {"champion_id"})
    elif name == "search_champions":
        validate_catalog_arguments(arguments, {"query", "cost", "trait_id"})

    elif name in {"search_comps_by_champions", "search_comps_by_trait"}:
        validate_comp_arguments(name, arguments)
    elif name == "search_champion_items":
        validate_champion_item_arguments(arguments)
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


def validate_comp_arguments(name, arguments):
    if name == "search_comps_by_champions":
        allowed = {"champions", "limit"}
        required = ("champions", "limit")
    else:
        allowed = {"trait", "level", "limit"}
        required = ("trait", "level", "limit")
    for field in arguments:
        if field not in allowed:
            raise SessionError("invalid_input", "Unknown argument.", {"field": field, "value": arguments[field]})
    for field in required:
        if field not in arguments:
            raise SessionError("invalid_input", "Missing required argument.", {"field": field, "value": None})
    if name == "search_comps_by_champions":
        champions = arguments["champions"]
        if type(champions) is not list or not 1 <= len(champions) <= MAX_CHAMPIONS:
            raise SessionError("invalid_input", "Invalid argument value.", {"field": "champions", "value": champions})
        for value in champions:
            if type(value) is not str or not value.strip():
                raise SessionError("invalid_input", "Invalid argument value.", {"field": "champions", "value": champions})
    else:
        trait = arguments["trait"]
        level = arguments["level"]
        if type(trait) is not str or not trait.strip():
            raise SessionError("invalid_input", "Invalid argument value.", {"field": "trait", "value": trait})
        if type(level) is not int or not 0 <= level <= MAX_LEVEL:
            raise SessionError("invalid_input", "Invalid argument value.", {"field": "level", "value": level})
    limit = arguments["limit"]
    if type(limit) is not int or not 1 <= limit <= MAX_LIMIT:
        raise SessionError("invalid_input", "Invalid argument value.", {"field": "limit", "value": limit})


def validate_champion_item_arguments(arguments):
    for field in arguments:
        if field not in {"champion", "items"}:
            raise SessionError("invalid_input", "Unknown argument.", {"field": field, "value": arguments[field]})
    if "champion" not in arguments:
        raise SessionError("invalid_input", "Missing required argument.", {"field": "champion", "value": None})
    champion = arguments["champion"]
    if type(champion) is not str or not champion.strip():
        raise SessionError("invalid_input", "Invalid argument value.", {"field": "champion", "value": champion})
    if "items" in arguments:
        items = arguments["items"]
        if type(items) is not list or len(items) > 2:
            raise SessionError("invalid_input", "Invalid argument value.", {"field": "items", "value": items})
        for value in items:
            if type(value) is not str or not value.strip():
                raise SessionError("invalid_input", "Invalid argument value.", {"field": "items", "value": items})


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

    def __init__(self, session: GameSession, stream=None):
        self.session = session
        self.stream = stream if stream is not None else StreamLog(None)
        self.tools = tools_for(session.mode)
        self.available = {tool.name: tool for tool in self.tools}
        self.lock = anyio.Lock()

    async def list_tools(self):
        self.stream.tools_listed(self.tools)
        return self.tools

    async def call_tool(self, name, arguments):
        session, available = self.session, self.available
        async with self.lock:
            self.stream.record_call(name, arguments)
            try:
                if name not in available:
                    raise SessionError("invalid_input", "Unknown tool.", {"tool": name})
                validate_arguments(name, arguments)
                with session.lifecycle_transaction():
                    session.record("tool_request", tool=name, arguments=arguments, game_id=session.game_id)
                    if name == "get_decision":
                        result = session.get_decision()
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
                    elif name == "get_board":
                        result = session.get_board(**arguments)
                    elif name == "get_last_fight":
                        result = session.get_last_fight()
                    elif name == "search_traits":
                        result = session.search_traits(**arguments)
                    elif name == "get_trait":
                        result = session.get_trait(**arguments)
                    elif name == "get_champion":
                        result = session.get_champion(**arguments)
                    elif name == "get_champion_pool":
                        result = session.get_champion_pool(**arguments)
                    elif name == "search_champions":
                        result = session.search_champions(**arguments)
                    elif name == "search_comps_by_champions":
                        result = session.search_comps_by_champions(**arguments)
                    elif name == "search_comps_by_trait":
                        result = session.search_comps_by_trait(**arguments)
                    elif name == "search_champion_items":
                        result = session.search_champion_items(**arguments)

                    elif name == "search_items":
                        result = session.search_items(**arguments)
                    elif name == "get_item":
                        result = session.get_item(arguments["item_id"])
                    else:
                        raise SessionError("internal_error", "Registered tool has no session operation.", {"tool": name})
                    schema = available[name].outputSchema
                    try:
                        jsonschema.validate(result, schema)
                    except jsonschema.ValidationError as error:
                        raise SessionError("internal_error", "Tool output does not match its schema.", {
                            "tool": name, "path": list(error.absolute_path), "error": error.message,
                        }) from error
                    session.record("tool_result", tool=name, result=result, is_error=False)
            except SessionError as error:
                result = error.result()
            except Exception as error:
                result = SessionError("internal_error", "Unexpected server failure.", {"error": str(error)}).result()
            else:
                self.stream.record_result(name, result)
                return result
            try:
                session.record("tool_error", tool=name, arguments=arguments, result=result, is_error=True)
            except SessionError as log_error:
                result = log_error.result()
            returned = CallToolResult(content=[TextContent(type="text", text=json.dumps(result))],
                                      structuredContent=result, isError=True)
            self.stream.record_result(name, returned)
            return returned
