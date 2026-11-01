"""US rev 2 main.dol data addresses -> PAL, from the address references of functions identical in both.
Usage: map_dol_data.py <tools dir> <us dol> <pal dol> <RSBE01_02 symbols.txt> <main_report.tsv> <out dir>
Writes <out>/data_map.tsv (every decomp data symbol: us, pal, how) and <out>/data_refs.tsv (voted reference pairs)."""
import bisect, collections, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from addr_map import Dol, r13_r2, refs

U, P = Dol(sys.argv[2]), Dol(sys.argv[3]); out = Path(sys.argv[6])
u13, u2 = r13_r2(U); p13, p2 = r13_r2(P)
pairs = []
for l in list(open(sys.argv[5]))[1:]:
    a, z, n, pa, pz, how = l.rstrip("\n").split("\t")
    if how in ("unique", "sequence"):
        pairs.append((int(a, 16), int(z, 16), int(pa, 16)))
votes = collections.defaultdict(collections.Counter)
for a, z, pa in pairs:
    ru, rp = dict(refs(U, a, z, u13, u2)), dict(refs(P, pa, z, p13, p2))
    for i, t in ru.items():
        if i in rp and 0x80003100 <= t < 0x81800000 and not U.is_text(t):
            votes[t][rp[i]] += 1
known = {}
for t, c in votes.items():
    (best, k), = c.most_common(1)
    if k * 2 > sum(c.values()):
        known[t] = (best, k, sum(c.values()))
ks = sorted(known)
# Data sections and bss, for "same section" checks.
import struct
def sections(d):
    h = struct.unpack(">18I18I18IIII", d.b[:0xE4])
    s = [(h[18 + i], h[18 + i] + h[36 + i]) for i in range(7, 18) if h[36 + i]]
    return s + [(h[54], h[54] + h[55])]
usecs = sections(U)
def sec_of(a):
    for i, (s, e) in enumerate(usecs):
        if s <= a < e: return i
syms = []
for l in open(sys.argv[4]):
    m = re.match(r"(\S+) = \.(\w+):0x([0-9A-Fa-f]+); // type:object(?: size:0x([0-9A-Fa-f]+))?", l)
    if m: syms.append((int(m[3], 16), int(m[4] or "0", 16), m[1], m[2]))
c = collections.Counter()
with open(out / "data_map.tsv", "w") as f:
    f.write("us_addr\tsize\tname\tsection\tpal_addr\thow\n")
    for a, z, n, sec in syms:
        if a in known:
            pa, how = known[a][0], "referenced"
        else:
            k = bisect.bisect_right(ks, a) - 1
            lo = ks[k] if k >= 0 and sec_of(ks[k]) == sec_of(a) else None
            hi = ks[k + 1] if k + 1 < len(ks) and sec_of(ks[k + 1]) == sec_of(a) else None
            dl = known[lo][0] - lo if lo is not None else None
            dh = known[hi][0] - hi if hi is not None else None
            if dl is not None and dl == dh:
                pa, how = a + dl, "bracketed"
            elif dl is not None or dh is not None:
                pa, how = a + (dl if dl is not None else dh), "nearest"
            else:
                pa, how = None, "unknown"
        c[how] += 1
        f.write("%08X\t%X\t%s\t.%s\t%s\t%s\n" % (a, z, n, sec, "%08X" % pa if pa is not None else "", how))
with open(out / "data_refs.tsv", "w") as f:
    f.write("us_addr\tpal_addr\tvotes\ttotal\n")
    for t in ks: f.write("%08X\t%08X\t%d\t%d\n" % (t, *known[t]))
contested = sum(1 for t, cc in votes.items() if t not in known)
print("matched functions used: %d   referenced data addresses: %d (+%d without a majority)" % (len(pairs), len(known), contested))
disagree = sum(1 for t in known if known[t][1] != known[t][2])
print("addresses where some votes disagreed: %d" % disagree)
print("decomp data symbols: %d" % len(syms), dict(c))
