#!/usr/bin/env python3
"""2.5D studio from the user's 16:9 studio render.

The image is split into depth layers that the virtual camera moves at different rates:
  far      back wall, big screen, side screens (desk area inpainted)   parallax 0.25
  desk     the anchor desk                                            parallax 0.45
  floor    podium and floor                                           parallax 0.60
  ceiling  ceiling rings and downlights                               parallax 0.55
The far layer also carries volumetric light cones from the downlights.
Screen content comes from v3/studio_image.py (lesson content per topic, replaces the world map).

build(out_dir, image) writes PNGs (uint8, canvas = image x2):
  far_<key>.png / far_<key>_soft.png   far layer with each screen content, sharp and racked-out
  desk.png, floor.png, ceiling.png      RGBA layers
  screen_mask.png"""
import os, sys
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "v3"))
import studio_image as S   # noqa: E402  (screen polygon + per-topic screen content)

SCALE, BG_W, BG_H, CX, CY, KEYS = S.SCALE, S.BG_W, S.BG_H, S.CX, S.CY, S.KEYS
PARALLAX = {"far": 0.25, "desk": 0.45, "floor": 0.60, "ceiling": 0.55}
CEIL_Y, FLOOR_Y = 290, 722            # layer boundaries in source-image pixels
DOWNLIGHTS = [(140, 100), (440, 160), (760, 182), (1070, 182), (1380, 152), (1640, 98)]


def desk_mask(im):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    reg = np.zeros(im.shape[:2], np.uint8)
    reg[630:830, 520:1140] = 1
    m = ((hsv[..., 1] < 60) & (hsv[..., 2] > 90) & (reg == 1)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    i = 1 + int(np.argmax(st[1:, 4]))
    cnts, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros(im.shape[:2], np.uint8)
    cv2.drawContours(out, cnts, -1, 1, -1)
    return out


def up(img):
    return cv2.resize(img, (BG_W, BG_H), interpolation=cv2.INTER_LANCZOS4)


def band(h, y0, y1, feather):
    """soft 0..1 mask that is 1 between y0 and y1 (source pixels), feathered"""
    y = np.arange(h, dtype=np.float32)
    a = np.clip((y - (y0 - feather)) / (2 * feather), 0, 1) if y0 > 0 else np.ones(h, np.float32)
    b = np.clip(((y1 + feather) - y) / (2 * feather), 0, 1) if y1 < h else np.ones(h, np.float32)
    return (a * b)[:, None]


def light_cones(h, w):
    """volumetric haze under each downlight (additive, source pixels)"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    acc = np.zeros((h, w), np.float32)
    for (lx, ly) in DOWNLIGHTS:
        dy = np.clip(yy - ly, 0, None)
        width = 18 + dy * 0.42
        cone = np.exp(-0.5 * ((xx - lx) / width) ** 2) * np.exp(-dy / 520) * (yy > ly)
        acc += cone
    acc = cv2.GaussianBlur(acc, (0, 0), 6)
    return acc / (acc.max() + 1e-6)


def build(out_dir, image):
    os.makedirs(out_dir, exist_ok=True)
    im = cv2.imread(image)
    h, w = im.shape[:2]
    dm = desk_mask(im)
    # far layer: desk removed by inpainting (it is only seen around the desk's moving edge)
    far = cv2.inpaint(im, cv2.dilate(dm, np.ones((9, 9), np.uint8)) * 255, 12, cv2.INPAINT_TELEA)
    haze = light_cones(h, w)[..., None] * np.array([230, 215, 150], np.float32)   # cool white haze (BGR)
    far = np.clip(far.astype(np.float32) + haze * 0.16, 0, 255).astype(np.uint8)
    # RGBA layers in source pixels
    ceil_a = band(h, 0, CEIL_Y, 6) * np.ones((1, w), np.float32)
    floor_a = band(h, FLOOR_Y, h, 6) * np.ones((1, w), np.float32)
    floor_a = floor_a * (1 - cv2.GaussianBlur(dm.astype(np.float32), (0, 0), 2))
    desk_a = cv2.GaussianBlur(dm.astype(np.float32), (0, 0), 1.2)
    for name, a, sig in (("ceiling", ceil_a, 2.2), ("floor", floor_a, 2.0), ("desk", desk_a, 1.6)):
        rgba = np.dstack([up(im), up((a * 255).astype(np.uint8))])
        rgb = cv2.GaussianBlur(rgba[..., :3], (0, 0), sig)          # depth of field
        cv2.imwrite(os.path.join(out_dir, f"{name}.png"), np.dstack([rgb, rgba[..., 3]]))
    # far layer + screen (glass) + per-topic content
    big = up(far).astype(np.float32)
    poly = np.array(S.screen_polygon(), np.int32)
    mask = np.zeros((BG_H, BG_W), np.uint8)
    cv2.fillPoly(mask, [poly], 255)
    glass = np.zeros_like(big)
    glass[:] = S.NAVY[::-1]
    yy, xx = np.mgrid[0:BG_H, 0:BG_W]
    glass[(xx % 64 < 2) | (yy % 64 < 2)] = (60, 45, 28)
    m = cv2.GaussianBlur(mask, (0, 0), 1.5).astype(np.float32)[..., None] / 255
    base = cv2.GaussianBlur(big * (1 - m) + glass * m, (0, 0), 2.6)
    cv2.imwrite(os.path.join(out_dir, "screen_mask.png"), mask)
    for k in KEYS:
        c = np.asarray(S.content(k)).astype(np.float32)
        a = c[..., 3:4] / 255 * (mask[..., None].astype(np.float32) / 255)
        rgb = c[..., [2, 1, 0]]
        sharp = base * (1 - a) + cv2.GaussianBlur(rgb, (0, 0), 1.4) * a
        soft = cv2.GaussianBlur(base * (1 - 0.6 * a) + rgb * 0.6 * a, (0, 0), 4)
        cv2.imwrite(os.path.join(out_dir, f"far_{k}.png"), np.clip(sharp, 0, 255).astype(np.uint8))
        cv2.imwrite(os.path.join(out_dir, f"far_{k}_soft.png"), np.clip(soft, 0, 255).astype(np.uint8))


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
