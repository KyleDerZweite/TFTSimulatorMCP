# TFTSimulatorMCP

Local stdio MCP tools for the unchanged [TFT simulator](https://github.com/silverlight6/TFTMuZeroAgent). Codex with GPT-6-Luna controls `player_0`. The default game is against seven simulator baselines. `TFT_MCP_MODE=single_player` starts the simulator's one-player campaign instead. The host supplies the model and tool loop.

One process runs one seeded game. The server starts it automatically. Each action returns the observation. `text` is the simulator language-model view: the full position on the first read, then only the action result and sections that changed. `end_turn` runs combat. The full lobby has 20 tools. Single-player mode has 19: no `get_players` or `get_board`, plus `get_last_fight`.

[Install and connect](docs/setup.md), then ask Codex to play using [$tft-mcp](.agents/skills/tft-mcp/SKILL.md). The skill explains tool mechanics. The model chooses its strategy.

- [Tools](docs/tool-reference.md): arguments, responses and limits.
- [Host contract](docs/mcp-host-contract.md): how Cursor and other agents receive those tools.
- [Contract](SPEC.md): module ownership and invariants.
- [Terms](GLOSSARY.md): domain vocabulary.
- [Verification](docs/verification.md): tested artifact and remaining limits.
- [Set 4 sources](docs/set4-sources.md): usable archives and data gaps.

The simulator is an external pinned dependency. This project supplies no model runner, live TFT connection, or gameplay resume. Final-board win rates come from the Set 4 Challenger index.
