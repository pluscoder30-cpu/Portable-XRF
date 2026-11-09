SPOKEN ABSENCES - this folder, never silent.

1. THE WIFI SNIFFER CAPTURE (the radio-ear fixture).
   Expected relative path (two levels above sniffer/session.py):
   phi-field-native-transformer\field_computer\server\field_wifi_sniffer\captures\air_60s.txt
   In the live tree resolved to: C:\Users\delta\brain\v6\research\32_PHI_PHYSICS\phi-field-native-transformer\field_computer\server\field_wifi_sniffer\captures\air_60s.txt
   In this release copy it resolves under RELEASE/ (the code's own
   grandparent convention) - place a capture there to run all three tests.
   Status: deliberately NOT in the release - it is 60 seconds of raw RF
   frames from the operator's own air; it can carry other broadcasters'
   traffic. Its sealed witness forms ARE here: every READS/ receipt binds
   it by SHA-256 and carries only the channel tokens (4,086 frames,
   2 channels, 1,620,552 bytes, sha256 prefix d4c42216...).
   Effect (spoken, measurable): with the capture absent, the suite in this
   copy reports 244 passed + 3 SKIPPED (the three witness tests in
   sniffer/tests/test_session.py skip with 'wifi sniffer capture not
   present on this machine'); on the operator's tree the full suite
   reports 247 passed, 0 skipped. The skip is the honest absence declared
   by the code itself, not a failure.
   The accepted capture format is the sniffer's own: text lines starting
   with 'F <channel tokens...>'; the witness seals channel tokens only.
