# Install and connect

Use Python 3.10+, Git and a fresh external environment. The pinned simulator installs automatically. Keep each installation separate from old packages sharing the `tft_mcp` import.

Run from the checkout at the revision you want to install:

```sh
mkdir -p "$HOME/.local/share/tft-simulator-mcp"
TFT_INSTALL="$(mktemp -d "$HOME/.local/share/tft-simulator-mcp/install-XXXXXXXX")"
mkdir "$TFT_INSTALL/source" "$TFT_INSTALL/host" "$TFT_INSTALL/logs"
git rev-parse HEAD > "$TFT_INSTALL/mcp-revision.txt"
git archive --output="$TFT_INSTALL/source.tar" HEAD
tar -xf "$TFT_INSTALL/source.tar" -C "$TFT_INSTALL/source"
env -u APPIMAGE python3 -m venv "$TFT_INSTALL/venv"
env -u APPIMAGE "$TFT_INSTALL/venv/bin/python" -m pip install "$TFT_INSTALL/source[dev]"
cp -R "$TFT_INSTALL/source/.agents" "$TFT_INSTALL/host/.agents"
git -C "$TFT_INSTALL/host" init -q
sha256sum "$TFT_INSTALL/source.tar"
```

The archive includes committed source only. Save the selected MCP revision, archive checksum and installed simulator identity separately.

Inspect `codex mcp get tft --json` before registration. Reuse a correct entry. Update only the named server's launcher, arguments and TFT environment fields; preserve credentials, global policies and existing per-tool restrictions. These commands add an absent entry:

```sh
codex mcp add tft --env TFT_MCP_SEED=0 \
  --env "TFT_MCP_AUDIT_PATH=$TFT_INSTALL/logs/audit.jsonl" \
  --env "TFT_MCP_NATIVE_LOG_DIR=$TFT_INSTALL/logs/native" \
  -- /usr/bin/env -u APPIMAGE -u PYTHONPATH "$TFT_INSTALL/venv/bin/tft-mcp"
cd "$TFT_INSTALL/host"
codex --model gpt-6-luna
```

Ask the fresh session to use `$tft-mcp` to play a game. An actual `get_decision` call proves tool execution. Registration alone does not. The repository skill is available automatically when Codex opens this checkout; the installation copies it into the dedicated host directory.

`TFT_MCP_SEED` is required, with decimal digits in `0..2147483647`. The server starts a game when connected. Restart the server for another game. Audit logging is required; native logs default beside the audit file. Keep host and SDK test logs separate. Graceful shutdown records a close; forced host termination can skip that callback.

For Claude, register the same absolute launcher using `claude mcp add --scope local --transport stdio tft`, the same seed/log fields and its stable project directory. Preserve an existing registration directory and permissions. Authenticated Claude gameplay remains unverified.

For a known trusted local installation, Codex's existing `mcp_servers.tft.default_tools_approval_mode = "approve"` can allow its tools. Keep saved per-tool overrides and global policy. See [native MCP configuration](https://developers.openai.com/codex/mcp/) for current host behavior.

If startup fails, check the seed, writable log paths and interpreter. The `/usr/bin/env -u APPIMAGE` wrapper avoids interpreter interference on AppImage hosts. The launcher sets `PYTHONHASHSEED=0`.

Remove only the named entry with `codex mcp remove tft`. Retain logs separately. For developer and installed checks, see [tool-reference.md](tool-reference.md#developer-checks) and [verification.md](verification.md).
