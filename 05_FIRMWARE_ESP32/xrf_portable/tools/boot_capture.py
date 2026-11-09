"""boot_capture.py — a clean boot-scope capture over the serial bridge.

Toggles the auto-reset (RTS -> EN) so the instrument's boot prints are inside
the capture window, reads at 115200, writes both the raw bytes and the decoded
text, and prints the firmware's own marker lines.

Usage:
  python tools/boot_capture.py [--port COM7] [--baud 115200] [--seconds 12]
"""
import argparse
import sys
import time

import serial


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM7")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--raw", default="nff_boot_capture.bin")
    ap.add_argument("--text", default="nff_boot_capture.txt")
    args = ap.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=1)
    # auto-reset: RTS low asserts EN through the devkit's transistor pair;
    # DTR low keeps GPIO0 high -> after RTS releases, the app boots.
    ser.rts = True
    ser.dtr = False
    time.sleep(0.15)
    ser.rts = False
    ser.reset_input_buffer()

    chunks = []
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        data = ser.read(4096)
        chunks.append(data)
    ser.close()
    raw = b"".join(chunks)
    with open(args.raw, "wb") as fh:
        fh.write(raw)
    text = raw.decode("utf-8", "replace").replace("\r", "\n")
    with open(args.text, "w", encoding="utf-8") as fh:
        fh.write(text)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    markers = [l for l in lines if "]" in l or "waiting" in l
               or "192.168" in l or "192.168.4.1" in l]
    print(f"captured {len(raw)} bytes in {args.seconds:.0f} s "
          f"({len(lines)} printable lines) — raw -> {args.raw}, "
          f"text -> {args.text}")
    seen = 0
    for line in markers:
        if seen < 40:
            print("  |", line[:160])
            seen += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
