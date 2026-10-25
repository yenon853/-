# Score for the Mekif Yud documentary short: 96 BPM, 24 bars = 60 s.
# Sections are locked to scene boundaries (bar = 2.5 s).
import mido

PPQ = 480
BEAT = PPQ
BAR = 4 * BEAT
mid = mido.MidiFile(ticks_per_beat=PPQ)

# note helpers
NAMES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
         "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def n(s):
    name, octv = s[:-1], int(s[-1])
    return 12 * (octv + 1) + NAMES[name]


events = []  # (tick, order, msg, channel)


def note(ch, pitch, start, dur, vel):
    p = n(pitch) if isinstance(pitch, str) else pitch
    events.append((int(start), 1, ("on", p, vel), ch))
    events.append((int(start + dur), 0, ("off", p, 0), ch))


def cc(ch, num, val, at):
    events.append((int(at), -1, ("cc", num, val), ch))


def prog(ch, program, at=0):
    events.append((int(at), -2, ("pc", program, 0), ch))


def bar(b, beat=0.0):
    """tick at bar b (1-based) plus beats"""
    return (b - 1) * BAR + beat * BEAT


# Channels
PIANO, STR, CELLO, TIMP, PAD, ARP, FX, BASS, CHOIR, HISTR, DR = 0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 9
prog(PIANO, 0); prog(STR, 48); prog(CELLO, 42); prog(TIMP, 47); prog(PAD, 89)
prog(ARP, 98); prog(FX, 119); prog(BASS, 38); prog(CHOIR, 52); prog(HISTR, 49)
for ch, vol, pan, rev in [(PIANO, 100, 58, 70), (STR, 92, 64, 90), (CELLO, 95, 70, 70),
                          (TIMP, 110, 64, 60), (PAD, 88, 64, 100), (ARP, 92, 50, 90),
                          (FX, 85, 64, 40), (BASS, 78, 64, 30), (CHOIR, 70, 64, 110),
                          (HISTR, 78, 54, 100), (DR, 100, 64, 45)]:
    cc(ch, 7, vol, 0); cc(ch, 10, pan, 0); cc(ch, 91, rev, 0); cc(ch, 93, 10, 0)

# Chord voicings (string pad, low root)
CH = {
    "Dm": (["D3", "A3", "D4", "F4", "A4"], "D2"),
    "Bb": (["Bb2", "F3", "D4", "F4", "Bb4"], "Bb1"),
    "F": (["F3", "C4", "F4", "A4", "C5"], "F2"),
    "F/A": (["A2", "F3", "C4", "F4", "A4"], "A1"),
    "C": (["C3", "G3", "E4", "G4", "C5"], "C2"),
    "Gm": (["G2", "D3", "Bb3", "D4", "G4"], "G1"),
    "A": (["A2", "E3", "C#4", "E4", "A4"], "A1"),
    "Asus": (["A2", "E3", "D4", "E4", "A4"], "A1"),
}
# arpeggio note sets for the piano ostinato
ARPN = {
    "Dm": ["D4", "A4", "F5", "A4", "D5", "A4", "F5", "A4"],
    "Bb": ["Bb3", "F4", "D5", "F4", "Bb4", "F4", "D5", "F4"],
    "F": ["F3", "C4", "A4", "C4", "F4", "C4", "A4", "C4"],
    "C": ["C4", "G4", "E5", "G4", "C5", "G4", "E5", "G4"],
    "Gm": ["G3", "D4", "Bb4", "D4", "G4", "D4", "Bb4", "D4"],
    "A": ["A3", "E4", "C#5", "E4", "A4", "E4", "C#5", "E4"],
    "F/A": ["A3", "F4", "C5", "F4", "A4", "F4", "C5", "F4"],
}

# Bar map: (bar, chord)
plan = {1: "Dm", 2: "Bb", 3: "F/A", 4: "Dm", 5: "Bb", 6: "F", 7: "C", 8: "Dm", 9: "Bb", 10: "C",
        11: "Dm", 12: "Bb", 13: "F", 14: "C", 15: "Gm", 16: "Bb", 17: "A", 18: "Dm", 19: "Dm",
        20: "Bb", 21: "C", 22: "Bb", 23: "F", 24: "F"}


def pad(b, chord, vel, bars=1, ch=STR):
    tones, _ = CH[chord]
    for t in tones:
        note(ch, t, bar(b), bars * BAR - 20, vel)


def root(b, chord, vel, ch=CELLO, bars=1):
    _, r = CH[chord]
    note(ch, r, bar(b), bars * BAR - 30, vel)


def ostinato(b, chord, vel, step=0.5, ch=PIANO, accent=12):
    seq = ARPN[chord]
    k = 0
    t = 0.0
    while t < 4.0 - 1e-6:
        v = vel + (accent if k % 4 == 0 else 0)
        note(ch, seq[k % len(seq)], bar(b, t), step * BEAT * 0.9, min(v, 127))
        k += 1
        t += step


# ---------- A: cold open (bars 1-3) — hook on frame one ----------
# impact on the very first downbeat, then an immediate pulse
note(TIMP, "D2", bar(1), 2 * BEAT, 120)
note(DR, 49, bar(1), 3 * BEAT, 112)
note(DR, 36, bar(1), BEAT, 124)
note(BASS, "D1", bar(1), 4 * BEAT, 90)
for t in ["D4", "F4", "A4"]:
    note(CHOIR, t, bar(1), 2 * BEAT, 78)
for b in (1, 2, 3):
    pad(b, plan[b], 44 + 6 * (b - 1))
    root(b, plan[b], 58)
    ostinato(b, plan[b] if plan[b] in ARPN else "F/A", 40 + 5 * (b - 1), step=0.5, accent=10)
    for beat in (0, 2):
        note(DR, 36, bar(b, beat), 0.4 * BEAT, 84 if b > 1 or beat else 0)
motif = [("A5", 0, 1.5), ("D6", 1.5, 1.0), ("E6", 2.5, 0.5), ("F6", 3.0, 1.0)]
for p, at, d in motif:
    note(HISTR, p, bar(2, at), d * BEAT, 70)
for p, at, d in [("E6", 0, 1.5), ("C6", 1.5, 1.0), ("A5", 2.5, 1.5)]:
    note(HISTR, p, bar(3, at), d * BEAT, 72)
# reverse cymbal swell into the zoom-through at 7.5 s
note(FX, "C4", bar(3, 1.0), 3.0 * BEAT, 78)
for i in range(8):
    note(DR, 38, bar(3, 2 + i * 0.25), 0.2 * BEAT, 50 + i * 8)

# ---------- B: the place (bars 4-7) ----------
for b in range(4, 8):
    c = plan[b]
    pad(b, c, 48 + 2 * (b - 4))
    root(b, c, 64)
    ostinato(b, c, 46 + 3 * (b - 4))
# melody (high strings) enters bar 6
for p, at, d in [("A5", 0, 2), ("G5", 2, 1), ("F5", 3, 1)]:
    note(HISTR, p, bar(6, at), d * BEAT, 60)
for p, at, d in [("E5", 0, 2), ("G5", 2, 2)]:
    note(HISTR, p, bar(7, at), d * BEAT, 64)
note(TIMP, "D2", bar(4), 2 * BEAT, 112)
note(DR, 49, bar(4), 2 * BEAT, 96)

# ---------- C: the number (bars 8-10) ----------
for b in range(8, 11):
    c = plan[b]
    pad(b, c, 58 + 4 * (b - 8))
    root(b, c, 74)
    ostinato(b, c, 54 + 4 * (b - 8), step=0.25, accent=14)
# timpani roll building into the 98% landing at bar 9 (20.0 s)
for i in range(16):
    note(TIMP, "D2", bar(8, i * 0.25), 0.22 * BEAT, 30 + i * 4)
note(TIMP, "A1", bar(9), 2 * BEAT, 118)
note(DR, 49, bar(9), 2 * BEAT, 110)  # crash
note(DR, 36, bar(9), BEAT, 120)
note(TIMP, "A1", bar(10), BEAT, 92)
for p, at, d in [("D6", 0, 2), ("C6", 2, 1), ("A5", 3, 1)]:
    note(HISTR, p, bar(9, at), d * BEAT, 72)
for p, at, d in [("G5", 0, 2), ("E5", 2, 2)]:
    note(HISTR, p, bar(10, at), d * BEAT, 70)

# ---------- D: the tracks (bars 11-14) full ----------
for b in range(11, 15):
    c = plan[b]
    pad(b, c, 70)
    root(b, c, 84)
    note(BASS, CH[c][1], bar(b), 2 * BEAT, 72)
    note(BASS, CH[c][1], bar(b, 2.5), 1.5 * BEAT, 66)
    ostinato(b, c, 60, step=0.25, accent=14)
    for beat in range(4):
        note(DR, 36, bar(b, beat), 0.4 * BEAT, 104 if beat in (0, 2) else 70)  # kick
        note(DR, 42, bar(b, beat + 0.5), 0.2 * BEAT, 52)  # closed hat
    note(DR, 41, bar(b, 1.5), 0.4 * BEAT, 80)  # low tom
    note(DR, 43, bar(b, 3.0), 0.4 * BEAT, 84)
    note(DR, 43, bar(b, 3.5), 0.4 * BEAT, 76)
    note(TIMP, CH[c][1].replace("1", "2"), bar(b), BEAT, 96)
mel = [(11, [("A5", 0, 1.5), ("D6", 1.5, 0.5), ("C6", 2, 1), ("A5", 3, 1)]),
       (12, [("Bb5", 0, 2), ("F5", 2, 1), ("D6", 3, 1)]),
       (13, [("C6", 0, 1.5), ("A5", 1.5, 0.5), ("F5", 2, 2)]),
       (14, [("E5", 0, 1), ("G5", 1, 1), ("C6", 2, 2)])]
for b, ns in mel:
    for p, at, d in ns:
        note(HISTR, p, bar(b, at), d * BEAT, 84)
note(DR, 49, bar(11), 2 * BEAT, 100)

# ---------- E: Alatz (bars 15-17) building tension ----------
for b in range(15, 18):
    c = plan[b]
    pad(b, c, 66 + 6 * (b - 15))
    root(b, c, 80 + 4 * (b - 15))
    ostinato(b, c, 58 + 6 * (b - 15), step=0.25, accent=12)
    for beat in range(4):
        note(DR, 36, bar(b, beat), 0.4 * BEAT, 96 if beat in (0, 2) else 64)
    note(TIMP, CH[c][1].replace("1", "2"), bar(b), BEAT, 100)
note(DR, 49, bar(15), 2 * BEAT, 104)
note(TIMP, "G1", bar(15), 2 * BEAT, 116)
# snare build in bar 17
for i in range(16):
    note(DR, 38, bar(17, i * 0.25), 0.2 * BEAT, 40 + i * 5)
note(FX, "C4", bar(16, 2.0), 6.0 * BEAT, 90)  # reverse cymbal into the glitch at 42.5
for p, at, d in [("D6", 0, 2), ("Bb5", 2, 2)]:
    note(HISTR, p, bar(15, at), d * BEAT, 84)
for p, at, d in [("F6", 0, 2), ("D6", 2, 2)]:
    note(HISTR, p, bar(16, at), d * BEAT, 88)
for p, at, d in [("E6", 0, 4)]:
    note(HISTR, p, bar(17, at), d * BEAT, 92)

# ---------- F: the reveal (bars 18-21) ----------
# bar 18: near silence, sub only, then the "machine" pulse enters on beat 3
note(BASS, "D1", bar(18), 4 * BEAT, 80)
note(PAD, "D3", bar(18), 4 * BEAT, 50)
note(PAD, "A3", bar(18), 4 * BEAT, 46)
for i in range(4):
    note(ARP, ["D5", "F5", "A5", "D6"][i], bar(18, 2 + i * 0.5), 0.4 * BEAT, 44 + i * 6)
for b in range(19, 22):
    c = plan[b]
    tones, r = CH[c]
    for t in tones[:4]:
        note(PAD, t, bar(b), BAR - 20, 60)
    note(BASS, r, bar(b), 2 * BEAT, 84)
    note(BASS, r, bar(b, 2), 2 * BEAT, 78)
    seq = ARPN[c if c in ARPN else "Dm"]
    for i in range(16):
        p = mido_p = seq[i % 8]
        note(ARP, p, bar(b, i * 0.25), 0.2 * BEAT, 50 + (10 if i % 4 == 0 else 0))
    for beat in range(4):
        note(DR, 36, bar(b, beat), 0.4 * BEAT, 100 if beat in (0, 2) else 60)
        note(DR, 42, bar(b, beat + 0.5), 0.2 * BEAT, 48)
    note(DR, 39, bar(b, 1), 0.3 * BEAT, 70)  # clap
    note(DR, 39, bar(b, 3), 0.3 * BEAT, 74)
    if b >= 20:
        pad(b, c, 56)
note(FX, "C4", bar(21, 1.0), 3.0 * BEAT, 84)  # swell into the end card at 52.5

# ---------- G: end card (bars 22-24) resolution ----------
note(DR, 49, bar(22), 3 * BEAT, 96)
note(TIMP, "Bb1", bar(22), 2 * BEAT, 104)
pad(22, "Bb", 72); root(22, "Bb", 80)
pad(23, "F", 74, bars=2); root(23, "F", 80, bars=2)
for t in ["F4", "A4", "C5"]:
    note(CHOIR, t, bar(22), 3 * BAR - 60, 66)
for p, at, d in [("D5", 0, 1), ("F5", 1, 1), ("Bb5", 2, 2)]:
    note(PIANO, p, bar(22, at), d * BEAT, 72)
for p, at, d in [("A5", 0, 1.5), ("G5", 1.5, 0.5), ("F5", 2, 2)]:
    note(PIANO, p, bar(23, at), d * BEAT, 70)
for p in ["F2", "C3", "F3", "A3", "C4", "F4"]:
    note(PIANO, p, bar(24), 4 * BEAT, 62)
note(HISTR, "C6", bar(22), 2 * BEAT, 80)
note(HISTR, "A5", bar(22, 2), 2 * BEAT, 78)
note(HISTR, "F5", bar(23), 2 * BAR - 40, 74)
# fade everything out over the last bar
for ch in (PIANO, STR, CELLO, CHOIR, HISTR):
    for i in range(9):
        cc(ch, 11, 127 - i * 14, bar(24, i * 0.5))

# ---------- write ----------
tr = mido.MidiTrack()
mid.tracks.append(tr)
tr.append(mido.MetaMessage("set_tempo", tempo=625000, time=0))
tr.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
events.sort(key=lambda e: (e[0], e[1]))
last = 0
for tick, _, (kind, a, b), ch in events:
    dt = tick - last
    last = tick
    if kind == "on":
        tr.append(mido.Message("note_on", channel=ch, note=a, velocity=b, time=dt))
    elif kind == "off":
        tr.append(mido.Message("note_off", channel=ch, note=a, velocity=0, time=dt))
    elif kind == "cc":
        tr.append(mido.Message("control_change", channel=ch, control=a, value=b, time=dt))
    elif kind == "pc":
        tr.append(mido.Message("program_change", channel=ch, program=a, time=dt))
tr.append(mido.MetaMessage("end_of_track", time=BAR * 2))
mid.save("score.mid")
print("bars", 24, "seconds", 24 * 2.5, "events", len(events))
