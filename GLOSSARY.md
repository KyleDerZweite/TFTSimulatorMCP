# TFT tool play

Terms for playing the installed TFT simulator through MCP tools.

## Language

**Controlled player**:
The lobby participant whose decisions are made by the LLM through tools.

**Baseline opponent**:
A lobby participant whose decisions are made by an existing reference policy.

**Board**:
The positioned units belonging to a player that participate in combat.

**Bench**:
A player's reserve units that are not positioned on the board.

**Shop**:
The champion offers currently available for purchase by a player.

**Purchase**:
The acquisition of a champion offer from the shop in exchange for gold. The acquired copy may merge with matching owned copies.

**Sale**:
The exchange of an owned unit for gold.

**Merge**:
The combination of matching champion copies into a higher-star unit.

**Own-state snapshot**:
The controlled player's visible board, bench, shop, inventory, economy and traits at one point in play. After player elimination, this can describe their final own state while the remaining lobby continues.

**Planning phase**:
The part of a round in which a player purchases, sells, positions units, and assigns items before combat.

**Planning budget**:
The maximum number of individual game actions a controlled player may perform during a planning phase. Information requests and rejected actions do not spend this budget.

**Player elimination**:
The point at which a lobby participant can no longer make game decisions and receives a finishing placement. Other participants may continue playing.

**Lobby completion**:
The terminal outcome of the entire lobby, after all remaining play has finished. Player elimination and lobby completion are distinct events.
