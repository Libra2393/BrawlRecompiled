"""Add PAL-only function starts (code no US function was placed on) to the PAL config.
Usage: add_pal_only.py <tools dir> <pal DATA dir> <pal config dir>"""
import sys, re, struct
from pathlib import Path
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, str(Path(__file__).parent))
from fill_gaps import gaps_and_starts
from addr_map import Dol
from prelink_rels import Rel
D, cfg = Path(sys.argv[2]), Path(sys.argv[3])
pat = re.compile(r"(\S+) = (\.\w+):0x([0-9A-F]+); // type:function size:0x([0-9A-F]+)")
P = Dol(D / "sys/main.dol")
from addr_map import r13_r2, refs


def ends(x):
    """blr, bctr, b or padding: what comes right before a function."""
    return x in (0x4E800020, 0x4E800420, 0) or (x >> 26 == 18 and not x & 1)


def dol_pointers(d):
    """Code addresses main.dol's code forms with lis/addi, right after the end of something: 99.7% of these are
    function starts in the US dol (data words are not: jump tables put switch cases there)."""
    out = set()
    r13, r2 = r13_r2(d)
    for s, e in d.text:
        for _, v in refs(d, s, e - s, r13, r2):
            if d.is_text(v) and ends(d.words(v - 4, 4)[0]): out.add(v)
    return out


def rel_pointers(mods):
    """{(module id, section): {offset}}: code addresses that lis/addi relocations (addr16 lo/ha) produce: all function
    starts in the US modules. addr32 ones are not (92%: jump tables)."""
    out = {}
    for m in mods.values():
        for k in range(m.imp_size // 8):
            imp, ro = struct.unpack(">II", m.raw[m.imp_off + 8 * k:m.imp_off + 8 * k + 8])
            c = ro
            while True:
                _d, typ, sec, add = struct.unpack(">HBBI", m.raw[c:c + 8]); c += 8
                if typ == 203: break
                if typ in (4, 6) and imp != 0:
                    out.setdefault((imp, sec), set()).add(add)
    return out


ptr_dol = dol_pointers(P)
observed = [l.split() for l in (cfg.parent.parent / "observed_starts.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
ptr_dol |= {int(x[1], 16) for x in observed if x[0] == "main"}
lines = (cfg / "symbols.txt").read_text().splitlines()
add, tot = [], 0
for sec, (s, e) in zip((".init", ".text"), P.text):
    pl = [(int(m[3], 16) - s, int(m[4], 16)) for m in map(pat.match, lines) if m[2] == sec]
    for o, z in gaps_and_starts(P.words(s, e - s), pl, [v - s for v in ptr_dol if s <= v < e]):
        add.append("fn_%08X = %s:0x%08X; // type:function size:0x%X  // match:pal-only" % (s + o, sec, s + o, z)); tot += z
print("main.dol: %d PAL-only function starts, %#x bytes of %#x" % (len(add), tot, sum(e - s for s, e in P.text)))


def split_changed(rows, starts):
    """An observed start inside a function placed as "changed" (PAL has more than one function there): cut it."""
    out = []
    for l in rows:
        m = pat.match(l)
        a, z = int(m[3], 16), int(m[4], 16)
        inside = sorted(x for x in starts if a < x[1] < a + z and x[0] == m[2]) if l.rstrip().endswith("match:changed") else []
        if not inside:
            out.append(l); continue
        bounds = [a] + [x[1] for x in inside] + [a + z]
        out.append(l.replace("size:0x%X" % z, "size:0x%X" % (bounds[1] - a)))
        for b0, b1 in zip(bounds[1:], bounds[2:]):
            out.append(fmt(b0, m[2], b1 - b0))
    return out


rows = sorted(lines + add, key=lambda l: int(pat.match(l)[3], 16))
fmt = lambda a, sec, z: "fn_%08X = %s:0x%08X; // type:function size:0x%X  // match:observed" % (a, sec, a, z)
rows = split_changed(rows, [(".text", int(x[1], 16)) for x in observed if x[0] == "main"])
(cfg / "symbols.txt").write_text("\n".join(rows) + "\n")
(cfg / "MAP.txt").write_text("".join("%s %s\n" % (pat.match(l)[3], pat.match(l)[1]) for l in rows))
mt = mn = allc = 0
mods = {d.name: Rel(D / "files/module" / (d.name + ".rel")) for d in (cfg / "rels").iterdir()}
ptr_rel = rel_pointers(mods)
for x in observed:
    if x[0] != "main":
        q = mods[x[0]]
        names = [l.split()[0] for l in (cfg / "rels" / x[0] / "splits.txt").read_text().split("Sections:")[1].strip().splitlines()]
        ptr_rel.setdefault((q.id, names.index(x[1]) + 1), set()).add(int(x[2], 16))
for d in sorted((cfg / "rels").iterdir()):
    q = mods[d.name]
    names = [l.split()[0] for l in (d / "splits.txt").read_text().split("Sections:")[1].strip().splitlines()]
    L = [l for l in (d / "symbols.txt").read_text().splitlines() if l]
    new = []
    for i, (o, ex, z) in enumerate(q.secs):
        if not ex or not z: continue
        allc += z
        sec = names[i - 1]
        w = list(struct.unpack(">%dI" % (z // 4), q.raw[o:o + z]))
        pl = [(int(m[3], 16), int(m[4], 16)) for m in map(pat.match, L) if m[2] == sec]
        for go, gz in gaps_and_starts(w, pl, ptr_rel.get((q.id, i), ())):
            new.append("fn_pal_%X = %s:0x%08X; // type:function size:0x%X  // match:pal-only" % (go, sec, go, gz)); mt += gz; mn += 1
    L = sorted(L + new, key=lambda l: (pat.match(l)[2], int(pat.match(l)[3], 16)))
    fmt = lambda a, sec, z: "fn_pal_%X = %s:0x%08X; // type:function size:0x%X  // match:observed" % (a, sec, a, z)
    L = split_changed(L, [(x[1], int(x[2], 16)) for x in observed if x[0] == d.name])
    (d / "symbols.txt").write_text("\n".join(L) + "\n")
print("modules: %d PAL-only function starts, %#x bytes of %#x" % (mn, mt, allc))
