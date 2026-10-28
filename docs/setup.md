# Install and connect

Use Git, [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.x, at least 0.13.5, and a fresh external environment. `.python-version` selects the Python 3.14 line without fixing its patch release. Use `uv python upgrade 3.14` to update a managed local interpreter to the latest patch available to uv. Development and installed checks used Python 3.14.8; package metadata retains Python 3.10+ support. The pinned simulator installs automatically. Keep each installation separate from old packages sharing the `tft_mcp` import.

Run from the checkout at the revision you want to install:

```sh
mkdir -p "$HOME/.local/share/tft-simulator-mcp"
TFT_INSTALL="$(mktemp -d "$HOME/.local/share/tft-simulator-mcp/install-XXXXXXXX")"
mkdir "$TFT_INSTALL/source" "$TFT_INSTALL/host" "$TFT_INSTALL/logs"
git rev-parse HEAD > "$TFT_INSTALL/mcp-revision.txt"
git archive --output="$TFT_INSTALL/source.tar" HEAD
tar -xf "$TFT_INSTALL/source.tar" -C "$TFT_INSTALL/source"
env -u APPIMAGE UV_PROJECT_ENVIRONMENT="$TFT_INSTALL/venv" \
  uv sync --project "$TFT_INSTALL/source" --locked --no-dev --no-editable
cp "$TFT_INSTALL/source/data/set4/player-results/comps.sqlite" "$TFT_INSTALL/comps.sqlite"
git -C "$TFT_INSTALL/host" init -q
sha256sum "$TFT_INSTALL/source.tar"
```

The archive includes committed source only. Save the selected MCP revision, archive checksum and installed simulator identity separately. `uv sync --locked` checks the committed lock without updating it. `--no-editable` installs the package independently of its source tree. Consumer installation with pip remains supported, but it does not apply the development lock.

Keep TFT in its dedicated game host. Connecting the MCP starts a game, so ordinary development chats should not load it. Use per-run overrides or the host's `.codex/config.toml`; `codex mcp add` writes a user-level registration and is unsuitable for this scope.

From the host directory, inspect `codex mcp get tft --json` before registration. Reuse a correct entry. Update only the named server's launcher, arguments and TFT environment fields; preserve credentials, unrelated tables and existing per-tool restrictions. For the newly created host above, this writes an absent config. Merge into an existing file instead of replacing it:

```sh
mkdir -p "$TFT_INSTALL/host/.codex"
cat > "$TFT_INSTALL/host/.codex/config.toml" <<EOF
[mcp_servers.tft]
command = "/usr/bin/env"
args = ["-u", "APPIMAGE", "-u", "PYTHONPATH", "$TFT_INSTALL/venv/bin/tft-mcp"]

[mcp_servers.tft.env]
TFT_MCP_SEED = "0"
TFT_MCP_AUDIT_PATH = "$TFT_INSTALL/logs/audit.jsonl"
TFT_MCP_NATIVE_LOG_DIR = "$TFT_INSTALL/logs/native"
TFT_MCP_COMP_DB = "$TFT_INSTALL/comps.sqlite"
EOF
cd "$TFT_INSTALL/host"
codex mcp list --json
```

Codex loads project config only for a trusted workspace. Review the intended host's trust when first opening it. Run MCP inspection from the actual directory; Codex 0.163.0's MCP subcommands do not use `-C` for that lookup. Repeat `codex mcp list --json` in an unrelated project and confirm TFT is absent there. Remove a superseded global TFT registration only after backing it up and preserving any still-needed hosts. Existing sessions can retain their old tools and processes until reconnected.

For an authorized game, run `codex --model gpt-6-luna` from that host and ask the fresh session to play with the TFT tools. The host receives mechanics through MCP initialization instructions and tool descriptions. An actual `get_decision` call proves tool execution. Registration alone does not.

`TFT_MCP_SEED` is required, with decimal digits in `0..2147483647`. `TFT_MCP_MODE` chooses the game: `full` (the default) or `single_player`. The server starts that game when connected. Restart the server for another game or the other mode.

For single-player, add `TFT_MCP_MODE=single_player` to the host's server environment. Both modes use the same installed launcher. Keep the absolute `TFT_MCP_COMP_DB` path for the separate database.

The pinned simulator's token encoder rejects round 40 and later. Early single-player games work, but completing its 45-round campaign requires an upstream fix. Failed progression rolls back; native assertions remain enabled.

The committed database supports runtime queries. To download the raw sources separately and rebuild it with the installed commands:

```sh
"$TFT_INSTALL/venv/bin/python" -m tft_mcp.comp_download \
  --csv "$TFT_INSTALL/data/games.csv" --items "$TFT_INSTALL/data/items.json"
"$TFT_INSTALL/venv/bin/python" -m tft_mcp.comp_index \
  --csv "$TFT_INSTALL/data/games.csv" --items "$TFT_INSTALL/data/items.json" \
  --database "$TFT_INSTALL/comps.sqlite"
```

The downloader verifies pinned SHA-256 hashes. Keep raw data, database and logs outside the installation's source archive. Audit logging is required; native logs default beside the audit file. The optional transcript defaults to `model-stream.txt` beside the audit. Set `TFT_MCP_STREAM_LOG` to another path or `off`. Transcript failures leave gameplay usable. Graceful shutdown records a close; forced termination can skip that callback.

For Claude, register the same absolute launcher using `claude mcp add --scope local --transport stdio tft`, the same seed/log fields and its stable project directory. Preserve an existing registration directory and permissions. Authenticated Claude gameplay remains unverified.

For a known trusted local installation, Codex's existing `mcp_servers.tft.default_tools_approval_mode = "approve"` can allow its tools. Keep saved per-tool overrides and global policy. See [native MCP configuration](https://developers.openai.com/codex/mcp/) for current host behavior.

If startup fails, check the seed, writable log paths and interpreter. The `/usr/bin/env -u APPIMAGE` wrapper avoids interpreter interference on AppImage hosts. The launcher sets `PYTHONHASHSEED=0`.

Each game keeps its simulator log at `<TFT_MCP_NATIVE_LOG_DIR>/<game_id>/log.txt`. Earlier versions copied that directory on every action, leaving many `<game_id>-<hex>` directories. Stop the server, then merge them with `"$TFT_INSTALL/venv/bin/python" -m tft_mcp.native_logs "$TFT_INSTALL/logs/native"`. It keeps the copy the audit last recorded and removes only copies whose files are proven redundant. Divergent or unique data is preserved and reported instead. `--dry-run` prints the plan. Games without a `game_closed` audit record are skipped unless `--include-open` is given. Older audit `native_log_dir` paths then point at removed copies; the game ID still names the merged directory.

To retire this host, remove its local `[mcp_servers.tft]` table and subtables, or its per-run overrides. Retain logs separately. For developer and installed checks, see [tool-reference.md](tool-reference.md#developer-checks) and [verification.md](verification.md).
