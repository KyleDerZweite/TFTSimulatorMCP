# TFTSimulatorMCP

Local stdio MCP tools for the unchanged [TFT simulator](https://github.com/silverlight6/TFTMuZeroAgent). Codex with GPT-6-Luna controls `player_0` against seven simulator baselines. The host supplies the model and tool loop.

One process runs one seeded game. The server starts it automatically. Actions return a receipt and updated observation; `end_turn` runs combat. There is one compact tool set with 16 tools.

[Install and connect](docs/setup.md), then ask Codex to play using [$tft-mcp](.agents/skills/tft-mcp/SKILL.md). The skill explains tool mechanics. The model chooses its strategy.

- [Tools](docs/tool-reference.md): arguments, responses and limits.
- [Contract](SPEC.md): module ownership and invariants.
- [Terms](GLOSSARY.md): domain vocabulary.
- [Verification](docs/verification.md): tested artifact and remaining limits.
- [Set 4 sources](docs/set4-sources.md): usable archives and data gaps.

The simulator is an external pinned dependency. This project supplies no model runner, live TFT connection, comp database or gameplay resume.
