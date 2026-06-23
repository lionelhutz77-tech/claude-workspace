# Quellen-Status (Stand 23.06.2026)

Übersicht aller geprüften Datenquellen — was funktioniert und was nicht.

## ✅ Funktioniert (in Pipeline aktiv)

| Quelle | Typ | Ertrag/Lauf | Region | Notiz |
|--------|-----|-------------|--------|-------|
| **Immowelt/Immonet** | Playwright | ~16–18 MFH | Oberhausen | Hauptquelle. Aggregiert die meisten Makler-Objekte. PLZ inkl. 46149, Energieklasse direkt aus Trefferkarte. |
| **KL Immobilien** | HTML (WooCommerce) | ~10 | Oberhausen/Essen | Detail-Seiten `/produkt/`. |
| **van Oepen** | HTML (inx-Plugin) | ~5 MFH | Bottrop/Marl | Zwei-/Dreifamilienhäuser. |
| **Blömker** | HTML | ~1 MFH | Bottrop/Gladbeck | Überwiegend Einfamilienhäuser → wenig MFH. |

Makler sind ein **stehendes Netz**: Auch wenig-Ertrag-Quellen bleiben drin, weil
jederzeit ein passendes Objekt auftauchen kann.

## ❌ Nicht praktikabel (deaktiviert, mit Grund)

| Quelle | Grund |
|--------|-------|
| **ImmoScout24** | Datadome-Bot-Schutz blockt auch headless Playwright + Stealth (Captcha „Ich bin kein Roboter"). |
| **VON POLL** | 403 Forbidden bei Requests. Bräuchte Playwright — später evtl. machbar. |
| **Marquardt** | Alter php4/FlowFact-Katalog, liefert keine Daten via GET (Session/POST nötig). In-region — Reaktivierung mit Mehraufwand denkbar. |
| **Bönighausen** | Berlin-fokussiert (kaum Ruhrgebiet), dünne strukturierte Daten. |
| **ARR / atelier rheinruhr** | .htm-CMS ohne Listing-Struktur, keine parsebaren Objekte. |
| **Sariguel / CT-Immobilien** | JS-gerendert, keine statischen Daten im HTML. |
| **Piezonka** | Leere Jimdo-Seite, keine Angebote. |
| **immobilien-oberhausen.com** | Domain tot (DNS löst nicht auf). |
| **Kleinanzeigen.de** | Immobilien-Kauf für Oberhausen geflutet mit bundesweiten Bauträger-Promo-Ads (Town&Country) + Service-Fakes. 0 echte Kauf-Objekte über 10 Seiten. |

## Mögliche nächste Schritte (optional)

- **VON POLL via Playwright** (wie Immowelt) — mittlerer Aufwand, etwas Mehrabdeckung.
- **Immowelt-Paginierung** — aktuell nur Seite 1 (~42 Karten). Mehr Seiten = mehr Objekte,
  aber Immowelt paginiert per JS (kein URL-Param), bräuchte Klick-Automatisierung.
- **Marquardt-Katalog** reverse-engineeren (php4 Session/POST).
