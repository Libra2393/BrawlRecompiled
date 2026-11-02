#!/usr/bin/env bash
# A region's function and data maps, from the decomp's US symbols and the two discs.
#   bash wiicompiled/projects/brawl-regions/tools/make-region-maps.sh <project> <US DATA> <region DATA> <decomp config/RSBE01_02>
# <project>: wiicompiled/projects/brawl-pal or brawl-jp, holding region.json and observed_starts.txt. Writes
# config/<id>/ (decomp-format symbols), MAP.txt, main_report.tsv, modules_report.tsv, data_map.tsv, data_refs.tsv and
# changed_functions.tsv there. build-region-linux.sh does the rest.
set -euo pipefail

project=$(cd "$1" && pwd) us=$2 region=$3 decomp=$4
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
tools=$(cd "$project/../brawl/tools" && pwd)   # the US project's addr_map.py, prelink_rels.py, build_modules.py
cfg=$project/config/$(python3 -I -c 'import json, sys; print(json.load(open(sys.argv[1]))["config"])' "$project/region.json")

rm -rf "$cfg" && mkdir -p "$cfg"
python3 -I "$here/match_dol.py" "$tools" "$us/sys/main.dol" "$region/sys/main.dol" "$decomp/symbols.txt" "$cfg"
python3 -I "$here/match_modules.py" "$tools" "$us/files/module" "$region/files/module" "$decomp" "$cfg" | head -8
python3 -I "$here/add_region_only.py" "$tools" "$region" "$cfg"
mv "$cfg/main_report.tsv" "$cfg/modules_report.tsv" "$project/"
cp "$cfg/MAP.txt" "$project/MAP.txt"
python3 -I "$here/map_dol_data.py" "$tools" "$us/sys/main.dol" "$region/sys/main.dol" "$decomp/symbols.txt" \
    "$project/main_report.tsv" "$project"
python3 -I "$here/list_changed.py" "$tools" "$us" "$region" "$decomp" "$project/main_report.tsv" "$project/changed_functions.tsv"
rm -rf "$here/__pycache__"
