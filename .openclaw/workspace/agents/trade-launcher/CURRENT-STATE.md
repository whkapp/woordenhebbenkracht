# LRNG MT5 Trade Launcher — Current State

_Last compacted: 2026-05-11 10:01 UTC_

Purpose: keep this as the first file to read for LRNG/MT5 questions so future turns do **not** need long chat history.

## Operational status
- MT5 helper + Telegram signal link flow is proven working.
- BUY and SELL execution were both tested successfully after the EA was compiled/loaded correctly.
- Earlier `invalid stops` errors were caused by stale/out-of-range TP/SL relative to live price, not by Telegram delivery.
- If SELL fails with invalid stops: TP is likely above current Bid; for SELL, TP must be below current price and SL above.
- If BUY fails with invalid stops: TP is likely below current Ask; for BUY, TP must be above current price and SL below.

## Important deployment lesson
- Do **not** compile MQ5 from a ZIP/Temp/Downloads path.
- Correct compile path is the MT5 data folder:
  `%APPDATA%\\MetaQuotes\\Terminal\\<terminal-id>\\MQL5\\Experts\\LRNG_TradeReceiver.mq5`
- After F7 compile, `LRNG_TradeReceiver.ex5` must appear in the same `MQL5\\Experts` folder.
- Then in MT5: Navigator → Expert Advisors → Refresh → remove old EA from chart → attach EA again.

## Latest packaging / downloads
- Public server download path used for final zip:
  `https://projects.doodsbang.nl/websites/LRNG-MT5-Helper-Windows-final.zip`
- Daily memory may contain newer broadcast/ForceLot packages; check `memory/2026-05-11.md` before packaging again.

## Current code areas
- Helper/source/package folder: `agents/trade-launcher/`
- Signal server: `agents/trade-launcher/lrng-signup-server.js`
- EA source: `agents/trade-launcher/LRNG_TradeReceiver.mq5`
- Helper source: `agents/trade-launcher/lrng_mt5_helper.cpp`
- Telegram signal sender: `agents/send-dual-market-whatsapp.py`

## Token-saving rule
For LRNG/MT5 questions, read this file first, then only inspect the specific file/log needed. Avoid pulling full chat history unless absolutely required.
## Next upgrade in progress
- EA source `LRNG_TradeReceiver.mq5` is upgraded toward a custom chart execution panel instead of the old `MessageBox` confirm.
- New flow target: show BUY/SELL, mode, entry, SL, TP1/TP2/TP3, lot, and Execute/Skip buttons directly on the MT5 chart.
- This source change still needs compilation into a fresh `.ex5` on the Windows/MT5 side before it is live in the installer flow.

- Received compiled `LRNG_TradeReceiver.ex5` for v1.30 (custom chart execution panel build), size 57,046 bytes, SHA256 `479c023f4fb616f83dc7b528f99e032da56ffeb8a70cd607ff40b587c604273c`. Re-embedded it into `lrng_ea_ex5.h`, rebuilt `LRNG-MT5-Helper.exe`, rebuilt `LessRisk_Installer_v1.exe`, and refreshed `LessRisk_Installerv1.zip`.
- Received compiled `LRNG_TradeReceiver.ex5` for v1.31 (inline chart status/error panel build), size 60,196 bytes, SHA256 `3ce0846e7921eecf6156ce796b895a4c73227b78cbe42b5499330b57d8fc00ce`. Re-embedded it into `lrng_ea_ex5.h`, rebuilt `LRNG-MT5-Helper.exe`, rebuilt `LessRisk_Installer_v1.exe`, and refreshed `LessRisk_Installerv1.zip`.
- Verified on 2026-05-11 that older artifact `dist-release/LRNG-MT5-Helper-Final-2026-05-11.zip` was stale (older helper + older `.ex5`). Built and published corrected package `dist-release/LessRisk-MT5-Helper-v131-2026-05-11.zip` plus `LessRisk_Installer_v1.exe` to `https://servermac.doodsbang.nl/lessrisk/`.
