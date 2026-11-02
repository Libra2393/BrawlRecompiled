"""Write a copy of wiicompiled/runtime for another region's disc: every guest address literal of the US build moved,
then the disc identity rewritten (the project's region.json, "identity").
Usage: remap_runtime_region.py <wiicompiled> <US DATA> <region DATA> <decomp RSBE01_02> <project dir> <out runtime dir>
Literals that cannot be mapped are left as they are and logged (UNMAPPED) in <project>/remap_runtime_log.tsv for
a hand fix. third_party/ is copied untouched; hle/brawl_module_layout.inc comes from the project folder."""
import json, re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from region_addr import RegionAddr

wc, usd, pald, dec, pal, out = map(Path, sys.argv[1:7])
M = RegionAddr(wc / "projects/brawl/tools", usd, pald, dec, wc / "projects/brawl/module_layout.json", pal)
LIT = re.compile(r"(?<![0-9A-Za-z_])0x(8[01][0-9A-Fa-f]{6}|9[4-7][0-9A-Fa-f]{6})(u?)(?![0-9A-Fa-f])")
# Function overrides take the address bare: PPC_NATIVE_OVERRIDE_VOID(801D8690, ...). (NSMBW_GX_POKE_NOOP's address
# only names the function it defines; the override after it carries the real one.)
MACRO = re.compile(r"\b(PPC_NATIVE_OVERRIDE\w*\(\s*)([0-9A-Fa-f]{8})\b")
# Calls into translated guest code by the translator's own symbol name: func_801D66A8(cpu).
FUNC = re.compile(r"\bfunc_([0-9A-Fa-f]{8})\b")
SDA = re.compile(r"(r13 - 0x|Sda1Offset = 0x|OffsetFromR13 = 0x)([0-9A-Fa-f]{4})")
# Values in the address range that are not guest addresses.
NOT_ADDR = {("src/hle/gx/gx_dl.cpp", 0x80808081)}
# After the addresses: the disc's identity (text, so the address pass never sees it), from region.json.
TEXT = [tuple(x) for x in json.loads((pal / "region.json").read_text())["identity"]]
if out.exists(): shutil.rmtree(out)
shutil.copytree(wc / "runtime", out)
shutil.copy(pal / "brawl_module_layout.inc", out / "src/hle/brawl_module_layout.inc")
log = []
for p in sorted(out.rglob("*")):
    rel = str(p.relative_to(out))
    if p.suffix not in (".cpp", ".h", ".hpp", ".inc", ".c", ".S") or rel.startswith("third_party") or rel.endswith("brawl_module_layout.inc"):
        continue
    text = p.read_text(errors="surrogateescape"); lines = text.split("\n"); changed = False
    for ln, line in enumerate(lines):
        def lit(m):
            a = int(m[1], 16)
            if (rel, a) in NOT_ADDR:
                log.append((rel, ln + 1, "%08X" % a, "", "skip not an address")); return m[0]
            if 0x80000000 <= a < 0x80004000 or a in (0x81800000, 0x94000000, 0x94004000, 0x98000000, 0x90000000):
                return m[0]
            pa, how = M.map(a)
            log.append((rel, ln + 1, "%08X" % a, "" if pa is None else "%08X" % pa, how))
            if pa is None or pa == a: return m[0]
            hexd = m[1]; up = hexd.upper() == hexd
            return "0x" + (("%08X" if up else "%08x") % pa) + m[2]
        def sda(m):
            off = int(m[2], 16); a = (M.u13 - off) & 0xFFFFFFFF
            pa, how = M.map(a)
            log.append((rel, ln + 1, "r13-%04X=%08X" % (off, a), "" if pa is None else "r13-%04X=%08X" % ((M.p13 - pa) & 0xFFFF, pa), "sda " + how))
            if pa is None: return m[0]
            return m[1] + ("%04X" % ((M.p13 - pa) & 0xFFFF))
        def macro(m):
            a = int(m[2], 16)
            pa, how = M.map(a)
            log.append((rel, ln + 1, "%08X" % a, "" if pa is None else "%08X" % pa, "override " + how))
            if pa is None: return m[0]
            return m[1] + (("%08X" if m[2].upper() == m[2] else "%08x") % pa)
        def func(m):
            a = int(m[1], 16)
            pa, how = M.map(a)
            log.append((rel, ln + 1, "func_%08X" % a, "" if pa is None else "func_%08X" % pa, "symbol " + how))
            if pa is None: return m[0]
            return "func_" + (("%08X" if m[1].upper() == m[1] else "%08x") % pa)
        nl = SDA.sub(sda, FUNC.sub(func, MACRO.sub(macro, LIT.sub(lit, line))))
        if nl != line: lines[ln] = nl; changed = True
    joined = "\n".join(lines)
    for x, y in TEXT:
        n = joined.count(x)
        if n:
            joined = joined.replace(x, y); changed = True
            log.append((rel, 0, x, y, "identity x%d" % n))
    if changed: p.write_text(joined, errors="surrogateescape")
with open(pal / "remap_runtime_log.tsv", "w") as f:
    f.write("file\tline\tus\tregion\thow\n")
    for r in log: f.write("%s\t%d\t%s\t%s\t%s\n" % r)
import collections
c = collections.Counter(r[4].split()[0] for r in log)
print("literals seen: %d" % len(log), dict(c))
