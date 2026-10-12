# MCP tools

All calls take JSON objects. Unknown keys and invalid types reject. Successful actions return `{receipt, decision}`; `end_turn` returns `decision` directly. Errors set MCP `isError` and return `{code, message, details}`. Reads and rejections spend no budget.

| Tools | Arguments / result |
| --- | --- |
| `get_decision` | `{}`. Own status, economy, occupied board/bench/items, all shop offers and nonzero traits. |
| `get_players` | `{}`. Public player IDs, health, level and placements. |
| `get_board` | Optional `player_id`. All 28 board slots; omission selects you. |
| `search_champions` | Optional `query`, `cost` 1..5, `trait_id`. Champion summaries. |
| `get_champion` | Required `champion_id`. Raw stats, rule parameters and Chosen metadata. |
| `search_traits` / `get_trait` | Optional `query` / required `trait_id`. Thresholds / effects and members. |
| `search_items` / `get_item` | Optional `query`, `kind` / required `item_id`. Summaries / effects, recipes and constraints. |
| `buy_unit` | `shop_slot` 0..4. |
| `sell_unit` | `location`. |
| `move_unit` | `source`, `target`. |
| `equip_item` | `item_slot` 0..9, `target`. |
| `refresh_shop` / `buy_xp` | `{}`. Spend the current native cost. |
| `end_turn` | `{}`. Finish planning and run combat. |

A location is `{"kind":"board","x":3,"y":0}` or `{"kind":"bench","slot":0}`. Board x=0..6 runs left to right; y=0..3 runs bottom to top. Bench slots are 0..8. Empty owned slots are omitted from decisions; their indices remain exact.

Search matches case-insensitive ID substrings. Exact lookups require case-sensitive simulator IDs. Champion filters combine with AND; item `kind` is `component`, `equipment` or `consumable`. No match returns an empty list. Definitions expose raw installed values, with unavailable text descriptions marked explicitly.

There are 14 ordinary actions per planning phase. Explicit `end_turn` remains available when that budget is exhausted. Terminal `snapshot_round` can precede `status.round`, because the lobby continues after your elimination. `get_players` then reports all eight placements. Opponent scouting exposes living boards only; removed players return `player_eliminated`.

## Native limits

The adapter rejects unsafe native behavior atomically. This includes bench-to-bench moves, early board-contributor merge cascades, unsafe equipment capacity, some glove combinations and trait removal/reforge cases. Board sales need room for equipment; bench overflow drops the entire equipment set. Kayn assignment and combat use inconsistent native form names, so transformation correctness is unproven. Errors explain the rejected case.

Carousel choices remain automatic. There is no fixed game duration, resume or external ranked meta. Rule lookups use the installed simulator rather than current live TFT rules.

## Developer checks

```sh
env -u APPIMAGE PYTHONHASHSEED=0 PYTHONPATH=src .venv/bin/python -m pytest tests -q
```

Installed acceptance launches an absolute `tft-mcp` outside both checkouts without `PYTHONPATH`. See [verification.md](verification.md) for actual results and [SPEC.md](../SPEC.md) for module responsibilities.
