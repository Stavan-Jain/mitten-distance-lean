"""Finite-group and lifted-product matrix model, extracted from qec-lab A26.

Only the group-table reader and the direct Eq. (J1) matrix construction are
retained; no search, graph-isomorphism, or research dependencies are required.
"""
from pathlib import Path
import numpy as np

class Group:
    """Finite group given by a multiplication table (0-based indices)."""

    def __init__(self, mt: np.ndarray, structure: str = "?"):
        self.mt = np.asarray(mt, dtype=np.int64)
        self.n = self.mt.shape[0]
        self.structure = structure
        eye = np.arange(self.n)
        e_cands = [i for i in range(self.n) if np.array_equal(self.mt[i], eye)]
        assert len(e_cands) == 1, f"identity not unique: {e_cands}"
        self.e = e_cands[0]
        self.inv = np.empty(self.n, dtype=np.int64)
        for g in range(self.n):
            w = np.nonzero(self.mt[g] == self.e)[0]
            assert len(w) == 1
            self.inv[g] = w[0]
        self.orders = np.empty(self.n, dtype=np.int64)
        for g in range(self.n):
            k, x = 1, g
            while x != self.e:
                x = int(self.mt[x, g])
                k += 1
            self.orders[g] = k

    @classmethod
    def from_file(cls, path) -> "Group":
        # GAP wraps long lines with backslash continuations; undo them.
        lines = Path(path).read_text().replace("\\\n", "").splitlines()
        n = int(lines[0])
        structure = lines[1].strip()
        mt = np.array([list(map(int, l.split())) for l in lines[4 : 4 + n]])
        g = cls(mt, structure)
        orders = np.array(list(map(int, lines[2].split())))
        inv = np.array(list(map(int, lines[3].split())))
        assert np.array_equal(orders, g.orders), "order table mismatch vs GAP"
        assert np.array_equal(inv, g.inv), "inverse table mismatch vs GAP"
        assert g.e == 0, "GAP Elements(G) does not start with identity"
        return g

    def mul(self, a: int, b: int) -> int:
        return int(self.mt[a, b])

    def conj_set(self, t: int, supp) -> tuple:
        ti = int(self.inv[t])
        return tuple(sorted(int(self.mt[self.mt[t, s], ti]) for s in supp))

    def center(self) -> list[int]:
        return [g for g in range(self.n) if np.array_equal(self.mt[g], self.mt[:, g])]

    def involutions(self) -> list[int]:
        return [g for g in range(self.n) if self.orders[g] == 2]

    def central_involutions(self) -> list[int]:
        c = set(self.center())
        return [g for g in self.involutions() if g in c]


# ----------------------------------------------------- ring-rep matrices


def Lmat(G: Group, supp) -> np.ndarray:
    """L(a)[y,x] = 1 iff y = g*x for some g in supp  (L(g)b(h)=b(gh))."""
    M = np.zeros((G.n, G.n), dtype=np.uint8)
    cols = np.arange(G.n)
    for g in supp:
        M[G.mt[g, cols], cols] ^= 1
    return M


def Rmat(G: Group, supp) -> np.ndarray:
    """R(a)[y,x] = 1 iff y = x*g^-1 for some g in supp  (R(g)b(h)=b(hg^-1))."""
    M = np.zeros((G.n, G.n), dtype=np.uint8)
    cols = np.arange(G.n)
    for g in supp:
        gi = int(G.inv[g])
        M[G.mt[cols, gi], cols] ^= 1
    return M


def star(G: Group, supp) -> tuple:
    return tuple(sorted(int(G.inv[g]) for g in supp))


def mitten_code(G: Group, a0, a1, b0, b1):
    """H_X, H_Z of LP([a0 a1],[b0 b1]) per arXiv:2607.28795 Eq. (J1)."""
    Z = np.zeros((G.n, G.n), dtype=np.uint8)
    HX = np.block(
        [
            [Lmat(G, a0), Z, Lmat(G, a1), Z, Rmat(G, star(G, b0))],
            [Z, Lmat(G, a0), Z, Lmat(G, a1), Rmat(G, star(G, b1))],
        ]
    )
    HZ = np.block(
        [
            [Rmat(G, b0), Rmat(G, b1), Z, Z, Lmat(G, star(G, a0))],
            [Z, Z, Rmat(G, b0), Rmat(G, b1), Lmat(G, star(G, a1))],
        ]
    )
    return HX.astype(np.uint8), HZ.astype(np.uint8)
