"""
Backtesting-Agent
Simuliert vergangene Kaufsignale unseres Systems und berechnet:
  - Trefferquote (wie oft lag das Signal richtig)
  - Durchschnittlicher Gewinn/Verlust pro Trade
  - Bestes / schlechtestes Asset
  - Sharpe Ratio (Rendite relativ zum Risiko)

Methode: Wir berechnen rueckwirkend RSI+MACD-Signale fuer die letzten
90 Tage und pruefen ob ein Kauf bei Signal zu +10% Ziel oder -5% Stop-Loss
gefuehrt haette.
"""

import sys
import time
from dataclasses import dataclass, field

import yfinance as yf
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Datenstruktur
# ---------------------------------------------------------------------------

@dataclass
class BacktestTrade:
    datum_einstieg: str
    preis_einstieg: float
    preis_ziel: float
    preis_stop: float
    datum_ausgang: str
    preis_ausgang: float
    ergebnis: str          # "GEWINN", "VERLUST", "OFFEN"
    rendite_pct: float


@dataclass
class BacktestErgebnis:
    asset: str
    zeitraum_tage: int
    trades_gesamt: int
    trades_gewinn: int
    trades_verlust: int
    trefferquote_pct: float
    durchschn_rendite_pct: float
    gesamt_rendite_pct: float
    bester_trade_pct: float
    schlechtester_trade_pct: float
    sharpe_ratio: float
    trades: list[BacktestTrade] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Indikatoren (kopiert aus stock_analyst, unabhaengig nutzbar)
# ---------------------------------------------------------------------------

def _berechne_signale(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet RSI, MACD und generiert Kauf-Signaltage."""
    # Moving Averages
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    # RSI
    delta = df["Close"].diff()
    g = delta.clip(lower=0).rolling(14).mean()
    v = (-delta.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + g / v))

    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # Kaufsignal: RSI < 70, MACD > Signal, Preis > MA20 > MA50
    df["Kaufsignal"] = (
        (df["RSI"] < 70) &
        (df["MACD"] > df["MACD_Signal"]) &
        (df["Close"] > df["MA20"]) &
        (df["MA20"]  > df["MA50"])
    )

    return df


# ---------------------------------------------------------------------------
# Trade-Simulation
# ---------------------------------------------------------------------------

def _simuliere_trade(
    df: pd.DataFrame,
    einstieg_idx: int,
    ziel_pct: float = 0.10,
    stop_pct: float = 0.05,
    max_haltezeit: int = 20,
) -> BacktestTrade:
    """
    Simuliert einen Trade ab einstieg_idx.
    Beendet wenn Ziel, Stop oder max_haltezeit erreicht.
    """
    einstieg_preis = float(df["Close"].iloc[einstieg_idx])
    ziel_preis     = einstieg_preis * (1 + ziel_pct)
    stop_preis     = einstieg_preis * (1 - stop_pct)
    einstieg_datum = str(df.index[einstieg_idx].date())

    ausgang_idx    = min(einstieg_idx + max_haltezeit, len(df) - 1)
    ausgang_preis  = float(df["Close"].iloc[ausgang_idx])
    ausgang_datum  = str(df.index[ausgang_idx].date())
    ergebnis       = "OFFEN"

    for i in range(einstieg_idx + 1, min(einstieg_idx + max_haltezeit + 1, len(df))):
        hoch  = float(df["High"].iloc[i])  if "High"  in df.columns else float(df["Close"].iloc[i])
        tief  = float(df["Low"].iloc[i])   if "Low"   in df.columns else float(df["Close"].iloc[i])
        datum = str(df.index[i].date())

        if hoch >= ziel_preis:
            ausgang_preis = ziel_preis
            ausgang_datum = datum
            ergebnis      = "GEWINN"
            break
        if tief <= stop_preis:
            ausgang_preis = stop_preis
            ausgang_datum = datum
            ergebnis      = "VERLUST"
            break

    rendite = (ausgang_preis - einstieg_preis) / einstieg_preis * 100

    return BacktestTrade(
        datum_einstieg=einstieg_datum,
        preis_einstieg=round(einstieg_preis, 2),
        preis_ziel=round(ziel_preis, 2),
        preis_stop=round(stop_preis, 2),
        datum_ausgang=ausgang_datum,
        preis_ausgang=round(ausgang_preis, 2),
        ergebnis=ergebnis,
        rendite_pct=round(rendite, 2),
    )


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

def backtest_asset(
    ticker: str,
    zeitraum_tage: int = 90,
    ziel_pct: float   = 0.10,
    stop_pct: float   = 0.05,
    ist_krypto: bool  = False,
) -> BacktestErgebnis:
    """Fuehrt den vollstaendigen Backtest fuer ein Asset durch."""

    # Daten laden
    if ist_krypto:
        from crypto_analyst import lade_kursdaten as lade_krypto, berechne_indikatoren
        df = lade_krypto(ticker, tage=zeitraum_tage + 60)
        df = berechne_indikatoren(df)
        df["Kaufsignal"] = (
            (df["RSI"] < 70) &
            (df["MACD"] > df["MACD_Signal"]) &
            (df["Close"] > df["MA20"])
        )
    else:
        aktie = yf.Ticker(ticker)
        df    = aktie.history(period=f"{zeitraum_tage + 60}d")
        df    = _berechne_signale(df)

    # Nur letzten Zeitraum betrachten
    df = df.iloc[-(zeitraum_tage):]
    df = df.dropna()

    if df.empty:
        return BacktestErgebnis(
            asset=ticker, zeitraum_tage=zeitraum_tage,
            trades_gesamt=0, trades_gewinn=0, trades_verlust=0,
            trefferquote_pct=0, durchschn_rendite_pct=0,
            gesamt_rendite_pct=0, bester_trade_pct=0,
            schlechtester_trade_pct=0, sharpe_ratio=0,
        )

    # Trades simulieren (kein Überlappung — warte nach jedem Trade)
    trades      = []
    naechster_i = 0

    for i, (datum, row) in enumerate(df.iterrows()):
        if i < naechster_i:
            continue
        if row.get("Kaufsignal", False):
            trade = _simuliere_trade(df, i, ziel_pct, stop_pct)
            trades.append(trade)
            # Naechsten Trade erst nach Abschluss dieses Trades
            tage_gehalten = (pd.to_datetime(trade.datum_ausgang) -
                             pd.to_datetime(trade.datum_einstieg)).days
            naechster_i = i + max(tage_gehalten, 1) + 1

    if not trades:
        return BacktestErgebnis(
            asset=ticker, zeitraum_tage=zeitraum_tage,
            trades_gesamt=0, trades_gewinn=0, trades_verlust=0,
            trefferquote_pct=0, durchschn_rendite_pct=0,
            gesamt_rendite_pct=0, bester_trade_pct=0,
            schlechtester_trade_pct=0, sharpe_ratio=0,
            trades=[],
        )

    renditen        = [t.rendite_pct for t in trades]
    gewinn_trades   = [t for t in trades if t.ergebnis == "GEWINN"]
    verlust_trades  = [t for t in trades if t.ergebnis == "VERLUST"]
    trefferquote    = len(gewinn_trades) / len(trades) * 100
    durchschn       = float(np.mean(renditen))
    gesamt          = float(np.sum(renditen))
    std             = float(np.std(renditen)) if len(renditen) > 1 else 1.0
    sharpe          = round(durchschn / std, 2) if std > 0 else 0.0

    return BacktestErgebnis(
        asset=ticker,
        zeitraum_tage=zeitraum_tage,
        trades_gesamt=len(trades),
        trades_gewinn=len(gewinn_trades),
        trades_verlust=len(verlust_trades),
        trefferquote_pct=round(trefferquote, 1),
        durchschn_rendite_pct=round(durchschn, 2),
        gesamt_rendite_pct=round(gesamt, 2),
        bester_trade_pct=round(max(renditen), 2),
        schlechtester_trade_pct=round(min(renditen), 2),
        sharpe_ratio=sharpe,
        trades=trades,
    )


def backtest_alle(
    aktien:  list[str] = None,
    kryptos: list[str] = None,
    zeitraum_tage: int = 90,
) -> list[BacktestErgebnis]:
    """Fuehrt Backtest fuer alle Assets durch und gibt sortierte Ergebnisse zurueck."""
    aktien  = aktien  or ["MSFT", "NVDA", "TSLA", "AAPL", "AMZN"]
    kryptos = kryptos or ["BTC", "ETH"]
    alle    = []

    for ticker in aktien:
        print(f"  Backtest {ticker} ...", end=" ", flush=True)
        try:
            e = backtest_asset(ticker, zeitraum_tage)
            alle.append(e)
            print(f"OK  ({e.trades_gesamt} Trades, {e.trefferquote_pct:.0f}% Trefferquote)")
        except Exception as ex:
            print(f"FEHLER: {ex}")

    for symbol in kryptos:
        print(f"  Backtest {symbol} ...", end=" ", flush=True)
        try:
            e = backtest_asset(symbol, zeitraum_tage, ist_krypto=True)
            alle.append(e)
            print(f"OK  ({e.trades_gesamt} Trades, {e.trefferquote_pct:.0f}% Trefferquote)")
            time.sleep(3)
        except Exception as ex:
            print(f"FEHLER: {ex}")

    # Sortiert nach Trefferquote absteigend
    alle.sort(key=lambda x: x.trefferquote_pct, reverse=True)
    return alle


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------

def drucke_backtest(e: BacktestErgebnis):
    breite = 62
    print("\n" + "=" * breite)
    print(f"  BACKTEST: {e.asset}  ({e.zeitraum_tage} Tage)")
    print("=" * breite)
    if e.trades_gesamt == 0:
        print("  Keine Trades im Zeitraum gefunden.")
        return
    print(f"  Trades gesamt    : {e.trades_gesamt}")
    print(f"  Gewinn / Verlust : {e.trades_gewinn} / {e.trades_verlust}")
    print(f"  Trefferquote     : {e.trefferquote_pct:.1f}%")
    print(f"  Ø Rendite/Trade  : {e.durchschn_rendite_pct:+.2f}%")
    print(f"  Gesamt-Rendite   : {e.gesamt_rendite_pct:+.2f}%")
    print(f"  Bester Trade     : {e.bester_trade_pct:+.2f}%")
    print(f"  Schlechtester    : {e.schlechtester_trade_pct:+.2f}%")
    print(f"  Sharpe Ratio     : {e.sharpe_ratio:+.2f}")
    if e.trades:
        print(f"\n  Letzte {min(3, len(e.trades))} Trades:")
        for t in e.trades[-3:]:
            symbol = "✓" if t.ergebnis == "GEWINN" else ("✗" if t.ergebnis == "VERLUST" else "~")
            print(f"    {symbol} {t.datum_einstieg}  ${t.preis_einstieg:,.2f}"
                  f"  ->  ${t.preis_ausgang:,.2f}  ({t.rendite_pct:+.1f}%)")
    print("=" * breite)


def drucke_zusammenfassung(ergebnisse: list[BacktestErgebnis]):
    print("\n" + "#" * 62)
    print("  BACKTEST-ZUSAMMENFASSUNG")
    print("#" * 62)
    print(f"  {'Asset':<8} {'Trades':>6} {'Treffer':>8} {'Ø Rendite':>10} {'Sharpe':>8}")
    print("  " + "-" * 50)
    for e in ergebnisse:
        if e.trades_gesamt == 0:
            continue
        print(f"  {e.asset:<8} {e.trades_gesamt:>6} "
              f"{e.trefferquote_pct:>7.0f}% "
              f"{e.durchschn_rendite_pct:>+9.2f}% "
              f"{e.sharpe_ratio:>+8.2f}")
    print("#" * 62)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print("Trading Intelligence System — Backtesting-Agent")
    print("Simuliere letzte 90 Tage...\n")

    ergebnisse = backtest_alle(
        aktien  = ["MSFT", "NVDA", "TSLA", "AAPL"],
        kryptos = ["BTC", "ETH"],
        zeitraum_tage = 90,
    )

    for e in ergebnisse:
        drucke_backtest(e)

    drucke_zusammenfassung(ergebnisse)
