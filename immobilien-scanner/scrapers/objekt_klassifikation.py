"""
Zentrale Objekt-Klassifikation fuer alle Scraper.

Loest das Kernproblem: eine einzelne Eigentumswohnung INNERHALB eines
Mehrfamilienhauses darf NICHT als ganzes Mehrfamilienhaus (mehrere Einheiten)
bewertet werden. Sonst wird die Rendite massiv ueberschaetzt.

Rueckgabe von klassifiziere():
  kategorie         : "EINZELWOHNUNG" | "MFH" | "EFH" | "UNKLAR"
  wohnungen         : Anzahl vermietbarer Einheiten (Einzelwohnung/EFH = 1)
  ist_einzelwohnung : True bei einzelner Wohnung/Teileigentum
"""

import re
import unicodedata

WORTZAHL = {
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
}

# Begriffe, die eine EINZELNE Wohnung / Teileigentum bezeichnen
WOHNUNG_TOKENS = [
    "eigentumswohnung", "etagenwohnung", "maisonette", "penthouse",
    "dachgeschosswohnung", "erdgeschosswohnung", "obergeschosswohnung",
    "souterrainwohnung", "terrassenwohnung", "gartenwohnung",
    "apartment", "appartement", "teileigentum", "loft",
    "2-zimmer", "3-zimmer", "4-zimmer", "1-zimmer", "5-zimmer",
]

# Begriffe, die ein GANZES Mehrfamilien-/Renditeobjekt bezeichnen
MFH_TOKENS = [
    "mehrfamilienhaus", "mehrfamilienhäuser", "wohnhaus", "wohnanlage",
    "zinshaus", "renditeobjekt", "anlageobjekt", "wohn- und geschäftshaus",
    "geschäftshaus", "wohnensemble", "wohnpark", "wohnquartier",
]

# Einfamilien-/Reihenhaus (kein Mietmodell mit mehreren Parteien)
EFH_TOKENS = [
    "einfamilienhaus", "doppelhaushälfte", "doppelhaus", "reihenhaus",
    "reihenendhaus", "reihenmittelhaus", "bungalow", "villa", "stadthaus",
    "stadtvilla",
]


def _explicit_multiunit_sale(t: str) -> bool:
    """True nur wenn explizit MEHRERE Einheiten verkauft werden
    (N-Familienhaus mit Zahlwort, oder 'X Wohnungen/Einheiten/Parteien').
    Ein blosses 'Mehrfamilienhaus' zaehlt hier NICHT (kann Container sein)."""
    if re.search(r"(zwei|drei|vier|fünf|fuenf|sechs|sieben|acht|neun|zehn)familienh", t):
        return True
    if re.search(r"\d+\s*(?:wohnung|wohneinheit|einheit|partei|we\b|familienhäuser)", t):
        return True
    return False


def _count_units(t: str, wohnflaeche: int) -> int:
    """Einheiten eines ganzen Mehrfamilienobjekts schaetzen."""
    # 1. N-Familienhaus per Zahlwort (eindeutigster Fall)
    for wort, n in WORTZAHL.items():
        if f"{wort}familienhaus" in t:
            return n
    # 2. Explizite Zahl: "mit 24 Wohnungen", "8 Einheiten"
    m = re.search(r"(\d+)\s*(?:wohnung|wohneinheit|einheit|partei)", t)
    if m:
        return max(2, int(m.group(1)))
    # 3. Generisches MFH ohne Zahl -> ueber Wohnflaeche schaetzen (~70 m²/Einheit)
    if wohnflaeche and wohnflaeche >= 140:
        return max(2, round(wohnflaeche / 70))
    return 2  # konservativ


# Container-Phrasen: "... im/in [kleinem] (Zwei|Drei|Mehr)familienhaus" beschreibt
# das GEBAEUDE, in dem die verkaufte Wohnung liegt — NICHT das Verkaufsobjekt.
_CONTAINER_RE = re.compile(
    r"\b(?:im|in)\s+(?:einem\s+|einer\s+|dem\s+|kleinen\s+|kleinem\s+|gepflegten\s+|"
    r"gepflegtem\s+|gro(?:ß|ss)en\s+|gro(?:ß|ss)em\s+)*"
    r"(?:zwei|drei|vier|fünf|fuenf|sechs|mehr)?familienhaus\w*"
)


def klassifiziere(text: str, wohnflaeche: int = 0):
    """Klassifiziert ein Objekt anhand von Titel/Objekttyp-Text."""
    t = unicodedata.normalize("NFKC", text or "").lower()
    # Container-Erwaehnungen entfernen, damit "im Zweifamilienhaus" nicht als
    # 2-Einheiten-Verkauf zaehlt. Single-Signale werden auf dem Originaltext geprueft.
    t_clean = _CONTAINER_RE.sub(" ", t)

    # 0. Makler-Kuerzel (als ganze Woerter, nicht als Teilstring)
    if re.search(r"\bzfh\b", t_clean):
        return "MFH", 2, False
    if re.search(r"\b(efh|dhh|rh|rmh|reh)\b", t):
        return "EFH", 1, False
    if re.search(r"\b(etw|etgw)\b", t):
        return "EINZELWOHNUNG", 1, True

    hat_wohnung_token = any(tok in t for tok in WOHNUNG_TOKENS)
    # "... wohnung ..." als verkauftes Objekt (nicht "X wohnungen" = Gebaeude)
    hat_einzel_wohnung_wort = bool(
        re.search(r"\bwohnung\b", t) and not re.search(r"\d+\s*wohnung", t)
    )
    single_signal = hat_wohnung_token or hat_einzel_wohnung_wort

    # 1. Einzelne Wohnung gewinnt — auch wenn ein Familienhaus als Container
    #    im Text steht — solange NICHT explizit mehrere Einheiten verkauft werden.
    if single_signal and not _explicit_multiunit_sale(t_clean):
        return "EINZELWOHNUNG", 1, True

    # 2. Ganzes Mehrfamilien-/Renditeobjekt (Container-bereinigt pruefen)
    if any(tok in t_clean for tok in MFH_TOKENS) or _explicit_multiunit_sale(t_clean):
        return "MFH", _count_units(t_clean, wohnflaeche), False

    # 3. Einfamilien-/Reihenhaus
    if any(tok in t for tok in EFH_TOKENS):
        return "EFH", 1, False

    # 4. Unklar -> konservativ als 1 Einheit behandeln
    return "UNKLAR", 1, False


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        ("Maisonette-Wohnung mit 5 Zimmern, Garten und Stellplatz", "EINZELWOHNUNG", 1),
        ("Bezugsfreie Wohnung mit Einbauküche – Modernisiert & gepflegt in kleinem Mehrfamilienhaus", "EINFAM?", 1),
        ("Mehrfamilienhaus zum Kauf", "MFH", None),
        ("Dreifamilienhaus mit Garten", "MFH", 3),
        ("Fünffamilienhaus mit 3 freien Wohnungen - 78 m²", "MFH", 5),
        ("Drei Mehrfamilienhäuser mit 24 Wohnungen & 24 Balkone", "MFH", 24),
        ("Einfamilienhaus zum Kauf", "EFH", 1),
        ("Saniertes ZFH mit Garage, Sauna und Pool", "?", None),
        ("Schöne Eigentumswohnung in zentraler Lage", "EINZELWOHNUNG", 1),
        ("Renditeobjekt: Wohn- und Geschäftshaus", "MFH", None),
        ("Portfolio für Entwickler und Strategen: 7 Mehrfamilienhäuser", "MFH", None),
        ("3-Zimmer-Wohnung mit Balkon im 2. OG", "EINZELWOHNUNG", 1),
        ("Maisonette-Wohnung mit 5 Zimmern, Garten und Stellplatz im Zweifamilienhaus", "EINZELWOHNUNG", 1),
        ("Gepflegte Wohnung in einem kleinen Dreifamilienhaus", "EINZELWOHNUNG", 1),
        ("Charmante 2-Zimmer-Wohnung im Mehrfamilienhaus", "EINZELWOHNUNG", 1),
    ]
    print(f"{'Kategorie':14} {'WE':>3}  {'einzel':6}  Titel")
    for text, _exp, _we in tests:
        kat, we, einzel = klassifiziere(text, wohnflaeche=120)
        print(f"{kat:14} {we:>3}  {str(einzel):6}  {text[:50]}")
