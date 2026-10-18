"""Append-only transcript of the model-facing MCP boundary."""

from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import sys
import threading


SCOPE = (
    "scope: initialize instructions, tools/list payloads, tool calls, and tool results "
    "returned to the host. User messages, assistant prose, skills, and the host system "
    "prompt stay with the host."
)


class StreamLog:
    """Write one text file outside the audit transaction. Failures do not affect the game."""

    def __init__(self, path):
        self.path = Path(path).expanduser().resolve() if path else None
        self.server_id = None
        self.sequence = 0
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls, environment):
        raw = environment.get("TFT_MCP_STREAM_LOG")
        if raw is not None:
            raw = raw.strip()
        if raw == "off":
            return cls(None)
        if raw:
            return cls(raw)
        audit = environment.get("TFT_MCP_AUDIT_PATH")
        if audit is None or not str(audit).strip():
            return cls(None)
        return cls(Path(str(audit).strip()).expanduser().resolve().with_name("model-stream.txt"))

    def open_session(self, seed, server_id):
        self.server_id = server_id
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self._disable(error)
            return
        self._safe("session", lambda: f"seed: {seed}\npath: {self.path}\n{SCOPE}")

    def instructions(self, text):
        self._safe("server -> model initialize instructions", lambda: text)

    def note(self, text):
        self._safe("server note", lambda: text)

    def tools_listed(self, tools):
        self._safe("server -> model tools/list", lambda: _tools_body(tools))

    def record_call(self, name, arguments):
        self._safe("model -> server tools/call", lambda: _call_body(name, arguments))

    def record_result(self, name, result):
        self._safe("server -> model tools/call result", lambda: _result_body(name, result))

    def _safe(self, title, body):
        if self.path is None:
            return
        try:
            self._append(title, body())
        except Exception as error:
            self._disable(error)

    def _append(self, title, body):
        if self.path is None:
            return
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._lock:
            if self.path is None:
                return
            self.sequence += 1
            text = (
                f"========== {self.sequence} {title} ==========\n"
                f"time: {stamp}\n"
                f"server_id: {self.server_id}\n"
                f"{body.rstrip()}\n\n"
            )
            with self.path.open("a", encoding="utf-8") as stream:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
                try:
                    stream.write(text)
                    stream.flush()
                    os.fsync(stream.fileno())
                finally:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def _disable(self, error):
        path = self.path
        self.path = None
        if path is None:
            return
        try:
            print(f"tft-mcp model stream log unavailable: {path}: {error}", file=sys.stderr, flush=True)
        except Exception:
            return


def _tools_body(tools):
    tools = list(tools)
    blocks = [f"count: {len(tools)}"]
    for tool in tools:
        blocks.append(
            f"--- {tool.name} ---\n"
            f"description: {tool.description}\n"
            f"inputSchema:\n{json.dumps(tool.inputSchema, indent=2)}\n"
            f"outputSchema:\n{json.dumps(tool.outputSchema, indent=2)}"
        )
    return "\n".join(blocks)


def _call_body(name, arguments):
    payload = {} if arguments is None else arguments
    return f"tool: {name}\narguments:\n{json.dumps(payload, indent=2, default=str)}"


def _result_body(name, result):
    structured = result if isinstance(result, dict) else getattr(result, "structuredContent", None)
    lines = [f"tool: {name}", f"isError: {str(_is_error(result)).lower()}"]
    if isinstance(structured, dict) and isinstance(structured.get("text"), str):
        lines.append("simulator text:")
        lines.append(structured["text"])
    lines.append("content:")
    lines.append(_content_text(structured, result))
    return "\n".join(lines)


def _is_error(result):
    if isinstance(result, dict):
        return False
    return bool(getattr(result, "isError", False))


def _content_text(structured, result):
    if isinstance(structured, (dict, list)):
        return json.dumps(structured, indent=2)
    content = getattr(result, "content", None)
    if content:
        texts = [block.text for block in content if getattr(block, "type", None) == "text" and hasattr(block, "text")]
        if any(texts):
            return "\n".join(texts)
    return json.dumps(structured, indent=2, default=str)
