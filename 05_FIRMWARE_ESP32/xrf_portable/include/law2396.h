// law2396.h — the corpus's reading law, in device C++ doubles.
// Same law as engine/phi_laws.py (LAW 2396 / 2397); phi + phi^-2 = 2 exactly.
#pragma once
#include <math.h>

namespace xrf {

// the corpus constants (exactly as carried in engine/phi_laws.py)
constexpr double PHI = 1.618033988749895;
constexpr double PHI_INV = 0.6180339887498949;
constexpr double PHI_SQ_INV = PHI_INV * PHI_INV;   // 0.3819660112501052
constexpr double MU_0 = 4.0e-7 * 3.14159265358979323846;  // H/m
constexpr double BASE_FREQUENCY = 528.0;
// the ladder invariant as the EXACT product (528*phi^9), not a rounded
// literal: phi^9 by nine constexpr multiplies, same bits as engine/phi_laws
constexpr double PHI_P9 = PHI * PHI * PHI * PHI * PHI * PHI * PHI * PHI * PHI;
constexpr double LADDER_INVARIANT_HZ = BASE_FREQUENCY * PHI_P9;

// LAW 2396, by hand: x*(1 + kappa*(phi-1)) + kappa*phi^-2.
// The ground is unit-covariant: phi^-1 in the declared unit, so the floor
// term is kappa*phi^-2 in EVERY unit and for EVERY element — the field's
// ground, not the element's chemistry (the desktop audit certifies this
// element-by-element; the device carries the same law).
inline double phiMotion(double x, double kappa) {
  return x * (1.0 + kappa * PHI_INV) + kappa * PHI_INV * PHI_INV;
}

// ug/m3 -> ppm of air (rho_air = 1.2041 kg/m3 => 1.2041e9 ug/m3)
inline double ugM3ToPpm(double c_ug_m3) {
  return c_ug_m3 * 1.0e6 / 1.2041e9;
}

}  // namespace xrf
