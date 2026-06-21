"""
GMx SMTP Mail-Integration für Immobilien-Scanner Reports
Zwei Kategorien: PROFIT (6%+) und FAMILY (0%+, PLZ 46149)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime


def send_report(properties: List[Dict], config: Dict) -> bool:
    """
    Sendet einen HTML-Report mit ZWEI Kategorien via GMx

    Args:
        properties: Evaluierte Immobilien-Liste
        config: Config-Dict mit Mail-Einstellungen

    Returns:
        True bei Erfolg, False bei Fehler
    """

    smtp_user = os.getenv("GMX_USER")
    smtp_password = os.getenv("GMX_APP_PASSWORD")

    if not smtp_user or not smtp_password:
        print("❌ FEHLER: GMX_USER oder GMX_APP_PASSWORD nicht gesetzt (.env)")
        return False

    # Filtern nach Kategorie
    profit_props = [p for p in properties if p.get("kategorie_profit", {}).get("qualifiziert", False)]
    family_props = [p for p in properties if p.get("kategorie_family", {}).get("qualifiziert", False)]

    # Top 10 pro Kategorie
    profit_top = sorted(profit_props, key=lambda x: x.get("kategorie_profit", {}).get("score", 0), reverse=True)[:10]
    family_top = sorted(family_props, key=lambda x: x.get("kategorie_family", {}).get("score", 0), reverse=True)[:10]

    if not profit_top and not family_top:
        print("⚠️  Keine empfehlenswerten Immobilien gefunden diese Woche")
        return False

    # HTML-Report bauen (beide Kategorien)
    html = build_html_report(profit_top, family_top, config)

    try:
        # Verbindung zu GMx
        server = smtplib.SMTP(config["mail"]["smtp_server"], config["mail"]["smtp_port"])
        server.starttls()
        server.login(smtp_user, smtp_password)

        # Email bauen
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{config['mail']['subject_prefix']} Wöchentlicher Report {datetime.now().strftime('%d.%m.%Y')}"
        msg["From"] = smtp_user
        msg["To"] = config["mail"]["to_email"]

        msg.attach(MIMEText(html, "html", "utf-8"))

        # Versenden
        server.sendmail(smtp_user, config["mail"]["to_email"], msg.as_string())
        server.quit()

        print(f"✅ Mail versendet an {config['mail']['to_email']}")
        return True

    except smtplib.SMTPException as e:
        print(f"❌ SMTP-Fehler: {e}")
        return False
    except Exception as e:
        print(f"❌ Fehler beim E-Mail-Versand: {e}")
        return False


def build_html_report(profit_props: List[Dict], family_props: List[Dict], config: Dict) -> str:
    """
    Erstellt einen HTML-Report mit ZWEI Kategorien
    """

    def build_category_rows(properties: List[Dict], category_key: str) -> str:
        """Hilfsfunktion für Tabellenzeilen einer Kategorie"""
        rows = ""
        for i, prop in enumerate(properties, 1):
            cat = prop.get(category_key, {})
            score = cat.get("score", 0)

            # Farbe nach Score
            if score >= 70:
                color = "#d4edda"  # Grün
            elif score >= 50:
                color = "#fff3cd"  # Gelb
            else:
                color = "#f8d7da"  # Rot

            rote_flaggen = "<br>".join(f"⚠️ {f}" for f in prop.get("rote_flaggen", []))
            positive = "<br>".join(f"✅ {f}" for f in prop.get("positive_merkmale", []))

            rows += f"""
            <tr style="background-color: {color};">
                <td style="padding: 12px; border-bottom: 1px solid #ddd;"><strong>{i}. {prop['adresse']}</strong></td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">
                    <strong style="font-size: 18px; color: #2c3e50;">{score}/100</strong>
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">
                    <strong>{prop['kaufpreis']:,}€</strong><br>
                    {prop['wohnungen']} Whg | Baujahr {prop['baujahr']}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">
                    <strong>{prop['brutto_rendite']:.1f}%</strong> Brutto<br>
                    <span style="color: #27ae60;"><strong>{prop['netto_cashflow']}€</strong>/Mo</span><br>
                    {prop['netto_rendite']:.1f}% auf EK
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; font-size: 11px;">
                    <strong>Risiken:</strong><br>{rote_flaggen or "✅ Keine"}<br><br>
                    <strong>Plus:</strong><br>{positive or "—"}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: center;">
                    <a href="{prop['link']}" style="color: #3498db; text-decoration: none; font-weight: bold;">
                        Link →
                    </a>
                </td>
            </tr>
            """
        return rows

    profit_rows = build_category_rows(profit_props, "kategorie_profit")
    family_rows = build_category_rows(family_props, "kategorie_family")

    # Zähler
    profit_count = len(profit_props)
    family_count = len(family_props)

    html_category_1 = ""
    if profit_props:
        html_category_1 = f"""
        <h2 style="color: #27ae60; border-bottom: 2px solid #27ae60; padding-bottom: 10px;">
            🏢 Kategorie 1: PROFIT (6%+ Rendite, Selbsttragend)
        </h2>
        <p><strong>{profit_count} Objekte</strong> | Ganz Oberhausen + Umgebung | Klassisches Investment</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: #27ae60; color: white;">
                    <th style="padding: 12px; text-align: left;">Adresse</th>
                    <th style="padding: 12px; text-align: right;">Score</th>
                    <th style="padding: 12px;">Eckdaten</th>
                    <th style="padding: 12px;">Rendite & Cashflow</th>
                    <th style="padding: 12px;">Risiken & Plus</th>
                    <th style="padding: 12px;">Quelle</th>
                </tr>
            </thead>
            <tbody>
                {profit_rows}
            </tbody>
        </table>
        """

    html_category_2 = ""
    if family_props:
        html_category_2 = f"""
        <h2 style="color: #e74c3c; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;">
            👨‍👩‍👧‍👦 Kategorie 2: FAMILY (0%+, PLZ 46149, für Eltern/Bekannte)
        </h2>
        <p><strong>{family_count} Objekte</strong> | Zentral 46149 | Vermietung an Familie (Rendite sekundär)</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background-color: #e74c3c; color: white;">
                    <th style="padding: 12px; text-align: left;">Adresse</th>
                    <th style="padding: 12px; text-align: right;">Score</th>
                    <th style="padding: 12px;">Eckdaten</th>
                    <th style="padding: 12px;">Rendite & Cashflow</th>
                    <th style="padding: 12px;">Risiken & Plus</th>
                    <th style="padding: 12px;">Quelle</th>
                </tr>
            </thead>
            <tbody>
                {family_rows}
            </tbody>
        </table>
        """

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 1400px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            h2 {{ margin-top: 40px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ padding: 12px; text-align: left; font-weight: bold; }}
            td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
            .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ font-size: 12px; color: #7f8c8d; margin-top: 30px; text-align: center; }}
            .legend {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .legend-item {{ margin: 8px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏘️ Immobilien-Scanner Report (ZWEI Kategorien)</h1>
            <p><strong>Woche vom {datetime.now().strftime('%d.%m.%Y')}</strong> | Region: Oberhausen (46149)</p>

            <div class="summary">
                <p><strong>Kategorie 1 (PROFIT):</strong> {profit_count} Objekte mit 6%+ Rendite (selbsttragend)</p>
                <p><strong>Kategorie 2 (FAMILY):</strong> {family_count} Objekte für Familie/Eltern (0%+ ok)</p>
                <p><strong>Gesamt:</strong> {profit_count + family_count} interessante Immobilien diese Woche</p>
            </div>

            {html_category_1}

            {html_category_2}

            <div class="legend">
                <h3>📋 Score-Legende</h3>
                <div class="legend-item"><strong style="color: #27ae60;">70-100:</strong> 🟢 Sehr empfohlen — aktiv prüfen</div>
                <div class="legend-item"><strong style="color: #f39c12;">50-70:</strong> 🟡 Prüfen — Potenzial vorhanden</div>
                <div class="legend-item"><strong style="color: #e74c3c;">< 50:</strong> 🔴 Nur bei speziellem Interest</div>
            </div>

            <div class="legend">
                <h3>🎯 Nächste Schritte</h3>
                <ol>
                    <li><strong>Kategorie 1 (PROFIT):</strong> Makler kontaktieren, Exposés anfordern, mit Bankberater finanzierbar checken</li>
                    <li><strong>Kategorie 2 (FAMILY):</strong> Mit Eltern besprechen, gemeinsam besichtigen, Verständigung über Vermietung/Nutzung</li>
                    <li>Rote Flaggen checken (Baujahr, Renovierungen) → Fachanwalt/Gutachter konsultieren</li>
                    <li>Price-Factor prüfen: Kaufpreis/Jahresmiete < 18 ist gut</li>
                </ol>
            </div>

            <div class="footer">
                <p>Automatisiert generiert von Immobilien-Scanner | {datetime.now().strftime('%d.%m.%Y %H:%M')} Uhr</p>
                <p><strong>Disclaimer:</strong> Dies ist eine automatische Analyse, keine Anlageberatung. Vor jedem Kauf Experten konsultieren!</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    # Test-Report
    import yaml
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    test_profit = [{
        "adresse": "Musterstraße 42, 46149 Oberhausen",
        "kaufpreis": 450000,
        "wohnungen": 4,
        "baujahr": 1985,
        "brutto_rendite": 7.2,
        "netto_cashflow": 637,
        "netto_rendite": 8.5,
        "rote_flaggen": ["Baujahr 1985"],
        "positive_merkmale": ["Garage", "Garten"],
        "link": "https://example.com/1",
        "kategorie_profit": {"score": 72, "qualifiziert": True}
    }]

    test_family = [{
        "adresse": "Königstr. 100, 46149 Oberhausen",
        "kaufpreis": 320000,
        "wohnungen": 2,
        "baujahr": 1995,
        "brutto_rendite": 2.8,
        "netto_cashflow": -150,
        "netto_rendite": -2.0,
        "rote_flaggen": [],
        "positive_merkmale": ["Zentral", "Garten"],
        "link": "https://example.com/2",
        "kategorie_family": {"score": 65, "qualifiziert": True}
    }]

    html = build_html_report(test_profit, test_family, config)
    with open("test_report_zwei_kategorien.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Test-Report generiert: test_report_zwei_kategorien.html")
