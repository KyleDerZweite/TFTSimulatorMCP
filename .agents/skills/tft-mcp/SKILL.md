---
name: tft-mcp
description: Use the TFT simulator MCP tools when asked to play a simulator game.
---

A seeded game starts when the host connects. Use `get_decision` for the current observation and legal action mask. Each action returns `reward`, `start_turn`, `terminal`, `mask` and native `text`. Show each result to the model before choosing the next action. Reads and masked rejections do not spend actions.

Planning ends at `end_turn` or the fifteenth legal action. Stop when `terminal` is true. Full mode controls player_0 against seven baselines. Single-player mode hides opponent scouting and provides `get_last_fight` for the completed fight.

Board coordinates are x=0..6 left to right and y=0..3 bottom to top. Bench slots are 0..8, shop slots 0..4 and item slots 0..9. Masks use board index x*4+y and bench index 28+slot.

Rule lookups read installed definitions. Comp and item-build queries use the separate historical database configured by `TFT_MCP_COMP_DB`. Restart the server for a fresh game. The model chooses its own strategy.
