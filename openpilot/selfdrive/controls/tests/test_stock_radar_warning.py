from types import SimpleNamespace

from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.stock_radar_warning import LOST_T_START, T_HOLD, T_START, StockRadarWarning, \
                                                                    needs_braking


def car_state(v=10.8, radar_lead=False, accel_request=0.0, cruise=True, brake=False, valid=True, a_ego=0.0):
  return SimpleNamespace(stockRadarValid=valid, stockRadarLead=radar_lead, stockAccelRequest=accel_request, vEgo=v,
                         aEgo=a_ego, brakePressed=brake, cruiseState=SimpleNamespace(enabled=cruise))


def lead(d=38.0, v=2.8, present=True):
  return SimpleNamespace(present=present, dRel=d, vLead=v)


def run_both(w, cs, ld, seconds=0.5):
  out = (False, False)
  for _ in range(round(seconds / DT_CTRL)):
    out = w.update(cs, ld)
  return out


def run(w, cs, ld, seconds=0.5):
  """the "BRAKE!" warning"""
  return run_both(w, cs, ld, seconds)[0]


def lost(w, cs, ld, seconds=1.0):
  """the "radar lost the car ahead" prompt"""
  return run_both(w, cs, ld, seconds)[1]


class TestStockRadarWarning:
  def test_route_23(self):
    # HS route 23: 39 km/h, a car slowing to 10 km/h 38 m ahead, the radar doesn't track it, the ACC isn't braking
    assert run(StockRadarWarning(), car_state(), lead())

  def test_not_when_the_radar_sees_it(self):
    assert not run(StockRadarWarning(), car_state(radar_lead=True), lead())

  def test_not_when_the_acc_brakes_enough(self):
    assert not run(StockRadarWarning(), car_state(accel_request=-2.0), lead())

  def test_measured_accel_without_a_request(self):
    # MG ZS: no ACC request (NaN), the car's own deceleration counts instead
    nan = float('nan')
    assert run(StockRadarWarning(), car_state(accel_request=nan, a_ego=-0.1), lead())
    assert not run(StockRadarWarning(), car_state(accel_request=nan, a_ego=-2.0), lead())

  def test_not_far_away_or_not_closing(self):
    assert not needs_braking(10.8, 80.0, 2.8, 0.0)  # 10 s away
    assert not needs_braking(10.8, 20.0, 10.5, 0.0)  # following at the same speed
    assert not needs_braking(10.8, 15.0, 12.0, 0.0)  # pulling away

  def test_not_without_a_lead_or_cruise(self):
    assert not run(StockRadarWarning(), car_state(), lead(present=False))
    assert not run(StockRadarWarning(), car_state(cruise=False), lead())
    assert not run(StockRadarWarning(), car_state(valid=False), lead())  # other cars

  def test_stops_when_the_driver_brakes(self):
    w = StockRadarWarning()
    assert run(w, car_state(), lead())
    assert not any(w.update(car_state(brake=True), lead()))

  def test_debounce_and_hold(self):
    w = StockRadarWarning()
    # a single frame doesn't warn
    assert not run(w, car_state(), lead(), seconds=T_START / 2)
    assert run(w, car_state(), lead(), seconds=T_START)
    # once it ends: keeps warning a moment, then stops
    assert run(w, car_state(radar_lead=True), lead(), seconds=T_HOLD / 2)
    assert not run(w, car_state(radar_lead=True), lead(), seconds=T_HOLD)

  def test_lost_motorcycle(self):
    # HS route 26: a motorcycle ~25-35 m ahead at the same ~30 km/h, the radar lost it in a turn and the ACC
    # accelerated at +1 m/s^2: not closing in yet (no "BRAKE!"), but be ready
    w = StockRadarWarning()
    cs, ld = car_state(v=8.1, accel_request=0.8), lead(d=30.0, v=8.1)
    assert lost(w, cs, ld)
    assert not run(StockRadarWarning(), cs, ld)

  def test_lost_needs_the_acc_to_accelerate(self):
    assert not lost(StockRadarWarning(), car_state(v=8.1, accel_request=0.1), lead(d=30.0, v=8.1))
    # MG ZS: measured acceleration
    nan = float('nan')
    assert lost(StockRadarWarning(), car_state(v=8.1, accel_request=nan, a_ego=0.8), lead(d=30.0, v=8.1))

  def test_lost_not_far_tracked_or_pulling_away(self):
    assert not lost(StockRadarWarning(), car_state(v=8.1, accel_request=0.8), lead(d=60.0, v=8.1))  # 7 s gap
    # HS route 2a: a lead ~65-70 m ahead at the same ~57 km/h, dropped by the radar for a moment: not worth a prompt
    assert not lost(StockRadarWarning(), car_state(v=15.8, accel_request=0.7), lead(d=68.0, v=15.8))
    assert not lost(StockRadarWarning(), car_state(v=8.1, accel_request=0.8, radar_lead=True), lead(d=30.0, v=8.1))
    assert not lost(StockRadarWarning(), car_state(v=8.1, accel_request=0.8), lead(d=30.0, v=11.0))

  def test_lost_debounce(self):
    w = StockRadarWarning()
    cs, ld = car_state(v=8.1, accel_request=0.8), lead(d=30.0, v=8.1)
    assert not lost(w, cs, ld, seconds=LOST_T_START / 2)
    assert lost(w, cs, ld, seconds=LOST_T_START)

  def test_brake_warning_wins(self):
    # closing in fast while the ACC still accelerates: only "BRAKE!"
    w = StockRadarWarning()
    assert run_both(w, car_state(v=10.8, accel_request=0.5), lead(d=20.0, v=2.8), seconds=1.0) == (True, False)
