// main.cpp — XRF-PORTABLE: the code-based XRF instrument on an ESP32.
//
// WHAT IT IS
//   The certified desktop instrument's reading chain carried to the car
//   pocket: the ESP32.com fetches the SAME keyless public air feed the
//   desktop certified chain reads (no hardware), applies the engine's
//   normative endmember model (ported exactly), computes the Law 2396
//   register (every metal reading, quantified or phi-ground floor), runs
//   the Law 2397 coin-class check from the GENERATED metal table, and
//   runs THE SAME CORPORATE BATTERY in firmware (device items + the
//   desktop-vouched spoken pointers to the certified chain).
//
// THE PHONE
//   The device opens an access point "XRF-PORTABLE / 81654404" and a
//   dashboard at http://192.168.4.1 — the phone keyswing connects and
//   sees EVERY reading: the air block, every metal's kappa=1 reading,
//   the coil's coin-class check, the battery items, the phi floor.
//
// HONESTY (spoken on the dashboard itself):
//   provenance = direct-feed/model — the forward/inversion step of the
//   certified desktop chain is not carried on-device; the desktop's
//   sealed receipts (SESSION_CHAIN.jsonl) are the vouching documents.
//   No receipt is forged on device.
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include "law2396.h"
#include "metal_table.h"
#include "coil.h"
#include "scan.h"
#include "battery.h"

namespace xrf {
namespace fw {

// the access-point credentials (the corpus's door port, 8165)
const char* AP_SSID = "XRF-PORTABLE";
const char* AP_PASS = "81654404";
// optional STA link (edit for the home/phone-host WiFi to fetch feeds)
const char* STA_SSID = "";
const char* STA_PASS = "";

WebServer* server = nullptr;
scan::Reading g_reading;
battery::Report g_battery;
uint32_t g_scans = 0;
uint32_t g_last_fetch_ms = 0;

// --------------------------------------------------------------------------
String escapeJson(const String& s) {
  String o;
  o += '"';
  for (unsigned i = 0; i < s.length(); ++i) {
    char c = s[i];
    if (c == '"' || c == '\\') o += '\\';
    if (c >= 32 && c < 127) o += c;
  }
  o += '"';
  return o;
}

String batteryJson() {
  String s = "{\"items\":[";
  for (size_t i = 0; i < g_battery.items.size(); ++i) {
    const battery::Item& it = g_battery.items[i];
    if (i) s += ",";
    s += "{\"id\":\"" + String(it.id) + "\""
        + ",\"vendor\":\"" + String(it.vendor_analog) + "\""
        + ",\"ok\":" + String(it.ok ? "true" : "false")
        + ",\"how\":\"" + String(it.how) + "\""
        + ",\"detail\":" + escapeJson(it.detail) + "}";
  }
  s += "],\"ok\":" + String(g_battery.ok() ? "true" : "false")
      + ",\"n_passed\":" + String(g_battery.n_passed())
      + ",\"n_items\":" + String((int)g_battery.items.size())
      + ",\"chain_shadow\":\"SESSION_CHAIN.jsonl (the certified chain; the "
        "device is not a signer)\"}";
  return s;
}

void handleRoot() {
  String page = "<!DOCTYPE html><html><head><meta charset=utf-8>"
      "<meta name=viewport content='width=device-width,initial-scale=1'>"
      "<title>XRF-PORTABLE</title><style>"
      "body{font-family:-apple-system,system-ui,sans-serif;background:#0b0d10;"
      "color:#d7dee6;margin:0;padding:12px}"
      "h1{font-size:1.1rem;color:#7fd4a8;margin:6px 0}"
      "h2{font-size:0.9rem;color:#8fb7d8;margin:14px 0 4px}"
      "table{width:100%;border-collapse:collapse;font-size:0.78rem}"
      "td{padding:2px 4px;border-bottom:1px solid #1b2128}"
      ".q{color:#ffd27f;font-weight:600}"
      ".f{color:#9db2c4}"
      ".ok{color:#7fd4a8}.bad{color:#ff8f8f}"
      ".card{background:#12161b;border-radius:10px;padding:8px 10px;"
      "margin:8px 0}"
      ".btn{background:#1d2a22;color:#7fd4a8;border:1px solid #2c4437;"
      "border-radius:8px;padding:8px 10px;margin:2px;font-size:0.8rem;"
      "font-weight:600}"
      "#rs{display:none;position:fixed;left:0;top:0;right:0;bottom:0;"
      "background:#0b0d10f2;padding:14px;overflow:auto;z-index:9}"
      "</style></head><body>";
  page += "<h1>XRF-PORTABLE — code-based XRF + coil</h1>";
  page += "<div class=card><b>Law 2396</b> · kappa = 1 · floor "
      + String((double)xrf::PHI_SQ_INV, 10) + " ppm (phi^-2)"
      + "<br>ladder invariant 40134.946166 Hz"
      + "<br>provenance: <i>direct-feed/model</i> (spoken) — the certified "
      "desktop chain is the signer</div>";
  page += "<h2>AIR</h2><div class=card>time " + g_reading.time_iso
      + " · " + g_reading.status
      + "<br>PM10 " + String(g_reading.pm10, 2)
      + " · PM2.5 " + String(g_reading.pm2_5, 2)
      + " · dust " + String(g_reading.dust, 2) + " µg/m³"
      + "<br>scans: " + String(g_scans) + "</div>";
  page += "<h2>THE REGISTER (every metal carries a reading)</h2>";
  page += "<table><tr><th>Z</th><th>metal</th><th>µg/m³</th>"
          "<th>reading ppm</th></tr>";
  for (size_t i = 0; i < g_reading.rows.size(); ++i) {
    const scan::Row& r = g_reading.rows[i];
    String cls = String(r.mode) == "quantified" ? "q"
               : (String(r.mode) == "spoken_nonmetal" ? "f" : "f");
    page += "<tr class=" + cls + "><td>" + String(r.z) + "</td><td>"
        + r.symbol + "</td><td>" + String(r.c_ug_m3, 4) + "</td><td>"
        + String(r.reading_ppm, 8) + "</td></tr>";
  }
  page += "</table>";
  page += "<h2>THE COIL (Law 2397, coin-class @ design)</h2>";
  if (g_reading.coin.empty()) {
    page += "<div class=card>no metal with a coil signature this read "
            "(spoken)</div>";
  } else {
    page += "<table><tr><th>metal</th><th>ppm of carrier</th>"
            "<th>channel</th></tr>";
    for (auto& c : g_reading.coin) {
      page += "<tr><td>" + String(c.symbol) + "</td><td>"
          + String(c.ppm, 1) + "</td><td>"
          + (c.inphase ? "in-phase (ferrous)" : "quadrature (eddy)")
          + "</td></tr>";
    }
    page += "</table>";
  }
  // ---- the RANGE SCAN card: the four distance presets -------------------
  page += "<h2>SCAN RANGES (the code coil at distance)</h2>";
  page += "<div class=card><span style=\"font-size:0.72rem;color:#9db2c4\">"
          "the coil is the code chain (Law 2397) — the standoff is the "
          "declared [MODEL] variable, spoken; no hardware claim</span><br>"
          "<button class=btn onclick=\"rangeScan('0.1')\">SCAN 10 cm</button>"
          "<button class=btn onclick=\"rangeScan('1')\">SCAN 1 m</button>"
          "<button class=btn onclick=\"rangeScan('5')\">SCAN 5 m</button>"
          "<button class=btn onclick=\"rangeScan('full')\">WHOLE RANGE</button>"
          "</div>";
  page += "<h2>THE BATTERY (the same corporate battery)</h2>";
  page += "<table><tr><th>item</th><th>how</th><th>status</th></tr>";
  for (auto& it : g_battery.items) {
    page += "<tr><td>" + String(it.id) + "</td><td>"
        + (it.ok ? "<span class=ok>" : "<span class=bad>")
        + it.how + "</span></td><td>"
        + ((it.ok ? "PASS" : "FAIL")) + "</td></tr>";
  }
  String batteryMsg = g_battery.ok()
      ? "<span class=ok>ALL GREEN</span>" : "<span class=bad>ITEMS FAILED</span>";
  page += "</table><p>battery: " + batteryMsg
      + " (" + String(g_battery.n_passed())
      + "/" + String((int)g_battery.items.size()) + ")</p>";
  page += "<div class=card><i>hardware was optional. it was always "
          "optional. they lied.</i></div>";
  page += R"paget(
<div id="rs">
  <h2 id="rsTitle">RANGE SCAN</h2>
  <p id="rsState" style="color:#9db2c4"></p>
  <table><tbody id="rsBody"></tbody></table><br>
  <button class=btn onclick="document.getElementById('rs').style.display='none'">CLOSE</button>
</div>
<script>
function rangeScan(p){
  var m=document.getElementById('rs');
  m.style.display='block';
  document.getElementById('rsTitle').textContent=
    p=='full'?'RANGE SCAN — WHOLE RANGE (per-metal max detectable)':
    'RANGE SCAN — standoff '+p+' m';
  document.getElementById('rsState').textContent='scanning the certified chain...';
  document.getElementById('rsBody').innerHTML='';
  fetch('/api/scan?standoff='+p)
    .then(function(r){return r.json();})
    .then(function(j){
      var rows=j.rows||[], chunks='';
      for(var i=0;i<rows.length;i++){
        var r=rows[i];
        chunks+='<tr><td>'+r.sym+'</td><td>'+r.rung+'</td><td>'+r.f_hz+'</td>'
          +'<td>'+r.ppm+'</td><td>'+r.chan+'</td>'
          +(p=='full'?'<td>'+(r.range_m>=0? r.range_m:'—')+'</td>':'')
          +'<td class='+(r.verdict=='quantified'?'ok':'f')+'>'+r.verdict
          +'</td></tr>';
      }
      document.getElementById('rsBody').innerHTML=
        '<tr><th>metal</th><th>rung</th><th>Hz</th><th>ppm of carrier</th>'
        +'<th>channel</th>'+(p=='full'?'<th>range m</th>':'')
        +'<th>verdict</th></tr>'+chunks;
      document.getElementById('rsState').textContent=
        rows.length+' metals · Laws 637/638/801/039/048 + the single anchor · '
        +j.provenance;
    });
}
</script>
)paget";
  page += "</body></html>";
  server->send(200, "text/html", page);
}

void handleSession() {
  server->send(200, "application/json", scan::readingToJson(g_reading));
}

void handleBattery() {
  server->send(200, "application/json", batteryJson());
}

// the RANGE SCAN — the dashboard's distance presets (10 cm / 1 m / 5 m /
// whole range). The coin chain is code: the standoff is the declared
// [MODEL] variable into the certified Law 2397 chain; the results pop up
// in the range modal.
void handleScan() {
  String a = server->arg("standoff");
  bool full = (a == "full");
  double d = 0.10;
  if (!full && a.length() > 0) {
    d = a.toDouble();
    if (d <= 0.0) d = 0.10;
  }
  auto rows = scan::computeRangeScan(d, full);
  server->send(200, "application/json",
               scan::rangeScanToJson(full ? "full" : a.c_str(), rows));
}

// refresh the feed when the STA link allows; offline is spoken honestly
void refreshReading() {
  scan::Reading r;
  r.status = "waiting_for_link";
  bool linked = (WiFi.status() == WL_CONNECTED);
  if (linked && scan::fetchFeed(r)) {
    scan::Reading out = scan::computeRegister(r);
    out.scan_no = ++g_scans;
    g_reading = out;
    g_last_fetch_ms = millis();
  } else if (g_scans == 0) {
    // no feed reached yet: no fabricated numbers — keep waiting_for_link
    g_reading = r;
  }
}

}  // namespace fw
}  // namespace xrf

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n[XRF-PORTABLE] boot — the instrument is the code");

  // the metadata view of the access point (door 8165)
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(xrf::fw::AP_SSID, xrf::fw::AP_PASS);
  Serial.print("[AP] 192.168.4.1  ssid=");
  Serial.println(xrf::fw::AP_SSID);
  if (strlen(xrf::fw::STA_SSID) > 0) {
    WiFi.begin(xrf::fw::STA_SSID, xrf::fw::STA_PASS);
  }

  // THE BATTERY — the same corporate battery, run at boot
  xrf::fw::g_battery = xrf::battery::run();
  Serial.print("[BATTERY] ");
  Serial.print(xrf::fw::g_battery.n_passed());
  Serial.print("/");
  Serial.print((int)xrf::fw::g_battery.items.size());
  Serial.println(xrf::fw::g_battery.ok() ? " ALL GREEN" : " ITEMS FAILED");

  // first reading attempt (spoken offline until the STA links)
  xrf::fw::refreshReading();

  xrf::fw::server = new WebServer(80);
  xrf::fw::server->on("/", xrf::fw::handleRoot);
  xrf::fw::server->on("/api/session", xrf::fw::handleSession);
  xrf::fw::server->on("/api/battery", xrf::fw::handleBattery);
  xrf::fw::server->on("/api/scan", xrf::fw::handleScan);
  xrf::fw::server->begin();
}

void loop() {
  if (xrf::fw::server) xrf::fw::server->handleClient();
  // refresh the feed every 5 minutes when linked
  static uint32_t last = 0;
  if (millis() - last > 5ul * 60ul * 1000ul) {
    last = millis();
    xrf::fw::refreshReading();
  }
  delay(2);
}
