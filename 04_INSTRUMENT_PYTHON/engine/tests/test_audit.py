"""The per-element law audit as permanent regression gates.

The headline invariant under test: EVERY registered metal carries the SAME
zero-mass floor the gold reading carries — the phi^-2 ground, 0.3819660113
ppm at kappa=1 (Law 2396, unit-covariant ground; the code double is within
1 ulp of the closest representable) — and the same classical-term
structure at any loading.  The audit re-derives everything by hand from
raw constants and data; these tests run the audit and pin its verdicts.
"""
from __future__ import annotations

import pytest

from engine import audit as eng_audit
from engine import metals as eng_metals
from engine import phi_laws


@pytest.fixture(scope="module")
def report():
    # one audit run for the whole module (the artifact is also written)
    return eng_audit.audit_all()


# ---------------------------------------------------------------------------
# the headline
# ---------------------------------------------------------------------------
def test_every_element_passes_every_applicable_check(report):
    assert report["n_elements"] == len(eng_metals.registry()) == 75
    assert report["n_passed"] == report["n_elements"]
    assert report["n_failed"] == 0
    for row in report["elements"]:
        failing = [k for k, c in row["checks"].items() if not c["ok"]]
        assert not failing, f"{row['symbol']}: failing {failing}"


def test_gold_parity_floor_is_exact_element_by_element():
    # the floor is the FIELD's ground, not the element's — verified by hand
    for sym in ("Au", "Fe", "Cu", "U", "Mg", "Ag", "Pb", "Ti", "K"):
        reg = eng_audit.register_empty(sym)
        assert reg["floor_exact"], reg
        assert reg["reading"] == pytest.approx(phi_laws.PHI_SQ_INV, abs=1e-15)


def test_loading_symmetry_any_element_same_reading():
    # 1 ug/cm2 of ANY two elements reads identically: the classical term is
    # element-independent in ppm (masster -> ug/m3 -> ppm chain) and the
    # ground in the field
    for a, b in (("Fe", "Au"), ("Cu", "U"), ("Al", "Pb"), ("K", "Mg")):
        ra = eng_audit.register_loaded(a, 1.0)
        rb = eng_audit.register_loaded(b, 1.0)
        assert ra["phi"] == rb["phi"]
        assert ra["phi"] == pytest.approx(
            ra["k0"] * (1.0 + phi_laws.PHI_INV) + phi_laws.PHI_SQ_INV,
            rel=1e-15)


def test_global_structures_hold(report):
    assert report["d1_empty_register_floor"]["ok"] is True
    assert report["d1_empty_register_floor"]["n_rows"] == 75
    assert report["d2_loading_symmetry"]["ok"] is True
    assert report["l5_moseley_coherence"]["ok"] is True
    ka1 = [g for g in report["l5_moseley_coherence"]["groups"]
           if g["line"] == "Ka1"][0]
    assert ka1["monotone"] and ka1["n"] >= 25


# ---------------------------------------------------------------------------
# per-element classical spot checks (Law 1347 identities from the raw data)
# ---------------------------------------------------------------------------
def test_binding_identity_gold_and_copper():
    rep = eng_audit.audit_element("Au")
    ident = {i["line"]: i
             for i in rep["checks"]["L3_binding_identity"]["detail"]["identities"]}
    # gold's K lines sit above the window; its L-series carries the identity
    la1 = ident["La1"]
    assert la1["rel_err"] <= 0.02
    assert la1["actual"] == pytest.approx(9713.0, abs=0.1)
    rep_cu = eng_audit.audit_element("Cu")
    ident_cu = {i["line"]: i
                for i in rep_cu["checks"]["L3_binding_identity"]["detail"]["identities"]}
    assert ident_cu["Ka1"]["rel_err"] <= 0.02
    assert ident_cu["Ka1"]["actual"] == pytest.approx(8046.3, abs=0.1)


def test_yield_identity_is_exact_and_model_coherent():
    for sym in ("Al", "Fe", "Cu", "Au", "U"):
        row = eng_audit.audit_element(sym)
        c = row["checks"]["L4_yield_identity"]["detail"]
        assert c["omega_K"] + c["auger"] == pytest.approx(1.0, abs=1e-12)
        assert 0.0 <= c["omega_K"] <= 1.0


def test_coil_channel_discipline_and_plan():
    for sym in ("Fe", "Co", "Ni"):
        row = eng_audit.audit_element(sym)
        c = row["checks"]["K2_channel_discipline"]["detail"]
        assert c["ferrous"] and c["inphase_ppm"] > c["quadrature_ppm"] > 0.0
    for sym in ("Cu", "Al", "Ag", "W"):
        row = eng_audit.audit_element(sym)
        c = row["checks"]["K2_channel_discipline"]["detail"]
        assert not c["ferrous"] and c["inphase_ppm"] == 0.0
        assert c["quadrature_ppm"] > 0.0
    # the declared plan re-derives identically under the audit's own scan
    for sym in ("Fe", "Cu", "Pb", "U", "Ti", "Al"):
        row = eng_audit.audit_element(sym)
        c = row["checks"]["K4_plan_consistency"]["detail"]
        assert c["declared_rung"] == c["derived_rung"]
        assert c["declared_channel"] == c["derived_channel"]


def test_coil_still_floor_by_conductivity_class():
    # no conductivity (Pm): both channels exactly the floor
    row = eng_audit.audit_element("Pm")
    assert row["checks"]["K3b_still_floor"]["ok"]
    assert "exactly" in row["checks"]["K3b_still_floor"]["detail"][
        "both_channels_phi"]
    # microscopic conductivity (Te): a tiny carried term ABOVE the floor
    row_te = eng_audit.audit_element("Te")
    c = row_te["checks"]["K3b_still_floor"]["detail"]
    assert c["quadrature_phi"] > c["floor"]
    # nonferrous conductors: the still in-phase channel is exactly the floor
    row_cu = eng_audit.audit_element("Cu")
    assert row_cu["checks"]["K3_coil_gold_parity"]["ok"]


def test_xrf_only_metals_speak_their_coil_absence():
    for sym in ("Pm", "At", "Fr", "Ac", "Pa"):
        row = eng_audit.audit_element(sym)
        for k in ("K2_channel_discipline", "K4_plan_consistency",
                  "K5_range_honesty"):
            assert row["checks"][k]["ok"], sym


def test_audit_self_check_and_artifact(report):
    assert eng_audit.self_check() == []
