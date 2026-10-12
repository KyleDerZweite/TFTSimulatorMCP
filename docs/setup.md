# Install and connect TFTSimulatorMCP

Use [SETUP_PROMPT.md](../SETUP_PROMPT.md) for agent-assisted setup, or follow this manual procedure. Setup checks idle tools without starting a game. Gameplay uses the separate [DEFAULT_GAME_PROMPT.md](../DEFAULT_GAME_PROMPT.md).

## Install a pinned revision

Use Python 3.10 or newer and a fresh external environment. The old `tft-mcp-server` and `tftmuzero-mcp` distributions share the `tft_mcp` import and `tft-mcp` launcher, so do not mix these packages in an existing environment. No simulator checkout, GPU or model-hosting dependencies are required. Pip installs the unchanged simulator automatically from its pinned Git dependency; Git must be available. This installation makes no promise about a PyPI simulator release.

Clone the repository, or use an existing checkout:

```sh
git clone https://github.com/KyleDerZweite/TFTSimulatorMCP.git
cd TFTSimulatorMCP
```

Run the following commands from that checkout. The commands select its current full Git HEAD and print that revision. To choose another release or reviewed commit, check out that revision first. Uncommitted changes are excluded from the archive.

Choose a new absolute installation path for each revision. The procedure refuses an existing path, so repeated setup cannot overwrite an archive or environment. Reuse an accepted installation when it already has the intended revision. Archive the selected source and install noneditably so later checkout changes cannot change the installed server.

```sh
set -eu
TFT_REPO="$(git rev-parse --show-toplevel)"
TFT_INSTALL="$HOME/.local/share/tft-simulator-mcp/install-$(date +%Y%m%d-%H%M%S)"
TFT_MCP_REVISION="$(git -C "$TFT_REPO" rev-parse --verify HEAD)"
TFT_SIMULATOR_REVISION=33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d
if [ -e "$TFT_INSTALL" ] || [ -L "$TFT_INSTALL" ]; then
    echo "Installation path already exists: $TFT_INSTALL" >&2
    exit 1
fi
mkdir -p "$TFT_INSTALL/source" "$TFT_INSTALL/host" "$TFT_INSTALL/logs/sdk" "$TFT_INSTALL/logs/codex" "$TFT_INSTALL/logs/claude"
chmod 700 "$TFT_INSTALL" "$TFT_INSTALL/logs"
printf '%s\n' "$TFT_MCP_REVISION" > "$TFT_INSTALL/mcp-revision.txt"
printf '%s\n' "$TFT_SIMULATOR_REVISION" > "$TFT_INSTALL/simulator-revision.txt"
printf 'Selected MCP revision: %s\n' "$TFT_MCP_REVISION"
git init -q "$TFT_INSTALL/host"
git -C "$TFT_REPO" archive --output="$TFT_INSTALL/source.tar" "$TFT_MCP_REVISION"
tar -xf "$TFT_INSTALL/source.tar" -C "$TFT_INSTALL/source"
env -u APPIMAGE python3 -m venv "$TFT_INSTALL/venv"
env -u APPIMAGE "$TFT_INSTALL/venv/bin/python" -m pip install "$TFT_INSTALL/source[dev]"
env -u APPIMAGE "$TFT_INSTALL/venv/bin/python" -m pip check
sha256sum "$TFT_INSTALL/source.tar" | tee "$TFT_INSTALL/source.sha256"
cd "$TFT_INSTALL/host"
env -u APPIMAGE -u PYTHONPATH "$TFT_INSTALL/venv/bin/python" -c 'import sys, Simulator, tft_mcp; from importlib.metadata import version; print(sys.executable, Simulator.__file__, tft_mcp.__file__); print({n:version(n) for n in ("tft-simulator","tft-simulator-mcp","numpy","PettingZoo","gymnasium","mcp")})'
TFT_CHECK_DIR="$(mktemp -d "$TFT_INSTALL/logs/sdk/check-XXXXXX")"
env -u APPIMAGE -u PYTHONPATH TFT_MCP_PROFILE=default TFT_MCP_TEST_COMMAND="$TFT_INSTALL/venv/bin/tft-mcp" "$TFT_INSTALL/venv/bin/python" -m pytest -c "$TFT_INSTALL/source/pyproject.toml" "$TFT_INSTALL/source/tests/test_protocol.py" -k production_discovery_and_idle -q --basetemp="$TFT_CHECK_DIR/protocol"
```

Imports must resolve inside the new venv. The idle SDK check launches the installed server outside both checkouts and verifies exactly 26 default-profile tools without starting a game. For installation acceptance that includes test games, use `-k 'not full_lobby and not invalid_output'` instead. The `invalid_output` fixture uses checkout source and belongs to developer checks.

Use a new `TFT_CHECK_DIR` for every run because pytest clears its basetemp directory. Record the MCP revision/archive checksum and simulator commit/source digest separately. Installed simulator `direct_url.json` commit metadata overrides conflicting environment hints. Archive installs may retain an explicit `TFT_MCP_SIMULATOR_REVISION` hint; every install records the actual source SHA-256. Package versions alone do not identify source content.

Save the printed revision, checksum and successful check output with the installation evidence. Existing installations under historical `tftmuzero-mcp` paths remain valid; renaming the project does not require moving their archives, environments or logs.

## Connect a native host

Inspect `codex mcp get tft --json` or `claude mcp get tft` first. For an existing Claude setup, run inspection from its original registered project directory before changing cwd. A private local entry in another project can otherwise appear absent. Preserve that exact project key and use its existing registration directory for fresh sessions and removal. The new installation's `host` directory is for a first registration only. Reuse an already correct entry. For an existing entry, update only its launcher, arguments, three TFT environment fields and the Codex server approval default described below. Preserve unrelated settings, environment fields, authentication and per-tool restrictions. Keep configuration file permissions and ownership. Removing and recreating an entry can discard custom policy.

When an existing entry needs a scoped update, follow the [SPEC configuration-preservation contract](../SPEC.md#implementation-decisions). Parse the original configuration in protected process memory, patch only the approved leaves, and reparse before replacement. Confirm the original bytes have not changed and preserve ownership and mode. Compare the complete parsed before/after configuration, excluding only the approved fields at the exact `tft` entry. Keep raw configuration and credentials out of evidence. No CLI update command is assumed here.

These commands register an absent entry. Run only the command for your host:

```sh
cd "$TFT_INSTALL/host"
codex mcp add tft --env "TFT_MCP_AUDIT_PATH=$TFT_INSTALL/logs/codex/audit.jsonl" --env "TFT_MCP_NATIVE_LOG_DIR=$TFT_INSTALL/logs/codex/native" --env "TFT_MCP_SIMULATOR_REVISION=$TFT_SIMULATOR_REVISION" -- /usr/bin/env -u APPIMAGE "$TFT_INSTALL/venv/bin/tft-mcp"
claude mcp add --scope local --transport stdio tft -e "TFT_MCP_AUDIT_PATH=$TFT_INSTALL/logs/claude/audit.jsonl" -e "TFT_MCP_NATIVE_LOG_DIR=$TFT_INSTALL/logs/claude/native" -e "TFT_MCP_SIMULATOR_REVISION=$TFT_SIMULATOR_REVISION" -- /usr/bin/env -u APPIMAGE "$TFT_INSTALL/venv/bin/tft-mcp"
```

Codex stores registration in `~/.codex/config.toml`. Claude's private local entry belongs to the project in `~/.claude.json`. For a first registration, use the same external `host` directory for registration and fresh Claude sessions. For an existing entry, retain its original project directory. Its empty Git repository establishes a stable project root without adding client configuration to the source repository.

For this known local server, add the following field to the existing `[mcp_servers.tft]` parent table before any `.env` or per-tool child table:

```toml
default_tools_approval_mode = "approve"
```

This setting trusts current and future tools from the installed `tft` server. Existing per-tool approval and enabled/disabled overrides retain precedence. Preserve global `approval_policy`, sandbox settings and all other server entries. Claude permissions remain unchanged. The server still checks inputs, lifecycle, legality and budget.

The `/usr/bin/env -u APPIMAGE` wrapper avoids interpreter interference on affected AppImage hosts. The launcher fixes `PYTHONHASHSEED=0` before imports. Audit logging is required; native logs default beside the audit file when omitted. Keep SDK and each host's audit, native and session logs separate.

Open a fresh native session and request an actual `tft.get_game_status` call. Registration and discovery alone do not prove tool execution. If the host needs a reload or lacks model access, report that result before claiming connection. CLI examples were checked with Codex 0.162.1 and Claude Code 2.1.294 on 2026-10-10. See [Codex MCP](https://developers.openai.com/codex/mcp/) and [Claude MCP](https://code.claude.com/docs/en/mcp) for host configuration.

## Play and verify

Supply the text block from [DEFAULT_GAME_PROMPT.md](../DEFAULT_GAME_PROMPT.md) to a fresh native session. Reads do not consume budget or randomness. Individual actions consume one of 14 planning slots and interleave baseline decisions. Explicit `end_turn` starts combat and finishes the remaining lobby after controlled elimination. Terminal own categories retain the controlled snapshot; `get_round` reports the final lobby round and `get_players` reports all eight placements.

Board coordinates are x=0..6 left to right and y=0..3 bottom to top. Bench slots are 0..8, shop slots 0..4 and loose inventory slots 0..9. Rules come from installed simulator definitions. See the [server reference](tool-reference.md) for opponent privacy, action schemas and unsupported native cases.

[Developer checks](tool-reference.md#developer-checks) select checkout source explicitly. Installed-launcher checks remain separate. Process restart begins idle; games do not resume. Closing a game preserves its logs.

## Troubleshooting

- If Python reports the AppImage executable or cannot import venv packages on an affected host, remove `APPIMAGE` from Python and server child environments. Use the documented `/usr/bin/env -u APPIMAGE` launcher wrapper.
- If a call returns `log_unavailable`, inspect `TFT_MCP_AUDIT_PATH` and the native log directory. Set a protected, writable audit destination; logging is required for tool execution.
- If registration succeeds but tools are absent, start a fresh native session. Make an actual idle `get_game_status` call before reporting connection.
- If Codex asks for tool approval, inspect the saved `mcp_servers.tft.default_tools_approval_mode` and its parent-table placement. Existing per-tool overrides still apply. Preserve those restrictions and global policies.
- If Claude reports Connected but model access fails, report the exact access error. The earlier authenticated model attempt returned HTTP 404 before gameplay; registration does not establish model access.

Lifecycle errors are documented in the [tool reference](tool-reference.md). `no_game` means the requested inspection or action needs a game; `game_active` means close the current game before starting another. `budget_exhausted` requires explicit `end_turn`; rejected actions and reads preserve budget.

## Remove the entry

When retiring the setup, remove only the named entry. Run only the command for your host. Claude removal must use its actual registration directory; the example assumes the first registration used this installation's `host` directory:

```sh
codex mcp remove tft
cd "$TFT_INSTALL/host"
claude mcp remove --scope local tft
```

Once no host uses the installation, remove its dedicated environment/source directory if wanted. Retain or delete gameplay logs separately.
