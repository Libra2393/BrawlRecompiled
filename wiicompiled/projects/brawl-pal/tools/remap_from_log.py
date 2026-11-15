"""Write the PAL copy of wiicompiled/runtime without a US disc: replay remap_runtime_log.tsv instead of matching code.
By Eldeallado (josiahg2502-glitch/BrawlRecompiled issue #10).

remap_runtime_pal.py needs both discs to work out where each US address moved; the log it commits already records
every answer by (file, line, US address). This reads the same patterns and identity text from remap_runtime_pal.py
and takes each address from the log, so a PAL user can build with only the PAL disc. It holds only while the runtime
matches the one the log was made from: an edit that moves a line holding a logged address shows up as "not in log"
(MISSING below), and then the log has to be made again with remap_runtime_pal.py and a US disc.

Usage: remap_from_log.py <wiicompiled> <brawl-pal dir> <out runtime dir> [--force]
Same regexes and identity text as remap_runtime_pal.py; every address comes from remap_runtime_log.tsv (file, line, us)."""
import re, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from remap_patterns_pal import LIT, MACRO, FUNC, SDA, NOT_ADDR, TEXT

if len(sys.argv) < 4:
    sys.exit(__doc__.split("\n\n")[-1].split("\n")[0])
wc, pal, out = map(Path, sys.argv[1:4])
force = "--force" in sys.argv[4:]

# The output tree is deleted and rebuilt below. Never let it overlap the runtime it copies or the brawl-pal dir, and only
# replace a non-empty dir that looks like an earlier output (every output gets src/hle/brawl_module_layout.inc).
_o = out.resolve()
for _keep in ((wc / "runtime").resolve(), pal.resolve()):
    if _o == _keep or _keep.is_relative_to(_o) or _o.is_relative_to(_keep):
        sys.exit(f"refusing to use {out} as the output: it overlaps {_keep}")
if out.exists():
    if not out.is_dir():
        sys.exit(f"output path exists and is not a directory: {out}")
    if any(out.iterdir()) and not (out / "src/hle/brawl_module_layout.inc").is_file() and not force:
        sys.exit(f"refusing to delete {out}: not empty and not an earlier output "
                 "(no src/hle/brawl_module_layout.inc); pass --force to replace it")

table = {}
for l in list(open(pal / "remap_runtime_log.tsv"))[1:]:
    f, ln, us, pa, how = l.rstrip("\n").split("\t")
    if ln != "0":
        table[(f, int(ln), us)] = pa

if out.exists(): shutil.rmtree(out)
shutil.copytree(wc / "runtime", out)
shutil.copy(pal / "brawl_module_layout.inc", out / "src/hle/brawl_module_layout.inc")
used = missing = 0
miss = []
for p in sorted(out.rglob("*")):
    rel = str(p.relative_to(out))
    if p.suffix not in (".cpp", ".h", ".hpp", ".inc", ".c", ".S") or rel.startswith("third_party") or rel.endswith("brawl_module_layout.inc"):
        continue
    text = p.read_text(errors="surrogateescape"); lines = text.split("\n"); changed = False
    for ln, line in enumerate(lines):
        def look(key):
            global used, missing
            k = (rel, ln + 1, key)
            if k not in table:
                missing += 1; miss.append(k); return None
            used += 1
            return table[k] or None
        def lit(m):
            a = int(m[1], 16)
            if (rel, a) in NOT_ADDR: return m[0]
            if 0x80000000 <= a < 0x80004000 or a in (0x81800000, 0x94000000, 0x94004000, 0x98000000, 0x90000000):
                return m[0]
            pa = look("%08X" % a)
            if pa is None or int(pa, 16) == a: return m[0]
            return "0x" + (("%08X" if m[1].upper() == m[1] else "%08x") % int(pa, 16)) + m[2]
        def sda(m):
            off = int(m[2], 16)
            hit = [v for (f, l, u), v in table.items() if f == rel and l == ln + 1 and u.startswith("r13-%04X=" % off)]
            if not hit:
                global missing; missing += 1; miss.append((rel, ln + 1, "r13-%04X" % off)); return m[0]
            if not hit[0]: return m[0]
            return m[1] + hit[0][4:8]
        def macro(m):
            pa = look("%08X" % int(m[2], 16))
            if pa is None: return m[0]
            return m[1] + (("%08X" if m[2].upper() == m[2] else "%08x") % int(pa, 16))
        def func(m):
            pa = look("func_%08X" % int(m[1], 16))
            if pa is None: return m[0]
            return "func_" + (("%08X" if m[1].upper() == m[1] else "%08x") % int(pa[5:], 16))
        nl = SDA.sub(sda, FUNC.sub(func, MACRO.sub(macro, LIT.sub(lit, line))))
        if nl != line: lines[ln] = nl; changed = True
    joined = "\n".join(lines)
    for x, y in TEXT:
        if x in joined: joined = joined.replace(x, y); changed = True
    if changed: p.write_text(joined, errors="surrogateescape")
print("addresses from log: %d, not in log: %d" % (used, missing))
for k in miss[:20]: print("  MISSING", *k)
