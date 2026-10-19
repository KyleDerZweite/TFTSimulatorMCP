import builtins
import importlib.util
import json
from types import SimpleNamespace

import pytest

from support import client
from tft_mcp.stream_log import StreamLog
import tft_mcp.stream_log as stream_log


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
    log.tools_listed([SimpleNamespace(name="get_decision", description="Read get_decision.",
                                    inputSchema={"type": "object"}, outputSchema={"type": "object"})])
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


@pytest.mark.parametrize('destination', ['directory', 'symlink-loop'])
def test_unusable_stream_log_disables_itself(tmp_path, capsys, destination):
    blocked = tmp_path / "blocked"
    if destination == 'directory':
        blocked.mkdir()
    else:
        blocked.symlink_to(blocked)
    log = StreamLog.from_environment({'TFT_MCP_STREAM_LOG': str(blocked)})
    log.open_session(0, "server")
    log.record_call("get_decision", {})
    assert log.path is None
    assert blocked.is_dir() if destination == 'directory' else blocked.is_symlink()
    assert capsys.readouterr().err.count('unavailable') == 1


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


@pytest.fixture
def protected_destination(tmp_path, request):
    collision = request.param
    audit = tmp_path / ('model-stream.txt' if collision == 'default-audit-name' else 'audit.jsonl')
    audit.write_bytes(b'{"retained": true}\n')
    native = tmp_path / 'native'
    native.mkdir()
    native_log = native / 'game' / 'log.txt'
    native_log.parent.mkdir()
    native_log.write_bytes(b'native evidence\x00')
    retained = {audit: audit.read_bytes(), native_log: native_log.read_bytes()}
    path = tmp_path / 'stream.txt'
    environment = {'TFT_MCP_AUDIT_PATH': str(audit)}
    if collision == 'audit':
        path = audit
    elif collision == 'default-audit-name':
        path = ''
    elif collision == 'audit-symlink':
        path.symlink_to(audit)
    elif collision == 'audit-hardlink':
        path.hardlink_to(audit)
    elif collision == 'native':
        path = native / 'future-game' / 'transcript.txt'
    elif collision == 'native-file':
        path = native_log
    elif collision == 'native-root':
        path = native
    elif collision == 'native-symlink':
        path.symlink_to(native_log)
    elif collision == 'native-hardlink':
        path.hardlink_to(native_log)
    elif collision == 'native-symlink-escape':
        external = tmp_path / 'outside-native.txt'
        external.write_bytes(b'escaped native evidence')
        retained[external] = external.read_bytes()
        path = native / 'escaped.txt'
        path.symlink_to(external)
    elif collision == 'default-native-root':
        environment['TFT_MCP_NATIVE_LOG_DIR'] = str(tmp_path)
        path = ''
    environment['TFT_MCP_STREAM_LOG'] = str(path)
    return environment, audit, retained


@pytest.mark.parametrize('protected_destination', [
    'audit', 'default-audit-name', 'audit-symlink', 'audit-hardlink',
    'native', 'native-root', 'native-symlink', 'native-hardlink',
    'native-symlink-escape', 'default-native-root',
], indirect=True)
def test_stream_log_rejects_protected_destinations_before_writing(tmp_path, capsys, protected_destination):
    environment, _, retained = protected_destination
    log = StreamLog.from_environment(environment)
    log.open_session(0, 'server')
    log.record_call('get_decision', {})
    assert log.path is None
    assert {path: path.read_bytes() for path in retained} == retained
    assert not (tmp_path / 'native' / 'future-game').exists()
    assert capsys.readouterr().err.count('unavailable') == 1


def test_stream_log_rechecks_aliases_created_after_configuration(tmp_path):
    audit = tmp_path / 'audit.jsonl'
    audit.write_bytes(b'audit evidence')
    path = tmp_path / 'stream.txt'
    log = StreamLog.from_environment({'TFT_MCP_AUDIT_PATH': str(audit), 'TFT_MCP_STREAM_LOG': str(path)})
    path.symlink_to(audit)
    log.open_session(0, 'server')
    assert log.path is None
    assert audit.read_bytes() == b'audit evidence'


def test_stream_log_imports_and_disables_without_fcntl(tmp_path, monkeypatch, capsys):
    real_import = builtins.__import__

    def without_fcntl(name, *args, **kwargs):
        if name == 'fcntl':
            raise ImportError('not supported on this platform')
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', without_fcntl)
    spec = importlib.util.spec_from_file_location('stream_log_without_fcntl', stream_log.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    log = module.StreamLog(tmp_path / 'new-directory' / 'stream.txt')
    log.open_session(0, 'server')
    log.record_call('get_decision', {})
    assert log.path is None
    assert list(tmp_path.iterdir()) == []
    assert 'file locking is unavailable' in capsys.readouterr().err


@pytest.mark.anyio
@pytest.mark.parametrize('protected_destination', ['audit', 'default-audit-name', 'native-file', 'native-symlink'],
                         indirect=True)
async def test_colliding_transcript_leaves_gameplay_and_retained_logs_usable(tmp_path, protected_destination):
    environment, audit, retained = protected_destination
    async with client(tmp_path, **environment) as sdk:
        assert not (await sdk.call_tool('get_decision', {})).isError
        assert not (await sdk.call_tool('end_turn', {})).isError
    assert audit.read_bytes().startswith(retained[audit])
    records = [json.loads(line) for line in audit.read_text().splitlines()]
    assert any(row.get('event') == 'tool_result' and row['tool'] == 'end_turn' for row in records)
    assert all(path.read_bytes() == content for path, content in retained.items() if path != audit)
