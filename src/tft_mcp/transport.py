"""Native stdio startup and SDK stream execution for one concrete game."""

import os

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from tft_mcp.session import GameSession
from tft_mcp.tool_calls import ToolCalls


def seed_configuration(environment):
    raw = environment.get("TFT_MCP_SEED", "")
    if not raw or not raw.isascii() or not raw.isdecimal():
        raise ValueError("TFT_MCP_SEED requires decimal digits in 0..2147483647.")
    canonical = raw.lstrip("0") or "0"
    if len(canonical) > 10 or int(canonical) > 2147483647:
        raise ValueError("TFT_MCP_SEED must be in 0..2147483647.")
    return int(canonical)


SERVER_INSTRUCTIONS = (
    "A seeded game already runs. You control player_0 against seven baselines. "
    "get_decision reads your visible state. Actions return receipt and updated decision; "
    "end_turn runs combat and returns the next decision. Reads and rejected actions are free. "
    "Planning allows 14 actions, then requires end_turn. Finish when status.state is terminal "
    "and status.outcome.lobby_complete is true. Empty owned slots are omitted; indices stay exact. "
    "Board x=0..6 left to right, y=0..3 bottom to top; bench 0..8, shop 0..4, items 0..9. "
    "Rule lookups describe the installed simulator. Shutdown closes the game."
)


async def run_session(session, read_stream, write_stream):
    """Run and close a concrete session over actual SDK-provided streams."""
    server = Server("tft-mcp-server", instructions=SERVER_INSTRUCTIONS)
    calls = ToolCalls(session)
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


async def serve():
    seed = seed_configuration(os.environ)
    session = GameSession(os.environ.get("TFT_MCP_AUDIT_PATH"), os.environ.get("TFT_MCP_NATIVE_LOG_DIR"))
    with session.lifecycle_transaction():
        session.record("process_start", seed=seed)
        session.start_game(seed)
    async with stdio_server() as (read_stream, write_stream):
        await run_session(session, read_stream, write_stream)
