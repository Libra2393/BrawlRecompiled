#!/usr/bin/env bash
# Linux build of Brawl Recompiled for the PAL disc (RSBP01), translated and compiled on Linux.
#   bash wiicompiled/projects/brawl-pal/tools/build-pal-linux.sh <US DATA> <PAL DATA> <decomp config/RSBE01_02>
# <US DATA>/<PAL DATA>: the discs' game partitions extracted with Dolphin (sys/ and files/); the US one is the rev 2
# disc the decomp's symbols match. Needs python3, dotnet (8 SDK), cmake, ninja, clang and lld on PATH (or DOTNET, CMAKE).
# Work tree: ~/brawl-linux/pal (wc/ = wiicompiled with the PAL runtime, game/ = the translation inputs).
# Output: ~/brawl-linux/pal/build/WiiCompiled
set -euo pipefail

us=$1 pal=$2 decomp=$3
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
project=$(dirname "$here")            # wiicompiled/projects/brawl-pal
src=$(cd "$project/../.." && pwd)     # wiicompiled
work=$HOME/brawl-linux/pal
jobs=${JOBS:-$(( $(nproc) * 3 / 4 ))}
dotnet=${DOTNET:-dotnet}
cmake=${CMAKE:-cmake}
mkdir -p "$work/game" "$work/logs"

echo "copying sources to $work/wc"
rsync -a --delete --exclude runtime --exclude generated --exclude native-build "$src/" "$work/wc/"
# The US runtime with every guest address moved to PAL (only files whose content changed are touched).
python3 -I "$here/remap_runtime_pal.py" "$src" "$us" "$pal" "$decomp" "$project" "$work/runtime-pal"
rsync -rc "$work/runtime-pal/" "$work/wc/runtime/"

# Modules at their homes, and main_translate.dol, with the PAL resident addresses.
cp "$project/MAP.txt" "$work/wc/projects/brawl/MAP.txt"
(cd "$work" && python3 -I "$here/run_build_modules_pal.py" "$work/wc/projects/brawl/tools" "$project/resident_estimate.json" \
    "$pal/files/module" "$project/config/RSBP01_01" "$work/game/brawl_modules.rel" "$work/wc" "$pal/sys/main.dol")
for f in MAP_modules.txt MAP_full.txt module_layout.json resident_data_ranges.txt; do
    cp "$work/wc/projects/brawl/$f" "$project/$f"; cp "$work/wc/projects/brawl/$f" "$work/wc/projects/brawl-pal/$f"
done
cp "$work/wc/runtime/src/hle/brawl_module_layout.inc" "$project/brawl_module_layout.inc"
sha=$(sha256sum "$work/game/main_translate.dol" | cut -d' ' -f1)
sed -i -E "s/(    sha256: )[0-9a-f]{64}/\1$sha/" "$project/recomp.yml" "$work/wc/projects/brawl-pal/recomp.yml"

echo "translating"
export DOTNET_ROLL_FORWARD=Major DOTNET_CLI_TELEMETRY_OPTOUT=1
(cd "$work/wc/translator" && "$dotnet" build -c Release src/Translator.Cli > "$work/logs/translator-build.log")
tr=translator/src/Translator.Cli/bin/Release/net8.0/Translator.Cli.dll
yml=projects/brawl-pal/recomp.yml
cd "$work/wc"
"$dotnet" $tr translate-recursive 0x8000403C --project $yml --outdir generated/functions \
    --output-metadata generated/base_translation_output.json --production-source-bundle generated/base_translation_sources.bin \
    --no-function-files --no-state-free-abi --data-in-text projects/brawl-pal/resident_data_ranges.txt --prune-stale \
    --threads "$jobs" > "$work/logs/translate.log" 2>&1
"$dotnet" $tr generate-data-init --project $yml > "$work/logs/data-init.log" 2>&1
"$dotnet" $tr emit-build-shards --project $yml --base-metadata generated/base_translation_output.json \
    --base-functions-dir generated/functions --native-source-dir runtime/src --out generated/build_shards --base-shards 600 \
    > "$work/logs/shards.log" 2>&1

# Dawn from upstream (encounter/dawn-build, Aurora's author) rather than the fork aurora-main pins.
"$cmake" -S "$work/wc/runtime" -B "$work/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_ASM_COMPILER=clang \
    -DCMAKE_AR="$(command -v llvm-ar)" -DCMAKE_RANLIB="$(command -v llvm-ranlib)" -DCMAKE_LINKER="$(command -v ld.lld)" \
    -DMKW_TRANSLATED_COMPILE_JOBS="$jobs" \
    -DAURORA_DAWN_PACKAGE_URL=https://github.com/encounter/dawn-build/releases/download/v20260603.191052/dawn-linux-x86_64.tar.gz \
    -DAURORA_DAWN_PACKAGE_URL_HASH=SHA256=f9e11d418548e2914fd5b2f6f34562a5920a6b9d9d552ebf2bfcc747a5df9ae1 \
    > "$work/logs/configure.log" 2>&1
"$cmake" --build "$work/build" --target WiiCompiled --parallel "$jobs" > "$work/logs/build.log" 2>&1
echo "DONE: $work/build/WiiCompiled"
