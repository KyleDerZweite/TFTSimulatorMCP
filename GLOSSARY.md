# TFT tool play

| Term | Meaning |
| --- | --- |
| Controlled player | `player_0`, whose actions the model chooses. |
| Baseline opponent | A player controlled by the simulator's existing reference policy. The full lobby has seven. The single-player campaign has none. |
| Single-player campaign | The simulator's one-player game. Planning matches the full lobby. Combat is that environment's generated fight. Winning the last round is placement 1. Losing a fight ends the game. |
| Board | Positioned units that participate in combat. |
| Bench | Reserve units. |
| Shop | Current champion offers. |
| Champion pool | Shared copies of one champion. A visible 1-star unit accounts for 1 copy, a 2-star for 3, and each further star multiplies by 3. |
| Purchase / sale | Exchange gold for a shop unit, or an owned unit for gold. |
| Merge | Combine matching copies into a higher-star unit. |
| Own-state snapshot | Detached visible state, retained at controlled elimination or victory. |
| Planning phase | Decisions before combat. The simulator allows 15 actions, then resolves the round. |
| Observation | Reward, start-of-turn flag, terminal flag, legal command mask, and text from the simulator language-model view. Text is the full visible position the first time, then the action result and only sections that changed. |
| Mask | The simulator's legal commands. An action outside it is rejected and spends nothing. |
| Player elimination | A participant stops making decisions and receives a placement. |
| Lobby completion | All players have final placements. |
| Comp | Exact set of champion names on a final board in the Challenger index. |
| Item build | Exact multiset of items on one champion at the end of a Challenger game. Star level and item order are ignored. |
| Top-4 rate | Share of those boards that finished in placements 1 through 4. |
