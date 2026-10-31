#!/usr/bin/env python3
"""Word-box kinetic captions (ASS) for the v4 reel.

Every word is its own event, laid out right-to-left by measured widths, so each word can animate
on its own: the line slides in with all words dimmed, each word lights up exactly when it is
spoken, and a rounded box (yellow for words, cyan for lesson concepts) jumps from word to word
with a small bounce."""


def layout(words, size, text_w, gap_k=0.30, max_w=900):
    """returns (size, [x_center per word]) for one RTL line centred at x=540"""
    while True:
        ws = [text_w(w, size) for w in words]
        gap = size * gap_k
        total = sum(ws) + gap * (len(ws) - 1)
        if total <= max_w or size <= 56:
            break
        size -= 2
    x = 540 + total / 2                       # right edge: first (Hebrew) word starts here
    xs = []
    for w in ws:
        xs.append(x - w / 2)
        x -= w + gap
    return size, xs, ws


def rrect(w, h, r):
    k = r * 0.45
    return (f"m {r} 0 l {w - r} 0 b {w - k} 0 {w} {k} {w} {r} l {w} {h - r} "
            f"b {w} {h - k} {w - k} {h} {w - r} {h} l {r} {h} b {k} {h} 0 {h - k} 0 {h - r} "
            f"l 0 {r} b 0 {k} {k} 0 {r} 0")


def build(chunks, word_time, colour_of, ev, text_w, NAVY, WHITE, YELL, TURQ, y=1398, size0=78):
    """chunks: [{start, end, words:[{w,...}]}] in output time; word_time(w) -> (t_on, t_off) output time
    colour_of(i, chunk) -> ASS colour for a highlighted word or None"""
    for c in chunks:
        toks = [w["w"] for w in c["words"]]
        size, xs, ws = layout(toks, size0, text_w)
        st, en = c["start"], c["end"]
        ms = lambda t: max(int(round((t - st) * 1000)), 0)            # noqa: E731
        bh = int(size * 1.22)
        for i, (tok, x, w) in enumerate(zip(toks, xs, ws)):
            on, off = word_time(c["words"][i])
            nxt = word_time(c["words"][i + 1])[0] if i + 1 < len(toks) else en
            hl = colour_of(i, c)
            box_col = TURQ if hl == TURQ else YELL
            rest = hl or WHITE
            a0, a1 = ms(on), ms(min(nxt, en))
            stagger = i * 22
            # the word: dim on entry, lights up (navy on the box) while spoken, then settles
            ev(61, st, en,
               f"{{\\an5\\move({x:.0f},{y + 22},{x:.0f},{y},{stagger},{stagger + 170})\\fs{size}\\bord6\\shad3"
               f"\\3c{NAVY}\\1c{rest}\\alpha&HFF&\\t({stagger},{stagger + 140},\\alpha&H8C&)"
               f"\\t({a0},{a0 + 50},\\alpha&H00&\\1c{NAVY}\\3c{box_col}\\shad0\\fscx114\\fscy114)"
               f"\\t({a0 + 50},{a0 + 170},\\fscx104\\fscy104)"
               f"\\t({a1},{a1 + 70},\\1c{rest}\\3c{NAVY}\\shad3\\fscx100\\fscy100)\\fad(0,90)}}{tok}",
               style="Cap")
            # the active-word box
            bw = int(w * 1.06 + size * 0.52)
            ev(60, on, min(nxt, en),
               f"{{\\an5\\pos({x:.0f},{y + 2})\\bord0\\shad0\\1c{box_col}\\fscx70\\fscy70"
               f"\\t(0,70,\\fscx108\\fscy108)\\t(70,150,\\fscx100\\fscy100)\\fad(30,60)\\p1}}{rrect(bw, bh, bh // 2.6)}",
               style="Cap")
