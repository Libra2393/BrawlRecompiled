"""US (RSBE01 rev 1/2) guest address -> another region's disc, from the maps in its project folder (brawl-pal/,
brawl-jp/) and its config/<id>/. map(a) -> (address or None, how). how starts with "same", "code", "data", "module-code", "module-data",
"module-bss", "arena" or "fst" when mapped; with "UNMAPPED" when not."""
import bisect, json, re, struct, sys
from pathlib import Path

LOWMEM_END = 0x80004000  # exception vectors and OS globals: the same on every disc


class RegionAddr:
    def __init__(self, tools, us_data, pal_data, decomp, us_layout, pal_dir):
        sys.path.insert(0, str(tools))
        from addr_map import Dol, r13_r2
        from prelink_rels import Rel
        from build_modules import fix_size
        pal_dir = Path(pal_dir); cfg = pal_dir / "config" / json.loads((pal_dir / "region.json").read_text())["config"]
        self.U, self.P = Dol(Path(us_data) / "sys/main.dol"), Dol(Path(pal_data) / "sys/main.dol")
        self.u13, self.u2 = r13_r2(self.U); self.p13, self.p2 = r13_r2(self.P)
        h = lambda d: struct.unpack(">18I18I18IIII", d.b[:0xE4])
        hu, hp = h(self.U), h(self.P)
        self.u_bss_end, self.p_bss_end = hu[54] + hu[55], hp[54] + hp[55]
        fst = (Path(pal_data) / "sys/fst.bin").stat().st_size
        self.pal_arena_hi = (0x81800000 - fst) & ~31
        # main.dol code
        self.f = []
        for l in list(open(pal_dir / "main_report.tsv"))[1:]:
            a, z, n, pa, pz, how = l.rstrip("\n").split("\t")
            self.f.append((int(a, 16), int(z, 16), int(pa, 16) if pa else None, how, int(pz, 16) if pz else None))
        self.f.sort(); self.fs = [x[0] for x in self.f]
        # main.dol data
        self.refs = {int(a, 16): int(b, 16) for a, b, *_ in (l.split("\t") for l in list(open(pal_dir / "data_refs.tsv"))[1:])}
        self.d = []
        for l in list(open(pal_dir / "data_map.tsv"))[1:]:
            a, z, n, sec, pa, how = l.rstrip("\n").split("\t")
            if pa: self.d.append((int(a, 16), max(int(z, 16), 1), int(pa, 16), how, n))
        self.d.sort(); self.ds = [x[0] for x in self.d]
        # modules
        lu, lp = json.load(open(us_layout)), json.load(open(pal_dir / "module_layout.json"))
        self.mods = []
        pat = re.compile(r"(\S+) = (\.\w+):0x([0-9A-Fa-f]+); // type:function size:0x([0-9A-Fa-f]+)")
        for name, u in lu.items():
            p = lp[name]
            ru, rp = Rel(Path(us_data) / "files/module" / (name + ".rel")), Rel(Path(pal_data) / "files/module" / (name + ".rel"))
            names = [x.split()[0] for x in (Path(decomp) / "rels" / name / "splits.txt").read_text().split("Sections:")[1].split("\n\n")[0].splitlines() if x.strip()]
            ufun = {}; pfun = {}
            for x in (Path(decomp) / "rels" / name / "symbols.txt").read_text().splitlines():
                m = pat.match(x)
                if m: ufun.setdefault(m[2], []).append((int(m[3], 16), int(m[4], 16), m[1]))
            for x in (cfg / "rels" / name / "symbols.txt").read_text().splitlines():
                m = pat.match(x)
                if m: pfun[(m[2], m[1])] = (int(m[3], 16), int(m[4], 16), x.rsplit("match:", 1)[-1])
            for v in ufun.values(): v.sort()
            self.mods.append(dict(name=name, ru=ru, rp=rp, names=names, ufun=ufun, pfun=pfun,
                                  uimg=int(u["image"], 16), ubss=int(u["bss"], 16), ufix=fix_size(ru),
                                  pimg=int(p["image"], 16), pbss=int(p["bss"], 16), pfix=fix_size(rp)))

    def _module(self, a):
        for m in self.mods:
            ru, rp = m["ru"], m["rp"]
            if m["ubss"] <= a < m["ubss"] + ru.bss_size:
                off = a - m["ubss"]
                return (m["pbss"] + off, "module-bss " + m["name"]) if off < rp.bss_size else (None, "UNMAPPED module-bss past end " + m["name"])
            if m["uimg"] <= a < m["uimg"] + m["ufix"]:
                fo = a - m["uimg"]
                for i, (o, ex, z) in enumerate(ru.secs):
                    if o and o <= fo < o + z:
                        sec = m["names"][i - 1] if i - 1 < len(m["names"]) else "?"
                        so = fo - o
                        po, pex, pz = rp.secs[i]
                        if ex:
                            fl = m["ufun"].get(sec, [])
                            k = bisect.bisect_right([x[0] for x in fl], so) - 1
                            if k < 0 or so >= fl[k][0] + fl[k][1]:
                                return None, "UNMAPPED module-code outside functions " + m["name"]
                            fo0, fz, fn = fl[k]
                            hit = m["pfun"].get((sec, fn))
                            if not hit:
                                return None, "UNMAPPED module-code changed %s %s" % (m["name"], fn)
                            pfo, pfz, how = hit
                            if how not in ("unique", "sequence") and so != fo0:
                                return None, "UNMAPPED module-code inside changed %s %s" % (m["name"], fn)
                            return m["pimg"] + po + pfo + (so - fo0), "module-code %s %s" % (m["name"], fn)
                        if z == pz:
                            return m["pimg"] + po + so, "module-data same-size %s %s" % (m["name"], sec)
                        return None, "UNMAPPED module-data %s %s resized %#x->%#x" % (m["name"], sec, z, pz)
                return None, "UNMAPPED module header " + m["name"]
        return None

    @staticmethod
    def _bl_target(d, at):
        x = d.words(at, 4)[0]
        if x >> 26 != 18 or x & 3 != 1:
            return None
        v = x & 0x03FFFFFC
        return (at + (v - 0x4000000 if v & 0x2000000 else v)) & 0xFFFFFFFF

    def _return_address(self, a, s, z, pa, pz):
        """a return address (just after a bl) inside a function the region changed: the same call (by target and ordinal)."""
        t = self._bl_target(self.U, a - 4)
        if t is None or pz is None:
            return None, "UNMAPPED code inside changed function %08X" % s
        pt, how = self.map(t)
        if pt is None:
            return None, "UNMAPPED code inside changed function %08X (callee unmapped)" % s
        us = [i for i in range(s, s + z, 4) if self._bl_target(self.U, i) == t]
        ps = [i for i in range(pa, pa + pz, 4) if self._bl_target(self.P, i) == pt]
        if len(us) != len(ps):
            return None, "UNMAPPED code inside changed function %08X (%d vs %d calls)" % (s, len(us), len(ps))
        return ps[us.index(a - 4)] + 4, "code return address in changed function %08X (call %d of %d)" % (s, us.index(a - 4) + 1, len(us))

    def map(self, a):
        if a < LOWMEM_END:
            return a, "same lowmem"
        if self.U.is_text(a):
            k = bisect.bisect_right(self.fs, a) - 1
            if k < 0 or a >= self.f[k][0] + self.f[k][1]:
                return None, "UNMAPPED code outside functions"
            s, z, pa, how, pz = self.f[k]
            if pa is None:
                return None, "UNMAPPED code in changed function %08X" % s
            if how not in ("unique", "sequence") and a != s:
                return self._return_address(a, s, z, pa, pz)
            return pa + (a - s), "code " + how
        if a < self.u_bss_end:
            if a in self.refs:
                return self.refs[a], "data referenced"
            k = bisect.bisect_right(self.ds, a) - 1
            if k >= 0 and a < self.d[k][0] + self.d[k][1]:
                s, z, pa, how, n = self.d[k]
                return pa + (a - s), "data %s %s" % (how, n)
            if k >= 0:
                s, z, pa, how, n = self.d[k]
                return pa + (a - s), "data after %s (check)" % n
            return None, "UNMAPPED data"
        r = self._module(a)
        if r:
            return r
        if 0x94000000 <= a < 0x98000000:
            return None, "UNMAPPED module-home area"
        if self.u_bss_end <= a < 0x80673FA0:
            return a + (self.p_bss_end - self.u_bss_end), "arena +%#x after main.dol bss (check)" % (self.p_bss_end - self.u_bss_end)
        if a == 0x81700000:
            return a, "same initial stack seed (high MEM1, not game data)"
        if a == 0x817DA5A0:
            return self.pal_arena_hi, "fst arena hi (MEM1 end - the disc's FST)"
        return None, "UNMAPPED heap"
