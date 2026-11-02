"""The 7 boot-loaded modules' addresses on a region's disc, from where sora_melee (the last of them) really loaded.
A boot log with a wrong resident_estimate.json says "REL module sora_melee loaded at 0x<image> (bss ...), not at ...".
The others sit before it by the US layout rule (bss = align32(image + fix size), next image = align32(previous end +
0xDC), which reproduces all 7 US addresses); each is the highest 32-aligned image that lands exactly on the next.
Usage: resident_from_log.py <US project tools dir> <region DATA> <sora_melee image, hex> <project>/resident_estimate.json"""
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from prelink_rels import Rel
from build_modules import RESIDENT, fix_size

D, melee, out = Path(sys.argv[2]), int(sys.argv[3], 16), Path(sys.argv[4])
a32 = lambda v: (v + 31) & ~31
names = list(RESIDENT)
mods = {n: Rel(D / "files/module" / (n + ".rel")) for n in names}
res = {"sora_melee": (melee, a32(melee + fix_size(mods["sora_melee"])))}
nxt = melee
for n in reversed(names[:-1]):
    m = mods[n]
    lands = lambda img: a32(a32(img + fix_size(m)) + m.bss_size + 0xDC)
    img = (nxt - 0xDC - m.bss_size - fix_size(m)) & ~31
    while lands(img) > nxt: img -= 32
    while lands(img + 32) == nxt: img += 32
    assert lands(img) == nxt, n
    res[n] = (img, a32(img + fix_size(m))); nxt = img
out.write_text(json.dumps({n: ["0x%08X" % res[n][0], "0x%08X" % res[n][1]] for n in names}, indent=1) + "\n")
for n in names: print("  %-26s 0x%08X / 0x%08X" % (n, *res[n]))
