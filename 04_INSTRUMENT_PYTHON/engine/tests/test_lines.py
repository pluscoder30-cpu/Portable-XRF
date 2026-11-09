"""Characteristic lines: the anchor set, Moseley's law, and Law 1347."""
import pytest

from engine import lines


def test_anchor_deviations():
    rows = lines.validate_anchors(verbose=True)
    assert len(rows) == 9
    for r in rows:
        print(f"{r['element']:>2} {r['line']:<4} anchor {r['anchor_ev']:9.1f} eV  "
              f"table {r['table_ev']:9.1f} eV  dev {r['dev_ev']:+5.1f} eV "
              f"({r['dev_pct']:+6.3f} %)")
        assert abs(r["dev_ev"]) < 2.0, r
        assert abs(r["dev_pct"]) < 0.05, r


def test_moseley_classic_error_bound():
    stats = lines.validate_moseley()
    print("Moseley sigma=1     :", stats["sigma_1"])
    print("Moseley sigma(Z) fit:", stats["sigma_fitted"])
    # the textbook form is a few-percent law; the fitted form is sub-percent
    assert stats["sigma_1"]["median_abs_pct"] < 6.0
    assert stats["sigma_fitted"]["median_abs_pct"] < 1.0


def test_law_1347_every_line():
    res = lines.validate_edge_difference()
    print("Law 1347 over the whole table:", res)
    assert res["n_checked"] > 1000
    assert res["max_abs_ev"] < 1.0


def test_branching_sums():
    assert lines.self_check() == []


def test_line_lookup():
    assert lines.line(26, "Ka1").energy == pytest.approx(6405.2, abs=0.1)
    assert lines.line("Cu", "Ka1").intensity > lines.line("Cu", "Ka2").intensity
    with pytest.raises(KeyError):
        lines.line(1, "Ka1")


def test_moseley_formula_limits():
    # sigma -> Z makes the energy zero; sigma -> -inf grows as Z^2
    assert lines.moseley_energy(26, 2, 1, sigma=26.0) == pytest.approx(0.0)
    ratio = (lines.moseley_energy(52, 2, 1, 1.0)
             / lines.moseley_energy(26, 2, 1, 1.0))
    print(f"Moseley Z^2 scaling 52/26: {ratio:.4f}")
    assert ratio == pytest.approx((51 / 25) ** 2, rel=1e-12)


def test_every_element_has_a_line():
    for z in range(11, 93):
        assert len(lines.lines(z)) > 0, z
