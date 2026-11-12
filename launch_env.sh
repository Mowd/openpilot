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
  export AGNOS_VERSION="20.5"
fi

export STAGING_ROOT="/data/safe_staging"

# 暫時：強制指定 MG HS PHEV 車型。fingerprints.py 裡的 HS 韌體版本號尚未在實車驗證，
# 取得實車 carFw 並更新 fingerprints.py 後移除此行
export FINGERPRINT="MG_HS"
