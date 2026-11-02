"""build_modules.py with a region's resident addresses. Usage: run_build_modules_region.py <wc tools dir> <resident json> <args...>"""
import json, sys
sys.path.insert(0, sys.argv[1])
import build_modules as bm
bm.RESIDENT = {k: tuple(int(x, 16) for x in v) for k, v in json.load(open(sys.argv[2])).items()}
bm.RESIDENT_VENEERS = bm.RESIDENT["sora_melee"][1]
sys.argv = [sys.argv[0]] + sys.argv[3:]
bm.main()
