# MG HS PHEV／MG ZS 更新紀錄

`hs-phev`（MG HS PHEV，車主本人）和 `zs`（MG ZS，朋友）兩個分支的功能變更，新的在最上面。時間是 commit 時間（台灣時間）。

- **分支**：HS = `hs-phev`，ZS = `zs`。`zs` 在 2026-11-15 03:06 從 `hs-phev` 開出，之前的項目 ZS 都有（標「HS 專屬」的除外）。
- **狀態**：✅ 實車驗證過；🔶 log 重播或測試通過，待實車確認；— 不需要實車驗證。
- **commit**：od = opendbc（`Mowd/opendbc`），op = openpilot（`Mowd/openpilot`）。HS／ZS 各一個時用「／」分開。
- 兩車的參數、功能差異見 `MG_HS_ZS_DIFF.md`（在 `hs-phev`）。這份紀錄在兩個分支內容相同，每次變更兩邊一起更新。

## 2026-11-16

| 時間 | 分支 | 變更 | 狀態 | commit |
|---|---|---|---|---|
| 00:48 | HS、ZS | **彎道自動降速（fork 專屬，預設關閉）。** openpilot 依模型預測路徑算出彎道安全速度（側向加速度 2.0 m/s²，預留原廠 ACC 1.0 m/s² 的減速距離），MG 車控用短按 −／+（每下 5 km/h，最低 30）調低原廠 ACC 設定速度，過彎後回到駕駛原本的速度。只在 ACC 作用中、車速比目標快時才調；駕駛自己按鍵後 2 秒內不動作，這個彎也不再調；ACC 反應不如預期（一下跳兩格或沒反應）就整趟停用。panda safety 改為啟用中允許單獨的 −／+。設定 → driving 的「slow down for curves」開關。舊 log 重播（HS route 10、0e、12、13、18，ZS route 05、06）：市區路段沒有誤觸發 | 🔶 | od `7f727772`／`a9f9822c`<br>op `c56715c72`／`dd877c90b` |
| 00:14 | ZS | 改用韌體自動辨識車型，拿掉強制 `FINGERPRINT="MG_ZS"`。朋友 11/15 三次發動（route 05–07）：EPS、相機、雷達都在 bus 0 回應，韌體版本精確比對到 MG_ZS | 🔶 | op `00186a6e8` |

## 2026-11-15

| 時間 | 分支 | 變更 | 狀態 | commit |
|---|---|---|---|---|
| 20:52 | HS、ZS | **導航：可改用自己的 Mapbox token。** route 16 的 log 顯示 comma 的路線 API 在沒有 comma prime 時回 403，所以一直「Waiting for route」。裝置上有 `/data/mapbox_token` 時，navd 改直接跟 Mapbox 要路線（token 只放裝置上，不進 repo）。地圖底圖還是跟 comma 要，可能一樣被擋。11/15 實車（route 19、1a）：路線正常，轉彎提示有中文路名，抵達前會提示（提示句是英文）；地圖底圖確定被擋（`mapsd.render_failed`：拿不到 comma 的圖磚），導航畫面沒有地圖，不影響開車 | ✅ HS（路線） | op `461b28979`／`fa7e019e9` |
| 17:33 | HS、ZS | **修正：踩煞車被當成撥桿取消。** openpilot 常比原廠 ACC 早 0.1–0.2 秒偵測到煞車，會先解除並送出 Cancel，讓 ACC 走撥桿取消的路徑（作用中→Brake Only→待命）。改成踩煞車期間和放開後 1 秒內不送 Cancel，讓 ACC 自己回到待命。11/14 log 重播：5 次煞車原本都送 Cancel，現在都不送。11/15 實車（route 18）：5 次踩煞車解除，ACC 都直接回到待命，沒送 Cancel | ✅ HS | od `13eee668`／`8266c65f`<br>op `09cec5647`／`7e1d542ce` |
| 17:29 | HS、ZS | **儀表 LKA 燈號。** openpilot 送出的轉向訊息原本固定送「LKA 關閉」，儀表燈號不亮。改成 openpilot 控制方向盤時送「作用中」，其他時候照抄原廠相機的值（HS 平常是「待命」）。11/15 實車（route 18）：送「作用中」時 EPS 照常接受扭力，儀表燈號正常亮起、狀態正確（車主確認） | ✅ HS | od `0b5f84a3`／`098e8644`<br>op `d747f3085`／`bb09fe51a` |
| 12:13 | ZS | **修正：Unknown Vehicle Variant。** AEB 判斷不再讀 0x251（`SCS_HSC2_FrP24`）。ZS 沒有這個訊息，讀了會讓 CAN 永遠無效。朋友的 rlog 證實只缺這個訊息。11/15 朋友實車（route 05–07，`8598fbbb5`）：三次發動都沒有 Car Unrecognized，整趟沒有 CAN 錯誤 | ✅ ZS | od `5c725512`<br>op `8598fbbb5` |
| 07:41 | ZS | 巡航按鍵訊息 0x1E1 改為選用，沒收到也不會讓 CAN 無效（不是 Unknown Vehicle Variant 的主因，主因見 12:13） | — | od `07239658`<br>op `bf23cd50d` |
| 07:17 | HS、ZS | openpilot 基底更新：合併 commaai/openpilot master（`cec317f`，2026-11-14） | ✅ | op `b33137f13`／`d88bd149d` |
| 06:08 | HS 專屬 | 扭力參數改用 openpilot 實車學習值 `[0.9, 2.5, 0.19]`（原本 `[1.2, 2.5, 0.22]`）。ZS 維持 `[1.2, 2.5, 0.18]`。11/15 實車（route 18）：時速 30 的急彎都過得去，不會放棄（車主確認） | ✅ HS | od `873c9942`<br>op `21a7544f1` |
| 05:07 | HS、ZS | 車門改讀四個車門的原廠訊號（HS 停車時逐一開關驗證） | ✅ HS | od `1f9c2330`、`e8b5c081`<br>op `5f395f116`、`f33bf9a47` |
| 03:36 | HS、ZS | 解析原廠 AEB／FCW 警示：FCW 任一級警示，AEB 作動時通知 openpilot | 🔶 | od `499611bb`<br>op `84ecd18eb`、`a86760550` |
| 03:11 | HS | 加入 HS／ZS 差異表 `MG_HS_ZS_DIFF.md` | — | op `ff722acd8` |
| 03:06 | ZS | **新增 MG ZS 2025 車型**（`MG_ZS`），沿用 HS 的 ADAS 邏輯和朋友 `mg-zs` 分支的參數；先強制 `FINGERPRINT="MG_ZS"`（11/16 改回自動辨識） | ✅ | od `4fb4f6a4`<br>op `c49751c81` |
| 02:56 | HS、ZS | 解析巡航按鍵事件（SET、RES、加減速、Cancel、車距）；主開關改看 ACC 狀態 | ✅ HS（車距鍵 11/15 route 18 確認：原廠車距 3→2→1；長按加速 11/15 route 19 確認：每 0.2 秒 +1 km/h，30→35；長按減速未測；ZS route 05–07 確認 SET、RES、加減速、Cancel，長按每 0.2 秒 ±1 km/h，短按一次 ±5 km/h） | od `b83cff68`<br>op `62af5bbb3` |

## 2026-11-14

| 時間 | 分支 | 變更 | 狀態 | commit |
|---|---|---|---|---|
| 22:58 | HS 專屬 | 轉向比改用實車資料 16.8 | ✅ | od `8be4c622`<br>op `b1ab37872` |
| 21:38 | HS、ZS | openpilot 解除時，如果原廠 ACC 還開著就送 Cancel（踩煞車的情況在 11/15 17:33 修正） | ✅ 實體 Cancel（HS、ZS） | od `3ffcb4ee`<br>op `13df32ad8` |
| 21:28 | HS | 改用韌體自動辨識車型（只查 bus 0），拿掉強制 `FINGERPRINT` | ✅ 兩次冷啟動 | od `264274e9`<br>op `6f4aa19c9` |
| 20:55 | HS 專屬 | 偵測 EPS 故障（EPS 狀態 3：要求超過 3 Nm 後整趟不再接受扭力） | 🔶 | od `9f00a759`<br>op `e82ba018c` |
| 20:46 | HS、ZS | 停車起步改為短按 RES（按住不放 ACC 不會動作）。11/15 實車（route 18）兩次：雷達發出起步提示後立刻送 RES，約 1 秒起步。ZS 朋友實車（route 05、06）：6 次停車後都自動送 RES 起步 | ✅ HS、ZS | od `f06bda90`<br>op `64d914158` |
| 14:59 | HS、ZS | 修正：轉向扭力變化速度 7／11 沒有生效 | ✅ | od `d1082dcb`<br>op `26397b31a` |
| 14:53 | HS、ZS | 轉向扭力增加／減少速度改為 7／11（ZS 減少速度另外是 8） | ✅ | od `b302e089`<br>op `54ed7c48b` |

## 2026-11-13

| 時間 | 分支 | 變更 | 狀態 | commit |
|---|---|---|---|---|
| 23:32 | HS 專屬 | 方向燈短撥時撥桿訊號只出現一下，改成維持 1 秒 | ✅ | od `b1267eb4`<br>op `9d6ce8a7c` |
| 22:29 | HS、ZS | 停車起步（stop & go）：前車離開後自動送 RES 起步（11/14 20:46 改為短按後實車驗證） | ✅ HS、ZS | od `69f7f7c3`<br>op `a35bce820` |
| 03:19 | HS | 加入實車 ECU 韌體版本號（EPS、相機、雷達） | ✅ | od `f61c6a40`<br>op `56bcfb901` |
| 03:13 | HS、ZS | 新增除錯工具：讀 ECU 韌體版本、找方向燈 CAN 位元 | — | op `9a263fa1f` |
| 02:50 | HS、ZS | 車況改用原 `hs` 分支的讀取方式，不套用 MG 5 EV 的假設 | ✅ | od `2f1e9265`<br>op `d72fa1a3a` |
| 02:41 | HS | 暫時強制 `FINGERPRINT=MG_HS`（11/14 21:28 改回自動辨識） | — | op `4b7efac79` |
| 00:27 | HS | **新增 MG HS PHEV 車型**（`MG_HS`）；openpilot 的 opendbc 改指向 `Mowd/opendbc` `hs-phev` | ✅ | od `4689e670`<br>op `bd7961a04`、`d8e9ce1ae` |
