"""Element table: completeness, ordering, and known reference values."""
import pytest

from engine import elements


def test_table_is_complete():
    assert len(elements.ELEMENTS) == 92
    assert [e.z for e in elements.ELEMENTS] == list(range(1, 93))
    assert elements.self_check() == []


def test_symbols_and_names():
    assert elements.element(1).symbol == "H"
    assert elements.element("Fe").z == 26
    assert elements.element("iron").z == 26
    assert elements.element("U").z == 92
    assert elements.element("cu").symbol == "Cu"


@pytest.mark.parametrize("symbol,edge,expected", [
    ("Fe", "K", 7112.0),
    ("Cu", "K", 8979.0),
    ("Mo", "K", 20000.0),
    ("Ag", "K", 25514.0),
    ("Pb", "L3", 13035.0),
    ("Si", "K", 1839.0),
    ("Al", "K", 1559.0),
])
def test_known_edges(symbol, edge, expected):
    got = elements.edge_energy(symbol, edge)
    print(f"{symbol} {edge}: expected {expected} eV, got {got} eV, "
          f"deviation {got - expected:+.2f} eV")
    assert abs(got - expected) < 2.0


def test_mass_and_density():
    fe = elements.element("Fe")
    print(f"Fe mass {fe.mass} u (ref 55.845), density {fe.density} g/cm3 (ref 7.874)")
    assert abs(fe.mass - 55.845) < 0.01
    assert abs(fe.density - 7.874) < 0.05
    assert abs(elements.element("Al").density - 2.70) < 0.01
    assert abs(elements.element("Au").density - 19.3) < 0.2


def test_edge_ordering():
    for el in elements.ELEMENTS:
        seq = [el.edge(n) for n in ("K", "L1", "L2", "L3") if el.has_edge(n)]
        for a, b in zip(seq, seq[1:]):
            assert b <= a + 0.5, (el.symbol, a, b)   # Na L2/L3 differ by 0.1 eV


def test_missing_shell_raises():
    h = elements.element("H")
    assert h.edge("L1") == 0.0        # documented: 0.0 means "no such shell"
    assert not h.has_edge("L1")
    with pytest.raises(KeyError):
        h.edge("Q9")


def test_mass_fraction_round_trip():
    comp = {"Si": 0.4674, "O": 0.5326}
    areal = elements.mass_fraction_to_areal(comp, 1e-4)
    back = elements.areal_to_mass_fraction(areal)
    assert abs(back[14] - 0.4674) < 1e-9
