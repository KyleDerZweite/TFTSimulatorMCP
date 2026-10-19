# Set 4 data

Collected on 2026-10-17. This folder holds the Set 4 archives that could be downloaded as files. Only `player-results/comps.sqlite` is loaded by the MCP server. Installed simulator definitions stay authoritative, and simulator source was not copied.

Set 4 is **Fates**. The playable shop is 58 champions, including Ahri, Aphelios, and Warwick. Set 4.5, **Festival of Beasts**, keeps a 58-champion shop and swaps 20 of those units. Both rosters appear below, in separate files.

## Layout

| Path | What it is |
| --- | --- |
| `player-results/kaggle/` | Real Challenger EUW games from original Fates, one row per player, with placement and the final board. |
| `riot/` | Riot's Fates archive: roster, trait, and item text, plus icons in the zip. |
| `communitydragon/` | Community Dragon `en_us.json` for every patch from 10.24 through 11.8 that still has the full Set 4 roster. |
| `tft-ddragon/festival-of-beasts/` | Name, cost, and text lists for the Festival roster from an archived Data Dragon commit. |

The Fates JSON in that same Data Dragon commit parses equal to `riot/champions.json`, `riot/traits.json`, and `riot/items.json`. Only the line endings differ, so it is not stored a second time.

## Real games

`player-results/kaggle/` is the [Fates Challenger EUW dataset](https://www.kaggle.com/datasets/mariuszmackowski/teamfight-tactics-fates-challenger-euw-rank-games), license CC0-1.0. It was scraped from the Riot API and published 2021-01-13, before Festival of Beasts. The zip is the download. `TFT_set4_euw_challanger_games.csv` is that zip's only file, 452,556,472 bytes, SHA-256 `df73994ce6172fd810846c92b66c099db488b5af12b27521a6e63fff18882f4e`. The zip SHA-256 is `8dae4c3229a8d8e13b6a20e454f92ab605bc30f8f1efb55e36d6bb83e482ab8c`.

The CSV has 748,928 player rows and 93,616 games. Placements 1 through 8 each occur 93,616 times, so every saved game has all eight players. Columns are `patch_version`, `match_id`, `puuid`, `placement`, `level`, `gold_left`, `last_round`, `time_in_game`, `total_dmg_to_players`, `players_eliminated`, `chosen_unit`, `chosen_trait`, `units`, and `traits`.

`units` is JSON. Each unit name maps to `items` and `stars`. `traits` is JSON of trait name to the number of units with that trait. There is no item name, no positioning, and no per-round history.

The `patch_version` values are 10.19 (22,696), 10.2 (42,872), 10.21 (61,168), 10.22 (97,336), 10.23 (102,560), 10.24 (154,336), 10.25 (258,800), and 11.1 (9,160). The boards are original Fates across those labels: Ahri appears in 82,363 rows and Aphelios in 41,226. Kayle, Samira, Ornn, and Xayah do not appear.

Only `player-results/comps.sqlite` and this README are committed. The CSV is too large for the repository. Download it, together with `riot/items.json` from the Riot archive below, with:

```sh
env PYTHONPATH=src python -m tft_mcp.comp_download
```

The command keeps only those two files and checks each against its pinned SHA-256. Kaggle serves the bundle without an API key.

## Comp index

`player-results/comps.sqlite` is the aggregate behind `search_comps_by_champions`, `search_comps_by_trait`, and `search_champion_items`. A comp is one exact set of champion names. Its win rate is the share of those final boards with placement 1 through 4. Trait level is the unit count stored in `traits`. An item build is the exact multiset of item ids on one champion. Champion lists below 100 boards are omitted, a trait level is omitted unless that count was recorded on at least 100 boards of that list, and an item build is omitted unless that champion carried it on at least 100 boards. Build a local reference from the downloaded CSV and items:

```sh
env PYTHONHASHSEED=0 PYTHONPATH=src python -m tft_mcp.comp_index \
  --database data/set4/player-results/comps.local.sqlite
```

The builder checks the CSV SHA-256 above, 748,928 rows, and 93,616 boards at each placement, then keeps the 682 champion lists, 5,994 trait levels, and 4,352 item builds with at least 100 boards. The committed reference is 675,840 bytes, SHA-256 `9939323da86b80fe775dbdcc9e5bc796d6ec7f3a9118c65a64ea564efb7ec50b`. Compare table contents when checking a rebuild; SQLite files can differ in physical row order.

The local file is ignored by Git. Set `TFT_MCP_COMP_DB` to its absolute path when starting the server to query it. The default still reads the committed reference.

## Riot Fates archive

`riot/set4.zip` is the file linked from [Riot's previous-set documentation](https://developer.riotgames.com/docs/tft#previous-sets). SHA-256 `81d8ca41149e9dd6e99c059ad10350092e104048c9c818b3688f2430f2a3ba2a`. The three JSON files beside it are the originals extracted from that zip.

| File | Records | Fields |
| --- | --- | --- |
| `champions.json` | 58 | `name`, `championId`, `cost`, `traits` |
| `traits.json` | 26 | `key`, `name`, `description`, `type` (`class` or `origin`), `sets` with `style`, `min`, and `max` |
| `items.json` | 54 | `id`, `name`, `description` |

The zip also holds icons: 58 champion PNGs, 54 item PNGs, 26 trait PNGs, 26 trait SVGs, and `traits/bg.png`. There is no combat stat, ability variable, or exact balance patch in this archive.

## Community Dragon

Each `communitydragon/<patch>/en_us.json` is the convenience dump from `https://raw.communitydragon.org/<patch>/cdragon/tft/en_us.json`. These dumps also contain empty entries for Sets 1–3. The Set 4 records are the ones that matter.

Top-level keys are `items`, `setData`, and `sets`.

- `sets["4"]` is named `Journeys`. Through patch 11.1 this is the Fates roster: 61 units and 26 traits. The 61 units are the 58 playable champions plus `TFT4_Galio`, `TFT4_AzirSoldier` (Sand Guard), and `TFT4_NPC_Nexus`.
- From patch 11.2, `sets["4"]` is still that Fates object, not the Festival shop. It grows to 62 units and 27 traits: `TFT_TrainingDummy` (Target Dummy) and a `Set4_Slayer` trait. Pyke, originally Cultist/Assassin, is also tagged Slayer in this object. Later patches keep editing these Fates records, so 11.2–11.8 are not a frozen opening-day roster.
- Festival of Beasts is a second `setData` entry, `mutator` `TFTSet4_Act2`, also numbered 4 and named `Journeys`. It is absent from 10.24, 10.25, and 11.1. From 11.2 it has 62 units and 27 traits. The same three non-playable units are present, plus Target Dummy, leaving 58 playable Festival champions. `sets["4"]` does not point at this entry.
- `items` is the patch item list, shared across sets in the file. It is not the 54-item Riot list. Counts are 105 on 10.24–11.1 and 120 from 11.2 onward.

A champion has `name`, `apiName`, `cost`, `traits`, `stats`, `icon`, and `ability`. The ability has `name`, `desc`, `variables`, and `icon`. One-star stats are `hp`, `damage`, `attackSpeed`, `armor`, `magicResist`, `initialMana`, `mana`, `range`, `critChance`, and `critMultiplier`. A trait has `apiName`, `name`, `desc`, `effects`, and `icon`. An item has `id`, `name`, `desc`, `effects`, `from`, `icon`, and `unique`.

Patch 11.9 replaces this with Set 5 and leaves only two Set 4 champions in the file. Those later dumps are not included. The current Community Dragon file does not contain this roster.

| Patch | `sets["4"]` champions / traits | Act 2 champions / traits | Items | Change from the previous retained patch |
| --- | --- | --- | --- | --- |
| 10.24 | 61 / 26 | absent | 105 | Earliest retained Fates dump. |
| 10.25 | 61 / 26 | absent | 105 | 19 champions, 6 traits, and 2 items differ. |
| 11.1 | 61 / 26 | absent | 105 | 15 champions and 3 traits differ. The item list matches 10.25. |
| 11.2 | 62 / 27 | 62 / 27 | 120 | Fates gains Target Dummy and Slayer. Festival Act 2 appears. 14 items are new and 9 existing items differ. |
| 11.3 | 62 / 27 | 62 / 27 | 120 | 4 Fates champions and 14 Festival champions differ. |
| 11.4 | 62 / 27 | 62 / 27 | 120 | 14 Fates champions and 28 Festival champions differ. |
| 11.5 | 62 / 27 | 62 / 27 | 120 | 5 Fates champions and 10 Festival champions differ. Trait text matches 11.4. |
| 11.6 | 62 / 27 | 62 / 27 | 120 | 10 Fates champions and 19 Festival champions differ. |
| 11.7 | 62 / 27 | 62 / 27 | 120 | 7 Fates champions and 14 Festival champions differ. The item list matches 11.6. |
| 11.8 | 62 / 27 | 62 / 27 | 120 | 4 Fates champions and 11 Festival champions differ. Last patch with the full roster. |

SHA-256 of each `en_us.json`:

| Patch | SHA-256 |
| --- | --- |
| 10.24 | `1e98f4e646c46bbda8e23e8816fe16847f1f7052ff538a6282213fe7ae53ace9` |
| 10.25 | `19660dcb3cdb04a116aa39a3d56d416484d5af86ff0f5135cc407167998116d1` |
| 11.1 | `67ead721c3f1234cbb76e7066e3070d4b6be3f660a109ac94cee5ceea0cb888d` |
| 11.2 | `e79b8d3bc86b4e684ba770a7236aafbf66b87e6a1e40ca79768945236b210765` |
| 11.3 | `4dc1c7345162203bf023c013a86441ebd75de923f9223077983503616c85c58c` |
| 11.4 | `ed953dce3f6c4f0a5101b05059ac048760112b641f21bdea35152bf207127531` |
| 11.5 | `27809db281a74e288bac4d279efdd524a8ee30f82fc04f76c9aab2de9cde4612` |
| 11.6 | `18375032ea1bacf41ed9c564859ba89d4d75fd9b048b759b8324fbad69d545fe` |
| 11.7 | `87285d3756c6c7b2d548812fefe7b0ce57402d96aa4c3904567e2e561a53c5c8` |
| 11.8 | `ef6483137a97789b7669859504c40dfaa1a47d2a9cc43129207f83f6d2d176b0` |

The 10.24 hash and the Riot zip hash match the copies recorded in [docs/set4-sources.md](../../docs/set4-sources.md).

## Festival name lists

`tft-ddragon/festival-of-beasts/` comes from [TFT_DDragon](https://github.com/noxelisdev/TFT_DDragon) commit `e83408e35b01b8e9c47a6d7d81791b1a04d01374`, path `latest/`. On that commit, `latest/` is Festival of Beasts and `previous/set4/` is Fates.

| File | Records | SHA-256 |
| --- | --- | --- |
| `champions.json` | 58 | `68ad92b6ae597582e6bee82ab458017dddfd13d6a0c70f3f3c40a84475b297a1` |
| `traits.json` | 27 | `8a9088435639875caeff516289828ad5ee131cea486171630cd0d3e51a9960e9` |
| `items.json` | 64 | `a61abe81daa9ff3d9595588599a453e613401449f7a9279a3674e77bb51f1d26` |

Fields match the Riot Fates files. There are no combat numbers. The 58 names match the playable Act 2 champions in Community Dragon. Four returning units use different ids: this list says `TFT4_Diana`, `TFT4_Kindred`, `TFT4_Morgana`, and `TFT4_Zed`, while Act 2 says `TFT4b_Diana`, `TFT4b_Kindred`, `TFT4b_Morgana`, and `TFT4b_Zed`.

Festival traits add Blacksmith, Daredevil, Dragonsoul, Executioner, Fabled, Slayer, and Syphoner, and drop Dazzler, Dusk, Hunter, Moonlight, Shade, and Tormented.

## Not collected

These were checked and left out:

- Live Data Dragon TFT files such as `tft-champion.json` for 10.24.1 through 11.3.1 return S3 `AccessDenied`. Ordinary League files on the same host still download.
- Blitz's [Set 4.5 comps page](https://blitz.gg/tft/set4_5/comps) is titled for Patch 18.4, but the stats request embedded in the page is `analyzed_comps` for patch 16.20, and those boards use current Set 18 unit ids such as `DA_18_Leona`. Asking that API for patch `18.4`, `set4_5`, `4.5`, `11.2`, or mode `REVIVAL` returns no comps. The separate `set4_5` unit catalog is the Festival roster and has no placements.
- MetaTFT's live comp feed is Set 18. Its revival slot is Set 15, and the Set 4.5 comps page is disabled.
- LoLChess's revival page did not include a placement payload. The other large Kaggle match dump, `teckmengwong/team-fight-tactics-matches`, is Set 7 from 2022.
- The wiki pages, the tftset.com catalog, and the Esports Tales article are written pages. Esports Tales lists boards and items without measured placements.
