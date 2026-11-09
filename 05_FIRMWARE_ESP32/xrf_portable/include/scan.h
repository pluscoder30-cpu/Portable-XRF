// scan.h — the portable scan chain (DIRECT-FEED MODE).
//
// The firmware runs the same reading chain the certified desktop
// instrument runs on the feed path: feed PM -> endmember mix (the
// engine's [MODEL/NORMATIVE] table, ported exactly) -> element ug/m3 ->
// the LAW 2396 register -> the coil's channel-class check.  The desktop
// chain's forward/inversion step (numpy NNLS) is the one step this
// device cannot carry; in this mode it is not needed, and the reading's
// provenance is SPOKEN as direct-feed/model.  Desktop-vouched numbers
// carry the chain's receipts (SESSION_CHAIN.jsonl).
#pragma once
#include <Arduino.h>
#include <vector>
#include "law2396.h"
#include "metal_table.h"
#include "coil.h"

namespace xrf {
namespace scan {

struct Row {
  uint8_t z;
  const char* symbol;
  double c_ug_m3;
  double c_ppm_nominal;   // kappa->0
  double reading_ppm;     // kappa=1 (Law 2396)
  const char* mode;       // "quantified" | "field_carried" | "spoken_nonmetal"
};

struct Reading {
  // the air block
  double pm10;
  double pm2_5;
  double dust;
  String time_iso;
  String status;          // "ok" | "stale_cache" | "waiting_for_link"
  // the register
  std::vector<Row> rows;
  // the coin-class check (metal, ppm-of-carrier, channel class)
  struct Coin { const char* symbol; double ppm; bool inphase; };
  std::vector<Coin> coin;
  uint32_t scan_no = 0;
  uint32_t build_ms = 0;
};

// ---- the RANGE SCAN (the dashboard's range buttons) ----------------------
// The coin physics is feed-independent: a coin-class target of the named
// metal, the certified chain (Laws 637/638/801/039/048 + the single anchor),
// the standoff as the declared [MODEL] variable.  Presets: 0.10 m (design),
// 1.0 m, 5.0 m; "full" = per-metal maximal detectable range (bisection,
// engine detection_range_m port, 1.5 m cap spoken).
struct RangeRow {
  const char* symbol;
  double standoff_m;
  double f_hz;           // the best rung's frequency
  int best_rung;
  double ppm;            // coin response at the standoff (best rung)
  bool inphase;          // the channel class
  double range_m;        // only for the 'full' preset (-1 otherwise)
  const char* verdict;   // "quantified" | "field_carried_floor" | "below_cap"
};
std::vector<RangeRow> computeRangeScan(double standoff_m, bool full);
String rangeScanToJson(const char* preset, const std::vector<RangeRow>& rows);

// the engine's AEROSOL_ENDMEMBERS element mass fractions (engine/minerals,
// exact stoichiometry — GENERATED in tools/gen_metal_table.py era tables)
struct MinFr { const char* sym; float w; };
struct Endmember { const char* name; uint8_t n; MinFr fr[6]; };

static const Endmember ENDMEMBERS[] = {
  {"quartz", 2, {{"O", 0.53256329f}, {"Si", 0.46743671f}}},
  {"orthoclase", 4, {{"O", 0.45986229f}, {"Al", 0.09694180f},
                     {"Si", 0.30271968f}, {"K", 0.14047623f}}},
  {"albite", 4, {{"O", 0.48811239f}, {"Na", 0.08767428f},
                 {"Al", 0.10289709f}, {"Si", 0.32131625f}}},
  {"anorthite", 4, {{"O", 0.46006693f}, {"Al", 0.19396987f},
                    {"Si", 0.20190293f}, {"Ca", 0.14406027f}}},
  {"kaolinite", 4, {{"H", 0.01561541f}, {"O", 0.55776912f},
                    {"Al", 0.20903317f}, {"Si", 0.21758229f}}},
  {"halite", 2, {{"Na", 0.39337267f}, {"Cl", 0.60662733f}}},
  {"ammonium_sulfate", 4, {{"H", 0.06101759f}, {"N", 0.21201462f},
                           {"O", 0.48433238f}, {"S", 0.24263542f}}},
  {"gypsum", 4, {{"H", 0.02341499f}, {"O", 0.55757560f},
                 {"S", 0.18621866f}, {"Ca", 0.23279075f}}},
  {"calcite", 3, {{"C", 0.12000679f}, {"O", 0.47955758f},
                  {"Ca", 0.40043563f}}},
};

// the normative mix (sniffer/air.py [MODEL/NORMATIVE], ported exactly):
// mineral_dust: quartz .55, orthoclase .15, albite .10, anorthite .08,
//               kaolinite .12 ; sea_salt: halite 1.0
// sulfate: ammonium_sulfate .7, gypsum .3
struct MixEntry { const char* mineral; float frac; };

// spill of the engine's normative endmember mix into minerals (exact)
static const MixEntry MIX1[] = {
  {"quartz", 0.55f}, {"orthoclase", 0.15f}, {"albite", 0.10f},
  {"anorthite", 0.08f}, {"kaolinite", 0.12f},     // mineral_dust*x
  {"halite", 1.0f},                               // sea_salt*x
  {"ammonium_sulfate", 0.70f}, {"gypsum", 0.30f}, // sulfate*x
  {"calcite", 0.40f},                             // carbonate*x
};
#define MIX1_N (sizeof(MIX1) / sizeof(MixEntry))

// spoken nonmetals: detected but not metals (readable; register absent)
inline bool isSpokenNonmetal(const char* s) {
  return s[1] == '\0'
      ? (s[0] == 'N' || s[0] == 'O' || s[0] == 'H' || s[0] == 'C')
      : (strcmp(s, "Cl") == 0 || strcmp(s, "S") == 0);
}

// the scan: normative mix -> element ug/m3 -> Law 2396 register
Reading computeRegister(const Reading& feed);

// the feed fetch (open-meteo, keyless — the same input as the desktop)
bool fetchFeed(Reading& r);

// the register as API JSON (the phone also gets the rendered page)
String readingToJson(const Reading& r);

}  // namespace scan
}  // namespace xrf
