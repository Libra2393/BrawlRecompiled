# Brawl Recompiled: Japan (RSBJ01 rev 0)

Dairantou Smash Brothers X, translated and built from the USA runtime with the tools in `../brawl-regions`. Nothing in
here is game code or data: only addresses, sizes and names.

**State:** the Linux build boots the Japanese disc through the strap, boot and save screens to the title screen at
60 fps, with every module at its translated home and every function translated (no interpreter fallbacks). It has not
gone past the title: the dump it was made with is the first 4 GiB of a split dump, so 153 of its movie files are
empty, and the title screen waits on the opening movie (`movie/OPMovie.thp`). A whole dump is needed for anything
after it. Menus, matches, saves and Windows are untried.

## How close it is to the USA game

| | Functions | Identical | Changed, placed | Changed, not placed | Japan-only starts |
|---|---|---|---|---|---|
| main.dol | 14,278 | 14,249 (99.8%) | 18 | 11 | 13 |
| 126 modules | 78,244 | 78,214 (99.96%) | 16 | 14 | 10 |

- 120 of the 126 modules have the USA code size. No fighter module differs. The changes are in the main and title
  menus, the scene manager, sora_melee (4 functions), the Home-Run Contest stage, and in main.dol the controller and
  Bluetooth code, the disc reset, Nintendo Wi-Fi login and a few game functions (`changed_functions.tsv`, 59). The 4
  small Subspace menu modules counted as not placed are byte for byte the USA ones; they are too small to anchor.
- Data: 13,890 referenced addresses, every vote unanimous; all 18,442 decomp data symbols placed (66 by their nearest
  neighbour only).
- Runtime: every guest address mapped (`remap_runtime_log.tsv`, nothing UNMAPPED), the arena as the game reports it
  (MEM1 0x805B4CC0-0x817DA5E0), the disc identity RSBJ01 revision 0, and Japanese as the default language (the disc has
  only Japanese text).
- The 7 boot-loaded modules (`resident_estimate.json`) follow from sora_melee's address in a boot log
  (`../brawl-regions/tools/resident_from_log.py`); the next boot loaded all of them there.

## Building

See `../brawl-regions/README.md`; this folder is the `<project>`.
