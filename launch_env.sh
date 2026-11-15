#!/usr/bin/env bash

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# models get lower priority than ui
# - ui is ~5ms
# - modeld is 20ms
# - DM is 10ms
# in order to run ui at 60fps (16.67ms), we need to allow
# it to preempt the model workloads. we have enough
# headroom for this until ui is moved to the CPU.
export QCOM_PRIORITY=12

if [ -z "$AGNOS_VERSION" ]; then
  export AGNOS_VERSION="20.6"
fi

export STAGING_ROOT="/data/safe_staging"

# MG ZS test build: force the MG_ZS fingerprint (as in the mg-zs branch) until FW auto-fingerprinting is verified on the car
export FINGERPRINT="MG_ZS"

# nav alpha: comma's route API answers 403 without comma prime, so navd can use a personal Mapbox token instead
# (MAPBOX_TOKEN, routes straight from api.mapbox.com). The token lives only on the device, never in this repo.
MAPBOX_TOKEN_FILE="/data/mapbox_token"
if [ -f "$MAPBOX_TOKEN_FILE" ]; then
  MAPBOX_TOKEN_VALUE="$(tr -d '[:space:]' < "$MAPBOX_TOKEN_FILE")"
  if [ -n "$MAPBOX_TOKEN_VALUE" ]; then
    export MAPBOX_TOKEN="$MAPBOX_TOKEN_VALUE"
  fi
  unset MAPBOX_TOKEN_VALUE
fi
unset MAPBOX_TOKEN_FILE
