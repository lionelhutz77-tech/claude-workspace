# -*- coding: utf-8 -*-
"""
Baut ein Instagram-Karussell im "Zeitreise"-Format (1845 vs. heute).

Layout pro Kontrast-Slide (1080x1350, Portrait):
  - obere Haelfte: Gemaelde-Stil (1845) + Textbox
  - untere Haelfte: modernes Foto + Textbox
Hook-Slide und CTA-Slide sind vollflaechig.

Ausführen: python -m tools.carousel_builder  (aus instagram-system/)
"""

import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.recipe_images import generate_image_flux

W, H = 1080, 1350
SERIF = "C:/Windows/Fonts/georgia.ttf"
SERIF_BOLD = "C:/Windows/Fonts/georgiab.ttf"

STYLE_1845 = ("oil painting in the style of 1845 German Biedermeier era, warm "
              "muted earth tones, soft candlelight, detailed brushwork, "
              "nostalgic atmosphere")
STYLE_HEUTE = ("modern realistic photography, cool blue-grey tones, harsh "
               "smartphone screen light, shallow depth of field, "
               "contemporary urban setting")

# Fuer persoenliche Kindheits-/Nostalgie-Themen (70er-90er) statt 1845:
STYLE_FRUEHER = ("warm nostalgic analog film photograph, golden hour sunlight, "
                 "1980s vibe, soft grain, joyful natural moment, faded warm "
                 "colors, cinematic")
STYLE_HEUTE_NEU = ("modern realistic photography, slightly cool tones, "
                   "everyday contemporary setting, natural light, candid")

STIL_PAARE = {
    "historisch": (STYLE_1845, STYLE_HEUTE),
    "nostalgie": (STYLE_FRUEHER, STYLE_HEUTE_NEU),
}

# Anatomie-Vorgabe gegen typische FLUX-Fehler (sechs Finger, verdrehte Glieder)
ANATOMY = ("anatomically correct, natural realistic hands with exactly five "
           "fingers, correct facial features, natural relaxed pose, "
           "well-proportioned body")

# (id, prompt, stil)
IMAGES = [
    ("hook", "An elderly couple from 1845 in traditional clothing looking "
     "directly at the viewer with knowing wise eyes, sitting in a warm "
     "candlelit parlor, slightly amused expression, " + STYLE_1845),
    ("brief_1845", "Hands of a young woman carefully reading a handwritten "
     "letter by candlelight, treasuring it, worn paper, " + STYLE_1845),
    ("brief_heute", "Person in bed at night scrolling endless message "
     "notifications on smartphone, blue screen light on tired face, " + STYLE_HEUTE),
    ("essen_1845", "Large family gathered around wooden dinner table, "
     "laughing, telling stories, warm hearth fire, " + STYLE_1845),
    ("essen_heute", "Family of four at modern dinner table, every person "
     "staring at their own smartphone, food untouched, silence, " + STYLE_HEUTE),
    ("warten_1845", "Young man lying in a summer meadow watching clouds, "
     "daydreaming, straw hat over forehead, " + STYLE_1845),
    ("warten_heute", "Person at bus stop compulsively checking phone, "
     "headphones in, not noticing golden sunset behind them, " + STYLE_HEUTE),
    ("abend_1845", "People sitting around evening fire, one telling a story, "
     "faces lit warmly, children listening with wide eyes, " + STYLE_1845),
    ("abend_heute", "Person alone on couch at night, face lit only by "
     "television and phone screen simultaneously, empty room, " + STYLE_HEUTE),
    ("sonnenuntergang_1845", "Couple standing on a hill quietly watching a "
     "dramatic sunset together, holding hands, seen from behind, " + STYLE_1845),
    ("sonnenuntergang_heute", "Row of people at scenic viewpoint all filming "
     "the sunset through their phones, nobody looking directly, " + STYLE_HEUTE),
    ("cta", "The same elderly couple from 1845 smiling warmly and waving "
     "goodbye at the viewer, candlelit parlor, inviting expression, " + STYLE_1845),
]

# Slides: (typ, daten)
SLIDES = [
    ("hook", {
        "bild": "hook",
        "zeilen": ["Deine Urgroßeltern", "besaßen fast nichts.", "",
                   "Außer das, wonach du dich", "heute am meisten sehnst."],
        "fusszeile": "Wische weiter  >>",
    }),
    ("paar", {"oben": ("brief_1845", "Früher: Ein Brief brauchte Wochen — und wurde dreißig Mal gelesen."),
              "unten": ("brief_heute", "Heute: Hundert Nachrichten am Tag. Wirklich gelesen? Kaum eine.")}),
    ("paar", {"oben": ("essen_1845", "Früher: Am Tisch wurden Geschichten erzählt."),
              "unten": ("essen_heute", "Heute: Am Tisch ist es still. Alle sind woanders.")}),
    ("paar", {"oben": ("warten_1845", "Früher: Langeweile war der Ort, an dem Träume entstanden."),
              "unten": ("warten_heute", "Heute: Jede freie Sekunde wird gefüllt. Wann hast du zuletzt geträumt?")}),
    ("paar", {"oben": ("abend_1845", "Früher: Abends saß man zusammen und hörte einander zu."),
              "unten": ("abend_heute", "Heute: Zwei Bildschirme gleichzeitig — und trotzdem allein.")}),
    ("paar", {"oben": ("sonnenuntergang_1845", "Früher: Man sah den Sonnenuntergang an."),
              "unten": ("sonnenuntergang_heute", "Heute: Man filmt ihn. Für Menschen, die ihn auch nicht ansehen.")}),
    ("hook", {
        "bild": "cta",
        "zeilen": ["Welchen dieser Momente", "vermisst du am meisten?", "",
                   "Schreib es in die Kommentare.", "",
                   "Folge @kiai1977", "für mehr Zeitreisen."],
        "fusszeile": None,
    }),
]


def font(size, bold=False):
    return ImageFont.truetype(SERIF_BOLD if bold else SERIF, size)


def fit_cover(img, w, h):
    """Bild proportional fuellen und mittig zuschneiden."""
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def textbox(draw, text, cx, y, max_w, fnt, pad=24):
    """Halbtransparente Textbox mit weissem Serifentext + Schatten, zentriert.
    Box ist bewusst durchscheinend, damit das Bild sichtbar bleibt."""
    lines = []
    for raw in text.split("\n"):
        avg = fnt.getbbox("Mm")[2] / 2
        lines += textwrap.wrap(raw, width=max(8, int(max_w / avg * 1.85))) or [""]
    line_h = fnt.getbbox("Ag")[3] + 12
    box_h = len(lines) * line_h + pad * 2
    widths = [draw.textbbox((0, 0), l, font=fnt)[2] for l in lines]
    box_w = min(max_w, max(widths) + pad * 2)
    x0 = cx - box_w / 2
    # Dunkle, halbtransparente Box (Bild scheint durch) statt deckendem Beige
    draw.rounded_rectangle([x0, y, x0 + box_w, y + box_h], radius=18,
                           fill=(0, 0, 0, 110))
    ty = y + pad
    for l, lw in zip(lines, widths):
        tx = cx - lw / 2
        # weicher Schatten fuer Lesbarkeit auf hellen Bildstellen
        for dx, dy in ((2, 2), (-2, 2), (2, -2), (-2, -2)):
            draw.text((tx + dx, ty + dy), l, font=fnt, fill=(0, 0, 0, 180))
        draw.text((tx, ty), l, font=fnt, fill=(248, 244, 236))
        ty += line_h
    return box_h


def _box_height(text, fnt, max_w, pad=24):
    """Misst die Hoehe, die textbox() fuer diesen Text belegen wird (gleiche Logik)."""
    lines = []
    for raw in text.split("\n"):
        avg = fnt.getbbox("Mm")[2] / 2
        lines += textwrap.wrap(raw, width=max(8, int(max_w / avg * 1.85))) or [""]
    line_h = fnt.getbbox("Ag")[3] + 12
    return len(lines) * line_h + pad * 2


def slide_paar(daten, raw_dir, out):
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    half = H // 2
    f = font(40)
    max_w = W - 120
    halves = []
    for idx, key in enumerate(["oben", "unten"]):
        img_id, text = daten[key]
        h_img = fit_cover(Image.open(raw_dir / f"{img_id}.png"), W, half)
        canvas.paste(h_img, (0, idx * half))
        halves.append((idx, text, h_img))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for idx, text, h_img in halves:
        faces = detect_faces(h_img)  # Koordinaten innerhalb der Halbhoehe
        box_h = _box_height(text, f, max_w)
        top_y, bot_y = 40, half - box_h - 40
        # Textbox an die Haelfte (oben/unten) legen, die KEIN Gesicht trifft

        def overlap(y0):
            return sum(1 for (fx, fy, fw, fh) in faces
                       if not (y0 + box_h < fy - 15 or y0 > fy + fh + 15))
        local_y = top_y if overlap(top_y) <= overlap(bot_y) else bot_y
        textbox(d, text, W / 2, idx * half + local_y, max_w, f)

    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    canvas.save(out, quality=93)


def detect_faces(pil_img):
    """Gibt Liste von (x, y, w, h) der erkannten Gesichter zurueck (auf W x H)."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return []
    gray = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
    found = []
    for name in ("haarcascade_frontalface_default.xml",
                 "haarcascade_profileface.xml"):
        c = cv2.CascadeClassifier(cv2.data.haarcascades + name)
        for f in c.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                    minSize=(60, 60)):
            found.append(tuple(int(v) for v in f))
    # auch gespiegelt (Profilgesichter zeigen oft nur in eine Richtung)
    flip = cv2.flip(gray, 1)
    cp = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    w_img = gray.shape[1]
    for (fx, fy, fw, fh) in cp.detectMultiScale(flip, 1.1, 5, minSize=(60, 60)):
        found.append((int(w_img - fx - fw), int(fy), int(fw), int(fh)))
    return found


def free_bands(faces, pad=30, top=20, bottom=None):
    """Liefert die gesichtsfreien vertikalen Baender als (y0, y1)-Liste
    innerhalb [top, bottom], mit Sicherheitsabstand um jedes Gesicht."""
    if bottom is None:
        bottom = H - 20
    blocked = sorted((max(0, fy - pad), min(H, fy + fh + pad))
                     for (fx, fy, fw, fh) in faces)
    bands, cursor = [], top
    for b0, b1 in blocked:
        if min(b0, bottom) - cursor > 0:
            bands.append((cursor, min(b0, bottom)))
        cursor = max(cursor, b1)
        if cursor >= bottom:
            break
    if bottom - cursor > 0:
        bands.append((cursor, bottom))
    return bands or [(top, bottom)]


def place_in_largest_band(faces, want_h, top=20, bottom=None):
    """Zentriert einen Block der Hoehe want_h im groessten gesichtsfreien Band
    und klemmt ihn sicher in [top, bottom]. Gibt (y_start, band) zurueck."""
    if bottom is None:
        bottom = H - 20
    bands = free_bands(faces, top=top, bottom=bottom)
    best = max(bands, key=lambda b: b[1] - b[0])
    y0, y1 = best
    y_start = y0 + max(0, ((y1 - y0) - want_h) / 2)
    y_start = min(max(y_start, top), max(top, bottom - want_h))
    return y_start, best


def place_block(faces, want_h, top=20, bottom=None, prefer_bottom=False):
    """Bestimmt y_start fuer einen Textblock der Hoehe want_h.
    prefer_bottom=True: legt den Block in das UNTERSTE gesichtsfreie Band, das
    passt (wie im viralen Listen-Format) — so bleibt das Gesicht (meist oben) frei.
    Sonst: groesstes Band, zentriert (bisheriges Verhalten)."""
    if bottom is None:
        bottom = H - 20
    bands = free_bands(faces, top=top, bottom=bottom)
    if prefer_bottom:
        fitting = [b for b in bands if (b[1] - b[0]) >= want_h]
        if fitting:
            b = max(fitting, key=lambda bb: bb[1])  # tiefstes passendes Band
            y_start = b[1] - want_h - 14
            return min(max(y_start, top), max(top, bottom - want_h))
    best = max(bands, key=lambda b: b[1] - b[0])
    y0, y1 = best
    y_start = y0 + max(0, ((y1 - y0) - want_h) / 2)
    return min(max(y_start, top), max(top, bottom - want_h))


def _wrap_lines(draw, zeilen, fnt, max_w):
    """Bricht zu lange Zeilen automatisch um, damit nichts ueber den Rand laeuft.
    Leere Zeilen bleiben als Abstand erhalten."""
    out = []
    for z in zeilen:
        if not z:
            out.append("")
            continue
        if draw.textbbox((0, 0), z, font=fnt)[2] <= max_w:
            out.append(z)
            continue
        words = z.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textbbox((0, 0), test, font=fnt)[2] <= max_w:
                cur = test
            else:
                if cur:
                    out.append(cur)
                cur = w
        if cur:
            out.append(cur)
    return out


def slide_voll(daten, raw_dir, out, prefer_bottom=False):
    img = fit_cover(Image.open(raw_dir / f"{daten['bild']}.png"), W, H)
    faces = detect_faces(img)
    d0 = ImageDraw.Draw(img)

    zeilen_in = daten["zeilen"]
    max_w = W - 130
    has_footer = bool(daten.get("fusszeile"))
    bottom_limit = H - 175 if has_footer else H - 35  # Fusszeile/Rand freihalten
    # Groesstes gesichtsfreies Band bestimmen; Schrift so verkleinern, bis der
    # umbrochene Textblock GARANTIERT in dieses Band passt (Gesicht bleibt frei).
    bands = free_bands(faces, top=20, bottom=bottom_limit)
    band_h = max(b[1] - b[0] for b in bands)
    f, zeilen, line_h, block_h = None, None, None, None
    for size in range(58, 27, -3):
        f = font(size, bold=True)
        zeilen = _wrap_lines(d0, zeilen_in, f, max_w)
        line_h = f.getbbox("Ag")[3] + 16
        block_h = len(zeilen) * line_h
        if block_h + 60 <= band_h:   # +60 Puffer fuer die Lesebox
            break
    y_start = place_block(faces, block_h, top=20, bottom=bottom_limit,
                          prefer_bottom=prefer_bottom)

    # Weiche dunkle Lesehilfe nur hinter dem Textblock (statt ganzem Bild)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    pad_y = 36
    od.rounded_rectangle([40, y_start - pad_y, W - 40, y_start + block_h + pad_y],
                         radius=28, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    d = ImageDraw.Draw(img)
    y = y_start
    for z in zeilen:
        if z:
            wpx = d.textbbox((0, 0), z, font=f)[2]
            x = (W - wpx) / 2
            for dx in (-3, 0, 3):
                for dy in (-3, 0, 3):
                    d.text((x + dx, y + dy), z, font=f, fill=(0, 0, 0))
            d.text((x, y), z, font=f, fill=(245, 238, 220))
        y += line_h
    fz = daten.get("fusszeile")
    if fz:
        f2 = font(40)
        wpx = d.textbbox((0, 0), fz, font=f2)[2]
        # Fusszeile ans untere Bild, mit eigenem Schatten
        fy = H - 120
        for dx, dy in ((2, 2), (-2, 2), (2, -2), (-2, -2)):
            d.text(((W - wpx) / 2 + dx, fy + dy), fz, font=f2, fill=(0, 0, 0))
        d.text(((W - wpx) / 2, fy), fz, font=f2, fill=(245, 238, 220))
    img.save(out, quality=93)


def slide_liste(daten, raw_dir, out, prefer_bottom=True):
    """Listen-Slide (viraler Stil): vollflaechiges Bild + optional Nummern-Badge
    + weisse Box mit schwarzem, fettem Spruch. Text wird ins groesste
    gesichtsfreie Band gelegt und so verkleinert, dass nichts ueberlaeuft."""
    img = fit_cover(Image.open(raw_dir / f"{daten['bild']}.png"), W, H)
    faces = detect_faces(img)
    draw = ImageDraw.Draw(img)
    nummer = str(daten.get("nummer") or "")
    text = daten["text"]
    max_w = W - 160
    bottom_limit = H - 40
    badge = 96 if nummer else 0

    bands = free_bands(faces, top=20, bottom=bottom_limit)
    band_h = max(b[1] - b[0] for b in bands)
    f, zeilen, line_h, block_h = None, None, None, None
    for size in range(60, 29, -3):
        f = font(size, bold=True)
        zeilen = _wrap_lines(draw, [text] if isinstance(text, str) else text, f, max_w)
        line_h = f.getbbox("Ag")[3] + 14
        block_h = len(zeilen) * line_h
        if block_h + badge + 70 <= band_h:
            break

    total_h = block_h + (badge + 20 if nummer else 0)
    y_start = place_block(faces, total_h, top=20, bottom=bottom_limit,
                          prefer_bottom=prefer_bottom)
    y = y_start

    if nummer:
        bx0 = (W - badge) / 2
        draw.rounded_rectangle([bx0, y, bx0 + badge, y + badge], radius=16,
                               fill=(250, 248, 244))
        nf = font(int(badge * 0.58), bold=True)
        nb = draw.textbbox((0, 0), nummer, font=nf)
        draw.text(((W - (nb[2] - nb[0])) / 2 - nb[0],
                   y + (badge - (nb[3] - nb[1])) / 2 - nb[1]),
                  nummer, font=nf, fill=(20, 20, 20))
        y += badge + 20

    box_pad = 24
    widths = [draw.textbbox((0, 0), z, font=f)[2] for z in zeilen if z]
    box_w = min(W - 60, max(widths) + box_pad * 2)
    box_x0 = (W - box_w) / 2
    draw.rounded_rectangle([box_x0, y - box_pad, box_x0 + box_w, y + block_h + box_pad],
                           radius=22, fill=(250, 248, 244))
    for z in zeilen:
        if z:
            wpx = draw.textbbox((0, 0), z, font=f)[2]
            draw.text(((W - wpx) / 2, y), z, font=f, fill=(20, 20, 20))
        y += line_h
    img.save(out, quality=93)


def build_list_from_spec(spec, base_dir):
    """Baut ein Listen-Karussell (viraler "X Wege..."-Stil):
      Hook-Slide + N nummerierte Einzelbild-Slides + CTA-Slide.

    spec = {
      "hook":  {"zeilen": [...], "prompt": "szene fuer hook"},
      "items": [{"text": "Spruch", "prompt": "szene"}, ...],
      "cta":   {"zeilen": [...], "prompt": "szene fuer cta"}
    }
    Bilder werden via _gen_image erzeugt ODER (Higgsfield-Workflow) aus
    vorhandenen raw/<id>.png uebernommen. IDs: hook, i0..iN, cta.
    """
    base = Path(base_dir)
    raw = base / "raw"
    slides_dir = base / "slides"
    raw.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(exist_ok=True)

    jobs = [("hook", spec["hook"].get("prompt", "hook"))]
    for i, it in enumerate(spec["items"]):
        jobs.append((f"i{i}", it.get("prompt", f"i{i}")))
    jobs.append(("cta", spec["cta"].get("prompt", "cta")))

    print(f"  Generiere {len(jobs)} Bilder...")
    for img_id, prompt in jobs:
        if not _gen_image(prompt, raw / f"{img_id}.png"):
            raise RuntimeError(f"Bildgenerierung fehlgeschlagen: {img_id}")

    slides = []
    s1 = slides_dir / "slide_01.jpg"
    slide_voll({"bild": "hook", "zeilen": spec["hook"]["zeilen"],
                "fusszeile": "Wische weiter  >>"}, raw, s1, prefer_bottom=True)
    slides.append(s1)

    # Instagram-Karussell erlaubt MAX 10 Slides. Hook zaehlt mit -> max 9 Items;
    # die CTA wandert dann in die Caption (statt eigener Slide).
    items = spec["items"][:9]
    for i, it in enumerate(items):
        out = slides_dir / f"slide_{i+2:02d}.jpg"
        slide_liste({"bild": f"i{i}", "nummer": i + 1, "text": it["text"]}, raw, out)
        slides.append(out)

    if 1 + len(items) < 10:  # nur dann passt noch ein CTA-Slide rein
        sN = slides_dir / f"slide_{len(items)+2:02d}.jpg"
        slide_voll({"bild": "cta", "zeilen": spec["cta"]["zeilen"],
                    "fusszeile": None}, raw, sN, prefer_bottom=True)
        slides.append(sN)
    else:
        print("  CTA-Slide weggelassen (IG-Limit 10 Slides) — CTA gehoert in die Caption.")

    print(f"  {len(slides)} Slides gerendert.")
    return slides


def _gen_image(prompt, target):
    if target.exists():
        return True
    # Primaer FLUX (beste Qualitaet); bei erschoepftem Tageslimit Stable Horde
    ok = generate_image_flux(prompt, target)
    if not ok:
        from tools.recipe_images import generate_image_horde
        print("  FLUX nicht verfuegbar -> Stable Horde (Fallback)")
        ok = generate_image_horde(prompt, target)
    if not ok:
        return False
    img = Image.open(target)
    if img.size == (1080, 1920):  # FLUX-Wrapper-Einbettung -> Quadrat zurueck
        img.crop((0, 420, 1080, 1500)).save(target)
    return True


def build_from_spec(spec, base_dir, stil="nostalgie"):
    """Baut ein komplettes Karussell aus einem Themen-Bauplan (spec dict).

    spec = {
      "hook": {"zeilen": [...], "prompt": "szene fuer hook"},
      "paare": [{"oben_text","oben_prompt","unten_text","unten_prompt"}, ... x5],
      "cta":  {"zeilen": [...], "prompt": "szene fuer cta"}
    }
    stil: "nostalgie" (Kindheit 70er-90er) oder "historisch" (1845).
    Gibt die Liste der erzeugten Slide-Pfade zurueck.
    """
    base = Path(base_dir)
    raw = base / "raw"
    slides_dir = base / "slides"
    raw.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(exist_ok=True)

    s_frueher, s_heute = STIL_PAARE.get(stil, STIL_PAARE["nostalgie"])

    # 1. Bilder generieren (mit Anatomie-Vorgabe gegen FLUX-Hand-/Koerperfehler)
    def fr(p):
        return p + ", " + s_frueher + ", " + ANATOMY
    def he(p):
        return p + ", " + s_heute + ", " + ANATOMY

    jobs = [("hook", fr(spec["hook"]["prompt"]))]
    for i, p in enumerate(spec["paare"]):
        jobs.append((f"p{i}_oben", fr(p["oben_prompt"])))
        jobs.append((f"p{i}_unten", he(p["unten_prompt"])))
    jobs.append(("cta", fr(spec["cta"]["prompt"])))

    print(f"  Generiere {len(jobs)} Bilder (FLUX)...")
    for img_id, prompt in jobs:
        if not _gen_image(prompt, raw / f"{img_id}.png"):
            raise RuntimeError(f"Bildgenerierung fehlgeschlagen: {img_id}")

    # 2. Slides rendern
    slides = []
    s1 = slides_dir / "slide_01.jpg"
    slide_voll({"bild": "hook", "zeilen": spec["hook"]["zeilen"],
                "fusszeile": "Wische weiter  >>"}, raw, s1)
    slides.append(s1)

    for i, p in enumerate(spec["paare"]):
        out = slides_dir / f"slide_{i+2:02d}.jpg"
        slide_paar({"oben": (f"p{i}_oben", p["oben_text"]),
                    "unten": (f"p{i}_unten", p["unten_text"])}, raw, out)
        slides.append(out)

    sN = slides_dir / f"slide_{len(spec['paare'])+2:02d}.jpg"
    slide_voll({"bild": "cta", "zeilen": spec["cta"]["zeilen"],
                "fusszeile": None}, raw, sN)
    slides.append(sN)

    print(f"  {len(slides)} Slides gerendert.")
    return slides


def main():
    base = Path("output/media/carousel_001")
    raw = base / "raw"
    slides_dir = base / "slides"
    raw.mkdir(parents=True, exist_ok=True)
    slides_dir.mkdir(exist_ok=True)

    print(f"1/2 Generiere {len(IMAGES)} Bilder (FLUX)...")
    for img_id, prompt in IMAGES:
        if not _gen_image(prompt, raw / f"{img_id}.png"):
            print("  FEHLER - Abbruch."); sys.exit(1)

    print("2/2 Rendere Slides...")
    for i, (typ, daten) in enumerate(SLIDES, 1):
        out = slides_dir / f"slide_{i:02d}.jpg"
        if typ == "paar":
            slide_paar(daten, raw, out)
        else:
            slide_voll(daten, raw, out)
        print(f"  {out.name}")

    print(f"\nFERTIG: {len(SLIDES)} Slides in {slides_dir}")


if __name__ == "__main__":
    main()
