# MG HS PHEV 與 MG ZS 差異表

兩台車用同一套 ADAS（攝影機、雷達）與 CAN 訊息，程式共用 `NON_EV_CAR` 的邏輯，下表只列出不同的地方。
新功能先在 `hs-phev` 做好、驗證，能套用到 ZS 的就同步到 `zs`。同步方式見最下方。

最後更新：2026-11-15

## 分支

| 項目 | MG HS PHEV | MG ZS |
|---|---|---|
| openpilot 分支 | `Mowd/openpilot` `hs-phev` | `Mowd/openpilot` `zs` |
| opendbc 分支 | `Mowd/opendbc` `hs-phev` | `Mowd/opendbc` `zs`（從 `hs-phev` 開出，多一個 MG_ZS commit） |
| openpilot 基底 | commaai master 2026-11-12（d2200f1） | commaai master 2026-11-13（77536e6） |
| 參數來源 | 原 `hs` 分支 + 實車 log | 朋友的 `mg-zs` 分支 |
| 測試者 | 車主本人（comma four） | 朋友 |
| 上游 PR | 目標 | 暫不考慮 |

## 車型參數

| 項目 | MG HS PHEV | MG ZS |
|---|---|---|
| 車型代號 | `MG_HS`（MG HS PHEV 2023） | `MG_ZS`（MG ZS 2025） |
| 軸距 | 2.72 m（規格表） | 2.58 m（mg-zs） |
| 轉向比 | 16.8（實車 log 學習值） | 15.8（mg-zs，從 MG 5 EV 沿用，未驗證） |
| 扭力參數 `override.toml` | `[1.2, 2.5, 0.22]` | `[1.2, 2.5, 0.18]` |
| 扭力上限 | 300（實測 EPS 硬上限 3.0 Nm） | 300（未實測上限） |
| 扭力增加／減少速度 | 7 / 11 | 7 / 8（mg-zs 原本 8/8，8 超過 ISO 11270 改 7） |
| 車型辨識 | 韌體自動辨識 | 強制 `FINGERPRINT="MG_ZS"`（`launch_env.sh`） |

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
| 原廠 AEB／FCW 警示 | 沒有（未驗證） | 有（mg-zs：`AEBMsgReqHSC2 == 2`、`FCWrnngSts == 1`） |
| 停車起步（短按 RES） | 有，待實車驗證 | 有，未驗證 |
| 取消原廠巡航 | 有，待實車驗證 | 有，未驗證 |
| 巡航按鍵事件、主開關 | 有，SET/RES/加減速已用 log 驗證 | 有，未驗證 |
| 煞車門檻 | 大於 1 格（75 kPa），與 safety 一致 | 同 HS（mg-zs 原本大於 0） |
| 車門、檔位、油門、安全帶、盲點 | 共用 | 共用 |

## 同步規則

1. 新功能先在 `hs-phev` 完成、測試。
2. 判斷 ZS 能不能用：共用的 ADAS／CAN 邏輯直接同步；只跟 HS 硬體有關的（例如 EPS 狀態意義、HS 的實測數值）先不套用到 ZS，或用 `CAR.MG_HS` 判斷限定。
3. opendbc：在 `zs` 上 `git merge hs-phev`（用 merge 不用 rebase，避免 force push 讓朋友裝置上的舊版本指到不存在的 commit），解決衝突後跑 `./test.sh`。
4. openpilot：`zs` 的 opendbc 子模組指到新的 opendbc `zs` commit。
5. 更新這張表，兩邊都 push。
