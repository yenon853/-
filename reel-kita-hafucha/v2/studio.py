#!/usr/bin/env python3
"""Procedural virtual studio (deep navy + turquoise architectural light, warm accents,
minimal bookshelves, large digital screen). Everything is drawn here, no stock assets.

make_studio(out_dir) writes:
  studio_base.png      – wall, light strips, shelves, bokeh (with depth-of-field blur)
  screen_<key>.png     – RGBA content for the big screen, one per topic
Canvas is larger than the frame (BG_W x BG_H) so the camera can parallax over it."""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BG_W, BG_H = 1400, 2490
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "fonts", "Heebo_900Black.ttf")
FONT_B = os.path.join(HERE, "..", "fonts", "Heebo_700Bold.ttf")

NAVY_D, NAVY, NAVY_L = (6, 16, 34), (11, 31, 58), (20, 52, 90)
TURQ, YELL, WARM = (46, 230, 214), (255, 214, 10), (255, 170, 90)

# screen rectangle on the canvas (behind and above the presenter's head)
SCREEN = (230, 330, 1170, 1010)


def glow(img, radius, strength=1.0):
    g = img.filter(ImageFilter.GaussianBlur(radius))
    a = np.asarray(g).astype(np.float32) * strength
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), img.mode)


def add(base, layer):
    b = np.asarray(base).astype(np.float32)
    l = np.asarray(layer.convert("RGB")).astype(np.float32)
    return Image.fromarray(np.clip(b + l, 0, 255).astype(np.uint8))


def make_studio(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(7)
    y = np.linspace(0, 1, BG_H)[:, None]
    x = np.linspace(0, 1, BG_W)[None, :]
    # wall: vertical gradient + soft central light pool
    top, mid, bot = np.array(NAVY_D), np.array(NAVY_L), np.array(NAVY_D)
    grad = np.where(y < 0.45, top + (mid - top) * (y / 0.45), mid + (bot - mid) * ((y - 0.45) / 0.55))
    pool = np.exp(-(((x - 0.5) / 0.32) ** 2 + ((y - 0.42) / 0.30) ** 2))[..., None]
    wall = grad[:, None, :] * (0.75 + 0.55 * pool) + np.array([4, 20, 30]) * pool
    img = Image.fromarray(np.clip(wall, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    # acoustic wall panels (slightly lighter vertical slats)
    for px in range(40, BG_W, 70):
        d.rectangle([px, 0, px + 3, BG_H], fill=(24, 48, 80))
    # floor plane + horizon line
    d.rectangle([0, 1900, BG_W, BG_H], fill=(8, 18, 34))
    lights = Image.new("RGB", (BG_W, BG_H), (0, 0, 0))
    ld = ImageDraw.Draw(lights)
    # architectural vertical LED strips (turquoise) and warm cove line
    for lx in (95, BG_W - 115):
        ld.rounded_rectangle([lx, 150, lx + 16, 1880], 8, fill=TURQ)
    ld.rectangle([0, 1895, BG_W, 1902], fill=WARM)
    img = add(img, glow(lights, 40, 1.2))
    img = add(img, glow(lights, 10, 0.9))
    img = add(img, lights.point(lambda v: int(v * 0.8)))
    d = ImageDraw.Draw(img)
    # minimalist bookshelves left/right with warm under-shelf light
    warm = Image.new("RGB", (BG_W, BG_H), (0, 0, 0))
    wd = ImageDraw.Draw(warm)
    book_cols = [(40, 70, 105), (150, 145, 135), (40, 110, 110), (160, 120, 80), (55, 80, 120), (95, 70, 80)]
    for side in (0, 1):
        x0, x1 = (150, 470) if side == 0 else (BG_W - 470, BG_W - 150)
        for sy in (1180, 1430, 1680):
            d.rectangle([x0, sy, x1, sy + 14], fill=(30, 46, 70))
            wd.rectangle([x0 + 10, sy + 14, x1 - 10, sy + 20], fill=WARM)
            bx = x0 + 12
            while bx < x1 - 30:
                bw = int(rng.integers(16, 34)); bh = int(rng.integers(120, 190))
                if rng.random() < 0.18:
                    bx += bw + 10
                    continue
                col = tuple(int(c * rng.uniform(0.45, 0.7)) for c in book_cols[int(rng.integers(len(book_cols)))])
                d.rectangle([bx, sy - bh, bx + bw, sy], fill=col)
                bx += bw + int(rng.integers(2, 6))
            # small plant / object
            ox = x0 + (40 if side else x1 - x0 - 90)
            d.ellipse([ox, sy - 70, ox + 60, sy], fill=(26, 90, 80))
    img = add(img, glow(warm, 22, 1.4))
    # screen bezel + inner glass
    sx0, sy0, sx1, sy1 = SCREEN
    frame = Image.new("RGB", (BG_W, BG_H), (0, 0, 0))
    fd = ImageDraw.Draw(frame)
    fd.rounded_rectangle([sx0 - 6, sy0 - 6, sx1 + 6, sy1 + 6], 26, outline=TURQ, width=5)
    img = add(img, glow(frame, 28, 1.3))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([sx0, sy0, sx1, sy1], 22, fill=(7, 20, 40))
    # subtle grid on screen glass
    for gx in range(sx0 + 40, sx1, 60):
        d.line([gx, sy0 + 10, gx, sy1 - 10], fill=(12, 34, 60), width=1)
    for gy in range(sy0 + 40, sy1, 60):
        d.line([sx0 + 10, gy, sx1 - 10, gy], fill=(12, 34, 60), width=1)
    img = add(img, frame.point(lambda v: int(v * 0.7)))
    # bokeh
    bok = Image.new("RGB", (BG_W, BG_H), (0, 0, 0))
    bd = ImageDraw.Draw(bok)
    for _ in range(14):
        bx, by = int(rng.integers(0, BG_W)), int(rng.integers(1100, 1880))
        r = int(rng.integers(26, 60))
        col = TURQ if rng.random() < 0.55 else WARM
        k = rng.uniform(0.10, 0.22)
        bd.ellipse([bx - r, by - r, bx + r, by + r], fill=tuple(int(c * k) for c in col))
    img = add(img, bok.filter(ImageFilter.GaussianBlur(10)))
    # edge vignette keeps attention in the centre
    vg = np.exp(-(((x - 0.5) / 0.62) ** 2 + ((y - 0.45) / 0.75) ** 2))[..., None]
    img = Image.fromarray((np.asarray(img).astype(np.float32) * (0.55 + 0.45 * vg)).astype(np.uint8))
    # depth of field: everything behind the presenter is soft
    base = cv2.GaussianBlur(np.asarray(img)[:, :, ::-1], (0, 0), 4.5)
    cv2.imwrite(os.path.join(out_dir, "studio_base.png"), base)

    # ---- screen contents (RGBA, same canvas); drawn sharp, blurred lightly at use
    fb = ImageFont.truetype(FONT, 118)
    fs = ImageFont.truetype(FONT_B, 54)
    screens = {
        "flip": ("כיתה הפוכה", "לומדים בבית · מתרגלים בכיתה"),
        "logic": ("קשרים לוגיים", "סיבה ותוצאה · ניגוד · הוספה"),
        "self": ("למידה עצמאית", "מיומנות לחיים"),
        "end": ("כיתה הפוכה", "חושבים · מקשרים · לומדים"),
    }
    for key, (title, sub) in screens.items():
        lay = Image.new("RGBA", (BG_W, BG_H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        cx = (sx0 + sx1) // 2
        ld.text((cx, sy0 + 150), title, font=fb, fill=TURQ + (255,), anchor="mm", direction="rtl")
        ld.text((cx, sy0 + 260), sub, font=fs, fill=(235, 240, 250, 230), anchor="mm", direction="rtl")
        # node graph motif along the bottom of the screen
        nodes = [(sx0 + 170, sy1 - 150), (cx - 120, sy1 - 220), (cx + 140, sy1 - 130), (sx1 - 170, sy1 - 210)]
        for (ax, ay), (bx, by) in zip(nodes, nodes[1:]):
            ld.line([ax, ay, bx, by], fill=(46, 230, 214, 160), width=5)
        for i, (nx, ny) in enumerate(nodes):
            c = YELL if i % 2 else TURQ
            ld.ellipse([nx - 16, ny - 16, nx + 16, ny + 16], fill=c + (255,))
        g = lay.filter(ImageFilter.GaussianBlur(14))
        out = Image.alpha_composite(g, lay).filter(ImageFilter.GaussianBlur(1.2))
        out.save(os.path.join(out_dir, f"screen_{key}.png"))


if __name__ == "__main__":
    import sys
    make_studio(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "assets"))
