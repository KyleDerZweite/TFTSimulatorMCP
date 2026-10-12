# Metabot archive feasibility

Investigated on 2026-10-12 against the installed simulator revision `33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d`. Metabot is technically extractable and offers clearer attributed-use terms than the previously investigated MetaTFT source. Original Set 4 recommendation compatibility remains unproven. This research does not add a runtime database, remote connection or gameplay tools.

## Access and reuse

The [official AI documentation](https://metabot.gg/de_DE/ai) describes a public read-only Streamable HTTP MCP endpoint at `https://metabot.gg/api/mcp`. No account or key is needed. It documents approximately 60 requests per minute per IP, a global limit and attribution to the exact source page. The investigation used bounded public requests rather than a bulk crawl.

The background research successfully tested initialize, tool discovery and two get_entity_build calls. Relevant discovered tools accept game, name and lang, without a historical set or patch filter. Sett resolves to a current patch 16.20 result at `DA_18_Sett`; requesting `TFT4_Sett` returns an unavailable-build fallback. A connection therefore does not establish historical access.

The [terms](https://metabot.gg/de_DE/legal/terms-of-service) grant attributed reuse of displayed/generated content and request reasonable automated access. Ordinary site use is described as personal/noncommercial. The inspected Dataset metadata declares CC BY 4.0. Preserve attribution and observed license metadata; these statements do not establish an unrestricted full-database mirror or a downloadable historical export.

## Archive evidence

The [Sett build page](https://metabot.gg/de_DE/TFT/unit/TFT4_Sett/build) returned HTTP 200 with rendered tables, Riot item identifiers and Dataset JSON-LD. A ten-row extraction sample is retained outside the repository at `/tmp/tft-metabot-sett-extraction-20261012.json`, explicitly unaccepted for simulator use. The raw public HTML sample is `/tmp/tft-metabot-sett-sample.html`.

The page labels itself a Set 4 archive, but its strongest build includes two TFT_Item_EmptyBag placeholders. Counted modern items and a tft_set4_5_revival splash reference require provenance clarification. Asset versions alone do not date matches. No inspected payload supplied match IDs, game versions, timestamps, queue IDs or an original-versus-revival distinction.

The [Sett comps page](https://metabot.gg/de_DE/TFT/unit/TFT4_Sett/comps) reports insufficient observations for ranked compositions. This inspected champion supplies no accepted comp catalog. It does not prove that every other archived champion lacks comp data.

The [methodology](https://metabot.gg/de_DE/data-methodology) describes Riot API match aggregation, CommunityDragon definitions and voluntary desktop-app submissions. It says data follow the latest patch and a patch switch waits for 100,000 matches. It does not explain original/revival archive separation or provide enough calculation detail to reproduce sample-size adjustment and tier rankings. Placement associations are not simulator-tested optimal strategies; Top 4 and first place are different outcomes.

## Installed-rule compatibility

The installed definitions identify Sett as a five-cost champion with the_boss and brawler. They contain jeweled_gauntlet, hand_of_justice, bloodthirster, thieves_gloves, infinity_edge and warmogs_armor. They do not contain TFT_Item_EmptyBag, strikers_flail or edge_of_night. Matching a name or mapping a Riot identifier does not establish matching effects, recipes, historical patch rules or statistical relevance.

Riot's [Fates introduction](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-fates/) places original Fates at patch 10.19. Riot introduced Hextech Augments later with [Gizmos & Gadgets](https://teamfighttactics.leagueoflegends.com/en-au/news/game-updates/gizmos-gadgets-set-mechanic-overview-hextech-augments/). Its [Festival of Beasts revival explanation](https://teamfighttactics.leagueoflegends.com/en-gb/news/game-updates/revival-the-return-of-festival-of-beasts/) describes changed mechanics and notes that Augments did not exist in the original set. The installed Simulator has no augment paths or supported augment decisions. Original Set 4 augment recommendations cannot be treated as an available simulator category.

## Consequence for this project

Metabot can support attributed exploratory lookup or a carefully validated derived snapshot. It currently cannot establish an original-Set-4 statistical recommendation database for this simulator. Keep installed rules authoritative, source recommendations separately identified and incompatible or unverified records out of accepted gameplay lookup. Do not replace unsupported IDs with plausible modern names, reinterpret placeholders as equipment, invent phase-specific comps or rank tiny samples as proven optimum.

The architecture review remains at candidate selection. No new lookup interface, database schema or implementation contract has been accepted. Any selected data work must settle source provenance, compatibility, supported recommendation categories and acceptance evidence before adding gameplay tools. Existing simulator code and rules remain unchanged.
