# MG HS PHEV 上游 PR 檢查清單

目標：發 PR 給 [commaai/opendbc](https://github.com/commaai/opendbc)，新增 MG HS PHEV 車型。
依據官方的 [Car porting checklist](https://github.com/commaai/opendbc/blob/master/docs/CAR_PORTING_CHECKLIST.md) 整理，項目對照目前 `hs-phev` 的狀態。

- `[x]` 已符合
- `[ ]` 還沒符合，就是接下來要做的
- 「待實車驗證」：程式已經寫好，但還沒上車確認

不需要做的部分：openpilot 自己控制油門煞車、雷達解析。HS 沿用原廠 ACC，官方不要求這些。
stop & go 也不是必要條件，官方支援的 406 個車款中有 97 個沒有自動停車起步。

最後更新：2026-11-14

---

## 1. 車輛與環境

- [ ] 在 `values.py` 寫清楚廠牌、車型、年份、等級、市場（台灣）、需要的 ADAS 配備（目前只寫「MG HS PHEV 2023」）
- [x] 看過的 ECU 韌體版本都加進 `fingerprints.py`（EPS、攝影機、雷達各兩組）
- [x] 跟 MG 5 EV 不同的訊號都在實車上驗證過，例如油門、煞車、檔位、車門
- [ ] 確認 harness 接腳與款式：文件寫 `vw_a`，實際用的是 xnor harness。不相容的話，要在 PR 裡註明是新的 harness 款式
- [x] CAN bus 分配：bus 0 是車輛／ADAS，bus 1 是 OBD／輔助（FCW 0x382 只在這條），bus 2 是攝影機
- [ ] 整理每個相關訊息由哪個 ECU 送、哪個收、誰轉發（決定 safety 要轉發或攔截什麼）
- [ ] 記錄原廠 LKAS、ACC、stop & go、駕駛介入時的行為，當作比對基準
- [ ] 裝置接著時，驗證點火偵測、開機、熄火、車輛休眠都正常

## 2. 車型辨識與參數

- [ ] 多次冷啟動都能正確辨識，不靠強制 `FINGERPRINT` 或快取（已移除強制指定，待實車驗證）
- [x] 韌體查詢用正確的 ECU 位址與 bus（HS 用 bus 0，MG 5 EV 保留 bus 1）
- [ ] 韌體查詢不會讓儀表板出現故障碼（待實車驗證）
- [ ] 精確與模糊辨識都能區分需要不同控制的車款，例如 MG HS 汽油版、沒有 ACC 的等級
- [ ] 不認識的韌體不會被誤判成不相容的車款。必要時用 CAN 訊號判斷，並設為 `dashcamOnly`
- [x] 軸距、轉向比要有可靠的資料來源：軸距 2720 mm（台灣、英國規格表一致）；原廠沒公布轉向比，改用實車資料定為 16.8（paramsd 30 段學到 16.6～17.0，低速偏航率推算 16.8，左右打死各約 480 度）
- [ ] `minSteerSpeed`、`minEnableSpeed`、`autoResumeSng`、`steerAtStandstill` 符合實際行為（目前是預設的 0 / 0 / True / False）

## 3. CAN 解析與訊息組裝

- [ ] 訊息位址、長度、bus、頻率、byte 順序、正負號、比例、單位都驗證過
- [ ] counter 與 checksum 用實車資料驗證，包含 counter 從最大值繞回 0。目前 HS 解析時全部略過
- [ ] 訊息遺失、過期、格式錯誤或 checksum 錯誤時，會正確變成 CAN 無效狀態
- [ ] 頻率會變動的訊息，在 `get_can_parsers` 明確指定頻率
- [ ] 開機時的預設值或無效值，不會被誤當成可以啟用
- [x] 複製原廠訊息時保留其他欄位，而且用最新的資料（0x1E1 每次都從最新的閘道器訊息複製）
- [x] 送出的訊息 bus、時機、counter、checksum、請求位元都正確（0x1FD checksum、0x1E1 PV 都和實車擷取的一致）
- [ ] 轉發與替換規則不會造成重複的控制訊息。0x1E1 的 counter 會跟閘道器的原始訊息重複，PR 裡要說明

## 4. 車輛狀態

- [ ] 安全帶：扣上、解開都正確更新 `seatbeltUnlatched`（已實作，待實車驗證）
- [ ] 車門：每個車門分別開關都正確，全部關上前 `doorOpen` 都維持 true。HS 目前只監看駕駛座和副駕駛座
- [x] 檔位：P、R、N、D 都有解析，不認得的值回報為 unknown，不會被當成 D
- [x] 煞車：用駕駛煞車壓力判斷，門檻跟 safety 一致
- [x] 油門：駕駛只要踩一點就是 `gasPressed`，巡航中也一樣，不會被 ACC 自己的加速誤判
- [ ] 手煞車 `parkingBrake`、Auto Hold `brakeHoldActive`
- [x] 車速、停車判斷跟 safety 用同一個訊號（0x23C）
- [x] 儀表車速、巡航設定速度跟實車一致（km/h）
- [x] 方向盤角度、駕駛扭力、EPS 扭力、`steeringPressed` 的方向和比例都正確
- [x] 方向燈：只有撥桿位置，所以用 `update_blinker_from_stalk`，短撥維持 1 秒
- [x] 盲點警示：左右對應正確
- [x] 轉向故障：攝影機 LDW 故障算暫時故障，EPS 狀態 3 算永久故障。EPS 狀態 4（駕駛用力打方向盤後的鎖定）刻意不算，因為要等再次送出轉向請求才會解除
- [ ] 低速轉向鎖定要用 `lowSpeedAlert`，不要當成故障（要先確認 HS 有沒有這種情況）
- [ ] `accFaulted`、`carFaultedNonCritical`、`carNotReady`、`vehicleSensorsInvalid` 都正確回報（`accFaulted` 目前取自攝影機 TJAICA 故障，未驗證）
- [ ] 解析 ESP 關閉／作動、原廠 AEB／FCW 狀態
- [ ] 偵測原廠 LKAS 設定（`invalidLkasSetting`）、非自適應巡航（`cruiseState.nonAdaptive`），如果有需要

## 5. 按鍵與巡航狀態

- [ ] SET、RES、Cancel、加速、減速、車距按鍵都轉成 `buttonEvents`（已實作。SET、RES、加速、減速已用 log 重播驗證；Cancel、車距鍵在 log 裡沒按過，待實車驗證）
- [ ] 主開關按鍵：0x1E1 的 `CCSwStsOnSwA` 在所有 log 中都是 1，不像按鍵，所以沒有產生 `mainCruise`。要實車關一次 ACC 主開關，看這個位元和 ACC 狀態怎麼變
- [x] 按下、放開各只觸發一次（log 重播：23 次按壓，每次各一個 press 和一個 release）
- [ ] 短按、長按、同時按都處理正確（log 裡只有短按）
- [ ] 巡航主開關狀態要真實反映：`cruiseState.available` 已改成 ACC 狀態不是 0（關閉），跟 MG 5 EV 相同。但 log 裡從沒出現過狀態 0，待實車關主開關驗證
- [x] 巡航啟用：駕駛踩油門介入（狀態 3）、停車中（狀態 5、6）都維持啟用
- [x] `cruiseState.standstill` 只在需要按 RES 才能起步時為 true（狀態 6）
- [ ] 設定速度的變更、單位切換、最低／最高設定速度都正確

## 6. 啟用與取消

- [ ] 按 SET／RES 只啟用一次，而且只在車輛準備好時啟用
- [ ] 安全帶、車門、檔位、手煞車、故障造成的拒絕啟用和解除都符合預期
- [ ] 駕駛按實體 Cancel 時，openpilot 和原廠巡航都會解除（待實車驗證）
- [ ] 軟體取消：openpilot 解除但原廠 ACC 還在時送出 Cancel（已實作，每秒短按一次，待實車驗證）
- [x] 取消優先於 SET／RES；重複取消不會恢復或重新啟用巡航（carcontroller 先判斷取消；safety 擋掉 Cancel 同時加其他按鍵）
- [ ] 關閉巡航主開關會解除，而且不會意外重新啟用
- [ ] 放開踏板、關上車門、扣上安全帶、故障解除後，不會自己重新啟用
- [x] 轉向請求位元用 `CC.latActive`

## 7. 轉向控制

- [x] 小幅度左右轉向的方向正確
- [x] 扭力上限與變化速度跟 safety 一致：300、每次加 7／減 11，jerk 2.92 / 4.58，在 ISO 11270 限制內
- [x] 駕駛介入時會減少扭力（driver torque limited）
- [x] 扭力上限 300 是 EPS 的硬上限：實測送 400 時，EPS 回應最多 3.0 Nm，超過約 0.1 秒就故障（PR 要附這項證據）
- [ ] 最低轉向速度附近的行為正常，低速沒有來回擺動
- [ ] 持續轉向、快速轉向、請求位元切換都不會造成 EPS 故障（300 以內目前沒看到，要多跑幾趟確認）
- [x] 轉向暫時不能用時，停止送請求並顯示警告
- [ ] 調校：各種速度和彎道都沒有擺動、延遲、扭力飽和（例如 30 km/h 轉不過的那個彎）
- [x] `actuatorsOutput` 跟實際送出的指令一致

## 8. 沿用原廠 ACC

- [ ] 原廠 ACC 搭配 openpilot 轉向時，取消、踩油門介入、stop & go 都正常（短按 RES 起步、取消都待實車驗證）

## 9. 原廠功能

- [x] 原廠 LKAS 不會跟 openpilot 搶控制（0x1FD 由 harness 繼電器攔截）
- [ ] 原廠安全訊息照預期轉發，確認 AEB／FCW 不受影響
- [ ] 正常使用時，儀表板不會出現持續的警告或故障碼
- [ ] openpilot 的接管、轉向無法使用等警告，會正確出現和消失

## 10. Safety

- [x] 只允許預期的送出位址、bus、長度（0x1FD；HS 另外允許 0x1E1）
- [x] safety 的啟用判斷跟 carstate 一致（ACC 狀態 2、3、5、6）
- [x] `controls_allowed` 為 false 時，非零扭力都會被擋
- [x] 未啟用時只允許送 Cancel；RES 只在啟用時允許，而且不能同時按其他鍵
- [x] 轉向扭力大小、變化速度、駕駛扭力都有檢查
- [ ] 送出訊息裡所有能控制車輛的欄位都有限制（0x1FD 的其他欄位，例如駕駛接管請求、震動等級，目前沒檢查）
- [ ] counter／checksum 錯誤、訊息遺失、資料過期時會停止控制。HS 目前全部略過 counter 和 checksum
- [x] 繼電器故障偵測涵蓋實際的 harness 架構（0x1FD 有檢查；0x1E1 閘道器本來就會送，所以不檢查）
- [x] safety 測試涵蓋 `NON_EV` 旗標，而且會擋不允許的指令

## 11. 回歸測試

- [ ] 在 `routes.py` 加入公開的實車 route（要選哪一趟、要不要公開，由車主決定）
- [ ] `test_models.py` 用新的 route 測試通過
- [x] `test.sh` 全部通過
- [ ] 補上辨識、解析、訊息組裝、特殊情況的測試
- [ ] 重新檢查受影響的既有車型：MG 5 EV 靠 CI 的 route 測試，不需要實車
- [ ] 多趟行程、多次熄火重開後，啟動、啟用、取消、熄火都正常

## 12. 發 PR 前的整理

- [ ] commit 訊息改成英文，壓成 1～2 個 commit
- [ ] 程式註解拿掉「original hs branch」這種說法，改成上游看得懂的描述
- [ ] 註明 DBC 與部分邏輯的來源，並加上原作者的 `Co-authored-by`
- [ ] ACC 狀態改用具名常數，不要直接寫 2、3、5、6
- [ ] 檢查每幀複製按鍵訊息（`copy.copy`）的寫法是否合適
- [ ] PR 說明照模板附上 Dongle ID 和 route，還有：車型年份、harness、扭力上限 300 的實測證據、safety 測試結果
- [ ] 車型文件註明支援程度，例如轉向扭力偏弱、有沒有 stop & go

---

## 下一步建議順序

1. 上車驗證這一版：自動辨識車型、短按 RES 起步、取消巡航、按 Cancel 和車距鍵、關一次 ACC 主開關
2. counter／checksum 檢查（carstate 和 safety 都要）
3. 車門監看補齊、手煞車／Auto Hold
4. harness 款式確認
5. 選一段公開 route，整理成英文 PR
