"""US rev 2 modules -> PAL modules. Usage: match_modules.py <tools dir> <us module dir> <pal module dir>
<decomp RSBE01_02 dir> <out dir>. Writes <out>/rels/<m>/symbols.txt + splits.txt (decomp format, PAL offsets,
functions only) and <out>/modules_report.tsv."""
import collections, re, struct, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, str(Path(__file__).parent))
from prelink_rels import Rel
from seqmatch import place

usd, pald, cfg, out = map(Path, sys.argv[2:6])
tot = collections.Counter(); totb = collections.Counter()
rep = []
for p in sorted(usd.glob("*.rel")):
    u, q = Rel(p), Rel(pald / p.name)
    splits = (cfg / "rels" / u.name / "splits.txt").read_text()
    names = [l.split()[0] for l in splits.split("Sections:")[1].split("\n\n")[0].splitlines() if l.strip()]
    secinfo = "same" if [(e, s) for o, e, s in u.secs] == [(e, s) for o, e, s in q.secs] else "sizes differ"
    if len(u.secs) != len(q.secs):
        secinfo = "section count differs"
    syms = collections.defaultdict(list)
    for l in (cfg / "rels" / u.name / "symbols.txt").read_text().splitlines():
        r = re.match(r"(\S+) = (\.\w+):0x([0-9A-Fa-f]+); // type:function size:0x([0-9A-Fa-f]+)", l)
        if r:
            syms[r[2]].append((int(r[3], 16), int(r[4], 16), r[1]))
    lines = []
    c = collections.Counter(); cb = collections.Counter()
    for sec, fl in syms.items():
        i = names.index(sec) + 1
        uo, _, us = u.secs[i]; po, _, ps = q.secs[i]
        uw = list(struct.unpack(">%dI" % (us // 4), u.raw[uo:uo + us]))
        pw = list(struct.unpack(">%dI" % (ps // 4), q.raw[po:po + ps]))
        for name, off, size, poff, psize, how in place(sorted(fl), uw, pw):
            k = how.split("(")[0]
            c[k] += 1; cb[k] += size
            if poff is not None:
                lines.append((sec, poff, psize, name, how))
    tot.update(c); totb.update(cb)
    n = sum(c.values())
    rep.append((u.name, n, c["unique"] + c["sequence"], c["changed"], c["region"], cb["changed"] + cb["region"], secinfo,
                sum(s for o, e, s in u.secs if e), sum(s for o, e, s in q.secs if e)))
    d = out / "rels" / u.name; d.mkdir(parents=True, exist_ok=True)
    d.joinpath("symbols.txt").write_text("".join("%s = %s:0x%08X; // type:function size:0x%X  // match:%s\n" % (nm, s, o, z, h)
                                         for s, o, z, nm, h in sorted(lines, key=lambda x: (x[0], x[1]))))
    d.joinpath("splits.txt").write_text("Sections:\n" + splits.split("Sections:")[1].split("\n\n")[0].strip("\n") + "\n\n")
with open(out / "modules_report.tsv", "w") as f:
    f.write("module\tfunctions\tidentical\tchanged_placed\tunplaced\tbytes_not_identical\tsections\tus_code\tpal_code\n")
    for r in rep:
        f.write("\t".join(str(x) if not isinstance(x, int) or x < 1000 else "%#x" % x for x in r) + "\n")
n = sum(tot.values())
print("modules: %d   functions: %d" % (len(rep), n))
for k in ("unique", "sequence", "changed", "region"):
    print("  %-9s %6d  %5.1f%%   %#9x bytes" % (k, tot[k], 100 * tot[k] / n, totb[k]))
print("identical code size: %d of %d modules" % (sum(r[7] == r[8] for r in rep), len(rep)))
print("modules with any non-identical function:", sum(r[3] + r[4] > 0 for r in rep))
for r in sorted(rep, key=lambda r: -r[5])[:15]:
    print("  %-28s fn %5d  same %5d  changed %3d  unplaced %3d  %#7x B  code %#x -> %#x  %s" % (r[0], r[1], r[2], r[3], r[4], r[5], r[7], r[8], r[6]))
