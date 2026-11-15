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

A_LAT_MAX = 2.0  # m/s^2, lateral acceleration allowed in a curve
A_DECEL = 1.0  # m/s^2, gentle braking expected from the stock ACC once its set speed drops
# s from the first tap until the stock ACC starts braking: measured on an MG ZS on-ramp, set speed 70 -> 45 km/h
# at 67 km/h, it braked ~1.5 s later (then at -1.3 to -1.5 m/s^2); without it the slowdown started inside the curve
ACC_DELAY = 1.5
T_LOOKAHEAD = 8.0  # s of the predicted path to look at
MIN_CURVATURE = 1e-4  # 1/m, straighter than this is not a curve
RISE_RATE = 1.0  # m/s per s: after a curve the target goes back up gradually, so it doesn't flicker


def curve_speed(model, acc_delay: float = ACC_DELAY) -> float:
  """Highest speed now (m/s) that can still slow down in time for every curve in the model's path."""
  t = np.asarray(model.position.t)
  if len(t) == 0 or len(model.velocity.x) != len(t) or len(model.orientationRate.z) != len(t):
    return math.inf
  dist = np.asarray(model.position.x)
  v_path = np.maximum(np.asarray(model.velocity.x), 1.0)
  curvature = np.abs(np.asarray(model.orientationRate.z)) / v_path

  sel = t <= T_LOOKAHEAD
  v_curve = np.sqrt(A_LAT_MAX / np.maximum(curvature[sel], MIN_CURVATURE))
  # the ACC keeps the current speed for acc_delay before it starts braking
  braking_dist = np.maximum(dist[sel] - v_path[0] * acc_delay, 0.0)
  v_now = np.sqrt(v_curve ** 2 + 2 * A_DECEL * braking_dist)
  return float(np.min(v_now))


class CurveSpeed:
  def __init__(self):
    self.target = math.inf

  def update(self, active: bool, model, model_updated: bool) -> float:
    """CarControl.cruiseControl.speedTarget (m/s), 0 = no target."""
    if not active:
      self.target = math.inf
      return 0.0

    if model_updated:
      new = curve_speed(model)
      # down right away, back up slowly
      self.target = min(new, self.target + RISE_RATE * DT_MDL)
    return float(self.target) if math.isfinite(self.target) else 0.0
