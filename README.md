# TFTSimulatorMCP

[TFTSimulatorMCP](https://github.com/KyleDerZweite/TFTSimulatorMCP) provides local stdio MCP tools for the unchanged [original TFT simulator, silverlight6/TFTMuZeroAgent](https://github.com/silverlight6/TFTMuZeroAgent). This repository owns the MCP adapter, tools and tests. The simulator owns game mechanics and remains an external dependency pinned to Git revision `33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d`.

The server controls `player_0` in one seeded eight-player game. Seven opponents use the simulator's existing `Default_Agent(False)` policy. Codex CLI or Claude Code owns model inference and chooses individual MCP actions. The installed Simulator runs in the same Python process as GameSession.

```mermaid
flowchart LR
    subgraph Python[Server Python process]
        Transport[MCP transport] --> Session[GameSession]
        Session --> Simulator[Installed Simulator library]
    end
    Host[Codex CLI or Claude Code] -->|stdio MCP| Transport
```

## Get started

```sh
git clone https://github.com/KyleDerZweite/TFTSimulatorMCP.git
cd TFTSimulatorMCP
```

Copy the text block from [SETUP_PROMPT.md](SETUP_PROMPT.md) into Codex CLI or Claude Code with this checkout available. It installs a selected revision in a fresh external environment and connects the named `tft` server. For manual installation, native configuration, connection checks, troubleshooting and removal, follow [docs/setup.md](docs/setup.md).

For the default profile, copy [DEFAULT_GAME_PROMPT.md](DEFAULT_GAME_PROMPT.md) into a fresh native session. For compact Codex play, use [GAME_PROMPT.md](GAME_PROMPT.md). The host chooses individual actions; information calls are free, and each planning round allows 14 actions before explicit `end_turn`.

For Codex with `gpt-6-luna`, follow [the compact play guide](docs/codex-play.md). Its optional compact profile exposes 16 tools, manages one game per process and returns visible decision state after actions. Codex supplies the existing model/tool loop.

## Documentation

- [Tool reference](docs/tool-reference.md): all 26 default tools, argument examples, coordinates, error behavior and native simulator limitations.
- [Setup guide](docs/setup.md): installation and native host operations.
- [SPEC.md](SPEC.md): accepted behavior, module responsibilities and acceptance requirements.
- [GLOSSARY.md](GLOSSARY.md): gameplay terms.
- [Verification record](docs/verification.md): tested revisions, historical results and unavailable evidence.
- [Developer checks](docs/tool-reference.md#developer-checks): source checks and separate installed acceptance.
- [Module layout](docs/tool-reference.md#module-layout): concrete protocol, session and helper responsibilities.
- [Original Set 4 sources](docs/set4-sources.md): verified archive downloads and compatibility limits for future offline knowledge.

## Limits

The server runs one local game per process. Restarting begins idle; games do not resume. Opponent scouting exposes only public boards, traits and status. Automated carousel decisions and unsupported native operations remain simulator limits. The reference documents equipment and merge cases that reject safely.

This project provides simulator tools. It does not train or host a MuZero model. Codex CLI or Claude Code supplies model inference. PoroSight integration remains future work outside the accepted contract.
