"""
Trading Intelligence System -- Haupt-Pipeline
Startet alle Agenten der Reihe nach und gibt den vollstaendigen Tagesbericht aus.

Ablauf:
  1. Nachrichten laden (News-Agent)
  2. Technische Analyse + Aggregation (Aktien + Krypto)
  3. KI-Revision (Revisions-Agent)
  4. Bull/Bear-Debatte (Portfolio-Manager)
  5. Tagesbericht ausgeben + als Datei speichern
"""

import os
import sys
import time
import dataclasses
from datetime import datetime

# UTF-8 Ausgabe erzwingen (behebt Sonderzeichen-Darstellung auf Windows)
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Agenten importieren
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
from news_agent      import analysiere_nachrichten, erstelle_asset_zusammenfassung
from stock_analyst   import analysiere_aktie
from crypto_analyst  import analysiere_krypto
from aggregator      import (
    AKTIEN_LISTE, KRYPTO_LISTE,
    aggregiere_aktie, aggregiere_krypto,
    SIGNAL_WERT,
)
from social_agent       import bewerte_social
from backtesting_agent  import backtest_alle, BacktestErgebnis
from memory_agent       import initialisiere_db, speichere_signal, aktualisiere_vergangene_signale, hole_historischen_kontext
from universe_scanner   import scanne_universum, lade_sp500_ticker, scanne_kryptos
from correlation_agent  import analysiere_alle_korrelationen
from strategy_agent     import klassifiziere_strategie, berechne_kosten, retro_analyse_alle
from telegram_agent     import sende_tagesbericht, sende_positions_update
from email_agent        import hole_email_signale, signale_als_dict
from pattern_agent      import analysiere_muster
from makro_agent        import erkenne_makro_events, makro_einfluss_auf_asset, drucke_makro_lage
from learning_agent     import fuehre_lernzyklus_durch, hole_lern_bericht, hole_top_lehren
from volume_agent       import analysiere_volumen
from multi_depot        import (initialisiere as init_multi, filtere_fuer_strategie,
                                oeffne_positionen, aktualisiere_positionen as update_multi,
                                speichere_tageswert as speichere_multi,
                                hole_alle_statistiken, STRATEGIEN)
from portfolio_agent    import (initialisiere_portfolio, oeffne_positionen_tagesbatch,
                                aktualisiere_positionen, speichere_tageswert,
                                hole_statistiken, drucke_depot_status,
                                berechne_positionsgroessen)
from revision_agent        import analysiere_mit_ki
from bull_bear_debate      import debatte, drucke_debatte
from dashboard             import speichere_und_oeffne
from tailwind_connector    import lade_tailwind_signale, wende_tailwind_bonus_an, hole_tailwind_universe
from sec_agent             import scanne_alle as sec_scanne_alle, wende_sec_an
from valuation_agent       import scanne_alle as val_scanne_alle, wende_an as wende_bewertung_an

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

# Welche Assets sollen heute analysiert werden?
AKTIEN  = ["MSFT", "NVDA", "TSLA", "AAPL", "AMZN"]
KRYPTOS = ["BTC", "ETH", "SOL"]

TRENNLINIE = "=" * 65
DOPPELLINIE = "#" * 65


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def signal_zu_dict(sig) -> dict:
    """Konvertiert ein Gesamtsignal-Dataclass-Objekt in ein Dict."""
    if dataclasses.is_dataclass(sig):
        return dataclasses.asdict(sig)
    return sig


def drucke_header():
    jetzt = datetime.now().strftime("%d.%m.%Y  %H:%M Uhr")
    print()
    print(DOPPELLINIE)
    print("  TRADING INTELLIGENCE SYSTEM")
    print(f"  Tagesbericht vom {jetzt}")
    print(DOPPELLINIE)


def drucke_fortschritt(schritt: int, gesamt: int, text: str):
    print(f"\n  [{schritt}/{gesamt}] {text}")
    print("  " + "-" * 50)


def speichere_bericht(bericht_zeilen: list[str]):
    """Speichert den Bericht als Textdatei im output-Ordner."""
    os.makedirs("output", exist_ok=True)
    dateiname = datetime.now().strftime("output/bericht_%Y-%m-%d_%H%M.txt")
    with open(dateiname, "w", encoding="utf-8") as f:
        f.write("\n".join(bericht_zeilen))
    print(f"\n  Bericht gespeichert: {dateiname}")
    return dateiname


# ---------------------------------------------------------------------------
# Analyse-Funktionen
# ---------------------------------------------------------------------------

def analysiere_alle_assets(
    nachrichten: list,
    social_cache: dict = None,
    aktien_liste: list = None,
    email_signal_dict: dict = None,
    makro_signale: list = None,
    kryptos_liste: list = None,
) -> list[dict]:
    """
    Fuehrt technische Analyse + Aggregation fuer alle konfigurierten Assets durch.
    Gibt eine Liste von Signal-Dicts zurueck.
    """
    if email_signal_dict is None:
        email_signal_dict = {}
    if makro_signale is None:
        makro_signale = []

    alle_signale = []

    aktien_heute = aktien_liste or AKTIEN
    kryptos_heute = kryptos_liste or KRYPTOS

    # --- Aktien ---
    print(f"\n  Aktien ({len(aktien_heute)} Assets):")
    for ticker in aktien_heute:
        print(f"    -> {ticker} ...", end=" ", flush=True)
        try:
            sig = aggregiere_aktie(ticker, nachrichten, social_cache, email_signal_dict)
            # Makro-Einfluss einpreisen
            makro_punkte, makro_begruendung = makro_einfluss_auf_asset(ticker, makro_signale)
            if makro_punkte != 0:
                d = signal_zu_dict(sig)
                d["gesamt_punkte"] = round(d.get("gesamt_punkte", 0) + makro_punkte * 0.2, 3)
                d["begruendung"] = d.get("begruendung", []) + makro_begruendung
                sig = d
            # RSI direkt aus der TA holen und ins Dict schreiben
            ta = analysiere_aktie(ticker)
            d = signal_zu_dict(sig)
            d["rsi"] = ta["rsi"]
            d["trend"] = (
                "Aufwaertstrend" if ta["preis"] > ta["ma20"] > ta["ma50"]
                else "Abwaertstrend" if ta["preis"] < ta["ma20"] < ta["ma50"]
                else "Seitwaertstrend"
            )
            alle_signale.append(d)
            print(f"OK  [{d.get('empfehlung', '?')}]")
        except Exception as e:
            print(f"FEHLER: {e}")

    # --- Krypto ---
    print(f"\n  Krypto ({len(kryptos_heute)} Assets):")
    for symbol in kryptos_heute:
        print(f"    -> {symbol} ...", end=" ", flush=True)
        try:
            sig = aggregiere_krypto(symbol, nachrichten, social_cache, email_signal_dict)
            if sig:
                makro_punkte, makro_begruendung = makro_einfluss_auf_asset(symbol, makro_signale)
                if makro_punkte != 0:
                    d = signal_zu_dict(sig)
                    d["gesamt_punkte"] = round(d.get("gesamt_punkte", 0) + makro_punkte * 0.2, 3)
                    d["begruendung"] = d.get("begruendung", []) + makro_begruendung
                    sig = d
            if sig is None:
                print("UEBERSPRUNGEN (Rate-Limit)")
                continue
            d = signal_zu_dict(sig)
            alle_signale.append(d)
            print(f"OK  [{d.get('empfehlung', '?')}]")
            time.sleep(3)   # CoinGecko Rate-Limit
        except Exception as e:
            print(f"FEHLER: {e}")
            time.sleep(5)

    return alle_signale


def ki_phase(signale: list[dict]) -> list[dict]:
    """
    Fuehrt KI-Revision + Bull/Bear-Debatte fuer alle Signale durch.
    Gibt erweiterte Signal-Dicts mit KI-Ergebnis zurueck.
    """
    ergebnisse = []
    gesamt = len(signale)

    for i, sig in enumerate(signale, 1):
        asset = sig["asset"]
        empfehlung = sig["empfehlung"]
        print(f"\n    [{i}/{gesamt}] {asset}  (Vorlaeufig: {empfehlung})")

        try:
            # Schritt 1: Revisions-Agent
            print(f"          Revisions-Agent ...", end=" ", flush=True)
            mit_revision = analysiere_mit_ki(sig)
            print("OK")

            # Schritt 2: Bull/Bear-Debatte
            print(f"          Bull/Bear-Debatte ...", end=" ", flush=True)
            mit_debatte = debatte(mit_revision)
            print(f"OK  -> {mit_debatte['finale']['empfehlung']}")

            ergebnisse.append(mit_debatte)

        except Exception as e:
            print(f"FEHLER: {e}")
            # Signal ohne KI-Erweiterung trotzdem behalten
            sig["ki_empfehlung"] = sig["empfehlung"]
            sig["finale"] = {
                "empfehlung": sig["empfehlung"],
                "einstieg":   sig["preis"],
                "ziel":       sig.get("ziel", sig["preis"] * 1.10),
                "stop_loss":  sig.get("stop_loss", sig["preis"] * 0.95),
                "risiko":     "UNBEKANNT",
                "gewinner":   "-",
                "begruendung": "KI-Analyse nicht verfuegbar.",
            }
            ergebnisse.append(sig)

        time.sleep(1)   # kurze Pause zwischen Groq-Aufrufen

    return ergebnisse


# ---------------------------------------------------------------------------
# Tagesbericht
# ---------------------------------------------------------------------------

def erstelle_tagesbericht(ergebnisse: list[dict]) -> list[str]:
    """Erstellt den vollstaendigen Tagesbericht als Liste von Zeilen."""
    zeilen = []
    jetzt = datetime.now().strftime("%d.%m.%Y %H:%M Uhr")

    zeilen.append(DOPPELLINIE)
    zeilen.append("  TRADING INTELLIGENCE SYSTEM -- TAGESBERICHT")
    zeilen.append(f"  {jetzt}")
    zeilen.append(DOPPELLINIE)

    kaufen    = [e for e in ergebnisse if e["finale"]["empfehlung"] == "KAUFEN"]
    verkaufen = [e for e in ergebnisse if e["finale"]["empfehlung"] == "VERKAUFEN"]
    abwarten  = [e for e in ergebnisse if e["finale"]["empfehlung"] == "ABWARTEN"]

    # --- KAUFEN ---
    zeilen.append(f"\n  KAUFEN ({len(kaufen)} Assets):")
    zeilen.append("  " + "-" * 60)
    if kaufen:
        header = f"  {'Asset':<8} {'Preis':>10}  {'Ziel':>10}  {'Stop-Loss':>10}  {'Risiko':<8}"
        zeilen.append(header)
        zeilen.append("  " + "-" * 60)
        for e in kaufen:
            f = e["finale"]
            zeile = (
                f"  {e['asset']:<8} "
                f"${f['einstieg']:>9,.2f}  "
                f"${f['ziel']:>9,.2f}  "
                f"${f['stop_loss']:>9,.2f}  "
                f"{f['risiko']:<8}"
            )
            zeilen.append(zeile)
    else:
        zeilen.append("  Keine Kaufempfehlungen heute.")

    # --- VERKAUFEN ---
    if verkaufen:
        zeilen.append(f"\n  VERKAUFEN ({len(verkaufen)} Assets):")
        zeilen.append("  " + "-" * 40)
        for e in verkaufen:
            zeilen.append(f"  {e['asset']:<8}  ${e['preis']:>10,.2f}")

    # --- ABWARTEN ---
    zeilen.append(f"\n  ABWARTEN ({len(abwarten)} Assets):")
    if abwarten:
        zeilen.append("  " + ", ".join(e["asset"] for e in abwarten))

    # --- DETAILBERICHTE ---
    zeilen.append("\n" + DOPPELLINIE)
    zeilen.append("  DETAILBERICHTE")
    zeilen.append(DOPPELLINIE)

    for e in ergebnisse:
        f = e["finale"]
        typ = "AKTIE" if e["asset_typ"] == "aktie" else "KRYPTO"
        zeilen.append(f"\n  [{typ}] {e['asset']}  --  ${e['preis']:,.2f}")
        zeilen.append("  " + "-" * 50)
        zeilen.append(f"  Technisch    : {e['technisches_signal']}")
        zeilen.append(f"  News         : {e['news_sentiment'].upper()}  ({e['news_anzahl']} Artikel)")
        zeilen.append(f"  Debatte      : {f['gewinner']} gewinnt")
        zeilen.append(f"  Portfolio-Mgr: {f['begruendung'][:120]}")
        zeilen.append(f"  EMPFEHLUNG   : {f['empfehlung']}")
        if f["empfehlung"] == "KAUFEN":
            zeilen.append(f"  Einstieg     : ${f['einstieg']:,.2f}")
            zeilen.append(f"  Ziel         : ${f['ziel']:,.2f}")
            zeilen.append(f"  Stop-Loss    : ${f['stop_loss']:,.2f}")
            zeilen.append(f"  Risiko       : {f['risiko']}")

    zeilen.append("\n" + DOPPELLINIE)
    zeilen.append("  HINWEIS: Alle Empfehlungen dienen nur zur Information.")
    zeilen.append("  Keine Anlageberatung. Eigene Recherche erforderlich.")
    zeilen.append(DOPPELLINIE)

    return zeilen


# ---------------------------------------------------------------------------
# Haupt-Pipeline
# ---------------------------------------------------------------------------

def pruefe_kill_switch() -> tuple[bool, str]:
    """
    Daily-Loss Kill Switch:
    Wenn das Portfolio heute mehr als 3% verloren hat, werden keine
    neuen KAUFEN-Signale ausgegeben. Verhindert Kaeufe in fallenden Maerkten.
    """
    try:
        stats = hole_statistiken()
        tages_pnl = stats.get("tages_pnl_pct", 0)
        if tages_pnl <= -3.0:
            return True, f"Kill Switch aktiv: Tages-PnL {tages_pnl:.1f}% — keine neuen Kaufsignale"
    except Exception:
        pass
    return False, ""


def wende_kill_switch_an(signale: list[dict], aktiv: bool, grund: str) -> list[dict]:
    """Setzt alle KAUFEN-Empfehlungen auf ABWARTEN wenn Kill Switch aktiv."""
    if not aktiv:
        return signale
    for sig in signale:
        if sig.get("empfehlung") == "KAUFEN":
            sig["empfehlung"] = "ABWARTEN"
            sig.setdefault("begruendung", []).append(f"⛔ {grund}")
    return signale


def main():
    drucke_header()

    # Schritt 0: Systeme initialisieren + Lernzyklus
    initialisiere_db()
    initialisiere_portfolio()
    init_multi()
    print("\n  Starte Lernzyklus (Fehleranalyse vergangener Signale)...")
    try:
        lern_ergebnis = fuehre_lernzyklus_durch()
        print(f"  {lern_ergebnis['signale_gesamt']} Signale geprueft — "
              f"{lern_ergebnis['korrekte']} korrekt "
              f"({lern_ergebnis['trefferquote']:.1f}%) — "
              f"{lern_ergebnis['fehler']} Verluste — "
              f"{lern_ergebnis.get('verpasste_chancen', 0)} verpasste Chancen")
        if lern_ergebnis.get("angepasst", 0) > 0:
            print(f"  Lean: {lern_ergebnis['angepasst']} ineffektive Regel(n) durch staerkere ersetzt.")
        if lern_ergebnis.get("top_lehren"):
            print(f"  Aktive Lektionen: {len(lern_ergebnis['top_lehren'])}")
    except Exception as e:
        print(f"  Lernzyklus Fehler: {e}")
        lern_ergebnis = {"top_lehren": [], "analysen": [], "signale_gesamt": 0,
                         "fehler": 0, "trefferquote": 0, "korrekte": 0,
                         "verpasste_chancen": 0, "angepasst": 0,
                         "probleme": [], "alle_abweichungen": []}
    geschlossene_pos = aktualisiere_positionen()
    if geschlossene_pos:
        print("\n  Positionen automatisch geschlossen:")
        for g in geschlossene_pos:
            symbol = "GEWINN" if g["pnl_eur"] > 0 else "VERLUST"
            print(f"    {symbol}: {g['asset']}  {g['pnl_eur']:+.2f} EUR ({g['pnl_pct']:+.1f}%)")
    print("\n  Aktualisiere historisches Gedaechtnis...")
    n_aktualisiert = aktualisiere_vergangene_signale()
    if n_aktualisiert > 0:
        print(f"  {n_aktualisiert} vergangene Signale mit echten Kursdaten ergaenzt.")

    # Schritt 1: Universe Scanner — beste Aktien-Kandidaten ermitteln
    drucke_fortschritt(1, 7, "Universe Scan (S&P 500 — Top 10 Kandidaten)")
    try:
        sp500 = lade_sp500_ticker()
        top_aktien = [e["ticker"] for e in scanne_universum(sp500, top_n=10, batch_groesse=100)]
        kern = [a for a in AKTIEN if a not in top_aktien]
        AKTIEN_HEUTE = top_aktien + kern[:max(0, 3 - len(kern))]
        print(f"\n  Aktien heute: {', '.join(AKTIEN_HEUTE)}")
    except Exception as e:
        print(f"  Universe Scan Fehler: {e} — nutze Standard-Assets.")
        AKTIEN_HEUTE = AKTIEN

    try:
        krypto_kandidaten = scanne_kryptos(50)
        KRYPTOS_HEUTE = [k["ticker"] for k in krypto_kandidaten]
        if not KRYPTOS_HEUTE:
            KRYPTOS_HEUTE = KRYPTOS
        print(f"  Kryptos heute:  {', '.join(KRYPTOS_HEUTE)}")
    except Exception as e:
        print(f"  Krypto-Scan Fehler: {e} — nutze Standard-Kryptos.")
        KRYPTOS_HEUTE = KRYPTOS

    # Tailwind-Signale laden (unterbewertete Aktien mit Makro-Rueckenwind)
    print("\n  Lade Tailwind-Scanner Signale...")
    try:
        tailwind_signale = lade_tailwind_signale()
        # Tailwind STARK-Kandidaten in Analyse-Liste aufnehmen (max. 5 zusaetzliche)
        tw_kandidaten = hole_tailwind_universe(tailwind_signale, min_score=55)
        neue = [t for t in tw_kandidaten[:5] if t not in AKTIEN_HEUTE and t not in KRYPTOS_HEUTE]
        if neue:
            AKTIEN_HEUTE = AKTIEN_HEUTE + neue
            print(f"  Tailwind-Kandidaten hinzugefuegt: {', '.join(neue)}")
    except Exception as e:
        print(f"  Tailwind Fehler: {e}")
        tailwind_signale = {}

    alle_assets = AKTIEN_HEUTE + KRYPTOS_HEUTE

    # Schritt 2: Email-Signale aus GMX
    drucke_fortschritt(2, 10, "Email-Signale aus GMX lesen")
    try:
        email_signale     = hole_email_signale()
        email_signal_dict = signale_als_dict(email_signale)
        if email_signal_dict:
            print(f"  Email-Signale fuer: {', '.join(email_signal_dict.keys())}")
        else:
            print("  Keine Email-Signale heute.")
    except Exception as e:
        print(f"  Email-Agent Fehler: {e}")
        email_signal_dict = {}

    # Schritt 3: Nachrichten
    drucke_fortschritt(3, 10, "Nachrichten laden (RSS-Feeds)")
    nachrichten = analysiere_nachrichten(max_pro_quelle=15)
    print(f"  {len(nachrichten)} Artikel geladen.")

    # Makro-Events erkennen
    makro_signale = erkenne_makro_events(nachrichten)
    if makro_signale:
        drucke_makro_lage(makro_signale)
    else:
        print("  Keine signifikanten Makro-Events heute.")

    # Schritt 3: Social Media
    drucke_fortschritt(3, 7, "Social Media Analyse (Google Trends + Reddit + StockTwits)")
    social_cache = {}
    for asset in alle_assets:
        print(f"    -> {asset} ...", end=" ", flush=True)
        typ = "krypto" if asset in KRYPTOS else "aktie"
        try:
            social_cache[asset] = bewerte_social(asset, typ)
            sig = social_cache[asset]
            print(f"OK  [{sig.gesamt_sentiment}]")
        except Exception as e:
            print(f"FEHLER: {e}")
        time.sleep(1)
    print(f"\n  {len(social_cache)} Assets mit Social-Daten.")

    # Schritt 4: Technische Analyse
    drucke_fortschritt(4, 7, "Technische Analyse + Aggregation")
    signale = analysiere_alle_assets(
        nachrichten, social_cache, AKTIEN_HEUTE,
        email_signal_dict, makro_signale, KRYPTOS_HEUTE
    )
    print(f"\n  {len(signale)} Assets analysiert.")

    # Schritt 5: Backtesting
    drucke_fortschritt(5, 7, "Backtesting (letzte 90 Tage)")
    try:
        backtest_ergebnisse = backtest_alle(
            aktien=AKTIEN_HEUTE, kryptos=KRYPTOS_HEUTE, zeitraum_tage=90
        )
        print(f"  {len(backtest_ergebnisse)} Assets getestet.")
    except Exception as e:
        print(f"  Backtest Fehler: {e}")
        backtest_ergebnisse = []

    # Volume & Marktstruktur Analyse
    print("\n  Volume-Analyse (OBV, Order Blocks, Fair Value Gaps)...")
    for sig in signale:
        ist_krypto = sig.get("asset_typ") == "krypto"
        try:
            vol = analysiere_volumen(sig["asset"], ist_krypto)
            if vol:
                sig["volume_punkte"]     = vol.volume_punkte
                sig["volume_empfehlung"] = vol.volume_empfehlung
                sig["obv_trend"]         = vol.obv_trend
                sig["rel_volumen"]       = vol.relatives_volumen
                sig["vol_divergenz"]     = vol.volumen_divergenz
                sig["order_blocks"]      = vol.order_blocks
                # Volumen-Divergenz als Warnung in Begruendung eintragen
                if vol.volumen_divergenz:
                    sig.setdefault("begruendung", []).append(
                        "WARNUNG: Volumen-Divergenz — Kurs steigt ohne institutionelle Unterstuetzung"
                    )
        except Exception:
            pass

    # Pattern-Analyse fuer alle Assets
    print("\n  Pattern-Analyse (Kerzen, Fibonacci, Stochastik)...")
    for sig in signale:
        ist_krypto = sig.get("asset_typ") == "krypto"
        try:
            pat = analysiere_muster(sig["asset"], ist_krypto)
            if pat:
                sig["pattern_punkte"]     = pat.pattern_punkte
                sig["pattern_empfehlung"] = pat.pattern_empfehlung
                sig["kerzenmuster"]       = pat.kerzenmuster
                sig["stoch_k"]            = pat.stoch_k
                sig["stoch_signal"]       = pat.stoch_signal
                sig["bb_position"]        = pat.bb_position
                sig["fib_level"]          = pat.fib_level_name
        except Exception:
            pass

    # Tailwind-Bonus auf alle Signale anwenden
    if tailwind_signale:
        tw_treffer = 0
        for i, sig in enumerate(signale):
            signale[i] = wende_tailwind_bonus_an(sig, tailwind_signale)
            if signale[i].get("tailwind_signal"):
                tw_treffer += 1
        if tw_treffer:
            print(f"\n  Tailwind-Bonus angewendet auf {tw_treffer} Asset(s).")

    # SEC EDGAR: Insider-Transaktionen + 8-K Accounting-Flags
    print("\n  SEC EDGAR: Insider-Kaeufe + Material Events (Form 4 / 8-K)...")
    try:
        aktien_fuer_sec = [s["asset"] for s in signale if s.get("asset_typ") == "aktie"]
        sec_signale = sec_scanne_alle(aktien_fuer_sec, tage=7)
        if sec_signale:
            for i, sig in enumerate(signale):
                signale[i] = wende_sec_an(sig, sec_signale)
            print(f"  {len(sec_signale)} Asset(s) mit SEC-Signal.")
        else:
            print("  Keine neuen Insider-Transaktionen oder 8-K Warnungen.")
    except Exception as e:
        print(f"  SEC-Agent Fehler: {e}")

    # Fundamentalbewertung: P/E vs. Sektor-Median
    print("\n  Fundamentalbewertung (P/E vs. Sektor-Median)...")
    try:
        aktien_fuer_val = [s["asset"] for s in signale if s.get("asset_typ") == "aktie"]
        bewertungen = val_scanne_alle(aktien_fuer_val)
        if bewertungen:
            for i, sig in enumerate(signale):
                signale[i] = wende_bewertung_an(sig, bewertungen)
            hoch = sum(1 for b in bewertungen.values() if b.bewertung in ("HOCH", "EXTREM"))
            if hoch:
                print(f"  {hoch} Asset(s) mit erhoehter Bewertungswarnung.")
        else:
            print("  Alle Assets fundamental fair bewertet.")
    except Exception as e:
        print(f"  Valuation-Agent Fehler: {e}")

    # Daily-Loss Kill Switch pruefen
    kill_aktiv, kill_grund = pruefe_kill_switch()
    if kill_aktiv:
        print(f"\n  ⛔ {kill_grund}")
        signale = wende_kill_switch_an(signale, kill_aktiv, kill_grund)

    # Schritt 6: Strategie-Klassifikation + Kosten
    drucke_fortschritt(6, 9, "Strategie-Klassifikation (Short/Medium/Long) + TR-Kosten")
    try:
        for sig in signale:
            rsi     = sig.get("rsi", 50)
            mom     = sig.get("momentum_5d", 0)
            typ     = sig.get("asset_typ", "aktie")
            preis   = sig.get("preis", 0)
            inv     = 100.0  # Basis fuer Kostenberechnung
            strat   = klassifiziere_strategie(
                sig["asset"], preis, rsi, mom, typ, inv
            )
            sig["strategie"]       = strat.strategie
            sig["haltezeit_tage"]  = strat.haltezeit_tage
            sig["breakeven_pct"]   = strat.breakeven_pct
            sig["strategie_ziel"]  = strat.ziel_preis
            sig["strategie_stop"]  = strat.stop_preis
            sig["strat_begruendung"] = strat.begruendung
        print(f"  Strategien klassifiziert.")

        # Retro-Analyse
        retro_ergebnisse = retro_analyse_alle([])
        if retro_ergebnisse:
            print(f"  {len(retro_ergebnisse)} historische Signale rueckwirkend ausgewertet.")
        else:
            retro_ergebnisse = []
    except Exception as e:
        print(f"  Strategie-Fehler: {e}")
        retro_ergebnisse = []

    # Schritt 7: Korrelationen
    drucke_fortschritt(6, 8, "Korrelations-Analyse")
    try:
        korrelationen = analysiere_alle_korrelationen(signale)
        # Korrelationsdaten an Signale anhaengen
        for sig in signale:
            asset = sig["asset"]
            if asset in korrelationen:
                k = korrelationen[asset]
                sig["korrelation_links"]      = [
                    {"asset": l["asset"], "korrelation": l["korrelation"],
                     "begruendung": l["begruendung"], "signal": l["signal"]}
                    for l in k.thematische_links
                ]
                sig["korrelation_verstaerkt"] = k.verstarkende_signale
                sig["korrelation_warnungen"]  = k.warnungen
                sig["verwandte_assets"]       = k.verwandte_kaufkandidaten
        print(f"  Korrelationen berechnet fuer {len(korrelationen)} Assets.")
    except Exception as e:
        print(f"  Korrelations-Fehler: {e}")
        korrelationen = {}

    # Schritt 8: KI-Phase
    drucke_fortschritt(8, 9, "KI-Analyse (Revision + Bull/Bear-Debatte)")
    ergebnisse = ki_phase(signale)

    # Schritt 9: Bericht + Memory speichern
    drucke_fortschritt(9, 9, "Tagesbericht erstellen + Signale im Gedaechtnis speichern")
    bericht = erstelle_tagesbericht(ergebnisse)

    print("\n")
    for zeile in bericht:
        print(zeile)

    speichere_bericht(bericht)

    # Heutige Signale im Gedaechtnis speichern
    for e in ergebnisse:
        try:
            speichere_signal(e)
        except Exception:
            pass
    print(f"  {len(ergebnisse)} Signale im Marktgedaechtnis gespeichert.")

    # Musterdepot: Kapital auf alle heutigen KAUFEN-Signale verteilen
    try:
        verteilung = berechne_positionsgroessen(ergebnisse)
        if verteilung:
            print(f"\n  Kapitalverteilung heute:")
            for asset, betrag in verteilung.items():
                print(f"    {asset:<8} {betrag:>7.2f} EUR")
        neue_assets = oeffne_positionen_tagesbatch(ergebnisse)
        speichere_tageswert()
        if neue_assets:
            print(f"  {len(neue_assets)} Positionen eroeffnet: {', '.join(neue_assets)}")
        else:
            print("  Keine neuen Positionen (kein Kapital frei oder keine KAUFEN-Signale).")
    except Exception as e:
        print(f"  Depot-Fehler: {e}")
    depot_stats = hole_statistiken()

    # Multi-Depot aktualisieren und neue Positionen eroeffnen
    update_multi()
    for strategie in STRATEGIEN:
        kandidaten = filtere_fuer_strategie(strategie, ergebnisse)
        oeffne_positionen(strategie, kandidaten)
    speichere_multi()
    multi_stats = hole_alle_statistiken()

    # Telegram zuerst senden (bevor optionale Schritte wie Dashboard crashen koennen)
    print("\n  Sende Telegram-Bericht...")
    sende_tagesbericht(ergebnisse, depot_stats)
    if geschlossene_pos:
        sende_positions_update(geschlossene_pos)

    # HTML-Dashboard erstellen (nicht kritisch -- Fehler stoppen den Lauf nicht)
    try:
        print("\n  HTML-Dashboard wird erstellt...")
        speichere_und_oeffne(ergebnisse, backtest_ergebnisse, depot_stats,
                             retro_ergebnisse, multi_stats, lern_ergebnis)
    except Exception as e:
        print(f"  [Dashboard] Fehler (nicht kritisch): {e}")


if __name__ == "__main__":
    main()
