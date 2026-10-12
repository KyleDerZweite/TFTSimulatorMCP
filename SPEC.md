# TFTSimulatorMCP contract

The MCP server lets a native Codex host control `player_0` against seven unchanged `Default_Agent(False)` opponents. Codex with GPT-6-Luna is the primary target. The host owns inference and the tool loop. This repository owns the adapter, documentation and tests.

## Runtime and protocol

There is one mode and one game per server process. Require `TFT_MCP_SEED` as decimal digits in `0..2147483647`. Start the game before serving tools and close it on graceful shutdown. Restarting starts a fresh game; retained logs survive shutdown. There are no lifecycle tools or profile selector.

Expose 16 tools: `get_decision`, `get_board`, `get_players`, `search_champions`, `get_champion`, `search_traits`, `get_trait`, `search_items`, `get_item`, `buy_unit`, `sell_unit`, `move_unit`, `equip_item`, `refresh_shop`, `buy_xp`, and `end_turn`. Search returns short summaries; exact lookups return installed definitions. Keep concrete calls and strict recursive schemas. Errors use MCP `isError` and `{code, message, details}`.

`get_decision` projects status, economy, occupied own board/bench/items, all shop offers and nonzero stored traits from one detached snapshot. Empty owned slots are omitted; slot indices remain exact. Actions return `{receipt, decision}`. `end_turn` returns the next decision directly. The receipt and projection must validate before committing the action.

Reads and rejected actions preserve gameplay and randomness. Each planning phase allows 14 ordinary actions, reserving the native fifteenth slot for explicit `end_turn`. Ordinary actions remain in the same round and interleave unchanged baseline decisions. `end_turn` drains planning and runs combat. After controlled elimination, baselines finish the lobby automatically. Terminal status includes all-lobby completion and controlled placement. `snapshot_round` retains the controlled player's final own-state round; `status.round` reports the final lobby round.

`get_players` exposes stable IDs, public health, level and native placements. `get_board` reads the controlled or a known living opponent's board using local coordinates. Removed opponents return `player_eliminated`; their final public status remains in `get_players`. Opponent shops, benches, inventories, economy, policies and future randomness stay private.

Board coordinates are `x=0..6` left to right and `y=0..3` bottom to top. Native index is `x*4+y`. Bench slots are `0..8`, shop slots `0..4`, inventory slots `0..9`. Container positions establish locations. Requests reject unknown fields, nulls, booleans in integer fields and out-of-range values.

## Module ownership

| Module | Responsibility |
| --- | --- |
| `launcher`, `transport` | Deterministic process startup, seed validation, SDK streams and graceful shutdown. |
| `tools`, `tool_schemas`, `tool_calls` | Concrete declarations, strict validation, serialized calls, result validation and audit records. |
| `session` | One game aggregate, scheduling, RNG/module isolation, transactions, public visibility and terminal snapshots. |
| `state` | Detached projections and action deltas shared by observations and receipts. |
| `action_helpers`, `purchase`, `movement`, `equipment` | Shared locations/prices and native legality/postconditions for their actions. |
| `champion_catalog`, `item_catalog` | Read-only definitions from the installed simulator. |
| `simulator_identity`, `errors` | Installed source identity and structured errors. |

Imports point from MCP to the installed simulator. Keep ordinary Python and the concrete adapter; add no generic dispatcher, provider framework or model runner. Preserve the `tft_mcp` import and `tft-mcp` launcher.

The simulator is an immutable external dependency pinned in `pyproject.toml`. Its installed definitions, rules and defaults are authoritative. Verify its actual Git revision and source digest separately from the MCP revision. Add no fixed set selector, copied runtime catalog or simulator modifications.

## Atomic actions

The session owns one transaction over the candidate game graph, RNG states, simulator module bindings, native logs and audit. Publish only after native execution, postconditions, detached receipt/projection, schema validation and audit succeed. Any failure discards the candidate and preserves accepted graph aliases, logs, budget and randomness. Record the structured error separately when logging is available.

Use native prices and merges. Preflight capacity and unsafe native operations; reject rather than repair simulator behavior. Verify copy conservation, equipment handling, gold, locations and native trait-cache timing. Preserve literal native Chosen and Kayn behavior. The existing real-simulator failure tests own detailed edge-case coverage.

## Usage and verification

The repository skill explains MCP mechanics only. The model chooses strategy. Setup uses a fresh noneditable installation and absolute launcher. Preserve operator credentials, unrelated configuration, existing per-tool policy and retained logs. Update only the explicitly authorized named `tft` entry. The server adds no approval layer.

Verify checkout behavior through the official SDK and real simulator. Cover all tool families, strict inputs, privacy, budget, rollback, graceful shutdown, terminal inspection and an exact full-game tape replayed across three processes. Extra/reordered reads and rejected actions must not change replay.

Verify installed acceptance outside both checkouts without `PYTHONPATH`. A native GPT-6-Luna game establishes target usability, separately from scripted SDK acceptance or strategic strength. Record current source identity, passed/failed/unexecuted checks and host limits in [docs/verification.md](docs/verification.md). Claude acceptance is separate when authenticated access exists. No GitHub Actions, deployment or persistent host reconfiguration is part of this change.
