"""Native stdio startup and SDK stream execution for one concrete game."""

import os

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from tft_mcp.session import GameSession
from tft_mcp.stream_log import StreamLog
from tft_mcp.tool_calls import ToolCalls


def seed_configuration(environment):
    raw = environment.get("TFT_MCP_SEED", "")
    if not raw or not raw.isascii() or not raw.isdecimal():
        raise ValueError("TFT_MCP_SEED requires decimal digits in 0..2147483647.")
    canonical = raw.lstrip("0") or "0"
    if len(canonical) > 10 or int(canonical) > 2147483647:
        raise ValueError("TFT_MCP_SEED must be in 0..2147483647.")
    return int(canonical)


def mode_configuration(environment):
    raw = environment.get("TFT_MCP_MODE", "full")
    if raw in {"", "full", "single_player"}:
        return "single_player" if raw == "single_player" else "full"
    raise ValueError("TFT_MCP_MODE must be full or single_player.")


SERVER_INSTRUCTIONS = (
    "A seeded game already runs. You control player_0 against seven baselines. "
    "get_decision returns the observation: reward, start_turn, terminal, mask, and text. "
    "text is the simulator llm observation. The first read lists the visible position, including opponent boards and traits. "
    "Call one action tool, then wait for its observation before any other tool call. "
    "text then starts with action succeeded and includes only sections that changed. "
    "A new planning phase also includes changed economy and any changed opponent boards and traits. "
    "A masked action failed and changed nothing. Planning ends at end_turn or the simulator's 15-action limit. "
    "Finish when terminal is true. "
    "Board x=0..6 left to right, y=0..3 bottom to top; bench 0..8, shop 0..4, items 0..9. "
    "Rule lookups describe the installed simulator. Shutdown closes the game."
)

SINGLE_PLAYER_INSTRUCTIONS = (
    "A seeded single-player game already runs. You control player_0. "
    "There are no baseline opponents. Each planning round ends in one fight: a PvE minion round or a generated enemy board. "
    "Losing any fight, including a PvE round, ends the game. Health never changes. "
    "Winning the last round finishes the campaign with placement 1. "
    "get_decision returns the observation: reward, start_turn, terminal, mask, and text. "
    "text is the simulator llm observation. The first read lists the visible position. "
    "Call one action tool, then wait for its observation before any other tool call. "
    "text then starts with action succeeded and includes only sections that changed. "
    "A new planning phase also includes changed economy. reward is the change in native cumulative reward: "
    "1 means a fight was won, -1 means a fight was lost, and 0 means no fight ran. "
    "get_last_fight shows the enemy board, traits and result of the fight that just ran. "
    "A masked action failed and changed nothing. Planning ends at end_turn or the simulator's 15-action limit. "
    "Finish when terminal is true. "
    "Board x=0..6 left to right, y=0..3 bottom to top; bench 0..8, shop 0..4, items 0..9. "
    "Rule lookups describe the installed simulator. Shutdown closes the game."
)


def _changes(entries, value):
    """Each (value, first round) where value differs from the previous generated fight."""
    changes, previous = [], object()
    for entry in entries:
        current = value(entry["enemy"])
        if current != previous:
            changes.append((current, entry["round"]))
            previous = current
    return changes


def _first_round(entries, test):
    return next((entry["round"] for entry in entries if test(entry["enemy"])), None)


def campaign_text(schedule):
    if not schedule:
        return ""
    last = schedule[-1]["round"]
    minions = [entry["round"] for entry in schedule if entry["kind"] == "minion"]
    carousels = [entry["round"] for entry in schedule if entry["carousel"]]
    combats = [entry for entry in schedule if entry["kind"] == "combat"]
    parts = [f"Campaign: rounds 1 through {last}, one fight each. "
             f"PvE minion rounds: {', '.join(map(str, minions))}. "
             f"A carousel runs before the fight in rounds {', '.join(map(str, carousels))}. "
             "Every other round fights a generated board."]
    levels = "; ".join(f"level {level} from round {start}" for level, start in _changes(combats, lambda e: e["level"]))
    parts.append(f"Enemy level: {levels}.")
    varies = _first_round(combats, lambda e: e["level_varies"])
    if varies is not None:
        parts.append(f"From round {varies} the enemy level varies by up to 2, capped at 9.")
    costs = "; ".join(f"{'any cost' if cost is None else f'up to {cost}-cost'} from round {start}"
                      for cost, start in _changes(combats, lambda e: e["max_cost"]))
    parts.append(f"Enemy units: {costs}.")
    for label, test in (("2-star units", lambda e: e["two_star_chance"] > 0),
                        ("3-star units", lambda e: e["three_star_chance"] > 0),
                        ("Chosen units", lambda e: e["chosen"])):
        start = _first_round(combats, test)
        if start is not None:
            parts.append(f"{label} can appear from round {start}.")
    items, most = [], 0
    for entry in combats:
        count = entry["enemy"]["items_per_unit"]
        if count > most:
            items.append(f"{count} from round {entry['round']}")
            most = count
    if items:
        parts.append(f"Base completed items per enemy unit reach {'; '.join(items)}.")
    varies = _first_round(combats, lambda e: e["items_vary"])
    if varies is not None:
        parts.append(f"From round {varies} each enemy's item count varies by up to 1 from the base, clipped to 0 through 3.")
    return " ".join(parts)


def instructions_for(session):
    if session.mode == "single_player":
        return SINGLE_PLAYER_INSTRUCTIONS + " " + campaign_text(session.campaign_schedule())
    return SERVER_INSTRUCTIONS


async def run_session(session, read_stream, write_stream, stream=None):
    """Run and close a concrete session over actual SDK-provided streams."""
    if stream is None:
        stream = StreamLog(None)
    server = Server("tft-mcp-server", instructions=instructions_for(session))
    calls = ToolCalls(session, stream)
    server.list_tools()(calls.list_tools)
    server.call_tool(validate_input=False)(calls.call_tool)
    try:
        await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        try:
            session.close_game()
        except Exception:
            # Shutdown cannot alter returned receipts or write to protocol stdout.
            pass
        stream.note("stdio closed")


async def serve():
    seed = seed_configuration(os.environ)
    mode = mode_configuration(os.environ)
    stream = StreamLog.from_environment(os.environ)
    session = GameSession(os.environ.get("TFT_MCP_AUDIT_PATH"), os.environ.get("TFT_MCP_NATIVE_LOG_DIR"))
    stream.open_session(seed, session.server_id)
    try:
        with session.lifecycle_transaction():
            session.record("process_start", seed=seed, mode=mode)
            session.start_game(seed, mode)
    except Exception as error:
        stream.note(f"startup failed: {error}")
        raise
    stream.instructions(instructions_for(session))
    stream.note("game started")
    async with stdio_server() as (read_stream, write_stream):
        await run_session(session, read_stream, write_stream, stream)
