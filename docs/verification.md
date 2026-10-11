# Verification

The results below are historical split evidence under the preceding TFTMuZeroMCP name. The project is now named TFTSimulatorMCP; this documentation change does not rerun or extend these checks.

Verified on 2026-10-11. The reviewed standalone implementation is `5fa9552d1a3b503efcd76c2869d858dc3f1a858c`, based on `da519e9278ba2facb5b5d1227d4ccd63492ef002`. Production modules have not changed since frozen source `bc8847e`. The later `367eff4` correction affects an acceptance assertion and its regression test only.

| Check | Result |
| --- | --- |
| Complete suite at bc8847e, including full lobbies | 329 passed in 657.52s |
| Fresh installed official SDK, including three-process full-game replay | 11 passed in 376.18s; 4 checkout-only fixture cases deselected |
| Final provenance and installed-origin checks | 7 passed; updated helper revalidated against all six recorded startup audits |
| Git dependency, noneditable imports, pip consistency, wheel separation | Passed; all seven installed production modules match |
| Independent Standards and Spec review at 5fa9552 | No remaining findings |
| Real Codex execution on the standalone installation | GPT-6.1-Sol low called get_game_status; idle, exit 0 |
| Simulator fork cleanup | PR28 merged; entire resulting tree equals the pinned original simulator tree |

The replay exercised all 25 tools and compared receipts, reads, baseline actions and all eight placements. Reordered reads and a rejected action preserved the result. All six source/installed processes ended at SDK round 25 with controlled placement 8. This proves operation and determinism, not playing strength. Final collection has 330 tests; the full suite was not repeated after the test-only correction.

The protected installation is `/home/kyle/.local/share/tftmuzero-mcp/standalone-20261011`. Python 3.14.7, MCP 1.30.0, NumPy 2.5.4, PettingZoo 1.27.0, Gymnasium 1.4.0 and pytest 9.1.1 were used. The frozen noneditable MCP archive SHA-256 is `e737c609ff9d5e6be35aa1d1a389b31d89195ed994c70aba7ca65234527b0253`.

Pip installed the external simulator from Git commit `33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d`, confirmed by installed PEP 610 metadata. Its 53 Python files have source digest `43db488008ac7503201978bef81230635d65a7d15c37b82b6cd368d2fa669dcb`. The wheel contains only `tft_mcp` and package metadata, including the preserved Apache license.

Both existing native registrations use the new absolute launcher. The original Claude project scope remains unchanged. The scoped configuration patch verified full parsed preservation outside the approved launcher and three TFT environment fields, unchanged auth/settings bytes, policies, ownership and mode. Independent inspection verified current registrations and the actual Codex call. Original before/after preservation is writer-origin evidence. No session approval override was used.

The public [standalone repository](https://github.com/KyleDerZweite/TFTSimulatorMCP) preserves filtered MCP history. README and GitHub website link [Silverlight's original](https://github.com/silverlight6/TFTMuZeroAgent). Upstream Draft PR89 was closed without merging. [Fork PR28](https://github.com/KyleDerZweite/TFTMuZeroAgent/pull/28) removed the old MCP files at merge `80de4e9e45cecf5e53fd642c336eec59241a80d2`; simulator code and history remain intact.

Retained `logs/` evidence includes `full-suite-2.log`, `installed-sdk-1.log`, `provenance-3.log`, `identity-helper-refresh.json`, `replay-summary-bc8847e.json`, installation identity, native migration proof and `codex/idle-session.jsonl`. Native idle thread: `01a1283e-cc97-7223-ac99-c24069100d91`. `migration-verification-at-5fa.md` retains the exact test commands. The initial fixture failure was corrected; the interrupted first suite is retained and not counted as passed.

No new native LLM full game or authenticated Claude gameplay was run. The historical Codex game at original source `c4011d0` reached placement 4; it proves the earlier installation only. Claude registration reports Connected, while its earlier model attempt returned HTTP 404 before gameplay. GitHub CI, a Python version matrix and separate simulator UnitTests were not run for this migration. PoroSight integration and durable game resume remain outside the accepted contract.
