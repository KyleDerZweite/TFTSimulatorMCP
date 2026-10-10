# Standalone migration verification

Verification date: 2026-10-11. Reviewed split contract: `7daa5c380a7d4c791dce091249d86be590a018db`. Implementation base: `da519e9278ba2facb5b5d1227d4ccd63492ef002`. Frozen functional MCP source: `bc8847eb4541e1898030e09f50a11c627a40e1e1`. Production source and tests stayed unchanged during the complete runs. Test-only identity follow-up: `367eff4fe1669c6845c095a43a376f0a52b90520`. Production modules remain byte-identical to the frozen installation; subsequent documentation records the evidence.

The MCP-only filtered history came from original revision `7fff190eb83af3d837fb74abfbb8a6fe7c30d2aa`. The standalone package contains no Simulator, UnitTests or training source. `tftmuzero-mcp` retains the `tft_mcp` import and `tft-mcp` launcher, so installation uses a fresh environment rather than mixing the historical distribution.

The fresh protected environment is `/home/kyle/.local/share/tftmuzero-mcp/standalone-20261011/venv`. Its noneditable MCP source archive has SHA-256 `e737c609ff9d5e6be35aa1d1a389b31d89195ed994c70aba7ca65234527b0253`. Pip resolved the declared Git simulator dependency automatically. Installed `direct_url.json` records simulator commit `33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d`; its actual Python source digest is `43db488008ac7503201978bef81230635d65a7d15c37b82b6cd368d2fa669dcb`. These values identify separate repositories.

Python 3.14.7, MCP 1.30.0, NumPy 2.5.4, PettingZoo 1.27.0, Gymnasium 1.4.0 and pytest 9.1.1 were used. Both project distributions are version 0.1.0. Imports outside both checkouts resolve inside the new venv. All seven installed MCP Python modules match the frozen source byte for byte. The built wheel contains only `tft_mcp` and distribution metadata, including the Apache license.

| Check | Result |
| --- | --- |
| Git dependency install, noneditable imports, `pip check` | Passed |
| Wheel separation and seven production module identities | Passed |
| Final provenance and acceptance-boundary checks at 367eff4 | 7 passed in 1.18s; identity helper passed against all six retained production startup audits |
| Complete migrated MCP suite at bc8847e | 329 passed in 657.52s |
| Installed official SDK protocol and acceptance | 11 passed, 4 source-fixture cases deselected in 376.18s |
| Local Markdown targets, documented shell syntax, `git diff --check` | Passed |
| Independent Standards and Spec reviews | Spec had no actionable findings; Standards found one stale simulator test command, removed; final evidence refresh pending |

The frozen suite retains every original MCP case except four obsolete monorepo scope cases and adds six provenance cases. Review later found that an acceptance assertion incorrectly rejected an installed venv beneath a checkout. The test-only fix verifies that the loaded Simulator directory equals its distribution directory instead. A new real-session regression demonstrates that the enclosing checkout is permitted. Final collection has 330 tests; the complete frozen 329-case run and the focused seven-case refresh establish the changed evidence. The full suite was not repeated for this test-only correction. It includes read purity, strict schemas, transactions, RNG isolation, rare real-session fixtures and complete games. Installed checks use the official SDK and absolute production launcher, with no custom LLM runner or simulator mocks. Three fresh processes replay the same full-game action tape; the third adds reordered/repeated reads and a legality rejection. They compare every receipt, category checkpoint, baseline action, source identity, outcome and all eight placements, then verify terminal inspection, rejection, close and idle. The seed-0 replay used 20 gameplay actions, including 13 end_turn calls. All processes completed the lobby at round 24 with controlled placement 8 and equal placements; SDK call counts were 307, 307 and 494. This establishes operability and determinism, not game quality.

The exact complete-run commands use separate retained basetemp directories:

```sh
TFT_CHECKOUT=/tmp/tft-mcp-worktrees/standalone-migration
TFT_INSTALL=/home/kyle/.local/share/tftmuzero-mcp/standalone-20261011
cd "$TFT_INSTALL/host"
env -u APPIMAGE -u TFT_MCP_TEST_COMMAND PYTHONHASHSEED=0 PYTHONPATH="$TFT_CHECKOUT/src" "$TFT_INSTALL/venv/bin/python" -m pytest -c "$TFT_CHECKOUT/pyproject.toml" "$TFT_CHECKOUT/tests" -q --basetemp="$TFT_INSTALL/logs/full-suite-2"
env -u APPIMAGE -u PYTHONPATH PYTHONHASHSEED=0 TFT_MCP_TEST_COMMAND="$TFT_INSTALL/venv/bin/tft-mcp" "$TFT_INSTALL/venv/bin/python" -m pytest -c "$TFT_INSTALL/source-bc8847e/pyproject.toml" "$TFT_INSTALL/source-bc8847e/tests/test_protocol.py" "$TFT_INSTALL/source-bc8847e/tests/test_acceptance.py" -k 'not invalid_output' -q --basetemp="$TFT_INSTALL/logs/installed-sdk-1"
```

Logs and SDK transcripts remain in the protected installation's `logs` directory. `identity-bc8847e.json` records actual interpreter, imports, package versions, both distribution provenance records and archive checksum. `install.log`, `full-suite-2.log`, `installed-sdk-1.log` and `provenance-3.log` retain command results. `identity-helper-refresh.json` names all six revalidated startup audits; `replay-summary-bc8847e.json` records the outcomes. Initial provenance tests failed because their test distribution stub omitted `version`; fixing that fixture produced six passes. The premature first full-suite attempt was interrupted and its log/artifacts were retained separately.

No new native LLM full game is claimed by these SDK checks. The historical Codex game at original MCP source `c4011d0ea32441b58827fb04b7a1720d8471a06c` completed on 2026-10-10 with seed 0, 129 MCP calls, 25 end_turn calls, round 29 and controlled placement 4. That evidence establishes the historical installation's usability only. It does not prove the new standalone installation or model skill. Native target verification and publication belong to the parent task. Authenticated Claude gameplay remains unverified. Configuration, credentials and retained historical logs were not changed by this migration writer.
