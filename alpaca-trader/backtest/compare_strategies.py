# -*- coding: utf-8 -*-
"""
Strategie-Vergleich fuer den Alpaca-Bot.
Vergleicht 4 Kandidaten auf Tagesdaten (2010 - heute), inkl. Kosten/Slippage.

Strategien:
  1. Buy & Hold SPY                       (Benchmark)
  2. SMA200-Trendfilter auf SPY           (long wenn Kurs > SMA200, sonst Cash)
  3. RSI-2 Mean Reversion auf SPY         (Connors: Kauf bei RSI2<10 & Kurs>SMA200, Verkauf bei RSI2>65)
  4. Dual Momentum monatlich SPY/QQQ/TLT  (12-Monats-Momentum, bestes Asset; alle negativ -> Cash)

Kosten: 0.05% pro Seite (Alpaca ist kommissionsfrei, das modelliert Slippage/Spread).
"""
import numpy as np
import pandas as pd
import yfinance as yf

COST = 0.0005  # 5 bps pro Trade-Seite
START = "2010-01-01"
TICKERS = ["SPY", "QQQ", "TLT"]


def load_prices():
    # yf.download (Bulk) liefert aktuell leere Daten; Ticker.history funktioniert.
    frames = {}
    for t in TICKERS:
        h = yf.Ticker(t).history(start=START, auto_adjust=True)
        h.index = h.index.tz_localize(None)
        frames[t] = h["Close"]
    close = pd.DataFrame(frames).dropna(how="any")
    return close


def perf_stats(equity, trades_per_year=None):
    ret = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    dd = (equity / equity.cummax() - 1).min()
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0.0
    worst_year = ret.groupby(ret.index.year).apply(lambda r: (1 + r).prod() - 1).min()
    return {
        "CAGR": f"{cagr * 100:6.2f}%",
        "MaxDrawdown": f"{dd * 100:7.2f}%",
        "Sharpe": f"{sharpe:5.2f}",
        "SchlechtestesJahr": f"{worst_year * 100:7.2f}%",
        "Trades/Jahr": f"{trades_per_year:5.1f}" if trades_per_year is not None else "  0.0",
    }


def apply_costs(daily_ret, position):
    """Zieht Kosten ab, wenn sich die Position aendert (Ein-/Ausstieg)."""
    turnover = position.diff().abs().fillna(position.abs())
    return daily_ret - turnover * COST


def strat_buy_hold(close):
    ret = close["SPY"].pct_change().fillna(0)
    equity = (1 + ret).cumprod()
    return equity, 0.0


def strat_sma200(close):
    spy = close["SPY"]
    sma = spy.rolling(200).mean()
    pos = (spy > sma).astype(float).shift(1).fillna(0)  # Signal heute -> Position morgen
    ret = apply_costs(spy.pct_change().fillna(0) * pos, pos)
    equity = (1 + ret).cumprod()
    years = (spy.index[-1] - spy.index[0]).days / 365.25
    n_trades = pos.diff().abs().sum() / 2
    return equity, n_trades / years


def rsi(series, period=2):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def strat_rsi2(close):
    spy = close["SPY"]
    sma200 = spy.rolling(200).mean()
    r = rsi(spy, 2)
    pos = pd.Series(0.0, index=spy.index)
    holding = False
    entry = (r < 10) & (spy > sma200)
    exit_ = r > 65
    entry_arr, exit_arr = entry.to_numpy(), exit_.to_numpy()
    pos_arr = np.zeros(len(spy))
    for i in range(len(spy)):
        if holding:
            if exit_arr[i]:
                holding = False
            else:
                pos_arr[i] = 1.0
        if not holding and entry_arr[i]:
            holding = True
        if holding:
            pos_arr[i] = 1.0
    pos = pd.Series(pos_arr, index=spy.index).shift(1).fillna(0)
    ret = apply_costs(spy.pct_change().fillna(0) * pos, pos)
    equity = (1 + ret).cumprod()
    years = (spy.index[-1] - spy.index[0]).days / 365.25
    n_trades = pos.diff().abs().sum() / 2
    return equity, n_trades / years


def strat_dual_momentum(close):
    monthly = close.resample("ME").last()
    mom = monthly.pct_change(12)
    # Bestes Asset nach 12M-Momentum; wenn alle negativ -> Cash
    daily_ret = close.pct_change().fillna(0)
    pos = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    month_ends = monthly.index
    switches = 0
    last_pick = None
    for i in range(12, len(month_ends) - 1):
        row = mom.iloc[i]
        pick = row.idxmax() if row.max() > 0 else None
        if pick != last_pick:
            switches += 1
            last_pick = pick
        start = month_ends[i]
        end = month_ends[i + 1]
        if pick is not None:
            pos.loc[(pos.index > start) & (pos.index <= end), pick] = 1.0
    strat_ret = (daily_ret * pos).sum(axis=1)
    turnover = pos.diff().abs().sum(axis=1).fillna(0)
    strat_ret = strat_ret - turnover * COST
    equity = (1 + strat_ret).cumprod()
    years = (close.index[-1] - close.index[0]).days / 365.25
    return equity, switches / years


def main():
    close = load_prices()
    print(f"Daten: {close.index[0].date()} bis {close.index[-1].date()}, {len(close)} Handelstage\n")

    results = {}
    for name, fn in [
        ("1. Buy & Hold SPY", strat_buy_hold),
        ("2. SMA200-Trendfilter", strat_sma200),
        ("3. RSI-2 Mean Reversion", strat_rsi2),
        ("4. Dual Momentum (mtl.)", strat_dual_momentum),
    ]:
        equity, tpy = fn(close)
        results[name] = perf_stats(equity, tpy)

    df = pd.DataFrame(results).T
    print(df.to_string())


if __name__ == "__main__":
    main()
