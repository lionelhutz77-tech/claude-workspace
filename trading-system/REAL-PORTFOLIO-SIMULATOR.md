# Privater Depot-Simulator

Separater, lokaler Was-wäre-wenn-Rechner für einen Screenshot-Schnappschuss des
echten Depots. Er ruft weder einen Broker noch einen KI-Dienst noch einen
Marktdatenanbieter auf. Er verändert weder das echte Depot noch die virtuellen
10.000-€-Strategiedepots. Die sensiblen Positionen liegen ausschließlich unter
`private/` und in der generierten, gitignorierten Datei unter `output/`.

Öffnen: `output/real_portfolio_simulator.html` im eigenen Browser.
Neu erzeugen: `python build_real_portfolio_simulator.py` (mit einer funktionierenden
Python-Installation). Für eine spätere Momentaufnahme kann eine andere lokale
JSON-Datei per `--source` übergeben werden.

In der Oberfläche Verkaufsbeträge und neue Kaufideen in EUR eingeben. Es wird
Cash inklusive angenommener Gebühren bilanziert; Überverkäufe und Käufe ohne
Deckung werden blockiert. Die vier Stressannahmen sind keine Prognosen. Für
reale Stückzahlen, Steuern, Einstandskurse, Währungsumrechnung und handelbare
Preise fehlen Daten. Copy-Trader bleiben Blackboxes. Darum ist das Werkzeug
eine Szenarioanalyse und keine individuelle Anlageempfehlung.

Der erste Screenshot-Satz vom 21.09.2026 enthält 42 sichtbare Positionen.
Ihre Werte und das sichtbare Cash ergeben 6,43 € weniger als die angezeigte
Kopfzeile; wahrscheinlich sind die zeitversetzten Screenshots der Grund,
aber die Ursache ist nicht belegt. Die Differenz wird im Dashboard offengelegt.

Die lokale Einzelprüfung in der Oberfläche liest nur die vorhandene
`market_memory.db`. Für die meisten Depotwerte fehlen darin aktuelle Kurse.
Der vorbereitete externe Marktcheck `portfolio_market_review.py` ist deshalb
standardmäßig gesperrt: Er würde die gehaltenen Ticker an Yahoo Finance
übertragen und darf erst nach ausdrücklicher Nutzerfreigabe mit
`--allow-symbol-upload` gestartet werden. Depotwerte oder Copy-Trader-Namen
werden dabei nicht übertragen. Bis dahin wird kein externer Check als
„durchgeführt“ dargestellt.

Tests: `node tests/test_real_portfolio_simulator.js` und nach dem Build
`node tests/test_real_portfolio_output.js`.
