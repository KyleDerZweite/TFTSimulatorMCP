# MCP tools

All calls take JSON objects. Unknown keys and invalid types reject. Successful actions and `get_decision` return one observation: `reward`, `start_turn`, `terminal`, `mask`, and `text`. `text` comes from the simulator `llm_observe` view. The first observation lists the visible position, including opponent boards and traits. Later action results start with `action succeeded` and list only sections that changed. The host presents that result before the next tool call. Errors set MCP `isError` and return `{code, message, details}`. Reads and masked rejections spend nothing. A masked action's message is `The action failed.`

| Tools | Arguments / result |
| --- | --- |
| `get_decision` | `{}`. Current observation. `mask` lists legal `{action_type, x1, x2}` commands. |
| `get_players` | `{}`. Public player IDs, health, level and placements. |
| `get_board` | Optional `player_id`. All 28 board slots; omission selects you. |
| `search_champions` | Optional `query`, `cost` 1..5, `trait_id`. Champion summaries. |
| `get_champion` | Required `champion_id`. Raw stats, rule parameters and Chosen metadata. |
| `get_champion_pool` | Required `champion_id`. Installed pool size, visible copies, and the most that can remain. |
| `search_traits` / `get_trait` | Optional `query` / required `trait_id`. Thresholds / effects and members. |
| `search_items` / `get_item` | Optional `query`, `kind` / required `item_id`. Summaries / effects, recipes and constraints. |
| `search_comps_by_champions` | Required `champions` (one or more) and `limit` 1..50. Highest top-4-rate final boards that include every named champion. |
| `search_comps_by_trait` | Required `trait`, `level` 0..14, and `limit` 1..50. Final boards with that exact trait count, highest top-4 rate first. |
| `search_champion_items` | Required `champion`. Optional `items`, one or two. Every item combination on that champion with at least 100 boards, highest top-4 rate first. |
| `buy_unit` | `shop_slot` 0..4. |
| `sell_unit` | `location`. |
| `move_unit` | `source`, `target`. |
| `equip_item` | `item_slot` 0..9, `target`. |
| `refresh_shop` / `buy_xp` | `{}`. Spend the current native cost. |
| `end_turn` | `{}`. Finish planning and run combat. |

A location is `{"kind":"board","x":3,"y":0}` or `{"kind":"bench","slot":0}`. Board x=0..6 runs left to right; y=0..3 runs bottom to top. Bench slots are 0..8. The mask uses the simulator's flat index: board `x*4+y`, bench `28+slot`.

Search matches case-insensitive ID substrings. Exact lookups require case-sensitive simulator IDs. Champion filters combine with AND; item `kind` is `component`, `equipment` or `consumable`. No match returns an empty list. Definitions expose raw installed values, with unavailable text descriptions marked explicitly.

`get_champion_pool` subtracts the current visible position from the installed pool size. Your board, your bench, and living opponents' boards count. A 1-star unit is 1 copy, a 2-star is 3, and each further star multiplies by 3. Shop offers stay in the pool until bought. Opponent benches and shops stay hidden, so the true pool can be lower than `remaining`. Eliminated players are omitted. The read spends nothing and does not change the pool.

`search_comps_by_champions` and `search_comps_by_trait` read the Set 4 Challenger EUW final-board index, pooled across patches 10.19 through 11.1. A comp is the exact set of champion names. Win rate is placements 1 through 4 divided by the number of those boards. Trait level is the recorded unit count, such as 6 for six Cultists. The trait query counts only boards at that exact count. Names accept the recorded spelling or the simulator id. The index keeps a champion list when it appears on at least 100 final boards, and a trait level when that count was recorded on at least 100 boards of that list. Ties break toward more games, then alphabetical champion lists. `search_champion_items` uses the same index. An item build is the exact multiset of items on one champion, at any star level. The index keeps a build recorded on at least 100 boards. One or two optional items keep only builds that include them. Item names accept the recorded name or the simulator id. These reads spend nothing and do not change the live game.

## Single-player mode

`TFT_MCP_MODE=single_player` runs the simulator's one-player campaign with 19 tools. `get_players` and `get_board` are not advertised; calling them returns `invalid_input`. The observation has no opponent section. `end_turn` runs that round's fight: a PvE minion round or a generated enemy board. `reward` 1 means it was won. Losing any fight ends the game with `terminal` true. Winning the last round finishes the campaign.

| Tool | Arguments / result |
| --- | --- |
| `get_last_fight` | `{}`. The fight that just resolved: `round`, `kind` (`none` before the first fight, `minion`, or `combat`), `won`, and `enemy`. `enemy` is `null` except after a generated fight, when it holds `level`, occupied `board` slots and active `traits`. |

The server instructions include a campaign summary computed from the installed simulator: the round count, PvE and carousel rounds, and the rounds where enemy level, unit cost, 2- and 3-star chances, Chosen units and items per unit increase. Generated boards are created when the fight runs, so the next enemy cannot be scouted. They draw from their own pool, so `get_champion_pool` subtracts only your board and bench.

A planning phase ends when the model calls `end_turn` or the simulator applies the 15th action. `end_turn` returns the next observation: the action result, changed economy, and any opponent board or traits that changed. In the full lobby those opponent sections are included when they changed. A pass refreshes those opponent sections too. After elimination, own-state reads keep the final controlled round while the lobby continues. `get_players` then reports all eight placements. Opponent scouting exposes living boards only; removed players return `player_eliminated`. A command absent from the mask returns `masked` and does not change the game.

## Native limits

The simulator mask rejects illegal buys, sales, moves, equipment, refreshes, and experience purchases. Those rejections leave the game unchanged. Kayn assignment and combat use inconsistent native form names, so transformation correctness is unproven.

Carousel choices remain automatic. There is no fixed game duration or resume. Rule lookups use the installed simulator. Comp win rates use the Challenger final-board index.

## Developer checks

```sh
env -u APPIMAGE PYTHONHASHSEED=0 PYTHONPATH=src .venv/bin/python -m pytest tests -q
```

Installed acceptance launches an absolute `tft-mcp` outside both checkouts without `PYTHONPATH`. See [verification.md](verification.md) for actual results and [SPEC.md](../SPEC.md) for module responsibilities.
