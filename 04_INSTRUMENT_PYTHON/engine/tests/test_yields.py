"""Fluorescence yields and the Auger identity."""
import pytest

from engine import yields


def test_yield_anchors():
    rows = yields.validate_yields(verbose=True)
    assert len(rows) == 4
    for r in rows:
        print(f"{r['element']:>2} anchor {r['anchor']:.3f}  table {r['table']:.4f} "
              f"({r['table_dev_pct']:+6.2f} %)  model {r['model']:.4f} "
              f"({r['model_dev_pct']:+6.2f} %)")
    by = {r["element"]: r for r in rows}
    assert abs(by["Cu"]["table_dev_pct"]) < 2.0
    assert abs(by["Mo"]["table_dev_pct"]) < 5.0
    assert abs(by["Al"]["table_dev_pct"]) < 10.0
    # Fe: the anchor (0.32) and Krause & Oliver (0.351) differ by 10 %;
    # the table is reported, not tuned.
    assert abs(by["Fe"]["table_dev_pct"]) < 15.0


def test_powerlaw_model_error():
    stats = yields.validate_table_vs_model()
    print("omega_K power law vs Krause & Oliver:", stats)
    assert stats["median_abs_pct"] < 5.0


def test_auger_identity():
    for z in (6, 13, 26, 42, 82):
        w = yields.omega_k(z)
        a = yields.auger_yield(z, "K")
        print(f"Z={z:>2} omega_K {w:.4f} + Auger {a:.4f} = {w + a:.12f}")
        assert w + a == pytest.approx(1.0, abs=1e-12)


def test_yield_monotonic_in_z():
    vals = [yields.omega_k(z) for z in range(10, 93)]
    # the tabulated curve is monotonic to within 0.1 % (two neighbouring
    # points, Z=65/66, are equal to 3 decimals in Krause & Oliver)
    for a, b in zip(vals, vals[1:]):
        assert b >= a - 0.005, (a, b)
    assert vals[-1] > 0.95


def test_self_check():
    assert yields.self_check() == []
