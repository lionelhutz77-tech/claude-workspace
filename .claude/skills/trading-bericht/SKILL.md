---
name: trading-bericht
description: >-
  Haus-Regeln für Berichte und Analysen des Multi-Agent-Trading-Systems des
  Users (Aktien/Krypto, tägliche Signale). UNBEDINGT verwenden, sobald
  Marktanalysen, Tagesberichte, Signal-Zusammenfassungen oder Dashboard-Texte
  für das Trading-System erstellt oder überarbeitet werden — auch ohne
  ausdrückliche Projektnennung, wenn klar dieser Kontext gemeint ist. Sorgt
  für einheitliche Struktur und ehrliche Einordnung der bekannten
  Daten-Schwächen.
---

# Trading-System — Bericht & Analyse-Regeln

Dieser Skill hält Struktur und Tonalität für die Ausgaben des Trading-Systems fest, damit sie nicht jedes Mal neu erklärt werden müssen. Es geht um die **automatisierten Berichte des eigenen Systems** des Users — die Pipeline rechnet, dieser Skill formt nur die Darstellung.

Kontext: Multi-Agent-System (Stock/Crypto/News/Social → Aggregator → Revision → Bull/Bear → Portfolio-Manager), läuft täglich 08:00. Status/Architektur stehen in `trading-system/PROJEKT.md` — immer dort den aktuellen Stand prüfen.

## Wichtig: keine persönliche Anlageberatung

Die Berichte geben die **berechneten Signale des Systems** wieder (Entry, Target, Stop-Loss, Timing) — als Output eines Werkzeugs, nicht als persönliche Empfehlung. Keine Formulierungen, die als individuelle Finanzberatung gelesen werden könnten. Jeder Bericht endet mit einem kurzen Hinweis: *„Automatisierte Modell-Ausgabe, keine Anlageberatung. Keine Gewähr."*

## Berichtsstruktur (einheitlich)

1. **Kopf**: Datum, Marktlage in 1-2 Sätzen.
2. **Top-Signale**: pro Asset Symbol, Richtung (Kauf/Verkauf/Halten), Entry, Target, Stop-Loss, Zeithorizont, **Konfidenz** und die treibenden Faktoren (welche Agenten/Quellen).
3. **Musterdepot** (1.000 EUR): aktuelle Positionen, Veränderung, kapitalgewichtete Verteilung.
4. **Backtest-Kontext**: historische Trefferquote zum Signaltyp, falls vorhanden.
5. **Unsicherheiten/Caveats** (siehe unten) — nie weglassen.

## Ehrliche Einordnung — bekannte Schwächen immer mitnennen

Konfidenz nie überzeichnen. Wenn relevant, transparent machen:
- Bull/Bear-Debatte nutzt **dasselbe Modell** → keine echte Unabhängigkeit.
- News-Sentiment ist **keyword-basiert**, nicht semantisch.
- StockTwits liefert oft ~50/50 → schwaches Social-Signal.
- Krypto-Symbole CoinGecko ↔ Yahoo Finance nicht immer kompatibel (Datenlücken möglich).
- Bei dünner Datenlage Signal als „schwach/unsicher" kennzeichnen statt forciert zu werten.

## Technik

- KI-Revision/Texte über Groq (`llama-3.3-70b-versatile`). Groq-Tageslimit (~100k Token) beachten — bei intensivem Lauf kann es erschöpft sein; dann darauf hinweisen statt still zu scheitern.
- Sprache: Deutsch, „du"-Form, sachlich-nüchtern.
