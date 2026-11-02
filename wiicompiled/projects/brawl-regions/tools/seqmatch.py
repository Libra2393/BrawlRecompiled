"""Place a source's functions in a target code block: unique skeleton anchors (longest increasing run), then a walk
forward and back from each anchor through neighbours whose skeletons match in sequence. What is left between two
walks is a changed stretch: one function there is placed with the gap's size, several are left unplaced."""
import bisect, collections
from addr_map import skeleton

K = 6

def strip(w):
    w = list(w)
    while w and w[-1] == 0:
        w.pop()
    return w

def place(funcs, src_words, tgt_words):
    """funcs: [(offset, size, name)] sorted, offsets into src_words*4. Returns [(name, src_off, size, tgt_off|None,
    tgt_size|None, how)]."""
    tsk = skeleton(tgt_words)
    idx = collections.defaultdict(list)
    for i in range(len(tsk) - K + 1):
        idx[tsk[i:i + K]].append(i)
    sks = []
    for off, size, name in funcs:
        w = src_words[off // 4:(off + size) // 4]
        sks.append(skeleton(w))
    def hits(sk):
        body = skeleton(strip(sk)) if False else sk
        n = len(body)
        while n and body[n - 1] == 0:
            n -= 1
        body = body[:n]
        if len(body) < K:
            return None
        return [i for i in idx.get(body[:K], ()) if tsk[i:i + len(body)] == body]
    n = len(funcs)
    pick = [None] * n
    how = [None] * n
    pairs = []
    for j, sk in enumerate(sks):
        h = hits(sk) if funcs[j][1] >= 32 else None
        if h and len(h) == 1:
            pairs.append((j, h[0]))
    tails, tidx, prev = [], [], [None] * len(pairs)
    for q, (_, b) in enumerate(pairs):
        k = bisect.bisect_left(tails, b)
        if k == len(tails): tails.append(b); tidx.append(q)
        else: tails[k] = b; tidx[k] = q
        prev[q] = tidx[k - 1] if k else None
    q = tidx[-1] if tidx else None
    while q is not None:
        j, b = pairs[q]; pick[j] = b; how[j] = "unique"; q = prev[q]
    def fits(j, at):
        sk = sks[j]
        if at is None or at < 0 or tsk[at:at + len(sk)] != sk:
            return False
        a = j - 1
        while a >= 0 and pick[a] is None: a -= 1
        b = j + 1
        while b < n and pick[b] is None: b += 1
        if a >= 0 and pick[a] + funcs[a][1] // 4 > at: return False
        if b < n and at + funcs[j][1] // 4 > pick[b]: return False
        return True
    # Walk outward from every placed function.
    changed = True
    while changed:
        changed = False
        for j in range(n):
            if pick[j] is None:
                continue
            # forward
            k, at = j + 1, pick[j] + funcs[j][1] // 4 + (funcs[j + 1][0] - funcs[j][0] - funcs[j][1]) // 4 if j + 1 < n else None
            if k < n and pick[k] is None and fits(k, at):
                pick[k], how[k], changed = at, "sequence", True
            k = j - 1
            if k >= 0 and pick[k] is None:
                at = pick[j] - (funcs[j][0] - funcs[k][0]) // 4
                if fits(k, at):
                    pick[k], how[k], changed = at, "sequence", True
    # Gaps: between placed neighbours.
    out = []
    j = 0
    tsize = [None] * n
    while j < n:
        if pick[j] is not None:
            j += 1
            continue
        e = j
        while e < n and pick[e] is None:
            e += 1
        lo = pick[j - 1] + funcs[j - 1][1] // 4 if j else 0
        hi = pick[e] if e < n else len(tgt_words)
        if e - j == 1 and hi >= lo and 0 < j and e < n:
            pick[j], how[j], tsize[j] = lo, "changed", (hi - lo) * 4
        else:
            for k in range(j, e):
                how[k] = "region(%d)" % (e - j)
        j = e
    for j, (off, size, name) in enumerate(funcs):
        out.append((name, off, size, None if pick[j] is None else pick[j] * 4,
                    tsize[j] if tsize[j] is not None else (size if pick[j] is not None else None), how[j]))
    return out
