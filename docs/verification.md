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

## Fork-Prüfung vom 2026-10-18

Verglichen wurden Main `e31c461a89ae5e84ed62d9f03953ab4ee2605186` und [Silvers Fork](https://github.com/silverlight6/TFTSimulatorMCP/commit/0effceb0fddaff0fdebd42865930ed144f61d1ae). Vier GPT-6.1-Sol-Subagents mit High Reasoning prüften Standards, SPEC und die vier Zukunftsoptionen. Empfehlung: derzeit keinen Fork-Code übernehmen.

Standards: Die gelöschte Mechanics-Skill fehlt beim dokumentierten Setup. Das gebaute Wheel enthält die Comp-Tools, aber keine SQLite-Datenbank. Eine Kollision zwischen Transcript- und Auditpfad beschädigt reproduzierbar das JSONL-Audit. Der neue Log-Cleanup löscht andere Kopien ohne Inhaltsprüfung.

SPEC: Observation-Format, Action-Limit, Single-Player-Modus und neue Tools ändern den bestehenden Vertrag. Preflight-Prüfungen und Postconditions entfallen. Der Simulator-Pin ändert außerdem Spielregeln. Diese Änderungen brauchen getrennte Entscheidungen und Acceptance.

Geprüfter Simulator: `a197a2a5bfab26c2900ac77e7b48c349efc14016`, Source-SHA-256 `5d0b5b8f3bcf42818e51af5fb457aa27c7a35456351795abd1d9ef0bb2ef53f8`. Unveränderte Installation in einem separaten Target, übrige Dependencies aus der bisherigen Testumgebung, Python 3.14.7. Der Checkout-Test mit `PYTHONPATH` ergab für `tests/test_single_player.py -q --maxfail=1` **2 passed, 1 failed**: `actions_taken` fehlt. Weitere benötigte Methoden wie `campaign_schedule` fehlen ebenfalls. Wheel-Build und Inhaltsprüfung wurden ausgeführt. Der erste Build-Versuch scheiterte an fehlendem pip; `uv build --wheel` gelang.

Vollständige Suite, frische installierte SDK-Acceptance und native Modellspiele für den Fork wurden nicht ausgeführt. Das ist keine Installed-Acceptance. Evidence mit Identitäten, Ausgaben und Reproduktionsbefehlen: `/home/kyle/.local/share/tft-simulator-mcp/fork-review-20261018-jrbhu1p0/`. Stream-Logging bleibt nach Fehlerkorrekturen separat prüfenswert.
