# Silver feedback analysis

Prepared on 2026-10-12 against the working diff based on `63c55f7`. The owner wants a broader architecture improvement, with smaller readable modules and shared implementations. Codex with `gpt-6-luna` remains the primary target. Metabot investigation is withdrawn. This document prepares design decisions; it does not report another implementation or gameplay run.

## What to take from the comments

Silver's strongest advice is to make each action produce the information needed for the next decision, use existing host and protocol implementations, and concentrate simulator knowledge in concrete modules. Some suggestions already exist in the working diff. Others require a distinction between simulator mechanics and the agent's decision to trigger them.

| Comment | Evidence in this project | Useful consequence |
| --- | --- | --- |
| Remove start_game and close_game from the model's tools. | The compact profile starts one explicitly seeded game when the server loads and closes it on graceful shutdown. It hides both tools. The default profile retains explicit lifecycle for compatibility. | Prefer compact for agent play. Keep lifecycle ownership in the server process. Forced host termination can bypass graceful close. |
| get_game_status duplicates other reads. | Compact hides it. get_decision includes lifecycle status and the planning budget. Default category tools remain compatible. | Use one decision observation rather than a sequence of category reads. |
| The simulator already handles end_turn. | Native combat and scheduling are automatic after planning slots drain. The adapter reserves the fifteenth native slot and exposes 14 ordinary actions. The model still needs to say when planning is finished. | Keep end_turn as that signal. Removing it or advancing automatically after action 14 changes planning behavior. |
| Add early, mid and late comp queries. | Current catalog tools expose installed rules, without strategic rankings. No accepted comp dataset exists. | A future search_comps tool can use a phase filter, champion/trait filters and a small limit. Three phase tools would repeat one query. Define phases and ranking evidence first. |
| Explain duration and game context at startup. | Initialization instructions already explain player_0, seven baselines, budget, automatic combat, terminal outcome and installed definitions. Game duration varies. | Describe progression and stopping conditions. Do not promise a fixed number of rounds. |
| Split the long session into readable files. | Equipment, movement, state, errors and identity have already been extracted. session.py is still 783 lines and transport.py 558 lines. | Deepen purchase/sale and state projection modules. Separate concrete tool declarations from the audited call path and process startup. |
| Put more information in simulator info. | Native infos contain live Player and shop references. Encoded observations contain arrays, not detached canonical records. Neither supplies the accepted retained terminal snapshot. | Reuse one visible-state projection in this adapter first. A simulator-native helper only earns its cost if another caller needs that same observation. |
| Use Qwen's model and MCP code rather than writing everything. | The project already uses the official Python MCP SDK. Codex owns inference, parsing, tool execution and conversation history. Silver later qualified this criticism. The owner changed the target from Qwen to Codex. | Keep the existing SDK and native host. Align names, schemas, errors and observations with actual Codex use. No new model runner is needed. |
| Treat play as a conversation. Add automatic feedback after actions and rounds. | Compact actions return receipt plus the actual decision. end_turn returns the next decision after combat or the completed lobby. Projection and output validation occur before the transaction commits. | Make these ordinary MCP results the conversation. Add concise derived feedback only when a measured decision problem needs it. |
| Download data locally and organize it with SQL. | Original Set 4 static sources are now verified. Historical ranked match data is not. | Build a versioned offline knowledge dataset first. Keep source descriptions, curated strategies and measured simulator outcomes distinct. |

The [MCP tool specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) defines ordinary tool results and structured output schemas. It does not require a server-side chat runner. [Codex's documentation](https://developers.openai.com/codex/mcp/) supports local stdio servers and initialization instructions, including self-contained workflow guidance in the first 512 characters. The [OpenAI API MCP guide](https://developers.openai.com/api/docs/mcp) addresses remote plugin and retrieval integrations; its example does not require replacing this local gameplay server.

## The actual conversation

The existing compact interaction is:

```text
Codex reads one decision and chooses an individual action.
The session validates it, runs the native action and baselines, and checks its effects.
The same transaction produces the receipt and a detached decision.
Transport validates the registered output schema and commits the audit.
Codex receives the result and chooses again.
end_turn releases planning and returns the next round or terminal decision.
```

The model-facing observation must contain literal IDs, locations, prices, resources and the remaining budget. The simulator remains authoritative for combat, rules and randomness. A prose summary must derive from observed changes. It cannot invent combat events that were not captured.

Unsolicited server notifications are unnecessary for this synchronous workflow. Their existence would not establish that a host adds them to model context. A custom automated chat loop would duplicate the native host's job.

## What the native evidence tells us

The retained Codex game used `gpt-6-luna`, seed 0 and 109 MCP calls, finishing in placement 7. There were 17 rejected actions: eight board-capacity move attempts, seven full-bench purchases, one unaffordable XP purchase and one empty-shop purchase. The audited errors already reported the relevant resource and available/required values. These observations identify a capacity and stale-slot reasoning problem; they do not establish that missing game feedback caused it. See [verification.md](verification.md) and the retained `logs/luna/audit.jsonl`.

A useful follow-up is to reinforce existing observation semantics: check regular-unit capacity before moving into an empty board location, use an occupied target for a capacity-neutral swap, check bench room or a reachable native merge before buying, and use actual post-action shop slots. A rejected request should change the next decision rather than produce repeated identical attempts. Measure these error categories over the same seeds before claiming improvement.

Smaller payloads and one completed game establish usability. They do not establish model superiority or strategic strength. A comp dataset can improve strategic context, but it cannot repair a protocol or capacity misunderstanding by itself.

## Prepared architecture proposal

The owner selected MCP-internal observations and accepted this bounded architecture contract on 2026-10-12. SPEC records the resulting responsibility changes while preserving behavior. Keep one reviewable working diff, the concrete GameSession adapter, both existing profiles and all current response contracts. No publication or operator configuration change is part of this work.

| Module | Responsibility and interface | Dependency direction and benefit |
| --- | --- | --- |
| tool_schemas.py and tools.py | Own shared record schemas and explicit tool declarations respectively. Reuse location, unit, status and decision schemas. | Protocol modules import these declarations. This separates protocol shape from process lifetime. |
| tool_calls.py | Own one validated, audited call path for the existing concrete GameSession, including a call lock around validation, execution and failure recording. Check availability and inputs, explicitly select the session method, build compact output, validate it and record the result within the existing transaction. | Depends on declarations, errors and the concrete session. Error translation and failed-request auditing belong to this same path. Keep explicit selection, without a handler registry or generic gameplay dispatcher. SDK memory tests exercise the same path as production. |
| transport.py | Own SDK registration, initialization instructions, stream wiring and startup/shutdown. | Depends on the concrete call path. It contains no native game rules. The selected session can be used with real SDK memory streams without replacing the process constructor. |
| purchase.py | Hide native purchase/sale offer checks, pricing, catalog consistency, inventory consequences and postconditions behind purchase/sale contracts and receipt construction. | Depends on concrete helpers and snapshots. GameSession keeps the transaction, budget and controlled_action seam. Locality improves because session no longer needs contributor ordering and item-return accounting. |
| action_helpers.py | Keep the one implementation of native locations, merge safety and copy accounting used by purchase, movement and equipment. | Does not import GameSession or protocol modules. Duplicator and purchase share merge validation. Extract a further module only for an actual responsibility, not a line-count target. |
| state.py | Own detached visible snapshots and shared board, bench, item, shop and trait projections. | GameSession chooses visibility, freezes once, and selects live versus retained terminal state. Preserve full category slots versus compact occupied slots and the two round values. |
| session.py | Own lifecycle, scheduling, atomic recovery, simulator scope, RNG isolation, public visibility and audit commitment. Orchestrate the concrete action modules. | Depends on the installed simulator and concrete modules. The simulator never imports MCP. Its transaction continues to contain native execution, baselines, projection, schema validation and audit publication. |

The module interface should hide knowledge, not merely relocate methods that require every GameSession field. Depth means leverage for callers. The existing concrete adapter is sufficient; a second backend or provider framework is unsupported. Each seam retains the same production and test responsibilities. Apply the deletion test: removing purchase.py should force catalog/inventory/postcondition knowledge back into session, while removing a pass-through wrapper should remove no knowledge.

Share the budget guard between require_action_budget and controlled_action. Reuse offer consistency and native price lookup between shop projection and purchasing, with the existing error contracts. Share validators across MCP calls and direct session entry points. Those two entry points still need protection; repeated validation calls are different from duplicated validation implementations.

Keep the async call lock outside the copied session state. It serializes the whole protocol request, including a rejected request's audit record. The session's existing SIMULATOR_LOCK still isolates process-native state and commits. Profile configuration validates before session construction; compact startup keeps its own lifecycle transaction. Share only offer identity derivation and the installed price-table lookup. Purchase/sale retain their playable-unit, supported-star and cost-consistency checks; read projection must not gain action-only restrictions.

An independent read-only review found the proposal coherent and identified these lock and pricing details, which are now explicit. Existing implementation evidence remains historical until the proposed refactor is implemented and verified.

## Simulator fork finding

Read-only inspection found `/home/kyle/CodingProjects/TFTMuZeroAgent` clean on main at `80de4e9e45cecf5e53fd642c336eec59241a80d2`. Its complete Git tree is `67f6792d194c08a618d347192ca5fb624c4d9f1e`, identical to pinned upstream `33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d`. The preceding repository extraction already removed the old source modifications. Cached remote refs were inspected without fetching; this does not claim fresh remote state.

No reset is needed. Historical feature branches, ignored logs and caches remain preserved. A native detached visible-state helper remains an optional future design if a second simulator caller needs it. It must be independent of MCP schemas and gameplay rules, read-only, RNG-neutral and tested for actual field fidelity and eliminated-player handling. Current evidence supports completing the MCP refactor first.

## Implementation order and acceptance

1. Extract concrete schema declarations and the complete audited call path. Verify default/compact discovery, strict arguments, initialization, profile isolation and real SDK result/error translation. Prove output/projection failure still rolls back the native action and audit.
2. Deepen purchase/sale and shared state projections. Verify ordinary and cascading merges, full bench, Chosen, item return/drop, Duplicator, traits, terminal own-state, read purity and direct-call protection. Retain actual native, baseline, observation, receipt, native-file and audit failure injection.
3. Run appropriate current checkout suites, deterministic action replay and production stdio full-lobby acceptance. A fresh noneditable external installation outside both checkouts establishes installed acceptance. Tie new evidence to its actual working-source and simulator identities.
4. Build offline knowledge only after a separate source/mapping contract. Start with Riot's original roster and descriptions, then validated historical descriptions. Add curated comps or measured simulator rankings only with their own evidence.

The accepted implementation contract keeps all tool behavior and simulator rules unchanged. A wider simulator change, a new knowledge tool or a changed default profile is a separate product decision. Independent contract review confirmed lock ownership, shared merge validation and existing fault-test seams before implementation. The owner's observation-ownership choice resolves the remaining grilling decision.
