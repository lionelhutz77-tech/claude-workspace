"""
Universe Scanner
Laedt alle S&P 500 Aktien (500 Titel), fuehrt einen schnellen
technischen Vorfilter durch und gibt die Top-N Kandidaten zurueck.

Ablauf:
  1. S&P 500 Ticker-Liste von Wikipedia laden (kein API-Key)
  2. Alle Kurse in einem Batch-Download holen (yfinance bulk)
  3. RSI, MACD, Trend fuer jeden Titel berechnen
  4. Nach Signal-Staerke sortieren
  5. Top N zurueckgeben fuer volle KI-Analyse
"""

import sys
import time
import warnings
warnings.filterwarnings("ignore")

import yfinance as yf
import pandas as pd
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# S&P 500 Ticker-Liste
# ---------------------------------------------------------------------------

def lade_sp500_ticker() -> list[str]:
    """
    Laedt alle S&P 500 Ticker.
    Versucht drei Quellen der Reihe nach:
      1. yfinance S&P 500 Index-Bestandteile (direkter API-Aufruf)
      2. Wikipedia (HTML-Scraping mit Browser-Header)
      3. Eingebettete vollstaendige Liste als Fallback
    """
    # Versuch 1: yfinance — S&P 500 via ^GSPC Bestandteile
    try:
        sp500 = yf.Ticker("^GSPC")
        # Alle im Index enthaltenen Titel ueber yfinance Screener
        import json, urllib.request
        url   = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&scrIds=most_actives&count=500"
        headers = {"User-Agent": "Mozilla/5.0"}
        req   = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            daten = json.loads(r.read())
        ticker = [q["symbol"] for q in daten["finance"]["result"][0]["quotes"]]
        if len(ticker) >= 100:
            print(f"    {len(ticker)} Titel geladen (Yahoo Finance Screener).")
            return ticker
    except Exception:
        pass

    # Versuch 2: Wikipedia mit Browser-Header
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp    = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers=headers, timeout=15
        )
        tables = pd.read_html(resp.text, attrs={"id": "constituents"})
        ticker = [t.replace(".", "-") for t in tables[0]["Symbol"].tolist()]
        if len(ticker) >= 400:
            print(f"    {len(ticker)} S&P 500 Titel geladen (Wikipedia).")
            return ticker
    except Exception:
        pass

    # Versuch 3: Vollstaendige eingebettete Liste (alle 503 S&P 500 Titel, Stand 2025)
    print("    Nutze eingebettete vollstaendige S&P 500 Liste (503 Titel).")
    return [
        "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","A","APD","ABNB","AKAM",
        "ALB","ARE","ALGN","ALLE","LNT","ALL","GOOGL","GOOG","MO","AMZN","AMCR","AEE",
        "AEP","AXP","AIG","AMT","AWK","AMP","AME","AMGN","APH","ADI","ANSS","AON","APA",
        "AAPL","AMAT","APTV","ACGL","ADM","ANET","AJG","AIZ","T","ATO","ADSK","ADP",
        "AZO","AVB","AVY","AXON","BKR","BALL","BAC","BK","BBWI","BAX","BDX","WRB","BBY",
        "BIO","TECH","BIIB","BLK","BX","BA","BKNG","BWA","BSX","BMY","AVGO","BR","BRO",
        "BF-B","BLDR","BG","CDNS","CZR","CPT","CPB","COF","CAH","KMX","CCL","CARR","CTLT",
        "CAT","CBOE","CBRE","CDW","CE","COR","CNC","CNP","CF","CHRW","CRL","SCHW","CHTR",
        "CVX","CMG","CB","CHD","CI","CINF","CTAS","CSCO","C","CFG","CLX","CME","CMS","KO",
        "CTSH","CL","CMCSA","CAG","COP","ED","STZ","CEG","COO","CPRT","GLW","CPAY","CTVA",
        "CSGP","COST","CTRA","CRWD","CCI","CSX","CMI","CVS","DHR","DRI","DVA","DAY","DECK",
        "DE","DELL","DAL","DVN","DXCM","FANG","DLR","DFS","DG","DLTR","D","DPZ","DOV",
        "DOW","DHI","DTE","DUK","DD","EMN","ETN","EBAY","ECL","EIX","EW","EA","ELV","LLY",
        "EMR","ENPH","ETR","EOG","EPAM","EQT","EFX","EQIX","EQR","ESS","EL","ETSY","EG",
        "EVRG","ES","EXC","EXPE","EXPD","EXR","XOM","FFIV","FDS","FICO","FAST","FRT","FDX",
        "FIS","FITB","FSLR","FE","FI","FMC","F","FTNT","FTV","FOXA","FOX","BEN","FCX",
        "GRMN","IT","GE","GEHC","GEV","GEN","GNRC","GD","GIS","GM","GPC","GILD","GS",
        "HAL","HIG","HAS","HCA","DOC","HSIC","HSY","HES","HPE","HLT","HOLX","HD","HON",
        "HRL","HST","HWM","HPQ","HUBB","HUM","HBAN","HII","IBM","IEX","IDXX","ITW","INCY",
        "IR","PODD","INTC","ICE","IFF","IP","IPG","INTU","ISRG","IVZ","INVH","IQV","IRM",
        "JBHT","JBL","JKHY","J","JNJ","JCI","JPM","JNPR","K","KVUE","KDP","KEY","KEYS",
        "KMB","KIM","KMI","KLAC","KHC","KR","LHX","LH","LRCX","LW","LVS","LDOS","LEN",
        "LII","LIN","LYV","LKQ","LMT","L","LOW","LULU","LYB","MTB","MRO","MPC","MKTX",
        "MAR","MMC","MLM","MAS","MA","MTCH","MKC","MCD","MCK","MDT","MRK","META","MET",
        "MTD","MGM","MCHP","MU","MSFT","MAA","MRNA","MHK","MOH","TAP","MDLZ","MPWR",
        "MNST","MCO","MS","MOS","MSI","MSCI","NDAQ","NTAP","NEE","NKE","NEM","NWSA","NWS",
        "NFLX","NI","NDSN","NSC","NTRS","NOC","NCLH","NRG","NUE","NVDA","NVR","NXPI",
        "ORLY","OXY","ODFL","OMC","ON","OKE","ORCL","OTIS","PCAR","PKG","PANW","PH","PAYX",
        "PAYC","PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW","PNC","POOL","PPG","PPL",
        "PFG","PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","QRVO","PWR","QCOM","DGX",
        "RL","RJF","RTX","O","REG","REGN","RF","RSG","RMD","RVTY","ROK","ROL","ROP","ROST",
        "RCL","SPGI","CRM","SBAC","SLB","STX","SRE","NOW","SHW","SPG","SWKS","SJM","SW",
        "SNA","SOLV","SO","LUV","SWK","SBUX","STT","STLD","STE","SYK","SMCI","SYF","SNPS",
        "SYY","TMUS","TROW","TTWO","TPR","TRGP","TGT","TEL","TDY","TFX","TER","TSLA","TXN",
        "TXT","TMO","TJX","TSCO","TT","TDG","TRV","TRMB","TFC","TYL","TSN","USB","UBER",
        "UDR","ULTA","UNP","UAL","UPS","URI","UNH","UHS","VLO","VTR","VLTO","VRSN","VRSK",
        "VZ","VRTX","VTRS","VICI","V","VST","VMC","WRK","WAB","WBA","WMT","DIS","WBD",
        "WM","WAT","WEC","WFC","WELL","WST","WDC","WY","WHR","WMB","WTW","GWW","WYNN",
        "XEL","XYL","YUM","ZBRA","ZBH","ZTS",
    ]


# ---------------------------------------------------------------------------
# Top-50 Krypto-Liste (dynamisch via CoinGecko)
# ---------------------------------------------------------------------------

def _netzwerk_verfuegbar(host: str = "8.8.8.8", port: int = 53, timeout: int = 5) -> bool:
    """Prueft ob Internetzugang vorhanden ist."""
    import socket
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception:
        return False


def lade_top_kryptos(anzahl: int = 50) -> list[dict]:
    """
    Laedt die Top-N Kryptos nach Marktkapitalisierung von CoinGecko.
    Gibt eine Liste mit id, symbol, name und aktuellem Preis zurueck.
    Kein API-Key noetig.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency":           "usd",
        "order":                 "market_cap_desc",
        "per_page":              anzahl,
        "page":                  1,
        "sparkline":             False,
        "price_change_percentage": "24h",
    }

    # Stablecoins ausschliessen (kein Handelssignal sinnvoll)
    # Stablecoins + illiquide/obskure Tokens ausschliessen
    STABLECOINS = {
        "USDT","USDC","DAI","BUSD","TUSD","USDP","FRAX","GUSD","LUSD","USDD",
        "PYUSD","USDG","USDS","USDE","USD1","USDY","USDX","RLUSD","FDUSD",
        "WBTC","WETH","STETH","CBBTC",  # Wrapped tokens — kein eigenes Signal
    }

    # Netzwerk-Check
    if not _netzwerk_verfuegbar():
        print("    Kein Netzwerk — nutze Basis-Krypto-Liste.")
        return [
            {"symbol": s, "id": s.lower(), "name": s, "preis": 0, "change_24h": 0, "marktkapitalisierung": 0}
            for s in ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","LINK"]
        ]

    for versuch in range(3):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                time.sleep(15 * (versuch + 1))
                continue
            resp.raise_for_status()
            coins = resp.json()
            MIN_MARKTKAPITALISIERUNG = 500_000_000  # 500 Mio. USD
            ergebnis = []
            for coin in coins:
                symbol = coin["symbol"].upper()
                if symbol in STABLECOINS:
                    continue
                if coin.get("market_cap", 0) < MIN_MARKTKAPITALISIERUNG:
                    continue
                ergebnis.append({
                    "symbol":       symbol,
                    "id":           coin["id"],
                    "name":         coin["name"],
                    "preis":        coin["current_price"],
                    "change_24h":   coin.get("price_change_percentage_24h", 0),
                    "marktkapitalisierung": coin.get("market_cap", 0),
                })
            print(f"    {len(ergebnis)} Kryptos geladen (CoinGecko Top {anzahl}).")
            return ergebnis
        except Exception as e:
            print(f"    CoinGecko Fehler: {e}")
            time.sleep(10)

    # Fallback
    print("    CoinGecko nicht erreichbar — nutze Basis-Krypto-Liste.")
    return [
        {"symbol": s, "id": s.lower(), "name": s, "preis": 0, "change_24h": 0, "marktkapitalisierung": 0}
        for s in ["BTC","ETH","BNB","SOL","XRP","ADA","AVAX","DOGE","DOT","MATIC",
                  "LINK","UNI","ATOM","LTC","BCH","XLM","ALGO","VET","SAND","MANA"]
    ]


def scanne_kryptos(anzahl: int = 50) -> list[dict]:
    """
    Holt Top-N Kryptos und bewertet sie technisch.
    Gibt Top-10 Kandidaten zurueck.
    """
    kryptos = lade_top_kryptos(anzahl)
    ergebnisse = []

    print(f"    Technische Bewertung fuer {len(kryptos)} Kryptos...")
    for i, coin in enumerate(kryptos):
        symbol = coin["symbol"]
        # CoinGecko-Symbol -> yfinance Symbol
        yf_symbol = f"{symbol}-USD"
        try:
            ticker = yf.Ticker(yf_symbol)
            hist   = ticker.history(period="3mo")
            if hist.empty or len(hist) < 20:
                continue
            bewertung = _schnell_bewerte(hist)
            if bewertung and bewertung["score"] >= 3:
                ergebnisse.append({
                    "ticker":   symbol,
                    "name":     coin["name"],
                    "change_24h": coin["change_24h"],
                    **bewertung,
                })
        except Exception:
            continue

        if i % 10 == 9:
            time.sleep(2)   # Rate-Limit schonen

    ergebnisse.sort(key=lambda x: x["score"], reverse=True)
    print(f"    {len(ergebnisse)} Krypto-Kandidaten gefunden.")
    return ergebnisse[:10]


# ---------------------------------------------------------------------------
# Schnelle technische Bewertung
# ---------------------------------------------------------------------------

def _schnell_bewerte(df: pd.DataFrame) -> dict:
    """
    Berechnet RSI, MACD, Trend und gibt einen Score (0-10) zurueck.
    Schnell und effizient — kein KI-Aufruf.
    """
    if df is None or len(df) < 30:
        return None

    close = df["Close"].dropna()
    if len(close) < 30:
        return None

    # Volumen-Plausibilitaet: mindestens 10 Tage mit Umsatz
    if "Volume" in df.columns:
        vol = df["Volume"].dropna()
        if (vol > 0).sum() < 10:
            return None  # Zu illiquide

    # Moving Averages
    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else ma20
    preis = float(close.iloc[-1])

    # RSI
    delta = close.diff()
    g     = delta.clip(lower=0).rolling(14).mean()
    v     = (-delta.clip(upper=0)).rolling(14).mean()
    rsi_s = 100 - (100 / (1 + g / v))
    rsi   = float(rsi_s.iloc[-1])
    if rsi != rsi or rsi >= 95 or rsi <= 5:
        return None  # RSI ausserhalb plausibler Range — duenner Markt

    # MACD
    ema12        = close.ewm(span=12, adjust=False).mean()
    ema26        = close.ewm(span=26, adjust=False).mean()
    macd         = float((ema12 - ema26).iloc[-1])
    macd_signal  = float((ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1])

    # 5-Tage-Momentum
    momentum_5d = float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 5 else 0

    # Scoring (0 = schwach, 10 = stark)
    score = 0

    if 40 < rsi < 65:      score += 2   # RSI im gesunden Bereich
    elif rsi < 35:         score += 1   # ueberverkauft — Erholungspotenzial
    elif rsi > 75:         score -= 1   # ueberkauft

    if macd > macd_signal: score += 2   # MACD bullish
    if preis > ma20:       score += 2   # Ueber kurzfristigem MA
    if ma20 > ma50:        score += 1   # Aufwaertstrend
    if momentum_5d > 1:    score += 1   # Positives kurzfristiges Momentum
    elif momentum_5d < -3: score -= 1

    return {
        "preis":       round(preis,       2),
        "rsi":         round(rsi,         1),
        "macd":        round(macd,        4),
        "macd_signal": round(macd_signal, 4),
        "ma20":        round(float(ma20), 2),
        "ma50":        round(float(ma50), 2),
        "momentum_5d": round(momentum_5d, 2),
        "score":       score,
        "trend":       "Aufwaerts" if preis > ma20 > ma50 else
                       "Abwaerts"  if preis < ma20 < ma50 else "Seitwaerts",
    }


# ---------------------------------------------------------------------------
# Batch-Download und Scan
# ---------------------------------------------------------------------------

def scanne_universum(
    ticker_liste: list[str] = None,
    top_n: int = 10,
    batch_groesse: int = 100,
    zeitraum: str = "3mo",
) -> list[dict]:
    """
    Laedt alle Aktien in Batches, bewertet sie technisch
    und gibt die Top N sortiert nach Score zurueck.
    """
    if ticker_liste is None:
        ticker_liste = lade_sp500_ticker()

    print(f"    Scanne {len(ticker_liste)} Titel in Batches von {batch_groesse}...")
    alle_ergebnisse = []
    batches         = [ticker_liste[i:i+batch_groesse]
                       for i in range(0, len(ticker_liste), batch_groesse)]

    for batch_nr, batch in enumerate(batches, 1):
        print(f"    Batch {batch_nr}/{len(batches)} ({len(batch)} Titel)...",
              end=" ", flush=True)
        try:
            daten = yf.download(
                batch,
                period=zeitraum,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            for ticker in batch:
                try:
                    # Neues yfinance-Format: MultiIndex (Feld, Ticker) oder flach
                    if len(batch) == 1:
                        df_ticker = daten
                    elif isinstance(daten.columns, pd.MultiIndex):
                        # Format: (Close, AAPL), (Volume, AAPL), ...
                        if ticker in daten.columns.get_level_values(1):
                            df_ticker = daten.xs(ticker, axis=1, level=1)
                        else:
                            continue
                    else:
                        continue

                    if df_ticker.empty:
                        continue

                    bewertung = _schnell_bewerte(df_ticker)
                    if bewertung and bewertung["score"] >= 4:
                        alle_ergebnisse.append({
                            "ticker": ticker,
                            **bewertung,
                        })
                except Exception:
                    continue

            print(f"OK  ({len([e for e in alle_ergebnisse if True])} Kandidaten)")

        except Exception as e:
            print(f"FEHLER: {e}")

        time.sleep(0.5)   # kurze Pause zwischen Batches

    # Nach Score sortieren, Top N zurueckgeben
    alle_ergebnisse.sort(key=lambda x: x["score"], reverse=True)
    top = alle_ergebnisse[:top_n]

    print(f"\n    {len(alle_ergebnisse)} Kandidaten gefunden, Top {top_n} ausgewaehlt.")
    return top


def drucke_scan_ergebnisse(ergebnisse: list[dict]):
    """Gibt die Top-Kandidaten tabellarisch aus."""
    print("\n" + "=" * 70)
    print(f"  TOP {len(ergebnisse)} AKTIEN-KANDIDATEN (S&P 500 Scan)")
    print("=" * 70)
    print(f"  {'#':<3} {'Ticker':<8} {'Preis':>8} {'RSI':>6} {'Trend':<12} {'Score':>6} {'5d-Mom':>8}")
    print("  " + "-" * 60)
    for i, e in enumerate(ergebnisse, 1):
        print(f"  {i:<3} {e['ticker']:<8} "
              f"${e['preis']:>7,.2f} "
              f"{e['rsi']:>6.1f} "
              f"{e['trend']:<12} "
              f"{e['score']:>6} "
              f"{e['momentum_5d']:>+7.1f}%")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System — Universe Scanner")
    print("Lade S&P 500 Titelliste...\n")

    ticker = lade_sp500_ticker()
    print(f"\nStarte Scan...")
    top10  = scanne_universum(ticker, top_n=10, batch_groesse=100)
    drucke_scan_ergebnisse(top10)
