"""Deterministic synthetic document image generator for fleet doc classification.

Produces 224x224 RGB images for 5 document classes using seeded RNG.
All documents are in Hebrew using bundled NotoSansHebrew font with RTL bidi.
"""

import os

import numpy as np
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

from data.dataset import CLASSES

IMG_W, IMG_H = 224, 224

_FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansHebrew[wdth,wght].ttf")


def _heb(text):
    """Convert Hebrew logical string to visual display order for PIL (LTR canvas)."""
    return get_display(text)


def _font(size=10):
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _rng_color(rng_np, light=True):
    if light:
        return tuple(rng_np.randint(200, 256, 3).tolist())
    return tuple(rng_np.randint(30, 200, 3).tolist())


def _row(draw, x, y, label, value, fl, fv, lc=(80, 80, 80), vc=(30, 30, 30)):
    draw.text((x, y), label + ":", font=fl, fill=lc)
    draw.text((x + 100, y), str(value), font=fv, fill=vc)


# ---------------------------------------------------------------------------
# Per-class generators - all text in Hebrew
# ---------------------------------------------------------------------------

def _make_insurance_cert(rng_np):
    img = Image.new("RGB", (IMG_W, IMG_H), color=_rng_color(rng_np, light=True))
    draw = ImageDraw.Draw(img)

    hdr = tuple(rng_np.randint(0, 80, 3).tolist())
    draw.rectangle([0, 0, IMG_W, 30], fill=hdr)
    draw.text((6, 6), _heb("פוליסת ביטוח רכב"), font=_font(11), fill=(240, 240, 240))

    companies = [_heb(c) for c in ["הפניקס", "הראל", "מנורה", "מגדל", "AIG ישראל"]]
    coverages = [_heb(c) for c in ["צד שלישי", "מקיף", "בסיסי"]]
    fields = [
        (_heb("מבוטח"),       f"נהג {rng_np.randint(100, 999)}"),
        (_heb("מספר פוליסה"), f"{rng_np.randint(10000000, 99999999)}"),
        (_heb("מספר רכב"),    f"{rng_np.randint(10,99)}-{rng_np.randint(100,999)}-{rng_np.randint(10,99)}"),
        (_heb("בתוקף מ"),     f"0{rng_np.randint(1,9)}/0{rng_np.randint(1,9)}/{rng_np.randint(2020,2025)}"),
        (_heb("בתוקף עד"),    f"0{rng_np.randint(1,9)}/0{rng_np.randint(1,9)}/{rng_np.randint(2025,2028)}"),
        (_heb("חברת ביטוח"),  rng_np.choice(companies)),
        (_heb("סוג כיסוי"),   rng_np.choice(coverages)),
    ]
    y = 38
    for label, val in fields:
        _row(draw, 8, y, label, val, _font(8), _font(8))
        y += 20

    logo_color = tuple(rng_np.randint(100, 200, 3).tolist())
    draw.rectangle([IMG_W - 40, 2, IMG_W - 2, 28], fill=logo_color)

    sx, sy = int(rng_np.randint(10, 60)), int(rng_np.randint(155, 185))
    sr = int(rng_np.randint(14, 22))
    sc = tuple(rng_np.randint(80, 180, 3).tolist())
    draw.ellipse([sx, sy, sx + sr * 2, sy + sr * 2], outline=sc, width=2)
    draw.text((sx + 3, sy + sr - 5), _heb("תקף"), font=_font(7), fill=sc)
    return img


def _make_annual_license(rng_np):
    bg = tuple(rng_np.randint(245, 256, 3).tolist())
    img = Image.new("RGB", (IMG_W, IMG_H), color=bg)
    draw = ImageDraw.Draw(img)

    border = tuple(rng_np.randint(0, 120, 3).tolist())
    draw.rectangle([2, 2, IMG_W - 2, IMG_H - 2], outline=border, width=3)
    draw.rectangle([4, 4, IMG_W - 4, 32], fill=border)
    draw.text((8, 8), _heb("רישיון רכב שנתי"), font=_font(12), fill=(255, 255, 255))

    makes = [_heb(m) for m in ["טויוטה", "יונדאי", "קיה", "פורד", "פולקסווגן", "מאזדה"]]
    models = ["קורולה", "i20", "ספורטאז'", "פוקוס", "גולף", "CX-5"]
    colors = [_heb(c) for c in ["לבן", "כסוף", "שחור", "כחול", "אדום"]]
    fields = [
        (_heb("בעלים"),       f"בעלים {rng_np.randint(100, 999)}"),
        (_heb("מספר רישוי"),  f"{rng_np.randint(10000000, 99999999)}"),
        (_heb("לוחית זיהוי"), f"{rng_np.randint(10,99)}-{rng_np.randint(100,999)}-{rng_np.randint(10,99)}"),
        (_heb("יצרן"),        rng_np.choice(makes)),
        (_heb("דגם"),         rng_np.choice(models)),
        (_heb("שנת ייצור"),   str(rng_np.randint(2010, 2024))),
        (_heb("תוקף רישיון"), f"0{rng_np.randint(1,9)}/{rng_np.randint(2024,2027)}"),
        (_heb("צבע"),         rng_np.choice(colors)),
    ]
    y = 40
    for label, val in fields:
        _row(draw, 10, y, label, val, _font(8), _font(8))
        y += 20

    seal_x = int(rng_np.randint(148, 172))
    seal_y = int(rng_np.randint(158, 188))
    draw.rectangle([seal_x, seal_y, seal_x + 52, seal_y + 22], fill=border)
    draw.text((seal_x + 4, seal_y + 4), _heb("משרד התחבורה"), font=_font(7), fill=(255, 255, 255))
    return img


def _make_traffic_ticket(rng_np):
    bg = tuple(rng_np.randint(250, 256, 3).tolist())
    img = Image.new("RGB", (IMG_W, IMG_H), color=bg)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, IMG_W, 28], fill=(180, 20, 20))
    draw.text((6, 6), _heb("דוח עבירת תנועה"), font=_font(11), fill=(255, 255, 255))

    offenses = [_heb(o) for o in [
        "עבירת מהירות", "מעבר באור אדום", "אי חגירת חגורה",
        "חניה אסורה", "שימוש בטלפון נייד",
    ]]
    cities = [_heb(c) for c in ["תל אביב", "ירושלים", "חיפה", "באר שבע", "ראשון לציון"]]
    fields = [
        (_heb("מספר דוח"),    f"TKT{rng_np.randint(1000000, 9999999)}"),
        (_heb("תאריך"),       f"0{rng_np.randint(1,9)}/0{rng_np.randint(1,9)}/{rng_np.randint(2020,2025)}"),
        (_heb("לוחית זיהוי"), f"{rng_np.randint(10,99)}-{rng_np.randint(100,999)}-{rng_np.randint(10,99)}"),
        (_heb("עבירה"),       rng_np.choice(offenses)),
        (_heb('קנס (ש"ח)'),  str(rng_np.randint(250, 3000))),
        (_heb("שוטר"),        f"תג {rng_np.randint(1000, 9999)}"),
        (_heb("מיקום"),       rng_np.choice(cities)),
        (_heb("תשלום עד"),    f"0{rng_np.randint(1,9)}/0{rng_np.randint(1,9)}/{rng_np.randint(2025,2027)}"),
    ]
    y = 36
    for label, val in fields:
        _row(draw, 8, y, label, val, _font(8), _font(8))
        y += 20

    sx = int(rng_np.randint(138, 162))
    sy = int(rng_np.randint(168, 192))
    draw.ellipse([sx, sy, sx + 52, sy + 24], outline=(180, 20, 20), width=2)
    draw.text((sx + 6, sy + 5), _heb("משטרת ישראל"), font=_font(7), fill=(180, 20, 20))
    return img


def _make_vehicle_photo(rng_np):
    # ponytail: geometric car approximation; replace with real photos if >75% target not met
    body = tuple(rng_np.randint(30, 220, 3).tolist())
    bg = tuple(rng_np.randint(150, 230, 3).tolist())
    img = Image.new("RGB", (IMG_W, IMG_H), color=bg)
    draw = ImageDraw.Draw(img)

    road = tuple(rng_np.randint(80, 130, 3).tolist())
    draw.rectangle([0, IMG_H * 2 // 3, IMG_W, IMG_H], fill=road)

    cx = int(rng_np.randint(20, 40))
    cw = int(rng_np.randint(130, 160))
    cy = int(rng_np.randint(90, 110))
    ch = int(rng_np.randint(50, 70))
    draw.rectangle([cx, cy, cx + cw, cy + ch], fill=body)

    ri = int(rng_np.randint(15, 25))
    draw.rectangle([cx + ri, cy - int(rng_np.randint(18, 28)), cx + cw - ri, cy], fill=body)
    draw.rectangle([cx + ri + 5, cy - int(rng_np.randint(16, 24)),
                    cx + cw - ri - 5, cy - 2], fill=(180, 210, 230))

    wr = int(rng_np.randint(10, 14))
    for wx in [cx + 20, cx + cw - 20]:
        wy = cy + ch
        draw.ellipse([wx - wr, wy - wr, wx + wr, wy + wr], fill=(30, 30, 30))

    plate = f"{rng_np.randint(10,99)}-{rng_np.randint(100,999)}-{rng_np.randint(10,99)}"
    draw.rectangle([cx + cw // 2 - 22, cy + ch - 14, cx + cw // 2 + 22, cy + ch - 2],
                   fill=(255, 255, 200))
    draw.text((cx + cw // 2 - 20, cy + ch - 13), plate, font=_font(8), fill=(0, 0, 0))
    return img


def _make_other(rng_np):
    bg = tuple(rng_np.randint(240, 256, 3).tolist())
    img = Image.new("RGB", (IMG_W, IMG_H), color=bg)
    draw = ImageDraw.Draw(img)

    services = [_heb(s) for s in ["החלפת שמן", "גלגלים", "בלמים", "מיזוג"]]
    docs = [
        (_heb("קבלה"), [
            (_heb("פריט"),   f"שירות #{rng_np.randint(1,99)}"),
            (_heb("סכום"),   f"{rng_np.randint(50, 5000)} ש\"ח"),
            (_heb("תאריך"),  f"0{rng_np.randint(1,9)}/0{rng_np.randint(1,9)}/202{rng_np.randint(0,5)}"),
            (_heb("אסמכתא"), f"RC{rng_np.randint(10000,99999)}"),
        ]),
        (_heb("חשבונית מס"), [
            (_heb("מספר חשבונית"), f"INV{rng_np.randint(10000,99999)}"),
            (_heb("לקוח"),         f"לקוח {rng_np.randint(100,999)}"),
            (_heb('סה"כ'),         f"{rng_np.randint(200, 20000)} ש\"ח"),
            (_heb('מע"מ'),         f"{rng_np.randint(14,18)}%"),
        ]),
        (_heb("כרטיס שירות רכב"), [
            (_heb("רכב"),   f"{rng_np.randint(10,99)}-{rng_np.randint(100,999)}-{rng_np.randint(10,99)}"),
            (_heb("שירות"), rng_np.choice(services)),
            (_heb('ק"מ'),   str(rng_np.randint(10000, 200000))),
            (_heb("מוסך"),  f"מוסך {rng_np.randint(1,99)}"),
        ]),
    ]

    title, fields = docs[int(rng_np.randint(0, 3))]
    hdr = tuple(rng_np.randint(40, 160, 3).tolist())
    draw.rectangle([0, 0, IMG_W, 28], fill=hdr)
    draw.text((6, 6), title, font=_font(11), fill=(255, 255, 255))

    y = 36
    for label, val in fields:
        _row(draw, 8, y, label, val, _font(8), _font(8))
        y += 20

    line_color = tuple(rng_np.randint(150, 200, 3).tolist())
    for ly in range(y + 5, IMG_H - 10, 12):
        draw.line([8, ly, IMG_W - 8, ly], fill=line_color, width=1)
    return img


_MAKERS = {
    "insurance_cert": _make_insurance_cert,
    "annual_license": _make_annual_license,
    "traffic_ticket": _make_traffic_ticket,
    "vehicle_photo":  _make_vehicle_photo,
    "other":          _make_other,
}


def generate(seed: int, n_per_class: int) -> tuple:
    """Generate synthetic Hebrew fleet document images.

    Args:
        seed: RNG seed for full determinism.
        n_per_class: Number of images per class.

    Returns:
        (images, labels): list[PIL.Image], list[str]
    """
    rng_np = np.random.RandomState(seed)
    images, labels = [], []
    for cls in CLASSES:
        for _ in range(n_per_class):
            images.append(_MAKERS[cls](rng_np))
            labels.append(cls)
    return images, labels
