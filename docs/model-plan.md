# Compact native model play

Accepted revised direction on 2026-10-12 prioritizes the existing Codex harness with `gpt-6-luna`. The initial Qwen investigation found context-allocation, argument-shape and round-boundary issues. The owner chose Codex before delivery. The optional Qwen host and dependencies were withdrawn. Research and partial target evidence remain recorded; discussion alone was not treated as an accepted scope change.

Delivery is one integration PR based on `63c55f7`. The owner invoked the pr skill after verification, authorizing commit, branch publication and PR creation for the complete working diff. Deployment, merging, persistent native configuration changes and changes to the simulator repository remain outside this delivery.

## Reviewed design contract

The unchanged simulator owns mechanics and combat. GameSession owns seed, lifecycle, scheduling, transactions and visibility. The concrete protocol modules own MCP schemas, profile selection and response formatting; transport owns process lifecycle and SDK stream execution. Codex owns inference, MCP execution and conversation history. No custom provider framework, client loop or replacement parser is needed.

The default profile keeps explicit lifecycle and existing receipts, adding one read-only `get_decision` tool. The decision combines own economy, occupied board/bench/inventory, shop offers and nonzero stored traits, with lifecycle status and a separate snapshot round. Freeze own state once under the lock. It never reveals opponents' shops, consumes randomness or advances play. Prices, XP thresholds and capacity come from the installed player state. No fixed game duration or copied set catalog is added.

The opt-in `TFT_MCP_PROFILE=compact` process requires `TFT_MCP_SEED` in the canonical seed range. Validate configuration before constructing the simulator, start one game per process and close it at process shutdown. Discovery contains `get_decision`, seven individual actions, six catalog tools, `get_board` and `get_players`. Reject omitted tools. `end_turn` remains explicit because it releases the reserved planning slot. Its compact response is the next decision; other actions return the existing receipt plus a decision. Projection, validation and audit publication stay inside the same transaction, so projection failure rolls back the whole action. Preserve terminal lobby and own-state round values separately.

Internal helpers are extracted by existing responsibility into errors, action/location helpers, state projections/receipts, movement, equipment and simulator identity. They remain ordinary concrete functions. Helpers never import the session; Simulator never imports this package. Session-level helper imports preserve established test seams.

Location schemas explicitly expose object type and fields as well as their original strict board/bench alternatives. This preserves exact argument shapes and legality while avoiding ambiguous host schema rendering. Native Codex tools receive these same self-contained schemas. Keep prompts short and use actual post-action observations. Do not infer strategic strength from model size or nominal usage limits.

MetaTFT remains research-only. An offline comp catalog needs reproducible original Set 4 data, provenance, reuse terms and installed-rule compatibility. No statistics or builds are invented.

## Review and verification

Initial independent design review required one frozen own snapshot, strict startup validation, separate terminal snapshot_round and atomic post-action projection. Both independent implementation reviewers verified extracted responsibilities and found seed normalization and optional-host evidence defects; those were fixed. The owner subsequently withdrew the optional host, leaving the native Codex interface for final review.

Verify default compatibility, compact discovery and omitted-tool rejection, strict seed/config validation, read/RNG purity, native prices/XP, terminal snapshots, failure rollback and simulator source identity. Exercise production stdio, a complete lobby and deterministic full-game replay. Installed acceptance uses a fresh noneditable external environment outside both checkouts without PYTHONPATH.

A real GPT-6-Luna native game establishes client operability. Retain model/session identity, source identity, seed, ordered calls, all placements, terminal decision and shutdown close. Preserve saved approval policy; a disposable session may override launcher/args/TFT environment only. Persistent registration and owner acceptance remain separate. Record exact tests, failures, unavailable evidence and final working-diff identity in verification.md.

## Progress

Research and initial design review completed. Revised Codex contract reconciled before dependent implementation. Model-neutral implementation, current affected checks, installed SDK acceptance and the native GPT-6-Luna full game completed. Independent Standards and Spec reviews have zero unresolved implementation findings. Native graceful-close evidence remains open because Codex terminated the process before a game_closed record; the already committed terminal outcome is retained. This target limit and whole-config byte-digest observation are recorded in verification.md.

## Architecture and knowledge follow-up

The owner broadened the architecture goal on 2026-10-12 to readable modules and shared implementations across session, tools and helpers. They asked to prepare Silver's feedback against actual code and investigate original Set 4 sources instead of Metabot. [silver-feedback.md](silver-feedback.md) records that analysis and the proposed responsibility contract. [set4-sources.md](set4-sources.md) records independently checked downloads and sample compatibility. The prior Metabot note remains historical research, without an implementation dependency.

The current simulator fork's source tree already matches the pinned upstream. No fork reset is needed. The owner selected MCP-internal observation projection and accepted the bounded refactor. Deepen purchase/sale and shared state projections, separate schema declarations and the full audited call path from process startup, and keep existing behavior and rollback evidence. Simulator helpers, a changed default profile, new knowledge tools and ranked comps remain separate design decisions.

Independent contract review found no blockers. tool_schemas owns shared records and tools owns concrete declarations. ToolCalls owns the full async request lock, validation, explicit method selection, compact projection, output validation and success/failure audit. transport.run_session accepts an existing concrete session and SDK streams; startup configuration, construction, compact start and shutdown remain process-owned. purchase contracts hide offer/catalog/inventory/postcondition knowledge while Session keeps snapshots, execution and fault-test receipt seams. State projections share slot/trait formatting, preserving full versus compact visibility and both round values. Direct-call protection and shared merge validation remain. SPEC records these accepted responsibilities.

The accepted refactor is implemented. Module declarations and initialize instructions match the before-refactor snapshot exactly. The complete checkout suite passes 351 tests, including receipt/projection/schema and native/log/audit recovery. Fresh external installed acceptance passes five production scenarios, including exact three-process replay. A new native GPT-6-Luna game completes the lobby; all 107 calls match audit. Standards and Spec reviews have zero unresolved findings. The native close callback and whole-config byte preservation remain bounded target evidence gaps, documented separately from completed gameplay in verification.md. Tests/packaging match the frozen tested archive; five production files have only publication-time EOF normalization, with identical Python ASTs. Glossary and evidence updates are later prose. The owner subsequently requested the integration PR; persistent registration remains unchanged.
