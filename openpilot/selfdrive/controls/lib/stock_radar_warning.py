"""
Fork feature (MG HS): warn when the stock radar ACC misses a lead that openpilot's camera sees closing in.

On these cars the stock radar ACC controls the speed. Now and then its radar doesn't track a slower lead the camera
sees (HS route 23: a car slowing to ~10 km/h, from 63 m down to 33 m at 39 km/h, the radar's lead flag stayed 0 and
the ACC asked for no braking until the driver braked). Lowering the set speed (lead_speed.py) can't go under 30 km/h
and can't stop the car, so this tells the driver to brake: the car port reports whether the radar tracks a lead
(CarState.stockRadarLead) and how much the ACC asks to brake (CarState.stockAccelRequest).
"""
from openpilot.common.realtime import DT_CTRL

TTC_MAX = 5.0  # s, closing in on the lead within this time at the current speeds
STOP_MARGIN = 4.0  # m to stay behind the lead
A_MARGIN = 0.5  # m/s^2, braking needed beyond what the ACC asks for
MIN_CLOSING_SPEED = 1.0  # m/s
MIN_SPEED = 3.0  # m/s
T_START = 0.2  # s the situation has to last before warning (single noisy frames)
T_HOLD = 1.0  # s to keep warning after it ends, so it doesn't flicker


def needs_braking(v_ego: float, d_rel: float, v_lead: float, accel_request: float) -> bool:
  closing = v_ego - v_lead
  if v_ego < MIN_SPEED or closing < MIN_CLOSING_SPEED:
    return False
  ttc = d_rel / closing
  # constant deceleration to come down to the lead's speed STOP_MARGIN behind it
  a_needed = closing ** 2 / (2 * max(d_rel - STOP_MARGIN, 0.5))
  return ttc < TTC_MAX and a_needed > max(-accel_request, 0.0) + A_MARGIN


class StockRadarWarning:
  def __init__(self):
    self.start_frames = 0
    self.hold_frames = 0

  def update(self, CS, lead) -> bool:
    """Every control frame (100 Hz): whether to warn the driver to brake."""
    if not CS.stockRadarValid or not CS.cruiseState.enabled or CS.brakePressed:
      self.start_frames = 0
      self.hold_frames = 0
      return False

    missed = (lead.present and not CS.stockRadarLead and
              needs_braking(CS.vEgo, lead.dRel, lead.vLead, CS.stockAccelRequest))
    if missed:
      self.start_frames += 1
      if self.start_frames * DT_CTRL >= T_START:
        self.hold_frames = round(T_HOLD / DT_CTRL)
    else:
      self.start_frames = 0
      self.hold_frames = max(self.hold_frames - 1, 0)
    return self.hold_frames > 0
