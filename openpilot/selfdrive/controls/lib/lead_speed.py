"""
Fork feature: start slowing down early for a slower lead on cars where the stock ACC controls the speed (MG HS/ZS).

The MG stock ACC often keeps its speed until it is close to a slower or stopping lead and then brakes hard, even when
its radar already tracks it. openpilot's model sees the lead slowing down several seconds earlier
(modelV2.action.desiredAcceleration; it doesn't know the ACC set speed, so lowering the set speed can't feed back
into it). While it wants to slow down for a lead, this asks for a set speed a few seconds of that deceleration below
the current speed; the car port lowers the stock ACC set speed (CarControl.cruiseControl.speedTarget) with the
cruise switches and restores the driver's speed as soon as the model no longer wants to slow down (if the lead is
still slower, the stock ACC follows it anyway).
"""
import math

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL

A_START = -0.5  # m/s^2, the model wants at least this much braking for a lead: start
A_KEEP = -0.2  # m/s^2, keep going while it still wants this much
T_AHEAD = 4.0  # s, target = current speed + wanted acceleration over this time
ACCEL_RC = 0.5  # s, smoothing of the model's wanted acceleration
RELEASE_DELAY = 1.5  # s to hold the last target after it stops slowing: the wanted braking flickers around A_START


class LeadSpeed:
  def __init__(self):
    self.accel = FirstOrderFilter(0.0, ACCEL_RC, DT_MDL)
    self.slowing = False
    self.target = math.inf
    self.release_frames = 0

  def reset(self):
    self.accel.x = 0.0
    self.slowing = False
    self.target = math.inf
    self.release_frames = 0

  def update(self, active: bool, v_ego: float, model, has_lead: bool, model_updated: bool) -> float:
    """CarControl.cruiseControl.speedTarget (m/s), 0 = no target."""
    if not active:
      self.reset()
      return 0.0

    if model_updated:
      a = self.accel.update(model.action.desiredAcceleration)
      self.slowing = has_lead and a < (A_KEEP if self.slowing else A_START)
      # follows the wanted braking both ways while slowing, and lets go shortly after: a slow release held the
      # set speed down for ~10 s after the lead had gone, while the model already wanted to speed up
      if self.slowing:
        self.target = max(v_ego + a * T_AHEAD, 0.0)
        self.release_frames = round(RELEASE_DELAY / DT_MDL)
      elif self.release_frames > 0:
        self.release_frames -= 1
      else:
        self.target = math.inf
    return float(self.target) if math.isfinite(self.target) else 0.0
