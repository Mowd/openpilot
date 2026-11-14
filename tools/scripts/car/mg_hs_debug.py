#!/usr/bin/env python3
"""MG HS debug helper, run on the device while the car is on (openpilot running).

1. prints the ECU firmware versions openpilot read at startup (for fingerprints.py)
2. finds which CAN bits follow the left/right turn signal

usage: python3 tools/scripts/car/mg_hs_debug.py
"""
import time
from collections import defaultdict

import openpilot.cereal.messaging as messaging
from openpilot.cereal import car
from openpilot.common.params import Params

PHASE_SECONDS = 8

# GW_HSC2_BCM_FrP04 (0x46a) signals already in the DBC: name -> (byte, bit)
BCM_ADDR = 0x46a
BCM_CANDIDATES = {
  "DircnIndLampSwStsHSC2==1 (left)": (0, 2),
  "DircnIndLampSwStsHSC2==2 (right)": (0, 3),
  "BlinkerLeft": (7, 3),
  "BlinkerRight": (7, 4),
  "BlinkerBulbLeft": (4, 5),
  "BlinkerBulbRight": (4, 6),
  "LDircnIOHSC2": (1, 3),
  "RDircnIOHSC2": (1, 1),
  "LDircnIndLghtFHSC2": (1, 2),
  "RDircnIndLghtFHSC2": (6, 0),
}


def print_fw_versions():
  print("=== ECU firmware versions ===")
  cp_bytes = Params().get("CarParams")
  if not cp_bytes:
    print("no CarParams yet: turn the car on and wait for openpilot to start")
    return
  with car.CarParams.from_bytes(cp_bytes) as cp:
    print(f"fingerprint: {cp.carFingerprint}  source: {cp.fingerprintSource}  VIN: {cp.carVin}")
    if len(cp.carFw) == 0:
      print("no ECU answered the firmware query")
    for fw in cp.carFw:
      print(f"  bus {fw.bus}  {fw.ecu}  {hex(fw.address)}  sub {fw.subAddress}  {fw.fwVersion!r}  ({fw.brand})")
  print()


def record(sock, seconds):
  """Returns {(bus, addr): (samples, [count of 1s per bit])}."""
  stats = defaultdict(lambda: [0, [0] * 64])
  messaging.drain_sock_raw(sock)
  end = time.monotonic() + seconds
  while time.monotonic() < end:
    for evt in messaging.drain_sock(sock, wait_for_one=True):
      for c in evt.can:
        if c.src >= 128:  # skip sent/rejected echoes
          continue
        s = stats[(c.src, c.address)]
        s[0] += 1
        for i, byte in enumerate(c.dat[:8]):
          for b in range(8):
            if byte >> b & 1:
              s[1][i * 8 + b] += 1
  return stats


def frac(stats, key, bit):
  n, ones = stats.get(key, (0, None))
  return ones[bit] / n if n else None


def changed_bits(base, phase):
  out = set()
  for key, (n, ones) in phase.items():
    if n < 5 or key not in base or base[key][0] < 5:
      continue
    for bit in range(64):
      f0 = base[key][1][bit] / base[key][0]
      f1 = ones[bit] / n
      if (f0 <= 0.02 and f1 >= 0.2) or (f0 >= 0.98 and f1 <= 0.8):
        out.add((key[0], key[1], bit))
  return out


def main():
  print_fw_versions()

  sock = messaging.sub_sock("can", timeout=100)
  phases = [
    ("off", "turn signals OFF, hazards OFF"),
    ("left", "turn on the LEFT turn signal and keep it on"),
    ("right", "turn on the RIGHT turn signal and keep it on"),
  ]
  results = {}
  for name, instruction in phases:
    input(f"--> {instruction}, then press Enter (records {PHASE_SECONDS} s)")
    results[name] = record(sock, PHASE_SECONDS)
    print(f"    recorded {sum(v[0] for v in results[name].values())} CAN frames")
    if not results[name]:
      print("no CAN received: is the car on and openpilot running?")
      return

  print("\n=== known 0x46a candidates: fraction of time the bit was 1 ===")
  print(f"{'signal':36s} {'bus':>3s}  {'off':>5s} {'left':>5s} {'right':>5s}")
  buses = sorted({bus for bus, addr in results["off"] if addr == BCM_ADDR})
  if not buses:
    print("0x46a not seen on any bus")
  for bus in buses:
    for sig, (byte, bit) in BCM_CANDIDATES.items():
      vals = [frac(results[p], (bus, BCM_ADDR), byte * 8 + bit) for p in ("off", "left", "right")]
      print(f"{sig:36s} {bus:3d}  " + " ".join(f"{v:5.2f}" if v is not None else "  -  " for v in vals))

  left = changed_bits(results["off"], results["left"])
  right = changed_bits(results["off"], results["right"])
  print("\n=== every bit that follows a turn signal (all messages) ===")
  if not (left | right):
    print("none found")
  for bus, addr, bit in sorted(left | right, key=lambda x: (x[1], x[0], x[2])):
    side = "left+right" if (bus, addr, bit) in left and (bus, addr, bit) in right else ("LEFT" if (bus, addr, bit) in left else "RIGHT")
    vals = [frac(results[p], (bus, addr), bit) for p in ("off", "left", "right")]
    print(f"  {side:10s} bus {bus}  {hex(addr):6s} byte {bit // 8} bit {bit % 8}  " +
          "off/left/right = " + "/".join(f"{v:.2f}" if v is not None else "-" for v in vals))


if __name__ == "__main__":
  main()
