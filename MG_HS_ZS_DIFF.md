# MG HS PHEV 與 MG ZS 差異表

兩台車用同一套 ADAS（攝影機、雷達）與 CAN 訊息，程式共用 `NON_EV_CAR` 的邏輯，下表只列出不同的地方。
新功能先在 `hs-phev` 做好、驗證，能套用到 ZS 的就同步到 `zs`。同步方式見最下方。

最後更新：2026-11-15（儀表 LKA 燈號：openpilot 控制時送作用中，其他時候照抄原廠相機；ZS：rlog 證實缺 0x251、有 0x1E1，韌體可自動辨識；AEB 不讀 0x251、0x1E1 改為選用，修正 Unknown Vehicle Variant；合併上游 openpilot 2026-11-14；HS 扭力參數改用學習值；車門改讀四個車門訊號；HS 實車驗證按鍵、主開關、自動辨識）

## 分支

| 項目 | MG HS PHEV | MG ZS |
|---|---|---|
| openpilot 分支 | `Mowd/openpilot` `hs-phev` | `Mowd/openpilot` `zs` |
| opendbc 分支 | `Mowd/opendbc` `hs-phev` | `Mowd/opendbc` `zs`（從 `hs-phev` 開出，加上 MG_ZS commit，之後用 merge 同步 hs-phev） |
| openpilot 基底 | commaai master 2026-11-14（cec317f，merge） | commaai master 2026-11-14（cec317f，merge） |
| 參數來源 | 原 `hs` 分支 + 實車 log | 朋友的 `mg-zs` 分支 |
| 測試者 | 車主本人（comma four） | 朋友 |
| 上游 PR | 目標 | 暫不考慮 |

## 車型參數

| 項目 | MG HS PHEV | MG ZS |
|---|---|---|
| 車型代號 | `MG_HS`（MG HS PHEV 2023） | `MG_ZS`（MG ZS 2025） |
| 軸距 | 2.72 m（規格表） | 2.58 m（mg-zs） |
| 轉向比 | 16.8（實車 log 學習值） | 15.8（mg-zs，從 MG 5 EV 沿用，未驗證） |
| 扭力參數 `override.toml` | `[0.9, 2.5, 0.19]`（openpilot 實車學習值，約 4260 個高速資料點） | `[1.2, 2.5, 0.18]`（mg-zs，可用朋友的 log 算學習值） |
| 扭力上限 | 300（實測 EPS 硬上限 3.0 Nm） | 300（未實測上限） |
| 扭力增加／減少速度 | 7 / 11 | 7 / 8（mg-zs 原本 8/8，8 超過 ISO 11270 改 7） |
| 車型辨識 | 韌體自動辨識（實車驗證：兩次冷啟動都成功） | 強制 `FINGERPRINT="MG_ZS"`（`launch_env.sh`）。朋友 rlog（`bf23cd5`）：EPS 0x721、相機 0x733、雷達 0x732 都在 bus 0 回應，三個版本都和 MG_ZS 完全相符，確認 CAN 正常後可以拿掉強制設定 |

## ECU 韌體

| ECU | MG HS PHEV | MG ZS |
|---|---|---|
| EPS | 0x721：`\x10D\x860\x01`、`\x10\x92\x33\x87\x01` | 0x721：`\x11\x06c\x94\x01` |
| 攝影機 | 0x733：`\x10cT\x97\x01`、`\x10\x79\x07\x92\x01` | 0x733：`\x10\x89wQ\x01` |
| 雷達 | **0x734**：`\x10cT\x99\x01`、`\x10\x92\x33\x80\x01` | **0x732**：`\x11RuP\x01` |
| 回應的 bus | bus 0、2（已驗證） | 未知，等朋友的 rlog |

## 車輛狀態與功能

| 功能 | MG HS PHEV | MG ZS |
|---|---|---|
| 方向燈 | 撥桿位置 `DircnIndLampSwStsHSC2`，短撥維持 1 秒 | 燈號位元 `BlinkerLeft/Right`（mg-zs） |
| EPS 故障偵測（狀態 3 = 永久故障） | 有 | **沒有**：EPS 型號不同，狀態意義未確認 |
| 原廠 AEB／FCW 警示 | 共用：FCW 任一級警示；AEB 是雷達作動或 ABS 已執行 AEB 減速（未實車觸發過） | FCW 同 HS；AEB 只看雷達：ZS 沒有 `SCS_HSC2_FrP24`（0x251），讀了會讓 CAN 永遠無效（Unknown Vehicle Variant）。朋友 rlog（`bf23cd5`）的 CANParser 警告證實只缺 0x251，`8598fbb` 已修正，待實車確認 |
| 停車起步（短按 RES） | 有，待實車驗證 | 有，未驗證 |
| 取消原廠巡航 | 有。實體 Cancel 已實車驗證；安全帶、煞車時原廠 ACC 會自己解除，還沒遇過需要軟體取消的情況 | 有，未驗證 |
| 巡航按鍵事件、主開關 | 有。SET/RES/加減速/Cancel 已實車驗證；主開關 `CCSwStsOnSwA` 是 ACC 開關狀態，不是按鍵；車距鍵待確認 | 0x1E1 設為選用（沒收到時沒有按鍵事件，也不會自動起步或送 Cancel）。朋友 rlog 證實 ZS 的 bus 0 有 0x1E1（約 40 Hz），按鍵功能應該可用，待實車驗證 |
| 儀表 LKA 燈號 | openpilot 控制方向盤時送 2（作用中），其他時候照抄原廠相機（HS 平常是 1 待命）。原本固定送 0（關閉），燈號不亮。重播 11/15 rlog 確認輸出正確，待實車確認燈號和 EPS 接受 2 | 同 HS。朋友停車的 log 相機送 0，照抄後一樣是 0；行駛中的值待確認 |
| 煞車門檻 | 大於 1 格（75 kPa），與 safety 一致 | 同 HS（mg-zs 原本大於 0） |
| 車門 | 四個車門的原廠訊號（實車驗證） | 同 HS（mg-zs 原本讀 bit 47 的 `DrvrDoorOpenSts_H1_Safety` 和副駕，HS 上 bit 47 不會變，待朋友驗證） |
| 檔位、油門、安全帶、盲點 | 共用 | 共用 |

## 同步規則

1. 新功能先在 `hs-phev` 完成、測試。
2. 判斷 ZS 能不能用：共用的 ADAS／CAN 邏輯直接同步；只跟 HS 硬體有關的（例如 EPS 狀態意義、HS 的實測數值）先不套用到 ZS，或用 `CAR.MG_HS` 判斷限定。
   **新讀任何 CAN 訊息都要注意**：CarState 讀到的訊息都會變成必要訊息，ZS 沒有就整個 CAN 無效。ZS 只能讀 mg-zs 用過的訊息（清單在 opendbc `zs` 的 `opendbc/car/mg/tests/test_mg.py`），其他的要用 `CAR.MG_HS` 限定或設為選用。
3. opendbc：在 `zs` 上 `git merge hs-phev`（用 merge 不用 rebase，避免 force push 讓朋友裝置上的舊版本指到不存在的 commit），解決衝突後跑 `./test.sh`。
4. openpilot：`zs` 的 opendbc 子模組指到新的 opendbc `zs` commit。
5. 更新這張表，兩邊都 push。
