BUILT FIRMWARE - flash-ready artifacts, both PlatformIO environments.

Built from: xrf_portable source in this release (platformio.ini envs esp32dev
and esp32-s3; lib_deps empty - no external libraries; the reading chain is
self-contained). Source files: src\battery.cpp, src\main.cpp, src\scan.cpp
Rebuild: `pio run` from xrf_portable/ (nothing is flashed without the operator).

Per environment: bootloader.bin + partitions.bin + firmware.bin.
NOT staged (spoken, never silent): the .elf, .map and every intermediate
object/cached build file - toolchain artifacts, staying only in the live
tree's .pio/build/; the staged bins are the deliverable.
