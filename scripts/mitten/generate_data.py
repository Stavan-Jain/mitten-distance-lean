"""Emit deterministic instance and floor data for the mitten formalization.

The group table, exhaustive triple census, and weight-ten witness are pinned
inputs. NumPy validates the generated algebra; Lean independently checks all
mathematical claims. No SAT search is used during reproduction.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
import numpy as np
import group_model

PACKAGE = Path(__file__).resolve().parent
GROUPS = PACKAGE / "inputs"
OUT = GROUPS
SETS = dict(a0=(0, 14, 23), a1=(0, 2, 11), b0=(7, 20, 24), b1=(0, 2, 29))

def build_dictionary(G):
    """GAP index → (i, j, k) with g = z^i r^j s^k, plus the mathlib
    carrier coordinates (i, dihedral) under the orientation
    r^j ↦ DihedralGroup.r j, r^j s ↦ DihedralGroup.sr (-j)."""
    n = G.n
    z = next(g for g in G.center() if G.orders[g] == 5)
    r = next(g for g in range(n) if int(G.orders[g]) == 3)
    ri = int(G.inv[r])
    s = next(g for g in range(n)
             if int(G.orders[g]) == 2 and G.mul(G.mul(g, r), g) == ri)
    table = {}
    zi = 0
    for i in range(5):
        for j in range(3):
            for k in range(2):
                el = zi
                for _ in range(j):
                    el = G.mul(el, r)
                if k:
                    el = G.mul(el, s)
                assert el not in table
                table[el] = (i, j, k)
        zi = G.mul(zi, z)
    assert len(table) == n

    # python model of mathlib DihedralGroup 3 multiplication
    # element = ('r'|'sr', idx mod 3);  ZMod-5 part is additive.
    def dmul(p, q):
        (t1, i1), (t2, i2) = p, q
        if t1 == "r" and t2 == "r":
            return ("r", (i1 + i2) % 3)
        if t1 == "r" and t2 == "sr":
            return ("sr", (i2 - i1) % 3)
        if t1 == "sr" and t2 == "r":
            return ("sr", (i1 + i2) % 3)
        return ("r", (i2 - i1) % 3)

    def carrier(ijk):
        i, j, k = ijk
        return (i, ("r", j) if k == 0 else ("sr", (-j) % 3))

    def cmul(p, q):
        return ((p[0] + q[0]) % 5, dmul(p[1], q[1]))

    for a in range(n):
        for b in range(n):
            assert cmul(carrier(table[a]), carrier(table[b])) == carrier(
                table[G.mul(a, b)]
            ), f"carrier-hom failure at {a},{b} — sr-orientation wrong?"
    return table, carrier, (z, r, s)


def lean_elem(c) -> str:
    i, (t, j) = c
    d = f"DihedralGroup.r {j}" if t == "r" else f"DihedralGroup.sr {j}"
    return f"(Multiplicative.ofAdd ({i} : ZMod 5), {d})"


# ---------------------------------------------- closed-form H entries


def closed_form_H(G):
    """H_X/H_Z entries from the Eq. (J1) closed forms, in GAP-index
    space; validated entry-for-entry against group_model.mitten_code."""
    n = G.n
    inv = G.inv

    def hx(beta, h, m, x):
        if m == 4:
            return int(G.mul(int(inv[x]), h) in SETS[f"b{beta}"])
        if m % 2 != beta:
            return 0
        return int(G.mul(h, int(inv[x])) in SETS[f"a{m // 2}"])

    def hz(alpha, h, m, x):
        if m == 4:
            return int(G.mul(x, int(inv[h])) in SETS[f"a{alpha}"])
        if m // 2 != alpha:
            return 0
        return int(G.mul(int(inv[h]), x) in SETS[f"b{m % 2}"])

    HX = np.zeros((60, 150), dtype=np.uint8)
    HZ = np.zeros((60, 150), dtype=np.uint8)
    for i in range(2):
        for h in range(n):
            for m in range(5):
                for x in range(n):
                    HX[i * n + h, m * n + x] = hx(i, h, m, x)
                    HZ[i * n + h, m * n + x] = hz(i, h, m, x)
    return HX, HZ


def fmt_list(items, per_line=6, indent="  "):
    lines = []
    for i in range(0, len(items), per_line):
        lines.append(indent + ", ".join(items[i : i + per_line])
                     + ("," if i + per_line < len(items) else ""))
    return "[\n" + "\n".join(lines) + "]"


def rref_rows(M: np.ndarray):
    """(pivot column list, W) with W·M[:,piv] = I over GF(2), asserting
    full row rank (with an independent inverse check after row reduction)."""
    m = M.shape[0]
    A = M.copy().astype(np.uint8)
    E = np.eye(m, dtype=np.uint8)
    piv, r = [], 0
    for c in range(M.shape[1]):
        nz = np.nonzero(A[r:, c])[0]
        if len(nz) == 0:
            continue
        p = r + nz[0]
        A[[r, p]] = A[[p, r]]
        E[[r, p]] = E[[p, r]]
        for i in range(m):
            if i != r and A[i, c]:
                A[i] ^= A[r]
                E[i] ^= E[r]
        piv.append(c)
        r += 1
        if r == m:
            break
    assert r == m, f"rank {r} < {m}"
    assert (E.astype(int) @ M[:, piv] % 2 == np.eye(m, dtype=int)).all()
    return piv, E


def nullspace(M: np.ndarray) -> np.ndarray:
    """Basis of ker over GF(2), rows = basis vectors."""
    m, n = M.shape
    A = M.copy().astype(np.uint8)
    piv, r = [], 0
    for c in range(n):
        if r >= m:
            break
        nz = np.nonzero(A[r:, c])[0]
        if len(nz) == 0:
            continue
        p = r + nz[0]
        A[[r, p]] = A[[p, r]]
        for i in range(m):
            if i != r and A[i, c]:
                A[i] ^= A[r]
        piv.append(c)
        r += 1
    free = [c for c in range(n) if c not in piv]
    basis = np.zeros((len(free), n), dtype=np.uint8)
    for k, c in enumerate(free):
        basis[k, c] = 1
        for i, pc in enumerate(piv):
            basis[k, pc] = A[i, c]
    assert not (M.astype(int) @ basis.T % 2).any()
    return basis


def symplectic_basis(HX, HZ):
    """(Lx, Lz) with rows Lx ⊂ ker H_Z, Lz ⊂ ker H_X, Lx·Lzᵀ = I₃₀,
    by greedy symplectic Gram–Schmidt over the kernel bases."""
    KZ = [v.copy() for v in nullspace(HX)]  # candidate Z-logicals
    KX = [v.copy() for v in nullspace(HZ)]  # candidate X-logicals
    Lx, Lz = [], []
    while len(Lz) < 30:
        found = None
        for iz, z in enumerate(KZ):
            for ix, x in enumerate(KX):
                if int(x @ z) % 2 == 1:
                    found = (iz, ix)
                    break
            if found:
                break
        assert found, "symplectic pairing exhausted early"
        iz, ix = found
        z, x = KZ.pop(iz), KX.pop(ix)
        KZ = [w ^ z if int(x @ w) % 2 else w for w in KZ]
        KX = [w ^ x if int(w @ z) % 2 else w for w in KX]
        Lz.append(z)
        Lx.append(x)
    Lx, Lz = np.array(Lx, dtype=np.uint8), np.array(Lz, dtype=np.uint8)
    assert not (HZ.astype(int) @ Lx.T % 2).any()
    assert not (HX.astype(int) @ Lz.T % 2).any()
    assert (Lx.astype(int) @ Lz.T % 2 == np.eye(30, dtype=int)).all()
    return Lx, Lz


def weight10_witness(HX, HZ, KX):
    """Validate the pinned weight-ten witness and its nonboundary pairing."""
    supports = json.loads((PACKAGE / "inputs/witness.json").read_text())
    vectors = []
    for name in ("witSup", "witPairSup"):
        support = supports[name]
        assert support == sorted(set(support))
        assert all(0 <= i < 150 for i in support)
        vector = np.zeros(150, dtype=np.uint8)
        vector[support] = 1
        vectors.append(vector)
    v, pair = vectors
    assert int(v.sum()) == 10
    assert not (HX.astype(int) @ v % 2).any()
    assert not (HZ.astype(int) @ pair % 2).any()
    assert int(pair @ v) % 2 == 1
    # Match the original generator's deterministic choice of pairing.
    assert np.array_equal(pair, next(x for x in KX if int(x @ v) % 2 == 1))
    return v, pair


def emit_instance(out_dir: Path, force: bool) -> None:
    """M2 data feed: canonical-labeling decoder/logical/witness data for
    `MittenDistance/M150/`, all validated before emission."""
    G = group_model.Group.from_file(GROUPS / "group_30_1.txt")
    table, carrier, (z, r, s) = build_dictionary(G)
    HX, HZ = closed_form_H(G)
    HXref, HZref = group_model.mitten_code(G, **SETS)
    assert (HX == HXref).all() and (HZ == HZref).all()

    pivX, WX = rref_rows(HX)
    pivZ, WZ = rref_rows(HZ)
    # decoder form: phi·(∂ basis matrix) = I with phi supported on pivots;
    # equivalently W·H[:,piv] = I plus square-inverse symmetry — validate
    # the exact identity the Lean file will check: for all i, p:
    # Σ_j W[i,j]·H[p, piv_j] = [i = p] (H[:,piv]·W = I, square case).
    assert (HX[:, pivX].astype(int) @ WX % 2 == np.eye(60, dtype=int)).all()
    assert (HZ[:, pivZ].astype(int) @ WZ % 2 == np.eye(60, dtype=int)).all()

    Lx, Lz = symplectic_basis(HX, HZ)
    KX = nullspace(HZ)
    wit, witPair = weight10_witness(HX, HZ, KX)
    print(f"[gen] instance data validated: pivots/W both sides, "
          f"symplectic 30-basis (Lx wts {sorted(set(Lx.sum(1)))[:3]}…, "
          f"Lz wts {sorted(set(Lz.sum(1)))[:3]}…), witness wt "
          f"{int(wit.sum())} + pairing wt {int(witPair.sum())}")

    elems = [lean_elem(carrier(table[g])) for g in range(30)]
    sets_lean = {k: [lean_elem(carrier(table[g])) for g in v]
                 for k, v in SETS.items()}
    packedW = lambda W: [
        int("".join(str(b) for b in row[::-1]), 2) for row in W]
    sup = lambda v: [int(i) for i in np.flatnonzero(v)]

    def fmt_sup_rows(rows) -> str:
        # nested list-of-lists, every line ≤ 100 chars (repo linter)
        out = []
        for k, row in enumerate(rows):
            body = fmt_list([str(i) for i in sup(row)], per_line=14,
                            indent="   ")
            out.append("  " + body + ("," if k + 1 < len(rows) else ""))
        return "[\n" + "\n".join(out) + "]"

    instance_banner = (
        "/-\nGENERATED FILE — DO NOT HAND-EDIT.\n"
        "Emitted by mitten-distance-lean:scripts/mitten/generate_data.py "
        "(mode: instance)\nfrom scripts/mitten/inputs/group_30_1.txt + "
        "arXiv:2607.28795 Table XIII sets;\nall facts validated in numpy "
        "before emission (dictionary hom, closed-form H vs\n"
        "group_model.mitten_code, pivot inverses, symplectic basis, "
        "witness).\nRegen: python3 scripts/mitten/generate_data.py "
        "instance --out <M150 dir> --force\n"
        "Attempt state: qec-lab:pipeline/attempts/mitten_150_30_10/.\n-/"
    )
    data = f"""{instance_banner}
import QEC.Stabilizer.Framework.Homological.LiftedProduct
import Mathlib.GroupTheory.SpecificGroups.Dihedral

namespace Quantum
namespace Stabilizer
namespace Homological
namespace LP
namespace M150

/-- The `[[150,30,10]]` mitten group carrier: C₅ (multiplicative) × S₃. -/
abbrev M150G : Type := Multiplicative (ZMod 5) × DihedralGroup 3

/-- GAP `Elements(SmallGroup(30,1))` order → carrier (z^i·r^j·s^k
parameterization; z = idx 2, r = idx 3, s = idx 1). -/
def gapElems : List M150G := {fmt_list(elems, per_line=1)}

/-- Carrier element of a GAP index (junk-total via identity). -/
def elemOf (i : Nat) : M150G := gapElems.getD i 1

/-- Qubit cell of a canonical qubit index `30·m + g`. -/
def qubitOf (c : Nat) : Fin 5 × M150G :=
  (⟨(c / 30) % 5, Nat.mod_lt _ (by omega)⟩, elemOf (c % 30))

/-- Check cell of a canonical check index `30·i + g`. -/
def checkOf (k : Nat) : Fin 2 × M150G :=
  (⟨(k / 30) % 2, Nat.mod_lt _ (by omega)⟩, elemOf (k % 30))

/-- Table XIII sets (paper order a0, a1, b0, b1). -/
def a0 : List M150G := {fmt_list(sets_lean["a0"], per_line=1)}
def a1 : List M150G := {fmt_list(sets_lean["a1"], per_line=1)}
def b0 : List M150G := {fmt_list(sets_lean["b0"], per_line=1)}
def b1 : List M150G := {fmt_list(sets_lean["b1"], per_line=1)}

/-- Pivot qubit indices for `H_X` (canonical `30·m + g`). -/
def pivX : List Nat := {fmt_list([str(c) for c in pivX], per_line=15)}

/-- Pivot qubit indices for `H_Z`. -/
def pivZ : List Nat := {fmt_list([str(c) for c in pivZ], per_line=15)}

/-- Rows of `(H_X[:,pivX])⁻¹`, packed little-endian 60-bit Nats. -/
def wX : List Nat := {fmt_list([str(v) for v in packedW(WX)], per_line=4)}

/-- Rows of `(H_Z[:,pivZ])⁻¹`. -/
def wZ : List Nat := {fmt_list([str(v) for v in packedW(WZ)], per_line=4)}

/-- Supports of the 30 logical-Z chains (rows of `Lz`, ⊂ ker H_X). -/
def logZsup : List (List Nat) := {fmt_sup_rows(Lz)}

/-- Supports of the 30 logical-X chains (rows of `Lx`, ⊂ ker H_Z);
`Lx·Lzᵀ = I₃₀` (validated offline, re-checked in Lean). -/
def logXsup : List (List Nat) := {fmt_sup_rows(Lx)}

/-- Support of the weight-10 distance witness (∈ ker H_X, ∉ rowspace H_Z). -/
def witSup : List Nat := {fmt_list([str(i) for i in sup(wit)], per_line=14)}

/-- Support of its dual pairing (∈ ker H_Z, ⟨·, wit⟩ = 1). -/
def witPairSup : List Nat := {fmt_list([str(i) for i in sup(witPair)], per_line=14)}

end M150
end LP
end Homological
end Stabilizer
end Quantum
"""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "Data.lean"
    if target.exists() and not force:
        sys.exit(f"refusing to overwrite {target} (use --force)")
    target.write_text(data)
    print(f"[gen] wrote {target}")




# --------------------------------------------------- m4 (floor data) mode

M4_BANNER = """/-
GENERATED FILE — DO NOT HAND-EDIT.
Emitted by mitten-distance-lean:scripts/mitten/generate_data.py (mode: m4)
from scripts/mitten/inputs/group_30_1.txt + arXiv:2607.28795 Table XIII sets
and the exhaustive light-triple censuses scripts/mitten/inputs/m4_triples.json
(a32_m4_collect.py).  Every table and every split sweep (all four
instances, all modes) plus both t-joins are simulated bit-for-bit in
python against the Lean driver semantics before emission; the
kernel-checked classification and grouped-join certificates re-verify
all of it inside the build.
Regen: python3 scripts/mitten/generate_data.py m4
  --out <M150 dir> --force
Attempt state: qec-lab:pipeline/attempts/mitten_150_30_10/.
-/"""


def _inv2(M):
    n = M.shape[0]
    A = np.concatenate([M.copy().astype(np.uint8), np.eye(n, dtype=np.uint8)], 1)
    for c in range(n):
        nz = [i for i in range(c, n) if A[i, c]]
        assert nz, "singular"
        A[[c, nz[0]]] = A[[nz[0], c]]
        for q in range(n):
            if q != c and A[q, c]:
                A[q] ^= A[c]
    W = A[:, n:] % 2
    assert ((M @ W) % 2 == np.eye(n, dtype=int)).all()
    assert ((W @ M) % 2 == np.eye(n, dtype=int)).all()
    return W


def _pseudo_inv(M):
    """(P, ln, ann): A P c = c on range(A); left-null rows; full Ann list."""
    n = M.shape[0]
    A = M.copy().astype(np.uint8)
    E = np.eye(n, dtype=np.uint8)
    piv, r = [], 0
    for c in range(n):
        nz = np.flatnonzero(A[r:, c])
        if nz.size == 0:
            continue
        pp = r + nz[0]
        A[[r, pp]], E[[r, pp]] = A[[pp, r]], E[[pp, r]]
        for q in np.flatnonzero(A[:, c]):
            if q != r:
                A[q] ^= A[r]
                E[q] ^= E[r]
        piv.append(c)
        r += 1
    assert r == 28
    P = np.zeros((n, n), dtype=np.uint8)
    for k, pc in enumerate(piv):
        P[pc] = E[k]
    assert not A[r:].any()
    ln = E[r:] % 2
    for j in range(n):
        c = M[:, j] % 2
        assert not (ln @ c % 2).any()
        assert ((M @ (P @ c % 2)) % 2 == c).all()
    free = [c for c in range(n) if c not in piv]
    k0 = np.zeros(n, dtype=np.uint8)
    kers = []
    for f in free:
        u = np.zeros(n, dtype=np.uint8)
        u[f] = 1
        u ^= P @ (M[:, f] % 2) % 2
        assert not (M @ u % 2).any() and u.any()
        kers.append(u)
    ann = [k0, kers[0], kers[1], kers[0] ^ kers[1]]
    assert len({tuple(a) for a in ann}) == 4
    return P, ln, ann


def _msk(v):
    return int(sum(1 << i for i in np.flatnonzero(np.asarray(v) % 2)))


def _cols(M):
    return [_msk(M[:, j]) for j in range(M.shape[1])]


def _xf(tbl, m):
    acc, i = 0, 0
    while m:
        if m & 1:
            acc ^= tbl[i]
        m >>= 1
        i += 1
    return acc


def _pop(m):
    return bin(m).count("1")


def emit_m4(out_dir: Path, force: bool) -> None:
    """M4 data feed: sweep tables, mode-assigned split lists, packed
    classification lists, and join row tables for the four triple
    instances — everything simulated bit-for-bit before emission."""
    from itertools import combinations
    from math import comb

    G = group_model.Group.from_file(GROUPS / "group_30_1.txt")
    mul, inv = G.mul, G.inv
    n = 30
    S = {k: set(v) for k, v in SETS.items()}

    def Lm(a):
        return np.array([[int(mul(h, int(inv[x])) in a) for x in range(n)]
                         for h in range(n)], dtype=np.uint8)

    def Rm(b):
        return np.array([[int(mul(int(inv[x]), h) in b) for x in range(n)]
                         for h in range(n)], dtype=np.uint8)

    def Lms(a):
        return np.array([[int(mul(x, int(inv[y])) in a) for x in range(n)]
                         for y in range(n)], dtype=np.uint8)

    def Rms(b):
        return np.array([[int(mul(int(inv[y]), x) in b) for x in range(n)]
                         for y in range(n)], dtype=np.uint8)

    A0, A1 = Lm(S["a0"]), Lm(S["a1"])
    Rb = {0: Rm(S["b0"]), 1: Rm(S["b1"])}
    B0s, B1s = Rms(S["b0"]), Rms(S["b1"])
    As = {0: Lms(S["a0"]), 1: Lms(S["a1"])}
    A1i = _inv2(A1)
    B1si = _inv2(B1s)
    B0si = _inv2(B0s)
    As1i = _inv2(As[1])
    PU, lnU, annU = _pseudo_inv(A0)     # X side: coset on u
    PT, lnT, annT = _pseudo_inv(As[0])  # Z side alpha=0: coset on t

    triples = json.loads((OUT / "m4_triples.json").read_text())
    idcols = [1 << i for i in range(n)]
    zero16 = dict(tWC=[], tTC=[], tP=[], ln0=0, ln1=0, ann=[],
                  tUC=[], tWC2=[], tPT=[], lnT0=0, lnT1=0, annT=[])

    inst = {}
    for beta in (0, 1):
        Ri = _inv2(Rb[beta])
        T = dict(zero16)
        T.update(
            tUW=_cols(A1i @ A0 % 2), tTW=_cols(A1i @ Rb[beta] % 2),
            tUT=_cols(Ri @ A0 % 2), tWT=_cols(Ri @ A1 % 2),
            tWC=_cols(A1), tTC=_cols(Rb[beta]), tP=_cols(PU),
            ln0=_msk(lnU[0]), ln1=_msk(lnU[1]),
            ann=[_msk(a) for a in annU],
        )
        inst[f"X{beta}"] = dict(T=T, modes=(0, 1, 2))
    for alpha in (0, 1):
        T = dict(zero16)
        T.update(
            tUW=_cols(B1si @ B0s % 2), tTW=_cols(B1si @ As[alpha] % 2),
            tUT=[], tWT=[],
            # mode 2 with a trivial coset = unique u-derivation
            tWC=_cols(B0si @ B1s % 2), tTC=_cols(B0si @ As[alpha] % 2),
            tP=list(idcols), ln0=0, ln1=0, ann=[0],
            # mode 3: coset (alpha=0) or trivial (alpha=1) on t
            tUC=_cols(B0s), tWC2=_cols(B1s),
            tPT=_cols(PT) if alpha == 0 else _cols(As1i),
            lnT0=_msk(lnT[0]) if alpha == 0 else 0,
            lnT1=_msk(lnT[1]) if alpha == 0 else 0,
            annT=[_msk(a) for a in annT] if alpha == 0 else [0],
        )
        inst[f"Z{alpha}"] = dict(T=T, modes=(0, 2, 3))

    # mode-assigned split lists (even totals <= 8; parity kills the rest)
    for name, I in inst.items():
        T, modes = I["T"], I["modes"]
        splits = []
        maxk = 0
        total = 0
        for ssum in range(0, 9, 2):
            for pp in range(ssum + 1):
                for qq in range(ssum + 1 - pp):
                    rr = ssum - pp - qq
                    opts = []
                    if 0 in modes:
                        opts.append((comb(30, pp) * comb(30, rr), 0, (pp, rr)))
                    if 1 in modes:
                        opts.append((comb(30, pp) * comb(30, qq), 1, (pp, qq)))
                    if 2 in modes:
                        opts.append((comb(30, qq) * comb(30, rr)
                                     * (3 + len(T["ann"])), 2, (qq, rr)))
                    if 3 in modes:
                        opts.append((comb(30, pp) * comb(30, qq)
                                     * (3 + len(T["annT"])), 3, (pp, qq)))
                    cost, mode, ks = min(opts)
                    splits.append((pp, qq, rr, mode))
                    maxk = max(maxk, *ks)
                    total += cost
        assert maxk <= 5, f"{name}: enumerated weight {maxk} > 5"
        I["splits"] = splits
        I["cost"] = total
        cls = sorted(
            (u | (w << 30) | (t << 60))
            for (u, w, t) in map(tuple, triples[name]["sols"])
            if (u, w, t) != (0, 0, 0))
        assert len(cls) == triples[name]["n"] - 1
        I["cls"] = cls
        print(f"[m4] {name}: {len(splits)} splits, ~{total:,} class-cost, "
              f"{len(cls)} classified triples")

    # join row tables (pack5) straight from the group data
    rows = {}
    for side in ("X", "Z"):
        rs = []
        for g in range(n):
            if side == "X":
                yb0 = _msk([int(x in {mul(g, t) for t in S["b0"]}) for x in range(n)])
                yb1 = _msk([int(x in {mul(g, t) for t in S["b1"]}) for x in range(n)])
                t0 = _msk([int(x in {mul(t, g) for t in S["a0"]}) for x in range(n)])
                t1 = _msk([int(x in {mul(t, g) for t in S["a1"]}) for x in range(n)])
                rs.append(yb0 | (yb1 << 60) | (t0 << 120))
                rs.append((yb0 << 30) | (yb1 << 90) | (t1 << 120))
            else:
                a0h = _msk([int(x in {mul(t, g) for t in
                                      {int(inv[s]) for s in S["a0"]}}) for x in range(n)])
                a1h = _msk([int(x in {mul(t, g) for t in
                                      {int(inv[s]) for s in S["a1"]}}) for x in range(n)])
                tb0 = _msk([int(x in {mul(g, t) for t in
                                      {int(inv[s]) for s in S["b0"]}}) for x in range(n)])
                tb1 = _msk([int(x in {mul(g, t) for t in
                                      {int(inv[s]) for s in S["b1"]}}) for x in range(n)])
                rs.append(a0h | (a1h << 60) | (tb0 << 120))
                rs.append((a0h << 30) | (a1h << 90) | (tb1 << 120))
        assert len(set(rs)) == 60
        rows[side] = sorted(rs)

    # ---------------- bit-for-bit simulation of every Lean obligation
    km = {k: [sum(1 << i for i in c) for c in combinations(range(n), k)]
          for k in range(0, 6)}

    def sim_check_split(T, cls_set, pp, qq, rr, mode):
        if mode == 0:
            for mu in km[pp]:
                fu = _xf(T["tUW"], mu)
                for mt in km[rr]:
                    mw = fu ^ _xf(T["tTW"], mt)
                    if _pop(mw) == qq and (mu | mw | mt) != 0 \
                            and (mu | (mw << 30) | (mt << 60)) not in cls_set:
                        return False
        elif mode == 1:
            for mu in km[pp]:
                fu = _xf(T["tUT"], mu)
                for mw in km[qq]:
                    mt = fu ^ _xf(T["tWT"], mw)
                    if _pop(mt) == rr and (mu | mw | mt) != 0 \
                            and (mu | (mw << 30) | (mt << 60)) not in cls_set:
                        return False
        elif mode == 2:
            for mw in km[qq]:
                fw = _xf(T["tWC"], mw)
                for mt in km[rr]:
                    c = fw ^ _xf(T["tTC"], mt)
                    if _pop(T["ln0"] & c) % 2 or _pop(T["ln1"] & c) % 2:
                        continue
                    up = _xf(T["tP"], c)
                    for a in T["ann"]:
                        mu = up ^ a
                        if _pop(mu) == pp and (mu | mw | mt) != 0 \
                                and (mu | (mw << 30) | (mt << 60)) not in cls_set:
                            return False
        else:
            for mu in km[pp]:
                fu = _xf(T["tUC"], mu)
                for mw in km[qq]:
                    c = fu ^ _xf(T["tWC2"], mw)
                    if _pop(T["lnT0"] & c) % 2 or _pop(T["lnT1"] & c) % 2:
                        continue
                    tp = _xf(T["tPT"], c)
                    for a in T["annT"]:
                        mt = tp ^ a
                        if _pop(mt) == rr and (mu | mw | mt) != 0 \
                                and (mu | (mw << 30) | (mt << 60)) not in cls_set:
                            return False
        return True

    t0 = time.perf_counter()
    for name, I in inst.items():
        cs = set(I["cls"])
        for (pp, qq, rr, mode) in I["splits"]:
            assert sim_check_split(I["T"], cs, pp, qq, rr, mode), \
                f"{name} sweep fires off-list at {(pp, qq, rr)} mode {mode}"
    print(f"[m4] all four instance sweeps simulate clean "
          f"({time.perf_counter() - t0:.0f}s)")

    m60 = (1 << 60) - 1
    for side, (n0, n1) in (("X", ("X0", "X1")), ("Z", ("Z0", "Z1"))):
        rset = set(rows[side])
        j1 = [(pk, pk >> 60, _pop(pk & ((1 << 30) - 1)) + _pop((pk >> 30) & ((1 << 30) - 1)))
              for pk in inst[n1]["cls"]]
        for pk0 in inst[n0]["cls"]:
            t = pk0 >> 60
            w0 = _pop(pk0 & ((1 << 30) - 1)) + _pop((pk0 >> 30) & ((1 << 30) - 1))
            for (pk1, t1, w1) in j1:
                if t != t1 or w0 + w1 + _pop(t) > 9:
                    continue
                p5 = (pk0 & m60) | ((pk1 & m60) << 60) | (t << 120)
                assert p5 in rset, f"{side} join off-row"
    print("[m4] both joins simulate clean")

    # ---------------- emission
    def fmt_nats(name, vals, per=4, chunk=1000):
        if len(vals) <= chunk:
            lines = [f"def {name} : List Nat := ["]
            for i in range(0, len(vals), per):
                seg = ", ".join(str(v) for v in vals[i:i + per])
                sep = "," if i + per < len(vals) else "]"
                lines.append(f"  {seg}{sep}")
            if not vals:
                lines = [f"def {name} : List Nat := []"]
            return "\n".join(lines)
        parts = []
        names = []
        for ci, lo in enumerate(range(0, len(vals), chunk)):
            nm = f"{name}c{ci}"
            names.append(nm)
            parts.append(fmt_nats(nm, vals[lo:lo + chunk], per))
        parts.append(f"def {name} : List Nat := {' ++ '.join(names)}")
        return "\n".join(parts)

    secs = [M4_BANNER,
            "import MittenDistance.M150.FloorCore",
            "",
            "set_option maxRecDepth 65536",
            "",
            "namespace Quantum",
            "namespace Stabilizer",
            "namespace Homological",
            "namespace LP",
            "namespace M150",
            ""]
    for name, I in inst.items():
        T = I["T"]
        for fld in ("tUW", "tTW", "tUT", "tWT", "tWC", "tTC", "tP",
                    "tUC", "tWC2", "tPT"):
            secs.append(fmt_nats(f"{fld}{name}", T[fld]))
        secs.append(fmt_nats(f"ann{name}", T["ann"], per=2))
        secs.append(fmt_nats(f"annT{name}", T["annT"], per=2))
        secs.append(fmt_nats(f"cls{name}", I["cls"], per=3))
        secs.append(
            f"/-- Sweep tables of instance {name} (see `FloorCore.SweepTables`). -/\n"
            f"def m4T{name} : SweepTables where\n"
            f"  tUW := tUW{name}\n  tTW := tTW{name}\n"
            f"  tUT := tUT{name}\n  tWT := tWT{name}\n"
            f"  tWC := tWC{name}\n  tTC := tTC{name}\n  tP := tP{name}\n"
            f"  ln0 := {T['ln0']}\n  ln1 := {T['ln1']}\n  ann := ann{name}\n"
            f"  tUC := tUC{name}\n  tWC2 := tWC2{name}\n  tPT := tPT{name}\n"
            f"  lnT0 := {T['lnT0']}\n  lnT1 := {T['lnT1']}\n  annT := annT{name}\n"
            f"  cls := cls{name}")
        spl_items = [f"({pp}, {qq}, {rr}, {mm})"
                     for (pp, qq, rr, mm) in I["splits"]]
        spl_lines = []
        for lo in range(0, len(spl_items), 6):
            seg = ", ".join(spl_items[lo:lo + 6])
            sep = "," if lo + 6 < len(spl_items) else "]"
            spl_lines.append(f"  {seg}{sep}")
        secs.append(f"/-- Mode-assigned even splits (≤ 8) of {name}. -/\n"
                    f"def splits{name} : List (Nat × Nat × Nat × Nat) := [\n"
                    + "\n".join(spl_lines))
        secs.append("")
    # bridge-layer tables (M4 chain plumbing): raw operator columns and
    # true inverses the derived-form lemmas compose against.  Validated
    # falsify-first here and by scripts/a32_m4_bridge_check.py.
    bridge = dict(
        tRawAX=_cols(A0),                 # raw L(a0) — X-side u-coefficient
        tCinvX0=_cols(_inv2(Rb[0])),      # R(b0)^-1  — X0 t-derivation
        tCinvX1=_cols(_inv2(Rb[1])),      # R(b1)^-1  — X1 t-derivation
        tRawCZ0=_cols(As[0]),             # raw L(a0~) — Z0 t-coefficient
        tRawCZ1=_cols(As[1]),             # raw L(a1~) — Z1 t-coefficient
        tAinvZ=_cols(B0si),               # R(b0~)^-1 — Z u-derivation
    )
    for beta in (0, 1):
        ci, T = bridge[f"tCinvX{beta}"], inst[f"X{beta}"]["T"]
        for i in range(n):
            assert _xf(ci, T["tTC"][i]) == 1 << i
            assert _xf(ci, bridge["tRawAX"][i]) == T["tUT"][i]
            assert _xf(ci, T["tWC"][i]) == T["tWT"][i]
            assert _xf(T["tTW"], T["tWT"][i]) == 1 << i
            assert _xf(T["tTW"], T["tUT"][i]) == T["tUW"][i]
            assert (_xf(T["tP"], bridge["tRawAX"][i]) ^ (1 << i)) in set(T["ann"])
    for alpha in (0, 1):
        rc, T = bridge[f"tRawCZ{alpha}"], inst[f"Z{alpha}"]["T"]
        for i in range(n):
            assert _xf(bridge["tAinvZ"], T["tUC"][i]) == 1 << i
            assert _xf(bridge["tAinvZ"], T["tWC2"][i]) == T["tWC"][i]
            assert _xf(bridge["tAinvZ"], rc[i]) == T["tTC"][i]
            assert _xf(T["tUW"], T["tWC"][i]) == 1 << i
            assert _xf(T["tUW"], T["tTC"][i]) == T["tTW"][i]
            assert (_xf(T["tPT"], rc[i]) ^ (1 << i)) in set(T["annT"])
    print("[m4] bridge tables validated (comp-ids, inverses, corr ∈ Ann)")
    secs.append("/-! Bridge-layer tables (M4 chain plumbing): raw operator\n"
                "columns and true inverses; see `FloorBridge.lean`. -/")
    for nm, vals in bridge.items():
        secs.append(fmt_nats(nm, vals))
    secs.append("")
    secs.append(fmt_nats("rowsXpk", rows["X"], per=2))
    secs.append(fmt_nats("rowsZpk", rows["Z"], per=2))
    secs += ["", "end M150", "end LP", "end Homological",
             "end Stabilizer", "end Quantum", ""]

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "FloorData.lean"
    if target.exists() and not force:
        sys.exit(f"refusing to overwrite {target} (use --force)")
    target.write_text("\n".join(secs))
    print(f"[m4] wrote {target}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=["instance", "m4"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.mode == "instance":
        emit_instance(args.out, args.force)
    else:
        emit_m4(args.out, args.force)


if __name__ == "__main__":
    main()
