#!/usr/bin/env python3
"""
build_reel.py — "כיתה הפוכה – לומדים קשרים לוגיים"
Builds a vertical 1080x1920 reel from the original talking-head video.

Everything that is editable lives at the top of this file:
  SEGMENTS   – the cut list (source in/out, order, zoom keyframes)
  HIGHLIGHT  – keyword colours in the captions
  graphics() – every animated graphic, keyed to the spoken words
The word-level transcript is in transcript_words.json (source timestamps).

Outputs (in ./output):
  reel_kita_hafucha.mp4   final reel (burned captions + graphics)
  reel_kita_hafucha.srt   captions only
  reel_overlays.ass       captions + graphics (open/edit in Aegisub)
  cover.jpg               reel cover 1080x1920
  edit_decision_list.csv  timecodes of every cut

Usage:  python3 build_reel.py /path/to/source.mp4
Needs:  ffmpeg (libass, libx264), numpy, opencv-python-headless (<5, for Haar cascades), pillow
"""
import csv, json, math, os, subprocess, sys
import numpy as np
import cv2
from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
OUT = os.path.join(HERE, "output")
TMP = os.path.join(OUT, "_tmp")
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "source.mp4")

W, H, FPS = 1080, 1920, 30
SW, SH = 478, 850                       # source frame size
EYE_LINE = 0.40                         # eyes at 40% of frame height
END_CARD = 2.6                          # seconds

# Brand palette (ASS colours are &HBBGGRR)
NAVY, NAVY2 = "&H3A1F0B&", "&H5A3414&"  # #0B1F3A, #14345A
TURQ, YELL, WHITE = "&HD6E62E&", "&H0AD6FF&", "&HFFFFFF&"  # #2EE6D6, #FFD60A

# ---------------------------------------------------------------- cut list
# Source times in seconds; cut points sit on silences in the source audio.
# zoom = [(seconds from segment start, zoom factor)], eased between keys.
SEGMENTS = [
    dict(id="H", src_in=46.62, src_out=61.92,      # hook + why
         zoom=[(0, 1.10), (15.3, 1.20)]),
    dict(id="M", src_in=15.85, src_out=27.40,      # what the model is
         zoom=[(0, 1.08), (11.55, 1.12)]),
    dict(id="A", src_in=62.15, src_out=78.50,      # the aspiration
         zoom=[(0, 1.14), (16.35, 1.20)]),
    dict(id="T", src_in=27.42, src_out=31.22,      # next topic: logical connectors
         zoom=[(0, 1.14), (2.25, 1.14), (2.6, 1.24), (3.8, 1.25)]),
    dict(id="C", src_in=80.12, src_out=87.72,      # no excuses, I'm available
         zoom=[(0, 1.10), (1.3, 1.10), (1.65, 1.18), (7.6, 1.20)]),
    dict(id="E", src_in=97.70, src_out=99.95,      # closing line
         zoom=[(0, 1.16), (2.25, 1.22)]),
]

# Keyword colouring in captions (sequences of words, matched without punctuation)
HIGHLIGHT = [
    (["כיתה", "הפוכה"], YELL), (["קשרים", "לוגיים"], YELL),
    (["למידה", "עצמאית"], TURQ), (["כלומדים", "עצמאיים"], TURQ),
    (["בכוחות", "עצמכם"], TURQ), (["אין", "דבר", "כזה"], YELL),
]

# Caption lines, in reel order (each segment's words are consumed line by line).
CAPTION_LINES = {
    "H": ["הסיבה שאני עושה כיתה הפוכה", "זה לא כדי להקשות עליכם,", "אלא כדי להכין אתכם",
          "למיומנות הנדרשת שלכם", "כלומדים עצמאיים", "בלמידה מקוונת,", "רוב האוניברסיטאות,",
          "רוב המכללות", "יהיו לכם קורסים מקוונים."],
    "M": ["מודל כיתה הפוכה זה חומר", "שאתם לומדים אותו בבית,", "אתם מגיעים לכיתה,", "ובכיתה עצמה,",
          "אני עושה תרגול וחזרה,", "ואתם נבדקים במבדק קצר", "של עשר שאלות."],
    "A": ["והשאיפה שלי זה", "שיהיה לכם את המיומנות הזו", "של למידה עצמאית בבית,", "שמגיעים עם למידה",
          "שלמדתם בכוחות עצמכם", "ובכיתה תרגול ומבדק,", "בלי למידה של החומר."],
    "T": ["והנושא הבא של כיתה הפוכה", "זה קשרים לוגיים."],
    "C": ["וגם חשוב לי לומר:", "אין דבר כזה", "לא ידעתי, לא שמעתי,", "לא עשיתי,", "אני זמין לשאלות."],
    "E": ["אז כיתה הפוכה מהנה!"],
}
CAP_SIZE, CAP_MAX_W = 78, 840          # shrink a line rather than wrap it

# ---------------------------------------------------------------- timeline
def frames(sec):
    return int(round(sec * FPS))

t = 0.0
for s in SEGMENTS:
    s["nf"] = frames(s["src_out"] - s["src_in"])
    s["dur"] = s["nf"] / FPS
    s["out_in"] = t
    t += s["dur"]
VOICE_END = t
TOTAL = VOICE_END + END_CARD
SEG = {s["id"]: s for s in SEGMENTS}


def o(seg_id, src_t):
    """Map a source time inside a segment to the output timeline."""
    s = SEG[seg_id]
    return s["out_in"] + min(max(src_t - s["src_in"], 0), s["dur"])


def ease(a):
    return a * a * (3 - 2 * a)


def zoom_at(seg, lt):
    k = seg["zoom"]
    if lt <= k[0][0]:
        return k[0][1]
    for (t0, z0), (t1, z1) in zip(k, k[1:]):
        if lt <= t1:
            return z0 + (z1 - z0) * ease((lt - t0) / max(t1 - t0, 1e-6))
    return k[-1][1]


# ---------------------------------------------------------------- ASS helpers
def ts(sec):
    sec = max(sec, 0)
    cs = int(round(sec * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


EVENTS = []


def ev(layer, start, end, text, style="G"):
    EVENTS.append(f"Dialogue: {layer},{ts(start)},{ts(end)},{style},,0,0,0,,{text}")


_font_cache = {}


def text_w(text, size, weight="900Black"):
    """Pixel width of text as libass renders it (ASS size = ascent+descent)."""
    key = (size, weight)
    if key not in _font_cache:
        path = os.path.join(FONTS, f"Heebo_{weight}.ttf")
        probe = ImageFont.truetype(path, 1000)
        a, d = probe.getmetrics()
        _font_cache[key] = ImageFont.truetype(path, max(1, round(size * 1000 / (a + d))))
    return _font_cache[key].getlength(text)


def rrect(w, h, r):
    """Rounded rectangle drawing, origin top-left."""
    k = r * 0.45
    return (f"m {r} 0 l {w - r} 0 b {w - k} 0 {w} {k} {w} {r} l {w} {h - r} "
            f"b {w} {h - k} {w - k} {h} {w - r} {h} l {r} {h} b {k} {h} 0 {h - k} 0 {h - r} "
            f"l 0 {r} b 0 {k} {k} 0 {r} 0")


POP = r"\fscx70\fscy70\t(0,220,0.5,\fscx104\fscy104)\t(220,320,\fscx100\fscy100)"


def pill(start, end, cx, cy, text, size=46, fg=WHITE, bg=NAVY, alpha="&H18&",
         pad_x=34, h=None, layer=10, weight="800ExtraBold", border=None, anim=POP, fade=(140, 160)):
    """Rounded label with centred text. Returns its width."""
    w = int(text_w(text, size, weight) + 2 * pad_x)
    h = h or int(size * 1.55)
    b = f"\\bord3\\3c{border}" if border else "\\bord0"
    ev(layer, start, end, f"{{\\an5\\pos({cx},{cy}){b}\\shad0\\1c{bg}\\1a{alpha}"
                          f"\\fad({fade[0]},{fade[1]}){anim}\\p1}}{rrect(w, h, h // 2)}")
    font = "Heebo Black" if weight == "900Black" else "Heebo ExtraBold"
    ev(layer + 1, start, end, f"{{\\an5\\pos({cx},{cy + 2})\\fn{font}\\fs{size}\\1c{fg}\\bord0\\shad0"
                              f"\\fad({fade[0]},{fade[1]}){anim}}}{text}")
    return w


def card(start, end, cx, cy, w, h, title, sub=None, sub_start=None, icon=None, layer=10,
         title_col=WHITE, sub_col=TURQ):
    ev(layer, start, end, f"{{\\an5\\pos({cx},{cy})\\bord3\\3c{TURQ}\\3a&H40&\\shad0\\1c{NAVY}\\1a&H14&"
                          f"\\fad(150,160){POP}\\p1}}{rrect(w, h, 34)}")
    ty = cy - (26 if sub else 0)
    tx = cx + (28 if icon else 0)
    ev(layer + 1, start, end, f"{{\\an5\\pos({tx},{ty})\\fnHeebo Black\\fs58\\1c{title_col}\\bord0\\shad0"
                              f"\\fad(150,160){POP}}}{title}")
    if icon:
        ix = tx + int(text_w(title, 58)) // 2 + 46
        icon(start, end, ix, ty, layer + 1)
    if sub:
        ss = sub_start if sub_start is not None else start
        ev(layer + 1, ss, end, f"{{\\an5\\pos({cx},{cy + 40})\\fnHeebo ExtraBold\\fs38\\1c{sub_col}\\bord0\\shad0"
                               f"\\fad(180,160)\\fscx85\\fscy85\\t(0,200,\\fscx100\\fscy100)}}{sub}")


def icon_house(start, end, x, y, layer):
    d = "m 0 22 l 30 -4 l 60 22 l 52 22 l 52 56 l 8 56 l 8 22 m 24 56 l 24 36 l 36 36 l 36 56"
    ev(layer, start, end, f"{{\\an7\\pos({x - 30},{y - 30})\\bord0\\shad0\\1c{YELL}\\fad(150,160)\\p1}}{d}")


def icon_board(start, end, x, y, layer):
    d = ("m 0 0 l 60 0 l 60 40 l 0 40 l 0 0 m 6 6 l 6 34 l 54 34 l 54 6 "
         "m 26 40 l 34 40 l 40 54 l 34 54 l 30 46 l 26 54 l 20 54")
    ev(layer, start, end, f"{{\\an7\\pos({x - 30},{y - 28})\\bord0\\shad0\\1c{YELL}\\fad(150,160)\\p1}}{d}")


def icon_check(start, end, x, y, layer, col=NAVY):
    d = "m 0 22 l 9 13 l 20 24 l 43 0 l 52 9 l 20 41"
    ev(layer, start, end, f"{{\\an5\\pos({x},{y})\\bord0\\shad0\\1c{col}\\fad(120,120){POP}\\p1}}{d}")


def arrow_left(start, end, cx, cy, length=90, layer=10, col=YELL):
    """Arrow pointing left (RTL flow), drawn in with a growing clip."""
    L = length
    d = f"m {L} 8 l 26 8 l 26 0 l 0 14 l 26 28 l 26 20 l {L} 20"
    x0, y0 = cx - L // 2, cy - 14
    ev(layer, start, end, f"{{\\an7\\pos({x0},{y0})\\bord0\\shad0\\1c{col}\\fad(0,160)"
                          f"\\clip({x0 + L},{y0 - 5},{x0 + L},{y0 + 35})"
                          f"\\t(0,260,\\clip({x0},{y0 - 5},{x0 + L},{y0 + 35}))\\p1}}{d}")


def line(start, end, x1, y1, x2, y2, width=6, col=TURQ, grow=260, layer=9, alpha="&H00&"):
    """Straight connector that 'draws' itself from (x1,y1) to (x2,y2)."""
    ang = math.atan2(y2 - y1, x2 - x1)
    nx, ny = -math.sin(ang) * width / 2, math.cos(ang) * width / 2
    pts = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
    d = "m " + " l ".join(f"{px:.0f} {py:.0f}" for px, py in pts)
    bx0, by0 = min(x1, x2) - 10, min(y1, y2) - 10
    bx1, by1 = max(x1, x2) + 10, max(y1, y2) + 10
    if x2 >= x1:
        c0, c1 = f"\\clip({bx0},{by0},{bx0 + 1},{by1})", f"\\clip({bx0},{by0},{bx1},{by1})"
    else:
        c0, c1 = f"\\clip({bx1 - 1},{by0},{bx1},{by1})", f"\\clip({bx0},{by0},{bx1},{by1})"
    if abs(x2 - x1) < 20:  # vertical-ish: grow top-down
        c0, c1 = f"\\clip({bx0},{by0},{bx1},{by0 + 1})", f"\\clip({bx0},{by0},{bx1},{by1})"
    ev(layer, start, end, f"{{\\an7\\pos(0,0)\\bord0\\shad0\\1c{col}\\1a{alpha}\\fad(0,160)"
                          f"{c0}\\t(0,{grow},{c1})\\p1}}{d}")


def strike(start, end, cx, cy, w, layer=14):
    x0 = cx + w // 2   # strike runs right-to-left, like reading
    d = f"m 0 0 l {w} 0 l {w} 9 l 0 9"
    ev(layer, start, end, f"{{\\an7\\pos({cx - w // 2},{cy - 4})\\bord0\\shad0\\1c{YELL}\\fad(0,160)"
                          f"\\clip({x0 - 1},{cy - 12},{x0},{cy + 12})"
                          f"\\t(0,240,\\clip({cx - w // 2},{cy - 12},{x0},{cy + 12}))\\p1}}{d}")


# ---------------------------------------------------------------- graphics
def graphics():
    # Graphics live in the band above the head (y≈130-470): the face stays clear.
    # ---- H: hook title
    a, b = 0.0, o("H", 51.15)
    ev(10, a, b, f"{{\\an5\\pos(540,250)\\bord0\\shad0\\1c{NAVY}\\1a&H10&\\fad(0,180){POP}\\p1}}{rrect(820, 150, 75)}")
    ev(11, a, b, f"{{\\an5\\pos(540,253)\\fnHeebo Black\\fs86\\bord0\\shad0\\fad(0,180){POP}}}"
                 f"למה {{\\1c{YELL}}}כיתה הפוכה{{\\1c{WHITE}}}?")
    ev(11, a + 0.25, b, f"{{\\an5\\pos(540,340)\\bord0\\shad0\\1c{TURQ}\\fad(0,180)"
                        f"\\clip(540,330,540,350)\\t(0,350,\\clip(330,330,750,350))\\p1}}m -200 0 l 200 0 l 200 8 l -200 8")
    # ---- H: the skill
    a, b = o("H", 54.35), o("H", 57.45)
    ev(10, a, b, f"{{\\an5\\pos(540,290)\\bord3\\3c{TURQ}\\3a&H40&\\shad0\\1c{NAVY}\\1a&H14&\\fad(150,160){POP}\\p1}}{rrect(760, 250, 40)}")
    ev(11, a, b, f"{{\\an5\\pos(540,215)\\fnHeebo ExtraBold\\fs40\\1c{TURQ}\\bord0\\shad0\\fad(150,160)}}המיומנות הנדרשת")
    ev(11, o("H", 55.2), b, f"{{\\an5\\pos(540,290)\\fnHeebo Black\\fs72\\1c{YELL}\\bord0\\shad0\\fad(150,160){POP}}}לומדים עצמאיים")
    ev(11, o("H", 56.25), b, f"{{\\an5\\pos(540,365)\\fnHeebo ExtraBold\\fs42\\1c{WHITE}\\bord0\\shad0"
                             f"\\fad(150,160)\\fscx85\\fscy85\\t(0,200,\\fscx100\\fscy100)}}בלמידה מקוונת")
    # ---- H: universities + colleges -> online courses (addition)
    b = o("H", 61.92)
    y = 300
    pill(o("H", 58.1), b, 820, y, "אוניברסיטאות", size=44)
    ev(12, o("H", 59.05), b, f"{{\\an5\\pos(655,{y})\\fnHeebo Black\\fs64\\1c{YELL}\\bord0\\shad0\\fad(120,160){POP}}}+")
    pill(o("H", 59.1), b, 530, y, "מכללות", size=44)
    arrow_left(o("H", 60.4), b, 402, y, length=70)
    pill(o("H", 60.6), b, 210, y, "קורסים מקוונים", size=40, fg=NAVY, bg=TURQ, alpha="&H00&", pad_x=26)

    # ---- M: the flipped-classroom model
    b = o("M", 27.40)
    pill(o("M", 15.95), b, 540, 160, "מודל כיתה הפוכה", size=40, fg=NAVY, bg=YELL, alpha="&H00&")
    card(o("M", 18.4), b, 785, 320, 400, 190, "בבית", "לומדים את החומר", icon=icon_house)
    arrow_left(o("M", 19.85), b, 540, 320, length=80)
    card(o("M", 20.05), b, 295, 320, 400, 190, "בכיתה", "תרגול וחזרה", sub_start=o("M", 23.05), icon=icon_board)
    pill(o("M", 24.75), b, 295, 445, "מבדק קצר · 10 שאלות", size=34, fg=NAVY, bg=YELL, alpha="&H00&", pad_x=24, layer=14)

    # ---- A: the aspiration
    a, b = o("A", 65.85), o("A", 69.55)
    ev(10, a, b, f"{{\\an5\\pos(540,290)\\bord3\\3c{TURQ}\\3a&H40&\\shad0\\1c{NAVY}\\1a&H14&\\fad(150,160){POP}\\p1}}{rrect(780, 230, 40)}")
    ev(11, a, b, f"{{\\an5\\pos(540,225)\\fnHeebo ExtraBold\\fs40\\1c{TURQ}\\bord0\\shad0\\fad(150,160)}}השאיפה שלי")
    ev(11, o("A", 66.75), b, f"{{\\an5\\pos(540,305)\\fnHeebo Black\\fs70\\1c{YELL}\\bord0\\shad0\\fad(150,160){POP}}}למידה עצמאית")
    a, b = o("A", 70.4), o("A", 78.50)
    pill(a, b, 770, 300, "לומדים בבית", size=44)
    icon_check(o("A", 72.0), b, 770, 380, 13, col=TURQ)
    arrow_left(o("A", 72.55), b, 560, 300, length=80)
    pill(o("A", 72.7), b, 330, 300, "בכיתה: תרגול ומבדק", size=44, fg=NAVY, bg=TURQ, alpha="&H00&")

    # ---- T: logical connectors (central node + connected ideas); held through "וגם חשוב לי לומר"
    b = o("C", 81.45)
    pill(o("T", 27.5), b, 540, 150, "הנושא הבא", size=38, fg=NAVY, bg=TURQ, alpha="&H00&", pad_x=28)
    pill(o("T", 29.8), b, 540, 250, "קשרים לוגיים", size=64, fg=NAVY, bg=YELL, alpha="&H00&", weight="900Black", layer=12)
    sats = [(850, "סיבה ותוצאה"), (540, "ניגוד"), (230, "הוספה")]
    for i, (sx, label) in enumerate(sats):
        st = o("T", 30.05) + 0.16 * i
        line(st, b, 540, 295, sx, 375, width=6)
        pill(st + 0.1, b, sx, 405, label, size=40, border=TURQ, layer=10)

    # ---- C: no excuses
    b = o("C", 85.62)
    ev(11, o("C", 81.5), b, f"{{\\an5\\pos(540,165)\\fnHeebo Black\\fs56\\1c{WHITE}\\bord0\\shad0\\fad(150,160){POP}}}"
                             f"אין דבר כזה:")
    items = [(845, "לא ידעתי", 82.36, 83.02), (540, "לא שמעתי", 83.30, 84.10), (235, "לא עשיתי", 84.52, 85.42)]
    for cx, label, s0, s1 in items:
        w = pill(o("C", s0), b, cx, 290, label, size=46)
        strike(o("C", s1) - 0.05, b, cx, 290, w - 30)
    a, b = o("C", 85.70), o("C", 87.72)
    w = pill(a, b, 540, 280, "אני זמין לשאלות", size=56, fg=NAVY, bg=TURQ, alpha="&H00&", weight="900Black", pad_x=40)
    icon_check(a + 0.15, b, 540 + w // 2 - 2, 200, 13, col=YELL)

    # ---- End card
    a, b = VOICE_END, TOTAL
    ev(21, a + 0.15, b, f"{{\\an5\\pos(540,820)\\fnHeebo Black\\fs132\\1c{YELL}\\bord0\\shad0\\fad(250,0)"
                        f"\\fscx80\\fscy80\\t(0,300,0.5,\\fscx100\\fscy100)}}כיתה הפוכה")
    ev(21, a + 0.45, b, f"{{\\an5\\pos(540,975)\\fnHeebo Black\\fs62\\1c{WHITE}\\bord0\\shad0\\fad(250,0)}}"
                        f"חושבים, מקשרים")
    ev(21, a + 0.75, b, f"{{\\an5\\pos(540,1060)\\fnHeebo Black\\fs62\\1c{TURQ}\\bord0\\shad0\\fad(250,0)}}"
                        f"ולומדים אחרת!")
    # three connected nodes motif
    for i, x in enumerate((360, 540, 720)):
        ev(20, a + 0.3 + 0.15 * i, b, f"{{\\an5\\pos({x},1190)\\bord0\\shad0\\1c{YELL if i == 1 else TURQ}"
                                      f"\\fad(150,0){POP}\\p1}}m 0 -16 b 9 -16 16 -9 16 0 b 16 9 9 16 0 16 b -9 16 -16 9 -16 0 b -16 -9 -9 -16 0 -16")
    line(a + 0.35, b, 720, 1190, 360, 1190, width=5, col=WHITE, grow=500, layer=19, alpha="&H40&")


# ---------------------------------------------------------------- captions
def clean(w):
    return w.strip(",.:!?\"'")


def build_captions(words):
    chunks = []
    for s in SEGMENTS:
        ws = [w for w in words if s["src_in"] <= (w["s"] + w["e"]) / 2 <= s["src_out"]]
        k = 0
        for line in CAPTION_LINES[s["id"]]:
            n = len(line.split())
            cur = ws[k:k + n]
            got = " ".join(w["w"] for w in cur)
            assert got == line, f"caption mismatch in {s['id']}: {got!r} != {line!r}"
            chunks.append(dict(seg=s["id"], words=cur))
            k += n
        assert k == len(ws), f"segment {s['id']} has uncaptioned words: {ws[k:]}"
    for i, c in enumerate(chunks):
        s = c["seg"]
        c["start"] = o(s, c["words"][0]["s"] - 0.06)
        c["end"] = o(s, c["words"][-1]["e"] + 0.25)
        if i + 1 < len(chunks) and chunks[i + 1]["seg"] == s:
            nstart = o(s, chunks[i + 1]["words"][0]["s"] - 0.06)
            c["end"] = nstart if nstart - c["end"] < 0.6 else min(c["end"], nstart)
        c["end"] = min(c["end"], SEG[s]["out_in"] + SEG[s]["dur"])
    return chunks


def styled(words):
    toks = [w["w"] for w in words]
    cols = [None] * len(toks)
    for phrase, col in HIGHLIGHT:
        n = len(phrase)
        for i in range(len(toks) - n + 1):
            if [clean(x) for x in toks[i:i + n]] == phrase:
                for k in range(n):
                    cols[i + k] = col
    out = []
    for tok, col in zip(toks, cols):
        out.append(f"{{\\1c{col}}}{tok}{{\\1c{WHITE}}}" if col else tok)
    return " ".join(out)


def srt_time(sec):
    ms = int(round(sec * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_subs(chunks):
    with open(os.path.join(OUT, "reel_kita_hafucha.srt"), "w", encoding="utf-8") as f:
        for i, c in enumerate(chunks, 1):
            f.write(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n"
                    f"{' '.join(w['w'] for w in c['words'])}\n\n")
    for c in chunks:
        txt = " ".join(w["w"] for w in c["words"])
        size = min(CAP_SIZE, int(CAP_SIZE * CAP_MAX_W / max(text_w(txt, CAP_SIZE), 1)))
        ev(30, c["start"], c["end"],
           rf"{{\an2\pos(540,1395)\fs{size}\fad(70,50)\fscx92\fscy92\t(0,130,\fscx100\fscy100)}}" + styled(c["words"]),
           style="Cap")
    head = f"""[Script Info]
Title: כיתה הפוכה – לומדים קשרים לוגיים
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Heebo Black,78,&H00FFFFFF,&H00FFFFFF,&H003A1F0B,&H96000000,0,0,0,0,100,100,0,0,1,6,3,2,150,170,0,-1
Style: G,Heebo ExtraBold,48,&H00FFFFFF,&H00FFFFFF,&H003A1F0B,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(os.path.join(OUT, "reel_overlays.ass"), "w", encoding="utf-8") as f:
        f.write(head + "\n".join(EVENTS) + "\n")


# ---------------------------------------------------------------- face tracking
CASCADE = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
DECODE_VF = "hqdn3d=2:1.5:4:3,eq=contrast=1.07:brightness=0.025:saturation=1.07:gamma=1.04," \
            "colorbalance=rs=-0.03:bs=0.03:rm=-0.02:bm=0.02:rh=-0.01:bh=0.01"


def read_segment(seg, vf=DECODE_VF):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{seg['src_in']:.3f}", "-i", SRC, "-t", f"{seg['dur']:.3f}",
           "-vf", f"fps={FPS},{vf}", "-frames:v", str(seg["nf"]), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = 0
    while n < seg["nf"]:
        buf = p.stdout.read(SW * SH * 3)
        if len(buf) < SW * SH * 3:
            break
        last = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
        yield last
        n += 1
    while n < seg["nf"]:          # pad (never expected, keeps A/V length exact)
        yield last
        n += 1
    p.stdout.close()
    p.wait()


def smooth(v, sigma):
    r = int(sigma * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(v, r, mode="edge"), k, mode="valid")


def track(seg):
    cx, ey, fw = [], [], []
    for i, fr in enumerate(read_segment(seg, vf="null")):
        if i % 2:
            cx.append(np.nan); ey.append(np.nan); fw.append(np.nan)
            continue
        g = cv2.equalizeHist(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY))
        f = CASCADE.detectMultiScale(g, 1.1, 5, minSize=(60, 60))
        if len(f):
            x, y, w, h = max(f, key=lambda r: r[2] * r[3])
            cx.append(x + w / 2); ey.append(y + 0.42 * h); fw.append(w)
        else:
            cx.append(np.nan); ey.append(np.nan); fw.append(np.nan)
    hit = float(np.mean(~np.isnan(np.array(cx[::2], float))))
    res = []
    for v, default in ((cx, SW / 2), (ey, SH * 0.39), (fw, 120)):
        v = np.array(v, float)
        ok = ~np.isnan(v)
        v = np.interp(np.arange(len(v)), np.where(ok)[0], v[ok]) if ok.any() else np.full(len(v), default)
        res.append(smooth(v, sigma=14))   # ~0.5 s: steady, no jitter
    return res, hit


# ---------------------------------------------------------------- render
def face_light(cx, cy, fw):
    gx = np.exp(-0.5 * ((np.arange(W) - cx) / (fw * 1.1)) ** 2)
    gy = np.exp(-0.5 * ((np.arange(H) - cy) / (fw * 1.5)) ** 2)
    return (1.0 + 0.07 * np.outer(gy, gx))[..., None].astype(np.float32)


_yy = np.arange(H, dtype=np.float32)
TOP_BAND = (0.45 * np.clip(1 - _yy / 640, 0, 1) ** 1.6)[:, None, None]   # navy wash behind graphics
NAVY_BGR = np.array([58, 31, 11], np.float32)


def window(seg, i, track_data):
    (tcx, tey, tfw) = track_data
    z = zoom_at(seg, i / FPS)
    ww, wh = SW / z, SH / z
    x0 = float(np.clip(tcx[i] - ww / 2, 0, SW - ww))
    y0 = float(np.clip(tey[i] - EYE_LINE * wh, 0, SH - wh))
    return z, x0, y0


def render_video(tracks):
    os.makedirs(TMP, exist_ok=True)
    silent = os.path.join(TMP, "video_noaudio.mkv")
    ass = os.path.join(OUT, "reel_overlays.ass").replace(":", r"\:")
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
         "-i", "-", "-vf", f"unsharp=5:5:0.55:5:5:0,vignette=angle=0.42,ass={ass}:fontsdir={FONTS}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", silent],
        stdin=subprocess.PIPE)
    last = None
    for seg in SEGMENTS:
        td = tracks[seg["id"]]
        for i, fr in enumerate(read_segment(seg)):
            z, x0, y0 = window(seg, i, td)
            s = W / (SW / z)
            M = np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]])
            out = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
            fx, fy = (td[0][i] - x0) * s, (td[1][i] - y0) * s
            out = out.astype(np.float32) * face_light(fx, fy, td[2][i] * s)
            out = np.clip(out * (1 - TOP_BAND) + NAVY_BGR * TOP_BAND, 0, 255).astype(np.uint8)
            enc.stdin.write(out.tobytes())
            last = out
        print(f"  rendered segment {seg['id']} ({seg['nf']} frames)", flush=True)
    # end card: last frame -> blurred, navy-tinted background
    navy = np.zeros_like(last); navy[:] = (58, 31, 11)
    blurred = cv2.GaussianBlur(last, (0, 0), 28)
    bg = cv2.addWeighted(blurred, 0.30, navy, 0.70, 0)
    nf = frames(END_CARD)
    for i in range(nf):
        a = ease(min(i / (0.35 * FPS), 1.0))
        enc.stdin.write(cv2.addWeighted(last, 1 - a, bg, a, 0).tobytes())
    enc.stdin.close()
    enc.wait()
    return silent


def make_music(path, dur, sr=48000):
    """Original ambient pad (generated here, royalty-free)."""
    t = np.arange(int(dur * sr)) / sr
    chords = [[57, 60, 64, 71], [53, 57, 60, 64], [48, 55, 60, 64], [55, 59, 62, 67]]  # Am9 Fmaj7 C G
    bar = 4 * 60 / 76
    L = np.zeros_like(t); R = np.zeros_like(t)
    for ci in range(int(dur / bar) + 1):
        notes = chords[ci % 4]
        t0 = ci * bar
        m = (t >= t0) & (t < t0 + bar + 1.5)
        tt = t[m] - t0
        env = np.minimum(tt / 1.2, 1) * np.where(tt > bar, np.exp(-(tt - bar) * 2.5), 1)
        for n in notes:
            f = 440 * 2 ** ((n - 69) / 12)
            L[m] += env * (np.sin(2 * np.pi * f * 0.998 * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) / len(notes)
            R[m] += env * (np.sin(2 * np.pi * f * 1.002 * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) / len(notes)
        for k in range(8):                       # soft plucked arpeggio
            n = notes[k % 4] + 12
            f = 440 * 2 ** ((n - 69) / 12)
            ts0 = t0 + k * bar / 8
            mm = (t >= ts0) & (t < ts0 + 1.2)
            tt = t[mm] - ts0
            p = 0.22 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 4.5) * np.minimum(tt / 0.005, 1)
            pan = 0.35 + 0.3 * (k % 2)
            L[mm] += p * (1 - pan); R[mm] += p * pan
    st = np.stack([L, R], 1)
    fade = np.minimum(1, t / 1.0) * np.minimum(1, (dur - t) / 1.6)
    st *= fade[:, None]
    st /= np.abs(st).max() + 1e-9
    st = (st * 0.6 * 32767).astype(np.int16)
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(st.tobytes())


def render_audio():
    parts, labels = [], []
    for k, s in enumerate(SEGMENTS):
        parts.append(f"[0:a]atrim={s['src_in']:.4f}:{s['src_in'] + s['dur']:.4f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.02,afade=t=out:st={s['dur'] - 0.03:.4f}:d=0.03[a{k}]")
        labels.append(f"[a{k}]")
    chain = ("highpass=f=85,lowpass=f=13000,afftdn=nr=14:nf=-38:tn=1,"
             "equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.5:g=2.5,"
             "acompressor=threshold=-22dB:ratio=3:attack=8:release=160:makeup=2,"
             f"apad=whole_dur={TOTAL:.4f}")
    fc = ";".join(parts) + f";{''.join(labels)}concat=n={len(SEGMENTS)}:v=0:a=1,{chain}"
    pre = os.path.join(TMP, "voice_pre.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", SRC, "-filter_complex", fc, "-ar", "48000", "-ac", "2", pre], check=True)
    # two-pass loudness normalisation to -14 LUFS (social platforms)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-15:TP=-1.5:LRA=8:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(r[r.rfind("{"):r.rfind("}") + 1])
    voice = os.path.join(TMP, "voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", pre, "-af",
                    f"loudnorm=I=-15:TP=-1.5:LRA=8:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                    f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
                    "-ar", "48000", voice], check=True)
    music = os.path.join(TMP, "music.wav")
    make_music(music, TOTAL)
    mix = os.path.join(TMP, "mix.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-i", music, "-filter_complex",
                    "[1:a]volume=-18dB[m];[0:a]asplit=2[v][sc];"
                    "[m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=40:release=500[md];"
                    "[v][md]amix=inputs=2:normalize=0,alimiter=limit=0.78",
                    "-ar", "48000", "-t", f"{TOTAL:.4f}", mix], check=True)
    return mix


def render_cover(tracks, src_t=85.9, seg_id="C"):
    seg = SEG[seg_id]
    i = frames(src_t - seg["src_in"])
    for k, fr in enumerate(read_segment(seg)):
        if k == i:
            break
    td = tracks[seg_id]
    z = 1.16
    ww, wh = SW / z, SH / z
    x0 = float(np.clip(td[0][i] - ww / 2, 0, SW - ww)); y0 = float(np.clip(td[1][i] - 0.36 * wh, 0, SH - wh))
    s = W / ww
    out = cv2.warpAffine(fr, np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]]), (W, H), flags=cv2.INTER_LANCZOS4)
    out = np.clip(out.astype(np.float32) * face_light((td[0][i] - x0) * s, (td[1][i] - y0) * s, td[2][i] * s), 0, 255).astype(np.uint8)
    # navy gradient at the bottom for the title
    g = np.clip((np.arange(H) - 980) / 480, 0, 1)[:, None, None] * 0.86
    g = np.maximum(g, TOP_BAND)
    out = (out * (1 - g) + NAVY_BGR * g).astype(np.uint8)
    raw = os.path.join(TMP, "cover_bg.png")
    cv2.imwrite(raw, out)
    cass = os.path.join(TMP, "cover.ass")
    dot = "m 0 -16 b 9 -16 16 -9 16 0 b 16 9 9 16 0 16 b -9 16 -16 9 -16 0 b -16 -9 -9 -16 0 -16"
    with open(cass, "w", encoding="utf-8") as f:
        f.write(open(os.path.join(OUT, "reel_overlays.ass"), encoding="utf-8").read().split("[Events]")[0])
        f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        # keep the title inside the centre 3:4 crop (y 240..1680) used by the profile grid
        def d(layer, body):
            f.write(f"Dialogue: {layer},0:00:00.00,0:00:05.00,G,,0,0,0,,{body}\n")
        d(2, f"{{\\an5\\pos(540,1270)\\fnHeebo Black\\fs150\\1c{YELL}\\bord6\\3c{NAVY}\\shad0}}כיתה הפוכה:")
        d(2, f"{{\\an5\\pos(540,1420)\\fnHeebo Black\\fs104\\1c{WHITE}\\bord5\\3c{NAVY}\\shad0}}לומדים")
        d(2, f"{{\\an5\\pos(540,1535)\\fnHeebo Black\\fs104\\1c{TURQ}\\bord5\\3c{NAVY}\\shad0}}קשרים לוגיים")
        d(1, f"{{\\an7\\pos(420,1638)\\bord0\\shad0\\1c{WHITE}\\1a&H50&\\p1}}m 0 0 l 240 0 l 240 4 l 0 4")
        for k, x in enumerate((420, 540, 660)):
            d(2, f"{{\\an5\\pos({x},1640)\\bord0\\shad0\\1c{YELL if k == 1 else TURQ}\\fscx70\\fscy70\\p1}}{dot}")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vf",
                    f"unsharp=5:5:0.55:5:5:0,ass={cass.replace(':', chr(92) + ':')}:fontsdir={FONTS}",
                    "-q:v", "2", os.path.join(OUT, "cover.jpg")], check=True)


def write_edl():
    with open(os.path.join(OUT, "edit_decision_list.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["#", "segment", "source_in", "source_out", "reel_in", "reel_out", "zoom"])
        for k, s in enumerate(SEGMENTS, 1):
            wr.writerow([k, s["id"], f"{s['src_in']:.2f}", f"{s['src_in'] + s['dur']:.2f}",
                         f"{s['out_in']:.2f}", f"{s['out_in'] + s['dur']:.2f}",
                         " → ".join(f"{z:.2f}" for _, z in s["zoom"])])
        wr.writerow([len(SEGMENTS) + 1, "END CARD", "", "", f"{VOICE_END:.2f}", f"{TOTAL:.2f}", ""])


def main():
    os.makedirs(TMP, exist_ok=True)
    words = json.load(open(os.path.join(HERE, "transcript_words.json"), encoding="utf-8"))["words"]
    graphics()
    write_subs(build_captions(words))
    write_edl()
    print(f"timeline: {VOICE_END:.2f}s speech + {END_CARD}s end card = {TOTAL:.2f}s")
    if "--subs-only" in sys.argv:
        return
    tracks = {}
    for s in SEGMENTS:
        tracks[s["id"]], hit = track(s)
        print(f"  face track {s['id']}: detected in {hit:.0%} of sampled frames", flush=True)
    render_cover(tracks)
    if "--cover-only" in sys.argv:
        return
    mix = render_audio()
    video = os.path.join(TMP, "video_noaudio.mkv") if "--audio-only" in sys.argv else render_video(tracks)
    final = os.path.join(OUT, "reel_kita_hafucha.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", mix, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    print("done:", final)


if __name__ == "__main__":
    main()
