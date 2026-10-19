# Verification

Checked on 2026-10-12. Tested MCP revision `3edc3ef69befe1c95b6782d3b2be88c7188f0150`, PR base `63c55f76e0a7649633ee208ba70650c495f36e24`. Subsequent verification-only edits leave production and tests unchanged.

The simulator remains unchanged at `33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d`. Installed source SHA-256 is `43db488008ac7503201978bef81230635d65a7d15c37b82b6cd368d2fa669dcb`.

| Check | Result |
| --- | --- |
| Full checkout suite | 345 passed in 579.56s. |
| Fresh installed SDK acceptance | 5 passed in 225.66s, outside both checkouts without `PYTHONPATH`. Includes three-process replay, all 16 tools, budget, audit recovery and graceful shutdown. |
| Native Codex GPT-6-Luna, low, seed 0 | Completed lobby, placement 5. Skill loaded. 125 calls, 112 successes, 13 rejections. Terminal state and all eight placements verified. |
| Artifact identity | All 17 installed production modules and the skill match tested source byte-for-byte. |
| Independent reviews | Standards 0 findings; Spec 0 findings. |

Evidence directory: `/home/kyle/.local/share/tft-simulator-mcp/single-mode-20261012-_ffc6i2b/`. It contains exact commands, source manifest, test logs, native session/audit and corrected test-adaptation failure records. Source archive SHA-256 is `77f3ec41bc056ae6545e2bd8fa567c0f280976f7e34f5aaa8ff6cfd8cdfa38b1`.

Codex termination skipped the graceful close audit callback. Terminal gameplay was committed, and no installed server process remained. SDK graceful close passed. Credentials and the saved TFT approval default remained unchanged; Codex rewrote configuration bytes, so whole-configuration preservation is unproven. No persistent server-entry update was performed.

No GitHub CI workflow, strength benchmark or authenticated Claude gameplay was checked. A completed game establishes usability, not improved playing strength.

Silver's feedback produced automatic lifecycle, shared observations, smaller modules and state after actions. `end_turn` remains a model decision. Codex owns the tool loop; Qwen-specific research adds no runtime requirement for this target. [Set 4 sources](set4-sources.md) remain a future offline-data foundation.

## Fork author checks on 2026-10-18

`get_champion_pool` was added after this record. The installed acceptance above does not cover it.

`search_comps_by_champions` and `search_comps_by_trait` were added on 2026-10-18. The index stores champion lists, trait levels, and per-champion item builds with at least 100 boards. `search_champion_items` reads those item builds. The tools do not take `min_games`. Installed SDK acceptance and native gameplay have not been rerun for them.

The model stream transcript was checked on 2026-10-18 from the dirty checkout at HEAD `e31c461a89ae5e84ed62d9f03953ab4ee2605186`. `tests/test_stream_log.py` passed 6 tests in 4.35s and `tests/test_protocol.py` passed 11 tests in 21.22s, using `/home/silver/R/T/.venv` (mcp 1.30.0) with `PYTHONPATH` and simulator revision `d66ce010736047ba914514f2fdd8428e20617030`. The full checkout suite, fresh installed acceptance, and native gameplay were not rerun.

The dependency pin is `a197a2a5bfab26c2900ac77e7b48c349efc14016`, which adds the language-model observation diff. Installed acceptance has not been rerun against that pin.

`TFT_MCP_MODE=single_player` was checked on 2026-10-18 against the simulator checkout at that same pin, with local controlled-step methods added on `TFT_Single_Player_Simulator`. `/home/silver/R/T/.venv` ran `UnitTests/single_player_controlled_test.py`, `test_single_player_env_income`, and `test_action_vector_single_player_steps`: 5 passed. With `PYTHONPATH=src`, `tests/test_single_player.py`, `test_opening_observation_includes_text_and_mask`, and `test_real_seeded_game_lifecycle_and_isolation`: 5 passed. The full checkout suite, installed acceptance, and a native single-player game were not run. The installed Cursor launcher does not include this mode until it is reinstalled.

Single-player tools were then narrowed the same day: `get_players` and `get_board` hidden, `get_last_fight` added, and a campaign summary added to the instructions from the new simulator `campaign_schedule()` and `last_fight`. Simulator `single_player_controlled_test.py`, `early_income_test.py`, `action_space_test.py`, `api_compliance_test.py`, `porosight_render_test.py` and `composition_test.py`: 46 passed. MCP `test_single_player.py`, `test_stream_log.py`, `test_decision.py`, `test_protocol.py`, `test_public_inspection.py`, `test_public_inspection_protocol.py` and `test_inspection_protocol.py`: 54 passed in 225s. A native single-player game is still unexecuted.

A Cursor installation was made on 2026-10-18 at `/home/silver/.local/share/tft-simulator-mcp/cursor-nvZ54sD6/`. Its source is the dirty working tree at HEAD `e31c461a89ae5e84ed62d9f03953ab4ee2605186`, tracked and untracked files without `data/`, archive SHA-256 `50cdc8a81ab2c589f315b8e2cc19612ab073bde7f3b598f5fd718a79a7f7d335`. `comps.sqlite` was copied beside it, SHA-256 `9939323da86b80fe775dbdcc9e5bc796d6ec7f3a9118c65a64ea564efb7ec50b`, and passed through `TFT_MCP_COMP_DB`. pip installed the simulator at the pinned revision with mcp 1.30.0. An SDK stdio smoke run from `/tmp` without `PYTHONPATH`, seed 0, listed 20 tools, returned the full first observation with seven baseline opponents, and answered `get_players` and `search_comps_by_trait`. `.cursor/mcp.json` registers that launcher as `tft`. The full checkout suite, installed SDK acceptance and a native Cursor game (Grok 4.7 High) were not executed.

Native logs became one in-place directory per game on 2026-10-18, with rollback from an in-memory snapshot and `python -m tft_mcp.native_logs` for legacy copies. The checkout suite, with the pinned simulator, ran 135 tests: 132 passed and 3 failed. The failures are `tests/test_single_player.py` (2, `TFT_Single_Player_Simulator` has no `actions_taken`) and `test_tools_describe_installed_simulator_without_set_selector` ("Set 4" in a comp tool description). Concurrent single-player and description edits landed during that run; those files are outside the log change. A rerun of `test_native_logs`, `test_session`, `test_progression`, `test_protocol` and `test_buy_sell` on the current tree passed 33. The change was applied to the Cursor installation's snapshot only, without the concurrent edits. Installed `test_native_logs` passed 5 from `/tmp` without `PYTHONPATH`. An installed SDK run with a masked sale and three `end_turn` calls left one native directory. The cleanup merged the finished Cursor Grok game `e1f7469fbb3a40978e56e72ec4df5047`, 156 directories totalling 94 MB, into one 1.2 MB `log.txt` ending at round 29. All 155 removed copies were verified as byte prefixes of the kept log first.
## Fork review on 2026-10-18

Compared main `e31c461a89ae5e84ed62d9f03953ab4ee2605186` with [Silver's fork](https://github.com/silverlight6/TFTSimulatorMCP/commit/0effceb0fddaff0fdebd42865930ed144f61d1ae). Four GPT-6.1-Sol subagents with High Reasoning reviewed standards, SPEC and the four proposed directions. Recommendation: defer a wholesale merge and assess the reusable components separately.

Standards: The documented setup needs the deleted mechanics skill. The built wheel contains the comp tools without their SQLite database. A transcript/audit path collision reproducibly corrupts the JSONL audit. The new log cleanup deletes other copies without checking their contents.

SPEC: The observation format, action limit, single-player mode and added tools change the existing contract. Preflight checks and postconditions are removed. The simulator pin also changes game rules. These changes need separate decisions and acceptance verification.

Tested simulator: `a197a2a5bfab26c2900ac77e7b48c349efc14016`, source SHA-256 `5d0b5b8f3bcf42818e51af5fb457aa27c7a35456351795abd1d9ef0bb2ef53f8`. Installed unchanged into a separate target directory, using other dependencies from the existing test environment and Python 3.14.7. Checkout testing with `PYTHONPATH` ran `tests/test_single_player.py -q --maxfail=1`: **2 passed, 1 failed** because `actions_taken` is missing. Other required methods, including `campaign_schedule`, are also missing. Wheel build and content inspection were completed. The initial build attempt failed because pip was unavailable; `uv build --wheel` succeeded.

The full suite, fresh installed SDK acceptance and native model games were not run for the fork. These checks do not establish installed acceptance. Evidence with identities, output and reproduction commands: `/home/kyle/.local/share/tft-simulator-mcp/fork-review-20261018-jrbhu1p0/`. Stream logging remains worth reviewing separately after fixing its defects.

Follow-up on the same day confirmed unchanged public MCP and simulator heads at the revisions above. The simulator's lobby controlled-step API, native observations, text deltas and rule fixes are public. Required single-player APIs remain absent from all ten checked public branch heads. A complete single-player handoff needs its simulator commit and an updated MCP dependency pin.

Reuse candidates include the visible-pool estimate, comp/item index and checksum-verified downloader, boundary transcript, native-log optimization, host documentation, and native observation/control integration. Database packaging, build-test fixtures, the deleted skill's setup references and logging defects need repair. Observation and action semantics need an explicit contract update; differences from the current SPEC alone do not make these features defective. Single-player needs the missing upstream source.

A broader checkout probe at the same source identities ran 44 selected tests: **32 passed, 12 failed**. Eight failures need the missing `data/set4/riot/items.json` build-test input; four need the single-player APIs. A separate SDK smoke test listed 20 tools and passed observation, pool, all three comp/item queries and `end_turn` against the committed database. It did not complete a game. These remain checkout checks, not installed acceptance. The first probe loaded the older simulator in SDK subprocesses; the corrected probe explicitly selected the paired sources. Both outputs and the correction are retained in `feature-recheck*.txt`, `feature-recheck-environment.txt` and `feature-sdk-xw12w9f_/` under the evidence directory above.
