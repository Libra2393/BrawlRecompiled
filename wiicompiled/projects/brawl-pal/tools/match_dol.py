"""US rev 2 main.dol functions -> PAL main.dol. Usage: match_dol.py <tools dir> <us dol> <pal dol> <symbols.txt> <out dir>
Writes <out>/symbols.txt (functions, decomp format, PAL addresses), <out>/MAP.txt, <out>/main_report.tsv."""
import collections, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, str(Path(__file__).parent))
from addr_map import Dol, r13_r2
from seqmatch import place

U, P = Dol(sys.argv[2]), Dol(sys.argv[3]); out = Path(sys.argv[5])
funcs = collections.defaultdict(list)
for l in open(sys.argv[4]):
    m = re.match(r"(\S+) = \.(init|text):0x([0-9A-Fa-f]+); // type:function size:0x([0-9A-Fa-f]+)", l)
    if m:
        funcs[m[2]].append((int(m[3], 16), int(m[4], 16), m[1]))
usec = dict(zip(("init", "text"), U.text)); psec = dict(zip(("init", "text"), P.text))
rows, c, cb = [], collections.Counter(), collections.Counter()
for sec, fl in funcs.items():
    (us, ue), (ps, pe) = usec[sec], psec[sec]
    fl = sorted((a - us, z, n) for a, z, n in fl)
    for name, off, size, poff, psize, how in place(fl, U.words(us, ue - us), P.words(ps, pe - ps)):
        k = how.split("(")[0]; c[k] += 1; cb[k] += size
        rows.append((sec, us + off, size, name, None if poff is None else ps + poff, psize, how))
rows.sort(key=lambda r: r[1])
placed = sorted((r for r in rows if r[4] is not None), key=lambda r: r[4])
bad = sum(a[4] + a[5] > b[4] for a, b in zip(placed, placed[1:]))
(out / "symbols.txt").write_text("".join("%s = .%s:0x%08X; // type:function size:0x%X  // match:%s\n" % (r[3], r[0], r[4], r[5], r[6]) for r in placed))
(out / "MAP.txt").write_text("".join("%08X %s\n" % (r[4], r[3]) for r in placed))
with open(out / "main_report.tsv", "w") as f:
    f.write("us_addr\tus_size\tname\tpal_addr\tpal_size\thow\n")
    for r in rows:
        f.write("%08X\t%X\t%s\t%s\t%s\t%s\n" % (r[1], r[2], r[3], "%08X" % r[4] if r[4] else "", "%X" % r[5] if r[5] else "", r[6]))
n = sum(c.values())
print("functions:", n, " overlaps:", bad)
for k in ("unique", "sequence", "changed", "region"):
    print("  %-9s %6d  %5.1f%%  %#9x bytes" % (k, c[k], 100 * c[k] / n, cb[k]))
for name, d in (("US", U), ("PAL", P)):
    a, b = r13_r2(d); print("%s r13 (sda_base) %08X  r2 (sda2_base) %08X" % (name, a, b))
