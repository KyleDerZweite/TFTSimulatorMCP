"""Native stdio startup and SDK stream execution for one concrete game."""

import os

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from tft_mcp.session import GameSession
from tft_mcp.tool_calls import ToolCalls


def profile_configuration(environment):
    profile = environment.get("TFT_MCP_PROFILE", "default")
    if profile not in {"default", "compact"}:
        raise ValueError("TFT_MCP_PROFILE must be default or compact.")
    seed = None
    if profile == "compact":
        raw = environment.get("TFT_MCP_SEED", "")
        if not raw or not raw.isascii() or not raw.isdecimal():
            raise ValueError("Compact profile requires TFT_MCP_SEED as decimal digits in 0..2147483647.")
        canonical = raw.lstrip("0") or "0"
        if len(canonical) > 10 or int(canonical) > 2147483647:
            raise ValueError("TFT_MCP_SEED must be in 0..2147483647.")
        seed = int(canonical)
    return profile, seed


def server_instructions(profile):
    lifecycle_instruction = (
        "Compact process: a seeded game already runs and closes at shutdown. Actions return receipt and decision; "
        "end_turn returns the next decision directly. " if profile == "compact" else
        "Default process: starts idle. Call start_game with an explicit seed before inspecting a game. "
    )
    instructions = lifecycle_instruction + (
        "Control player_0 against seven baselines. Read get_decision and use actual post-action observations. "
        "Reads and rejections are free; planning allows 14 actions. Call end_turn to run combat. "
        "Continue until status.state is terminal and outcome.lobby_complete is true. "
        "After controlled elimination, baselines finish the remaining lobby automatically. "
        "Missing owned board, bench and inventory slots are empty; indices stay exact. "
        "No fixed duration or current live TFT rules are assumed. Query installed definitions as needed. "
        "Board x=0..6 left to right, y=0..3 bottom to top; bench 0..8, shop 0..4, items 0..9."
    )
    return instructions


async def run_session(session, profile, read_stream, write_stream):
    """Run and close a concrete session over actual SDK-provided streams."""
    server = Server("tft-mcp-server", instructions=server_instructions(profile))
    calls = ToolCalls(session, profile)
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
    profile, seed = profile_configuration(os.environ)
    session = GameSession(os.environ.get("TFT_MCP_AUDIT_PATH"), os.environ.get("TFT_MCP_NATIVE_LOG_DIR"))
    if profile == "compact":
        with session.lifecycle_transaction():
            session.record("profile_start", profile=profile, seed=seed)
            session.start_game(seed)
    async with stdio_server() as (read_stream, write_stream):
        await run_session(session, profile, read_stream, write_stream)
