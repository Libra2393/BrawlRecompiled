"""Every US function whose PAL code differs. Usage: list_changed.py <tools dir> <US DATA> <PAL DATA> <decomp RSBE01_02>
<main_report.tsv> <out.tsv>"""
import re, struct, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, str(Path(__file__).parent))
from prelink_rels import Rel
from seqmatch import place
U, Pd, cfg = map(Path, sys.argv[2:5])
rows = []
for l in list(open(sys.argv[5]))[1:]:
    a, z, n, pa, pz, how = l.rstrip("\n").split("\t")
    if how.split("(")[0] in ("changed", "region"):
        rows.append(("main.dol", n, a, z, pa, pz, how))
for p in sorted((U / "files/module").glob("*.rel")):
    u, q = Rel(p), Rel(Pd / "files/module" / p.name)
    names = [l.split()[0] for l in (cfg / "rels" / u.name / "splits.txt").read_text().split("Sections:")[1].split("\n\n")[0].splitlines() if l.strip()]
    by = {}
    for l in (cfg / "rels" / u.name / "symbols.txt").read_text().splitlines():
        r = re.match(r"(\S+) = (\.\w+):0x([0-9A-Fa-f]+); // type:function size:0x([0-9A-Fa-f]+)", l)
        if r: by.setdefault(r[2], []).append((int(r[3], 16), int(r[4], 16), r[1]))
    for sec, fl in by.items():
        i = names.index(sec) + 1
        uo, _, us = u.secs[i]; po, _, ps = q.secs[i]
        for name, off, size, poff, psize, how in place(sorted(fl), list(struct.unpack(">%dI" % (us // 4), u.raw[uo:uo + us])), list(struct.unpack(">%dI" % (ps // 4), q.raw[po:po + ps]))):
            if how.split("(")[0] in ("changed", "region"):
                rows.append((u.name, name, "%s+%X" % (sec, off), "%X" % size, "" if poff is None else "%s+%X" % (sec, poff), "" if psize is None else "%X" % psize, how))
with open(sys.argv[6], "w") as f:
    f.write("where\tname\tus\tus_size\tpal\tpal_size\thow\n")
    for r in rows: f.write("\t".join(r) + "\n")
print(len(rows), "changed functions")
