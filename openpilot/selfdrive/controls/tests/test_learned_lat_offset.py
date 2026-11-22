import math

import pytest

from openpilot.cereal import log
from opendbc.car.structs import car
from opendbc.car.car_helpers import interfaces
from opendbc.car.mg.values import CAR as MG
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.selfdrive.controls.lib.learned_lat_offset import MAX_LAT_ACCEL_OFFSET, learned_offset_torque_params


def get_CP(car_name):
  return interfaces[car_name].get_non_essential_params(car_name)


def torque_params(offset, use_params=False):
  ltp = log.LateralTorqueParameters.new_message()
  ltp.useParams = use_params
  ltp.latAccelFactorFiltered = 0.5  # learned values that must not be used
  ltp.frictionCoefficientFiltered = 0.01
  ltp.latAccelOffsetFiltered = offset
  return ltp


def straight_road_torque(CP, roll_deg, offset_params=None):
  CI = interfaces[CP.carFingerprint](CP)
  controller = LatControlTorque(CP.as_reader(), CI, DT_CTRL)
  if offset_params is not None:
    controller.update_torque_parameters(*offset_params)
  CS = car.CarState.new_message()
  CS.vEgo = 11.0  # ~40 km/h, where the MG HS sat furthest left of lane center
  params = log.VehicleParameters.new_message()
  params.roll = math.radians(roll_deg)
  torque = 0.0
  for _ in range(10):
    torque, _, _ = controller.update(True, CS, VehicleModel(CP), params, False, 0.0, False, 0.2)
  return torque


class TestLearnedLatOffset:
  def test_mg_uses_only_the_offset(self):
    CP = get_CP(MG.MG_HS)
    tune = CP.lateralTuning.torque
    assert learned_offset_torque_params(CP, torque_params(-0.31)) == pytest.approx((tune.latAccelFactor, -0.31, tune.friction))

  def test_offset_is_bounded(self):
    CP = get_CP(MG.MG_HS)
    assert learned_offset_torque_params(CP, torque_params(-2.0))[1] == -MAX_LAT_ACCEL_OFFSET
    assert learned_offset_torque_params(CP, torque_params(2.0))[1] == MAX_LAT_ACCEL_OFFSET

  def test_other_brands_unchanged(self):
    assert learned_offset_torque_params(get_CP(TOYOTA.TOYOTA_COROLLA_TSS2), torque_params(-0.31)) is None
    # brands torqued already applies all learned params to
    assert learned_offset_torque_params(get_CP(MG.MG_HS), torque_params(-0.31, use_params=True)) is None

  def test_route_5a_roll_bias_cancelled(self):
    # MG HS routes 55-5b: roll averaged +2.2 deg on straight roads and torqued learned latAccelOffset -0.31
    CP = get_CP(MG.MG_HS)
    without = straight_road_torque(CP, 2.2)
    with_offset = straight_road_torque(CP, 2.2, learned_offset_torque_params(CP, torque_params(-0.31)))
    assert without > 0.1  # pushes left (left-positive) on a straight road
    assert abs(with_offset) < without / 2  # what is left is mostly the friction term
