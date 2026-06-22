# -*- coding: utf-8 -*-
"""Legt die 7 neuen Higgsfield-Karussells (item_08..item_14) als Bauplaene an.
Texte + Platzhalter-IDs; Bilder kommen via Higgsfield-MCP nach raw/."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.theme_generator import _normalize

HASH_BASIS = ("#FrüherVsHeute #Lebensweisheiten #Nachdenklich #BewusstLeben "
              "#Gedankenwelt #Menschlichkeit #Achtsamkeit #Erinnerungen "
              "#Werte #EchteVerbindung")

CAR = {
    "item_08": {
        "thema": "Spontane Verabredungen",
        "hook": ["Weißt du noch?", "Als man einfach klingelte", "und der andere da war?",
                 "", "Als ein Plan ein Plan blieb", "und niemand absagte?"],
        "paare": [
            ("Früher: Spontan an der Tür geklingelt", "Heute: Drei Tage vorher per Chat angefragt"),
            ("Früher: Ein Versprechen galt", "Heute: Kurz vorher kommt die Absage"),
            ("Früher: Am Treffpunkt gewartet, bis er kam", "Heute: \"Bin gleich da\" – und dann doch nicht"),
            ("Früher: Der ganze Nachmittag war offen", "Heute: Jedes Treffen ist durchgetaktet"),
            ("Früher: Von Angesicht zu Angesicht verabredet", "Heute: Alles läuft über Nachrichten"),
        ],
        "cta": ["Wann hast du zuletzt", "einfach spontan geklingelt?"],
        "caption": ("Weißt du noch? Früher klingelte man einfach - und der Nachmittag "
                    "gehörte euch. Ein Versprechen war ein Versprechen, niemand sagte "
                    "kurzfristig ab. Heute wird drei Tage vorher angefragt und eine "
                    "Stunde vorher abgesagt. Dabei ist es das Spontane, das Verbindungen "
                    "echt macht. Wann hast du zuletzt einfach spontan geklingelt? "
                    "Schreib mir EIN Wort in die Kommentare. 👇"),
        "hashtags": "#Verbindlichkeit #Spontanität #EchteFreundschaft #Miteinander #ZeitFüreinander " + HASH_BASIS,
    },
    "item_09": {
        "thema": "Draußen spielen & Vertrauen",
        "hook": ["Weißt du noch?", "Als wir morgens rausgingen", "und erst abends heimkamen?",
                 "", "Als Eltern vertrauten,", "ohne ständig zu fragen?"],
        "paare": [
            ("Früher: Raus, bis die Laternen angingen", "Heute: Alle 20 Minuten eine Kontroll-Nachricht"),
            ("Früher: Dreckig und glücklich heimgekommen", "Heute: Drinnen bleiben, bloß nichts riskieren"),
            ("Früher: Niemand wusste jede Minute, wo du warst", "Heute: Live-Standort auf dem Handy"),
            ("Früher: Man fand selbst nach Hause", "Heute: Für jeden Weg gefahren werden"),
            ("Früher: Abenteuer am Bach, im Wald", "Heute: Abenteuer nur noch auf dem Bildschirm"),
        ],
        "cta": ["Wann hast du dein Kind zuletzt", "einfach losziehen lassen?"],
        "caption": ("Weißt du noch? Früher gingen wir morgens raus und kamen erst abends "
                    "wieder - dreckig, müde, glücklich. Unsere Eltern vertrauten, ohne "
                    "jede Minute zu wissen, wo wir waren. Heute begleitet uns die "
                    "ständige Sorge und der Live-Standort. Ein bisschen mehr Vertrauen "
                    "täte allen gut. Wann hast du dein Kind zuletzt einfach losziehen "
                    "lassen? Schreib mir EIN Wort in die Kommentare. 👇"),
        "hashtags": "#Kindheit #Vertrauen #DraußenSpielen #Freiheit #Elternsein " + HASH_BASIS,
    },
    "item_10": {
        "thema": "Fantasie & Kreativität",
        "hook": ["Weißt du noch?", "Als aus Langeweile", "die besten Ideen wurden?",
                 "", "Als ein Karton", "alles sein konnte?"],
        "paare": [
            ("Früher: Aus einem Karton wurde ein Raumschiff", "Heute: Fertiges Spielzeug, das alles vorgibt"),
            ("Früher: Eigene Spielregeln erfunden", "Heute: Vorgegebene Level abgearbeitet"),
            ("Früher: Stöcke wurden zu Schwertern", "Heute: Alles passiert auf dem Display"),
            ("Früher: Langeweile war der Anfang von Ideen", "Heute: Sofort das Handy gegen die Stille"),
            ("Früher: Draußen gebaut und gegraben", "Heute: Daneben sitzen und zuschauen"),
        ],
        "cta": ["Wann hast du zuletzt", "etwas aus dem Nichts erfunden?"],
        "caption": ("Weißt du noch? Früher wurde aus einem Karton ein Raumschiff und aus "
                    "Langeweile die beste Idee. Wir erfanden eigene Regeln, bauten, gruben, "
                    "träumten. Heute gibt das fertige Spielzeug oder das Display alles vor. "
                    "Dabei steckt in jedem Kind ein Erfinder. Wann hast du zuletzt etwas "
                    "aus dem Nichts erschaffen? Schreib mir EIN Wort in die Kommentare. 👇"),
        "hashtags": "#Fantasie #Kreativität #Kinderspiel #Erfindergeist #Spielfreude " + HASH_BASIS,
    },
    "item_11": {
        "thema": "Musik mit Wert",
        "hook": ["Weißt du noch?", "Als ein Album", "ein Schatz war?",
                 "", "Als man wochenlang", "auf eine Platte wartete?"],
        "paare": [
            ("Früher: Wochenlang auf den Release gewartet", "Heute: Alles sofort da, nichts ersehnt"),
            ("Früher: Das Cover studiert, das Booklet gelesen", "Heute: Nur ein kleines Bild im Stream"),
            ("Früher: Ein Album von vorne bis hinten gehört", "Heute: Nach 20 Sekunden weitergewischt"),
            ("Früher: Songtexte auswendig gelernt", "Heute: Kaum noch den Titel gemerkt"),
            ("Früher: Gemeinsam eine Platte aufgelegt", "Heute: Jeder mit Kopfhörern allein"),
        ],
        "cta": ["Wann hast du ein Album zuletzt", "ganz durchgehört?"],
        "caption": ("Weißt du noch? Früher war ein Album ein Schatz. Man wartete wochenlang "
                    "auf den Release, studierte das Cover, lernte die Texte auswendig. "
                    "Heute ist alles sofort da und nach 20 Sekunden weitergewischt. "
                    "Vielleicht lohnt es sich, mal wieder ein ganzes Album zu hören. "
                    "Wann hast du das zuletzt getan? Schreib mir EIN Wort in die "
                    "Kommentare. 👇"),
        "hashtags": "#Musikliebe #Vinyl #Schallplatte #Vorfreude #MusikMitWert " + HASH_BASIS,
    },
    "item_12": {
        "thema": "Den Moment erleben",
        "hook": ["Weißt du noch?", "Als ein Konzert", "einfach ein Konzert war?",
                 "", "Als man mittendrin war —", "ohne Bildschirm dazwischen?"],
        "paare": [
            ("Früher: Beim Konzert mitgesungen und getanzt", "Heute: Die halbe Show durch die Handykamera"),
            ("Früher: Den Sonnenuntergang einfach angeschaut", "Heute: Erst zehn Fotos, dann vielleicht schauen"),
            ("Früher: Ein Moment blieb in Erinnerung", "Heute: Ein Moment landet in der Cloud"),
            ("Früher: Ganz da, wo man war", "Heute: In Gedanken schon beim Posten"),
            ("Früher: Mit den Augen festgehalten", "Heute: Nur noch durch die Linse gesehen"),
        ],
        "cta": ["Wann hast du zuletzt etwas erlebt,", "ohne es zu filmen?"],
        "caption": ("Weißt du noch? Früher war ein Konzert einfach ein Konzert - man war "
                    "mittendrin, ohne Bildschirm dazwischen. Heute landet der schönste "
                    "Moment erst in der Cloud, bevor wir ihn wirklich erleben. Dabei "
                    "bleibt am meisten, was wir mit den Augen festhalten. Wann hast du "
                    "zuletzt etwas erlebt, ohne es zu filmen? Schreib mir EIN Wort in "
                    "die Kommentare. 👇"),
        "hashtags": "#ImMoment #Präsenz #EchteMomente #Achtsamkeit #HierUndJetzt " + HASH_BASIS,
    },
    "item_13": {
        "thema": "Nachbarschaft",
        "hook": ["Weißt du noch?", "Als man jeden", "im Viertel kannte?",
                 "", "Als ein Nachbar mehr war", "als ein Name am Klingelschild?"],
        "paare": [
            ("Früher: Man kannte jedes Kind in der Straße", "Heute: Man grüßt sich kaum im Treppenhaus"),
            ("Früher: Für eine Tasse Mehl geklingelt", "Heute: Lieber alles online bestellt"),
            ("Früher: Die Straße passte auf die Kinder auf", "Heute: Jeder bleibt für sich"),
            ("Früher: Auf der Bank vorm Haus zusammengesessen", "Heute: Hinter geschlossener Tür allein"),
            ("Früher: Ein neuer Nachbar wurde begrüßt", "Heute: Man weiß nicht, wer nebenan wohnt"),
        ],
        "cta": ["Wann hast du zuletzt", "deinen Nachbarn gegrüßt?"],
        "caption": ("Weißt du noch? Früher kannte man jeden im Viertel - jedes Kind, jeden "
                    "Nachbarn. Man klingelte für eine Tasse Mehl und passte gemeinsam "
                    "aufeinander auf. Heute grüßt man sich kaum noch im Treppenhaus. "
                    "Dabei beginnt Gemeinschaft mit einem einfachen Hallo. Wann hast du "
                    "zuletzt deinen Nachbarn gegrüßt? Schreib mir EIN Wort in die "
                    "Kommentare. 👇"),
        "hashtags": "#Nachbarschaft #Gemeinschaft #Zusammenhalt #Viertel #Miteinander " + HASH_BASIS,
    },
    "item_14": {
        "thema": "Im Café wirklich da sein",
        "hook": ["Weißt du noch?", "Als ein Kaffee zu zweit", "wirklich zu zweit war?",
                 "", "Als das Handy", "in der Tasche blieb?"],
        "paare": [
            ("Früher: Geredet, bis der Kaffee kalt war", "Heute: Beide tippen, statt zu reden"),
            ("Früher: Das Handy blieb in der Tasche", "Heute: Es liegt griffbereit auf dem Tisch"),
            ("Früher: Blickkontakt über den Tisch", "Heute: Blick nach unten aufs Display"),
            ("Früher: Blinkte nichts, war man einfach da", "Heute: Jede Vibration unterbricht das Gespräch"),
            ("Früher: Man ging, weil es schön war", "Heute: Man bleibt, ist aber längst woanders"),
        ],
        "cta": ["Wann hast du dein Handy zuletzt", "einfach weggelegt?"],
        "caption": ("Weißt du noch? Früher war ein Kaffee zu zweit wirklich zu zweit - das "
                    "Handy blieb in der Tasche, der Blick beim anderen. Heute liegt das "
                    "Handy griffbereit und jede Vibration unterbricht das Gespräch. Echte "
                    "Nähe entsteht, wenn wir ganz da sind. Wann hast du dein Handy zuletzt "
                    "einfach weggelegt? Schreib mir EIN Wort in die Kommentare. 👇"),
        "hashtags": "#Präsenz #Aufmerksamkeit #EchteNähe #HandyWeglegen #ZeitZuZweit " + HASH_BASIS,
    },
}


def build():
    for item, c in CAR.items():
        spec = {
            "thema": c["thema"],
            "quelle": "Higgsfield Soul 2.0",
            "hook": {"zeilen": c["hook"], "prompt": "hook"},
            "paare": [
                {"oben_text": o, "oben_prompt": f"p{i}_oben",
                 "unten_text": u, "unten_prompt": f"p{i}_unten"}
                for i, (o, u) in enumerate(c["paare"])
            ],
            "cta": {"zeilen": c["cta"], "prompt": "cta"},
            "caption": c["caption"],
            "hashtags": c["hashtags"],
        }
        _normalize(spec)
        base = Path("output/queue") / item
        (base / "raw").mkdir(parents=True, exist_ok=True)
        for f in (base / "raw").glob("*.png"):
            f.unlink()
        json.dump(spec, open(base / "spec.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"{item}: Bauplan '{c['thema']}' angelegt")


if __name__ == "__main__":
    build()
