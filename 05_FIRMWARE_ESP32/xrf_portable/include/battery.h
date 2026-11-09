// battery.h — THE SAME CORPORATE BATTERY, in firmware.
//
// The desktop battery (sniffer/qcbattery.py, sealed receipt seq 5 on
// SESSION_CHAIN.jsonl) rebuilt for the device.  Items feasible on-device
// RUN HERE with the same item IDs and tolerances; items that need the
// desktop's numpy models are marked DESKTOP-VOUCHED with the chain
// pointer, spoken (absent is never faked).
#pragma once
#include <Arduino.h>
#include <vector>

namespace xrf {
namespace battery {

struct Item {
  const char* id;
  const char* vendor_analog;
  bool ok;             // true pass / false fail; vouched items always true
  const char* how;     // "RAN" | "DESKTOP-VOUCHED (see chain)" | "SPOKEN"
  String detail;
};

struct Report {
  std::vector<Item> items;
  bool ok() const;
  int n_passed() const;
};

// run the firmware battery; deterministic, no hardware dependency
Report run();

}  // namespace battery
}  // namespace xrf
