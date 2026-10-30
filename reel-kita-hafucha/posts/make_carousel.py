#!/usr/bin/env python3
"""Instagram/Facebook carousel (5 slides, 1080x1350) for the flipped-classroom reel.
Each slide tags the logical connector it uses, so the post itself teaches the topic.
Usage: python3 make_carousel.py STUDIO_FRAME.png OUT_DIR"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts")
W, H = 1080, 1350
NAVY_D, NAVY, NAVY2 = (6, 16, 34), (11, 31, 58), (20, 52, 90)
TURQ, YELL, WHITE, MUTED = (46, 230, 214), (255, 214, 10), (255, 255, 255), (170, 190, 215)


def font(size, w="900Black"):
    return ImageFont.truetype(os.path.join(FONTS, f"Heebo_{w}.ttf"), size)


def base():
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    g = np.array(NAVY_D) + (np.array(NAVY2) - np.array(NAVY_D)) * np.exp(-((x - 0.5) / 0.55) ** 2 - ((y - 0.35) / 0.45) ** 2)
    img = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for gx in range(0, W, 60):
        d.line([gx, 0, gx, H], fill=(16, 38, 66), width=1)
    for gy in range(0, H, 60):
        d.line([0, gy, W, gy], fill=(16, 38, 66), width=1)
    return img


def glow_text(img, xy, text, f, fill, anchor="mm", glow=TURQ, radius=18, strength=0.6):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text(xy, text, font=f, fill=glow + (int(255 * strength),), anchor=anchor, direction="rtl")
    img.paste(lay.filter(ImageFilter.GaussianBlur(radius)), (0, 0), lay.filter(ImageFilter.GaussianBlur(radius)))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=fill, anchor=anchor, direction="rtl")


def text(img, xy, s, size, fill=WHITE, w="900Black", anchor="mm"):
    ImageDraw.Draw(img).text(xy, s, font=font(size, w), fill=fill, anchor=anchor, direction="rtl")


def pill(img, cx, cy, s, size=40, fg=NAVY, bg=TURQ, pad=34, outline=None, w="900Black"):
    d = ImageDraw.Draw(img)
    f = font(size, w)
    tw = d.textlength(s, font=f, direction="rtl")
    h = int(size * 1.6)
    box = [cx - tw / 2 - pad, cy - h / 2, cx + tw / 2 + pad, cy + h / 2]
    d.rounded_rectangle(box, h // 2, fill=bg, outline=outline, width=4 if outline else 0)
    d.text((cx, cy + 2), s, font=f, fill=fg, anchor="mm", direction="rtl")
    return box


def card(img, box, r=36, fill=NAVY, outline=TURQ):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=4)


def footer(img, n):
    d = ImageDraw.Draw(img)
    for i in range(5):
        x = W / 2 + (2 - i) * 34
        d.ellipse([x - 8, H - 62, x + 8, H - 46], fill=YELL if i == n else (60, 85, 120))
    text(img, (W - 60, H - 54), "כיתה הפוכה", 30, TURQ, "700Bold", anchor="rm")
    if n < 4:
        text(img, (100, H - 54), "החליקו", 30, MUTED, "700Bold", anchor="lm")
        ImageDraw.Draw(img).polygon([(60, H - 54), (84, H - 66), (84, H - 42)], fill=MUTED)


def connector_tag(img, word, kind, cy=H - 150):
    pill(img, W / 2, cy, f"{word} = קשר של {kind}", size=34, fg=NAVY, bg=YELL, pad=28)


def arrow_down(img, cx, y0, length=70, col=YELL):
    d = ImageDraw.Draw(img)
    d.rectangle([cx - 6, y0, cx + 6, y0 + length - 22], fill=col)
    d.polygon([(cx - 22, y0 + length - 24), (cx + 22, y0 + length - 24), (cx, y0 + length)], fill=col)


def slide1(photo, out):
    ph = Image.open(photo).convert("RGB")
    img = ph.crop((0, 380, 1080, 380 + H))
    a = np.asarray(img).astype(np.float32)
    g = np.clip((np.arange(H) - 620) / 520, 0, 1)[:, None, None] * 0.92
    a = a * (1 - g) + np.array(NAVY_D) * g
    img = Image.fromarray(a.astype(np.uint8))
    pill(img, W / 2, 860, "כיתה הפוכה", 44)
    glow_text(img, (W / 2, 985), "למה אני הופך", font(112), WHITE)
    glow_text(img, (W / 2, 1105), "את הכיתה?", font(112), YELL, glow=YELL, strength=0.35)
    text(img, (W / 2, 1210), "ולא — זה לא כדי להקשות עליכם", 44, TURQ, "700Bold")
    footer(img, 0)
    img.save(out, quality=95)


def slide2(out):
    img = base()
    text(img, (W / 2, 150), "איך זה עובד?", 96, WHITE)
    text(img, (W / 2, 245), "המודל בשלושה שלבים", 44, TURQ, "700Bold")
    steps = [("1", "בבית", "לומדים את החומר בקצב שלכם"), ("2", "בכיתה", "תרגול וחזרה עם המורה"),
             ("3", "מבדק קצר", "10 שאלות — ויודעים איפה עומדים")]
    y = 330
    for i, (n, t, s) in enumerate(steps):
        card(img, [110, y, W - 110, y + 220])
        d = ImageDraw.Draw(img)
        d.ellipse([W - 230, y + 55, W - 120, y + 165], fill=YELL)
        text(img, (W - 175, y + 112), n, 64, NAVY)
        text(img, (W - 270, y + 80), t, 64, WHITE, anchor="rm")
        text(img, (W - 270, y + 158), s, 40, MUTED, "700Bold", anchor="rm")
        if i < 2:
            arrow_down(img, W / 2, y + 222, 50)
        y += 290
    footer(img, 1)
    img.save(out, quality=95)


def slide3(out):
    img = base()
    text(img, (W / 2, 160), "המטרה האמיתית", 60, TURQ, "800ExtraBold")
    card(img, [140, 260, W - 140, 440], fill=(16, 30, 52), outline=(90, 110, 140))
    text(img, (W / 2, 350), "לא כדי להקשות עליכם", 66, (150, 165, 185))
    d = ImageDraw.Draw(img)
    d.rectangle([180, 344, W - 180, 356], fill=YELL)
    glow_text(img, (W / 2, 590), "אלא", font(170), YELL, glow=YELL, strength=0.45)
    card(img, [110, 720, W - 110, 980])
    text(img, (W / 2, 800), "כדי להכין אתכם", 76, WHITE)
    text(img, (W / 2, 900), "למיומנות של לומדים עצמאיים", 50, TURQ, "800ExtraBold")
    connector_tag(img, "אלא", "ניגוד", cy=1120)
    footer(img, 2)
    img.save(out, quality=95)


def slide4(out):
    img = base()
    text(img, (W / 2, 150), "למה זה חשוב?", 96, WHITE)
    pill(img, W / 2 + 200, 330, "אוניברסיטאות", 50, fg=WHITE, bg=NAVY2, outline=TURQ)
    text(img, (W / 2 - 40, 330), "+", 90, YELL)
    pill(img, W / 2 - 240, 330, "מכללות", 50, fg=WHITE, bg=NAVY2, outline=TURQ)
    arrow_down(img, W / 2, 400, 90)
    pill(img, W / 2, 560, "קורסים מקוונים", 60, fg=NAVY, bg=TURQ)
    card(img, [110, 690, W - 110, 1010])
    text(img, (W / 2, 780), "מי שיודע ללמוד לבד", 64, WHITE)
    text(img, (W / 2, 870), "מגיע מוכן", 64, YELL)
    text(img, (W / 2, 950), "לכיתה היום, ולאקדמיה מחר", 42, MUTED, "700Bold")
    connector_tag(img, "כדי ש...", "תכלית", cy=1120)
    footer(img, 3)
    img.save(out, quality=95)


def slide5(out):
    img = base()
    text(img, (W / 2, 170), "אין דבר כזה", 100, YELL)
    for i, s in enumerate(["לא ידעתי", "לא שמעתי", "לא עשיתי"]):
        cx = (820, 540, 260)[i]
        box = pill(img, cx, 330, s, 48, fg=WHITE, bg=NAVY2, outline=TURQ, pad=26)
        ImageDraw.Draw(img).rectangle([box[0] + 14, 326, box[2] - 14, 336], fill=YELL)
    card(img, [110, 450, W - 110, 800])
    text(img, (W / 2, 540), "אני זמין לשאלות", 72, WHITE)
    text(img, (W / 2, 640), "וואטסאפ · משוב · פנים אל פנים", 44, TURQ, "800ExtraBold")
    text(img, (W / 2, 725), "שבוע של למידה — ואז מתרגלים יחד", 40, MUTED, "700Bold")
    box = pill(img, W / 2 + 26, 920, "צפו ברילס המלא", 54, fg=NAVY, bg=YELL, pad=80)
    ImageDraw.Draw(img).polygon([(box[0] + 34, 920), (box[0] + 62, 902), (box[0] + 62, 938)], fill=NAVY)
    text(img, (W / 2, 1040), "שמרו · שתפו עם מורה שצריך את זה", 40, WHITE, "700Bold")
    connector_tag(img, "וגם", "הוספה", cy=1150)
    footer(img, 4)
    img.save(out, quality=95)


if __name__ == "__main__":
    photo, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    slide1(photo, os.path.join(out, "slide1.jpg"))
    slide2(os.path.join(out, "slide2.jpg"))
    slide3(os.path.join(out, "slide3.jpg"))
    slide4(os.path.join(out, "slide4.jpg"))
    slide5(os.path.join(out, "slide5.jpg"))
    print("ok")
