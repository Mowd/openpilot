# fork (MG): apply only the latAccelOffset torqued learns
#
# torqued only applies its learned params to the brands in torqued.ALLOWED_CARS, which leaves out mg.
# On the MG HS the roll compensation is too big for this car (vehicleParameters.roll averages +2.1 to +2.4 deg
# on straight roads), so with a zero offset the feedforward pushes ~1 Nm left and holds the car ~0.17 m left of
# lane center. torqued learns latAccelOffset ~ -0.31 m/s^2, which cancels it.
# The learned latAccelFactor and friction stay unused: on the ZS they were skewed by heavy driver intervention.
import numpy as np

MAX_LAT_ACCEL_OFFSET = 0.5  # m/s^2, torqued doesn't bound the offset
LEARNED_OFFSET_BRANDS = ('mg',)


def learned_offset_torque_params(CP, torque_params):
  """Torque params with only the learned latAccelOffset, or None when this car doesn't use it."""
  if CP.brand not in LEARNED_OFFSET_BRANDS or torque_params.useParams:
    return None
  tune = CP.lateralTuning.torque
  offset = float(np.clip(torque_params.latAccelOffsetFiltered, -MAX_LAT_ACCEL_OFFSET, MAX_LAT_ACCEL_OFFSET))
  return tune.latAccelFactor, offset, tune.friction
