# OmniRoute – Sicherheits- und Nutzenentscheidung

Stand: 2026-09-11

## Urteil

OmniRoute wird **nicht als aktiver Provider installiert und nicht vor Codex oder Claude
geschaltet**. Das bestehende Free-AI-Gateway bleibt die verbindliche Schicht. Die direkt
nutzbare Token-Sparidee wurde durch profilbezogene, nicht überschreibbare Ausgabegrenzen
umgesetzt.

## Belegte Gründe

- MIT-Lizenz bedeutet kostenlose Software, aber kein garantiert kostenloses
  Modellkontingent. Free-Tiers und deren Bedingungen stammen von den jeweiligen Providern.
- Die Paketmetadaten von `omniroute` 3.8.50 nennen rund 452 MB entpackte Größe.
- OmniRoute speichert OAuth-/API-Zugangsdaten; die eigene Sicherheitsdokumentation nennt
  einen Klartext-Passthrough, solange kein `STORAGE_ENCRYPTION_KEY` gesetzt ist.
- Die Distribution umfasst privilegierte MITM-, TLS-/CLI-Fingerprint-, Tunnel-, Proxy-,
  Memory- und Managementfunktionen, die Lionel OS für reines Routing nicht benötigt.
- Die vom Projekt genannte Gratis-Tokenmenge ist ausdrücklich eine Schätzung und wurde
  bereits wegen Doppelzählungen und beendeter Angebote nach unten korrigiert.

## Voraussetzung für eine spätere optionale Anbindung

1. Minimal-Build ohne MITM, Tunnel, Cloud-Sync, Memory und Provider-Imitation.
2. Ausschließlich `127.0.0.1`, keine Remote- oder Dashboard-Freigabe.
3. Verschlüsselung der Credentials zwingend; keine Schlüsselübernahme aus Projektdateien.
4. Explizite Allowlist einzelner offiziell bestätigter Gratisprovider; kein `auto/cheap`,
   das kostenpflichtige Ziele wählen könnte.
5. Kostenlimit null, kein stiller Providerwechsel, lokale Metadaten-Evidenz und
   End-to-end-Tests vor Aktivierung.

## Quellen

- Projekt-Repository und Security Policy:
  `https://github.com/CullinanCloud/omniroute`
- Free-Tier-Methodik:
  `https://github.com/CullinanCloud/omniroute/blob/release/v3.8.49/docs/reference/FREE_TIERS.md`
- Claude-Code-Plugin-Marktplätze:
  `https://code.claude.com/docs/en/discover-plugins`
- Lokale npm-Metadatenabfrage für `omniroute` 3.8.50.
