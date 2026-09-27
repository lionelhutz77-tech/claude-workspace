# Vorregistrierte 10.000-€-Testserie

Start: 21.09.2026. Vier **alternative virtuelle Depots** mit je 10.000 €
Startwert. Sie testen vier Verwendungen desselben gedachten Budgets; es werden
weder 40.000 € reales Kapital benötigt noch echte Orders an Alpaca oder einen
anderen Broker gesendet. Die fünf bisherigen 1.000-€-Depots bleiben unverändert.

Startnachweis: 13 heute protokollierte Signale wurden geprüft. Zwei finale
Krypto-Kaufsignale (ETH, SOL) sind im KONSENS-Arm vorgemerkt; die anderen Arme
hatten nach ihren festgelegten Filtern keinen Kandidaten. Noch keine Position
ist eröffnet, daher stehen alle vier Depots zunächst bei 10.000 € Cash.
Der lokale Task `TradingIntelligenceSystem` war am 21.09.2026 erfolgreich,
ist aktiviert und hat den nächsten Lauf am 22.09.2026 um 08:00 Uhr. Dieser
Lauf nutzt die geänderten lokalen Dateien. Die separate GitHub-Actions-Fassung
ist noch nicht mit diesen uncommitteten lokalen Änderungen synchronisiert.

## Feste Strategiearme

Alle Arme sehen dieselben täglichen Aktien- und Krypto-Signale des
Trading-Intelligence-Systems. Nur finale `KAUFEN`-Voten werden berücksichtigt.
Instrumenttyp und Kurswährung werden getrennt gespeichert; ein Krypto-Ticker
darf nicht versehentlich als gleichnamige Aktie bewertet werden.

| Arm | Vorregistrierte Auswahl |
|---|---|
| KONSENS | Bis zu fünf finale Kaufsignale, nach Gesamtpunktzahl |
| MOMENTUM | Finale Kaufsignale mit 5-Tage-Momentum > 2 und RSI 50–<70 |
| VALUE | Finale Kaufsignale mit RSI > 0 und < 40 |
| TAILWIND | Finale Kaufsignale mit starkem Tailwind-Scanner-Signal |

Fehlende oder ungültige Kennzahlen gelten nicht als erfülltes Kriterium.
Kein Arm wird während der ersten Auswertungsperiode nachträglich optimiert.

## Ausführung und Kontrolle

- Das Signal wird zunächst mit Zeitpunkt und kompakten Eingabefaktoren
  gespeichert. Es wird **nicht** zum bereits bekannten Signalpreis gekauft.
- Frühestens ein später beobachteter Yahoo-Finance-Kurs führt die virtuelle
  Order aus. Aktienkurse werden nur mit belegter EUR-/USD-Währung verwendet;
  USD wird mit einem beobachteten USD/EUR-Kurs umgerechnet. Unbekannte Währung,
  fehlender, veralteter oder zukünftiger Kurs blockiert die Ausführung.
- Eine offene Order verfällt nach drei Kalendertagen. Jede Position ist auf
  2.000 € begrenzt, ohne Fremdkapital und ohne Short-Positionen.
- 0,2 % Kosten-/Slippage-Abschlag auf jeder Seite. Virtueller Exit am später
  beobachteten Kurs bei etwa +10 %, −7 % oder nach 20 Kalendertagen. Stop/Ziel
  sind **keine garantierten Ausführungspreise**; Gaps können das Ergebnis ändern.
- Doppelte Tagesläufe sind idempotent. Fehlende Kurse werden sichtbar und
  verhindern eine vermeintlich exakte Depotbewertung.
- Zustand: eigene Tabellen (`portfolios`, `orders`, `positions`, `snapshots`,
  `runs`) in der bereits täglich gesicherten `data/multi_depot.db`. Die alten
  Tabellen (`depots`, `positionen`, `verlauf`) bleiben getrennt und unverändert.
  Bericht: `output/experiment_10000_aktuell.html`; beim nächsten vollständigen
  Tageslauf erscheint die Testserie zusätzlich im regulären Dashboard.

## Bewertung

Erster Zwischenblick ab 19.10.2026. Kein Gewinnerurteil allein aus der
Trefferquote: verglichen werden Netto-Rendite, realisierter Gewinn/Verlust,
Trefferquote **mit Fallzahl**, größter beobachteter Rückgang, offene Positionen,
Liquiditätsanteil und fehlende Kurse. Eine belastbarere Rangfolge setzt
mindestens 20 geschlossene Trades je Arm und mehrere Marktphasen voraus.
Cash-Halten kann kurzfristig führen, ohne dass die Auswahlstrategie dadurch
überlegen wäre. Alle Ergebnisse sind hypothetisch und keine Prognose.

## Neue Videohypothesen vom 21.09.2026 – nicht Teil dieses Zyklus

Reels zu Robinhood-Agenten, Bybit-Krypto-Shorts und einem „Quant-System“ mit
43/55 Gewinnern liefern weder vollständige Verlustlisten noch Zeit-/Kosten-
Belege. Robinhoods Agenten-MCP kann echte Orders ausführen und wird nicht
verbunden. Die vier oben vorregistrierten Paper-Arme werden nicht nachträglich
geändert. Für den nächsten Zyklus ist höchstens ein separater Shadow-Arm
denkbar: jedes Signal vor dem Ergebnis mit Zeit, Richtung, Instrument, Regel,
Kostenannahme und Benchmark versiegeln; danach alle Gewinner **und** Verlierer
auswerten. Quelle: `PICTURES-AUDIT-2026-09-21.md`.

Automatisierte Modell-Ausgabe, keine Anlageberatung. Keine Gewähr.
