# NVLD-Tipps — Übernahme-Report

Stand: 2026-06-19. Vollständiger Durchgang aller Claude-relevanten Seiten (Index: [nvld-tipps-index.md](nvld-tipps-index.md)).

## ✅ Bereits umgesetzt (autonom gebaut)

| Was | Wo | Aus Tipp |
|-----|-----|----------|
| 3 wiederverwendbare Skills (Instagram, Lern-Auswertung, Trading) | `.claude/skills/{kiai-content,lern-auswertung,trading-bericht}/` | 117 |
| Knappe Antworten als Standard | Memory `feedback_antwortlaenge` | 192 |
| Portables Kontext-File | [KONTEXT.md](KONTEXT.md) | 189/105/186 |
| 12 Lern-Prompts (kopierfertig) | `.claude/skills/lern-auswertung/references/lern-prompts.md` | 104+188 |
| Ressourcen-Liste | [claude-ressourcen.md](claude-ressourcen.md) | 179 |
| Leitsatz „Tipps proaktiv übernehmen" | Memory `feedback_tipps_uebernehmen` | — |

## 🔧 Nur DU kannst das tun (App/Konto/Abo — einmalig)

1. **Memory-Schalter in der Claude-App** (empfohlen, 1 Min): Einstellungen → Fähigkeiten → „Chats durchsuchen und referenzieren" + „Gedächtnis aus Chatverlauf generieren" aktivieren. *(Tipps 105/186/189)*
2. **Kontext-File hinterlegen**: Inhalt von KONTEXT.md in ein Claude.ai-**Project** einfügen → dort dauerhaft dabei. *(189)*
3. **GitHub-Konnektor** in der Desktop-App (Settings → Connectors), falls du Repos per App bearbeiten willst. Hier in Claude Code habe ich Repo-Zugriff ohnehin. *(136)*
4. **Skills aus den Haus-Skills**: Bodys der 3 SKILL.md (ohne Kopf-Block) als Projekt-Anweisung in die jeweiligen Claude.ai-Projects kopieren — dann greifen die Regeln auch in der App. *(117)*

## 🟡 Optional (nur wenn du das Tool nutzt)

- **Higgsfield MCP** (Bild/Video direkt im Chat) — Setup: higgsfield.ai/mcp → in Claude als „Benutzerdefinierter Konnektor" → verbinden. ⚠️ Braucht **Higgsfield Pro** (du hast Basic → ggf. nicht nutzbar). *(134)*
- **Canva-, Adobe/Blender/Fusion-, OnePage-Konnektoren** — nur bei aktiver Nutzung dieser Tools. *(167, 130, 191)*
- **Cowork-Agenten / Prompt-Sets** (Reiseplaner 168, Bewerbung 169, Wochenplanung 193) — bei Bedarf sag Bescheid, dann ziehe ich die Master-Prompts als kopierfertige Dateien.

## ⏭️ Bewusst übersprungen

- **131** (5 „geheime Codes") & **166** (Supergenius Pack) — Gimmick/Marketing, keine echten Funktionen.
- **122** (Opus 4.7) — Modell-Info veraltet (aktuell Opus 4.8).
- Reine Nicht-Claude-Seiten (Tools/ChatGPT/Video) — laut Filter von Anfang an raus.
