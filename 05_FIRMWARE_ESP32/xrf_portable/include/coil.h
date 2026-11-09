// coil.h — Law 2397's coil chain, ported exactly from engine/coil.py.
// The declared geometry, the design anchor (Cu coin = 10,000 ppm of the
// nulled carrier @ 528 Hz @ 0.10 m) and the Laws 637/638/801/039/048
// formulas — the same closed forms, device doubles.
#pragma once
#include <math.h>
#include "law2396.h"
#include "metal_table.h"

namespace xrf {
namespace coil {

// the declared coil geometry (engine/coil.py, [MODEL/DECLARED])
constexpr int N_TX = 200;
constexpr int N_RX = 200;
constexpr double COIL_RADIUS_M = 0.04;
constexpr double COIL_LENGTH_M = 0.01;
constexpr double PAIR_SEPARATION_M = 0.30;
constexpr double DRIVE_CURRENT_A = 0.1;
constexpr double COIN_RADIUS_M = 0.0125;
constexpr double COIN_THICKNESS_M = 0.002;
constexpr double DESIGN_STANDOFF_M = 0.10;
constexpr double DESIGN_RESPONSE_PPM = 10000.0;  // the single anchor
constexpr double MIN_DETECT_PPM = 30.0;
constexpr double M_SAT_FERRO = 1.7e6;
constexpr double MU_R_FERRO_THRESHOLD = 10.0;
constexpr double SHEET_BAND_W_M = 0.004;

inline double selfInductance() {
  return MU_0 * double(N_TX) * double(N_TX) * 3.14159265358979323846
      * COIL_RADIUS_M * COIL_RADIUS_M / COIL_LENGTH_M;
}

// LAW 637 (near-field dipole form)
inline double mutual(double d, double a1, double a2, int n1, int n2) {
  return MU_0 * double(n1) * double(n2) * 3.14159265358979323846
      * (a1 * a1 * a2 * a2)
      / (2.0 * pow(a1 * a1 + d * d, 1.5));
}

// the coin-class target's eddy response (quadrature), engine coil.py.
// `standoff_m` defaults to the design standoff so every existing call site
// keeps its exact bit pattern; the range presets (10 cm / 1 m / 5 m /
// whole-range) pass their own declared standoff [MODEL].
inline double rawCoinEddy(double sigma, double mu_r, double omega,
                          double standoff_m = DESIGN_STANDOFF_M) {
  double d_tx = standoff_m;
  double d_rx = fabs(PAIR_SEPARATION_M - d_tx);
  double m_tt = mutual(d_tx, COIL_RADIUS_M, COIN_RADIUS_M, N_TX, 1);
  double m_rt = mutual(d_rx, COIL_RADIUS_M, COIN_RADIUS_M, N_RX, 1);
  double l_geo = MU_0 * mu_r * COIN_RADIUS_M
      * (log(8.0 * COIL_RADIUS_M / 5e-4) - 2.0);
  double delta = sqrt(2.0 / (sigma * MU_0 * mu_r * omega));
  double t_active = delta < COIN_THICKNESS_M ? delta : COIN_THICKNESS_M;
  double r_eddy = (1.0 / sigma) * (2.0 * 3.14159265358979323846
                                   * COIL_RADIUS_M)
      / (SHEET_BAND_W_M * t_active);
  double z = sqrt(r_eddy * r_eddy + omega * omega * l_geo * l_geo);
  return omega * omega * m_tt * m_rt * DRIVE_CURRENT_A / z;  // volts
}

// the ferrous in-phase magnetization channel (standoff-parameterized,
// default = design, bit-identical to the pre-range build)
inline double rawCoinInphase(double mu_r, double omega,
                             double standoff_m = DESIGN_STANDOFF_M) {
  if (mu_r < MU_R_FERRO_THRESHOLD) return 0.0;
  double h = (MU_0 * double(N_TX) * DRIVE_CURRENT_A
              * COIL_RADIUS_M * COIL_RADIUS_M
              / (2.0 * pow(COIL_RADIUS_M * COIL_RADIUS_M
                           + standoff_m * standoff_m, 1.5)))
      / MU_0;
  double chi = mu_r - 1.0;
  double m_eff = chi * h < M_SAT_FERRO ? chi * h : M_SAT_FERRO;
  double volume = 3.14159265358979323846 * COIN_RADIUS_M * COIN_RADIUS_M
      * COIN_THICKNESS_M;
  double m_dip = m_eff * volume;
  double d_rx = fabs(PAIR_SEPARATION_M - standoff_m);
  double b_dip = MU_0 / (4.0 * 3.14159265358979323846) * 2.0 * m_dip
      / (d_rx * d_rx * d_rx);
  double area_rx = 3.14159265358979323846 * COIL_RADIUS_M * COIL_RADIUS_M;
  return omega * b_dip * area_rx;  // volts
}

struct CoinPpm {
  double inphase;
  double quadrature;
  double total() const { return sqrt(inphase * inphase
                                     + quadrature * quadrature); }
};

// K_null = design_V * 100 (the declared calibration anchor)
inline double nullV() {
  const XrfMetal* cu = nullptr;
  for (int i = 0; i < XRF_N_METALS; ++i)
    if (XRF_METALS[i].z == 29) cu = &XRF_METALS[i];
  double omega = 2.0 * 3.14159265358979323846 * BASE_FREQUENCY;
  double v = rawCoinEddy(cu->sigma, cu->mu_r, omega)
      + rawCoinInphase(cu->mu_r, omega);
  return v * 100.0;
}

// (in-phase, quadrature) reading in ppm of the nulled carrier, kappa base
inline CoinPpm coinResponsePpm(const XrfMetal& m, double f_hz,
                               double standoff_m = DESIGN_STANDOFF_M) {
  double omega = 2.0 * 3.14159265358979323846 * double(f_hz);
  double k_null = nullV();
  double q = m.sigma > 0 ? 1e6 * rawCoinEddy(m.sigma, m.mu_r, omega,
                                             standoff_m) / k_null
                         : 0.0;
  double ip = m.sigma > 0 ? 1e6 * rawCoinInphase(m.mu_r, omega, standoff_m)
                                  / k_null
                          : 0.0;
  // zero does not exist in a READING (Law 171): the phi-ground is carried
  // per channel at declared coupling by the caller (phiMotion).
  return {ip, q};
}

// ---- the range-scan layer (the range buttons' certified model) -----------

// the ladder rung frequencies f_k = 528*phi^k, engine ladder_frequencies
inline double ladderFreq(int k) {
  return BASE_FREQUENCY * pow(PHI, double(k));
}

// the metal's maximal coin-detectable standoff (engine detection_range_m:
// bisect to >= MIN_DETECT_PPM on the best rung; the same 0.005 m floor,
// 1.5 m cap and 60-iteration bisection)
inline double detectionRangeM(const XrfMetal& m,
                              double cap_m = 1.5) {
  auto bestAt = [&](double d) {
    double best = 0.0;
    for (int k = 0; k < 10; ++k) {
      CoinPpm c = coinResponsePpm(m, ladderFreq(k), d);
      double t = sqrt(c.inphase * c.inphase + c.quadrature * c.quadrature);
      if (t > best) best = t;
    }
    return best;
  };
  double lo = 0.005, hi = cap_m;
  if (bestAt(lo) < MIN_DETECT_PPM) return 0.0;
  for (int i = 0; i < 60; ++i) {
    double mid = 0.5 * (lo + hi);
    if (bestAt(mid) >= MIN_DETECT_PPM) lo = mid;
    else hi = mid;
  }
  return lo;
}

// the channel class: ferrous -> in-phase magnetization, else quadrature
inline bool channelClassIsInphase(const XrfMetal& m, double f_hz) {
  CoinPpm r = coinResponsePpm(m, f_hz);
  return r.inphase > r.quadrature;
}

}  // namespace coil
}  // namespace xrf
