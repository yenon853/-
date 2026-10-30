#!/usr/bin/env python3
"""
build_v2.py — "כיתה הפוכה – לומדים קשרים לוגיים", high-energy studio version.

Pipeline
  1. matte.py       ISNet person matte for every frame (cached PNGs)
  2. studio.py      procedural virtual studio + big-screen contents
  3. this file      camera moves (punch/zoom-out/split/whip), compositing with relight,
                    rim light, wall shadow, light wrap; kinetic captions + graphics (ASS);
                    SFX (whoosh/pop/click) synced to the graphics; music; mix; cover.

Reuses the cut list, transcript and caption lines from ../build_reel.py.
Usage: python3 build_v2.py SOURCE.mp4 MATTE_DIR [--ass-only] [--audio-only]
"""
import json, math, os, subprocess, sys, wave
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import build_reel as R          # noqa: E402
import studio                   # noqa: E402

SRC, MATTE = sys.argv[1], sys.argv[2]
R.SRC = SRC
OUT = os.path.join(HERE, "..", "output_v2")
TMP = os.path.join(OUT, "_tmp")
ASSETS = os.path.join(TMP, "studio")
W, H, FPS = R.W, R.H, R.FPS
SW, SH = R.SW, R.SH
o, SEG, SEGMENTS = R.o, R.SEG, R.SEGMENTS
NAVY, TURQ, YELL, WHITE = R.NAVY, R.TURQ, R.YELL, R.WHITE
EYE = 0.42
END_CARD = 2.6
VOICE_END = R.VOICE_END
TOTAL = VOICE_END + END_CARD


def L(seg, src_t):
    """source time -> local time inside a segment"""
    return src_t - SEG[seg]["src_in"]


# ============================================================ camera
# keys per segment: (local_t, zoom, dx, ease_seconds). A key starts a move that
# lasts ease_seconds (short = punch/snap, long = drift). dx shifts the presenter
# sideways for split-screen layouts (positive = to the right).
CAM = {
    "H": [(0, 1.20, 0, 0), (0.18, 1.40, 0, 0.14), (0.4, 1.40, 0, 0), (3.5, 1.46, 0, 3.0),
          (L("H", 50.22), 1.58, 0, 0.12),                       # punch: "להקשות"
          (L("H", 51.15), 1.00, 230, 0.32),                      # split: contrast panel
          (L("H", 55.10), 0.92, 0, 0.45),                        # zoom-out reveal: cause -> effect
          (L("H", 57.50), 1.04, -225, 0.32),                     # split: addition stack
          (L("H", 60.60), 1.12, -225, 0.12)],                    # punch: "קורסים מקוונים"
    "M": [(0, 1.22, 0, 0), (1.8, 1.26, 0, 1.8),
          (L("M", 18.30), 1.00, -225, 0.32),                     # split: flipped-classroom panel
          (L("M", 24.75), 1.08, -225, 0.12)],                    # punch: "במבדק"
    "A": [(0, 1.14, 0, 0), (3.6, 1.22, 0, 3.6),
          (L("A", 65.85), 1.02, 0, 0.35),                        # zoom-out reveal
          (L("A", 66.70), 1.12, 0, 0.12),                        # punch: "למידה עצמאית"
          (L("A", 69.50), 1.00, 230, 0.32),                      # split: sequence panel
          (L("A", 76.75), 1.08, 230, 0.12)],                     # punch: "בלי למידה"
    "T": [(0, 1.26, 0, 0), (L("T", 29.72), 0.92, 0, 0.45)],      # zoom-out reveal: concept map
    "C": [(0, 0.92, 0, 0),                                       # matches T framing (match cut)
          (L("C", 81.45), 1.30, 0, 0.12), (L("C", 82.32), 1.36, 0, 0.1),
          (L("C", 83.26), 1.42, 0, 0.1), (L("C", 84.48), 1.48, 0, 0.1),   # stair punches
          (L("C", 85.62), 1.06, 0, 0.3)],                        # zoom-out: "אני זמין"
    "E": [(0, 1.16, 0, 0), (2.25, 1.30, 0, 2.25)],
}
# transitions at the end of a segment (into the next one)
TRANS = {"H": "whip_l", "M": "zoomblur", "A": "whip_r", "T": "cut", "C": "whip_l", "E": "pull"}
TRANS_FR = 6


def ease(a):
    a = min(max(a, 0.0), 1.0)
    return a * a * (3 - 2 * a)


def cam_at(seg_id, lt):
    keys = CAM[seg_id]
    z, dx = keys[0][1], keys[0][2]
    for (t0, z1, dx1, d) in keys[1:]:
        if lt < t0:
            break
        a = 1.0 if d <= 0 else ease((lt - t0) / d)
        z, dx = z + (z1 - z) * a, dx + (dx1 - dx) * a
    return z, dx


# ============================================================ big screen (behind the presenter)
SCREEN_TL = [(0.0, "flip"), (o("H", 55.0), "self"), (o("M", 15.85), "flip"), (o("A", 62.15), "self"),
             (o("T", 27.42), "logic"), (o("E", 97.70), "end")]
FOCUS_GRAPHICS = []          # (start, end) intervals when front graphics are on: screen racks out of focus


def screen_weights(t):
    """returns {key: weight} with 0.35 s crossfades"""
    w = {}
    for i, (t0, k) in enumerate(SCREEN_TL):
        t1 = SCREEN_TL[i + 1][0] if i + 1 < len(SCREEN_TL) else 1e9
        a = ease((t - t0) / 0.35) if i else 1.0
        b = 1 - ease((t - t1) / 0.35) if t > t1 else 1.0
        v = min(a, b) if t >= t0 else 0
        if v > 0:
            w[k] = w.get(k, 0) + v
    s = sum(w.values()) or 1
    return {k: v / s for k, v in w.items()}


def focus_at(t):
    """0 = screen sharp, 1 = screen defocused (graphics on top)"""
    v = 0.0
    for a, b in FOCUS_GRAPHICS:
        v = max(v, min(ease((t - a + 0.15) / 0.3), 1 - ease((t - b) / 0.3)))
    return v


# ============================================================ SFX bookkeeping
SFX = []   # (time, kind)


def sfx(t, kind):
    SFX.append((round(t, 3), kind))


# ============================================================ ASS graphics (front layer)
R.EVENTS = []
ev, rrect, text_w = R.ev, R.rrect, R.text_w
POP = R.POP
NAVY2 = R.NAVY2


def pill(start, end, cx, cy, text, sound=True, **kw):
    if sound:
        sfx(start, "pop")
    if "bg" not in kw:                       # lifted navy + turquoise edge reads on any backdrop
        kw.update(bg=NAVY2, border=TURQ, alpha="&H00&")
    return R.pill(start, end, cx, cy, text, **kw)


def panel(start, end, x0, y0, w, h, side="left", layer=8):
    """Split-screen glass panel that slides in from its side."""
    dx = -w - 60 if side == "left" else w + 60
    cx, cy = x0 + w // 2, y0 + h // 2
    ev(layer, start, end, f"{{\\an5\\move({cx + dx},{cy},{cx},{cy},0,320)\\bord4\\3c{TURQ}\\3a&H30&\\shad0"
                          f"\\1c{NAVY}\\1a&H22&\\fad(0,220)\\p1}}{rrect(w, h, 36)}")
    sfx(start, "whoosh_s")
    FOCUS_GRAPHICS.append((start, end))


def tag(start, end, cx, cy, text, col=TURQ):
    """Small label naming the logical connector."""
    return pill(start, end, cx, cy, text, size=38, fg=NAVY, bg=col, alpha="&H00&", pad_x=24, layer=14, sound=False)


def big_pop(start, end, cx, cy, text, size=110, col=YELL, layer=40):
    """Pop-up word: bounces in, slightly oversized, then settles."""
    ev(layer, start, end, f"{{\\an5\\pos({cx},{cy})\\fnHeebo Black\\fs{size}\\1c{col}\\bord7\\3c{NAVY}\\shad4\\4a&H60&"
                          f"\\fad(60,180)\\fscx40\\fscy40\\t(0,170,0.6,\\fscx112\\fscy112)\\t(170,300,\\fscx100\\fscy100)}}{text}")
    sfx(start, "pop_big")
    FOCUS_GRAPHICS.append((start, end))


def icon_student(start, end, x, y, layer=13, col=WHITE, scale=100, delay=0):
    head = "m 0 -46 b 13 -46 22 -37 22 -24 b 22 -11 13 -2 0 -2 b -13 -2 -22 -11 -22 -24 b -22 -37 -13 -46 0 -46"
    body = "m -34 44 b -34 18 -18 4 0 4 b 18 4 34 18 34 44 l -34 44"
    d = head + " " + body
    t0 = int(delay * 1000)
    ev(layer, start, end, f"{{\\an7\\pos({x},{y})\\bord0\\shad0\\1c{col}\\fscx{scale}\\fscy{scale}\\alpha&HFF&"
                          f"\\t({t0},{t0 + 160},\\alpha&H00&)\\fad(0,200)\\p1}}{d}")


def icon_laptop(start, end, x, y, layer=14):
    d = "m -30 -22 l 30 -22 l 30 14 l -30 14 l -30 -22 m -24 -16 l -24 8 l 24 8 l 24 -16 m -42 18 l 42 18 l 36 26 l -36 26"
    ev(layer, start, end, f"{{\\an7\\pos({x},{y})\\bord0\\shad0\\1c{YELL}\\fad(120,200){POP}\\p1}}{d}")


def icon_x(start, end, x, y, layer=14, col="&H5A5AFF&"):
    d = "m -16 -22 l 0 -6 l 16 -22 l 22 -16 l 6 0 l 22 16 l 16 22 l 0 6 l -16 22 l -22 16 l -6 0 l -22 -16"
    ev(layer, start, end, f"{{\\an7\\pos({x},{y})\\bord0\\shad0\\1c{col}\\fad(100,200){POP}\\p1}}{d}")


def icon_check(start, end, x, y, layer=14, col=TURQ):
    d = "m -26 0 l -17 -9 l -6 2 l 17 -21 l 26 -12 l -6 20"
    ev(layer, start, end, f"{{\\an7\\pos({x},{y})\\bord0\\shad0\\1c{col}\\fad(100,200){POP}\\p1}}{d}")


def big_icon(fn, start, end, x, y, scale=180, layer=13):
    """Draw one of the v1 icons scaled up (fn = R.icon_house / R.icon_board)."""
    n0 = len(R.EVENTS)
    fn(start, end, x, y, layer)
    e = R.EVENTS[n0]
    s = scale
    pop = (f"\\fscx{s * 0.7:.0f}\\fscy{s * 0.7:.0f}\\t(0,220,0.5,\\fscx{s * 1.04:.0f}\\fscy{s * 1.04:.0f})"
           f"\\t(220,320,\\fscx{s}\\fscy{s})")
    R.EVENTS[n0] = e.replace("\\p1}", pop + "\\p1}", 1)


def arrow_down(start, end, cx, y0, length=70, layer=12, col=YELL):
    d = f"m -6 0 l 6 0 l 6 {length - 22} l 18 {length - 22} l 0 {length} l -18 {length - 22} l -6 {length - 22}"
    ev(layer, start, end, f"{{\\an7\\pos({cx},{y0})\\bord0\\shad0\\1c{col}\\fad(0,200)"
                          f"\\clip({cx - 30},{y0},{cx + 30},{y0 + 1})\\t(0,280,\\clip({cx - 30},{y0},{cx + 30},{y0 + length + 4}))\\p1}}{d}")
    sfx(start, "click")


def text(start, end, cx, cy, s, size=46, col=WHITE, layer=13, font="Heebo ExtraBold", anim=POP, fade=(120, 200)):
    ev(layer, start, end, f"{{\\an5\\pos({cx},{cy})\\fn{font}\\fs{size}\\1c{col}\\bord0\\shad0\\fad({fade[0]},{fade[1]}){anim}}}{s}")


def graphics():
    # ---------------- H · hook
    a, b = 0.05, o("H", 51.05)
    ev(40, a, b, f"{{\\an5\\pos(540,250)\\bord0\\shad0\\1c{NAVY}\\1a&H08&\\fad(0,160)"
                 f"\\fscx30\\fscy30\\t(0,200,0.6,\\fscx106\\fscy106)\\t(200,320,\\fscx100\\fscy100)\\p1}}{rrect(900, 190, 95)}")
    ev(41, a, b, f"{{\\an5\\pos(540,254)\\fnHeebo Black\\fs108\\bord0\\shad0\\fad(0,160)"
                 f"\\fscx30\\fscy30\\t(0,200,0.6,\\fscx106\\fscy106)\\t(200,320,\\fscx100\\fscy100)}}"
                 f"למה {{\\1c{YELL}}}כיתה הפוכה{{\\1c{WHITE}}}?")
    sfx(a, "pop_big"); sfx(a, "whoosh")
    FOCUS_GRAPHICS.append((a, b))
    big_pop(o("H", 50.20), o("H", 51.05), 540, 430, "להקשות?", size=86, col=WHITE, layer=42)

    # ---------------- H · contrast (split screen): "לא כדי להקשות ... אלא כדי להכין"
    a, b = o("H", 51.15), o("H", 55.05)
    panel(a, b, 40, 300, 440, 820, side="left")
    tag(a + 0.15, b, 260, 360, "ניגוד")
    pill(a + 0.25, b, 260, 500, "להקשות עליכם", size=48, layer=12)
    icon_x(a + 0.35, b, 260, 575)
    R.strike(a + 0.45, b, 260, 500, 330)
    sfx(a + 0.45, "click")
    big_pop(o("H", 51.24), b, 260, 700, "אלא", size=104, layer=15)
    pill(o("H", 51.80), b, 260, 900, "להכין אתכם", size=54, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", layer=12)
    icon_check(o("H", 51.95), b, 260, 985)

    # ---------------- H · cause -> effect (zoom-out reveal)
    a, b = o("H", 55.15), o("H", 57.45)
    tag(a, b, 540, 160, "סיבה ותוצאה · כדי ש...")
    pill(a + 0.05, b, 810, 280, "כיתה הפוכה", size=54, layer=12)
    R.arrow_left(a + 0.3, b, 540, 280, length=120); sfx(a + 0.3, "click")
    pill(a + 0.45, b, 270, 280, "לומדים עצמאיים", size=52, fg=NAVY, bg=YELL, alpha="&H00&", weight="900Black", layer=12)
    text(o("H", 56.24), b, 270, 375, "בלמידה מקוונת", size=44, col=TURQ)
    FOCUS_GRAPHICS.append((a, b))

    # ---------------- H · addition (split screen, stacked)
    a, b = o("H", 57.55), o("H", 61.90)
    panel(a, b, 600, 300, 440, 860, side="right")
    tag(a + 0.15, b, 820, 360, "הוספה · וגם")
    pill(o("H", 58.10), b, 820, 500, "אוניברסיטאות", size=50, layer=12)
    big_pop(o("H", 59.0), b, 820, 600, "+", size=96, layer=15)
    pill(o("H", 59.10), b, 820, 700, "מכללות", size=50, layer=12)
    arrow_down(o("H", 60.35), b, 820, 760, length=80)
    pill(o("H", 60.60), b, 820, 900, "קורסים מקוונים", size=48, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", layer=12)

    # ---------------- M · the flipped-classroom model (split, animated scenes)
    b = o("M", 27.40)
    pill(o("M", 15.95), o("M", 18.25), 540, 170, "מודל כיתה הפוכה", size=46, fg=NAVY, bg=YELL, alpha="&H00&", weight="900Black")
    FOCUS_GRAPHICS.append((o("M", 15.95), o("M", 18.25)))
    a = o("M", 18.30)
    panel(a, b, 600, 260, 440, 960, side="right")
    # scene 1: at home
    s1e = o("M", 19.95)
    tag(a + 0.1, s1e, 820, 330, "שלב 1 · בבית")
    big_icon(R.icon_house, a + 0.2, s1e, 800, 450)
    icon_student(a + 0.3, s1e, 790, 640, scale=150, delay=0.1)
    icon_laptop(a + 0.45, s1e, 880, 690)
    text(a + 0.55, s1e, 820, 830, "לומדים את החומר", size=52)
    text(a + 0.65, s1e, 820, 905, "בקצב שלכם", size=44, col=TURQ)
    # scene 2: in class
    a2 = o("M", 20.0)
    tag(a2, b, 820, 330, "שלב 2 · בכיתה")
    sfx(a2, "whoosh_s")
    big_icon(R.icon_board, a2 + 0.1, b, 800, 440)
    for i, x in enumerate((725, 820, 915)):
        icon_student(a2 + 0.2, b, x, 580, scale=105, delay=0.12 * i)
    text(o("M", 23.05), b, 820, 680, "תרגול וחזרה", size=54, col=YELL)
    sfx(o("M", 23.05), "pop")
    # quiz: 10 dots fill in
    q0 = o("M", 24.80)
    text(q0, b, 820, 790, "מבדק קצר", size=46)
    sfx(q0, "pop")
    for i in range(10):
        x = 820 + (i - 4.5) * 38
        dot = "m 0 -13 b 7 -13 13 -7 13 0 b 13 7 7 13 0 13 b -7 13 -13 7 -13 0 b -13 -7 -7 -13 0 -13"
        t1 = int((0.25 + 0.12 * i) * 1000)
        ev(14, q0, b, f"{{\\an7\\pos({x:.0f},870)\\bord2\\3c{TURQ}\\shad0\\1c{NAVY}\\fad(120,200)"
                      f"\\t({t1},{t1 + 80},\\1c{YELL}\\fscx120\\fscy120)\\t({t1 + 80},{t1 + 160},\\fscx100\\fscy100)\\p1}}{dot}")
        if i % 3 == 0:
            sfx(q0 + t1 / 1000, "tick")
    text(q0 + 1.5, b, 820, 940, "10 שאלות", size=52, col=YELL, font="Heebo Black")

    # ---------------- A · the aspiration
    a, b = o("A", 65.85), o("A", 69.45)
    pill(a, b, 540, 190, "השאיפה שלי", size=40, fg=NAVY, bg=TURQ, alpha="&H00&")
    big_pop(o("A", 66.70), b, 540, 320, "למידה עצמאית", size=96)
    # sequence (split)
    a, b = o("A", 69.55), o("A", 78.50)
    panel(a, b, 40, 300, 440, 900, side="left")
    tag(a + 0.15, b, 260, 360, "רצף הלמידה")
    pill(o("A", 70.95), b, 260, 500, "לומדים בכוחות עצמכם", size=38, layer=12)
    arrow_down(o("A", 72.4), b, 260, 545, length=80)
    pill(o("A", 72.60), b, 260, 680, "בכיתה: תרגול ומבדק", size=40, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", layer=12)
    big_pop(o("A", 76.75), b, 260, 830, "בלי", size=80, col=WHITE, layer=15)
    pill(o("A", 77.10), b, 260, 940, "למידה של החומר", size=44, layer=12)
    R.strike(o("A", 77.55), b, 260, 940, 300); sfx(o("A", 77.55), "click")

    # ---------------- T · concept map of logical connectors (held into C)
    b = o("C", 81.40)
    pill(o("T", 27.50), o("T", 29.70), 540, 175, "הנושא הבא", size=44, fg=NAVY, bg=TURQ, alpha="&H00&")
    FOCUS_GRAPHICS.append((o("T", 27.50), b))
    big_pop(o("T", 29.80), b, 540, 250, "קשרים לוגיים", size=100)
    nodes = [(850, "לכן", "סיבה ותוצאה"), (540, "אבל", "ניגוד"), (230, "וגם", "הוספה")]
    for i, (sx, word, kind) in enumerate(nodes):
        st = o("T", 30.10) + 0.16 * i
        R.line(st, b, 540, 320, sx, 420, width=7)
        sfx(st, "click")
        ev(12, st + 0.1, b, f"{{\\an5\\pos({sx},470)\\bord4\\3c{TURQ}\\shad0\\1c{NAVY}\\1a&H10&\\fad(120,200){POP}\\p1}}"
                            f"{rrect(250, 130, 30)}")
        text(st + 0.1, b, sx, 448, word, size=58, col=YELL, font="Heebo Black")
        text(st + 0.1, b, sx, 503, kind, size=30, col=WHITE)
        sfx(st + 0.1, "pop")

    # ---------------- C · no excuses (stair punches)
    b = o("C", 85.55)
    big_pop(o("C", 81.50), b, 540, 175, "אין דבר כזה", size=84)
    for i, (s0, s1, label) in enumerate([(82.36, 83.0, "לא ידעתי"), (83.30, 84.1, "לא שמעתי"), (84.52, 85.4, "לא עשיתי")]):
        cx = (845, 540, 235)[i]
        w = pill(o("C", s0), b, cx, 300, label, size=46)
        R.strike(o("C", s1) - 0.05, b, cx, 300, w - 30)
        sfx(o("C", s1) - 0.05, "click")
    a, b = o("C", 85.68), o("C", 87.72)
    w = pill(a, b, 540, 260, "אני זמין לשאלות", size=60, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", pad_x=44)
    icon_check(a + 0.15, b, 540 + w // 2 + 30, 200, col=YELL)
    FOCUS_GRAPHICS.append((a, b))

    # ---------------- E · closing pop
    big_pop(o("E", 98.95), o("E", 99.95), 540, 300, "מהנה!", size=120, col=TURQ)

    # ---------------- end card
    a, b = VOICE_END + 0.25, TOTAL
    ev(50, a, b, f"{{\\an5\\pos(540,760)\\bord0\\shad0\\1c{NAVY}\\1a&H18&\\fad(200,0)\\fscx60\\fscy60"
                 f"\\t(0,260,0.6,\\fscx100\\fscy100)\\p1}}{rrect(960, 560, 60)}")
    ev(51, a + 0.05, b, f"{{\\an5\\pos(540,630)\\fnHeebo Black\\fs140\\1c{YELL}\\bord0\\shad0\\fad(200,0)"
                        f"\\fscx70\\fscy70\\t(0,280,0.6,\\fscx100\\fscy100)}}כיתה הפוכה")
    ev(51, a + 0.35, b, f"{{\\an5\\pos(540,790)\\fnHeebo Black\\fs66\\1c{WHITE}\\bord0\\shad0\\fad(200,0)}}חושבים, מקשרים")
    ev(51, a + 0.6, b, f"{{\\an5\\pos(540,880)\\fnHeebo Black\\fs66\\1c{TURQ}\\bord0\\shad0\\fad(200,0)}}ולומדים אחרת!")
    for i, x in enumerate((380, 540, 700)):
        ev(52, a + 0.8 + 0.12 * i, b, f"{{\\an5\\pos({x},975)\\bord0\\shad0\\1c{YELL if i == 1 else TURQ}\\fad(120,0){POP}\\p1}}"
                                      "m 0 -14 b 8 -14 14 -8 14 0 b 14 8 8 14 0 14 b -8 14 -14 8 -14 0 b -14 -8 -8 -14 0 -14")
        sfx(a + 0.8 + 0.12 * i, "tick")
    R.line(a + 0.85, b, 700, 975, 380, 975, width=5, col=WHITE, grow=400, layer=51, alpha="&H40&")
    sfx(a, "pop_big")


# ============================================================ kinetic captions
KEY_COLS = {}


def kinetic_captions(words):
    chunks = R.build_captions(words)
    for c in chunks:
        toks = c["words"]
        cols = [None] * len(toks)
        for phrase, col in R.HIGHLIGHT:
            n = len(phrase)
            for i in range(len(toks) - n + 1):
                if [R.clean(x["w"]) for x in toks[i:i + n]] == phrase:
                    for k in range(n):
                        cols[i + k] = col
        txt = " ".join(w["w"] for w in toks)
        size = min(80, int(80 * 840 / max(text_w(txt, 80), 1)))
        st = c["start"]
        parts = []
        for w, col in zip(toks, cols):
            # word appears (fade + scale bounce) when it is spoken
            wt = max(int((o(c["seg"], w["s"]) - st) * 1000), 0)
            base = col or WHITE
            if col:   # keyword: bigger bounce
                anim = (f"\\1c{base}\\alpha&HB0&\\fscx100\\fscy100\\t({wt},{wt + 90},\\alpha&H00&\\fscx122\\fscy122)"
                        f"\\t({wt + 90},{wt + 230},\\fscx100\\fscy100)")
            else:
                anim = (f"\\1c{base}\\alpha&HB0&\\t({wt},{wt + 90},\\alpha&H00&\\fscx108\\fscy108)"
                        f"\\t({wt + 90},{wt + 200},\\fscx100\\fscy100)")
            parts.append(f"{{{anim}}}{w['w']}")
        ev(60, st, c["end"], rf"{{\an2\pos(540,1405)\fs{size}\fad(60,40)\move(540,1430,540,1405,0,140)}}" + " ".join(parts),
           style="Cap")
    return chunks


def write_ass(path):
    head = open(os.path.join(R.OUT, "reel_overlays.ass"), encoding="utf-8").read().split("[Events]")[0]
    head = head.replace("Style: Cap,Heebo Black,78,&H00FFFFFF,&H00FFFFFF,&H003A1F0B,&H96000000,0,0,0,0,100,100,0,0,1,6,3,",
                        "Style: Cap,Heebo Black,80,&H00FFFFFF,&H00FFFFFF,&H003A1F0B,&H80000000,0,0,0,0,100,100,0,0,1,7,4,")
    with open(path, "w", encoding="utf-8") as f:
        f.write(head + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        f.write("\n".join(R.EVENTS) + "\n")


# ============================================================ compositing
def load_studio():
    studio.make_studio(ASSETS)
    base = cv2.imread(os.path.join(ASSETS, "studio_base.png")).astype(np.float32)
    plates = {}
    for k in ("flip", "logic", "self", "end"):
        s = cv2.imread(os.path.join(ASSETS, f"screen_{k}.png"), cv2.IMREAD_UNCHANGED).astype(np.float32)
        a = s[..., 3:4] / 255.0
        sharp = base * (1 - a) + s[..., :3] * a
        soft = cv2.GaussianBlur(base * (1 - 0.22 * a) + s[..., :3] * 0.22 * a, (0, 0), 12)
        plates[k] = (sharp, soft)
    return plates


def bg_frame(plates, t, z, dx):
    w = screen_weights(t)
    f = focus_at(t)
    canvas = None
    for k, wk in w.items():
        sharp, soft = plates[k]
        p = sharp * (1 - f) + soft * f if 0 < f < 1 else (soft if f >= 1 else sharp)
        canvas = p * wk if canvas is None else canvas + p * wk
    # parallax: background moves/zooms 30% of the presenter's move
    bz = 1 + (z - 1) * 0.3
    bdx = dx * 0.3
    s = bz
    cxs, cys = studio.BG_W / 2, studio.BG_H / 2 - 40
    M = np.float32([[s, 0, W / 2 - cxs * s + bdx], [0, s, H / 2 - cys * s]])
    return cv2.warpAffine(canvas, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


EDGE_FEATHER = None


def subject_layer(fr, alpha2x, z, dx, tcx, tey, tfw):
    s = W / SW * z
    # presenter's eyes on the eye line, but never lift the body off the bottom edge
    ox = W / 2 + dx - tcx * s
    oy = EYE * H - tey * s
    oy = max(oy, H + 4 - SH * s)
    M = np.float32([[s, 0, ox], [0, s, oy]])
    subj = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    M2 = np.float32([[s / 2, 0, ox], [0, s / 2, oy]])
    a = cv2.warpAffine(alpha2x, M2, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    fx, fy = W / 2 + dx, tey * s + oy
    return subj, a, fx, fy, tfw * s


def relight(subj, a, bg, fx, fy, fw):
    # softbox: broad, soft key on the face
    gx = np.exp(-0.5 * ((np.arange(W) - fx - 0.15 * fw) / (fw * 1.4)) ** 2)
    gy = np.exp(-0.5 * ((np.arange(H) - fy) / (fw * 1.9)) ** 2)
    key = (1.0 + 0.12 * np.outer(gy, gx))[..., None].astype(np.float32)
    subj = subj * key
    # gentle subject-only sharpening (eyes / hair detail)
    blur = cv2.GaussianBlur(subj, (0, 0), 1.3)
    subj = subj + 0.45 * (subj - blur)
    # rim light from the alpha edge: turquoise from the right, warm from the left
    a3 = a[..., None]
    inner = cv2.erode(a, np.ones((9, 9), np.uint8))
    edge = cv2.GaussianBlur(np.clip(a - inner, 0, 1), (0, 0), 3)[..., None]
    side = np.clip((np.arange(W) - fx) / 300, -1, 1)[None, :, None]
    rim = np.where(side > 0, np.array([214, 230, 46], np.float32) * side, np.array([90, 170, 255], np.float32) * -side)
    subj = subj + edge * rim * 0.55
    # light wrap: let the studio light spill over the outline
    bgb = cv2.GaussianBlur(bg, (0, 0), 12)
    subj = subj * (1 - 0.30 * edge) + bgb * 0.30 * edge
    return np.clip(subj, 0, 255)


def composite(bg, subj, a):
    # soft contact shadow on the wall behind
    sh = cv2.GaussianBlur(np.roll(np.roll(a, 26, axis=1), 18, axis=0), (0, 0), 22)[..., None]
    bg = bg * (1 - 0.38 * sh)
    a3 = a[..., None]
    return bg * (1 - a3) + subj * a3


def motion_blur_h(img, length):
    length = int(abs(length))
    if length < 3:
        return img
    k = np.ones((1, length), np.float32) / length
    return cv2.filter2D(img, -1, k)


def transition(img, kind, phase, i, n):
    """phase 'out' (last n frames of a segment) or 'in' (first n frames)."""
    if kind in ("whip_l", "whip_r"):
        sgn = -1 if kind == "whip_l" else 1
        p = (i + 1) / n if phase == "out" else 1 - i / n
        shift = sgn * (W * 0.55) * (p ** 2.2) * (1 if phase == "out" else -1)
        vel = W * 0.55 * 2.2 * p ** 1.2 / n
        M = np.float32([[1, 0, shift], [0, 1, 0]])
        img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        return motion_blur_h(img, min(vel * 1.4, 160))
    if kind == "zoomblur":
        p = (i + 1) / n if phase == "out" else 1 - i / n
        acc = np.zeros_like(img)
        for k in range(5):
            s = 1 + 0.18 * p * (k / 4)
            M = cv2.getRotationMatrix2D((W / 2, H * 0.42), 0, s)
            acc += cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        return acc / 5
    return img


def render(tracks):
    plates = load_studio()
    silent = os.path.join(TMP, "v2_video.mkv")
    ass = os.path.join(OUT, "reel_v2_overlays.ass").replace(":", r"\:")
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-vf", f"vignette=angle=0.38,ass={ass}:fontsdir={R.FONTS}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", silent],
        stdin=subprocess.PIPE)
    prev_kind = None
    last = None
    for si, seg in enumerate(SEGMENTS):
        sid = seg["id"]
        td = tracks[sid]
        n = seg["nf"]
        prev_a = None
        prev_z = None
        for i, fr in enumerate(R.read_segment(seg)):
            t = seg["out_in"] + i / FPS
            lt = i / FPS
            z, dx = cam_at(sid, lt)
            a2 = cv2.imread(os.path.join(MATTE, sid, f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            # feather the source's side borders (body cut by the original frame)
            if EDGE_FEATHER is None:
                globals()["EDGE_FEATHER"] = np.clip(np.minimum(np.arange(2 * SW), 2 * SW - 1 - np.arange(2 * SW)) / 24, 0, 1)[None, :].astype(np.float32)
            a2 = a2 * EDGE_FEATHER
            # temporal de-flicker: blend small changes only (fast motion stays crisp)
            if prev_a is not None:
                dlt = np.abs(a2 - prev_a)
                a2 = np.where(dlt < 0.2, 0.6 * a2 + 0.4 * prev_a, a2)
            prev_a = a2
            # motion blur during fast punches: average sub-steps of the zoom
            zs = [z] if prev_z is None or abs(z - prev_z) < 0.015 else list(np.linspace(prev_z, z, 3))
            prev_z = z
            bg = bg_frame(plates, t, z, dx)
            acc = None
            for zz in zs:
                subj, a, fx, fy, fw = subject_layer(fr, a2, zz, dx, td[0][i], td[1][i], td[2][i])
                subj = relight(subj, a, bg, fx, fy, fw)
                c = composite(bg, subj, a)
                acc = c if acc is None else acc + c
            img = acc / len(zs)
            if i >= n - TRANS_FR and TRANS[sid] not in ("cut", "pull"):
                img = transition(img, TRANS[sid], "out", i - (n - TRANS_FR), TRANS_FR)
            if i < TRANS_FR and prev_kind not in (None, "cut", "pull"):
                img = transition(img, prev_kind, "in", i, TRANS_FR)
            last = np.clip(img, 0, 255).astype(np.uint8)
            enc.stdin.write(last.tobytes())
        prev_kind = TRANS[sid]
        print(f"  composited {sid} ({n} frames)", flush=True)
    # end card: pull back into the studio with depth blur, then navy title plate
    nf = R.frames(END_CARD)
    lf = last.astype(np.float32)
    for i in range(nf):
        p = ease(i / (0.6 * FPS))
        s = 1 - 0.12 * p
        M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, s)
        img = cv2.warpAffine(lf, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        if p > 0:
            img = cv2.GaussianBlur(img, (0, 0), 0.1 + 14 * p)
        navy = np.array([42, 22, 8], np.float32)
        img = img * (1 - 0.55 * p) + navy * 0.55 * p
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    return silent


# ============================================================ audio
SR = 48000


def tone_env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(t / max(attack, 1e-4), 1) * np.exp(-t / decay)


def make_sfx():
    rng = np.random.default_rng(3)
    lib = {}
    # whoosh: band-passed noise with a rising-then-falling sweep
    n = int(0.45 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    env = np.sin(np.pi * np.clip(t / 0.45, 0, 1)) ** 2
    sweep = np.zeros(n); y = 0.0
    fc = 300 + 3500 * np.sin(np.pi * t / 0.45)
    for k in range(n):  # one-pole low-pass with moving cutoff
        a = 1 - math.exp(-2 * math.pi * fc[k] / SR)
        y += a * (noise[k] - y); sweep[k] = y
    lib["whoosh"] = 0.55 * sweep * env / (np.abs(sweep).max() + 1e-9)
    lib["whoosh_s"] = lib["whoosh"][::2] * 0.6         # shorter, lighter
    # pop: short sine with a pitch drop
    n = int(0.09 * SR); t = np.arange(n) / SR
    f = 900 * np.exp(-t * 18) + 380
    lib["pop"] = 0.42 * np.sin(2 * np.pi * np.cumsum(f) / SR) * tone_env(n, 0.002, 0.03)
    n = int(0.16 * SR); t = np.arange(n) / SR
    f = 700 * np.exp(-t * 14) + 180
    lib["pop_big"] = 0.55 * np.sin(2 * np.pi * np.cumsum(f) / SR) * tone_env(n, 0.002, 0.05)
    # click / tick: filtered transient
    n = int(0.03 * SR)
    lib["click"] = 0.35 * rng.standard_normal(n) * tone_env(n, 0.0005, 0.004)
    lib["tick"] = 0.30 * np.sin(2 * np.pi * 2400 * np.arange(n) / SR) * tone_env(n, 0.0005, 0.006)
    return lib


def write_wav(path, st):
    st = np.clip(st, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def render_sfx(path):
    lib = make_sfx()
    out = np.zeros((int(TOTAL * SR) + SR, 2))
    # add camera-driven whooshes (transitions and split moves are already in SFX)
    events = list(SFX)
    for seg in SEGMENTS:
        if TRANS[seg["id"]] in ("whip_l", "whip_r", "zoomblur"):
            events.append((seg["out_in"] + seg["dur"] - TRANS_FR / FPS, "whoosh"))
    events.append((VOICE_END, "whoosh"))
    events.sort()
    last_t = {}
    for t, k in events:
        if t - last_t.get(k, -9) < 0.12:         # never stack the same sound
            continue
        last_t[k] = t
        s = lib[k]
        i = int(t * SR)
        pan = 0.5 + 0.15 * math.sin(t * 3.1)
        out[i:i + len(s), 0] += s * (1 - pan) * 1.4
        out[i:i + len(s), 1] += s * pan * 1.4
    write_wav(path, out[:int(TOTAL * SR)])


def make_music(path):
    """Original, gently rhythmic bed (100 BPM), generated here — royalty free."""
    n = int(TOTAL * SR); t = np.arange(n) / SR
    beat = 60 / 100
    L = np.zeros(n); Rr = np.zeros(n)
    chords = [[57, 60, 64, 71], [53, 57, 60, 64], [48, 55, 60, 64], [55, 59, 62, 67]]
    bar = 4 * beat
    rng = np.random.default_rng(11)
    for b in range(int(TOTAL / bar) + 1):
        notes = chords[b % 4]; t0 = b * bar
        m = (t >= t0) & (t < t0 + bar + 1.0); tt = t[m] - t0
        env = np.minimum(tt / 0.6, 1) * np.where(tt > bar, np.exp(-(tt - bar) * 3), 1)
        for nn in notes:
            f = 440 * 2 ** ((nn - 69) / 12)
            L[m] += 0.5 * env * np.sin(2 * np.pi * f * 0.997 * tt) / 4
            Rr[m] += 0.5 * env * np.sin(2 * np.pi * f * 1.003 * tt) / 4
        for k in range(8):                       # plucked 8th-note arpeggio
            nn = notes[(k * 3) % 4] + 12; f = 440 * 2 ** ((nn - 69) / 12)
            ts0 = t0 + k * beat / 2
            mm = (t >= ts0) & (t < ts0 + 0.5); tt = t[mm] - ts0
            p = 0.16 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9) * np.minimum(tt / 0.004, 1)
            L[mm] += p * (0.65 - 0.3 * (k % 2)); Rr[mm] += p * (0.35 + 0.3 * (k % 2))
        for k in range(4):                       # soft kick on every beat, hat on off-beats
            ts0 = t0 + k * beat
            mm = (t >= ts0) & (t < ts0 + 0.3); tt = t[mm] - ts0
            kick = 0.5 * np.sin(2 * np.pi * (50 + 70 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14)
            L[mm] += kick; Rr[mm] += kick
            hs = ts0 + beat / 2
            mm = (t >= hs) & (t < hs + 0.05); tt = t[mm] - hs
            hat = 0.06 * rng.standard_normal(mm.sum()) * np.exp(-tt * 90)
            L[mm] += hat * 0.8; Rr[mm] += hat
    st = np.stack([L, Rr], 1)
    fade = np.minimum(1, t / 0.8) * np.minimum(1, (TOTAL - t) / 1.2)
    st *= fade[:, None]
    st /= np.abs(st).max() + 1e-9
    write_wav(path, st * 0.6)


def render_audio():
    os.makedirs(TMP, exist_ok=True)
    voice = os.path.join(R.TMP, "voice.wav")        # cleaned + normalised voice from the v1 build
    if not os.path.exists(voice):
        R.render_audio()
    music = os.path.join(TMP, "music_v2.wav"); make_music(music)
    fx = os.path.join(TMP, "sfx.wav"); render_sfx(fx)
    mix = os.path.join(TMP, "mix_v2.wav")
    pre = os.path.join(TMP, "mix_v2_pre.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", music, "-i", fx, "-filter_complex",
                    "[1:a]volume=-17dB[m];[0:a]asplit=2[v][sc];"
                    "[m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=30:release=400[md];"
                    "[2:a]volume=-11dB[fx];"
                    "[v][md][fx]amix=inputs=3:normalize=0",
                    "-ar", "48000", "-t", f"{TOTAL:.4f}", pre], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(r[r.rfind("{"):r.rfind("}") + 1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
                    f"loudnorm=I=-14:TP=-1.5:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                    f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
                    "-ar", "48000", mix], check=True)
    return mix


# ============================================================ cover
def render_cover(tracks, plates):
    seg = SEG["C"]; i = R.frames(85.9 - seg["src_in"])
    for k, fr in enumerate(R.read_segment(seg)):
        if k == i:
            break
    a2 = cv2.imread(os.path.join(MATTE, "C", f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    td = tracks["C"]
    z, dx = 1.12, 0
    old = globals()["SCREEN_TL"]
    globals()["SCREEN_TL"] = [(0, "logic")]
    bg = bg_frame(plates, 0, z, dx)
    globals()["SCREEN_TL"] = old
    subj, a, fx, fy, fw = subject_layer(fr, a2, z, dx, td[0][i], td[1][i] + 40, td[2][i])
    img = composite(bg, relight(subj, a, bg, fx, fy, fw), a)
    g = np.clip((np.arange(H) - 1050) / 450, 0, 1)[:, None, None] * 0.85
    img = img * (1 - g) + np.array([58, 31, 11], np.float32) * g
    raw = os.path.join(TMP, "cover_v2_bg.png"); cv2.imwrite(raw, np.clip(img, 0, 255).astype(np.uint8))
    cass = os.path.join(TMP, "cover_v2.ass")
    head = open(os.path.join(OUT, "reel_v2_overlays.ass"), encoding="utf-8").read().split("[Events]")[0]
    dot = "m 0 -16 b 9 -16 16 -9 16 0 b 16 9 9 16 0 16 b -9 16 -16 9 -16 0 b -16 -9 -9 -16 0 -16"
    lines = [
        f"{{\\an5\\pos(540,1300)\\fnHeebo Black\\fs150\\1c{YELL}\\bord7\\3c{NAVY}\\shad5\\4a&H60&}}כיתה הפוכה",
        f"{{\\an5\\pos(540,1395)\\bord0\\shad0\\1c{TURQ}\\p1}}m -150 0 l 150 0 l 150 8 l -150 8",
        f"{{\\an5\\pos(540,1480)\\fnHeebo Black\\fs100\\1c{WHITE}\\bord5\\3c{NAVY}\\shad0}}לומדים קשרים לוגיים",
    ] + [f"{{\\an5\\pos({x},1590)\\bord0\\shad0\\1c{YELL if k == 1 else TURQ}\\p1}}{dot}" for k, x in enumerate((440, 540, 640))]
    with open(cass, "w", encoding="utf-8") as f:
        f.write(head + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for k, l in enumerate(lines):
            f.write(f"Dialogue: {k},0:00:00.00,0:00:05.00,G,,0,0,0,,{l}\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf",
                    f"ass={cass.replace(':', chr(92) + ':')}:fontsdir={R.FONTS}", "-q:v", "2",
                    os.path.join(OUT, "cover_v2.jpg")], check=True)


def main():
    os.makedirs(TMP, exist_ok=True)
    words = json.load(open(os.path.join(HERE, "..", "transcript_words.json"), encoding="utf-8"))["words"]
    graphics()
    chunks = kinetic_captions(words)
    write_ass(os.path.join(OUT, "reel_v2_overlays.ass"))
    with open(os.path.join(OUT, "reel_v2.srt"), "w", encoding="utf-8") as f:
        for k, c in enumerate(chunks, 1):
            f.write(f"{k}\n{R.srt_time(c['start'])} --> {R.srt_time(c['end'])}\n{' '.join(w['w'] for w in c['words'])}\n\n")
    json.dump(sorted(SFX), open(os.path.join(OUT, "sfx_cues.json"), "w"), indent=0)
    print(f"timeline {TOTAL:.2f}s · {len(R.EVENTS)} ASS events · {len(SFX)} sfx cues", flush=True)
    if "--ass-only" in sys.argv:
        return
    if "--test" in sys.argv:      # composite a few frames of one segment to PNG (no ASS)
        sid = sys.argv[sys.argv.index("--test") + 1]
        idx = [int(v) for v in sys.argv[sys.argv.index("--test") + 2].split(",")]
        seg = SEG[sid]; td = R.track(seg)[0]; plates = load_studio()
        for i, fr in enumerate(R.read_segment(seg)):
            if i not in idx:
                continue
            z, dx = cam_at(sid, i / FPS)
            a2 = cv2.imread(os.path.join(MATTE, sid, f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            bg = bg_frame(plates, seg["out_in"] + i / FPS, z, dx)
            subj, a, fx, fy, fw = subject_layer(fr, a2, z, dx, td[0][i], td[1][i], td[2][i])
            cv2.imwrite(os.path.join(TMP, f"test_{sid}_{i}.png"), np.clip(composite(bg, relight(subj, a, bg, fx, fy, fw), a), 0, 255).astype(np.uint8))
        return
    tracks = {s["id"]: R.track(s)[0] for s in SEGMENTS}
    mix = render_audio()
    if "--audio-only" in sys.argv:
        video = os.path.join(TMP, "v2_video.mkv")
    else:
        video = render(tracks)
    render_cover(tracks, load_studio())
    final = os.path.join(OUT, "reel_kita_hafucha_v2.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", mix, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("done:", final)


if __name__ == "__main__":
    main()
