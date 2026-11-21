# MG HS PHEV 上游 PR 檢查清單

目標：發 PR 給 [commaai/opendbc](https://github.com/commaai/opendbc)，新增 MG HS PHEV 車型。
依據官方的 [Car porting checklist](https://github.com/commaai/opendbc/blob/master/docs/CAR_PORTING_CHECKLIST.md) 整理，項目對照目前 `hs-phev` 的狀態。

- `[x]` 已符合
- `[ ]` 還沒符合，就是接下來要做的
- 「待實車驗證」：程式已經寫好，但還沒上車確認

不需要做的部分：openpilot 自己控制油門煞車、雷達解析。HS 沿用原廠 ACC，官方不要求這些。
stop & go 也不是必要條件，官方支援的 406 個車款中有 97 個沒有自動停車起步。

最後更新：2026-11-22（EPS 狀態 4：鎖住時停送請求再重送，ZS route 3d 發現持續請求時不會解除；2026-11-19 route 3e 停車起步：前車只以 1～3 km/h 慢慢爬時 openpilot 的規劃判定該停著、要自己按 RES，fork 改成鏡頭看到前車在走就送（待實車，PR 不含）；之前 2026-11-16：支援 MG HS 1.5 油車：0xAF 區分 PHEV／油車、修正油車韌體版本）

---

## 1. 車輛與環境

- [ ] 在 `values.py` 寫清楚廠牌、車型、年份、等級、市場（台灣）、需要的 ADAS 配備（目前只寫「MG HS PHEV 2023」）
- [x] 看過的 ECU 韌體版本都加進 `fingerprints.py`（EPS、攝影機、雷達各兩組：PHEV 和 1.5 油車）。油車那組原本是從 pctine 的 hs 分支抄來的，EPS 和攝影機版本放反了，11/16 用油車 rlog 確認後修正
- [x] 跟 MG 5 EV 不同的訊號都在實車上驗證過，例如油門、煞車、檔位、車門
- [ ] 確認 harness 接腳與款式：文件寫 `vw_a`，實際用的是 xnor harness。不相容的話，要在 PR 裡註明是新的 harness 款式
- [x] CAN bus 分配：bus 0 是車輛／ADAS（雷達、ABS、閘道器、EPS），bus 1 是只能聽的私有 CAN（FCW 0x382、約 15 Hz 的物件清單 0x340～0x3FF），bus 2 是攝影機
- [ ] 整理每個相關訊息由哪個 ECU 送、哪個收、誰轉發（決定 safety 要轉發或攔截什麼）。2026-11-16 已確認：bus 2 只有攝影機的 0x166、0x167、0x1FD、0x33B；雷達的 0x242（ACC 加減速要求，送給 ABS）、0x244、0x246 都在 bus 0，不經過 harness。還沒整理成完整表格
- [ ] 記錄原廠 LKAS、ACC、stop & go、駕駛介入時的行為，當作比對基準
- [ ] 裝置接著時，驗證點火偵測、開機、熄火、車輛休眠都正常

## 2. 車型辨識與參數

- [x] 多次冷啟動都能正確辨識，不靠強制 `FINGERPRINT` 或快取（2026-11-15 熄火重開兩次，`fingerprintSource` 都是 `fw`，三個 ECU 都在 bus 0 回應）
- [x] 韌體查詢用正確的 ECU 位址與 bus（HS 用 bus 0，MG 5 EV 保留 bus 1）
- [ ] 韌體查詢不會讓儀表板出現故障碼（待實車驗證）
- [ ] 精確與模糊辨識都能區分需要不同控制的車款，例如 MG HS 汽油版、沒有 ACC 的等級。11/16：1.5 油車用同一個 `MG_HS`，靠 CAN 上有沒有 PHEV 的 HCU 訊息 0xAF 區分（油車 rlog 重播：韌體精確辨識、CAN 全程有效、safety 沒有收訊錯誤）；油車還沒實車啟用過，`values.py` 的車款文件也還沒加油車
- [ ] 不認識的韌體不會被誤判成不相容的車款。必要時用 CAN 訊號判斷，並設為 `dashcamOnly`
- [x] 軸距、轉向比要有可靠的資料來源：軸距 2720 mm（台灣、英國規格表一致）；原廠沒公布轉向比，改用實車資料定為 16.8（paramsd 30 段學到 16.6～17.0，低速偏航率推算 16.8，左右打死各約 480 度）
- [ ] `minSteerSpeed`、`minEnableSpeed`、`autoResumeSng`、`steerAtStandstill` 符合實際行為（目前是預設的 0 / 0 / True / False）

## 3. CAN 解析與訊息組裝

- [ ] 訊息位址、長度、bus、頻率、byte 順序、正負號、比例、單位都驗證過
- [x] counter 與 checksum 用實車資料驗證，包含 counter 從最大值繞回 0（2026-11-16 route 23 實車開啟檢查，24 分鐘只有開機前 3 幀 CAN 無效；5 條路線，車速、雷達、方向盤角度、ABS 是 CRC-8＋4 bit counter，EPS 是 MG 5 EV 的自訂 checksum，checksum 全部正確、counter 只在開機時跳；油門 0xC9 的 counter 會跳所以只檢查 checksum；煞車壓力 0x214 只有 2 bit counter）
- [x] 訊息遺失、過期、格式錯誤或 checksum 錯誤時，會正確變成 CAN 無效狀態（用實車 log 故意改壞 0x23C、0x242、0x1EC 的 checksum 或 0x214 的 counter，CAN 都變成無效）
- [ ] 頻率會變動的訊息，在 `get_can_parsers` 明確指定頻率
- [ ] 開機時的預設值或無效值，不會被誤當成可以啟用
- [x] 複製原廠訊息時保留其他欄位，而且用最新的資料（0x1E1 每次都從最新的閘道器訊息複製）
- [x] 送出的訊息 bus、時機、counter、checksum、請求位元都正確（0x1FD checksum、0x1E1 PV 都和實車擷取的一致）
- [ ] 轉發與替換規則不會造成重複的控制訊息。0x1E1 的 counter 會跟閘道器的原始訊息重複，PR 裡要說明

## 4. 車輛狀態

- [x] 安全帶：扣上、解開都正確更新 `seatbeltUnlatched`（實車：啟用中解開，openpilot 立即解除，原廠 ACC 同時自己回到 Standby）
- [x] 車門：每個車門分別開關都正確，全部關上前 `doorOpen` 都維持 true。原本讀的 `DrvrDoorOpenSts_H1_Safety`（bit 47）開駕駛座門時不會變，已改成四個車門的原廠訊號，用實車 log 重播四個門都正確，行駛中沒有誤判
- [x] 檔位：P、R、N、D 都有解析，不認得的值回報為 unknown，不會被當成 D
- [x] 煞車：用駕駛煞車壓力判斷，門檻跟 safety 一致。11/16 route 26 發現：輕碰煞車時，煞車開關（0xAF `EPTBrkPdlDscrtInptStsHSC2`）先變 1、壓力只有 75 kPa，原廠 ACC 就取消了，但 openpilot 的門檻是壓力 > 100 kPa，三次都沒偵測到（看起來像 ACC 自己取消）。已改成「煞車開關或壓力」，carstate 和 safety 一致（od `aa0c02cb`）；route 2a 實車 9 次踩煞車都在 ACC 取消前偵測到，包括 75 kPa 的輕碰
- [x] 油門：駕駛只要踩一點就是 `gasPressed`，巡航中也一樣，不會被 ACC 自己的加速誤判
- [ ] 手煞車 `parkingBrake`、Auto Hold `brakeHoldActive`
- [x] 車速、停車判斷跟 safety 用同一個訊號（0x23C）
- [x] 儀表車速、巡航設定速度跟實車一致（km/h）
- [x] 方向盤角度、駕駛扭力、EPS 扭力、`steeringPressed` 的方向和比例都正確
- [x] 方向燈：只有撥桿位置，所以用 `update_blinker_from_stalk`，短撥維持 1 秒
- [x] 盲點警示：左右對應正確
- [x] 轉向故障：攝影機 LDW 故障算暫時故障，EPS 狀態 3 算永久故障。EPS 狀態 4（駕駛反向施力後的鎖定）不算故障，改由 carcontroller 停送請求 0.2 秒再重送；EPS 輸出凍結（鎖住前 1.9 秒的前兆）時就提早停送（2026-11-22：ZS route 3d 鎖住後 openpilot 持續請求，EPS 鎖 18～120 秒都沒解除，停止請求後 0.03～2 秒就解除；HS 多半不用請求就解除、少數重新請求後才解除，所以停送和重送交替）。HS 實車待確認重送後恢復出力
- [ ] 低速轉向鎖定要用 `lowSpeedAlert`，不要當成故障（要先確認 HS 有沒有這種情況）
- [ ] `accFaulted`、`carFaultedNonCritical`、`carNotReady`、`vehicleSensorsInvalid` 都正確回報（`accFaulted` 目前取自攝影機 TJAICA 故障，未驗證）
- [ ] 解析 ESP 關閉／作動（還沒做）
- [x] 原廠 AEB／FCW 設定：車上把 FCW 靈敏度改成 1、3 再改回 2，`FCWSnstvtLvl` 跟著變；關閉 AEB 時 `AEBPedtrnDspCmd` 從 2 變 1。改設定都沒有讓 `stockFcw`／`stockAeb` 誤報
- [ ] 原廠 AEB／FCW 警示：已實作。`stockFcw` 是 FCW 警示等級不為 0；`stockAeb` 是雷達 AEB 作動，或 ABS 回應已執行 AEB 減速。重播三趟 log 都沒有誤報，但還沒真的發生過警示或 AEB，無法安全地刻意觸發
- [ ] 偵測原廠 LKAS 設定（`invalidLkasSetting`）、非自適應巡航（`cruiseState.nonAdaptive`），如果有需要

## 5. 按鍵與巡航狀態

- [x] SET、RES、Cancel、加速、減速、車距按鍵都轉成 `buttonEvents`（都已實車驗證；車距鍵 2026-11-15 route 18 確認，原廠車距等級 3→2→1 跟著變）
- [x] 主開關：0x1E1 的 `CCSwStsOnSwA` 是 ACC 開關狀態，不是按鍵。實車用 Cancel 關閉 ACC 時它和 ACC 狀態同時變 0，按 RES 後同時恢復成 1，所以不產生 `mainCruise`
- [x] 按下、放開各只觸發一次（log 重播：23 次按壓，每次各一個 press 和一個 release）
- [ ] 短按、長按、同時按都處理正確（短按、長按都已實車確認：短按跳到下一個 5 的倍數，長按約 0.6 秒後每 0.2 秒 ±1，HS route 19 長按 +、ZS route 06 長按 ±；同時按還沒測）
- [x] 巡航主開關狀態要真實反映：`cruiseState.available` 是 ACC 狀態不是 0。實車關閉 ACC 時變 False，畫面出現 wrongCarMode，恢復後變回 True
- [x] 巡航啟用：駕駛踩油門介入（狀態 3）、停車中（狀態 5、6）都維持啟用
- [x] `cruiseState.standstill` 只在需要按 RES 才能起步時為 true（狀態 6）
- [ ] 設定速度的變更、單位切換、最低／最高設定速度都正確（變更和最低 30 km/h 已從 log 確認；單位切換、最高設定速度還沒測）

## 6. 啟用與取消

- [ ] 按 SET／RES 只啟用一次，而且只在車輛準備好時啟用
- [ ] 安全帶、車門、檔位、手煞車、故障造成的拒絕啟用和解除都符合預期
- [x] 駕駛按實體 Cancel 時，openpilot 和原廠巡航都會解除（實車：ACC 狀態 2 → 4 → 1）
- [ ] 軟體取消：openpilot 解除但原廠 ACC 還在時送出 Cancel（已實作，每秒短按一次）。踩煞車期間和放開後 1 秒內不送，route 18 五次踩煞車都由 ACC 自己回到待命、沒有送 Cancel。還沒遇過真的需要靠它解除的情況
- [x] 取消優先於 SET／RES；重複取消不會恢復或重新啟用巡航（carcontroller 先判斷取消；safety 擋掉 Cancel 同時加其他按鍵）
- [x] 關閉巡航主開關會解除，而且不會意外重新啟用（停車時關閉顯示 wrongCarMode；HS 撥桿推到底一定會先經過 Cancel 才關閉 ACC，兩段都已實車驗證：Cancel 在 route 13、關閉在 route 12）
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
- [x] 調校：各種速度和彎道都沒有擺動、延遲、扭力飽和（例如 30 km/h 轉不過的那個彎）
  - 2026-11-15：扭力參數從 1.2／0.22 改成 openpilot 實車學習值 0.9／0.19（torqued 約 4260 個 54 km/h 以上的資料點，學到 0.88～0.94、摩擦約 0.19）。route 18 實車：手感良好，時速 30 的急彎都過得去（車主確認）
- [x] `actuatorsOutput` 跟實際送出的指令一致

## 8. 沿用原廠 ACC

- [x] 原廠 ACC 搭配 openpilot 轉向時，取消、踩油門介入、stop & go 都正常（route 18：前車離開後短按 RES 約 1 秒起步兩次、踩煞車解除五次都直接回到待命；實體 Cancel 在 route 13 驗證；route 3e：前車開走後自動送 RES 起步，但前車只以 1～3 km/h 慢慢往前時，openpilot 的 MPC 和 e2e 模型都判定該停著、不送 RES，駕駛約 6 秒後自己按 RES，這是上游 openpilot 的規劃行為；fork 另外改成鏡頭看到前車在走也送 RES，見第 12 節）

## 9. 原廠功能

- [x] 原廠 LKAS 不會跟 openpilot 搶控制（0x1FD 由 harness 繼電器攔截）
- [ ] 原廠安全訊息照預期轉發，確認 AEB／FCW 不受影響
- [ ] 正常使用時，儀表板不會出現持續的警告或故障碼（韌體查詢是否留下故障碼還沒確認）
- [x] 儀表 LKA 燈號：openpilot 控制方向盤時送「作用中」，其他時候照抄原廠攝影機。route 18 確認 EPS 照常接受扭力、燈號正常（車主確認）
- [ ] openpilot 的接管、轉向無法使用等警告，會正確出現和消失

## 10. Safety

- [x] 只允許預期的送出位址、bus、長度（0x1FD；HS 另外允許 0x1E1）
- [x] safety 的啟用判斷跟 carstate 一致（ACC 狀態 2、3、5、6）
- [x] `controls_allowed` 為 false 時，非零扭力都會被擋
- [x] 未啟用時只允許送 Cancel；RES 只在啟用時允許，而且不能同時按其他鍵（fork 另外允許啟用中單獨送 −／+，送 PR 前要拿掉，見第 12 節）
- [x] 轉向扭力大小、變化速度、駕駛扭力都有檢查
- [ ] 送出訊息裡所有能控制車輛的欄位都有限制（0x1FD 的其他欄位，例如駕駛接管請求、震動等級，目前沒檢查）
- [x] counter／checksum 錯誤、訊息遺失、資料過期時會停止控制（車速、EPS、雷達檢查兩者，油門只檢查 checksum，煞車壓力只檢查 counter；5 條路線 safety 重播約 1,570 萬個訊框沒有誤判）
- [ ] safety 重播時，原本就有部分 0x1FD 轉向訊息在啟用中被擋（route 18 約 1.8 萬次），改 counter／checksum 前後一樣，實車轉向正常，原因待查。官方 CI 也會跑 safety 重播，送 PR 前要解決。11/16 實車（route 23）panda 的 `safetyTxBlocked` 整趟只加 3 次，都在踩煞車解除的那一刻（panda 先停止控制，openpilot 還多送一幀 0x1FD），所以重播的 1.8 萬次是重播本身的問題，不是實車行為
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
- [ ] 拿掉 fork 專屬功能，不放進 PR：彎道自動降速（opendbc `speed_buttons.py`、`car.capnp` 的 `speedTarget`、safety 允許 −／+ 和對應測試；openpilot 的 `curve_speed.py`、`lead_speed.py`、controlsd、兩個設定開關）；原廠雷達漏看前車警示（`car.capnp` 的 `stockRadar*`、carstate 讀 0x242／0x246 的部分；openpilot 的 `stock_radar_warning.py`、`stockRadarMissedLead`／`stockRadarLostLead` 事件）；停車起步不等規劃（openpilot 的 `lead_moving_off.py`、controlsd 的 resume 條件、`test_lead_moving_off.py`）；撥一次方向燈只變換一個車道、變換車道 2 Nm 確認門檻（openpilot 的 `desire_helper.py` 和 `test_desire_helper.py`）

---

## 下一步建議順序

1. 查 safety 重播時 0x1FD 被擋的原因
2. 手煞車／Auto Hold、ESP 關閉
3. harness 款式確認、整理訊息收送表
4. 選一段公開 route，整理成英文 PR（拿掉 fork 專屬功能）
5. 持續觀察：EPS 故障、原廠 AEB／FCW 自然觸發時的 log、韌體查詢有沒有留下故障碼
