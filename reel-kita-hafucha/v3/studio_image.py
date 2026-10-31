#!/usr/bin/env python3
"""Vertical virtual studio built from the user's 16:9 studio render.

The landscape image is upscaled x2 into a canvas larger than the 9:16 frame (room for
parallax). The original big screen (a world map, unrelated to the lesson) is replaced
by lesson content per topic, laid out to the sides of the presenter's head.

make_studio(out_dir, image) writes:
  studio_base.png       canvas with an empty screen (dark glass + grid)
  screen_<key>.png      RGBA screen content per topic (same canvas)
  screen_mask.png       where the screen is (for the animated light sweep)"""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SCALE = 2
BG_W, BG_H = 1920 * SCALE, 1080 * SCALE
CX, CY = 880 * SCALE, 540 * SCALE          # canvas point that sits at the frame centre
KEYS = ("why", "flip", "self", "logic", "end")
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")

NAVY = (16, 27, 53)            # #101B35
CYAN = (0, 217, 232)           # #00D9E8
YELL = (255, 212, 71)          # #FFD447
SOFT = (101, 175, 255)         # #65AFFF
WHITE = (255, 255, 255)

# screen outline measured on the source image (x, top, bottom), original pixels
EDGES = [(645, 347, 634), (708, 344, 636), (868, 348, 635), (1028, 342, 636), (1188, 340, 639),
         (1348, 338, 644), (1508, 330, 652), (1625, 323, 662)]


def out2canvas(x, y):
    """frame coordinates (1080x1920, camera at rest) -> canvas coordinates"""
    return x - 540 + CX, y - 960 + CY


def font(size, w="900Black"):
    return ImageFont.truetype(os.path.join(FONTS, f"Heebo_{w}.ttf"), size)


def screen_polygon(inset=-3):
    """slightly larger than the measured screen so no pixel of the old content survives"""
    top = [(x * SCALE, (t + inset) * SCALE) for x, t, b in EDGES]
    bot = [(x * SCALE, (b - inset + 2) * SCALE) for x, t, b in reversed(EDGES)]
    return top + bot


def t(d, xy, s, size, fill, w="900Black"):
    d.text(out2canvas(*xy), s, font=font(size, w), fill=fill + (255,), anchor="mm", direction="rtl")


def node(d, xy, r, col):
    x, y = out2canvas(*xy)
    d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))


def link(d, a, b, col=CYAN, w=6, alpha=200):
    d.line([out2canvas(*a), out2canvas(*b)], fill=col + (alpha,), width=w)


def house(d, cx, cy, s, col):
    x, y = out2canvas(cx, cy)
    d.polygon([(x - 50 * s, y), (x, y - 45 * s), (x + 50 * s, y)], fill=col + (255,))
    d.rectangle([x - 36 * s, y, x + 36 * s, y + 50 * s], fill=col + (255,))


def board(d, cx, cy, s, col):
    x, y = out2canvas(cx, cy)
    d.rectangle([x - 55 * s, y - 38 * s, x + 55 * s, y + 30 * s], outline=col + (255,), width=int(8 * s))
    d.line([x, y + 30 * s, x - 25 * s, y + 60 * s], fill=col + (255,), width=int(7 * s))
    d.line([x, y + 30 * s, x + 25 * s, y + 60 * s], fill=col + (255,), width=int(7 * s))


def laptop(d, cx, cy, s, col):
    x, y = out2canvas(cx, cy)
    d.rectangle([x - 45 * s, y - 32 * s, x + 45 * s, y + 22 * s], outline=col + (255,), width=int(7 * s))
    d.polygon([(x - 62 * s, y + 30 * s), (x + 62 * s, y + 30 * s), (x + 52 * s, y + 42 * s), (x - 52 * s, y + 42 * s)],
              fill=col + (255,))


def arrow(d, a, b, col=YELL, w=8):
    (x1, y1), (x2, y2) = out2canvas(*a), out2canvas(*b)
    d.line([x1, y1, x2, y2], fill=col + (255,), width=w)
    ang = np.arctan2(y2 - y1, x2 - x1)
    for s in (-1, 1):
        d.line([x2, y2, x2 - 30 * np.cos(ang + s * 0.5), y2 - 30 * np.sin(ang + s * 0.5)], fill=col + (255,), width=w)


def content(key):
    lay = Image.new("RGBA", (BG_W, BG_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # layout: the presenter's head covers x≈360..720 (frame coords); content lives beside it
    if key == "why":
        t(d, (880, 720), "למה", 130, YELL)
        t(d, (880, 850), "כיתה הפוכה", 54, WHITE, "800ExtraBold")
        t(d, (190, 760), "?", 230, CYAN)
    elif key == "flip":
        house(d, (880), 690, 1.3, YELL)
        t(d, (880, 830), "בבית", 70, WHITE)
        t(d, (880, 905), "לומדים", 46, CYAN, "800ExtraBold")
        board(d, 190, 700, 1.2, YELL)
        t(d, (190, 830), "בכיתה", 70, WHITE)
        t(d, (190, 905), "מתרגלים", 46, CYAN, "800ExtraBold")
        arrow(d, (760, 640), (330, 640))
    elif key == "self":
        t(d, (880, 700), "למידה", 92, CYAN)
        t(d, (880, 800), "עצמאית", 92, CYAN)
        t(d, (880, 890), "מיומנות לחיים", 42, WHITE, "800ExtraBold")
        laptop(d, 190, 720, 1.3, YELL)
        t(d, (190, 840), "קורסים", 50, WHITE, "800ExtraBold")
        t(d, (190, 900), "מקוונים", 50, WHITE, "800ExtraBold")
    elif key == "logic":
        t(d, (880, 640), "קשרים לוגיים", 50, YELL)
        hub = (540, 660)
        pts = [((880, 760), "לכן", "סיבה ותוצאה"), ((190, 700), "אבל", "ניגוד"), ((190, 900), "וגם", "הוספה"),
               ((880, 930), "כמו", "השוואה")]
        for (xy, w, k) in pts:
            link(d, hub, xy)
        for (xy, w, k) in pts:
            node(d, xy, 16, CYAN)
            t(d, (xy[0], xy[1] - 52), w, 56, WHITE)
            t(d, (xy[0], xy[1] + 44), k, 34, SOFT, "700Bold")
    elif key == "end":
        t(d, (880, 720), "כיתה", 110, YELL)
        t(d, (880, 840), "הפוכה", 110, YELL)
        for i, x in enumerate((110, 190, 270)):
            node(d, (x, 780), 18, YELL if i == 1 else CYAN)
        link(d, (110, 780), (270, 780), WHITE, 5)
        t(d, (190, 870), "חושבים · מקשרים", 36, WHITE, "700Bold")
    g = lay.filter(ImageFilter.GaussianBlur(10))
    return Image.alpha_composite(g, lay)


def make_studio(out_dir, image):
    os.makedirs(out_dir, exist_ok=True)
    src = cv2.imread(image)
    big = cv2.resize(src, (BG_W, BG_H), interpolation=cv2.INTER_LANCZOS4)
    poly = np.array(screen_polygon(), np.int32)
    mask = np.zeros((BG_H, BG_W), np.uint8)
    cv2.fillPoly(mask, [poly], 255)
    # empty screen: dark navy glass with a faint grid, light falloff towards the edges
    glass = np.zeros_like(big, np.float32)
    glass[:] = NAVY[::-1]
    yy, xx = np.mgrid[0:BG_H, 0:BG_W]
    glass[(xx % 64 < 2) | (yy % 64 < 2)] = (60, 45, 28)
    m = cv2.GaussianBlur(mask, (0, 0), 1.5).astype(np.float32)[..., None] / 255
    base = big.astype(np.float32) * (1 - m) + glass * m
    # depth of field on the whole set (the presenter is sharp, the studio is not)
    base = cv2.GaussianBlur(base, (0, 0), 2.2)
    cv2.imwrite(os.path.join(out_dir, "studio_base.png"), np.clip(base, 0, 255).astype(np.uint8))
    cv2.imwrite(os.path.join(out_dir, "screen_mask.png"), mask)
    for k in KEYS:
        c = content(k)
        a = np.asarray(c)[..., 3].astype(np.float32) * (mask.astype(np.float32) / 255)
        arr = np.asarray(c).copy()
        arr[..., 3] = a.astype(np.uint8)
        Image.fromarray(arr).filter(ImageFilter.GaussianBlur(1.6)).save(os.path.join(out_dir, f"screen_{k}.png"))


if __name__ == "__main__":
    import sys
    make_studio(sys.argv[1], sys.argv[2])
