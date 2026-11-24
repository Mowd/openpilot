"""
Fork feature: slow down for curves on cars where the stock ACC controls the speed (MG HS/ZS).

From the model's predicted path this finds the highest speed that keeps the lateral acceleration in the curves
ahead under A_LAT_MAX, allowing the stock ACC to react (ACC_DELAY) and then brake gently (A_DECEL) before each of
them. The car port lowers the stock ACC set speed to it (CarControl.cruiseControl.speedTarget) and restores the
driver's speed after.
"""
import math

import numpy as np

from openpilot.common.realtime import DT_MDL

# m/s^2, lateral acceleration allowed in a curve. 2.0 was too slow: an MG ZS on-ramp loop (R ~90 m) was held at 44-48
# km/h for ~30 s, the driver takes it at 52-56 km/h (behind a lead, ~2.6 m/s^2) and pressed the gas at 49 km/h in a
# R ~75 m curve (~2.5 m/s^2)
A_LAT_MAX = 2.5
# MG HS: 2.0. Its EPS is capped at 3 Nm and saturates well below 2.5: HS route 67 entered a R ~67 m curve in the rain at
# 48 km/h (~2.6 m/s^2), the steering saturated ("turn exceeds limit"), the driver had to help and on the exit openpilot
# swung from 3 Nm right to 3 Nm left within 0.5 s to get back to the lane center; route 60 had the same in an S-curve
# at ~38 km/h. 2.0 targets ~42 km/h there instead of ~47 and starts slowing earlier
A_LAT_MAX_CAR = {"MG_HS": 2.0}
A_DECEL = 1.0  # m/s^2, gentle braking expected from the stock ACC once its set speed drops
# s from the first tap until the stock ACC starts braking: measured on an MG ZS on-ramp, set speed 70 -> 45 km/h
# at 67 km/h, it braked ~1.5 s later (then at -1.3 to -1.5 m/s^2); without it the slowdown started inside the curve
ACC_DELAY = 1.5
T_LOOKAHEAD = 8.0  # s of the predicted path to look at
MIN_CURVATURE = 1e-4  # 1/m, straighter than this is not a curve
# m/s per s: after a curve the target goes back up gradually, so it doesn't flicker. 1.0 was too slow: after a turn
# at an intersection (HS route 2a, R 15-20 m) the curve speed was back to 62 km/h but the target needed ~11 s to
# get there, and the set speed crawled up from 30 with it (the lead had long gone)
RISE_RATE = 3.0


def curve_speed(model, acc_delay: float = ACC_DELAY, a_lat_max: float = A_LAT_MAX) -> float:
  """Highest speed now (m/s) that can still slow down in time for every curve in the model's path."""
  t = np.asarray(model.position.t)
  if len(t) == 0 or len(model.velocity.x) != len(t) or len(model.orientationRate.z) != len(t):
    return math.inf
  dist = np.asarray(model.position.x)
  v_path = np.maximum(np.asarray(model.velocity.x), 1.0)
  curvature = np.abs(np.asarray(model.orientationRate.z)) / v_path

  sel = t <= T_LOOKAHEAD
  v_curve = np.sqrt(a_lat_max / np.maximum(curvature[sel], MIN_CURVATURE))
  # the ACC keeps the current speed for acc_delay before it starts braking
  braking_dist = np.maximum(dist[sel] - v_path[0] * acc_delay, 0.0)
  v_now = np.sqrt(v_curve ** 2 + 2 * A_DECEL * braking_dist)
  return float(np.min(v_now))


class CurveSpeed:
  def __init__(self, car_fingerprint: str = ""):
    self.a_lat_max = A_LAT_MAX_CAR.get(car_fingerprint, A_LAT_MAX)
    self.target = math.inf

  def update(self, active: bool, model, model_updated: bool) -> float:
    """CarControl.cruiseControl.speedTarget (m/s), 0 = no target."""
    if not active:
      self.target = math.inf
      return 0.0

    if model_updated:
      new = curve_speed(model, a_lat_max=self.a_lat_max)
      # down right away, back up slowly
      self.target = min(new, self.target + RISE_RATE * DT_MDL)
    return float(self.target) if math.isfinite(self.target) else 0.0
