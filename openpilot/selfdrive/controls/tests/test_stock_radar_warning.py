from types import SimpleNamespace

from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.stock_radar_warning import T_HOLD, T_START, StockRadarWarning, needs_braking


def car_state(v=10.8, radar_lead=False, accel_request=0.0, cruise=True, brake=False, valid=True):
  return SimpleNamespace(stockRadarValid=valid, stockRadarLead=radar_lead, stockAccelRequest=accel_request, vEgo=v,
                         brakePressed=brake, cruiseState=SimpleNamespace(enabled=cruise))


def lead(d=38.0, v=2.8, present=True):
  return SimpleNamespace(present=present, dRel=d, vLead=v)


def run(w, cs, ld, seconds=0.5):
  out = False
  for _ in range(round(seconds / DT_CTRL)):
    out = w.update(cs, ld)
  return out


class TestStockRadarWarning:
  def test_route_23(self):
    # HS route 23: 39 km/h, a car slowing to 10 km/h 38 m ahead, the radar doesn't track it, the ACC isn't braking
    assert run(StockRadarWarning(), car_state(), lead())

  def test_not_when_the_radar_sees_it(self):
    assert not run(StockRadarWarning(), car_state(radar_lead=True), lead())

  def test_not_when_the_acc_brakes_enough(self):
    assert not run(StockRadarWarning(), car_state(accel_request=-2.0), lead())

  def test_not_far_away_or_not_closing(self):
    assert not needs_braking(10.8, 80.0, 2.8, 0.0)  # 10 s away
    assert not needs_braking(10.8, 20.0, 10.5, 0.0)  # following at the same speed
    assert not needs_braking(10.8, 15.0, 12.0, 0.0)  # pulling away

  def test_not_without_a_lead_or_cruise(self):
    assert not run(StockRadarWarning(), car_state(), lead(present=False))
    assert not run(StockRadarWarning(), car_state(cruise=False), lead())
    assert not run(StockRadarWarning(), car_state(valid=False), lead())  # other cars, MG ZS

  def test_stops_when_the_driver_brakes(self):
    w = StockRadarWarning()
    assert run(w, car_state(), lead())
    assert not w.update(car_state(brake=True), lead())

  def test_debounce_and_hold(self):
    w = StockRadarWarning()
    # a single frame doesn't warn
    assert not run(w, car_state(), lead(), seconds=T_START / 2)
    assert run(w, car_state(), lead(), seconds=T_START)
    # once it ends: keeps warning a moment, then stops
    assert run(w, car_state(radar_lead=True), lead(), seconds=T_HOLD / 2)
    assert not run(w, car_state(radar_lead=True), lead(), seconds=T_HOLD)
