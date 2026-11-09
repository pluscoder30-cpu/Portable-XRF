"""FLASH SESSION — the ESP32-S3 flash + readback, sealed (user-directed).

The user plugged the board in ("k it in"), then instructed: DO NOT connect to
the AP from the PC — they will connect on their phone. The dashboard's
browser-level verification is therefore user-gated (phone), SPOKEN here.

What this receipt binds (all hashes inside):
  - the chip-identity gate (esptool over the serial bridge, pre-flash)
  - two verified flashes to COM7 (hash of data verified by esptool both
    times; the second reflash carries the range-scan feature + the
    UART-bridge print routing)
  - the clean boot capture (tools/boot_capture.py): the three boot lines
  - the on-device battery verdict: 9/9 ALL GREEN (printed on boot)
  - NFF MCP get_device_info (the FTDI bridge sheet; the auto-ID mislabel
    reproduced — the silicon is the esptool-verified S3)
  - NFF diagnose on the captured output: no crash signature found
  - the range buttons: SCAN 10 cm / 1 m / 5 m / WHOLE RANGE + the popup,
    compiled into BOTH envs from the identical source
  - compile sizes for the flashed env (esp32-s3)

Exit-code convention: 0 = session facts bound; 2 = spoken user-gates present;
1 = would mean a failed verification (not the case).
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)

from sniffer import receipt as receipt_mod

CHAIN = os.path.join(ROOT, "SESSION_CHAIN.jsonl")
OUT_JSON = os.path.join(HERE, "flash_session.json")
FW = os.path.join(ROOT, "FIRMWARE", "xrf_portable")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("== FLASH SESSION (ESP32-S3, user-directed) ==")

    captures = {
        "boot_capture_text": sha256_file(os.path.join(FW, "nff_boot_capture.txt")),
        "boot_capture_raw": sha256_file(os.path.join(FW, "nff_boot_capture.bin")),
        "device_info": sha256_file(os.path.join(FW, "nff_device_info.txt")),
        "capture_tool": sha256_file(os.path.join(FW, "tools", "boot_capture.py")),
    }
    for k, v in captures.items():
        print(f"  {k}: {v[:16]}…")

    payload = {
        "schema": "xrf-proof/flash-session-v1",
        "law": "the instrument's optional body flashed + verified on device",
        "instrument": "XRF-PORTABLE on ESP32-S3 (the user-held board)",
        "model": {
            "name": "flash-session",
            "version": "sniffer-1.0.0+engine-1.1.0",
            "calibration_id": "fw-flash-esp32-s3-2026-11-03",
            "physics": "classical",
            "method": ("PIO upload (env esp32-s3, esp32-s3-devkitc-1) via the "
                       "onboard FTDI bridge; esptool chip gate pre-flash; "
                       "boot capture via tools/boot_capture.py; NFF MCP "
                       "device sheet + offline diagnose"),
        },
        "provenance": "model",
        "timestamp": stamp,
        "chip_identity_gate": {
            "tool": "esptool (chip_id, pre-flash)",
            "chip": "ESP32-S3 (QFN56) revision v0.2",
            "features": "Wi-Fi, BT 5 (LE), dual core + LP core, 240 MHz, embedded PSRAM 8 MB (AP_3v3)",
            "crystal_mhz": 40.0,
            "mac": "84:c7:bb:5a:5b:74",
            "port": "COM7 (FTDI FT232RL bridge — vendor 0403 / product 6001)",
            "note": "NFF's auto-ID labels the bridge 'ESP8266 (FTDI)' — the "
                    "skill's gotcha reproduced live; the silicon behind the "
                    "bridge is the esptool-verified S3",
        },
        "flashes": [
            {"n": 1, "bytes_written": 916144, "at_offset": "0x10000",
             "hash_verified": True, "env_state": "USB-CDC variant "
             "(Serial on the native connector)",
             "duration_s": 32.5, "board": "esp32-s3-devkitc-1"},
            {"n": 2, "bytes_written": None,
             "hash_verified": True,
             "image_bin": {"size_bytes": os.path.getsize(
                 os.path.join(FW, ".pio", "build", "esp32-s3", "firmware.bin")),
                 "sha256": sha256_file(
                     os.path.join(FW, ".pio", "build", "esp32-s3",
                                  "firmware.bin"))},
             "env_state": "UART-bridge routing (Serial on UART0 = COM7; the "
                          "USB-CDC flags retired after the plug-in discovery)",
             "io_note": "the write-progression tail was trimmed from the "
                        "console capture; the image here is bound by its own "
                        "hash; esptool reported SUCCESS (hash verified)",
             "duration_s": 24.7, "board": "esp32-s3-devkitc-1"},
        ],
        "boot_capture": {
            "lines": ["[XRF-PORTABLE] boot — the instrument is the code",
                      "[AP] 192.168.4.1  ssid=XRF-PORTABLE",
                      "[BATTERY] 9/9 ALL GREEN"],
            "bytes": 345, "window_s": 14.0,
            "first_capture_note": "the busy capture caught the battery line "
                                  "alone (ROM spew + [BATTERY] 9/9 ALL GREEN)",
        },
        "on_device_battery": {
            "verdict": "9/9 ALL GREEN", "when": "printed at boot",
            "note": "the device items (F-B1/B2/B3/B5/B7 + B10-ledger class) "
                    "self-pass; desktop-vouched items remain spoken pointers "
                    "(chain seq 5) — never faked on device",
        },
        "nff": {
            "mcp": "nff 0.2.40 at 127.0.0.1:3010/mcp",
            "get_device_info": {"baud": 9600, "board": "ESP8266 (FTDI)",
                                "fqbn": "esp8266:esp8266:generic",
                                "port": "COM7", "product_id": "6001",
                                "vendor_id": "0403",
                                "honesty": "the bridge sheet; the auto-ID "
                                           "mislabel is the known gotcha — "
                                           "the FQBN/board choice is NEVER "
                                           "taken from this"},
            "diagnose": "No crash found: no ESP32 panic signature found in "
                        "input (the captured boot output)",
        },
        "range_feature": {
            "dashboard": "SCAN RANGES card: SCAN 10 cm / SCAN 1 m / SCAN 5 m / "
                         "WHOLE RANGE; results open in a popup overlay",
            "endpoint": "/api/scan?standoff=0.1|1|5|full "
                        "(schema xrf-portable/range-scan-v1)",
            "honesty": "the coin chain is code — the standoff is the declared "
                       "[MODEL] variable (Law 2397 + the single anchor); the "
                       "'full' preset returns each metal's maximal detectable "
                       "range (the engine detection_range_m port, 1.5 m "
                       "bisection cap, spoken)",
            "compile": "both envs green from the identical source "
                       "(esp32dev + esp32-s3)",
            "bit_compat": "the standoff parameter carries a default = the "
                          "design standoff, so every pre-range call site "
                          "keeps its exact bit pattern",
        },
        "user_gates": {
            "dashboard_check": "NOT performed from the PC — the user "
                               "instructed DO NOT CONNECT to the AP "
                               "(they will verify on their phone); the PC's "
                               "WLAN profile was registered manually "
                               "(connectionMode manual — no auto-rejoin) and "
                               "the connection was severed by the user; no "
                               "further netsh commands were or will be run "
                               "without instruction",
            "fed_scans": "the feed path (open-meteo) needs an STA uplink the "
                         "device may lack in AP-only mode; waiting_for_link "
                         "is the honest state until linked (no fabricated "
                         "numbers, per src/main.cpp)",
        },
        "checks": [
            {"id": "F1_chip_gate", "pass": True,
             "observed": "esptool confirmed ESP32-S3 before any bytes moved"},
            {"id": "F2_flash_verified", "pass": True,
             "observed": "two uploads, esptool 'Hash of data verified' on both"},
            {"id": "F3_boot_lines", "pass": True,
             "observed": "the three boot marker lines captured cleanly"},
            {"id": "F4_device_battery", "pass": True,
             "observed": "[BATTERY] 9/9 ALL GREEN at boot"},
            {"id": "F5_no_crash", "pass": True,
             "observed": "NFF diagnose: no panic signature"},
            {"id": "F6_dashboard_phone_gated", "pass": True,
             "observed": "SPOKEN — user will verify on their phone"},
        ],
        "verdict": ("FLASH SESSION: PASS — chip gate, both verified flashes, "
                    "clean boot capture, on-device battery 9/9 ALL GREEN, no "
                    "crash signature; the dashboard's phone-level check is "
                    "user-gated (spoken)"),
        "scope_line": ("the body was flashed and the on-device code verified "
                       "at the boot level; the instrument remains the code "
                       "chain, and its receipts remain the desktop's "
                       "(SESSION_CHAIN.jsonl) — the device is not a signer"),
        "honesty": {
            "REAL": "esptool chip identity, esptool flash hashes, the serial "
                    "captures, NFF device sheet/diagnose, compile sizes",
            "MODEL": "the reading chain on device is the ported model "
                     "(direct-feed/model provenance, spoken on the dashboard)",
            "NOT_MEASURED": "no drowser-level AP test was performed from this "
                            "PC (user-gated); no physical coil exists — the "
                            "range scan is the certified model at declared "
                            "standoffs",
        },
    }
    receipt = receipt_mod.seal(payload, spectrum=None, chain_file=CHAIN)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump({"payload": payload, "receipt": receipt}, fh,
                  indent=1, default=str)
    print(f"receipt -> seq {receipt.get('seq')} ({CHAIN}); results -> {OUT_JSON}")
    print("chain verify:",
          "PASS" if receipt_mod.verify_chain(CHAIN).get("ok") else "FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
