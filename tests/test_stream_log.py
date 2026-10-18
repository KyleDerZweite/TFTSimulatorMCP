import json
from types import SimpleNamespace

import pytest

from support import client
from tft_mcp.stream_log import StreamLog


def _tool(name="get_decision"):
    return SimpleNamespace(name=name, description=f"Read {name}.",
                           inputSchema={"type": "object"}, outputSchema={"type": "object"})


def test_stream_log_path_follows_the_environment(tmp_path):
    audit = tmp_path / "logs" / "audit.jsonl"
    default = StreamLog.from_environment({"TFT_MCP_AUDIT_PATH": str(audit)})
    assert default.path == audit.resolve().with_name("model-stream.txt")
    explicit = tmp_path / "custom.txt"
    assert StreamLog.from_environment({"TFT_MCP_STREAM_LOG": str(explicit)}).path == explicit.resolve()
    assert StreamLog.from_environment({"TFT_MCP_STREAM_LOG": "off", "TFT_MCP_AUDIT_PATH": str(audit)}).path is None
    assert StreamLog.from_environment({"TFT_MCP_STREAM_LOG": "  ", "TFT_MCP_AUDIT_PATH": str(audit)}).path == default.path
    assert StreamLog.from_environment({}).path is None


def test_stream_log_appends_the_model_boundary(tmp_path):
    path = tmp_path / "model-stream.txt"
    log = StreamLog(path)
    log.open_session(0, "server-a")
    log.instructions("A seeded game already runs.")
    log.note("game started")
    log.tools_listed([_tool()])
    log.record_call("get_decision", {})
    log.record_result("get_decision", {"reward": 0.0, "text": "round 1\nboard", "mask": []})
    error = SimpleNamespace(isError=True, structuredContent={"code": "invalid_input", "message": "bad", "details": {}},
                            content=[])
    log.record_call("get_decision", {"extra": 1})
    log.record_result("get_decision", error)
    first = path.read_text()
    StreamLog(path).open_session(1, "server-b")
    text = path.read_text()
    assert text.startswith(first)
    assert first.index("server -> model initialize instructions") < first.index("server note")
    assert first.index("server note") < first.index("server -> model tools/list")
    assert first.index("server -> model tools/list") < first.index("model -> server tools/call")
    assert first.index("model -> server tools/call") < first.index("simulator text:\nround 1\nboard")
    assert first.index("simulator text:\nround 1\nboard") < first.index('"extra": 1')
    assert "isError: false" in first and "isError: true" in first and "invalid_input" in first
    assert "server-a" in first and "server-b" in text
    assert "Read get_decision." in first


def test_disabled_stream_log_writes_nothing(tmp_path):
    log = StreamLog.from_environment({"TFT_MCP_STREAM_LOG": "off", "TFT_MCP_AUDIT_PATH": str(tmp_path / "audit.jsonl")})
    log.open_session(0, "server")
    log.instructions("hidden")
    log.record_call("get_decision", {})
    log.record_result("get_decision", {"text": "round 1\n"})
    assert list(tmp_path.iterdir()) == []


def test_unwritable_stream_log_disables_itself(tmp_path, capsys):
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    log = StreamLog(blocked)
    log.open_session(0, "server")
    log.record_call("get_decision", {})
    assert log.path is None
    assert "unavailable" in capsys.readouterr().err
    assert capsys.readouterr().err == ""


@pytest.mark.anyio
async def test_server_writes_instructions_catalog_calls_and_results(tmp_path):
    path = tmp_path / "model-stream.txt"
    async with client(tmp_path, TFT_MCP_STREAM_LOG=str(path)) as sdk:
        await sdk.list_tools()
        decision = await sdk.call_tool("get_decision", {})
        failed = await sdk.call_tool("get_decision", {"extra": 1})
    assert not decision.isError and decision.structuredContent["text"].startswith("round 1\n")
    assert failed.isError and failed.structuredContent["code"] == "invalid_input"
    text = path.read_text()
    assert text.index("server -> model initialize instructions") < text.index("server -> model tools/list")
    assert text.index("server -> model tools/list") < text.index("model -> server tools/call")
    assert text.index("model -> server tools/call") < text.index("simulator text:\n" + decision.structuredContent["text"])
    assert "A seeded game already runs." in text
    assert "Read the current observation before choosing an action." in text
    assert '"extra": 1' in text and "invalid_input" in text and "isError: true" in text
    records = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert any(row["event"] == "tool_result" and row["tool"] == "get_decision" for row in records)


@pytest.mark.anyio
async def test_stream_log_off_leaves_the_audit_as_the_only_transcript(tmp_path):
    async with client(tmp_path) as sdk:
        assert not (await sdk.call_tool("get_decision", {})).isError
    assert not (tmp_path / "model-stream.txt").exists()
    assert (tmp_path / "audit.jsonl").exists()
