"""
Valuation Agent — Fundamentalbewertung
Vergleicht P/E, P/B, EV/EBITDA mit Sektor-Medianen.

Warnt bei:
  - P/E > 3x Sektor-Median  → -1 Punkt
  - P/E > 8x Sektor-Median  → -3 Punkte (PLTR-Szenario)
  - P/B > 20x               → Zusatzwarnung

Bonus bei:
  - P/E < 0.5x Sektor-Median UND Kurs nahe 52W-Tief → +1 Punkt (Value Play)
"""

from dataclasses import dataclass
import yfinance as yf

# Historische Sektor-P/E Mediane (langjaehrige Durchschnitte)
_SEKTOR_PE: dict[str, float] = {
    "Technology":              28.0,
    "Healthcare":              22.0,
    "Consumer Cyclical":       24.0,
    "Consumer Defensive":      22.0,
    "Financial Services":      13.0,
    "Energy":                  14.0,
    "Utilities":               17.0,
    "Industrials":             21.0,
    "Basic Materials":         17.0,
    "Real Estate":             30.0,
    "Communication Services":  20.0,
}
_DEFAULT_PE = 22.0

# Bekannte Ausnahmen: Wachstumstitel die strukturell hoeher bewertet sind
# Hier wird der Warnschwelle ein Multiplikator aufgeschlagen
_WACHSTUMS_AUSNAHMEN = {
    "NVDA", "TSLA", "AMZN", "NFLX", "CRM", "SHOP",
}
_WACHSTUMS_FAKTOR = 2.0  # Schwelle verdoppelt fuer Wachstumstitel

# Schwellen (Vielfaches des Sektor-Medians)
_SCHWELLE_HOCH    = 3.0
_SCHWELLE_EXTREM  = 8.0

# Kryptos haben kein P/E
_KRYPTOS = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB",
            "MATIC", "AVAX", "DOT", "LINK", "UNI", "QBTS"}


@dataclass
class BewertungsSignal:
    ticker:         str
    sektor:         str
    pe_trailing:    float
    pe_forward:     float
    pb_ratio:       float
    ev_ebitda:      float
    sektor_median:  float
    pe_vielfaches:  float
    bewertung:      str    # FAIR / HOCH / EXTREM / GÜNSTIG
    punkte:         int
    warnung:        str


def analysiere(ticker: str) -> BewertungsSignal | None:
    """Wertet Fundamentaldaten eines Tickers aus."""
    if ticker.upper() in _KRYPTOS:
        return None

    try:
        info = yf.Ticker(ticker).info

        pe_t  = float(info.get("trailingPE")       or 0)
        pe_f  = float(info.get("forwardPE")         or 0)
        pb    = float(info.get("priceToBook")        or 0)
        ev_eb = float(info.get("enterpriseToEbitda") or 0)
        sektor = info.get("sector", "") or "Technology"

        # Nehme den verfuegbaren P/E (trailing bevorzugt, sonst forward)
        pe = pe_t if pe_t > 0 else pe_f
        if pe <= 0 or pe > 5000:  # Negative Earnings oder unrealistisch
            return None

        sektor_median = _SEKTOR_PE.get(sektor, _DEFAULT_PE)
        vielfaches    = pe / sektor_median

        # Wachstumstitel bekommen einen erhoehten Schwellenwert
        faktor = _WACHSTUMS_FAKTOR if ticker.upper() in _WACHSTUMS_AUSNAHMEN else 1.0
        schwelle_hoch   = _SCHWELLE_HOCH   * faktor
        schwelle_extrem = _SCHWELLE_EXTREM * faktor

        if vielfaches >= schwelle_extrem:
            bewertung = "EXTREM"
            punkte    = -3
            warnung   = (
                f"P/E {pe:.0f}x ist {vielfaches:.1f}x der Sektor-Norm ({sektor_median:.0f}x) — "
                f"EXTREME Bewertung. Pflicht-Trailing-Stop! (Wie PLTR-Lektion)"
            )
        elif vielfaches >= schwelle_hoch:
            bewertung = "HOCH"
            punkte    = -1
            warnung   = (
                f"P/E {pe:.0f}x = {vielfaches:.1f}x Sektor-Median — "
                f"Ueberbewertung erhoht Absturzrisiko bei schlechten News"
            )
        elif vielfaches < 0.5 and pe > 0:
            # Guenstiger als halb so teuer wie der Sektor
            bewertung = "GÜNSTIG"
            punkte    = +1
            warnung   = ""
        else:
            bewertung = "FAIR"
            punkte    = 0
            warnung   = ""

        # Zusatzwarnung bei extremem Price-to-Book
        if pb > 20 and bewertung in ("HOCH", "EXTREM"):
            warnung += f" | P/B {pb:.1f}x (sehr hoch)"

        return BewertungsSignal(
            ticker=ticker, sektor=sektor,
            pe_trailing=pe_t, pe_forward=pe_f,
            pb_ratio=pb, ev_ebitda=ev_eb,
            sektor_median=sektor_median,
            pe_vielfaches=round(vielfaches, 1),
            bewertung=bewertung, punkte=punkte, warnung=warnung,
        )

    except Exception as e:
        return None


def scanne_alle(tickers: list[str]) -> dict[str, BewertungsSignal]:
    """Wertet alle Aktien-Ticker aus. Gibt nur nicht-faire Bewertungen zurueck."""
    ergebnisse: dict[str, BewertungsSignal] = {}
    aktien = [t for t in tickers if t.upper() not in _KRYPTOS]

    for ticker in aktien:
        b = analysiere(ticker)
        if b and b.bewertung != "FAIR":
            ergebnisse[ticker] = b
            if b.bewertung == "EXTREM":
                print(f"    🔴 {ticker}: {b.warnung}")
            elif b.bewertung == "HOCH":
                print(f"    🟡 {ticker}: P/E {b.pe_trailing:.0f}x = {b.pe_vielfaches}x Sektor")
            elif b.bewertung == "GÜNSTIG":
                print(f"    🟢 {ticker}: P/E {b.pe_trailing:.0f}x — guenstig vs. Sektor")

    return ergebnisse


def wende_an(signal: dict, bewertungen: dict[str, BewertungsSignal]) -> dict:
    """Wendet Bewertungs-Punkte auf ein aggregiertes Signal an."""
    ticker = signal.get("asset", "")
    if ticker not in bewertungen:
        return signal

    b = bewertungen[ticker]
    if b.punkte == 0:
        return signal

    signal = dict(signal)
    signal["gesamt_punkte"] = round(signal.get("gesamt_punkte", 0) + b.punkte, 2)

    if b.warnung:
        icon = "🔴" if b.punkte <= -3 else "🟡" if b.punkte < 0 else "🟢"
        signal.setdefault("begruendung", []).append(f"{icon} Bewertung: {b.warnung}")

    # Extrem-Bewertung: Trailing-Stop-Hinweis direkt in Empfehlung
    if b.bewertung == "EXTREM" and signal.get("empfehlung") == "KAUFEN":
        signal.setdefault("begruendung", []).append(
            "⚠️ PFLICHT: Bei Kauf zwingend Trailing-Stop setzen (extreme Bewertung)"
        )

    signal["bewertung"] = b.bewertung
    return signal


# ─── Standalone-Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Valuation Agent — Test\n")
    test = ["MSFT", "PLTR", "NVDA", "TSLA", "JPM", "XOM", "META"]
    for t in test:
        b = analysiere(t)
        if b:
            print(f"  {t:6s}  PE={b.pe_trailing:6.1f}x  Sektor={b.sektor_median:.0f}x  "
                  f"Vielfaches={b.pe_vielfaches}x  [{b.bewertung}]  {b.warnung[:60]}")
        else:
            print(f"  {t:6s}  — kein P/E verfuegbar")
