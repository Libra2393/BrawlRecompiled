# Brawl Recompiled: other regions' discs

Tools that make a build for a disc other than the USA one from the decomp's USA symbols, the USA runtime and your own
discs. Each region has a project folder of its own (`../brawl-pal`: RSBP01, `../brawl-jp`: RSBJ01) holding its
`region.json`, `observed_starts.txt`, `recomp.yml` and everything the tools write. No game code or data is in any of
them: only addresses, sizes and names.

## region.json

| Key | |
|---|---|
| `game_id`, `label` | The disc (RSBP01) and how messages name the region (PAL) |
| `config` | The folder under `config/` the decomp-format symbols go in (RSBP01_01) |
| `only_tag`, `only_prefix` | How functions only that region has are tagged and named (`pal-only`, `fn_pal_`) |
| `identity` | Text rewrites applied to the runtime after its addresses are moved: game code, NAND title folder, the revision the disc's boot.bin says, messages, the default language |

## Making a region's build

Extract both discs with Dolphin (game partition: `sys/` and `files/`): a USA revision 2 disc, whose `main.dol` the
decomp's `config/RSBE01_02` symbols match byte for byte, and the region's disc. Then:

```
bash wiicompiled/projects/brawl-regions/tools/make-region-maps.sh <project> <USA rev 2 DATA> <region DATA> <doldecomp/brawl config/RSBE01_02>
bash wiicompiled/projects/brawl-regions/tools/build-region-linux.sh <project> <USA rev 2 DATA> <region DATA> <doldecomp/brawl config/RSBE01_02>
```

The first writes the function and data maps; the second the module layout, the region's runtime, the translation
and the Linux build, in `~/brawl-linux/<project>`. Needs python3, a .NET 8 SDK, CMake, Ninja, clang and lld.

Two things only a boot can tell, each a line in the log:

- **The 7 modules the game loads at boot** sit at fixed addresses, which `resident_estimate.json` guesses from the
  USA layout. If the log says `REL module sora_melee loaded at 0x<image> ..., not at ...`, run
  `tools/resident_from_log.py <brawl/tools> <region DATA> <image> <project>/resident_estimate.json` and build again.
- **Function starts the static rules miss** (code reached only through vtables): each
  `interpreter: running untranslated guest code at <address>` line is one more for `observed_starts.txt`.

## Tools

| | |
|---|---|
| `match_dol.py`, `match_modules.py`, `seqmatch.py` | USA functions placed on the region's code by masked instructions, then in order |
| `add_region_only.py`, `fill_gaps.py` | Starts for code only the region has (proven references, observed starts) |
| `map_dol_data.py` | Data addresses, from the references of functions identical in both |
| `list_changed.py` | Every USA function whose code differs |
| `region_addr.py`, `remap_runtime_region.py` | The runtime with every guest address moved (logged in `remap_runtime_log.tsv`) |
| `run_build_modules_region.py`, `resident_from_log.py` | The USA `build_modules.py` with the region's boot-loaded module addresses |
| `make-region-maps.sh`, `build-region-linux.sh` | All of the above, in order |
