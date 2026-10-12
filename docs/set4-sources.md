# Set 4 sources

Checked on 2026-10-12. [Riot's original Fates archive](https://static.developer.riotgames.com/docs/tft/set4.zip), linked in the [previous-set documentation](https://developer.riotgames.com/docs/tft#previous-sets), contains 58 playable champions, 54 items and 26 traits. It supplies IDs, roster membership and item/trait descriptions, without an exact balance patch or comp statistics.

[CommunityDragon 10.24](https://raw.communitydragon.org/10.24/cdragon/tft/en_us.json) adds champion stats, ability templates, effects and recipes. Filter its 61 units through Riot's playable roster to exclude Galio, Nexus and Azir's soldier. Preserve unresolved template variables. Five checked simulator values match 10.24; full compatibility remains unproven.

These archives can support future offline explanations after explicit ID mapping and compatibility checks. Installed simulator definitions remain authoritative. No historical comp/winrate dataset was verified, and [Augments arrived later with Gizmos & Gadgets](https://teamfighttactics.leagueoflegends.com/en-au/news/game-updates/gizmos-gadgets-set-mechanic-overview-hextech-augments/). A SQLite recommendation database would need curated entries or measured simulator experiments.

No archive is packaged into runtime. This keeps the current adapter small. Before distributing derived data, check its reuse terms and retain attribution.

Retained downloads: `/tmp/tft-set4-sources-20261012/`. SHA-256: Riot `81d8ca41149e9dd6e99c059ad10350092e104048c9c818b3688f2430f2a3ba2a`; CommunityDragon `1e98f4e646c46bbda8e23e8816fe16847f1f7052ff538a6282213fe7ae53ace9`.
