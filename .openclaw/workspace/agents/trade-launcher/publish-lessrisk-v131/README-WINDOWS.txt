LESS RISK NO GLORY — MT5 Helper Setup Package

Professionele Windows package voor semi-auto MT5 execution.

Schone herstart aanbevolen:
1. Sluit MT5.
2. Verwijder oude LRNG helper-bestanden van je Windows machine.
3. Start daarna opnieuw met deze package.

Installatie:
1. Download LRNG-MT5-Helper.exe naar je Windows laptop/VPS waar MT5 op staat.
2. Heb je nog geen MetaTrader 5? Download die dan eerst via:
   https://download.terminal.free/cdn/web/metaquotes.ltd/mt5/mt5setup.exe?utm_source=www.metatrader5.com&utm_campaign=download
3. Start MT5 eerst minimaal 1x en sluit hem daarna weer.
4. Start LRNG-MT5-Helper.exe.
5. Er opent direct een browservenster op http://127.0.0.1:17891 en het terminalvenster blijft open.
6. Klik op Install / refresh MT5 EA.
7. Open MT5 -> Navigator -> Expert Advisors -> Refresh.
8. Sleep LRNG_TradeReceiver op een XAUUSD chart.
9. In de EA settings -> Common: zet Allow Algo Trading aan.
10. Zet ook bovenin MT5 AutoTrading / Algo Trading aan.
11. Laat LRNG-MT5-Helper.exe actief; met autostart-optie start hij automatisch met Windows op achtergrond.
12. Klik in helper op Send test signal.
13. MT5 moet een bevestiging popup tonen. Pas na YES stuurt hij de order.

In deze package:
- LRNG-MT5-Helper.exe
- LRNG_TradeReceiver.ex5
- README-WINDOWS.txt
- QUICK-START.html

Wat is nu gefixt:
- package bevat nu de actuele gecompileerde LRNG_TradeReceiver.ex5
- market vs pending order keuze
- validatie van SL/TP voor ordersend
- check op minimale broker stopafstand
- duidelijkere foutmeldingen bij invalid stops / disabled trading

Telegram signal flow:
- Zonder actieve helper worden signalen niet lokaal opgehaald.
- Telegram signal krijgt knop naar de publieke LRNG signal URL.
- Je lokale Windows helper pollt de server elke 2 seconden.
- Helper schrijft het signaal lokaal naar MT5.
- EA pakt het signaal op en vraagt bevestiging.
- Bij ongeldige setup krijg je nu eerst een duidelijke foutmelding in plaats van een stille misser.

Veiligheid:
- Geen blind auto-trading.
- Standaard lot = 0.5.
- EA gebruikt TP1 als take profit voor executie.
- SL/TP komen uit het signaal en worden eerst gevalideerd.

Uninstall:
- Na installatie staat `Uninstall.exe` in de installatiemap.
- Er komt ook een Start Menu shortcut: `Uninstall LessRisk MT5 Helper`.

UI gedrag:
- Geen zwart terminalvenster meer: dat is nu bewust vervangen door de browserpagina + background helper.
- De zichtbare status/log hoort in de helper-webpagina te staan.
