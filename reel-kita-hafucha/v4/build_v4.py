#!/usr/bin/env python3
"""
build_v4.py — "כיתה הפוכה – לומדים קשרים לוגיים", v4 (premium).

What v4 adds on top of v3 (whose graphics helpers it reuses):
  • Real-ESRGAN detail on the face/hair/eyes (sr_cache.py), blended 55% to keep natural skin texture
  • edge colour decontamination of the matte (no light fringe around the hair)
  • 2.5D studio (layers.py): wall/screen, desk, floor, ceiling move at different depths
  • virtual camera: opening dolly with roll, subtle handheld drift throughout
  • giant "hero" words BEHIND the presenter (hero.py)
  • graphics rendered as their own RGBA layer: neon glow, soft shadow, light spill onto the presenter
  • word-box kinetic captions (captions_v4.py), burned last so they stay crisp
  • finishing (finish.py): split-tone grade, bloom/halation, film grain, chromatic aberration and
    light leaks on transitions, floating dust in the studio light
  • new score (100 BPM, arc with breakdown and build) and SFX with reverb tails, shimmer, sub impacts

Usage: python3 build_v4.py SOURCE.mp4 MATTE_DIR STUDIO_IMAGE SR_CACHE [--ass-only] [--test SEG i,j] [--audio-only]
"""
import json, math, os, subprocess, sys, wave
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "v3"))
sys.path.insert(0, HERE)
SR_CACHE = sys.argv[4]
import build_v3 as B3          # noqa: E402  (sets palette, segments, graphics helpers)
import build_reel as R         # noqa: E402
import layers as LY            # noqa: E402
import hero as HR              # noqa: E402
import finish as FX            # noqa: E402
import captions_v4 as CAPS     # noqa: E402

SRC, MATTE, STUDIO_IMG = B3.SRC, B3.MATTE, B3.STUDIO_IMG
OUT = os.path.join(HERE, "..", "output_v4")
TMP = os.path.join(OUT, "_tmp")
ASSETS = os.path.join(TMP, "layers")
W, H, FPS = R.W, R.H, R.FPS
SW, SH = R.SW, R.SH
o, SEG, SEGMENTS, L = R.o, R.SEG, R.SEGMENTS, B3.L
NAVY, TURQ, YELL, WHITE = R.NAVY, R.TURQ, R.YELL, R.WHITE
NAVY_BGR = B3.NAVY_BGR
EYE = B3.EYE
END_CARD = 2.6
VOICE_END = R.VOICE_END
TOTAL = VOICE_END + END_CARD
NFRAMES = R.frames(TOTAL)
ease = B3.ease
ev, rrect, text_w, sfx = R.ev, R.rrect, R.text_w, B3.sfx

# ============================================================ camera
# (local_t, zoom, dx, ease_seconds) per segment; v4 opens with a fast dolly from a wide studio shot
B3.CAM["H"] = [(0, 0.96, 0, 0), (0.04, 1.40, 0, 0.50), (0.6, 1.40, 0, 0), (3.5, 1.46, 0, 2.9),
               (L("H", 50.22), 1.58, 0, 0.12),
               (L("H", 51.15), 1.00, 230, 0.32),
               (L("H", 55.10), 0.92, 0, 0.45),
               (L("H", 57.50), 1.04, -225, 0.32),
               (L("H", 60.60), 1.12, -225, 0.12)]
cam_at = B3.cam_at
TRANS, TRANS_FR = B3.TRANS, B3.TRANS_FR
_ph = np.random.default_rng(21).uniform(0, 2 * np.pi, 8)


def cam_global(t):
    """handheld drift + opening roll: (roll_deg, scale, tx, ty)"""
    tx = 5.0 * math.sin(2 * math.pi * 0.13 * t + _ph[0]) + 2.5 * math.sin(2 * math.pi * 0.31 * t + _ph[1])
    ty = 4.0 * math.sin(2 * math.pi * 0.11 * t + _ph[2]) + 2.0 * math.sin(2 * math.pi * 0.27 * t + _ph[3])
    roll = 0.22 * math.sin(2 * math.pi * 0.07 * t + _ph[4])
    k = 1 + 0.004 * math.sin(2 * math.pi * 0.05 * t + _ph[5])
    if t < 0.6:                                   # opening: camera rolls level as it rushes in
        roll += -3.2 * (1 - ease(t / 0.55))
    return roll, k, tx, ty


def cam_matrix(t, depth):
    """3x3 camera matrix for a layer at a given depth (1 = presenter, 0.25 = back wall)"""
    roll, k, tx, ty = cam_global(t)
    c, s = math.cos(math.radians(roll)) * k, math.sin(math.radians(roll)) * k
    px, py = 540, 860
    return np.array([[c, -s, px - c * px + s * py + tx * (0.4 + 0.6 * depth)],
                     [s, c, py - s * px - c * py + ty * (0.4 + 0.6 * depth)],
                     [0, 0, 1]], np.float64)


# ============================================================ big screen + focus
B3.SCREEN_TL = [(0.0, "flip"), (o("H", 55.0), "self"), (o("M", 15.85), "flip"), (o("A", 62.15), "self"),
                (o("A", 65.6), "flip"), (o("T", 27.42), "flip"), (o("C", 81.40), "logic"), (o("E", 97.70), "end")]
FOCUS = B3.FOCUS_GRAPHICS

# ============================================================ hero words (behind the presenter)
HEROES = []


def hero(lines, t0, t1, cy, size, kind="yellow", max_w=1000):
    cols = {"yellow": ((255, 236, 140), (255, 196, 40), (0, 217, 232)),
            "cyan": ((170, 252, 255), (0, 205, 232), (255, 212, 71))}[kind]
    HEROES.append(HR.Hero(lines, t0, t1, cy, size, *cols, max_w=max_w))
    FOCUS.append((t0, t1))
    sfx(t0, "impact"); sfx(t0 + 0.02, "shimmer")


def build_heroes():
    hero(["למה?"], 0.10, o("H", 50.15), 300, 330)
    hero(["למידה", "עצמאית"], o("A", 66.70), o("A", 69.40), 345, 215, "cyan")
    hero(["אין דבר כזה"], o("C", 81.50), o("C", 85.50), 290, 200, max_w=900)
    hero(["מהנה!"], o("E", 99.22), VOICE_END + 0.05, 300, 300, "cyan")
    hero(["כיתה", "הפוכה"], VOICE_END + 0.12, TOTAL + 1, 345, 240)


# ============================================================ graphics (front layer)
def graphics():
    pill, panel, tag, big_pop, text = B3.pill, B3.panel, B3.tag, B3.big_pop, B3.text
    # ---------------- H · hook: kicker on top, the hero word "למה?" sits behind the presenter
    big_pop(o("H", 50.20), o("H", 51.05), 540, 430, "להקשות?", size=86, col=WHITE, layer=42)

    # ---------------- H · contrast (split screen)
    a, b = o("H", 51.15), o("H", 55.05)
    panel(a, b, 40, 300, 440, 820, side="left")
    tag(a + 0.15, b, 260, 360, "ניגוד")
    pill(a + 0.25, b, 260, 500, "להקשות עליכם", size=48, layer=12)
    B3.icon_x(a + 0.35, b, 260, 575)
    R.strike(a + 0.45, b, 260, 500, 330)
    sfx(a + 0.45, "click")
    big_pop(o("H", 51.24), b, 260, 700, "אלא", size=104, layer=15)
    pill(o("H", 51.80), b, 260, 900, "להכין אתכם", size=54, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", layer=12)
    B3.icon_check(o("H", 51.95), b, 260, 985)

    # ---------------- H · cause -> effect (zoom-out reveal)
    a, b = o("H", 55.15), o("H", 57.45)
    tag(a, b, 540, 160, "סיבה ותוצאה · כדי ש...")
    pill(a + 0.05, b, 810, 280, "כיתה הפוכה", size=54, layer=12)
    R.arrow_left(a + 0.3, b, 540, 280, length=120, col=YELL); sfx(a + 0.3, "click")
    pill(a + 0.45, b, 270, 280, "לומדים עצמאיים", size=52, fg=NAVY, bg=YELL, alpha="&H00&", weight="900Black", layer=12)
    text(o("H", 56.24), b, 270, 375, "בלמידה מקוונת", size=44, col=TURQ)
    FOCUS.append((a, b))

    # ---------------- H · addition (split screen, stacked)
    a, b = o("H", 57.55), o("H", 61.90)
    panel(a, b, 600, 300, 440, 860, side="right")
    tag(a + 0.15, b, 820, 360, "הוספה · וגם")
    pill(o("H", 58.10), b, 820, 500, "אוניברסיטאות", size=50, layer=12)
    big_pop(o("H", 59.0), b, 820, 600, "+", size=96, layer=15)
    pill(o("H", 59.10), b, 820, 700, "מכללות", size=50, layer=12)
    B3.arrow_down(o("H", 60.35), b, 820, 760, length=80)
    pill(o("H", 60.60), b, 820, 900, "קורסים מקוונים", size=48, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", layer=12)

    # ---------------- M · the flipped-classroom model
    b = o("M", 27.40)
    pill(o("M", 15.95), o("M", 18.25), 540, 170, "מודל כיתה הפוכה", size=46, fg=NAVY, bg=YELL, alpha="&H00&", weight="900Black")
    FOCUS.append((o("M", 15.95), o("M", 18.25)))
    a = o("M", 18.30)
    panel(a, b, 600, 260, 440, 960, side="right")
    s1e = o("M", 19.95)
    tag(a + 0.1, s1e, 820, 330, "שלב 1 · בבית")
    B3.big_icon(R.icon_house, a + 0.2, s1e, 800, 450)
    B3.icon_student(a + 0.3, s1e, 790, 640, scale=150, delay=0.1)
    B3.icon_laptop(a + 0.45, s1e, 880, 690)
    text(a + 0.55, s1e, 820, 830, "לומדים את החומר", size=52)
    text(a + 0.65, s1e, 820, 905, "בקצב שלכם", size=44, col=TURQ)
    a2 = o("M", 20.0)
    tag(a2, b, 820, 330, "שלב 2 · בכיתה")
    sfx(a2, "whoosh_s")
    B3.big_icon(R.icon_board, a2 + 0.1, b, 800, 440)
    for i, x in enumerate((725, 820, 915)):
        B3.icon_student(a2 + 0.2, b, x, 580, scale=105, delay=0.12 * i)
    text(o("M", 23.05), b, 820, 680, "תרגול וחזרה", size=54, col=YELL)
    sfx(o("M", 23.05), "pop")
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

    # ---------------- A · the aspiration: hero "למידה עצמאית" behind, kicker on top
    a, b = o("A", 65.85), o("A", 69.45)
    a, b = o("A", 69.55), o("A", 78.50)
    panel(a, b, 40, 300, 440, 900, side="left")
    tag(a + 0.15, b, 260, 360, "רצף הלמידה")
    pill(o("A", 70.95), b, 260, 500, "לומדים בכוחות עצמכם", size=38, layer=12)
    B3.arrow_down(o("A", 72.4), b, 260, 545, length=80)
    pill(o("A", 72.60), b, 260, 680, "בכיתה: תרגול ומבדק", size=40, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", layer=12)
    big_pop(o("A", 76.75), b, 260, 830, "בלי", size=80, col=WHITE, layer=15)
    pill(o("A", 77.10), b, 260, 940, "למידה של החומר", size=44, layer=12)
    R.strike(o("A", 77.55), b, 260, 940, 300); sfx(o("A", 77.55), "click")

    # ---------------- T · concept map of logical connectors (held into C)
    b = o("C", 81.40)
    pill(o("T", 27.50), o("T", 29.70), 540, 175, "הנושא הבא", size=44, fg=NAVY, bg=TURQ, alpha="&H00&")
    FOCUS.append((o("T", 27.50), b))
    big_pop(o("T", 29.80), b, 540, 250, "קשרים לוגיים", size=100)
    nodes = [(850, "לכן", "סיבה ותוצאה"), (540, "אבל", "ניגוד"), (230, "וגם", "הוספה")]
    for i, (sx, word, kind) in enumerate(nodes):
        st = o("T", 30.10) + 0.16 * i
        R.line(st, b, 540, 320, sx, 420, width=7, col=TURQ)
        sfx(st, "click")
        ev(12, st + 0.1, b, f"{{\\an5\\pos({sx},470)\\bord4\\3c{TURQ}\\shad0\\1c{NAVY}\\1a&H10&\\fad(120,200){R.POP}\\p1}}"
                            f"{rrect(250, 130, 30)}")
        text(st + 0.1, b, sx, 448, word, size=58, col=YELL, font="Heebo Black")
        text(st + 0.1, b, sx, 503, kind, size=30, col=WHITE)
        sfx(st + 0.1, "pop")

    # ---------------- C · no excuses: hero "אין דבר כזה" behind, struck chips at chest height
    b = o("C", 85.55)
    for i, (s0, s1, label) in enumerate([(82.36, 83.0, "לא ידעתי"), (83.30, 84.1, "לא שמעתי"), (84.52, 85.4, "לא עשיתי")]):
        cx = (845, 540, 235)[i]
        w = pill(o("C", s0), b, cx, 1200, label, size=44)
        R.strike(o("C", s1) - 0.05, b, cx, 1200, w - 30)
        sfx(o("C", s1) - 0.05, "click")
    a, b = o("C", 85.68), o("C", 87.72)
    w = pill(a, b, 540, 260, "אני זמין לשאלות", size=60, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", pad_x=44)
    B3.icon_check(a + 0.15, b, 540 + w // 2 + 30, 200, col=YELL)
    FOCUS.append((a, b))

    # ---------------- end card: hero "כיתה הפוכה" behind the frozen presenter, glass tagline panel
    a, b = VOICE_END + 0.35, TOTAL
    ev(50, a, b, f"{{\\an5\\move(540,1380,540,1330,0,320)\\bord3\\3c{TURQ}\\3a&H30&\\shad0\\1c{NAVY}\\1a&H28&\\fad(220,0)\\p1}}"
                 f"{rrect(900, 250, 50)}")
    ev(51, a + 0.12, b, f"{{\\an5\\pos(540,1290)\\fnHeebo Black\\fs64\\1c{WHITE}\\bord0\\shad0\\fad(200,0)}}חושבים, מקשרים")
    ev(51, a + 0.32, b, f"{{\\an5\\pos(540,1375)\\fnHeebo Black\\fs64\\1c{TURQ}\\bord0\\shad0\\fad(200,0)}}ולומדים אחרת!")
    for i, x in enumerate((420, 540, 660)):
        ev(52, a + 0.5 + 0.1 * i, b, f"{{\\an5\\pos({x},1478)\\bord0\\shad0\\1c{YELL if i == 1 else TURQ}\\fad(120,0){R.POP}\\p1}}"
                                     "m 0 -12 b 7 -12 12 -7 12 0 b 12 7 7 12 0 12 b -7 12 -12 7 -12 0 b -12 -7 -7 -12 0 -12")
        sfx(a + 0.5 + 0.1 * i, "tick")
    R.line(a + 0.55, b, 660, 1478, 420, 1478, width=4, col=WHITE, grow=360, layer=51, alpha="&H40&")


# ============================================================ captions
R.HIGHLIGHT = R.HIGHLIGHT + [(["הכיתה", "ההפוכה"], TURQ), (["בכיתה", "ההפוכה"], TURQ), (["תתרגלו"], YELL),
                             (["נבחנים"], YELL)]


def captions(words):
    chunks = R.build_captions(words)
    for c in chunks:
        for w in c["words"]:
            w["on"], w["off"] = o(c["seg"], w["s"]), o(c["seg"], w["e"])
    chunks = R.apply_caption_edits(chunks)            # normative Hebrew (language edit)
    for c in chunks:
        toks = c["words"]
        cols = [None] * len(toks)
        for phrase, col in R.HIGHLIGHT:
            n = len(phrase)
            for i in range(len(toks) - n + 1):
                if [R.clean(x["w"]) for x in toks[i:i + n]] == phrase:
                    for k in range(n):
                        cols[i + k] = col
        c["cols"] = cols
    CAPS.build(chunks, lambda w: (w["on"], w["off"]), lambda i, c: c["cols"][i], ev, text_w, NAVY, WHITE, YELL, TURQ)
    return chunks


def write_ass(path, which):
    evs = [e for e in R.EVENTS if (which == "all") or ((",Cap," in e) == (which == "captions"))]
    with open(path, "w", encoding="utf-8") as f:
        f.write(B3.ASS_HEAD.replace("(v3)", "(v4)").replace("Style: Cap,Heebo Black,80", "Style: Cap,Heebo Black,78")
                + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        f.write("\n".join(evs) + "\n")


# ============================================================ studio layers
class Studio:
    def __init__(self):
        LY.build(ASSETS, STUDIO_IMG)
        rd = lambda n, f=cv2.IMREAD_COLOR: cv2.imread(os.path.join(ASSETS, n), f)   # noqa: E731
        self.far = {k: (rd(f"far_{k}.png"), rd(f"far_{k}_soft.png")) for k in LY.KEYS}
        self.lay = {n: rd(f"{n}.png", cv2.IMREAD_UNCHANGED) for n in ("desk", "floor", "ceiling")}
        self.mask = rd("screen_mask.png", cv2.IMREAD_GRAYSCALE)
        rng = np.random.default_rng(9)
        self.motes = rng.uniform(0, 1, (70, 2)), rng.uniform(-0.004, 0.004, 70), rng.uniform(-0.012, -0.003, 70), \
            rng.uniform(1.2, 4.0, 70), rng.uniform(25, 85, 70)

    def M(self, t, z, dx, f):
        s = 1 + (z - 1) * f
        Ml = np.array([[s, 0, 540 - LY.CX * s + dx * f], [0, s, 960 - LY.CY * s], [0, 0, 1]], np.float64)
        return (cam_matrix(t, f) @ Ml)[:2].astype(np.float32)

    def frame(self, t, z, dx, dim=0.0):
        Mf = self.M(t, z, dx, LY.PARALLAX["far"])
        wp = lambda img, M, bv=0: cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR,   # noqa: E731
                                                 borderMode=cv2.BORDER_REFLECT)
        foc = B3.focus_at(t)
        out = None
        for k, wk in B3.screen_weights(t).items():
            sharp, soft = self.far[k]
            p = wp(sharp, Mf).astype(np.float32) if foc < 0.99 else None
            if foc > 0.01:
                q = wp(soft, Mf).astype(np.float32)
                p = q if p is None else p * (1 - foc) + q * foc
            out = p * wk if out is None else out + p * wk
        # light sweep across the screen every 4 s
        m = wp(self.mask, Mf).astype(np.float32) / 255
        sx = -300 + ((t % 4.0) / 4.0) * (W + 600)
        bandx = np.exp(-0.5 * ((np.arange(W) - sx) / 90) ** 2).astype(np.float32)[None, :]
        out += (m * bandx)[..., None] * np.array([232, 217, 0], np.float32) * 0.10
        for n in ("desk", "floor", "ceiling"):
            lay = wp(self.lay[n], self.M(t, z, dx, LY.PARALLAX[n])).astype(np.float32)
            a = lay[..., 3:4] / 255
            out = out * (1 - a) + lay[..., :3] * a
        # floating dust in the light (between the set and the presenter)
        (p0, vx, vy, r, br) = self.motes
        dust = np.zeros((H, W), np.float32)
        for (x0, y0), ux, uy, rr, bb in zip(p0, vx, vy, r, br):
            x = ((x0 + ux * t) % 1) * W + dx * 0.6
            y = ((y0 + uy * t) % 1) * H
            cv2.circle(dust, (int(x), int(y)), int(rr), float(bb), -1, cv2.LINE_AA)
        dust = cv2.GaussianBlur(dust, (0, 0), 1.6)[..., None]
        out += dust * np.array([1.0, 0.96, 0.85], np.float32) * 0.55
        if dim > 0:
            out *= 1 - 0.20 * dim
        return out


# ============================================================ presenter
_EDGE_FEATHER = np.clip(np.minimum(np.arange(2 * SW), 2 * SW - 1 - np.arange(2 * SW)) / 24, 0, 1)[None, :].astype(np.float32)


def sr_patch(seg_id, i):
    p = os.path.join(SR_CACHE, seg_id, f"{i:04d}.png")
    pj = os.path.join(SR_CACHE, seg_id, "pos.json")
    if not (os.path.exists(p) and os.path.exists(pj)):
        return None
    if not hasattr(sr_patch, "pos") or sr_patch.pos[0] != seg_id:
        sr_patch.pos = (seg_id, json.load(open(pj)))
    x0, y0 = sr_patch.pos[1][str(i)]
    return cv2.imread(p).astype(np.float32), 2 * x0, 2 * y0


_SR_W = None


def presenter_2x(fr, a2, seg_id, i):
    """2x frame with Real-ESRGAN detail on the head, and a colour-decontaminated matte edge"""
    global _SR_W
    up2 = cv2.resize(fr, (2 * SW, 2 * SH), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    sp = sr_patch(seg_id, i)
    if sp is not None:
        img, x, y = sp
        h, w = img.shape[:2]
        if _SR_W is None or _SR_W.shape[:2] != (h, w):
            fx = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / 46, 0, 1)
            fy = np.clip(np.minimum(np.arange(h), h - 1 - np.arange(h)) / 46, 0, 1)
            _SR_W = (np.outer(fy, fx) * 0.55)[..., None].astype(np.float32)      # 55% model, 45% original
        up2[y:y + h, x:x + w] = up2[y:y + h, x:x + w] * (1 - _SR_W) + img * _SR_W
    # decontaminate: semi-transparent edge pixels take the colour of the nearby opaque presenter
    a = a2 * _EDGE_FEATHER
    w2 = a * a
    num = cv2.GaussianBlur(up2 * w2[..., None], (0, 0), 5)
    den = cv2.GaussianBlur(w2, (0, 0), 5)[..., None] + 1e-4
    est = num / den
    e = (np.clip((0.97 - a) / 0.97, 0, 1) * (a > 0.01))[..., None]
    up2 = up2 * (1 - e) + est * e
    return up2, a


def presenter_layer(up2, a2, t, z, dx, tcx, tey, tfw):
    s = W / SW * z                       # output px per source px
    roll = abs(cam_global(t)[0])
    gap = 540 * math.tan(math.radians(roll)) + 8
    ox = W / 2 + dx - tcx * s
    oy = EYE * H - tey * s
    oy = max(oy, H + gap - SH * s)       # never lift the body off the bottom edge
    Ml = np.array([[s / 2, 0, ox], [0, s / 2, oy], [0, 0, 1]], np.float64)
    M = (cam_matrix(t, 1.0) @ Ml)[:2].astype(np.float32)
    subj = cv2.warpAffine(up2, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    a = cv2.warpAffine(a2, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    fx, fy = M[0, 0] * tcx * 2 + M[0, 1] * tey * 2 + M[0, 2], M[1, 0] * tcx * 2 + M[1, 1] * tey * 2 + M[1, 2]
    return subj, a, fx, fy, tfw * s


def relight(subj, a, bg, fx, fy, fw, spill):
    gx = np.exp(-0.5 * ((np.arange(W) - fx - 0.15 * fw) / (fw * 1.4)) ** 2)
    gy = np.exp(-0.5 * ((np.arange(H) - fy) / (fw * 1.9)) ** 2)
    subj = subj * (1.0 + 0.13 * np.outer(gy, gx))[..., None].astype(np.float32)        # soft key
    subj = subj + 0.22 * (subj - cv2.GaussianBlur(subj, (0, 0), 1.2))                  # gentle crispness
    inner = cv2.erode(a, np.ones((9, 9), np.uint8))
    edge = cv2.GaussianBlur(np.clip(a - inner, 0, 1), (0, 0), 3)[..., None]
    side = np.clip((np.arange(W) - fx) / 300, -1, 1)[None, :, None]
    rim = np.where(side > 0, np.array([232, 217, 0], np.float32) * side, np.array([255, 175, 101], np.float32) * -side)
    subj = subj + edge * rim * 0.6
    bgb = cv2.resize(cv2.GaussianBlur(cv2.resize(bg, (W // 4, H // 4)), (0, 0), 3), (W, H))
    subj = subj * (1 - 0.30 * edge) + bgb * 0.30 * edge                                  # light wrap
    if spill is not None:                                                               # graphics light the presenter
        ah = cv2.resize(a, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        wide = cv2.resize(cv2.GaussianBlur(np.clip(ah - cv2.erode(ah, np.ones((15, 15), np.uint8)), 0, 1), (0, 0), 4.5),
                          (W, H))[..., None]
        subj = subj + wide * spill * 0.55
    subj = subj * np.array([1.04, 1.0, 0.965], np.float32)                               # match the cool set
    return np.clip(subj, 0, 255)


def composite(bg, subj, a):
    small = cv2.resize(a, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    sh = cv2.resize(cv2.GaussianBlur(np.roll(np.roll(small, 6, axis=1), 4, axis=0), (0, 0), 5.5), (W, H))[..., None]
    bg = bg * (1 - 0.22 * sh)
    a3 = a[..., None]
    return bg * (1 - a3) + subj * a3


# ============================================================ graphics layer stream
class Overlay:
    """front graphics rendered by libass into an RGBA stream (alpha=1), one frame per output frame"""
    def __init__(self, ass_path):
        self.p = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
             f"color=c=black@0.0:s={W}x{H}:r={FPS}:d={TOTAL + 0.5:.3f},format=rgba",
             "-vf", f"ass={ass_path.replace(':', chr(92) + ':')}:fontsdir={R.FONTS}:alpha=1",
             "-frames:v", str(NFRAMES), "-f", "rawvideo", "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
        self.n = W * H * 4

    def next(self):
        buf = self.p.stdout.read(self.n)
        if len(buf) < self.n:
            return None
        f = np.frombuffer(buf, np.uint8).reshape(H, W, 4)
        if not f[..., 3].any():
            return None
        rgb = f[..., 2::-1].astype(np.float32)          # RGBA -> BGR
        a = f[..., 3:4].astype(np.float32) / 255
        return rgb, a


def overlay_spill(g):
    if g is None:
        return None
    rgb, a = g
    small = cv2.resize(rgb * a, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(small, (0, 0), 10), (W, H))


def apply_overlay(img, g):
    if g is None:
        return img
    rgb, a = g
    small_a = cv2.resize(a[..., 0], (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    sh = cv2.resize(cv2.GaussianBlur(np.roll(np.roll(small_a, 4, 0), 3, 1), (0, 0), 5), (W, H))[..., None]
    img = img * (1 - 0.35 * sh)                                              # soft drop shadow
    glow = cv2.resize(cv2.GaussianBlur(cv2.resize(rgb * a, (W // 2, H // 2), interpolation=cv2.INTER_AREA), (0, 0), 7), (W, H))
    img = img + glow * 0.45                                                  # neon glow
    return img * (1 - a) + rgb * a


# ============================================================ frame assembly
def hero_dim(t):
    v = 0.0
    for h in HEROES:
        if h.active(t):
            v = max(v, min(ease((t - h.t0) / 0.2), 1 - ease((t - h.t1) / 0.25)))
    return v


def assemble(studio, t, z, dx, up2, a2, track_i, g, fidx, zs=None):
    zs = zs or [z]
    acc = None
    spill = overlay_spill(g)
    for zz in zs:
        bg = studio.frame(t, zz, dx, dim=hero_dim(t))
        Mc = cam_matrix(t, 0.8)[:2]
        for h in HEROES:
            h.draw(bg, t, Mc, zz, dx)
        subj, a, fx, fy, fw = presenter_layer(up2, a2, t, zz, dx, *track_i)
        c = composite(bg, relight(subj, a, bg, fx, fy, fw, spill), a)
        acc = c if acc is None else acc + c
    return acc / len(zs)


def finish(img, g, fidx, trans_amt=0.0, leak=0.0, side=1):
    img = FX.grade(img)
    if trans_amt > 0:
        img = FX.aberration(img, trans_amt)
    if leak > 0:
        img = FX.light_leak(img, leak, side)
    img = apply_overlay(img, g)
    img = FX.bloom(img)
    return FX.grain(img, fidx)


def render(tracks):
    studio = Studio()
    clean = os.path.join(TMP, "v4_clean.mkv")
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-vf", "vignette=angle=0.34", "-c:v", "libx264", "-preset", "medium", "-crf", "10",
         "-pix_fmt", "yuv420p", clean], stdin=subprocess.PIPE)
    ov = Overlay(os.path.join(OUT, "reel_v4_graphics.ass"))
    fidx, prev_kind, last = 0, None, None
    for seg in SEGMENTS:
        sid, n = seg["id"], seg["nf"]
        td = tracks[sid]
        prev_a, prev_z = None, None
        for i, fr in enumerate(R.read_segment(seg)):
            t = seg["out_in"] + i / FPS
            z, dx = cam_at(sid, i / FPS)
            a2 = cv2.imread(os.path.join(MATTE, sid, f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            if prev_a is not None:                         # temporal de-flicker of the matte
                d = np.abs(a2 - prev_a)
                a2 = np.where(d < 0.2, 0.6 * a2 + 0.4 * prev_a, a2)
            prev_a = a2
            up2, a2d = presenter_2x(fr, a2, sid, i)
            dz = 0 if prev_z is None else abs(z - prev_z)
            zs = [z] if dz < 0.012 else list(np.linspace(prev_z, z, int(min(9, 5 + dz / 0.01))))
            prev_z = z
            g = ov.next()
            img = assemble(studio, t, z, dx, up2, a2d, (td[0][i], td[1][i], td[2][i]), g, fidx, zs)
            amt, leak, side = min(1.0, dz / 0.03), 0.0, 1
            kind_out, kind_in = TRANS[sid], prev_kind
            if i >= n - TRANS_FR and kind_out not in ("cut", "pull"):
                k = i - (n - TRANS_FR)
                img = B3.transition(img, kind_out, "out", k, TRANS_FR)
                amt = max(amt, (k + 1) / TRANS_FR)
                if kind_out.startswith("whip"):
                    leak, side = (k + 1) / TRANS_FR, (-1 if kind_out == "whip_l" else 1)
            if i < TRANS_FR and kind_in not in (None, "cut", "pull"):
                img = B3.transition(img, kind_in, "in", i, TRANS_FR)
                amt = max(amt, 1 - i / TRANS_FR)
                if kind_in.startswith("whip"):
                    leak, side = 1 - i / TRANS_FR, (1 if kind_in == "whip_l" else -1)
            if t < 0.55:                                   # opening dolly
                amt = max(amt, 1 - t / 0.55)
            img = finish(img, g, fidx, amt, leak, side)
            last = (up2, a2d, (td[0][-1], td[1][-1], td[2][-1]), z)
            enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
            fidx += 1
        prev_kind = TRANS[sid]
        print(f"  composited {sid} ({n} frames)", flush=True)
    # end card: freeze the last frame of the presenter, camera pulls back through the 2.5D set
    up2, a2d, tr, z0 = last
    for i in range(NFRAMES - fidx):
        t = VOICE_END + i / FPS
        p = ease(i / (0.9 * FPS))
        z = z0 + (0.98 - z0) * p
        g = ov.next()
        img = assemble(studio, t, z, 0, up2, a2d, tr, g, fidx)
        img = finish(img, g, fidx, 0.0)
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
        fidx += 1
    enc.stdin.close()
    enc.wait()
    return clean


# ============================================================ audio
SR = 48000


def env_ad(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1) * np.exp(-t / d)


def reverb_ir(seconds=1.8, seed=4):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 3.2)
    irl = rng.standard_normal(n) * env
    irr = rng.standard_normal(n) * env
    for ir in (irl, irr):                       # darker tail
        ir[:] = np.convolve(ir, np.ones(6) / 6, "same")
    return np.stack([irl, irr], 1) / np.sqrt((irl ** 2).sum())


def fft_conv(x, ir):
    n = len(x) + len(ir) - 1
    nf = 1 << (n - 1).bit_length()
    out = np.zeros((len(x), 2))
    for c in range(2):
        y = np.fft.irfft(np.fft.rfft(x[:, c], nf) * np.fft.rfft(ir[:, c], nf), nf)[:len(x)]
        out[:, c] = y
    return out


def onepole_lp(x, fc):
    a = 1 - math.exp(-2 * math.pi * fc / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y


def make_sfx():
    rng = np.random.default_rng(3)
    lib = {}
    n = int(0.5 * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    fc = 250 + 4200 * np.sin(np.pi * t / 0.5) ** 1.5
    y, acc = np.zeros(n), 0.0
    for k in range(n):
        acc += (1 - math.exp(-2 * math.pi * fc[k] / SR)) * (noise[k] - acc); y[k] = acc
    env = np.sin(np.pi * np.clip(t / 0.5, 0, 1)) ** 2
    w = y * env / (np.abs(y).max() + 1e-9)
    pan = np.linspace(-0.8, 0.8, n)                                    # stereo sweep
    lib["whoosh"] = np.stack([w * (1 - pan) / 2, w * (1 + pan) / 2], 1) * 1.1
    lib["whoosh_s"] = lib["whoosh"][::2] * 0.55
    n = int(0.09 * SR); t = np.arange(n) / SR
    m = 0.4 * np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 18) + 380) / SR) * env_ad(n, 0.002, 0.03)
    lib["pop"] = np.stack([m, m], 1)
    n = int(0.16 * SR); t = np.arange(n) / SR
    m = 0.5 * np.sin(2 * np.pi * np.cumsum(700 * np.exp(-t * 14) + 180) / SR) * env_ad(n, 0.002, 0.05)
    lib["pop_big"] = np.stack([m, m], 1)
    n = int(0.03 * SR)
    m = 0.32 * rng.standard_normal(n) * env_ad(n, 0.0005, 0.004)
    lib["click"] = np.stack([m, m], 1)
    m = 0.28 * np.sin(2 * np.pi * 2400 * np.arange(n) / SR) * env_ad(n, 0.0005, 0.006)
    lib["tick"] = np.stack([m, m], 1)
    n = int(0.9 * SR); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (42 + 70 * np.exp(-t * 22)) * t) * np.exp(-t * 5)
    crack = rng.standard_normal(n) * np.exp(-t * 35) * 0.25
    m = 0.75 * sub + crack
    lib["impact"] = np.stack([m, m], 1)
    n = int(0.75 * SR); t = np.arange(n) / SR
    sw = np.cumsum(rng.standard_normal(n)); sw -= np.convolve(sw, np.ones(200) / 200, "same")
    tone = np.sin(2 * np.pi * np.cumsum(300 + 1100 * (t / 0.75) ** 2) / SR)
    m = (0.25 * sw / (np.abs(sw).max() + 1e-9) + 0.13 * tone) * (t / 0.75) ** 2.2
    lib["rise"] = np.stack([m * 0.9, m], 1)
    n = int(1.1 * SR); t = np.arange(n) / SR
    bell = sum(np.sin(2 * np.pi * f * t + p) * a for f, a, p in ((2093, 0.5, 0), (3136, 0.3, 1), (4186, 0.22, 2), (5274, 0.12, 3)))
    m = 0.16 * bell * env_ad(n, 0.003, 0.35)
    lib["shimmer"] = np.stack([m, np.roll(m, 240)], 1)
    ir = reverb_ir(1.4, 8)
    for k in ("whoosh", "impact", "shimmer", "pop_big", "rise"):      # room tails
        dry = np.vstack([lib[k], np.zeros((int(1.4 * SR), 2))])
        lib[k] = dry + fft_conv(dry, ir) * 0.35
    return lib


def write_wav(path, st):
    st = np.clip(st, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


RISE_CUES = [o("H", 51.24), o("H", 55.15), o("T", 29.80), o("C", 81.50), VOICE_END + 0.12]


def render_sfx(path):
    lib = make_sfx()
    out = np.zeros((int(TOTAL * SR) + 3 * SR, 2))
    events = list(B3.SFX)
    for seg in SEGMENTS:
        if TRANS[seg["id"]] in ("whip_l", "whip_r", "zoomblur", "wipe"):
            events.append((seg["out_in"] + seg["dur"] - TRANS_FR / FPS, "whoosh"))
    events += [(0.0, "whoosh"), (VOICE_END, "whoosh")]
    events += [(max(p - 0.75, 0), "rise") for p in RISE_CUES]
    events.sort()
    last = {}
    gain = {"impact": 1.0, "shimmer": 0.9, "rise": 0.9, "whoosh": 1.0, "whoosh_s": 1.0, "pop": 0.8, "pop_big": 0.9,
            "click": 0.9, "tick": 0.8}
    for t, k in events:
        if t - last.get(k, -9) < 0.12:
            continue
        last[k] = t
        s = lib[k]
        i = int(t * SR)
        out[i:i + len(s)] += s[:len(out) - i] * gain[k] * 1.3
    write_wav(path, out[:int(TOTAL * SR)])


def make_music(path):
    """Original score, 100 BPM: hit at the hook, groove, breakdown under the topic reveal,
    build into 'אין דבר כזה', final swell on the end card. Generated here, royalty-free."""
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    beat = 0.6
    bar = 4 * beat
    rng = np.random.default_rng(11)
    pad, pluck, bass, drums = (np.zeros((n, 2)) for _ in range(4))
    chords = [[57, 60, 64, 71], [53, 57, 60, 64], [48, 55, 60, 64], [55, 59, 62, 67]]
    roots = [45, 41, 36, 43]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)                                  # noqa: E731
    brk0, brk1 = o("T", 27.42), o("T", 29.80)                                  # breakdown window
    build0 = o("C", 80.12)
    for b in range(int(TOTAL / bar) + 1):
        t0 = b * bar
        ch, rt = chords[b % 4], roots[b % 4]
        m = (t >= t0) & (t < t0 + bar + 1.2)
        tt = t[m] - t0
        envp = np.minimum(tt / 0.5, 1) * np.where(tt > bar, np.exp(-(tt - bar) * 3), 1)
        for k, nn in enumerate(ch):                                          # warm detuned pad
            for det, c in ((0.996, 0), (1.004, 1)):
                f = hz(nn) * det
                wv = sum(np.sin(2 * np.pi * f * h * tt) / h for h in (1, 2, 3)) * 0.33
                pad[m, c] += envp * wv / len(ch)
        for k in range(8):                                                   # 8th-note pluck arpeggio
            ts0 = t0 + k * beat / 2
            mm = (t >= ts0) & (t < ts0 + 0.6)
            q = t[mm] - ts0
            f = hz(ch[(k * 3) % 4] + 12)
            v = (np.sin(2 * np.pi * f * q) + 0.35 * np.sin(4 * np.pi * f * q)) * np.exp(-q * 8) * np.minimum(q / 0.003, 1)
            pan = 0.3 + 0.4 * (k % 2)
            pluck[mm, 0] += v * (1 - pan) * 0.22
            pluck[mm, 1] += v * pan * 0.22
        for k in range(8):                                                   # bass on 8ths
            ts0 = t0 + k * beat / 2
            mm = (t >= ts0) & (t < ts0 + 0.28)
            q = t[mm] - ts0
            v = np.tanh(1.6 * np.sin(2 * np.pi * hz(rt) * q)) * np.exp(-q * 6) * (1.0 if k % 2 == 0 else 0.6)
            bass[mm] += v[:, None] * 0.30
        for k in range(4):                                                   # drums
            ts0 = t0 + k * beat
            if brk0 <= ts0 < brk1 + bar * 0.5 or ts0 > VOICE_END:
                continue
            mm = (t >= ts0) & (t < ts0 + 0.35); q = t[mm] - ts0
            kick = np.sin(2 * np.pi * (48 + 80 * np.exp(-q * 30)) * q) * np.exp(-q * 11)
            drums[mm] += kick[:, None] * 0.55
            if k in (1, 3):                                                  # soft clap
                mm = (t >= ts0) & (t < ts0 + 0.2); q = t[mm] - ts0
                clap = rng.standard_normal(mm.sum()) * (np.exp(-q * 30) + 0.5 * np.exp(-np.abs(q - 0.012) * 300))
                drums[mm] += onepole_lp(clap, 3500)[:, None] * 0.16
            for hh in (0.5, 0.25, 0.75):                                     # hats
                hs = ts0 + beat * hh
                mm = (t >= hs) & (t < hs + 0.05); q = t[mm] - hs
                hat = rng.standard_normal(mm.sum()) * np.exp(-q * 90) * (0.06 if hh == 0.5 else 0.03)
                drums[mm, 0] += hat * 0.8; drums[mm, 1] += hat
    # build: snare roll into the stair punches of "אין דבר כזה"
    for k in range(16):
        ts0 = build0 + k * (1.3 / 16)
        mm = (t >= ts0) & (t < ts0 + 0.08); q = t[mm] - ts0
        sn = rng.standard_normal(mm.sum()) * np.exp(-q * 45) * (0.05 + 0.12 * k / 15)
        drums[mm] += sn[:, None]
    ir = reverb_ir(2.2, 6)
    wet = fft_conv(pad * 0.6 + pluck + drums * 0.25, ir) * 0.35
    mix = pad * 0.55 + pluck + bass + drums + wet
    # arc: slightly lower under the model explanation, swell at the end card
    arc = np.ones(n)
    arc *= np.where((t > brk0) & (t < brk1), 0.75, 1.0)
    arc *= np.where(t > VOICE_END, 1.25, 1.0)
    fade = np.minimum(1, t / 0.4) * np.minimum(1, (TOTAL - t) / 1.4)
    mix *= (arc * fade)[:, None]
    mix /= np.abs(mix).max() + 1e-9
    write_wav(path, mix * 0.7)


def render_audio():
    os.makedirs(TMP, exist_ok=True)
    voice = os.path.join(R.TMP, "voice.wav")
    if not os.path.exists(voice):
        R.render_audio()
    music = os.path.join(TMP, "music_v4.wav"); make_music(music)
    fx = os.path.join(TMP, "sfx_v4.wav"); render_sfx(fx)
    pre = os.path.join(TMP, "mix_v4_pre.wav")
    mix = os.path.join(TMP, "mix_v4.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", music, "-i", fx, "-filter_complex",
                    "[0:a]deesser=i=0.35,equalizer=f=120:t=q:w=1:g=1.5[vo];"
                    "[1:a]volume=-16dB[m];[vo]asplit=2[v][sc];"
                    "[m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=25:release=380[md];"
                    "[2:a]volume=-10dB[fx];[v][md][fx]amix=inputs=3:normalize=0",
                    "-ar", "48000", "-t", f"{TOTAL:.4f}", pre], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(r[r.rfind("{"):r.rfind("}") + 1])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
                    f"loudnorm=I=-14:TP=-1.5:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                    f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
                    "-ar", "48000", mix], check=True)
    return mix


# ============================================================ cover + QA images
def render_cover(tracks):
    studio = Studio()
    seg = SEG["C"]
    i = R.frames(85.9 - seg["src_in"])
    for k, fr in enumerate(R.read_segment(seg)):
        if k == i:
            break
    a2 = cv2.imread(os.path.join(MATTE, "C", f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    up2, a2d = presenter_2x(fr, a2, "C", i)
    td = tracks["C"]
    old_tl, old_focus, old_heroes = B3.SCREEN_TL, list(FOCUS), list(HEROES)
    B3.SCREEN_TL = [(0, "flip")]
    HEROES[:] = [HR.Hero(["כיתה", "הפוכה"], -1, 9, 330, 260)]
    t = 30.0
    z = 1.10
    img = assemble(studio, t, z, 0, up2, a2d, (td[0][i], td[1][i] + 30, td[2][i]), None, 0)
    g = np.clip((np.arange(H) - 1180) / 380, 0, 1)[:, None, None] * 0.88
    img = img * (1 - g) + NAVY_BGR * g
    img = FX.grain(FX.bloom(FX.grade(img)), 0)
    B3.SCREEN_TL, HEROES[:] = old_tl, old_heroes
    raw = os.path.join(TMP, "cover_v4_bg.png"); cv2.imwrite(raw, np.clip(img, 0, 255).astype(np.uint8))
    cass = os.path.join(TMP, "cover_v4.ass")
    dot = "m 0 -16 b 9 -16 16 -9 16 0 b 16 9 9 16 0 16 b -9 16 -16 9 -16 0 b -16 -9 -9 -16 0 -16"
    lines = [f"{{\\an5\\pos(540,1400)\\fnHeebo Black\\fs108\\1c{WHITE}\\bord6\\3c{NAVY}\\shad4\\4a&H60&}}לומדים",
             f"{{\\an5\\pos(540,1520)\\fnHeebo Black\\fs108\\1c{TURQ}\\bord6\\3c{NAVY}\\shad4\\4a&H60&}}קשרים לוגיים",
             f"{{\\an5\\pos(540,1612)\\bord0\\shad0\\1c{YELL}\\p1}}m -170 0 l 170 0 l 170 9 l -170 9"]
    lines += [f"{{\\an5\\pos({x},1660)\\bord0\\shad0\\1c{YELL if k == 1 else TURQ}\\p1}}{dot}" for k, x in enumerate((450, 540, 630))]
    with open(cass, "w", encoding="utf-8") as f:
        f.write(B3.ASS_HEAD + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for k, l in enumerate(lines):
            f.write(f"Dialogue: {k},0:00:00.00,0:00:05.00,G,,0,0,0,,{l}\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf", f"ass={cass.replace(':', chr(92) + ':')}:fontsdir={R.FONTS}",
                    "-q:v", "2", os.path.join(OUT, "cover_v4.jpg")], check=True)


def safe_zone_check(video, t=9.6):
    """frame with Instagram/TikTok interface zones drawn on top, to show nothing important is hidden"""
    p = os.path.join(TMP, "sz.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", video, "-frames:v", "1", p], check=True)
    img = cv2.imread(p).astype(np.float32)
    zones = [((0, 0, W, 150), "top"), ((0, H - 420, W, H), "bottom"), ((W - 150, 760, W, H - 420), "right")]
    for (x0, y0, x1, y1), _ in zones:
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * 0.55 + np.array([60, 60, 230], np.float32) * 0.45
    cv2.rectangle(img, (150, 150), (W - 150, H - 420), (90, 220, 90), 4)
    cv2.imwrite(os.path.join(OUT, "safe_zones_check.jpg"), np.clip(img, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])


# ============================================================ EDL
EDL_EXTRA = [
    ("00:00.00–00:00.55", "דולי מהיר מצילום רחב של האולפן לתקריב (0.96 ← 1.40) עם גלגול מצלמה 3.2° ← 0°, טשטוש תנועה וסטייה כרומטית"),
    ("00:00.10–00:03.53", "מילת ענק \"למה?\" מאחורי הדמות (בין האולפן לבינך), נכנסת ב-slam עם overshoot. Impact + shimmer"),
    ("לאורך כל הסרטון", "אולפן 2.5D: קיר ומסך 0.25, דסק 0.45, תקרה 0.55, רצפה 0.60 מתנועת המצלמה. אבק מרחף באור, רעידת מצלמה עדינה"),
    ("לאורך כל הסרטון", "פרטי פנים: Real-ESRGAN על הראש (55%), ניקוי צבע בקצוות השיער, תאורת softbox רכה, אור צד טורקיז/כחול, אור מהגרפיקה שנופל עליך"),
    ("לאורך כל הסרטון", "כתוביות word-box: כל מילה נדלקת כשהיא נאמרת, ותיבה צהובה (או טורקיז למושגים) קופצת ממילה למילה"),
    (f"{o('A', 66.70):05.2f}–{o('A', 69.40):05.2f}", "מילת ענק \"למידה עצמאית\" (טורקיז) מאחורי הדמות"),
    (f"{o('C', 81.50):05.2f}–{o('C', 85.50):05.2f}", "מילת ענק \"אין דבר כזה\" מאחורי הדמות, ושלוש תוויות מחוקות בגובה החזה, עם punch מדורג"),
    (f"{o('E', 99.22):05.2f}–{VOICE_END:05.2f}", "מילת ענק \"מהנה!\" (טורקיז)"),
    (f"{VOICE_END:05.2f}–{TOTAL:05.2f}", "פריים קפוא, המצלמה נסוגה דרך שכבות האולפן, \"כיתה הפוכה\" מאחורי הדמות, ופאנל זכוכית: חושבים, מקשרים ולומדים אחרת!"),
    ("לאורך כל הסרטון", "גרייד: צל טורקיז ואור חם (split-tone), bloom על נורות ה-LED והגרפיקה, גרעין פילם עדין, light leaks במעברי whip"),
    ("סאונד", "פסקול מקורי ב-100 BPM עם hit בפתיחה, breakdown בחשיפת הנושא, תופי snare לקראת \"אין דבר כזה\" ו-swell בסיום. אפקטים עם הדהוד חדר, de-esser על הקול, ‎-14 LUFS"),
]


def write_edl():
    src = open(os.path.join(HERE, "..", "output_v3", "EDL_v3.md"), encoding="utf-8").read()
    src = src.replace("v3", "v4", 1)
    add = ["", "## מה חדש בגרסה 4", "", "| זמן | מה קורה |", "|---|---|"] + [f"| {a} | {b} |" for a, b in EDL_EXTRA]
    add += ["", "**שינויים מול v3:** \"למה?\", \"למידה עצמאית\", \"אין דבר כזה\" ו\"מהנה!\" עברו מכותרות קופצות מלפנים "
            "למילות ענק מאחורי הדמות. התוויות \"לא ידעתי/לא שמעתי/לא עשיתי\" ירדו לגובה החזה (y=1200). "
            "המסך מאחור מציג \"בבית ← בכיתה\" בפתיחה במקום \"למה ?\", כדי לא לכפול את מילת הענק."]
    open(os.path.join(OUT, "EDL_v4.md"), "w", encoding="utf-8").write(src + "\n".join(add) + "\n")


# ============================================================ main
def main():
    os.makedirs(TMP, exist_ok=True)
    words = json.load(open(os.path.join(HERE, "..", "transcript_words.json"), encoding="utf-8"))["words"]
    R.EVENTS.clear()
    build_heroes()
    graphics()
    chunks = captions(words)
    write_ass(os.path.join(OUT, "reel_v4_graphics.ass"), "graphics")
    write_ass(os.path.join(OUT, "reel_v4_captions.ass"), "captions")
    write_ass(os.path.join(OUT, "reel_v4_full.ass"), "all")
    with open(os.path.join(OUT, "reel_v4.srt"), "w", encoding="utf-8") as f:
        for k, c in enumerate(chunks, 1):
            f.write(f"{k}\n{R.srt_time(c['start'])} --> {R.srt_time(c['end'])}\n{' '.join(w['w'] for w in c['words'])}\n\n")
    json.dump(sorted(B3.SFX), open(os.path.join(OUT, "sfx_cues.json"), "w"), indent=0)
    write_edl()
    print(f"timeline {TOTAL:.2f}s · {NFRAMES} frames · {len(R.EVENTS)} ASS events · {len(B3.SFX)} sfx cues · {len(HEROES)} heroes", flush=True)
    if "--ass-only" in sys.argv:
        return
    if "--reburn" in sys.argv:            # captions changed only: burn them onto the finished picture
        clean, mix = os.path.join(TMP, "v4_clean.mkv"), os.path.join(TMP, "mix_v4.wav")
        caps = os.path.join(OUT, "reel_v4_captions.ass").replace(":", r"\:")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clean, "-i", mix, "-map", "0:v", "-map", "1:a",
                        "-vf", f"ass={caps}:fontsdir={R.FONTS}", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                        "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p", "-r", str(FPS),
                        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                        "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
                        os.path.join(OUT, "reel_kita_hafucha_v4_mobile.mp4")], check=True)
        print("done: reburn", flush=True)
        return
    tracks = {s["id"]: R.track(s)[0] for s in SEGMENTS}
    if "--test" in sys.argv:
        sid = sys.argv[sys.argv.index("--test") + 1]
        idx = [int(v) for v in sys.argv[sys.argv.index("--test") + 2].split(",")]
        seg, td, studio = SEG[sid], tracks[sid], Studio()
        gpath = os.path.join(OUT, "reel_v4_graphics.ass")
        for i, fr in enumerate(R.read_segment(seg)):
            if i not in idx:
                continue
            t = seg["out_in"] + i / FPS
            z, dx = cam_at(sid, i / FPS)
            a2 = cv2.imread(os.path.join(MATTE, sid, f"{i:04d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            up2, a2d = presenter_2x(fr, a2, sid, i)
            gp = os.path.join(TMP, "g.rgba")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black@0.0:s={W}x{H}:r=30:d=0.1,format=rgba",
                            "-vf", f"setpts=PTS+{t}/TB,ass={gpath}:fontsdir={R.FONTS}:alpha=1", "-frames:v", "1",
                            "-f", "rawvideo", "-pix_fmt", "rgba", gp], check=True)
            f4 = np.fromfile(gp, np.uint8).reshape(H, W, 4)
            g = (f4[..., 2::-1].astype(np.float32), f4[..., 3:4].astype(np.float32) / 255) if f4[..., 3].any() else None
            img = assemble(studio, t, z, dx, up2, a2d, (td[0][i], td[1][i], td[2][i]), g, i)
            img = finish(img, g, i, 1 - t / 0.55 if t < 0.55 else 0.0)
            cv2.imwrite(os.path.join(TMP, f"test_{sid}_{i}.png"), np.clip(img, 0, 255).astype(np.uint8))
        return
    mix = render_audio()
    if "--audio-only" in sys.argv:
        clean = os.path.join(TMP, "v4_clean.mkv")
    else:
        clean = render(tracks)
    render_cover(tracks)
    final = os.path.join(OUT, "reel_kita_hafucha_v4.mp4")
    caps = os.path.join(OUT, "reel_v4_captions.ass").replace(":", r"\:")
    common = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", str(FPS),
              "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
              "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clean, "-i", mix, "-map", "0:v", "-map", "1:a",
                    "-vf", f"ass={caps}:fontsdir={R.FONTS}"] + common + [final], check=True)
    print("done:", final, flush=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clean, "-i", mix, "-map", "0:v", "-map", "1:a"] + common
                   + [os.path.join(OUT, "reel_kita_hafucha_v4_no_captions.mp4")], check=True)
    print("done: no-captions", flush=True)
    safe_zone_check(final)


if __name__ == "__main__":
    main()
