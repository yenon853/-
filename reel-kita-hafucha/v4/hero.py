#!/usr/bin/env python3
"""Giant 'hero' words composited BEHIND the presenter (between the studio and the person).

Each hero is pre-rendered once as RGBA (extruded 3D face, gradient fill, soft glow) and animated
per frame: slam-in (scale 1.3 -> 1.0, fade), slow push, fade-out. It follows the camera with
parallax 0.35, so it reads as an object in the room, in front of the wall and behind the presenter."""
import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "fonts", "Heebo_900Black.ttf")
NAVY = (16, 27, 53)


def render(lines, size, top_col, bot_col, glow_col, max_w=1040):
    """lines: list of strings (RTL). Returns RGBA float32 (premultiplied-ready) and its centre."""
    f = ImageFont.truetype(FONT, size)
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    widths = [tmp.textlength(l, font=f, direction="rtl") for l in lines]
    scale = min(1.0, max_w / max(widths))
    if scale < 1:
        f = ImageFont.truetype(FONT, int(size * scale))
        size = int(size * scale)
    lh = int(size * 0.98)
    w = int(max(tmp.textlength(l, font=f, direction="rtl") for l in lines)) + 160
    h = lh * len(lines) + 220
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for i, l in enumerate(lines):
        d.text((w / 2, 110 + lh * (i + 0.5)), l, font=f, fill=255, anchor="mm", direction="rtl")
    m = np.asarray(mask).astype(np.float32) / 255
    # extrusion: stacked offset copies going down-right, darkening to navy
    depth = max(8, size // 22)
    ext = np.zeros_like(m)
    for k in range(depth, 0, -1):
        sh = np.roll(np.roll(m, k, axis=0), k // 2, axis=1)
        ext = np.maximum(ext, sh * (0.55 + 0.45 * (1 - k / depth)))
    # face colour: vertical gradient
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    face = np.array(top_col, np.float32) * (1 - yy) + np.array(bot_col, np.float32) * yy
    rgb = np.zeros((h, w, 3), np.float32)
    a = np.maximum(m, ext)
    rgb[:] = np.array(NAVY, np.float32) * 0.8
    rgb = rgb * (1 - m[..., None]) + face * m[..., None]
    # thin bright rim on the top edge of each letter
    rim = np.clip(m - np.roll(m, 3, axis=0), 0, 1)[..., None]
    rgb = rgb + rim * 70
    # glow behind
    glow = cv2.GaussianBlur(m, (0, 0), size / 9) * 0.85
    ga = np.clip(glow - a, 0, 1)[..., None]
    out_rgb = rgb * a[..., None] + np.array(glow_col, np.float32) * ga
    out_a = np.clip(a + ga[..., 0] * 0.9, 0, 1)
    rgba = np.dstack([out_rgb[..., ::-1], out_a * 255]).astype(np.float32)     # BGR + alpha
    return rgba


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def back_out(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


class Hero:
    def __init__(self, lines, t0, t1, cy, size=330, top=(255, 230, 120), bot=(255, 196, 40), glow=(0, 217, 232),
                 max_w=1000):
        self.t0, self.t1, self.cy = t0, t1, cy
        self.img = render(lines, size, top, bot, glow, max_w)

    def active(self, t):
        return self.t0 - 0.01 <= t <= self.t1 + 0.25

    def draw(self, canvas, t, cam_M, z, dx):
        """composite onto canvas (float BGR) in place; cam_M = 2x3 global camera affine"""
        if not self.active(t):
            return 0.0
        p_in = ease((t - self.t0) / 0.22)
        p_out = 1 - ease((t - self.t1) / 0.25)
        alpha = min(p_in, p_out)
        if alpha <= 0:
            return 0.0
        s_anim = 1.32 - 0.32 * back_out((t - self.t0) / 0.32)          # slam in with overshoot
        s_anim *= 1 + 0.035 * max(0.0, t - self.t0)                     # slow push while on screen
        s_cam = 1 + (z - 1) * 0.35                                       # depth: between the wall and the presenter
        s = s_anim * s_cam
        h, w = self.img.shape[:2]
        tx = 540 + dx * 0.35 - w / 2 * s
        ty = self.cy - h / 2 * s
        M = np.float32([[s, 0, tx], [0, s, ty], [0, 0, 1]])
        M = (np.vstack([cam_M, [0, 0, 1]]) @ M)[:2]
        lay = cv2.warpAffine(self.img, M, (canvas.shape[1], canvas.shape[0]), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        a = lay[..., 3:4] / 255 * alpha
        canvas *= (1 - a)
        canvas += lay[..., :3] * a
        return alpha
