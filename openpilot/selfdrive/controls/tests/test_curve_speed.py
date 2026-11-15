import math
from types import SimpleNamespace

import numpy as np

from openpilot.selfdrive.controls.lib.curve_speed import A_DECEL, A_LAT_MAX, CurveSpeed, curve_speed

T = np.linspace(0, 10, 33)


def model(v, yaw_rate):
  """A constant speed path; yaw_rate per point (rad/s)."""
  yaw_rate = np.broadcast_to(np.asarray(yaw_rate, dtype=float), T.shape)
  return SimpleNamespace(position=SimpleNamespace(t=T.tolist(), x=(v * T).tolist()),
                         velocity=SimpleNamespace(x=[v] * len(T)),
                         orientationRate=SimpleNamespace(z=yaw_rate.tolist()))


class TestCurveSpeed:
  def test_straight_is_fast(self):
    assert curve_speed(model(25.0, 0.0)) > 100

  def test_curve_now(self):
    # 100 m radius right now: sqrt(2.0 * 100) ~ 14.1 m/s
    v = 20.0
    target = curve_speed(model(v, v / 100.0))
    assert math.isclose(target, math.sqrt(A_LAT_MAX * 100.0), rel_tol=1e-3)

  def test_curve_ahead_allows_braking_distance(self):
    v = 20.0
    yaw = np.where(T >= 5.0, v / 100.0, 0.0)  # straight for 5 s, then the curve
    dist = v * T[np.argmax(T >= 5.0)]
    expected = math.sqrt(A_LAT_MAX * 100.0 + 2 * A_DECEL * dist)
    assert math.isclose(curve_speed(model(v, yaw)), expected, rel_tol=1e-3)
    assert curve_speed(model(v, yaw)) > curve_speed(model(v, v / 100.0))

  def test_bad_model(self):
    empty = SimpleNamespace(position=SimpleNamespace(t=[], x=[]), velocity=SimpleNamespace(x=[]),
                            orientationRate=SimpleNamespace(z=[]))
    assert curve_speed(empty) == math.inf

  def test_inactive_is_zero(self):
    cs = CurveSpeed()
    assert cs.update(False, model(20.0, 0.2), True) == 0.0

  def test_drops_fast_rises_slow(self):
    cs = CurveSpeed()
    curve, straight = model(20.0, 0.2), model(20.0, 0.0)
    low = cs.update(True, curve, True)
    assert math.isclose(low, math.sqrt(A_LAT_MAX * 100.0), rel_tol=1e-3)
    # one model frame later on a straight: only up by RISE_RATE * DT_MDL
    assert cs.update(True, straight, True) < low + 0.1
    # no new model frame: unchanged
    assert cs.update(True, straight, False) == cs.target
