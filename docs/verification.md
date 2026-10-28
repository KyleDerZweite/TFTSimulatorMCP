# Verification

## uv maintenance on 2026-10-28

Base and unchanged HEAD are `b6f8fe17c8b025d990256167a5c7440ed7da514d` on `main`. The repository was initially clean. This maintenance changes packaging and developer workflows. `SPEC.md` retains module ownership, protocol behavior and the MCP-to-simulator dependency direction. Runtime code, simulator rules and the simulator pin remain unchanged.

Development requires uv `>=0.13.5,<0.14` and the Python 3.14 line; the checks below used Python 3.14.8. The first checks below used uv 0.11.16 with an already installed interpreter. Independent review established that this older uv could not provision the pinned Python on a fresh host. Root verified that uv 0.13.5 lists and downloads Python 3.14.8 into a separate installation directory. Pytest moves to the default `dev` dependency group. The 52-package universal lock retains Python `>=3.10`; other Python versions resolved but received no runtime acceptance here. Native uv Dependabot configuration was removed before delivery because [GitHub currently supports uv 0.11](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories). Scoped manual updates remain documented, and simulator upgrades still require separate acceptance.

Root then completed a fresh locked noneditable installation with the downloaded
interpreter. Real SDK startup, initial observations and graceful shutdown passed
for the 20-tool lobby and 19-tool campaign, with the unchanged simulator revision
and source digest verified from the audit. Three installed protocol/restart checks
passed outside both checkouts without `PYTHONPATH`. These focused checks supplement
the earlier full-suite receipts below. They do not establish a new model-driven
game or complete campaign acceptance.

Package metadata now uses the existing `Apache-2.0` license expression and requires
Setuptools 77 or later. The `LICENSE` file and its terms are unchanged. Fresh
distribution builds include that license file.

| Check | Result |
| --- | --- |
| Lock and environment | `uv lock --check`, `uv sync --frozen` and `uv pip check` passed. |
| Build | `env -u APPIMAGE UV_CONCURRENT_BUILDS=2 uv build` produced an sdist and wheel. All 21 production modules match checkout; no simulator source is vendored. Existing setuptools license-table deprecation remains. |
| Runtime-only installation | `uv sync --locked --no-dev --no-editable` installed 36 packages. External SDK smoke checks passed 20/19 tools, initial observation and graceful shutdown in both modes. |
| Installed acceptance | 20 passed in 561.90 seconds. Includes exact three-process full-game replay and native late-campaign assertion/rollback. Ran outside both checkouts without `PYTHONPATH`, using the absolute installed launcher and a separate database. |
| Checkout suite | 207 passed in 1413.40 seconds with `env -u APPIMAGE PYTHONHASHSEED=0 PYTHONPATH=src uv run --locked python -m pytest tests -q`. |

The noneditable test environment has 41 packages, including MCP 1.30.0, NumPy 2.5.4, anyio 4.15.1 and pytest 9.2.0. All installed MCP modules and metadata match the final wheel. Installed simulator revision is `a197a2a5bfab26c2900ac77e7b48c349efc14016`, source SHA-256 `5d0b5b8f3bcf42818e51af5fb457aa27c7a35456351795abd1d9ef0bb2ef53f8`. No new model-driven host game was run.

No compatible encoder update was found on upstream's default branch or in open PRs. Upstream `main` remains exactly the simulator pin, with zero commits ahead and no open PRs. Its [native encoder](https://github.com/silverlight6/TFTMuZeroAgent/blob/a197a2a5bfab26c2900ac77e7b48c349efc14016/Simulator/encoding/token/basic_observation.py#L385) still asserts `game_round < 40`. The late-campaign regression proves the error and rollback. Complete 45-round campaign acceptance remains blocked, with assertions enabled.

Remote default HEAD matches local HEAD; there are no open PRs or dependency-update PRs. Dependabot vulnerability alerts were enabled and confirmed with HTTP 204. The paginated inventory then returned zero alerts, which does not establish a scan of this unpushed lock. Automatic security updates remain disabled; secret scanning and push protection remain enabled. Code scanning remains unavailable, HTTP 404 `no analysis found`. GitHub also created its managed `Dependency Graph` entry at `dynamic/dependabot/update-graph`; no repository Actions CI workflow was added. Issue #2 remains unchanged; local docs record its current 20/19-tool acceptance. The older 16-tool verification below remains historical.

Parallel setup initially hit a 300-second uv Git-cache lock timeout. The first sync later ended with signal 143, cause unconfirmed. A duplicate checkout download was stopped before tests began; serial setup then reused the completed cache. Failed setup logs and final test receipts remain separate.

Evidence: `/home/kyle/.local/share/tft-simulator-mcp/uv-maintenance-20261028-trbpq25z/`. The `source/` directory captures this working diff, not a committed revision. Receipts contain exact commands and environments. No commit, push, merge, deployment or persistent host registration occurred. Independent review remains Root-owned.

## Isolated native Codex game on 2026-10-19

MCP `f43e6608bfb04d2b1ca983ecb1d410f372a3ef11`, with all 21 installed production modules matching checkout, ran one full lobby against seven unchanged baselines. The simulator retains the PR 9 revision and digest below. Native Codex 0.163.0 used GPT-6.1-Sol, High Reasoning and seed 0. Player 0 placed 2nd of 8 with -6 health at level 9. The terminal observation reports round 31; native progression last resolved round 30. The process finished in 14m30s with exit code 0.

All 237 individual TFT calls match across native host events, MCP transcript and audit. There were 235 successes, one `unknown_champion` lookup and one `masked` move. No shell or code tools supplied gameplay. Final `get_players`, repeated terminal `get_decision` and `lobby_complete` agree on the result and all eight placements.

The external host used per-process MCP overrides, ignored user configuration and required ChatGPT login with the API key unset. Its old global `tft` registration was backed up privately and removed. Previous unrelated settings and authentication bytes remain unchanged. An additional unrelated project entry appeared during the run and was preserved. Observed child processes stopped, but `game_closed` was absent. A hosted ChatGPT connector transport warning did not interrupt the local game. This single game establishes the installed host journey; broader playing strength and single-player model gameplay remain unverified.

Evidence: `/home/kyle/.local/share/tft-simulator-mcp/isolated-model-game-20261019-crm5p3_j/`, including exact invocation, source identities, logs, `run-summary.json` and `parent-verification.json`. No production or test code changed for this check.

## Test consolidation on 2026-10-19

Tested MCP head `bb28c7c7e0bd6eaadd0caa5706d0c93f6f80c539` against base `d5a21f57f19c3eec503a6733cc28e5dd809116f3`. Single-player tests now share one module; logging and catalog tests share setup and overlapping journeys. Tests shrink by 127 lines. Both game modes, production modules and shared test helpers remain unchanged.

The four affected modules and `test_comp_download.py` passed 93 checks in 21.21s. Seven installed SDK checks passed in 13.38s outside both checkouts without `PYTHONPATH`, using the existing noneditable installation and rebuilt local database. All 21 installed production modules match checkout bytes. The simulator retains the PR 9 revision and digest below. Independent Standards and Spec reviews reported no findings.

The redundant final-victory xfail was removed. The actual native late-campaign error and rollback regression remains; complete 45-round acceptance still requires the upstream encoder fix. The full suite and model games were not rerun for this test-only change.

Exact commands, source identities, logs and JUnit results: `/home/kyle/.local/share/tft-simulator-mcp/test-consolidation-20261019-lqw4y2/`.

## Skill-free setup and local reference on 2026-10-19

Checked from base `ace84a75b8e962ffbc2db1efe274a449105f7aa9` with only skill and documentation changes. MCP initialization instructions and tool descriptions supply gameplay mechanics. Setup no longer installs or invokes a repository skill.

The existing `comp_download` command revalidated the previously downloaded Kaggle CSV and Riot items against their pinned hashes. A fresh `comp_index --database data/set4/player-results/comps.local.sqlite` build processed 748,928 boards. All seven ordered application tables and the schema match the committed reference; SQLite integrity is `ok`. The result contains 682 comps, 5,994 trait rows and 4,352 item builds. Its SHA-256 is `1829f0dd970b314fb07b5b1840f40f5c9351e84bef825f7f68b60a79d49b04b5`. The local database is ignored by Git and selected through `TFT_MCP_COMP_DB`.

Installed SDK checks ran from empty external host directories without a skill or `PYTHONPATH`. Both modes supplied initialization instructions, listed 20/19 tools, answered all three data-query families from the rebuilt database, preserved observation state across reads, progressed a round and shut down gracefully. Production code and the simulator retain the PR 9 identities below. These are scripted SDK checks; no new model game or full-suite run was performed for this documentation change.

Evidence: `/home/kyle/.local/share/tft-simulator-mcp/skill-free-data-20261019-yq1fgtlv/`, including build output, source URLs/hashes, ordered-table checks and SDK receipts.

## PR 9 integration on 2026-10-19

Tested MCP revision `1b9f753cf53312e12a4d1f7f0bece04a7a6d7f63`, main base `b72adbf3dc18f930630a564d6625d06778b30cab`, original PR head `0effceb0fddaff0fdebd42865930ed144f61d1ae`. Later documentation edits leave production and tests unchanged. The accepted contract is this PR's 20-tool lobby and 19-tool campaign, with native validation and observations.

The simulator remains unchanged at `a197a2a5bfab26c2900ac77e7b48c349efc14016`, source SHA-256 `5d0b5b8f3bcf42818e51af5fb457aa27c7a35456351795abd1d9ef0bb2ef53f8`. A concrete MCP adapter uses its published single-player Gym interface, without requiring unpublished simulator methods.

| Check | Result |
| --- | --- |
| Final checkout suite | 213 passed, 1 expected failure in 923.71s. The expected failure is the native late-campaign encoder limit. |
| Fresh installed SDK acceptance | 13 passed in 343.38s. Includes all 20 lobby tools, three-process full-game replay, 19-tool campaign startup, native campaign loss, audit recovery and shutdown. |
| External data rebuild | 748,928 boards; all seven tables and metadata match the committed database; 4,321 query comparisons passed; SQLite integrity `ok`. |
| Installed identity | All 21 Python modules match tested source. Noneditable installation, Python 3.14.7, MCP 1.30.0. |
| Independent reviews | Standards and Spec reported no remaining adapter findings. Final docs review corrected mode-specific registration descriptions. |

Installed checks run outside both source checkouts with `PYTHONPATH` unset and `TFT_MCP_COMP_DB` pointing to a separate database. Checkout checks use `env -u APPIMAGE PYTHONHASHSEED=0 PYTHONPATH=src <venv>/bin/python -m pytest tests -q`. Installed checks select `test_acceptance.py`, `test_single_player.py` and the SDK test for native campaign loss with the absolute installed `TFT_MCP_TEST_COMMAND`.

The native token encoder asserts `game_round < 40`, although its campaign has 45 controlled rounds. Late progression rolls back, and the final-win test reports this upstream failure as expected. Complete campaign acceptance remains blocked. Assertions stay enabled. Native Codex/Claude model games and playing strength were not checked for this revision. The fork author's Cursor canvas benchmark report was not rerun or rendered. There is no GitHub CI workflow, deployment or persistent host configuration change.

The initial partial suite reported 97 passed and one obsolete description assertion before interruption in a raw protocol test. That test passed separately. Failed fixture and replay probes remain in the evidence logs; corrected rollback and delta tests passed. Active episode RNG remains part of the replay comparison.

Evidence root: `/home/kyle/.local/share/tft-simulator-mcp/pr9-20261019-b5mihahz/`. It retains failed and final logs, archive, installed identity and data manifest. Tested archive SHA-256 is `1280f988d88847c0a0986d9dc6514fdb4183f0bdd194d4ffa6b3cb24dfc91c10`. Downloaded CSV SHA-256 is `df73994ce6172fd810846c92b66c099db488b5af12b27521a6e63fff18882f4e`; items SHA-256 is `f8c7c36a9d52caeab2ccd33fb6c0c224f246b35ff074bdce21d64d4661ac46f0`; database SHA-256 is `9939323da86b80fe775dbdcc9e5bc796d6ec7f3a9118c65a64ea564efb7ec50b`. Raw sources are separate downloads; the committed SQLite index supports runtime queries.

## Earlier verification

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
