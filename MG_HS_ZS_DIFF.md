# MG HS PHEV 與 MG ZS 差異表

兩台車用同一套 ADAS（攝影機、雷達）與 CAN 訊息，程式共用 `NON_EV_CAR` 的邏輯，下表只列出不同的地方。
新功能先在 `hs-phev` 做好、驗證，能套用到 ZS 的就同步到 `zs`。同步方式見最下方。

最後更新：2026-11-16（ZS 朋友實車 route 05–07（`8598fbbb5`）：三次發動韌體都精確比對到 MG_ZS、沒有 Car Unrecognized；停車起步 6 次、按鍵、Cancel、完全關閉 ACC、行駛中解開安全帶都正常；沒有 AEB／FCW 誤報或轉向故障；開機後約 3 秒前鏡頭 LDW 故障位元會亮（轉向暫時不可用，無聲），HS 沒有；route 06 rlog：FCW 靈敏度、AEB 開關、ACC 主開關都讀得到；ZS 駕駛座門在 47|2，已修正（待實車）、左後右後門共用一個訊號；HS 實車 route 19、1a：Mapbox 導航路線正常、長按加速每次 +1 km/h；route 18 驗證：踩煞車不送 Cancel、自動停車起步、EPS 接受 LKA 狀態 2、儀表 LKA 燈號正常、車距鍵、扭力參數手感良好；踩煞車不再送 Cancel；儀表 LKA 燈號：openpilot 控制時送作用中，其他時候照抄原廠相機；ZS：rlog 證實缺 0x251、有 0x1E1，韌體可自動辨識；AEB 不讀 0x251、0x1E1 改為選用，修正 Unknown Vehicle Variant；合併上游 openpilot 2026-11-14；HS 扭力參數改用學習值；車門改讀四個車門訊號；HS 實車驗證按鍵、主開關、自動辨識）

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
| 車型代號 | `MG_HS`（MG HS PHEV 2023；1.5 油車也是 `MG_HS`，CAN 上沒有 0xAF 就當油車） | `MG_ZS`（MG ZS 2025） |
| 軸距 | 2.72 m（規格表） | 2.58 m（mg-zs） |
| 轉向比 | 16.8（實車 log 學習值） | 15.8（mg-zs，從 MG 5 EV 沿用，未驗證） |
| 扭力參數 `override.toml` | `[0.9, 2.5, 0.19]`（openpilot 實車學習值，約 4260 個高速資料點；route 18 實車手感良好，時速 30 急彎都過得去） | `[1.2, 2.5, 0.18]`（mg-zs，可用朋友的 log 算學習值） |
| 扭力上限 | 300（實測 EPS 硬上限 3.0 Nm） | 300（未實測上限） |
| 扭力增加／減少速度 | 7 / 11 | 7 / 8（mg-zs 原本 8/8，8 超過 ISO 11270 改 7） |
| 車型辨識 | 韌體自動辨識（實車驗證：兩次冷啟動都成功） | 韌體自動辨識（11/16 拿掉強制 `FINGERPRINT="MG_ZS"`，待朋友更新後實車確認）。朋友 rlog（`bf23cd5`）：EPS 0x721、相機 0x733、雷達 0x732 都在 bus 0 回應，三個版本都和 MG_ZS 完全相符。11/15 route 05–07 三次發動：同樣三顆 ECU 都在 bus 0 回應，用 zs 分支比對都精確辨識為 MG_ZS |

## ECU 韌體

| ECU | MG HS PHEV | MG ZS |
|---|---|---|
| EPS | 0x721：`\x10D\x860\x01`（PHEV）、`\x10\x79\x07\x92\x01`（1.5 油車） | 0x721：`\x11\x06c\x94\x01` |
| 攝影機 | 0x733：`\x10cT\x97\x01`（PHEV）、`\x10\x92\x33\x87\x01`（1.5 油車） | 0x733：`\x10\x89wQ\x01` |
| 雷達 | **0x734**：`\x10cT\x99\x01`（PHEV）、`\x10\x92\x33\x80\x01`（1.5 油車） | **0x732**：`\x11RuP\x01` |
| 回應的 bus | bus 0、2（已驗證） | bus 0（朋友 4 次發動都一樣） |

## 車輛狀態與功能

| 功能 | MG HS PHEV | MG ZS |
|---|---|---|
| 方向燈 | 撥桿位置 `DircnIndLampSwStsHSC2`，短撥維持 1 秒 | 燈號位元 `BlinkerLeft/Right`（mg-zs） |
| EPS 故障偵測（狀態 3 = 永久故障） | 有 | **沒有**：EPS 型號不同，狀態意義未確認 |
| 原廠 AEB／FCW 警示 | 共用：FCW 任一級警示；AEB 是雷達作動或 ABS 已執行 AEB 減速（未實車觸發過） | FCW 同 HS；AEB 只看雷達：ZS 沒有 `SCS_HSC2_FrP24`（0x251），讀了會讓 CAN 永遠無效（Unknown Vehicle Variant）。朋友 rlog（`bf23cd5`）的 CANParser 警告證實只缺 0x251，`8598fbb` 已修正，待實車確認 |
| 停車起步（短按 RES） | 有，實車驗證（11/15 route 18 兩次：雷達起步提示 `ACCGoNotfr` 後立刻送 RES，約 1 秒起步） | 有，實車驗證（11/15 route 05、06 共 6 次：停車後自動送 RES 起步） |
| 取消原廠巡航 | 有。實體 Cancel 已實車驗證。踩煞車時原廠 ACC 會自己回到待命（2→1），但常比 openpilot 偵測到煞車晚約 0.1–0.2 秒，原本 openpilot 會趁這段時間送 Cancel，變成撥桿取消（2→4 Brake Only→1）。現在踩煞車期間和放開後 1 秒內不送 Cancel（重播 11/14 log：5 次煞車原本都送，現在都不送；11/15 route 18 實車 5 次踩煞車都直接 2→1，沒送 Cancel） | 有，未驗證 |
| 巡航按鍵事件、主開關 | 有。SET/RES/加減速/Cancel 已實車驗證；主開關 `CCSwStsOnSwA` 是 ACC 開關狀態，不是按鍵；車距鍵實車驗證（route 18：原廠車距等級跟著變）。長按加速實車驗證（route 19：每 0.2 秒 +1 km/h，30→35），長按減速未測。撥桿推到底關閉 ACC 一定會先經過 Cancel，所以 openpilot 作用中時會先照 Cancel 解除，再變成 ACC 關閉；兩段都已實車驗證（Cancel：route 13；關閉：route 12 停車測試，ACC 1→0，openpilot 判斷主開關關閉） | 0x1E1 設為選用（沒收到時沒有按鍵事件，也不會自動起步或送 Cancel）。朋友 rlog 證實 ZS 的 bus 0 有 0x1E1（約 40 Hz），按鍵功能應該可用，待實車驗證 |
| counter／checksum 檢查 | 車速 0x23C、雷達 0x242、EPS 0x1EC、方向盤角度 0x1E5、ABS 0x251 的 checksum 和 counter；油門 0xC9 只檢查 checksum；煞車壓力 0x214 只檢查 counter（5 條路線重播沒有誤判；11/16 route 23 實車整趟沒有 CAN 錯誤） | 自己的 DBC `mg_zs_generated` 和 safety 旗標 `ZS`：只檢查車速、EPS 的 checksum，和車速、EPS、煞車壓力、方向盤角度、按鍵、攝影機的 counter。ZS 的雷達 0x242、油門 0xC9 沒有對應的 counter／checksum，方向盤角度 checksum 也不同（3 條路線重播沒有誤判） |
| 彎道自動降速（fork 專屬） | 有，預設關閉，11/16 route 23 實車有觸發、正常恢復（ZS route 08 實測：上坡後的急彎太晚減速，已加入 ACC 延遲 1.5 秒；ACC 偶爾會忽略按鍵，改成暫停 10 秒再試；模型 80 m 外的彎道看不準，高速匝道仍可能來不及；連續彎道會在 5 km/h 檔位間來回按，已加遲滯；route 2a 轉彎和前車離開後加速太慢，目標上升速率 1 → 3 m/s²、往上加不再等車速）。短按 −／+ 調原廠 ACC 設定速度（每下 5 km/h，最低 30），過彎後恢復 | 同 HS（共用程式），待實車驗證 |
| 前車減速提前降速（fork 專屬） | 有，預設關閉，11/16 route 23 實車正常（前車減速時設定速度降到 30，平順減速不用踩煞車）。模型想為前車減速時短按 − 提早調低原廠 ACC 設定速度（最低 30），不再需要時恢復 | 同 HS（共用程式），待實車驗證 |
| 原廠雷達漏看前車警示（fork 專屬） | 有，預設開啟。鏡頭看到正在接近的前車、原廠雷達沒鎖定（0x246 `ACCObjDet_RadarHSC2`）且 ACC 煞車不夠（0x242 `ACCAccReqValHSC2`）時，顯示「BRAKE!」並發出警示音（route 23 重播只在雷達漏看那次響） | 有。目標旗標和 HS 相同（route 06、08：357 次有 347 次和鏡頭一致）；ZS 讀不到 ACC 的加減速要求（0x242 幾乎全是 0），改用車子實際的加速度判斷。ZS 3 條路線重播沒有誤報，還沒遇過雷達漏看的實際情況 |
| 原廠雷達跟丟前車提示（fork 專屬） | 有。鏡頭看到 5 秒車距、40 m 內的前車、雷達沒鎖定、ACC 加速要求 > 0.3 m/s² 持續 0.5 秒，顯示「Stock Radar Lost the Car Ahead」並響一聲（route 2a 實車有作動） | 有，ACC 加速改用實際加速度 |
| 變換車道（fork 專屬） | 撥一次方向燈只變換一個車道；要往變換方向施力超過 2 Nm 才開始（`steeringPressed` 維持 1 Nm）。HS 手扶方向盤就有 1～2 Nm（route 2b：超過 1 Nm 佔 31%、超過 2 Nm 佔 2%），原本方向燈一撥就開始，變換完方向燈還撥著時也會自己觸發第二次 | 同 HS（共用程式），ZS 的施力情況未確認 |
| 車型辨識失敗重試（fork 專屬） | 有（HS 沒遇過辨識失敗） | 有。ZS 偶爾 Car Unrecognized，推測是發動引擎時 ECU 漏回應；認不出時等 2 秒再查，最多重試 2 次 |
| 儀表 LKA 燈號 | openpilot 控制方向盤時送 2（作用中），其他時候照抄原廠相機（HS 平常是 1 待命）。原本固定送 0（關閉），燈號不亮。重播 11/15 rlog 確認輸出正確；route 18 實車確認 EPS 在狀態 2 照常接受扭力（CtrlSts 1），儀表燈號正常亮起（車主確認） | 同 HS。朋友停車的 log 相機送 0，照抄後一樣是 0；行駛中的值待確認 |
| 煞車門檻 | 壓力大於 1 格（75 kPa）或煞車開關（0xAF `EPTBrkPdlDscrtInptStsHSC2`，輕碰就會讓原廠 ACC 取消），與 safety 一致。0xAF 是 PHEV 的 HCU 才有，1.5 油車只用壓力（開機時看 CAN 上有沒有 0xAF，設 `MgFlags.PHEV`／safety `PHEV`） | 只用壓力大於 1 格（ZS 沒有 0xAF；mg-zs 原本大於 0） |
| 車門 | 四個車門的原廠訊號（實車驗證） | 駕駛座門讀 47\|2（DBC 裡是 `BntOpenStsHSC2`，原 hs 分支叫 `DrvrDoorOpenSts_H1_Safety`；ZS 的 `DrvrDoorOpenStsHSC2` 不會變），副駕同 HS，左後、右後門共用 `RLDoorOpenStsHSC2`（朋友確認）。route 06 重播四個門都抓得到、整趟沒有誤判，待實車確認 |
| 檔位、油門、安全帶、盲點 | 共用 | 共用 |

## 同步規則

1. 新功能先在 `hs-phev` 完成、測試。
2. 判斷 ZS 能不能用：共用的 ADAS／CAN 邏輯直接同步；只跟 HS 硬體有關的（例如 EPS 狀態意義、HS 的實測數值）先不套用到 ZS，或用 `CAR.MG_HS` 判斷限定。
   **新讀任何 CAN 訊息都要注意**：CarState 讀到的訊息都會變成必要訊息，ZS 沒有就整個 CAN 無效。ZS 只能讀 mg-zs 用過的訊息（清單在 opendbc `zs` 的 `opendbc/car/mg/tests/test_mg.py`），其他的要用 `CAR.MG_HS` 限定或設為選用。
3. opendbc：在 `zs` 上 `git merge hs-phev`（用 merge 不用 rebase，避免 force push 讓朋友裝置上的舊版本指到不存在的 commit），解決衝突後跑 `./test.sh`。
4. openpilot：`zs` 的 opendbc 子模組指到新的 opendbc `zs` commit。
5. 更新這張表，兩邊都 push。
