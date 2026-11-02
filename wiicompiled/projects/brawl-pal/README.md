# Brawl Recompiled: PAL (RSBP01 rev 1)

The European disc, translated and built from the same runtime as the USA one. Nothing in here is game code or data:
only addresses, sizes and names, and the tools that make them from your own two discs.

**State:** the Linux build boots the PAL disc to the title screen, runs the attract demo battle (8 fighters, Smashville)
and How to Play, at 60 fps, every function translated (no interpreter fallbacks in a 4-minute run). Menus, a real
match, Subspace, saves and mods have not been tried. Windows has not been built.

## How it is made

1. **Function map** (`config/RSBP01_01/`, `MAP*.txt`): the decomp's US symbols (doldecomp/brawl `config/RSBE01_02`, which
   match a US rev 2 `main.dol` byte for byte) placed on the PAL code by masked-instruction matching
   (`addr_map.py`'s `skeleton()`), then a walk through neighbours in order; what is left is PAL's own code, split at
   function starts the code itself proves (lis/addi references after a function end: 99.7-100% exact on the US files)
   and at starts seen at run time (`observed_starts.txt`).

   | | Functions | Identical in PAL | Changed, placed | Changed, not placed | PAL-only starts |
   |---|---|---|---|---|---|
   | main.dol | 14,278 | 14,026 (98.2%) | 98 | 154 | 160 |
   | 126 modules | 78,244 | 77,670 (99.3%) | 185 | 389 | 366 |

2. **Data map** (`data_map.tsv`, `data_refs.tsv`): every data address that identical functions reference, read from
   the same instruction in both: 13,348 addresses, all votes unanimous; every one of the decomp's 18,442 data symbols
   placed from them (436 only by their nearest neighbour).
3. **Module layout** (`module_layout.json`, `brawl_module_layout.inc`, `resident_data_ranges.txt`): the project's own
   `build_modules.py` on the PAL modules. The 7 modules the game loads at boot sit at fixed addresses
   (`resident_estimate.json`): sora_melee's was read from a PAL boot log, the other 6 follow from it by the US layout
   rule (bss = align32(image + fix size), next image = align32(previous end + 0xDC), which reproduces all 7 US
   addresses), and the next boot loaded all 7 exactly there.
4. **Runtime** (`../brawl-regions/tools/remap_runtime_region.py`, with this folder's `region.json`): a copy of `wiicompiled/runtime` with every guest address rewritten:
   390 function overrides, 268 code and 134 data literals, 28 in resident modules, 20 r13 offsets, 22 calls to
   translated functions by name, the arena bounds (MEM1 0x805B6F60-0x817D63C0, as PAL's OSInit reports) and the disc
   identity (RSBP01; the partition's boot.bin says revision 0, the disc header 1). Two literals stay unmapped, both
   harmless (a debug-only lr check in a draw dump, and a comment). Every change is in `remap_runtime_log.tsv`.
5. **Build** (`../brawl-regions/tools/build-region-linux.sh`): runs the layout and runtime steps into `~/brawl-linux/brawl-pal`, translates (40 s), and compiles
   with clang/lld (about 2 minutes on 14 jobs).

## Building on Linux

Extract both discs with Dolphin (game partition: `sys/` and `files/`): a USA rev 2 disc for the symbols to match, and
the PAL disc. Then, with python3, a .NET 8 SDK, CMake, Ninja, clang and lld (tested: CMake 4.3.3, clang 23):

```
bash wiicompiled/projects/brawl-regions/tools/make-region-maps.sh wiicompiled/projects/brawl-pal <USA rev 2 DATA> <PAL DATA> <doldecomp/brawl config/RSBE01_02>
bash wiicompiled/projects/brawl-regions/tools/build-region-linux.sh wiicompiled/projects/brawl-pal <USA rev 2 DATA> <PAL DATA> <doldecomp/brawl config/RSBE01_02>
```

To run it, put next to `~/brawl-linux/brawl-pal/build/WiiCompiled`: `portable.txt` (from `Play/`), `dsp_coef.bin` and
`cacert.pem` (from the build folder), `wiicompiled/runtime/assets/wii` as `wii_bootstrap/`, and
`UserData/Config.toml` with `[paths] dvd_root = "<PAL DATA>"` and `[game] language = "en"` (or de, fr, es, it).

Dawn comes from upstream (encounter/dawn-build, the Aurora author's builds) instead of the fork `aurora-main` pins.

## Not done

- **Launcher** (`launcher/`): still accepts only RSBE01 rev 1. A PAL build needs `WiiDisc.cs`'s `Game`/`GameRevision`
  (RSBP01, header revision 1) and its messages changed.
- **Windows build**, packaging, and the updater.
- **Gecko codes and mods**: they target the USA game. `tools/cheats-RSBE01.ini` is USA-only too.
- **Online play** with USA players: PAL changes ft_captain (4 functions) and ft_yoshi (2), so lockstep would desync.
- **Changed functions** (`changed_functions.tsv`, 826) are located, not reviewed. Hooks on them were checked: none of
  the runtime's overrides land inside one.
- `observed_starts.txt` will grow as more of the game is played: each "interpreter: running untranslated guest code
  at <address>" line in a log is one more start to add.
