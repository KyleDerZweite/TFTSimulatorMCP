# Compact play with Codex and GPT-6-Luna

Use the existing Codex harness with model `gpt-6-luna`. Codex supplies inference, tool execution and conversation history. The MCP server supplies visible game decisions and validated individual actions. No Ollama, Qwen-Agent, extra model dependencies or custom runner are required.

The [MCP introduction](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro) describes the shared protocol. [OpenAI's MCP guide](https://developers.openai.com/api/docs/mcp) includes ChatGPT plugins and research retrieval; its `search`/`fetch` compatibility interface is for those workflows. [Codex's MCP documentation](https://developers.openai.com/codex/mcp/) supports local stdio commands and environment configuration, which is the appropriate integration here. Keep the official Python MCP SDK and local launcher. Codex reads server initialization instructions; the first 512 characters explain lifecycle and the action/decision workflow, following its documented guidance.

## Setup

Install a pinned noneditable revision in a fresh external environment using [setup.md](setup.md#install-a-pinned-revision). First verify the default profile's 26 tools and idle state. Model access, installation, registration and gameplay are separate checks.

For compact play, configure only these additional fields in the existing named `tft` server environment:

```toml
[mcp_servers.tft.env]
TFT_MCP_PROFILE = "compact"
TFT_MCP_SEED = "0"
```

Keep the existing absolute launcher, writable audit/native destinations and simulator revision. Preserve unrelated environment fields, global policy, per-tool restrictions and credentials. Merge these fields into the existing env table; do not create a duplicate table or replace the complete configuration. Follow the configuration-preservation procedure in SPEC, additionally permitting only these two leaves at `mcp_servers.tft.env` for this compact operation. Changing the profile starts a game when that server process loads, so use a dedicated play session. The setup idle check still uses the default profile without these fields.

Select the model without changing the global default:

```sh
codex --model gpt-6-luna
```

Open a fresh native session so the compact server loads. Copy [GAME_PROMPT.md](../GAME_PROMPT.md) to authorize and start model gameplay. The server has already started exactly one seeded game. Its seed must be explicit decimal digits in 0..2147483647. Invalid configuration fails before constructing the simulator.

The compact game lives in its server process and is discarded when that process ends. Graceful cleanup records a close event; forced host termination can bypass that callback. A completed lobby outcome is already committed before end_turn returns. A new process creates a fresh game, with no durable gameplay resume. Reuse an accepted installation and preserve retained logs. To return to explicit lifecycle tools, set `TFT_MCP_PROFILE="default"` or remove the two compact fields, then reload and use [DEFAULT_GAME_PROMPT.md](../DEFAULT_GAME_PROMPT.md).

## Decision conversation

Compact discovery contains 16 tools: `get_decision`, `get_board`, `get_players`, six champion/trait/item catalog tools and seven individual action tools. Lifecycle tools, category reads and redundant trait-member lookup are omitted. Calls to omitted tools reject without changing the game. The default profile still exposes its existing tools plus the additive `get_decision`.

`get_decision({})` returns `status`, `snapshot_round`, `economy`, `board`, `bench`, `shop`, `items` and nonzero stored `traits`. Occupied owned slots retain exact locations and indices; missing owned slots are empty. Shop retains all five offers and native purchase prices. Economy includes action prices, capacity, streaks and the native XP threshold. `next_level_cost` is a total threshold, not remaining XP; use `exp` to determine the difference. It is null at the level cap.

Individual actions return `{receipt, decision}`. The receipt preserves the default protocol result and the decision contains actual post-action state. `end_turn` returns the next decision directly. This completes the model/action/observation conversation without requiring another sequence of category reads. Projection, schema validation and audit publication are part of the same atomic transaction.

Information calls and rejected actions are free. Individual actions consume one of 14 planning slots. `end_turn` explicitly releases planning and triggers simulator combat. After controlled elimination the existing baselines finish the lobby automatically. There is no promised fixed duration. At terminal, `status.round` is the completed lobby round and `snapshot_round` is the retained own-state round. `get_players` supplies all eight final placements.

## Verification

A disposable native acceptance session can override the installed launcher, args and TFT environment using `codex exec -c`, preserving ordinary saved approval policy. This does not update operator registration. Actual target evidence must include the model/session identity, working-source identity, pinned simulator revision/digest, seed, ordered native tool calls, completed lobby, all placements, stable terminal inspection and an attempted shutdown-close check. Record a missing close callback as a target limit, separately from completed gameplay.

The full SDK game and replay establish tool operation and determinism; they do not replace native LLM gameplay. Smaller payloads do not establish playing strength. Actual results, failures and unavailable evidence are recorded in [verification.md](verification.md).

Qwen findings and original Set 4 MetaTFT availability remain in [qwen-research.md](qwen-research.md). No comp database is shipped without a reproducible permitted dataset and installed-rule compatibility.
