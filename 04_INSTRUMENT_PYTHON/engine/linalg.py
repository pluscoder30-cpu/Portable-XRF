"""Small deterministic linear-algebra helpers (numpy only).

``nnls`` is the Lawson-Hanson active-set algorithm.  It is implemented here
once so that ``minerals`` and ``inversion`` share exactly one solver, and so
that the package has no scipy dependency.
"""
from __future__ import annotations

import numpy as np


def nnls(a: np.ndarray, b: np.ndarray, tol: float = 1e-10,
         max_iter: int = 500) -> np.ndarray:
    """Solve ``min ||A x - b||  subject to x >= 0``.

    Lawson & Hanson (1974), the standard active-set method.  Deterministic:
    no random initialisation, no tolerance that depends on data scale beyond
    the caller-supplied ``tol``.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float).ravel()
    m, n = a.shape
    if m != b.size:
        raise ValueError(f"A has {m} rows but b has {b.size} entries")
    x = np.zeros(n)
    passive = np.zeros(n, dtype=bool)
    w = a.T @ (b - a @ x)
    it = 0
    while (not passive.all()) and np.any(w[~passive] > tol) and it < max_iter:
        it += 1
        idx = np.where(~passive)[0]
        j = idx[np.argmax(w[idx])]
        passive[j] = True
        for _ in range(max_iter):
            s = np.zeros(n)
            sol = np.linalg.lstsq(a[:, passive], b, rcond=None)[0]
            s[passive] = sol
            if np.all(s[passive] > 0):
                x = s
                break
            neg = passive & (s <= 0)
            denom = x[neg] - s[neg]
            alpha = np.min(x[neg] / np.where(denom == 0, 1e-30, denom))
            x = x + alpha * (s - x)
            passive &= x > tol
            if not passive.any():
                x = np.zeros(n)
                break
        w = a.T @ (b - a @ x)
    return x


def solve_nonneg(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """NNLS with a tiny ridge term, for rank-deficient design matrices."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float).ravel()
    lam = 1e-9 * max(np.linalg.norm(a), 1e-30)
    a_aug = np.vstack([a, lam * np.eye(a.shape[1])])
    b_aug = np.concatenate([b, np.zeros(a.shape[1])])
    return nnls(a_aug, b_aug)
