"""
Fork feature (MG HS/ZS): move off from a standstill behind a lead that is moving off, as a driver in a queue does.

In Standstill Wait the MG stock ACC only moves off after RES, which the car port sends once openpilot asks to resume
(CarControl.cruiseControl.resume) and the radar's own "lead has left" prompt is on. openpilot asks to resume when its
planner no longer wants to stop, but in a queue the lead often creeps off at 1-3 km/h and the planner keeps wanting to
stop until it is far ahead: HS route 3e, the lead crept from 4 to 10 m in 6 s, the radar's prompt was on for 5 s and
the driver had to press RES, leaving a gap. So also resume while the model sees the lead moving off; the stock ACC
still follows it and stops again behind it if it stops.
"""
from openpilot.common.realtime import DT_MDL

MIN_PROB = 0.5  # the model's lead probability
MIN_SPEED = 0.3  # m/s (1.1 km/h), a stopped lead reads 0-0.15 m/s
T_MOVING = 0.5  # s the lead has to keep moving


class LeadMovingOff:
  def __init__(self):
    self.frames = 0

  def update(self, model, model_updated: bool) -> bool:
    if model_updated:
      leads = model.leadsV3
      moving = len(leads) > 0 and leads[0].prob > MIN_PROB and leads[0].v[0] > MIN_SPEED
      self.frames = self.frames + 1 if moving else 0
    return self.frames >= round(T_MOVING / DT_MDL)
