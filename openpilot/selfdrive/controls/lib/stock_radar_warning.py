"""
Fork feature (MG HS/ZS): warn when the stock radar ACC misses a lead that openpilot's camera sees.

On these cars the stock radar ACC controls the speed. Now and then its radar doesn't track a lead the camera sees:
- HS route 23: a car slowing to ~10 km/h, from 63 m down to 33 m at 39 km/h; the radar's lead flag stayed 0 and the
  ACC asked for no braking until the driver braked. -> "BRAKE!" (missed): closing in, more braking needed than the
  ACC is doing.
- HS route 26: a motorcycle 25-35 m ahead at the same ~30 km/h; the radar lost it in a turn and the ACC started
  accelerating at +1 m/s^2 towards it, the driver braked. Not closing in yet, so no "BRAKE!" (that would have come
  ~6 s later) -> a lighter prompt (lost): the ACC accelerates with a lead close ahead that its radar doesn't track.
- HS route 3e: a car slowing to ~5 km/h, from 80 m down to 25 m at 34 km/h; the camera's lead speed jumped between
  4 and 32 km/h from frame to frame, so the closing-in check never held for T_START and the driver braked first. The
  missed check uses the lowest lead speed of the last V_LEAD_WINDOW, which warned 1.2 s before the driver braked
  (no extra warnings in 15 routes, ~92 min engaged; the only other new one, ZS route 6, was 0.7 s before the driver
  braked too).
Lowering the set speed (lead_speed.py) can't go under 30 km/h and can't stop the car, so this tells the driver. The
car port reports whether the radar tracks a lead (CarState.stockRadarLead) and the ACC's acceleration request
(CarState.stockAccelRequest); the MG ZS doesn't report the request (NaN), so there the car's measured acceleration
stands in for it.
"""
import math
from collections import deque

from openpilot.common.realtime import DT_CTRL

# missed: brake now
TTC_MAX = 5.0  # s, closing in on the lead within this time at the current speeds
STOP_MARGIN = 4.0  # m to stay behind the lead
A_MARGIN = 0.5  # m/s^2, braking needed beyond what the ACC asks for
MIN_CLOSING_SPEED = 1.0  # m/s
MIN_SPEED = 3.0  # m/s
T_START = 0.2  # s the situation has to last before warning (single noisy frames)
T_HOLD = 1.0  # s to keep warning after it ends, so it doesn't flicker
RADAR_WARNING_LINGER = 5.0  # s selfdrived keeps them on screen after they end ("BRAKE!" as a silent note)
V_LEAD_WINDOW = 1.0  # s, the camera's lead speed is noisy: closing in uses its lowest value over this time

# lost: be ready to brake
LOST_GAP = 5.0  # s, the lead is within this time gap (route 26's motorcycle: 22-35 m at 29 km/h, so 4 s flickered)
LOST_ACCEL = 0.3  # m/s^2, the ACC accelerates at least this much
LOST_PULLING_AWAY = 2.0  # m/s, not when the lead drives away faster than this
LOST_MAX_DIST = 40.0  # m: farther leads are often dropped by the radar for a moment while keeping their speed
LOST_T_START = 0.5  # s


def needs_braking(v_ego: float, d_rel: float, v_lead: float, accel_request: float) -> bool:
  closing = v_ego - v_lead
  if v_ego < MIN_SPEED or closing < MIN_CLOSING_SPEED:
    return False
  ttc = d_rel / closing
  # constant deceleration to come down to the lead's speed STOP_MARGIN behind it
  a_needed = closing ** 2 / (2 * max(d_rel - STOP_MARGIN, 0.5))
  return ttc < TTC_MAX and a_needed > max(-accel_request, 0.0) + A_MARGIN


def accelerating_towards(v_ego: float, d_rel: float, v_lead: float, accel: float) -> bool:
  return (v_ego > MIN_SPEED and d_rel < min(LOST_GAP * v_ego, LOST_MAX_DIST) and v_lead < v_ego + LOST_PULLING_AWAY and
          accel > LOST_ACCEL)


class Debounce:
  def __init__(self, t_start: float, t_hold: float):
    self.start = round(t_start / DT_CTRL)
    self.hold = round(t_hold / DT_CTRL)
    self.start_frames = 0
    self.hold_frames = 0

  def reset(self):
    self.start_frames = 0
    self.hold_frames = 0

  def update(self, cond: bool) -> bool:
    if cond:
      self.start_frames += 1
      if self.start_frames >= self.start:
        self.hold_frames = self.hold
    else:
      self.start_frames = 0
      self.hold_frames = max(self.hold_frames - 1, 0)
    return self.hold_frames > 0


class StockRadarWarning:
  def __init__(self):
    self.missed = Debounce(T_START, T_HOLD)
    self.lost = Debounce(LOST_T_START, T_HOLD)
    self.v_leads: deque[float] = deque(maxlen=round(V_LEAD_WINDOW / DT_CTRL))

  def update(self, CS, lead) -> tuple[bool, bool]:
    """Every control frame (100 Hz): (warn the driver to brake, prompt that the radar lost the lead)."""
    if lead.present:
      self.v_leads.append(lead.vLead)
    else:
      self.v_leads.clear()

    if not CS.stockRadarValid or not CS.cruiseState.enabled or CS.brakePressed:
      self.missed.reset()
      self.lost.reset()
      return False, False

    accel = CS.stockAccelRequest if math.isfinite(CS.stockAccelRequest) else CS.aEgo
    untracked = lead.present and not CS.stockRadarLead
    missed = self.missed.update(untracked and needs_braking(CS.vEgo, lead.dRel, min(self.v_leads, default=lead.vLead), accel))
    lost = self.lost.update(untracked and accelerating_towards(CS.vEgo, lead.dRel, lead.vLead, accel))
    return missed, lost and not missed
