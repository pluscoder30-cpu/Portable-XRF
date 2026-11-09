// scan.cpp — the portable scan chain body.
// Feed fetch (open-meteo, keyless — the SAME input the certified desktop
// instrument reads), the engine's normative endmember mix (ported), the
// Law 2396 register, and the Law 2397 coin-class check.
#include "scan.h"
#include <math.h>
#include <HTTPClient.h>

namespace xrf {
namespace scan {

static const char* OPEN_METEO =
    "http://air-quality-api.open-meteo.com/v1/air-quality?latitude=40.7000"
    "&longitude=-74.0000&current=pm10,pm2_5,dust&timezone=UTC";

static double findMetalSigma(uint8_t z) {
  for (int i = 0; i < XRF_N_METALS; ++i)
    if (XRF_METALS[i].z == z) return XRF_METALS[i].sigma;
  return 0.0;
}

static const char* findMetalSym(uint8_t z) {
  for (int i = 0; i < XRF_N_METALS; ++i)
    if (XRF_METALS[i].z == z) return XRF_METALS[i].sym;
  return "?";
}

static bool isRegistered(uint8_t z) {
  for (int i = 0; i < XRF_N_METALS; ++i)
    if (XRF_METALS[i].z == z) return true;
  return false;
}

// ---- the normative mix of the feed PM (air.py ported) -------------------
static void normativeMix(const Reading& r, double frac[MIX1_N]) {
  double total = r.pm10 > 0 ? r.pm10 : r.pm2_5;
  double coarse = 0.0;
  if (r.pm10 > 0 && r.pm2_5 > 0 && r.pm10 > 0)
    coarse = max(0.0, (r.pm10 - r.pm2_5) / r.pm10);
  double dust_frac;
  if (r.dust > 0) {
    dust_frac = min(0.60, max(0.05, r.dust / total));
  } else {
    dust_frac = min(0.60, max(0.10, coarse));   // the 0.10 floor proxy
  }
  double sulfate = 0.30;
  double sea_salt = coarse < 0.20 ? 0.05 : 0.15;
  double soot = max(0.0, 1.0 - dust_frac - sulfate - sea_salt);
  // the mineral_dust split onto its five minerals (x dust_frac)
  frac[0] = dust_frac * 0.55;   // quartz
  frac[1] = dust_frac * 0.15;   // orthoclase
  frac[2] = dust_frac * 0.10;   // albite
  frac[3] = dust_frac * 0.08;   // anorthite
  frac[4] = dust_frac * 0.12;   // kaolinite
  frac[5] = sea_salt;           // halite
  frac[6] = sulfate * 0.70;     // ammonium_sulfate
  frac[7] = sulfate * 0.30;     // gypsum
  frac[8] = 0.0;                // carbonate: the normative mix has none
  (void)soot;                    // soot is the carbonaceous stand-in
  double norm = 0.0;
  for (int i = 0; i < (int)MIX1_N; ++i) norm += frac[i];
  if (norm <= 0) norm = 1.0;
  for (int i = 0; i < (int)MIX1_N; ++i) frac[i] /= norm;
}

// ---- the scan -----------------------------------------------------------
Reading computeRegister(const Reading& feed) {
  Reading out = feed;
  double frac[MIX1_N];
  normativeMix(feed, frac);

  double total = feed.pm10 > 0 ? feed.pm10 : feed.pm2_5;

  // element ug/m3 = sum over minerals (mass-fraction of the element in the
  // mineral) * (mineral ug/m3)   [engine/minerals stoichiometry]
  double elem[40];   // ug/m3 per Z (index = z-1)
  const char* esym[40];
  for (int i = 0; i < 40; ++i) elem[i] = 0.0;
  for (int i = 0; i < (int)MIX1_N; ++i) {
    double mineral_ug_m3 = MIX1[i].frac * total;
    if (mineral_ug_m3 <= 0) continue;
    // find the mineral's fractions in ENDMEMBERS
    for (auto& em : ENDMEMBERS) {
      if (strcmp(em.name, MIX1[i].mineral) != 0) continue;
      for (int k = 0; k < em.n; ++k) {
        const char* sym = em.fr[k].sym;
        // element index by symbol lookup through the table (metals),
        // plus the spoken nonmetals (O,N,C,H,Cl,S,Na)
        uint8_t z = 0;
        for (int j = 0; j < XRF_N_METALS; ++j)
          if (strcmp(XRF_METALS[j].sym, sym) == 0) { z = XRF_METALS[j].z; break; }
        if (z == 0) {  // nonmetal symbols: H1 C6 N7 O8 Na11 Cl17 S16
          if (sym[0]=='O') z = 8; else if (sym[0]=='C' && sym[1]==0) z = 6;
          else if (sym[0]=='N' && sym[1]==0) z = 7;
          else if (sym[0]=='H' && sym[1]==0) z = 1;
          else if (strcmp(sym, "Cl") == 0) z = 17;
          else if (strcmp(sym, "S") == 0) z = 16;
          else if (strcmp(sym, "Na") == 0) z = 11;
        }
        if (z >= 1 && z <= 40) elem[z - 1] += em.fr[k].w * mineral_ug_m3;
      }
      break;
    }
  }

  // the Law 2396 register: kappa->0 nominal, kappa=1 reading
  for (uint8_t z = 1; z <= 40; ++z) {
    double c = elem[z - 1];
    if (c <= 0) continue;
    Row row;
    row.z = z;
    bool registered = isRegistered(z);
    if (registered) row.symbol = findMetalSym(z);
    else {
      // the spoken nonmetal symbols
      if (z == 8) row.symbol = "O"; else if (z == 6) row.symbol = "C";
      else if (z == 7) row.symbol = "N"; else if (z == 1) row.symbol = "H";
      else if (z == 17) row.symbol = "Cl"; else if (z == 16) row.symbol = "S";
      else if (z == 11) row.symbol = "Na";
      else continue;
    }
    row.c_ug_m3 = c;
    row.c_ppm_nominal = ugM3ToPpm(c);
    row.reading_ppm = phiMotion(row.c_ppm_nominal, 1.0);
    if (!registered) row.mode = "spoken_nonmetal";
    else if (c > 0) row.mode = "quantified";
    else row.mode = "field_carried";
    out.rows.push_back(row);

    // the coin-class check for register metals with a coil signature
    if (registered && findMetalSigma(z) > 0.0) {
      for (int i = 0; i < XRF_N_METALS; ++i) {
        if (XRF_METALS[i].z != z) continue;
        coil::CoinPpm cp = coil::coinResponsePpm(XRF_METALS[i],
                                                 BASE_FREQUENCY);
        Reading::Coin cc{XRF_METALS[i].sym, cp.total(),
                         cp.inphase > cp.quadrature};
        out.coin.push_back(cc);
        break;
      }
    }
  }
  return out;
}

// ---- the feed fetch (open-meteo, keyless) -------------------------------
bool fetchFeed(Reading& r) {
  HTTPClient http;
  http.setConnectTimeout(5000);
  http.setTimeout(8000);
  if (!http.begin(OPEN_METEO)) return false;
  int code = http.GET();
  bool ok = (code == 200);
  if (ok) {
    String body = http.getString();
    // minimal field extraction (the feed's tiny JSON current block)
    auto grab = [&](const char* key, double* dst) {
      int i = body.indexOf(key);
      if (i < 0) return false;
      i = body.indexOf(':', i) + 1;
      int j = body.indexOf(',', i);
      int j2 = body.indexOf('}', i);
      if (j2 >= 0 && (j < 0 || j2 < j)) j = j2;
      String v = body.substring(i, j);
      v.trim();
      *dst = v.toDouble();
      return true;
    };
    grab("\"pm10\"", &r.pm10);
    grab("\"pm2_5\"", &r.pm2_5);
    grab("\"dust\"", &r.dust);
    int ti = body.indexOf("\"time\"");
    if (ti > 0) {
      int q1 = body.indexOf('"', ti + 7);
      int q2 = body.indexOf('"', q1 + 1);
      r.time_iso = body.substring(q1 + 1, q2);
    }
    r.status = "ok";
  }
  http.end();
  return ok;
}

String readingToJson(const Reading& r) {
  String s = "{";
  s += "\"schema\":\"xrf-portable/reading-v1\",";
  s += "\"pm10\":" + String(r.pm10, 3);
  s += ",\"pm2_5\":" + String(r.pm2_5, 3);
  s += ",\"dust\":" + String(r.dust, 3);
  s += ",\"time\":\"" + r.time_iso + "\",\"status\":\"" + r.status + "\"";
  s += ",\"law\":\"PHI-2396\",\"kappa\":1.0";
  s += ",\"floor_ppm\":" + String((double)xrf::PHI_SQ_INV, 10);
  s += ",\"rows\":[";
  for (size_t i = 0; i < r.rows.size(); ++i) {
    const Row& row = r.rows[i];
    if (i) s += ",";
    s += "{\"z\":" + String(row.z);
    s += ",\"sym\":\"" + String(row.symbol) + "\"";
    s += ",\"ug_m3\":" + String(row.c_ug_m3, 4);
    s += ",\"ppm0\":" + String(row.c_ppm_nominal, 8);
    s += ",\"ppm\":" + String(row.reading_ppm, 8);
    s += ",\"mode\":\"" + String(row.mode) + "\"}";
  }
  s += "],\"coin\":[";
  for (size_t i = 0; i < r.coin.size(); ++i) {
    if (i) s += ",";
    s += "{\"sym\":\"" + String(r.coin[i].symbol) + "\"";
    s += ",\"ppm\":" + String(r.coin[i].ppm, 1);
    s += ",\"class\":\"" + String(r.coin[i].inphase
                                  ? "inphase" : "quadrature") + "\"}";
  }
  s += "]}";
  return s;
}

// ---- the RANGE SCAN (the dashboard's range buttons) ----------------------
std::vector<RangeRow> computeRangeScan(double standoff_m, bool full) {
  std::vector<RangeRow> out;
  for (int i = 0; i < XRF_N_METALS; ++i) {
    const XrfMetal& m = XRF_METALS[i];
    if (m.sigma <= 0.0f) continue;        // no coil signature (spoken)
    RangeRow row{m.sym, standoff_m, 0.0, 0, 0.0, false, -1.0,
                 "field_carried_floor"};
    // best rung at the standoff
    double best = 0.0;
    int best_k = 0;
    for (int k = 0; k < 10; ++k) {
      coil::CoinPpm c = coil::coinResponsePpm(m, coil::ladderFreq(k),
                                              standoff_m);
      double t = c.total();
      if (t > best) { best = t; best_k = k; }
    }
    if (full) {
      // per-metal maximal detectable standoff (engine detection_range_m;
      // the 1.5 m cap is the desktop's own bisection bound — spoken)
      double range = coil::detectionRangeM(m, 1.5);
      row.best_rung = best_k;
      row.f_hz = coil::ladderFreq(best_k);
      row.standoff_m = range;
      row.range_m = range;
      row.ppm = best;                      // the response scale at design-cap
      row.verdict = range >= 1.5 ? "below_cap" :
          (range > 0.0 ? "quantified" : "field_carried_floor");
      row.inphase = coil::channelClassIsInphase(m, BASE_FREQUENCY);
    } else {
      coil::CoinPpm c = coil::coinResponsePpm(m, coil::ladderFreq(best_k),
                                              standoff_m);
      row.best_rung = best_k;
      row.f_hz = coil::ladderFreq(best_k);
      row.ppm = c.total();
      row.inphase = c.inphase > c.quadrature;
      row.verdict = row.ppm >= coil::MIN_DETECT_PPM
          ? "quantified" : "field_carried_floor";
    }
    out.push_back(row);
  }
  return out;
}

String rangeScanToJson(const char* preset,
                       const std::vector<RangeRow>& rows) {
  String s = "{\"schema\":\"xrf-portable/range-scan-v1\"";
  s += ",\"preset\":\"" + String(preset) + "\"";
  s += ",\"law\":\"PHI-2397\",\"provenance\":\"model (spoken) — the coin "
         "chain is code; the standoff is the declared [MODEL] variable\"";
  s += ",\"floor_ppm\":" + String((double)xrf::PHI_SQ_INV, 10);
  s += ",\"rows\":[";
  for (size_t i = 0; i < rows.size(); ++i) {
    const RangeRow& r = rows[i];
    if (i) s += ",";
    s += "{\"sym\":\"" + String(r.symbol) + "\"";
    s += ",\"rung\":" + String(r.best_rung);
    s += ",\"f_hz\":" + String(r.f_hz, 3);
    s += ",\"ppm\":" + String(r.ppm, 2);
    s += ",\"chan\":\"" + String(r.inphase ? "inphase" : "quadrature") + "\"";
    if (r.range_m >= 0.0)
      s += ",\"range_m\":" + String(r.range_m, 3);
    s += ",\"verdict\":\"" + String(r.verdict) + "\"}";
  }
  s += "]}";
  return s;
}

}  // namespace scan
}  // namespace xrf
