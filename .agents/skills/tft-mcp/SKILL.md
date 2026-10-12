---
name: tft-mcp
description: Use the TFT simulator MCP tools when asked to play a simulator game.
---

Read `get_decision` first. The server already runs one seeded game for `player_0`.

Use the returned slots and canonical IDs. Empty own board, bench and inventory slots are omitted. Board coordinates are `x=0..6` left to right and `y=0..3` bottom to top. Bench slots are `0..8`, shop slots `0..4`, inventory slots `0..9`.

Actions return a receipt and updated `decision`. Reads and rejected actions are free. Use `search_*` for rule IDs, `get_*` for details, and `get_players` plus `get_board(player_id)` for public scouting.

Call `end_turn` when planning is finished or the 14-action budget is exhausted. It runs combat and returns the next decision. Continue until `status.state` is `terminal` and `status.outcome.lobby_complete` is true. Report your placement from the terminal outcome.

For an error, read `code`, `message` and `details` before choosing the next call. A new server process starts a fresh game.
