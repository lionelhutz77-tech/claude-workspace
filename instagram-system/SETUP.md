# Instagram-Zugriff einrichten

Ziel: Ein langlebiger Access Token in `.env`, mit dem die Skripte posten können —
ohne Browser, ohne eingeloggt zu sein.

## Schritt 1: Instagram-Account auf Professional umstellen (einmalig, in der App)

1. Instagram-App → Profil → Menü (≡) → **Einstellungen und Aktivität**
2. → **Kontoart und Tools** → **Zu professionellem Konto wechseln**
3. Typ **Creator** wählen (reicht völlig, Business geht auch)

Ohne diesen Schritt verweigert die API jeden Zugriff.

## Schritt 2: Token im Meta-Dashboard generieren (einmalig, im Browser)

1. https://developers.facebook.com → einloggen → **Meine Apps** → deine App öffnen
   (App-ID 1550250336791489 existiert bereits)
2. Linke Seitenleiste: **Instagram** → **API-Setup mit Instagram-Login**
   (englisch: "API setup with Instagram business login")
3. Abschnitt **"Access Token generieren"** / "Generate access tokens":
   → **Konto hinzufügen** → mit dem Instagram-Account einloggen
   → alle angefragten Berechtigungen bestätigen (mindestens
   `instagram_business_basic` und `instagram_business_content_publish`)
4. → **Token generieren** → Token kopieren (langer String, beginnt mit `IG...`)

Der Token ist langlebig (60 Tage) und wird später automatisch verlängert.

## Schritt 3: Token eintragen und prüfen

```
python check_access.py <HIER_DEN_TOKEN_EINFUEGEN>
```

Das Skript prüft Identität + Publish-Berechtigung und speichert alles in `.env`.
Wenn am Ende `ZUGRIFF VOLLSTAENDIG EINGERICHTET` steht, ist der Zugriff fertig.

## Danach (läuft automatisch, kein Zutun nötig)

Die Windows-Aufgabe **„Instagram Token Guard"** läuft täglich um 10:00
(bzw. beim nächsten Einschalten, falls der PC aus war) und führt
`token_guard.py` aus:

- Restlaufzeit > 30 Tage: nichts zu tun, nur Log-Eintrag
- Restlaufzeit ≤ 30 Tage: Token wird automatisch um 60 Tage verlängert
  (kurzes Info-Popup zur Bestätigung)
- Restlaufzeit ≤ 5 Tage und Verlängerung schlägt fehl: täglich ein
  Warn-Popup → dann neuen Token im Meta-Dashboard generieren (Schritt 2)
  und `python check_access.py <TOKEN>` ausführen

Log: `output/token_guard.log` · Manuelle Checks jederzeit:
`python check_access.py` (Gesundheitscheck) · `python token_guard.py` (Wächter-Testlauf)

## Video-Hosting (eingerichtet & verifiziert am 11.06.2026)

Die Instagram-API lädt Videos nicht vom PC hoch, sondern holt sie von einer
öffentlichen URL ab. Dafür dient das öffentliche GitHub-Repo
**lionelhutz77-tech/ig-media** als kostenloser Zwischenspeicher:

- `tools/video_host.py` — lädt Videos hoch (`upload_video`), liefert die
  öffentliche URL und räumt nach dem Posten auf (`delete_video`)
- Der Publisher macht das automatisch: Posts mit `video_file` (lokaler Pfad)
  in der Queue werden hochgeladen → gepostet → vom Host gelöscht
- Verifiziert per `tools/check_video_url.py` (erstellt einen Test-Container,
  ohne zu posten): Instagram akzeptiert die raw.githubusercontent.com-URLs

## Fallback

Falls der Dashboard-Weg nicht klappt: `python get_token.py` startet einen
eigenen OAuth-Flow. Dafür muss in der Meta-App unter den
Business-Login-Einstellungen die Redirect-URI `http://localhost:8888/callback`
eingetragen sein (Meta verlangt hier teils HTTPS — deshalb ist das nur Plan B).

## Sicherheit

- Alle Keys/Token liegen in `.env` — die ist per `.gitignore` vom Commit
  ausgeschlossen. Nichts davon committen oder pushen.
- Vor einem späteren Push zu GitHub (für Actions): Keys in GitHub Secrets
  hinterlegen, niemals im Code.
