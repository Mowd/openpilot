"""
Fork feature (MG ZS): retry the fingerprint when no car matched.

MG cars are only recognized by the FW versions of three ECUs (EPS, camera, radar), all of them essential for the
exact match and all excluded from the fuzzy match, and they have no CAN fingerprint. When one of them misses the
query, the car comes up unrecognized (dashcam mode) for the whole drive: the friend's MG ZS hit it a few times,
likely when the engine is cranked while openpilot is already querying (the voltage dip restarts ECUs; the MG HS PHEV
has no starter and never hit it). Query again a couple of times before giving up; pandad waits for
FirmwareQueryDone, so it is safe to take a few seconds longer.
"""
import time

from opendbc.car.carlog import carlog

FINGERPRINT_RETRIES = 2
FINGERPRINT_RETRY_DELAY = 2.  # s


def get_car_with_retries(get_car_fn, retries: int = FINGERPRINT_RETRIES, delay: float = FINGERPRINT_RETRY_DELAY,
                         sleep=time.sleep):
  CI = get_car_fn()
  for attempt in range(retries):
    if CI.CP.brand != "mock":
      break
    carlog.error({"event": "fingerprint retry", "attempt": attempt + 1,
                  "car_fw": [(str(fw.ecu), fw.address) for fw in CI.CP.carFw]})
    sleep(delay)
    CI = get_car_fn()
  return CI
