# Compact Codex TFT play

Use after configuring the compact `tft` server with an explicit seed. Setup alone does not authorize gameplay. Select `gpt-6-luna` in the native Codex harness, then copy this prompt into a fresh session. The default profile uses [DEFAULT_GAME_PROMPT.md](DEFAULT_GAME_PROMPT.md).

```text
Play one complete game using only individual tools from the connected tft MCP
server. The compact server already started one seeded game. First call
get_decision. Use its actual state and the decision returned after each action.
Do not use shell, a script or a custom client for gameplay.

You control player_0 against seven existing simulator baselines. Buy affordable
useful champions, deploy units up to economy.max_units, position them and equip
compatible items. Use buy_unit and move_unit when legal. Group units by their
installed traits and use focused rule tools when needed. Do not assume current
live TFT rules or MetaTFT builds. Choose your own strategy.

Board x=0..6 left to right, y=0..3 bottom to top. Bench slots are 0..8, shop
0..4 and items 0..9. Locations are JSON objects, for example
{"kind":"board","x":3,"y":0} or {"kind":"bench","slot":0}.
Empty owned slots are omitted. Shop purchase_cost includes Chosen pricing.
next_level_cost is the total native XP threshold; exp is current XP.

Information calls and rejected actions are free. There are 14 planning actions
per round. Spend only on useful actions, use the latest returned decision and
call end_turn explicitly to run combat and receive the next decision. With zero
gold and no useful legal action, end_turn immediately. Do not start or close
this process-owned game. Continue until status.state is terminal and
status.outcome.lobby_complete is true. Use at most 40 end_turn calls. If an error
or a limit prevents completion, report it and retain the partial evidence.

At terminal, call get_players to verify all eight placements. Call get_decision
again to confirm stable terminal state. snapshot_round is the retained own
round; status.round is the completed lobby round. Report the seed, game_id,
model/session identity, controlled placement, all eight placements and any
errors. Include source revisions and log paths only when supplied by setup.
The server closes automatically when the native session ends.
```
