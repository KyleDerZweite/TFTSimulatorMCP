"""TFT_MCP_MODE=single_player starts the simulator's one-player campaign."""

import json

import jsonschema
import pytest

from support import client
from tft_mcp.errors import SessionError
from tft_mcp.session import GameSession
from tft_mcp.tools import SINGLE_PLAYER_TOOLS, TOOLS, tools_for
from tft_mcp.transport import SERVER_INSTRUCTIONS, campaign_text, instructions_for, mode_configuration


def single_player_session(tmp_path):
    session = GameSession(tmp_path / "audit.jsonl", tmp_path / "native")
    session.start_game(0, "single_player")
    return session


def last_fight_schema():
    return next(tool.outputSchema for tool in SINGLE_PLAYER_TOOLS if tool.name == "get_last_fight")


def test_mode_configuration_accepts_full_by_default_and_rejects_other_names():
    assert mode_configuration({}) == "full"
    assert mode_configuration({"TFT_MCP_MODE": ""}) == "full"
    assert mode_configuration({"TFT_MCP_MODE": "full"}) == "full"
    assert mode_configuration({"TFT_MCP_MODE": "single_player"}) == "single_player"
    with pytest.raises(ValueError, match="TFT_MCP_MODE"):
        mode_configuration({"TFT_MCP_MODE": "position"})


def test_tool_lists_differ_only_in_single_player_mode():
    assert tools_for("full") is TOOLS
    full = {tool.name for tool in TOOLS}
    single = {tool.name for tool in SINGLE_PLAYER_TOOLS}
    assert "get_last_fight" not in full
    assert single == (full - {"get_players", "get_board"}) | {"get_last_fight"}
    for tool in SINGLE_PLAYER_TOOLS:
        assert "opponent" not in tool.description


def test_single_player_session_has_one_seat_and_a_generated_fight(tmp_path):
    session = single_player_session(tmp_path)
    assert session.mode == "single_player"
    assert session.baselines == {}
    # Native reset creates eight dormant seats; only player_0 is controlled.
    assert len(session.game.native.player_manager.player_states) == 8
    assert [player["player_id"] for player in session.get_players()["players"]] == ["player_0"]
    decision = session.get_decision()
    assert decision["terminal"] is False
    assert decision["text"].startswith("round ")
    assert "opponents" not in decision["text"]
    with pytest.raises(SessionError) as error:
        session.get_board("player_1")
    assert error.value.code == "invalid_player"
    passed = session.end_turn()
    assert passed["text"].startswith("action succeeded")
    assert "opponents" not in passed["text"]
    assert passed["start_turn"] is True
    if not passed["terminal"]:
        assert session.game.actions_taken["player_0"] == 0
    records = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    started_row = next(row for row in records if row["event"] == "game_started")
    assert started_row["configuration"]["mode"] == "single_player"
    assert started_row["configuration"]["num_players"] == 1
    assert started_row["baseline"] == "generated"
    session.close_game()


def test_last_fight_reports_minion_rounds_then_the_generated_board(tmp_path):
    session = single_player_session(tmp_path)
    schema = last_fight_schema()
    opening = session.get_last_fight()
    jsonschema.validate(opening, schema)
    assert opening == {"game_id": session.game_id, "round": None, "kind": "none", "won": None, "enemy": None}
    schedule = {entry["round"]: entry for entry in session.campaign_schedule()}
    seen = []
    for _ in range(3):
        observation = session.end_turn()
        fight = session.get_last_fight()
        jsonschema.validate(fight, schema)
        seen.append(fight)
        assert fight["kind"] == schedule[fight["round"]]["kind"]
        assert fight["won"] is (observation["reward"] > 0)
        if observation["terminal"]:
            break
    assert [fight["round"] for fight in seen] == list(range(1, len(seen) + 1))
    assert all(fight["enemy"] is None for fight in seen if fight["kind"] == "minion")
    combat = next((fight for fight in seen if fight["kind"] == "combat"), None)
    if combat is not None:
        assert combat["enemy"]["level"] == schedule[combat["round"]]["enemy"]["level"]
        assert combat["enemy"]["board"]
        assert all(slot["unit"] is not None for slot in combat["enemy"]["board"])
        assert all(trait["count"] for trait in combat["enemy"]["traits"])
    before = session.get_decision()
    session.get_last_fight()
    assert session.get_decision() == before
    session.close_game()


def test_full_mode_keeps_its_instructions_and_rejects_last_fight(tmp_path):
    session = GameSession(tmp_path / "audit.jsonl", tmp_path / "native")
    session.start_game(0)
    assert instructions_for(session) == SERVER_INSTRUCTIONS
    assert session.campaign_schedule() == []
    with pytest.raises(SessionError) as error:
        session.get_last_fight()
    assert error.value.code == "invalid_input"
    session.close_game()


def test_campaign_text_comes_from_the_simulator_schedule(tmp_path):
    session = single_player_session(tmp_path)
    schedule = session.campaign_schedule()
    text = campaign_text(schedule)
    minions = [entry["round"] for entry in schedule if entry["kind"] == "minion"]
    first_combat = next(entry for entry in schedule if entry["kind"] == "combat")
    assert f"rounds 1 through {schedule[-1]['round']}" in text
    assert f"PvE minion rounds: {', '.join(map(str, minions))}." in text
    assert f"level {first_combat['enemy']['level']} from round {first_combat['round']}" in text
    assert instructions_for(session).endswith(text)
    session.close_game()


@pytest.mark.anyio
async def test_single_player_process_advertises_its_tools_and_campaign(tmp_path):
    stream = tmp_path / "model-stream.txt"
    async with client(tmp_path, TFT_MCP_MODE="single_player", TFT_MCP_STREAM_LOG=str(stream)) as sdk:
        tools = {tool.name for tool in (await sdk.list_tools()).tools}
        decision = (await sdk.call_tool("get_decision", {})).structuredContent
        fight = await sdk.call_tool("get_last_fight", {})
        hidden = [await sdk.call_tool(name, {}) for name in ("get_players", "get_board")]
        extra = await sdk.call_tool("get_last_fight", {"extra": 1})
    assert tools == {tool.name for tool in SINGLE_PLAYER_TOOLS}
    assert len(tools) == 19
    assert decision["terminal"] is False and "opponents" not in decision["text"]
    assert not fight.isError and fight.structuredContent["kind"] == "none"
    for result in hidden:
        assert result.isError and result.structuredContent["code"] == "invalid_input"
    assert extra.isError and extra.structuredContent["code"] == "invalid_input"
    transcript = stream.read_text()
    assert "A seeded single-player game already runs." in transcript
    assert "Campaign: rounds 1 through" in transcript
    assert transcript.index("initialize instructions") < transcript.index("server -> model tools/list")
    assert '"mode": "single_player"' in (tmp_path / "audit.jsonl").read_text()
