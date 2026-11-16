from types import SimpleNamespace

from openpilot.cereal import log
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.desire_helper import LANE_CHANGE_START_TIME, DesireHelper

LaneChangeState = log.LaneChangeState


def car_state(right_blinker=True, torque=-1.5, v=20.0):
  # on the HS the hands on the wheel alone give 1-2 Nm (negative: towards the right)
  return SimpleNamespace(vEgo=v, leftBlinker=False, rightBlinker=right_blinker, steeringPressed=abs(torque) > 1.0,
                         steeringTorque=torque, leftBlindspot=False, rightBlindspot=False)


def run(dh, cs, lane_change_prob, seconds):
  for _ in range(round(seconds / DT_MDL)):
    dh.update(cs, True, lane_change_prob)
  return dh.lane_change_state


class TestDesireHelper:
  def test_lane_change(self):
    dh = DesireHelper()
    assert run(dh, car_state(), 0.0, DT_MDL) == LaneChangeState.preLaneChange
    assert run(dh, car_state(), 1.0, 2.0) == LaneChangeState.laneChangeStarting
    assert dh.desire == log.Desire.laneChangeRight
    assert run(dh, car_state(), 0.0, 1.0) == LaneChangeState.off
    assert dh.desire == log.Desire.none

  def test_one_lane_change_per_blinker(self):
    # route 2b: done while the stalk was still held, the resting torque started a second one right away
    dh = DesireHelper()
    run(dh, car_state(), 1.0, 3.0)
    assert run(dh, car_state(), 0.0, 3.0) == LaneChangeState.off
    assert dh.desire == log.Desire.none
    # blinker off and on again: the next lane change
    run(dh, car_state(right_blinker=False), 0.0, 0.5)
    assert run(dh, car_state(), 1.0, 0.5) == LaneChangeState.laneChangeStarting

  def test_keeps_going_until_the_model_is_done(self):
    # releasing the stalk during the lane change doesn't stop it
    dh = DesireHelper()
    run(dh, car_state(), 1.0, 1.0)
    assert run(dh, car_state(right_blinker=False), 0.5, 2.0) == LaneChangeState.laneChangeStarting
    assert run(dh, car_state(right_blinker=False), 0.0, LANE_CHANGE_START_TIME) == LaneChangeState.off

  def test_waits_for_a_nudge(self):
    dh = DesireHelper()
    assert run(dh, car_state(torque=-0.5), 0.0, 2.0) == LaneChangeState.preLaneChange
    assert run(dh, car_state(torque=1.5), 0.0, 1.0) == LaneChangeState.preLaneChange  # the other way
