# TFTSimulatorMCP contract

The MCP server lets a native Codex host control `player_0`. Unset, or with `TFT_MCP_MODE=full`, that player faces seven unchanged `Default_Agent(False)` opponents. `TFT_MCP_MODE=single_player` starts the simulator's one-player campaign instead: the same planning actions, then that environment's generated fight. Codex with GPT-6-Luna is the primary target. The host owns inference and the tool loop. This repository owns the adapter, documentation and tests.

## Runtime and protocol

There is one game per server process. Require `TFT_MCP_SEED` as decimal digits in `0..2147483647`. `TFT_MCP_MODE` is `full` or `single_player`; an empty or unset value means `full`. Start the game before serving tools and close it on graceful shutdown. Restarting starts a fresh game; retained logs survive shutdown. There are no lifecycle tools or profile selector.

`TFT_MCP_STREAM_LOG` selects an append-only text transcript of the model-facing MCP boundary. Unset, the process writes `model-stream.txt` beside the audit file. `off` disables it. The transcript contains the initialize instructions, each `tools/list` payload, each tool call, and each tool result returned to the host, with observation `text` repeated above the structured JSON. User messages, assistant prose, skills, and the host system prompt stay with the host. A stream-log failure leaves the game and the audit unchanged. The transcript survives shutdown and is separate from the audit transaction.

Expose 20 tools: `get_decision`, `get_board`, `get_players`, `search_champions`, `get_champion`, `get_champion_pool`, `search_traits`, `get_trait`, `search_items`, `get_item`, `search_comps_by_champions`, `search_comps_by_trait`, `search_champion_items`, `buy_unit`, `sell_unit`, `move_unit`, `equip_item`, `refresh_shop`, `buy_xp`, and `end_turn`. Search returns short summaries; exact lookups return installed definitions. Comp and item-build searches read the Set 4 Challenger final-board index. Keep concrete calls and strict recursive schemas. Errors use MCP `isError` and `{code, message, details}`.

Single-player mode advertises `tools.SINGLE_PLAYER_TOOLS`: the same set without `get_players` and `get_board`, plus `get_last_fight`. `get_last_fight` reads the fight that just resolved: round, `minion` or `combat`, the result, and the generated enemy's level, occupied board slots and active traits. The enemy is created at combat time, so nothing about the next board is visible before it is fought. `end_turn`, `get_decision` and `get_champion_pool` keep their behavior with descriptions that do not mention opponents. Campaign instructions derive from the installed round schedule and generator curriculum, including native variation in enemy level and items.

The concrete `single_player` adapter uses the installed Gym `reset`/`step` interface, native action mask and text renderer. It converts cumulative native rewards to per-call deltas and retains the completed fight separately from the next planning round. `session` still owns transactions, RNG isolation, detached projections and audit publication. The adapter changes no simulator classes, rules, schedules or defaults and generates no future enemy for inspection.

`get_decision` returns the controlled player's observation: `reward`, `start_turn`, `terminal`, `mask`, and `text`. `text` uses the installed simulator renderer, through `llm_observe` in full mode and the concrete native view in single-player mode. The first read has no previous position, so it lists the visible position: round, health, gold, level, experience, streaks, board capacity, board, bench, shop, items, traits, and each opponent's health, level, board, and traits. Each later action returns that same observation shape. Its `text` starts with `action succeeded` and includes only sections whose contents changed. A board move returns the board. A new planning phase also includes changed economy, such as gold and streaks, the reset action count, and any opponent board or traits that changed. The simulator refreshes opponent boards and traits at the start of a planning phase and on a pass. `end_turn` passes the phase and returns that next observation. A masked command returns `masked` with message `The action failed.`, spends nothing, and does not repeat the position. The host shows each action result to the model before the next tool call. The observation must validate before committing the action.

Reads and rejected actions preserve gameplay and randomness. The simulator mask is the only game check. A command that is off in the mask returns `masked` and spends nothing. Planning allows the simulator's 15 actions. The fifteenth legal action resolves the round. `end_turn` passes the rest of the phase and runs combat. Other living seats play `Default_Agent` inside the simulator. After controlled elimination, baselines finish the lobby automatically. Terminal observation sets `terminal` true. `get_game_status` still reports lobby completion and controlled placement. Own-state inspection keeps the controlled player's final round, which can precede the lobby's last round.

`get_players` exposes stable IDs, public health, level and native placements. `get_board` reads the controlled or a known living opponent's board using local coordinates. Removed opponents return `player_eliminated`; their final public status remains in `get_players`. Opponent shops, benches, inventories, economy, policies and future randomness stay private.

`get_champion_pool` reads one exact champion ID. `remaining` is the installed pool size minus copies in the current visible position: the controlled board and bench, and living opponents' boards. A 1-star unit is 1 copy, a 2-star is 3, and each further star multiplies by 3. Shop offers stay in the pool until purchased. Eliminated players are omitted because their units return to the pool and leave the visible boards. This is a visible-state estimate. Hidden units and native duplication effects can make the actual pool differ in either direction. The read does not change the pool.

`search_comps_by_champions` and `search_comps_by_trait` read `data/set4/player-results/comps.sqlite`. A comp is the exact set of champion names on a final board. Win rate is the share of those boards with placement 1 through 4. Trait level is the recorded unit count. The index keeps champion lists with at least 100 boards, and trait levels recorded on at least 100 boards of that list. `search_champion_items` reads item combinations on one champion. A combination is the exact multiset of items on that champion, ignoring star level and item order. It keeps combinations recorded on at least 100 boards. Optional one or two items restrict the result to combinations that include them. The reads do not change the live game. Download the pinned Challenger CSV and Fates item list with `python -m tft_mcp.comp_download`, then rebuild the index with `python -m tft_mcp.comp_index`.

Board coordinates are `x=0..6` left to right and `y=0..3` bottom to top. Native index is `x*4+y`. Bench slots are `0..8`, shop slots `0..4`, inventory slots `0..9`. Container positions establish locations. Requests reject unknown fields, nulls, booleans in integer fields and out-of-range values.

## Module ownership

| Module | Responsibility |
| --- | --- |
| `launcher`, `transport` | Deterministic process startup, seed validation, SDK streams and graceful shutdown. |
| `stream_log` | Append-only transcript of initialize instructions, advertised tools, calls and results. Outside the audit transaction. |
| `tools`, `tool_schemas`, `tool_calls` | Concrete declarations, strict validation, serialized calls, result validation and audit records. |
| `session` | One game aggregate, scheduling, RNG/module isolation, transactions, public visibility and terminal snapshots. |
| `state` | Detached projections for the public and own-state reads. |
| `single_player` | Concrete native Gym stepping, reward deltas, observations, completed fights and campaign metadata. |
| `action_helpers`, `movement`, `equipment` | JSON shape checks for locations and action arguments. Game legality stays in the simulator mask. |
| `champion_catalog`, `item_catalog` | Read-only definitions from the installed simulator. |
| `comp_index` | Read-only Set 4 Challenger final-board aggregates, comp queries, and champion item builds. |
| `comp_download` | Operator command that downloads the pinned Challenger CSV and Fates item list for rebuilding the comp index. |
| `simulator_identity`, `errors` | Installed source identity and structured errors. |
| `native_logs` | Operator command that merges legacy per-action native log copies into one directory per game. |

Imports point from MCP to the installed simulator. Keep ordinary Python and the concrete adapter; add no generic dispatcher, provider framework or model runner. Preserve the `tft_mcp` import and `tft-mcp` launcher.

The simulator is an immutable external dependency pinned in `pyproject.toml`. Its installed definitions, rules and defaults are authoritative. Verify its actual Git revision and source digest separately from the MCP revision. Add no fixed set selector, copied runtime catalog or simulator modifications.

## Atomic actions

The session owns one transaction over the candidate game graph, RNG states, simulator module bindings, native logs and audit. Publish only after the simulator accepts the command, the observation matches its schema, and the audit succeeds. Any failure discards the candidate and preserves accepted graph aliases, logs and randomness. Record the structured error separately when logging is available.

The simulator writes `log.txt` relative to its working directory and takes no log path. Each game runs in one native directory, `<TFT_MCP_NATIVE_LOG_DIR>/<game_id>/`, written in place. A mutating call keeps that directory's accepted bytes in memory and restores them when the transaction fails, so rejected calls leave no copies and audit `native_log_dir` stays one path per game. A failed start keeps its directory as diagnostic evidence.

Gold, bench space, merges, item combinations and movement limits come from the simulator mask. A disagreement between a legal native action and the mask is fixed in the simulator, not rechecked here. Preserve literal native Chosen and Kayn behavior.

## Usage and verification

The repository skill explains MCP mechanics only. The model chooses strategy. Setup uses a fresh noneditable installation and absolute launcher. Preserve operator credentials, unrelated configuration, existing per-tool policy and retained logs. Update only the explicitly authorized named `tft` entry. The server adds no approval layer.

Verify checkout behavior through the official SDK and real simulator. Cover all tool families, strict inputs, privacy, the mask, rollback, graceful shutdown, terminal inspection and an exact full-game tape replayed across three processes. Extra/reordered reads and rejected actions must not change replay.

Verify installed acceptance outside both checkouts without `PYTHONPATH`. A native GPT-6-Luna game establishes target usability, separately from scripted SDK acceptance or strategic strength. Record current source identity, passed/failed/unexecuted checks and host limits in [docs/verification.md](docs/verification.md). Claude acceptance is separate when authenticated access exists. No GitHub Actions, deployment or persistent host reconfiguration is part of this change.

The pinned native token encoder rejects rounds 40 and later. Complete 45-round single-player campaign acceptance requires an upstream fix. Preserve assertions and roll back failed progression.
