"""
Dashboard-Generator mit TradingView-Charts
Erstellt eine HTML-Datei und oeffnet sie im Browser.
TradingView-Widgets sind kostenlos und benoetigen keinen API-Key.
"""

import os
import sys
import webbrowser
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# TradingView Symbol-Mapping
# ---------------------------------------------------------------------------

TV_SYMBOLE = {
    "AAPL":  "NASDAQ:AAPL",
    "MSFT":  "NASDAQ:MSFT",
    "NVDA":  "NASDAQ:NVDA",
    "TSLA":  "NASDAQ:TSLA",
    "AMZN":  "NASDAQ:AMZN",
    "GOOGL": "NASDAQ:GOOGL",
    "META":  "NASDAQ:META",
    "BTC":   "BINANCE:BTCUSDT",
    "ETH":   "BINANCE:ETHUSDT",
    "SOL":   "BINANCE:SOLUSDT",
    "XRP":   "BINANCE:XRPUSDT",
    "BNB":   "BINANCE:BNBUSDT",
    "DOGE":  "BINANCE:DOGEUSDT",
}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _farbe(empfehlung: str) -> str:
    return {"KAUFEN": "#00c896", "VERKAUFEN": "#ff4d6d", "ABWARTEN": "#f0a500"}.get(empfehlung, "#888")

def _risiko_farbe(risiko: str) -> str:
    return {"NIEDRIG": "#00c896", "MITTEL": "#f0a500", "HOCH": "#ff4d6d"}.get(risiko.upper(), "#888")

def _tv_symbol(asset: str) -> str:
    return TV_SYMBOLE.get(asset, f"NASDAQ:{asset}")

def _mini_chart(asset: str, empfehlung: str) -> str:
    """Kleines TradingView Mini-Chart Widget fuer Uebersichtskarten."""
    symbol = _tv_symbol(asset)
    farbe  = "00c896" if empfehlung == "KAUFEN" else ("ff4d6d" if empfehlung == "VERKAUFEN" else "f0a500")
    return f"""
    <div class="tv-mini">
      <div class="tradingview-widget-container" style="height:120px;">
        <div class="tradingview-widget-container__widget"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
        {{
          "symbol": "{symbol}",
          "width": "100%",
          "height": 120,
          "locale": "de_DE",
          "dateRange": "1M",
          "colorTheme": "dark",
          "trendLineColor": "rgba({int(farbe[0:2],16)}, {int(farbe[2:4],16)}, {int(farbe[4:6],16)}, 1)",
          "underLineColor": "rgba({int(farbe[0:2],16)}, {int(farbe[2:4],16)}, {int(farbe[4:6],16)}, 0.15)",
          "isTransparent": true,
          "autosize": true,
          "largeChartUrl": ""
        }}
        </script>
      </div>
    </div>"""

def _grosser_chart(asset: str) -> str:
    """Vollstaendiges TradingView Chart Widget fuer den Detailbereich."""
    symbol = _tv_symbol(asset)
    widget_id = f"tv_{asset.lower()}"
    return f"""
    <div class="tv-chart-container">
      <div id="{widget_id}" class="tradingview-widget-container" style="height:420px; width:100%;">
        <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px); width:100%;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
        {{
          "autosize": true,
          "symbol": "{symbol}",
          "interval": "D",
          "timezone": "Europe/Berlin",
          "theme": "dark",
          "style": "1",
          "locale": "de_DE",
          "allow_symbol_change": false,
          "calendar": false,
          "studies": [
            "STD;RSI",
            "STD;MACD",
            "STD;MA%ribbon"
          ],
          "support_host": "https://www.tradingview.com"
        }}
        </script>
      </div>
    </div>"""


# ---------------------------------------------------------------------------
# HTML-Bausteine
# ---------------------------------------------------------------------------

def _zusammenfassung_karte(e: dict, backtest_map: dict = None) -> str:
    f      = e["finale"]
    farbe  = _farbe(f["empfehlung"])
    r_farbe = _risiko_farbe(f.get("risiko", "MITTEL"))
    typ    = "AKTIE" if e["asset_typ"] == "aktie" else "KRYPTO"
    mini   = _mini_chart(e["asset"], f["empfehlung"])
    bt_badge = _backtest_badge(e["asset"], backtest_map or {})

    kauf_felder = ""
    if f["empfehlung"] == "KAUFEN":
        kauf_felder = f"""
        <div class="preis-zeile">
          <span class="label">Ziel</span>
          <span class="wert gruen">${f["ziel"]:,.2f}</span>
        </div>
        <div class="preis-zeile">
          <span class="label">Stop-Loss</span>
          <span class="wert rot">${f["stop_loss"]:,.2f}</span>
        </div>
        <div class="preis-zeile">
          <span class="label">Risiko</span>
          <span class="wert" style="color:{r_farbe};">{f.get("risiko","–")}</span>
        </div>"""

    return f"""
    <div class="asset-card">
      <div class="card-header" style="border-left: 4px solid {farbe};">
        <span class="asset-typ">{typ}</span>
        <span class="asset-name">{e['asset']}</span>
        <span class="empfehlung-badge" style="background:{farbe};">{f['empfehlung']}</span>
      </div>
      {mini}
      <div class="card-body">
        <div class="preis-zeile">
          <span class="label">Preis</span>
          <span class="wert">${e['preis']:,.2f}</span>
        </div>
        {kauf_felder}
        <div class="signale">
          <span class="signal-item">📈 {e.get("technisches_signal","–")}</span>
          <span class="signal-item">📰 {e.get("news_sentiment","–").upper()}</span>
          {bt_badge}
          {_strategie_badge(e)}
        </div>
        <div class="begruendung">{f.get("begruendung","")[:180]}…</div>
      </div>
    </div>"""


def _korrelations_sektion(e: dict) -> str:
    """Rendert die Korrelations-Links fuer einen Asset-Detailbereich."""
    links      = e.get("korrelation_links", [])
    verstaerkt = e.get("korrelation_verstaerkt", [])
    warnungen  = e.get("korrelation_warnungen", [])
    verwandte  = e.get("verwandte_assets", [])

    if not links and not verstaerkt and not warnungen:
        return ""

    link_zeilen = ""
    for l in links[:6]:
        k = l["korrelation"]
        farbe = "#00c896" if k > 0 else "#ff4d6d"
        balken_len = int(abs(k) * 8)
        balken = "█" * balken_len
        sig = f'<span style="font-size:0.7rem;background:#21262d;padding:1px 6px;border-radius:10px;">{l["signal"]}</span>' if l["signal"] != "–" else ""
        link_zeilen += f"""
        <div class="korr-zeile">
          <span class="korr-asset">{l["asset"]}</span>
          <span class="korr-balken" style="color:{farbe};">{balken}</span>
          <span class="korr-wert" style="color:{farbe};">{k:+.0%}</span>
          {sig}
          <span class="korr-text">{l["begruendung"][:50]}</span>
        </div>"""

    verstaerkt_html = "".join(
        f'<div class="korr-verstaerkt">✚ {v}</div>' for v in verstaerkt
    )
    warn_html = "".join(
        f'<div class="korr-warnung">⚠ {w}</div>' for w in warnungen
    )
    verwandte_html = (
        f'<div class="korr-verwandte">Auch prüfen: '
        + "".join(f'<span>{a}</span>' for a in verwandte)
        + "</div>"
    ) if verwandte else ""

    return f"""
    <div class="korr-box">
      <h4>🔗 Korrelationen & verwandte Assets</h4>
      {link_zeilen}
      {verstaerkt_html}
      {warn_html}
      {verwandte_html}
    </div>"""


def _detail_karte(e: dict) -> str:
    f      = e["finale"]
    farbe  = _farbe(f["empfehlung"])
    chart  = _grosser_chart(e["asset"])

    bull_html = "".join(
        f"<li>{z.strip().lstrip('*•123456789. ')}</li>"
        for z in e.get("bull_argumente","").splitlines()
        if z.strip() and len(z.strip()) > 12
    )
    bear_html = "".join(
        f"<li>{z.strip().lstrip('*•123456789. ')}</li>"
        for z in e.get("bear_argumente","").splitlines()
        if z.strip() and len(z.strip()) > 12
    )
    ki_abs   = [z.strip() for z in e.get("ki_analyse","").splitlines()
                if z.strip() and "EMPFEHLUNG:" not in z]
    ki_html  = "".join(f"<p>{z}</p>" for z in ki_abs[:14])

    # Tiefen-Analyse (nur fuer Top-Kaufkandidaten vorhanden)
    deep_html = ""
    if e.get("deep_dive"):
        absaetze = "".join(
            f"<p>{z.strip()}</p>"
            for z in e["deep_dive"].splitlines() if z.strip()
        )
        deep_html = f"""
        <div class="deep-dive" style="margin-top:14px;padding:12px;border:1px solid #2c3e50;border-radius:8px;background:rgba(52,152,219,0.06);">
          <h4>🔍 Tiefen-Analyse (Top-Kaufkandidat)</h4>
          {absaetze}
        </div>"""

    trade_box = ""
    if f["empfehlung"] == "KAUFEN":
        trade_box = f"""
        <div class="trade-box">
          <div class="trade-item"><span>Einstieg</span><strong>${f["einstieg"]:,.2f}</strong></div>
          <div class="trade-item gruen"><span>Ziel</span><strong>${f["ziel"]:,.2f}</strong></div>
          <div class="trade-item rot"><span>Stop-Loss</span><strong>${f["stop_loss"]:,.2f}</strong></div>
          <div class="trade-item"><span>Risiko</span><strong style="color:{_risiko_farbe(f.get('risiko','MITTEL'))}">{f.get("risiko","–")}</strong></div>
        </div>"""

    return f"""
    <details class="detail-karte">
      <summary style="border-left: 4px solid {farbe};">
        <span class="detail-name">{e['asset']}</span>
        <span class="detail-preis">${e['preis']:,.2f}</span>
        <span class="empfehlung-badge" style="background:{farbe};">{f['empfehlung']}</span>
        <span class="debatte-info">Debatte: {f.get("gewinner","–")} gewinnt</span>
      </summary>
      <div class="detail-body">
        {chart}
        {trade_box}
        <div class="debatte-grid">
          <div class="bull-box">
            <h4>🟢 Bull-Argumente</h4>
            <ul>{bull_html or "<li>Keine Daten verfuegbar.</li>"}</ul>
          </div>
          <div class="bear-box">
            <h4>🔴 Bear-Argumente</h4>
            <ul>{bear_html or "<li>Keine Daten verfuegbar.</li>"}</ul>
          </div>
        </div>
        <div class="ki-analyse">
          <h4>🤖 KI-Revision (Llama 3.3 70B)</h4>
          {ki_html or "<p>Keine KI-Analyse verfuegbar.</p>"}
        </div>
        {deep_html}
        {_korrelations_sektion(e)}
      </div>
    </details>"""


# ---------------------------------------------------------------------------
# Haupt-HTML-Generator
# ---------------------------------------------------------------------------

def _backtest_badge(asset: str, backtest_map: dict) -> str:
    """Kleines Badge mit Trefferquote aus dem Backtest."""
    if asset not in backtest_map:
        return ""
    b = backtest_map[asset]
    if b.trades_gesamt == 0:
        return ""
    farbe = "#00c896" if b.trefferquote_pct >= 50 else ("#f0a500" if b.trefferquote_pct >= 35 else "#ff4d6d")
    return f'<span class="bt-badge" style="background:{farbe}20;color:{farbe};border:1px solid {farbe}40;" title="Backtest: {b.trades_gesamt} Trades, Ø {b.durchschn_rendite_pct:+.1f}%/Trade">📊 {b.trefferquote_pct:.0f}% Treffer</span>'


def _backtest_sektion(backtest_ergebnisse: list) -> str:
    """Rendert eine kompakte Backtest-Übersichtstabelle."""
    if not backtest_ergebnisse:
        return ""
    zeilen = ""
    for b in backtest_ergebnisse:
        if b.trades_gesamt == 0:
            continue
        farbe = "#00c896" if b.trefferquote_pct >= 50 else ("#f0a500" if b.trefferquote_pct >= 35 else "#ff4d6d")
        rendite_farbe = "#00c896" if b.durchschn_rendite_pct > 0 else "#ff4d6d"
        zeilen += f"""
        <tr>
          <td style="font-weight:700;">{b.asset}</td>
          <td>{b.trades_gesamt}</td>
          <td style="color:{farbe};font-weight:600;">{b.trefferquote_pct:.0f}%</td>
          <td style="color:{rendite_farbe};font-weight:600;">{b.durchschn_rendite_pct:+.2f}%</td>
          <td>{b.gesamt_rendite_pct:+.2f}%</td>
          <td>{b.sharpe_ratio:+.2f}</td>
        </tr>"""
    return f"""
    <h2>🧪 Backtest (letzte 90 Tage)</h2>
    <div class="bt-tabelle-wrap">
      <table class="bt-tabelle">
        <thead>
          <tr>
            <th>Asset</th><th>Trades</th><th>Trefferquote</th>
            <th>Ø Rendite</th><th>Gesamt</th><th>Sharpe</th>
          </tr>
        </thead>
        <tbody>{zeilen}</tbody>
      </table>
    </div>"""


def erstelle_html(ergebnisse: list[dict], datum: str, backtest_ergebnisse: list = None, depot_stats: dict = None, retro_ergebnisse: list = None, multi_stats: list = None, lern_ergebnis: dict = None) -> str:
    backtest_ergebnisse = backtest_ergebnisse or []
    backtest_map = {b.asset: b for b in backtest_ergebnisse}
    kaufen    = [e for e in ergebnisse if e["finale"]["empfehlung"] == "KAUFEN"]
    verkaufen = [e for e in ergebnisse if e["finale"]["empfehlung"] == "VERKAUFEN"]
    abwarten  = [e for e in ergebnisse if e["finale"]["empfehlung"] == "ABWARTEN"]

    kaufen_html    = "\n".join(_zusammenfassung_karte(e, backtest_map) for e in kaufen) \
                     or "<p class='leer'>Keine Kaufempfehlungen heute.</p>"
    verkaufen_html = "\n".join(_zusammenfassung_karte(e, backtest_map) for e in verkaufen)
    abwarten_chips = "".join(
        f'<span class="abwarten-chip">{e["asset"]}</span>' for e in abwarten
    ) or "<p class='leer'>–</p>"
    detail_html    = "\n".join(_detail_karte(e) for e in ergebnisse)

    vk_sektion = ""
    if verkaufen:
        vk_sektion = f"""
        <h2>🔻 Verkaufen ({len(verkaufen)})</h2>
        <div class="karten-grid">{verkaufen_html}</div>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trading Intelligence System — {datum}</title>
  <style>
    :root {{
      --bg:#0d1117; --bg2:#161b22; --bg3:#21262d;
      --text:#e6edf3; --text2:#8b949e;
      --gruen:#00c896; --rot:#ff4d6d; --gelb:#f0a500;
      --border:#30363d; --radius:10px;
    }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ background:var(--bg); color:var(--text);
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
            padding:28px 32px; max-width:1400px; margin:0 auto; }}
    h1   {{ font-size:1.6rem; font-weight:700; margin-bottom:4px; }}
    .datum {{ color:var(--text2); font-size:0.9rem; margin-bottom:36px; }}
    h2   {{ font-size:0.85rem; font-weight:700; text-transform:uppercase;
            letter-spacing:.1em; color:var(--text2); margin:32px 0 14px; }}
    .karten-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:16px; }}
    /* Karten */
    .asset-card {{ background:var(--bg2); border:1px solid var(--border);
                   border-radius:var(--radius); overflow:hidden; }}
    .card-header {{ display:flex; align-items:center; gap:10px; padding:13px 16px;
                    background:var(--bg3); }}
    .asset-typ  {{ font-size:0.68rem; color:var(--text2); background:var(--bg);
                   padding:2px 8px; border-radius:20px; }}
    .asset-name {{ font-size:1.1rem; font-weight:700; flex:1; }}
    .empfehlung-badge {{ font-size:0.72rem; font-weight:800; padding:3px 10px;
                         border-radius:20px; color:#000; white-space:nowrap; }}
    .tv-mini    {{ border-bottom:1px solid var(--border); }}
    .card-body  {{ padding:14px 16px; }}
    .preis-zeile {{ display:flex; justify-content:space-between; padding:5px 0;
                    border-bottom:1px solid var(--border); font-size:0.88rem; }}
    .preis-zeile:last-of-type {{ border:none; }}
    .label  {{ color:var(--text2); }}
    .wert   {{ font-weight:600; }}
    .gruen  {{ color:var(--gruen); }}
    .rot    {{ color:var(--rot); }}
    .signale {{ display:flex; gap:7px; flex-wrap:wrap; margin-top:10px; }}
    .signal-item {{ font-size:0.75rem; background:var(--bg3);
                    padding:3px 8px; border-radius:6px; color:var(--text2); }}
    .begruendung {{ font-size:0.76rem; color:var(--text2); margin-top:10px; line-height:1.55; }}
    .leer {{ color:var(--text2); font-style:italic; padding:8px 0; }}
    .abwarten-chip {{ display:inline-block; background:var(--bg3);
                      border:1px solid var(--border); padding:5px 15px;
                      border-radius:20px; margin:4px; font-size:0.88rem;
                      color:var(--gelb); }}
    /* Detail-Karten */
    details.detail-karte {{ background:var(--bg2); border:1px solid var(--border);
                             border-radius:var(--radius); margin-bottom:10px; overflow:hidden; }}
    details summary {{ display:flex; align-items:center; gap:12px; padding:14px 18px;
                       cursor:pointer; user-select:none; background:var(--bg3); list-style:none; }}
    details summary::-webkit-details-marker {{ display:none; }}
    details summary::before {{ content:"▶"; font-size:0.65rem; color:var(--text2);
                                transition:transform .2s; flex-shrink:0; }}
    details[open] summary::before {{ transform:rotate(90deg); }}
    .detail-name  {{ font-size:1.05rem; font-weight:700; flex:1; }}
    .detail-preis {{ color:var(--text2); font-size:0.88rem; }}
    .debatte-info {{ font-size:0.75rem; color:var(--text2);
                     background:var(--bg); padding:2px 8px; border-radius:20px; }}
    .detail-body  {{ padding:20px; }}
    .tv-chart-container {{ margin-bottom:20px; border-radius:8px; overflow:hidden;
                           border:1px solid var(--border); }}
    .trade-box {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:20px; }}
    .trade-item {{ background:var(--bg3); border-radius:8px; padding:12px; text-align:center; }}
    .trade-item span {{ display:block; font-size:0.72rem; color:var(--text2); margin-bottom:4px; }}
    .trade-item strong {{ font-size:1rem; }}
    .trade-item.gruen strong {{ color:var(--gruen); }}
    .trade-item.rot   strong {{ color:var(--rot); }}
    .debatte-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }}
    .bull-box, .bear-box {{ background:var(--bg3); border-radius:8px; padding:14px; }}
    .bull-box h4 {{ color:var(--gruen); margin-bottom:10px; font-size:0.85rem; }}
    .bear-box h4 {{ color:var(--rot);   margin-bottom:10px; font-size:0.85rem; }}
    .bull-box li, .bear-box li {{ font-size:0.8rem; color:var(--text2);
                                   margin-bottom:6px; line-height:1.45;
                                   padding-left:16px; list-style:none; position:relative; }}
    .bull-box li::before {{ content:"▸"; position:absolute; left:0; color:var(--gruen); }}
    .bear-box li::before {{ content:"▸"; position:absolute; left:0; color:var(--rot); }}
    .ki-analyse {{ background:var(--bg3); border-radius:8px; padding:16px; }}
    .ki-analyse h4 {{ color:var(--text2); margin-bottom:10px; font-size:0.85rem; }}
    .ki-analyse p {{ font-size:0.8rem; color:var(--text); line-height:1.65; margin-bottom:8px; }}
    .lern-box {{ background:var(--bg2); border:1px solid var(--border); border-radius:var(--radius); padding:20px; }}
    .lern-stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:16px; }}
    .ls-item {{ background:var(--bg3); border-radius:8px; padding:12px; text-align:center; }}
    .ls-item span {{ display:block; font-size:0.72rem; color:var(--text2); margin-bottom:4px; }}
    .ls-item strong {{ font-size:1rem; }}
    .lern-box h4 {{ font-size:0.85rem; color:var(--text2); margin:14px 0 8px; }}
    .lern-fehler {{ background:var(--bg3); border-left:3px solid var(--rot); border-radius:6px; padding:12px; margin-bottom:8px; }}
    .lf-header {{ display:flex; gap:12px; align-items:center; margin-bottom:8px; }}
    .lf-asset {{ font-weight:700; }}
    .lf-rendite {{ font-weight:600; font-size:0.88rem; }}
    .lf-datum {{ color:var(--text2); font-size:0.78rem; margin-left:auto; }}
    .lf-analyse {{ font-size:0.78rem; color:var(--text); line-height:1.6; }}
    .lern-lehre {{ display:flex; gap:10px; align-items:flex-start; padding:7px 0; border-bottom:1px solid var(--border); }}
    .lern-lehre:last-child {{ border:none; }}
    .ll-count {{ background:var(--bg3); color:var(--gelb); font-size:0.72rem; font-weight:700; padding:2px 7px; border-radius:10px; white-space:nowrap; flex-shrink:0; }}
    .ll-text {{ font-size:0.82rem; color:var(--text); line-height:1.5; }}
    .md-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:14px; margin-bottom:8px; }}
    .md-karte {{ background:var(--bg2); border:1px solid var(--border); border-radius:var(--radius); padding:16px; }}
    .md-header {{ display:flex; align-items:center; gap:8px; margin-bottom:10px; }}
    .md-name {{ font-weight:700; font-size:0.95rem; }}
    .md-wert {{ font-size:1.1rem; font-weight:700; margin-bottom:4px; }}
    .md-pnl  {{ font-size:0.88rem; font-weight:600; margin-bottom:8px; }}
    .md-meta {{ font-size:0.75rem; color:var(--text2); }}
    .depot-box {{ background:var(--bg2); border:1px solid var(--border);
                  border-radius:var(--radius); padding:20px; }}
    .depot-kpis {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
                   gap:12px; margin-bottom:16px; }}
    .depot-kpi  {{ background:var(--bg3); border-radius:8px; padding:12px; }}
    .depot-kpi span {{ display:block; font-size:0.72rem; color:var(--text2); margin-bottom:4px; }}
    .depot-kpi strong {{ font-size:0.95rem; }}
    .depot-chart {{ width:100%; height:70px; display:block;
                    background:var(--bg3); border-radius:8px; margin-bottom:16px; }}
    .depot-pos, .depot-trade {{ display:flex; align-items:center; gap:12px; padding:7px 0;
                                 border-bottom:1px solid var(--border); font-size:0.82rem; }}
    .depot-pos:last-child, .depot-trade:last-child {{ border:none; }}
    .dp-asset {{ font-weight:700; width:50px; flex-shrink:0; }}
    .dp-info  {{ color:var(--text2); }}
    .dp-stop  {{ color:var(--rot); }}
    .korr-box {{ background:var(--bg3); border-radius:8px; padding:14px; margin-top:16px; }}
    .korr-box h4 {{ color:var(--text2); margin-bottom:10px; font-size:0.85rem; }}
    .korr-zeile {{ display:flex; align-items:center; gap:8px; padding:4px 0;
                   border-bottom:1px solid var(--border); font-size:0.8rem; }}
    .korr-zeile:last-of-type {{ border:none; }}
    .korr-asset {{ font-weight:700; width:48px; flex-shrink:0; }}
    .korr-balken {{ letter-spacing:-1px; width:70px; flex-shrink:0; }}
    .korr-wert {{ font-weight:600; width:38px; flex-shrink:0; }}
    .korr-text {{ color:var(--text2); flex:1; overflow:hidden;
                  white-space:nowrap; text-overflow:ellipsis; }}
    .korr-verstaerkt {{ color:var(--gruen); font-size:0.78rem; margin-top:8px; }}
    .korr-warnung {{ color:var(--gelb); font-size:0.78rem; margin-top:6px; }}
    .korr-verwandte {{ margin-top:10px; font-size:0.78rem; color:var(--text2); }}
    .korr-verwandte span {{ display:inline-block; background:var(--bg);
                            border:1px solid var(--border); padding:2px 8px;
                            border-radius:12px; margin:2px; color:var(--text); }}
    .strat-badge {{ font-size:0.72rem; padding:2px 8px; border-radius:20px; font-weight:700; }}
    .bt-badge {{ font-size:0.72rem; padding:2px 8px; border-radius:20px; font-weight:600; }}
    .bt-tabelle-wrap {{ overflow-x:auto; }}
    .bt-tabelle {{ width:100%; border-collapse:collapse; background:var(--bg2);
                   border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }}
    .bt-tabelle th {{ background:var(--bg3); padding:10px 16px; text-align:left;
                      font-size:0.78rem; color:var(--text2); text-transform:uppercase;
                      letter-spacing:.06em; }}
    .bt-tabelle td {{ padding:10px 16px; border-top:1px solid var(--border);
                      font-size:0.88rem; }}
    .bt-tabelle tr:hover td {{ background:var(--bg3); }}
    .footer {{ margin-top:48px; padding-top:16px; border-top:1px solid var(--border);
               color:var(--text2); font-size:0.78rem; line-height:1.8; }}
    @media (max-width:700px) {{
      body {{ padding:16px; }}
      .debatte-grid {{ grid-template-columns:1fr; }}
      .trade-box {{ grid-template-columns:repeat(2,1fr); }}
    }}
  </style>
</head>
<body>
  <h1>📊 Trading Intelligence System</h1>
  <p class="datum">Tagesbericht · {datum}</p>

  <h2>✅ Kaufen ({len(kaufen)})</h2>
  <div class="karten-grid">{kaufen_html}</div>

  {vk_sektion}

  <h2>⏸ Abwarten ({len(abwarten)})</h2>
  <div>{abwarten_chips}</div>

  {_lern_sektion(lern_ergebnis or {})}

  {_multi_depot_sektion(multi_stats or [])}

  {_depot_sektion(depot_stats)}

  {_retro_sektion(retro_ergebnisse or [])}

  {_backtest_sektion(backtest_ergebnisse)}

  <h2>📋 Detailberichte mit Live-Charts</h2>
  {detail_html}

  <div class="footer">
    Charts bereitgestellt von <a href="https://www.tradingview.com" style="color:var(--gruen);">TradingView</a>
    &nbsp;·&nbsp; Analyse: Trading Intelligence System
    &nbsp;·&nbsp; {datum}<br>
    <strong>Hinweis:</strong> Alle Empfehlungen dienen nur zur Information und stellen keine Anlageberatung dar.
    Eigene Recherche und Risikoabwägung sind erforderlich.
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Speichern & Browser oeffnen
# ---------------------------------------------------------------------------

def _lern_sektion(lern_ergebnis: dict) -> str:
    if not lern_ergebnis:
        return ""

    top_lehren   = lern_ergebnis.get("top_lehren", [])
    analysen     = lern_ergebnis.get("analysen",   [])
    trefferquote = lern_ergebnis.get("trefferquote", 0)
    gesamt       = lern_ergebnis.get("signale_gesamt", 0)
    fehler       = lern_ergebnis.get("fehler", 0)

    if not gesamt:
        return ""

    tq_farbe = "#00c896" if trefferquote >= 55 else ("#f0a500" if trefferquote >= 40 else "#ff4d6d")

    # Fehleranalysen
    fehler_html = ""
    for a in analysen[:3]:
        if not hasattr(a, "ki_analyse") or not a.ki_analyse:
            continue
        zeilen = [z.strip() for z in a.ki_analyse.splitlines() if z.strip()][:5]
        text   = "<br>".join(zeilen)
        fehler_html += f"""
        <div class="lern-fehler">
          <div class="lf-header">
            <span class="lf-asset">{a.asset}</span>
            <span class="lf-rendite" style="color:#ff4d6d;">{a.rendite_5d:+.1f}% in 5d</span>
            <span class="lf-datum">{a.datum_signal}</span>
          </div>
          <div class="lf-analyse">{text}</div>
        </div>"""

    # Top Lehren
    lehren_html = ""
    for l in top_lehren[:5]:
        lehren_html += f"""
        <div class="lern-lehre">
          <span class="ll-count">{l['haeufigkeit']}x</span>
          <span class="ll-text">{l['lehre']}</span>
        </div>"""

    return f"""
    <h2>🧠 Was das System gelernt hat</h2>
    <div class="lern-box">
      <div class="lern-stats">
        <div class="ls-item">
          <span>Signale geprueft</span><strong>{gesamt}</strong>
        </div>
        <div class="ls-item">
          <span>Trefferquote</span>
          <strong style="color:{tq_farbe};">{trefferquote:.1f}%</strong>
        </div>
        <div class="ls-item">
          <span>Fehler analysiert</span><strong>{fehler}</strong>
        </div>
      </div>
      {"<h4>Fehleranalysen</h4>" + fehler_html if fehler_html else ""}
      {"<h4>Kumulierte Erkenntnisse</h4>" + lehren_html if lehren_html else "<p class='leer'>Noch keine Erkenntnisse — waechst taeglich.</p>"}
    </div>"""


def _multi_depot_sektion(multi_stats: list) -> str:
    """Rendert den Strategie-Vergleich aller 4 Depots."""
    if not multi_stats:
        return ""

    farben = {"MOMENTUM": "#f0a500", "VALUE": "#8b5cf6",
               "BALANCED": "#00c896", "PATTERN": "#38bdf8"}
    emoji  = {"MOMENTUM": "🚀", "VALUE": "💎", "BALANCED": "⚖️", "PATTERN": "📊"}

    karten = ""
    for s in multi_stats:
        pnl    = s["pnl_eur"]
        farbe  = farben.get(s["strategie"], "#888")
        pfarbe = "#00c896" if pnl >= 0 else "#ff4d6d"
        karten += f"""
        <div class="md-karte" style="border-top:3px solid {farbe};">
          <div class="md-header">
            <span>{emoji.get(s['strategie'],'')}</span>
            <span class="md-name">{s['strategie']}</span>
          </div>
          <div class="md-wert">{s['depotwert']:,.2f} EUR</div>
          <div class="md-pnl" style="color:{pfarbe};">{pnl:+.2f} EUR ({s['pnl_pct']:+.1f}%)</div>
          <div class="md-meta">
            Treffer: {s['trefferquote']:.0f}% &nbsp;|&nbsp;
            Offen: {s['trades_offen']} &nbsp;|&nbsp;
            Trades: {s['trades_gesamt']}
          </div>
        </div>"""

    return f"""
    <h2>🏆 Strategie-Vergleich (4 Musterdepots)</h2>
    <div class="md-grid">{karten}</div>"""


def _depot_sektion(stats: dict) -> str:
    """Rendert den Musterdepot-Bereich im Dashboard."""
    if not stats:
        return ""
    pnl      = stats["gesamt_pnl_eur"]
    pnl_pct  = stats["gesamt_pnl_pct"]
    pnl_farbe = "#00c896" if pnl >= 0 else "#ff4d6d"
    pf       = stats["profit_factor"]
    pf_farbe = "#00c896" if pf >= 1.5 else ("#f0a500" if pf >= 1.0 else "#ff4d6d")

    # Verlaufschart (mini, nur letzten 30 Tage)
    verlauf     = stats.get("verlauf", [])[-30:]
    chart_html  = ""
    if len(verlauf) > 1:
        werte    = [v["depotwert"] for v in verlauf if v["depotwert"] is not None]
        if not werte:
            werte = [0.0]
        min_w    = min(werte)
        max_w    = max(werte)
        spanne   = max_w - min_w if max_w != min_w else 1
        punkte   = " ".join(
            f"{int(i / (len(werte)-1) * 280)},{int((1 - (w - min_w) / spanne) * 60)}"
            for i, w in enumerate(werte)
        )
        chart_farbe = "#00c896" if werte[-1] >= werte[0] else "#ff4d6d"
        chart_html = f"""
        <svg viewBox="0 0 280 70" class="depot-chart">
          <polyline points="{punkte}" fill="none" stroke="{chart_farbe}" stroke-width="2"/>
        </svg>"""

    # Offene Positionen
    offene_html = ""
    for p in stats.get("offene_positionen", []):
        offene_html += f"""
        <div class="depot-pos">
          <span class="dp-asset">{p['asset']}</span>
          <span class="dp-info">Einstieg ${p['einstieg_preis']:,.2f}</span>
          <span class="dp-info">Ziel ${p['ziel_preis']:,.2f}</span>
          <span class="dp-info dp-stop">SL ${p['stop_loss_preis']:,.2f}</span>
          <span class="dp-info">Inv {p['investiert_eur']:,.0f} EUR</span>
        </div>"""

    # Letzte Trades
    trades_html = ""
    for p in reversed(stats.get("letzten_trades", [])[-5:]):
        farbe = "#00c896" if p["pnl_eur"] > 0 else "#ff4d6d"
        icon  = "✓" if p["pnl_eur"] > 0 else "✗"
        trades_html += f"""
        <div class="depot-trade">
          <span style="color:{farbe};font-weight:700;">{icon}</span>
          <span class="dp-asset">{p['asset']}</span>
          <span class="dp-info">{p['schluss_datum']}</span>
          <span style="color:{farbe};font-weight:600;">{p['pnl_eur']:+,.2f} EUR</span>
          <span style="color:{farbe};">({p['pnl_pct']:+.1f}%)</span>
          <span class="dp-info">[{p['status']}]</span>
        </div>"""

    return f"""
    <h2>💼 Musterdepot (Paper Trading)</h2>
    <div class="depot-box">
      <div class="depot-kpis">
        <div class="depot-kpi">
          <span>Depotwert</span>
          <strong>{stats['depotwert']:,.2f} EUR</strong>
        </div>
        <div class="depot-kpi">
          <span>Gesamt P&L</span>
          <strong style="color:{pnl_farbe};">{pnl:+,.2f} EUR ({pnl_pct:+.2f}%)</strong>
        </div>
        <div class="depot-kpi">
          <span>Trefferquote</span>
          <strong>{stats['trefferquote']:.1f}%</strong>
        </div>
        <div class="depot-kpi">
          <span>Profit Factor</span>
          <strong style="color:{pf_farbe};">{pf:.2f}</strong>
        </div>
        <div class="depot-kpi">
          <span>Trades gesamt</span>
          <strong>{stats['trades_gesamt']} ({stats['trades_offen']} offen)</strong>
        </div>
        <div class="depot-kpi">
          <span>Cash</span>
          <strong>{stats['cash']:,.2f} EUR</strong>
        </div>
      </div>
      {chart_html}
      {"<h4 style='margin:16px 0 8px;font-size:0.85rem;color:var(--text2)'>Offene Positionen</h4>" + offene_html if offene_html else ""}
      {"<h4 style='margin:16px 0 8px;font-size:0.85rem;color:var(--text2)'>Letzte abgeschlossene Trades</h4>" + trades_html if trades_html else "<p class='leer'>Noch keine abgeschlossenen Trades — das System lernt gerade.</p>"}
    </div>"""


def _strategie_badge(e: dict) -> str:
    s = e.get("strategie", "")
    farben = {"SHORT": "#00c896", "MEDIUM": "#f0a500", "LONG": "#8b5cf6"}
    farbe  = farben.get(s, "#888")
    if not s:
        return ""
    tage   = e.get("haltezeit_tage", "")
    be     = e.get("breakeven_pct", 0)
    return f'<span class="strat-badge" style="background:{farbe}20;color:{farbe};border:1px solid {farbe}40;">{s} ~{tage}d · BE +{be:.1f}%</span>'


def _retro_sektion(retro_ergebnisse: list) -> str:
    if not retro_ergebnisse:
        return ""
    zeilen = ""
    for r in retro_ergebnisse[:10]:
        beste_n = max(r.netto_5d_eur, r.netto_10d_eur, r.netto_20d_eur)
        farbe   = "#00c896" if beste_n > 0 else "#ff4d6d"
        beste_label = {"5d":"Short","10d":"Medium","20d":"Long"}.get(r.beste_strategie,"–")
        zeilen += f"""
        <tr>
          <td style="font-weight:700">{r.asset}</td>
          <td>{r.analyse_datum}</td>
          <td>${r.einstieg_preis:,.2f}</td>
          <td style="color:{'#00c896' if r.rendite_5d_pct>0 else '#ff4d6d'}">{r.rendite_5d_pct:+.1f}%</td>
          <td style="color:{'#00c896' if r.rendite_10d_pct>0 else '#ff4d6d'}">{r.rendite_10d_pct:+.1f}%</td>
          <td style="color:{'#00c896' if r.rendite_20d_pct>0 else '#ff4d6d'}">{r.rendite_20d_pct:+.1f}%</td>
          <td style="color:{farbe};font-weight:700">{beste_label}</td>
        </tr>"""
    return f"""
    <h2>🔄 Retro-Analyse (was wäre gewesen?)</h2>
    <div class="bt-tabelle-wrap">
      <table class="bt-tabelle">
        <thead><tr>
          <th>Asset</th><th>Signal-Datum</th><th>Einstieg</th>
          <th>5 Tage</th><th>10 Tage</th><th>20 Tage</th>
          <th>Beste Strategie</th>
        </tr></thead>
        <tbody>{zeilen}</tbody>
      </table>
    </div>"""


def speichere_und_oeffne(ergebnisse: list[dict], backtest_ergebnisse: list = None, depot_stats: dict = None, retro_ergebnisse: list = None, multi_stats: list = None, lern_ergebnis: dict = None) -> str:
    os.makedirs("output", exist_ok=True)
    datum   = datetime.now().strftime("%d.%m.%Y %H:%M Uhr")
    datei   = datetime.now().strftime("output/dashboard_%Y-%m-%d_%H%M.html")
    aktuell = "output/dashboard_aktuell.html"

    html = erstelle_html(ergebnisse, datum, backtest_ergebnisse or [], depot_stats,
                         retro_ergebnisse or [], multi_stats, lern_ergebnis)
    with open(datei,   "w", encoding="utf-8") as f:
        f.write(html)
    with open(aktuell, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Dashboard gespeichert: {datei}")
    # Browser nur lokal oeffnen, nicht in CI/GitHub Actions
    if not os.environ.get("CI"):
        webbrowser.open(f"file:///{os.path.abspath(aktuell).replace(os.sep, '/')}")
    return datei


# ---------------------------------------------------------------------------
# Demo-Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo = [
        {
            "asset": "MSFT", "asset_typ": "aktie", "preis": 443.90,
            "technisches_signal": "KAUFEN", "news_sentiment": "neutral", "news_anzahl": 2,
            "technische_punkte": 3, "gesamt_punkte": 1.8,
            "bull_argumente": "1. Starke Azure Cloud-Sparte mit 30% Wachstum\n2. Solider Aufwärtstrend über MA20 und MA50\n3. RSI bei 69 – nicht überkauft\n4. KI-Integration in alle Produkte\n5. Stabile Dividendenhistorie",
            "bear_argumente": "1. Hohe Bewertung – KGV über Branchendurchschnitt\n2. Wachsendes AWS-Risiko im Cloud-Segment\n3. Regulierungsdruck in der EU\n4. RSI nähert sich überkauftem Bereich\n5. Makroökonomische Unsicherheit",
            "ki_analyse": "LAGE: Microsoft befindet sich in einem klaren Aufwärtstrend gestützt durch starkes Cloud-Wachstum.\n\nSTÄRKEN:\n- Azure wächst überproportional\n- RSI im neutralen Bereich bietet Einstiegschance\n- KI-Produkte treiben Umsatz\n\nRISIKEN:\n- Hohe Bewertung lässt wenig Puffer bei Enttäuschungen\n- Wettbewerb durch Amazon und Google\n\nFAZIT: Solide Kaufgelegenheit mit mittlerem Risiko.",
            "finale": {
                "empfehlung": "KAUFEN", "einstieg": 443.90, "ziel": 488.29,
                "stop_loss": 421.70, "risiko": "MITTEL",
                "gewinner": "BULL",
                "begruendung": "Die starke Marktposition von Microsoft und das Cloud-Wachstum überwiegen die Bewertungsbedenken.",
            },
        },
        {
            "asset": "BTC", "asset_typ": "krypto", "preis": 73955.0,
            "technisches_signal": "HALTEN / ABWARTEN", "news_sentiment": "neutral", "news_anzahl": 18,
            "technische_punkte": 0, "gesamt_punkte": 0.0,
            "bull_argumente": "1. RSI bei 22 – historisch starkes Kaufsignal\n2. Institutionelle Nachfrage bleibt hoch\n3. Bitcoin ETF-Zuflüsse stabilisieren Markt",
            "bear_argumente": "1. Kein Trendwechsel technisch bestätigt\n2. Unter MA20 und MA50\n3. Makroökonomischer Gegenwind",
            "ki_analyse": "LAGE: Bitcoin befindet sich in einer Konsolidierungsphase nach dem jüngsten Rückgang.\n\nSTÄRKEN:\n- RSI stark überverkauft – Erholungspotenzial vorhanden\n\nRISIKEN:\n- Kein bestätigter Trendwechsel\n- Breakout nach unten möglich\n\nFAZIT: Abwarten bis technische Bestätigung vorliegt.",
            "finale": {
                "empfehlung": "ABWARTEN", "einstieg": 73955.0, "ziel": 85000.0,
                "stop_loss": 68000.0, "risiko": "HOCH",
                "gewinner": "BEAR",
                "begruendung": "Kein technischer Trendwechsel bestätigt – Geduld zahlt sich aus.",
            },
        },
    ]
    speichere_und_oeffne(demo)
    print("Demo-Dashboard geöffnet.")
