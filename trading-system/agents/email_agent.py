"""
Email-Agent
Liest taeglich Trading-Informationen aus einem GMX-Postfach
und extrahiert relevante Signale daraus.

Konfiguration in .env:
  GMX_EMAIL            = deine@gmx.de
  GMX_PASSWORT         = dein_passwort
  EMAIL_ABSENDER_FILTER = absender1@x.com, absender2@y.com, absender3@z.com
                          (kommagetrennte Liste; leer = alle Emails der letzten 25h lesen)

Mehrere Newsletter koennen einfach als Komma-Liste eingetragen werden.
Die Werbe-Erkennung filtert automatisch nicht-relevante Emails heraus.
"""

import sys
import os
import imaplib
import email as email_lib
import re
from email.header import decode_header
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GMX_IMAP_SERVER = "imap.gmx.net"
GMX_IMAP_PORT   = 993

GMX_EMAIL    = os.environ.get("GMX_EMAIL", "")
GMX_PASSWORT = os.environ.get("GMX_PASSWORT", "")

# Kommagetrennte Liste — z.B. "daily@finanzfluss.de, report@wikifolio.com, signal@..."
_absender_raw = os.environ.get("EMAIL_ABSENDER_FILTER", "")
ABSENDER_LISTE: list[str] = [a.strip() for a in _absender_raw.split(",") if a.strip()]


# ---------------------------------------------------------------------------
# Datenstruktur
# ---------------------------------------------------------------------------

@dataclass
class EmailSignal:
    datum: str
    betreff: str
    absender: str
    inhalt_roh: str
    newsletter_quelle: str = ""       # Welcher der konfigurierten Absender
    gefundene_ticker: list[str] = field(default_factory=list)
    richtung: str = "neutral"         # "bullish", "bearish", "neutral"
    sentiment_punkte: int = 0
    zusammenfassung: str = ""


# ---------------------------------------------------------------------------
# IMAP-Verbindung
# ---------------------------------------------------------------------------

def verbinde_gmx() -> imaplib.IMAP4_SSL | None:
    """Stellt eine IMAP-Verbindung zu GMX her."""
    if not GMX_EMAIL or not GMX_PASSWORT:
        print("  [Email] GMX_EMAIL oder GMX_PASSWORT fehlen in .env")
        return None
    try:
        mail = imaplib.IMAP4_SSL(GMX_IMAP_SERVER, GMX_IMAP_PORT)
        mail.login(GMX_EMAIL, GMX_PASSWORT)
        return mail
    except imaplib.IMAP4.error as e:
        print(f"  [Email] Login fehlgeschlagen: {e}")
        print("  Tipp: IMAP in GMX-Einstellungen aktivieren und Passwort pruefen.")
        return None
    except Exception as e:
        print(f"  [Email] Verbindungsfehler: {e}")
        return None


def trenne_gmx(mail: imaplib.IMAP4_SSL):
    """Schliesst die IMAP-Verbindung sauber."""
    try:
        mail.logout()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Emails lesen (multi-sender-faehig)
# ---------------------------------------------------------------------------

def _dekodiere_header(wert: str) -> str:
    """Dekodiert Email-Header (oft base64 oder quoted-printable)."""
    teile = decode_header(wert)
    ergebnis = ""
    for inhalt, kodierung in teile:
        if isinstance(inhalt, bytes):
            ergebnis += inhalt.decode(kodierung or "utf-8", errors="replace")
        else:
            ergebnis += str(inhalt)
    return ergebnis


def _extrahiere_text(msg) -> str:
    """Extrahiert den Plaintext aus einer Email (auch multipart)."""
    text = ""
    if msg.is_multipart():
        for teil in msg.walk():
            content_type = teil.get_content_type()
            if content_type == "text/plain":
                try:
                    charset = teil.get_content_charset() or "utf-8"
                    text += teil.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    pass
            elif content_type == "text/html" and not text:
                # HTML als Fallback, Tags entfernen
                try:
                    charset = teil.get_content_charset() or "utf-8"
                    html = teil.get_payload(decode=True).decode(charset, errors="replace")
                    text += re.sub(r'<[^>]+>', ' ', html)
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    text = re.sub(r'<[^>]+>', ' ', text)
        except Exception:
            pass
    # Mehrfache Leerzeichen/Newlines bereinigen
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _hole_email_ids_fuer_absender(
    mail: imaplib.IMAP4_SSL,
    absender: str,
    datum_str: str,
) -> list[bytes]:
    """
    Sucht ungelesene Email-IDs fuer einen bestimmten Absender.
    Nur UNSEEN-Emails werden zurueckgegeben — bereits gelesene werden nie doppelt verarbeitet.
    Datum-Filter als Sicherheitsnetz damit alte Stapel-Emails ignoriert werden.
    """
    try:
        # UNSEEN = nur ungelesene; SINCE = Sicherheitsnetz (max. 30 Tage alt)
        status, ids = mail.search(None, f'UNSEEN FROM "{absender}" SINCE {datum_str}')
        if status == "OK" and ids[0]:
            return ids[0].split()
    except Exception as e:
        print(f"    [Email] Suchfehler fuer '{absender}': {e}")
    return []


def _lade_email_by_id(mail: imaplib.IMAP4_SSL, email_id: bytes, als_gelesen_markieren: bool = True) -> dict | None:
    """
    Laedt eine einzelne Email anhand ihrer ID.
    Markiert sie danach als gelesen (\\Seen) damit sie beim naechsten Lauf
    nicht erneut verarbeitet wird.
    """
    try:
        status, daten = mail.fetch(email_id, "(RFC822)")
        if status != "OK":
            return None
        msg      = email_lib.message_from_bytes(daten[0][1])
        betreff  = _dekodiere_header(msg.get("Subject", ""))
        absender = _dekodiere_header(msg.get("From", ""))
        datum    = msg.get("Date", "")
        text     = _extrahiere_text(msg)

        # Als gelesen markieren — verhindert Doppelverarbeitung bei naechstem Lauf
        if als_gelesen_markieren:
            try:
                mail.store(email_id, "+FLAGS", "\\Seen")
            except Exception:
                pass  # Kein kritischer Fehler falls Markierung fehlschlaegt

        return {
            "betreff":  betreff,
            "absender": absender,
            "datum":    datum,
            "text":     text[:5000],
        }
    except Exception as e:
        print(f"    [Email] Fehler beim Laden von ID {email_id}: {e}")
        return None


def _absender_stimmt_ueberein(email_absender: str, filter_absender: str) -> bool:
    """Prueft ob der Email-Absender zum Filter passt (Teilstring-Match)."""
    ea = email_absender.lower()
    fa = filter_absender.lower()
    # Exakter Match oder Domain/Name-Teil-Match
    return fa in ea or ea.endswith(fa)


def lese_emails(stunden_zurueck: int = 25) -> list[dict]:
    """
    Liest alle UNGELESENEN Emails der konfigurierten Newsletter-Absender.
    Nach dem Lesen werden Emails als gelesen markiert — keine Doppelverarbeitung.
    Sicherheitsnetz: max. 30 Tage alte Emails werden beruecksichtigt.
    """
    mail = verbinde_gmx()
    if not mail:
        return []

    emails: list[dict] = []
    gesehene_ids: set[bytes] = set()

    try:
        mail.select("INBOX")

        # Sicherheitsnetz: max. 30 Tage alte Emails beruecksichtigen
        # (verhindert dass ein jahrelanger Stapel unglesener Mails auf einmal verarbeitet wird)
        seit      = datetime.now(timezone.utc) - timedelta(days=30)
        datum_str = seit.strftime("%d-%b-%Y")

        if ABSENDER_LISTE:
            # Fuer jeden Absender einzeln suchen — nur UNGELESENE (UNSEEN)
            alle_ids: list[tuple[bytes, str]] = []
            for absender in ABSENDER_LISTE:
                ids = _hole_email_ids_fuer_absender(mail, absender, datum_str)
                neu = 0
                for eid in ids:
                    if eid not in gesehene_ids:
                        gesehene_ids.add(eid)
                        alle_ids.append((eid, absender))
                        neu += 1
                if neu > 0:
                    print(f"    [{absender}] → {neu} neue Email(s)")
                # else: kein Output um Logs sauber zu halten

            total = len(alle_ids)
            if total == 0:
                print("  [Email] Keine neuen Newsletter seit letztem Lauf.")
                return []
            print(f"  [Email] {total} neue Email(s) von {len(ABSENDER_LISTE)} Newsletter(n).")

            # Max 20 insgesamt verarbeiten
            for eid, quelle in alle_ids[-20:]:
                em = _lade_email_by_id(mail, eid, als_gelesen_markieren=True)
                if em:
                    em["newsletter_quelle"] = quelle
                    emails.append(em)

        else:
            # Kein Absender-Filter — alle UNGELESENEN der letzten 30 Tage (Ad-Filter greift)
            status, ids = mail.search(None, f'UNSEEN SINCE {datum_str}')
            if status != "OK" or not ids[0]:
                print("  [Email] Keine ungelesenen Emails gefunden.")
                return []
            id_liste = ids[0].split()
            print(f"  [Email] {len(id_liste)} ungelesene Email(s) in INBOX.")
            for eid in id_liste[-20:]:  # Max 20 neueste
                em = _lade_email_by_id(mail, eid, als_gelesen_markieren=True)
                if em:
                    em["newsletter_quelle"] = ""
                    emails.append(em)

    except Exception as e:
        print(f"  [Email] Fehler beim Lesen: {e}")
    finally:
        trenne_gmx(mail)

    return emails


# ---------------------------------------------------------------------------
# Werbe-Erkennung
# ---------------------------------------------------------------------------

WERBE_BETREFF_KW = [
    "angebot", "rabatt", "sale", "deal", "promo", "promotion",
    "sonderangebot", "jetzt kaufen", "nur heute", "limited", "exklusiv",
    "einladung", "webinar", "event", "veranstaltung", "kostenlos testen",
    "gratis", "free trial", "upgrade", "premium", "abonnement", "abo",
    "unsubscribe", "abmelden", "nicht mehr", "partner", "sponsored",
    "advertisement", "werbung", "anzeige",
    "willkommen", "welcome", "bestätige", "bestatige", "klick", "anmeldung",
    "umfrage", "input", "feedback", "noch mehr", "gefällig", "empfehlung",
    "weitere briefings", "perfekt zu dir", "mach besser", "noch besser",
]

REPORT_BETREFF_KW = [
    "signal", "analyse", "report", "update", "markt", "trading", "aktie",
    "krypto", "crypto", "empfehlung", "watchlist", "scan", "alert",
    "daily", "taeglich", "morning", "evening", "weekly", "briefing",
    "portfolio", "ticker", "crunch", "insight", "research", "analyse",
    "hot stock", "kaufen", "sell", "short", "long", "bullish", "bearish",
]


def ist_werbung(betreff: str, text: str) -> tuple[bool, str]:
    """
    Erkennt ob eine Email Werbung ist oder ein echter Trading-Report.
    Gibt (ist_werbung, begruendung) zurueck.
    """
    betreff_lower = betreff.lower()
    text_lower    = text[:500].lower()
    kombiniert    = betreff_lower + " " + text_lower

    # Harte Ausschlusskriterien
    if any(kw in betreff_lower for kw in ["unsubscribe", "abmelden", "werbung", "anzeige"]):
        return True, "Betreff enthaelt Werbe-Indikator"

    # Werbe-/Report-Treffer
    werbe_treffer  = [kw for kw in WERBE_BETREFF_KW  if kw in kombiniert]
    report_treffer = [kw for kw in REPORT_BETREFF_KW if kw in kombiniert]

    werbe_score  = len(werbe_treffer)  * 2
    report_score = len(report_treffer) * 2

    # Viele Links = Werbung
    link_anzahl = text_lower.count("http")
    if link_anzahl > 8:
        werbe_score += 3

    # Sehr kurz + wenig Zahlen = Werbung
    zahlen_anzahl = sum(1 for c in text[:500] if c.isdigit())
    if len(text) < 200 and zahlen_anzahl < 5:
        werbe_score += 2

    if werbe_score > report_score and werbe_score >= 3:
        return True, f"Werbe-Score {werbe_score} > Report-Score {report_score} (Treffer: {werbe_treffer[:3]})"

    return False, f"Report-Score {report_score} (Treffer: {report_treffer[:3]})"


# ---------------------------------------------------------------------------
# Signal-Extraktion
# ---------------------------------------------------------------------------

# Bekannte Ticker-Pattern im Text erkennen
TICKER_PATTERN = re.compile(
    r'\b([A-Z]{2,5})\b(?:\s*[-/]\s*(?:Aktie|stock|ETF|USD|EUR))?'
)

# Bekannte Krypto-Namen
KRYPTO_NAMEN = {
    "Bitcoin": "BTC", "BTC": "BTC",
    "Ethereum": "ETH", "ETH": "ETH",
    "Solana": "SOL", "SOL": "SOL",
    "Ripple": "XRP", "XRP": "XRP",
    "Cardano": "ADA", "ADA": "ADA",
    "Dogecoin": "DOGE", "DOGE": "DOGE",
}

BULLISH_KW = [
    "kaufen", "buy", "long", "bullish", "steigen", "aufwaerts", "empfehlung",
    "kauf", "einstieg", "chance", "potential", "steigerung", "positiv",
    "outperform", "uebergewichten", "erholung", "breakout", "rallye",
]
BEARISH_KW = [
    "verkaufen", "sell", "short", "bearish", "fallen", "abwaerts", "warnung",
    "risiko", "verlust", "korrektur", "negativ", "untergewichten", "vorsicht",
    "absturz", "einbruch", "stopp", "crash",
]

# Woerter die KEINE Ticker sind
KEIN_TICKER = {
    "THE", "AND", "FOR", "BUY", "SELL", "EUR", "USD", "ETF", "RSI", "ATH",
    "ATL", "ALL", "NEW", "DAX", "ARE", "NOT", "BUT", "YOU", "CAN", "ITS",
    "YOUR", "THIS", "THAT", "FROM", "HAVE", "WITH", "BEEN", "WILL", "MORE",
    "THAN", "THEY", "WHAT", "ALSO", "INTO", "JUST", "LIKE", "SOME", "EACH",
    "ONE", "TWO", "GET", "NOW", "HOW", "HAS", "HAD", "HER", "HIS", "ITS",
    "OUR", "OUT", "OFF", "WHY", "WHO", "MAY", "USE", "DID", "END", "ANY",
    "TOP", "LOW", "HIGH", "WAS", "CEO", "CFO", "IPO", "API", "FAQ", "PDF",
    "HTML", "HTTP", "NEWS", "GDAX", "COIN", "CASH", "FUND", "REAL", "RATE",
}


def analysiere_email(email_dict: dict) -> "EmailSignal | None":
    """Gibt None zurueck wenn die Email als Werbung erkannt wird."""
    werbung, grund = ist_werbung(email_dict["betreff"], email_dict["text"])
    if werbung:
        print(f"    [Werbung uebersprungen] '{email_dict['betreff'][:50]}' — {grund}")
        return None
    return _analysiere_email_inhalt(email_dict)


def _analysiere_email_inhalt(email_dict: dict) -> EmailSignal:
    """Extrahiert Trading-Signale aus einer Email."""
    text     = (email_dict["betreff"] + " " + email_dict["text"]).lower()
    text_roh = email_dict["betreff"] + " " + email_dict["text"]

    # Ticker finden
    gefundene: list[str] = []
    for name, symbol in KRYPTO_NAMEN.items():
        if name.lower() in text:
            gefundene.append(symbol)

    # Aktien-Ticker (Grossbuchstaben 2-5 Zeichen)
    for match in TICKER_PATTERN.finditer(text_roh):
        ticker = match.group(1)
        if ticker not in KEIN_TICKER and len(ticker) >= 2:
            gefundene.append(ticker)

    gefundene = list(dict.fromkeys(gefundene))[:10]  # Duplikate entfernen

    # Sentiment
    bull_count = sum(1 for kw in BULLISH_KW if kw in text)
    bear_count = sum(1 for kw in BEARISH_KW if kw in text)
    punkte     = bull_count - bear_count

    if punkte >= 2:
        richtung = "bullish"
    elif punkte <= -2:
        richtung = "bearish"
    else:
        richtung = "neutral"

    zusammenfassung = email_dict["text"][:300].replace("\n", " ").strip()

    return EmailSignal(
        datum=email_dict["datum"],
        betreff=email_dict["betreff"],
        absender=email_dict["absender"],
        inhalt_roh=email_dict["text"][:1000],
        newsletter_quelle=email_dict.get("newsletter_quelle", ""),
        gefundene_ticker=gefundene,
        richtung=richtung,
        sentiment_punkte=punkte,
        zusammenfassung=zusammenfassung,
    )


def hole_email_signale() -> list[EmailSignal]:
    """Hauptfunktion: Liest Emails und gibt analysierte Signale zurueck."""
    if not GMX_EMAIL or not GMX_PASSWORT:
        print("  [Email] Nicht konfiguriert — wird uebersprungen.")
        return []

    if ABSENDER_LISTE:
        print(f"  Lese Emails von {len(ABSENDER_LISTE)} Newsletter(n):")
        for a in ABSENDER_LISTE:
            print(f"    - {a}")
    else:
        print("  Lese alle Emails der letzten 25h (kein Absender-Filter)...")

    emails = lese_emails(stunden_zurueck=25)

    signale: list[EmailSignal] = []
    for em in emails:
        sig = analysiere_email(em)
        if sig is None:
            continue
        signale.append(sig)
        quelle_info = f" [{sig.newsletter_quelle}]" if sig.newsletter_quelle else ""
        if sig.gefundene_ticker:
            print(f"    Email{quelle_info}: '{sig.betreff[:45]}' → "
                  f"Ticker: {sig.gefundene_ticker} | {sig.richtung}")
        else:
            print(f"    Email{quelle_info}: '{sig.betreff[:45]}' → {sig.richtung} (keine Ticker)")

    return signale


def signale_als_dict(signale: list[EmailSignal]) -> dict:
    """
    Konvertiert Email-Signale in ein Dict das der Aggregator versteht:
    {ticker: {"sentiment": "bullish/neutral/bearish", "quelle": "Email", ...}}
    """
    ergebnis: dict = {}
    for sig in signale:
        quelle_label = f"Email ({sig.newsletter_quelle})" if sig.newsletter_quelle else "Email"
        for ticker in sig.gefundene_ticker:
            if ticker not in ergebnis:
                ergebnis[ticker] = {
                    "sentiment": sig.richtung,
                    "punkte":    sig.sentiment_punkte,
                    "betreff":   sig.betreff,
                    "quelle":    quelle_label,
                }
            elif sig.richtung == "bullish":
                # Bullish gewinnt bei mehrfachem Auftreten
                ergebnis[ticker]["sentiment"] = "bullish"
                ergebnis[ticker]["quelle"]    = quelle_label
    return ergebnis


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Trading Intelligence System — Email-Agent\n")

    if not GMX_EMAIL:
        print("Noch nicht konfiguriert. Bitte in .env eintragen:")
        print("  GMX_EMAIL=deine@gmx.de")
        print("  GMX_PASSWORT=dein_passwort")
        print("  EMAIL_ABSENDER_FILTER=absender1@x.com, absender2@y.com")
    else:
        print(f"Konfiguriert fuer: {GMX_EMAIL}")
        if ABSENDER_LISTE:
            print(f"Newsletter-Filter ({len(ABSENDER_LISTE)}):")
            for a in ABSENDER_LISTE:
                print(f"  - {a}")
        else:
            print("Kein Absender-Filter — alle Emails werden gelesen.")
        print()

        signale = hole_email_signale()
        if signale:
            print(f"\n{len(signale)} Email(s) ausgewertet:")
            for sig in signale:
                quelle = f" [{sig.newsletter_quelle}]" if sig.newsletter_quelle else ""
                print(f"\n  Betreff : {sig.betreff}{quelle}")
                print(f"  Richtung: {sig.richtung} ({sig.sentiment_punkte:+d})")
                print(f"  Ticker  : {sig.gefundene_ticker}")
                print(f"  Vorschau: {sig.zusammenfassung[:150]}")

            print("\n--- Aggregierte Ticker-Signale ---")
            ticker_dict = signale_als_dict(signale)
            for ticker, info in ticker_dict.items():
                print(f"  {ticker}: {info['sentiment']} | {info['quelle']}")
        else:
            print("Keine relevanten Emails gefunden oder Verbindung fehlgeschlagen.")
