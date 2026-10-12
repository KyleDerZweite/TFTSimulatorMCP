# Set up TFTSimulatorMCP

Copy this prompt into Codex CLI or Claude Code with the repository checkout available. It authorizes installation and configuration of the named `tft` entry. Use [DEFAULT_GAME_PROMPT.md](DEFAULT_GAME_PROMPT.md) separately for gameplay.

```text
Install the TFT MCP server from the repository containing this prompt and
connect it to my current Codex CLI or Claude Code host. Use the existing
checkout and a pinned full Git revision of TFTSimulatorMCP. Select the checkout's
full Git HEAD and record it. If no checkout is available, clone
https://github.com/KyleDerZweite/TFTSimulatorMCP and record its selected full HEAD.

Read README.md, docs/setup.md, docs/tool-reference.md and the installation/client
contract in SPEC.md. Follow the canonical docs/setup.md procedure for archived-source
CPU-only installation in a fresh external directory. Install the standalone
package noneditably; its pinned Git dependency installs the unchanged simulator
automatically. Use a fresh environment, because the old
tft-mcp-server and tftmuzero-mcp packages share the same import and launcher names.
Refuse an existing installation path. Reuse an already accepted installation
without overlaying its archive or venv. Preserve unrelated checkout work and
host settings.

Use absolute installed launcher paths and protected writable logs. Remove
APPIMAGE from Python/server child environments on affected hosts. Run pip check,
check installed import paths and use the documented SDK selector
-k production_discovery_and_idle from outside the checkout without PYTHONPATH.
Select TFT_MCP_PROFILE=default for the check regardless of inherited shell fields.
Verify exactly 26 default-profile tools and idle status. Do not start test games during setup.

Inspect the named tft entry before registration, including repeated setup. For
Claude, inspect from the original registered project directory before changing
cwd; an existing private local entry can appear absent in a different project.
Retain a correct entry without rewriting it. Update only an incorrect launcher,
arguments or the three TFT environment fields. For Codex, also persist
mcp_servers.tft.default_tools_approval_mode="approve" for this inspected local
server. Place it in the parent TOML table before child tables. This trusts
current and future tools from that server; existing per-tool overrides retain
precedence. Preserve global approval_policy, sandbox, other servers, per-tool
restrictions, unrelated environment fields and authentication. Preserve Claude
permissions. Use native registration only when tft is absent.

Preserve Claude's exact existing project scope and registration directory. For a
first registration, use private local scope in the same stable external host
directory for registration and play. Keep file permissions and ownership when
editing existing configuration. Follow the SPEC's configuration-preservation checks. Keep secrets
and raw operator configuration out of project evidence. Use separate SDK and
host logs. No custom client, provider adapter or permission override is needed.

Open a fresh native host session and make an actual idle tft get_game_status
call. Report an exact reload or access blocker if it fails; registration and
discovery alone do not establish connection. Retain a correct entry unchanged
on repeated setup.

Report MCP revision and simulator revision separately, package versions, source digest, interpreter/launcher
paths, log locations, host version, configuration preservation and checks that
passed or remain open. Provide DEFAULT_GAME_PROMPT.md and the removal commands.
```
