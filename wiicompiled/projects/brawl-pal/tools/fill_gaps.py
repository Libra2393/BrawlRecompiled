"""Function starts in target code no source function was placed on. Candidates inside each gap: the gap's first
non-padding word, bl targets from anywhere in the block, and the word after a blr/b/bctr when it is a prologue
(stwu r1 or mflr r0). Returns [(offset, size)] (offsets in words*4)."""
BLR, BCTR = 0x4E800020, 0x4E800420

def prologue(x):
    return x >> 16 == 0x9421 or x == 0x7C0802A6  # stwu r1,-n(r1) / mflr r0

def sext26(v):
    return v - 0x4000000 if v & 0x2000000 else v

def gaps_and_starts(words, placed, pointers=()):
    """placed: [(offset_bytes, size_bytes)]. pointers: byte offsets something takes the address of (vtables,
    callbacks), which are function starts too."""
    n = len(words)
    cov = bytearray(n)
    for o, z in placed:
        for i in range(o // 4, min(n, (o + z) // 4)):
            cov[i] = 1
    bl = set()
    for i, x in enumerate(words):
        if x >> 26 == 18 and x & 3 == 1:
            t = i + sext26(x & 0x03FFFFFC) // 4
            if 0 <= t < n:
                bl.add(t)
    gaps, i = [], 0
    while i < n:
        if cov[i]:
            i += 1; continue
        j = i
        while j < n and not cov[j]:
            j += 1
        s = i
        while s < j and words[s] == 0:
            s += 1
        if s < j:
            st = {s} | {p // 4 for p in pointers if s * 4 <= p < j * 4 and not p & 3}
            for k in range(s, j):
                if k in bl:
                    st.add(k)
                if k + 1 < j and (words[k] in (BLR, BCTR) or words[k] >> 26 == 18 and not words[k] & 1) and prologue(words[k + 1]):
                    st.add(k + 1)
            st = sorted(st)
            ends = st[1:] + [j]
            for a, b in zip(st, ends):
                e = b
                while e > a and words[e - 1] == 0:
                    e -= 1
                gaps.append((a * 4, (e - a) * 4))
        i = j
    return gaps
