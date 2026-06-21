"""
GMx SMTP Mail-Integration für Immobilien-Scanner Reports
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime


def send_report(properties: List[Dict], config: Dict) -> bool:
    """
    Sendet einen HTML-Report mit den Top-Immobilien via GMx

    Args:
        properties: Evaluierte Immobilien-Liste (von evaluator.py)
        config: Config-Dict mit Mail-Einstellungen

    Returns:
        True bei Erfolg, False bei Fehler
    """

    smtp_user = os.getenv("GMX_USER")
    smtp_password = os.getenv("GMX_APP_PASSWORD")

    if not smtp_user or not smtp_password:
        print("❌ FEHLER: GMX_USER oder GMX_APP_PASSWORD nicht gesetzt (.env)")
        return False

    # Top 5-10 nach Score filtern
    top_props = sorted(properties, key=lambda x: x.get("score", 0), reverse=True)[:10]

    if not top_props:
        print("⚠️  Keine empfehlenswerten Immobilien gefunden diese Woche")
        return False

    # HTML-Report bauen
    html = build_html_report(top_props, config)

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


def build_html_report(properties: List[Dict], config: Dict) -> str:
    """
    Erstellt einen formatierten HTML-Report
    """

    rows = ""
    for i, prop in enumerate(properties, 1):
        # Farbe nach Score
        if prop["score"] >= 80:
            color = "#d4edda"  # Grün
        elif prop["score"] >= 60:
            color = "#fff3cd"  # Gelb
        else:
            color = "#f8d7da"  # Rot

        rote_flaggen = "<br>".join(f"⚠️ {f}" for f in prop.get("rote_flaggen", []))
        positive = "<br>".join(f"✅ {f}" for f in prop.get("positive_merkmale", []))

        rows += f"""
        <tr style="background-color: {color};">
            <td style="padding: 12px; border-bottom: 1px solid #ddd;"><strong>{i}. {prop['adresse']}</strong></td>
            <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: right;">
                <strong style="font-size: 18px; color: #2c3e50;">{prop['score']}/100</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #ddd;">
                Kaufpreis: <strong>{prop['kaufpreis']:,}€</strong><br>
                Wohnungen: <strong>{prop['wohnungen']}</strong><br>
                Baujahr: <strong>{prop['baujahr']}</strong>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #ddd;">
                Cashflow: <strong style="color: #27ae60;">{prop['netto_cashflow']}€/Monat</strong><br>
                Rendite: <strong>{prop['netto_rendite']:.1f}%</strong> p.a.
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #ddd; font-size: 12px;">
                <strong>Rote Flaggen:</strong><br>{rote_flaggen or "✅ Keine"}<br><br>
                <strong>Pluspunkte:</strong><br>{positive or "—"}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: center;">
                <a href="{prop['link']}" style="color: #3498db; text-decoration: none;">
                    <strong>Link →</strong>
                </a>
            </td>
        </tr>
        """

    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 12px; border-bottom: 1px solid #ddd; }}
            .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ font-size: 12px; color: #7f8c8d; margin-top: 30px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏘️ Immobilien-Scanner Report</h1>
            <p><strong>Woche vom {datetime.now().strftime('%d.%m.%Y')}</strong> | Region: Oberhausen (46149)</p>

            <div class="summary">
                <p><strong>Diese Woche:</strong> {len(properties)} Immobilien analysiert</p>
                <p><strong>Empfehlungen:</strong> {len(properties)} interessant</p>
                <p><strong>Durchschnitt-Score:</strong> {sum(p.get('score', 0) for p in properties) / len(properties):.0f}/100</p>
            </div>

            <h2>Top 10 Objekte (nach Score rankiert)</h2>
            <table>
                <thead>
                    <tr style="background-color: #3498db; color: white;">
                        <th>Adresse</th>
                        <th>Score</th>
                        <th>Eckdaten</th>
                        <th>Finanzen</th>
                        <th>Risiken & Chancen</th>
                        <th>Quelle</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>

            <h2>Bewertungs-Legende</h2>
            <ul>
                <li><strong style="color: #27ae60;">80+:</strong> Sehr gute Rendite, wenig Risiken → Aktiv prüfen</li>
                <li><strong style="color: #f39c12;">60-80:</strong> Gute Rendite, moderate Risiken → Detailanalyse empfohlen</li>
                <li><strong style="color: #e74c3c;">< 60:</strong> Schwache Rendite oder hohe Risiken → Nur bei special Interest</li>
            </ul>

            <h2>Nächste Schritte</h2>
            <ol>
                <li>Top-Objekte in vollständiger Maklerbeschreibung prüfen (Exposé lesen)</li>
                <li><strong>Rote Flaggen checken:</strong> Baujahr → Besichtigung mit Fachmann</li>
                <li>Vor Kaufvertrag: <strong>Bankfinanzierung vorab klären</strong> (LTV 80%, Zins~4%)</li>
                <li>Mietermarkt Oberhausen: 950€ Kaltmiete ist realistisch für 3-4 Zimmer</li>
            </ol>

            <div class="footer">
                <p>Automatisiert generiert von Immobilien-Scanner | {datetime.now().strftime('%d.%m.%Y %H:%M')} Uhr</p>
                <p>Disclaimer: Dies ist eine automatische Analyse, keine Anlageberatung. Vor Kauf immer Experten konsultieren.</p>
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

    test_props = [
        {
            "adresse": "Musterstraße 42, 46149 Oberhausen",
            "kaufpreis": 450000,
            "wohnungen": 4,
            "baujahr": 1985,
            "netto_cashflow": 637,
            "netto_rendite": 8.5,
            "score": 72,
            "rote_flaggen": ["Baujahr 1985: Wahrscheinlich feuchte Keller"],
            "positive_merkmale": ["Garage", "Garten"],
            "link": "https://example.com/1"
        }
    ]

    # Nur HTML generieren (nicht versenden) für Test
    html = build_html_report(test_props, config)
    with open("test_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Test-Report generiert: test_report.html")
