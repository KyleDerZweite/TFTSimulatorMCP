# Original Set 4 source research

Investigated on 2026-10-12 for the installed simulator at `silverlight6/TFTMuZeroAgent@33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d`. The best verified foundation is Riot's original Fates archive, supplemented by historical CommunityDragon exports. These sources contain static knowledge, not composition win rates. Metabot is withdrawn from this work.

## Verified downloads

[Riot's previous-set documentation](https://developer.riotgames.com/docs/tft#previous-sets) links Fates to [set4.zip](https://static.developer.riotgames.com/docs/tft/set4.zip), separately from Fates: Festival of Beasts at set4update.zip. The downloaded original archive contains:

| File | Records | Available fields |
| --- | ---: | --- |
| champions.json | 58 | name, championId, cost, traits |
| items.json | 54 | numeric id, name, qualitative description |
| traits.json | 26 | key, name, description, origin/class type, activation breakpoints |

This supplies an original playable-roster filter and descriptive item/trait knowledge. It does not identify an exact balance patch or contain numerical champion statistics, ability scaling, recommended compositions or match outcomes.

The [CommunityDragon documentation](https://www.communitydragon.org/docs) explains its Riot-client exports. The verified [10.24 TFT export](https://raw.communitydragon.org/10.24/cdragon/tft/en_us.json) contains sets["4"], named Journeys, with 61 exported units and 26 traits. Champion records include apiName, traits, stats and ability descriptions/variables. Trait records include description templates and effect thresholds/variables. Items include effects, recipe IDs, uniqueness and description templates.

All 58 Riot champion IDs occur in the 10.24 export. Its additional units are TFT4_Galio, TFT4_NPC_Nexus and TFT4_AzirSoldier. They have plausible costs, so a cost filter would incorrectly accept summons and NPCs. Join against the original Riot roster. Some template variables are hashes rather than readable identifiers, so unresolved descriptions must remain marked instead of being filled by guesses.

10.25 and 11.1 exports were also downloaded and parsed by the research agent. The parent independently retained and checked the Riot archive and 10.24 export. Downloads and source manifest are outside the repository at `/tmp/tft-set4-sources-20261012/`. These exploratory files are not packaged or accepted for gameplay lookup.

| Download | Bytes | SHA-256 |
| --- | ---: | --- |
| Riot set4.zip | 1179582 | 81d8ca41149e9dd6e99c059ad10350092e104048c9c818b3688f2430f2a3ba2a |
| CommunityDragon 10.24 | 483307 | 1e98f4e646c46bbda8e23e8816fe16847f1f7052ff538a6282213fe7ae53ace9 |
| CommunityDragon 10.25 | 483508 | 19660dcb3cdb04a116aa39a3d56d416484d5af86ff0f5135cc407167998116d1 |
| CommunityDragon 11.1 | 483578 | 67ead721c3f1234cbb76e7066e3070d4b6be3f660a109ac94cee5ceea0cb888d |

Riot required no authentication. The research agent observed intermittent HTTPS 403 responses from CommunityDragon and succeeded over HTTP with a browser User-Agent. The parent's retained 10.24 download succeeded over HTTPS and matched the recorded hash. Neither observation establishes permanent endpoint availability.

## Compatibility with actual installed rules

The installed definitions match 10.24 in the checked examples. They differ from 10.25 and 11.1 in these examples:

| Field | Installed simulator | CommunityDragon 10.24 | CommunityDragon 10.25 |
| --- | ---: | ---: | ---: |
| Divine damage reduction / bonus true damage | 50% / 50% | 50% / 50% | 45% / 45% |
| Talon HP | 750 | 750 | 800 |
| Kalista attack speed | 1.0 | 1.0 | 0.9 |
| Xin Zhao attack speed | 0.8 | 0.8 | 0.85 |
| Yuumi HP | 600 | 600 | 650 |

[Riot's 10.25 notes](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/teamfight-tactics-patch-10-25-notes/) confirm those balance changes. This is sample compatibility, not proof that every simulator mechanic equals patch 10.24. Keep installed rules authoritative. Record external patch/source identity per entry and retain mismatches explicitly. A Set 4 archive label is not sufficient compatibility evidence.

Original Fates is distinct from the 11.2 mid-set and later revivals. [Riot's Festival of Beasts announcement](https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/festival-of-beasts/) identifies that mid-set release. Augments were introduced later with [Gizmos & Gadgets](https://teamfighttactics.leagueoflegends.com/en-au/news/game-updates/gizmos-gadgets-set-mechanic-overview-hextech-augments/). The installed simulator supports no augment decisions.

## Recommendations and statistics

The verified archives can support champion, trait, item, recipe and ability explanations. They cannot establish recommended comp rankings. No downloaded, reusable original Set 4 match-statistics dataset was verified in this investigation.

Riot's match API is a separate authenticated source. Its documentation says fresh data is cheaper; the investigation did not establish that original 2020 Set 4 matches remain retrievable. An indexed historical BunnyMuffins 10.25 article was found, but direct retrieval returned 403. It remains an unverified editorial candidate rather than a downloaded recommendation dataset. A guessed Meraki TFT repository returned 404; no verified historical Meraki dataset emerged.

A directly retrieved [Mobalytics Set 4 theorycraft article](https://mobalytics.gg/blog/tft/tft-best-synergy-combinations-set-4-predictions/) by AlanDood, dated 2020-09-03, describes carry selection, Chosen, transitions and example synergies. It explicitly presents PBE predictions before release. It can inform an attributed editorial template, but does not establish the later 10.24 meta or measured win rates. Copying a full article or treating predictions as statistical rankings is not part of this proposal.

Curated comp templates can be useful if their source and editorial status are stated. Generated candidate boards can be evaluated in this exact simulator. Such results must identify seeds, baseline opponents, strategy, sample count, mean placement, Top 4 rate and first-place rate. They are simulator experiment results, not historical ranked statistics. Early/mid/late strategy requires actual decision traces or editorial annotations; a final board alone cannot establish the transition path.

## Reuse and preparation

No independent permissive license for blanket redistribution of these Riot-derived exports was verified. Source code licenses for extraction tooling do not establish the data license. Preserve source identity and attribution, and review [Riot's published IP terms](https://www.riotgames.com/en/legal) and [developer terms](https://developer.riotgames.com/docs/tft) for the intended distribution. This research performs bounded public downloads; it does not publish a mirrored catalog.

A prepared offline knowledge design should keep source records and raw hashes, explicit canonical-ID mappings, compatible external descriptions, curated strategy records and measured experiment results separate. SQLite is sufficient for bounded joins and filters. No remote connection, provider framework or database server is needed during gameplay. Rule-query tools continue to read the installed simulator; external text and recommendations need their own accepted lookup contract.
