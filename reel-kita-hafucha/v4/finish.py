#!/usr/bin/env python3
"""Picture finishing for the v4 reel (all functions take/return float32 BGR, 0..255).

grade()       teal shadows / warm highlights split-tone, gentle S-curve, a touch of saturation
bloom()       highlights glow (LED rings, screen, graphics) with a slight warm halation
grain()       fine animated film grain, lighter in the highlights
aberration()  chromatic fringe used only on transitions and punch-ins
light_leak()  warm/cyan flare used on whip-pan transitions"""
import numpy as np
import cv2

W, H = 1080, 1920
_rng = np.random.default_rng(5)
_GRAIN = [(_rng.standard_normal((H // 2, W // 2)).astype(np.float32)) for _ in range(24)]


def _build_lut():
    y = np.linspace(0, 1, 256, dtype=np.float32)
    sh, hi = (1 - y) ** 2, y ** 2
    lut = np.zeros((256, 1, 3), np.float32)
    for c, (s_, h_) in enumerate(((0.030, -0.022), (0.016, 0.006), (-0.018, 0.026))):   # B, G, R
        x = y + sh * s_ + hi * h_
        x = x + 0.055 * np.sin((x - 0.5) * np.pi) * (1 - np.abs(2 * x - 1))
        lut[:, 0, c] = np.clip(x, 0, 1) * 255
    return np.clip(lut, 0, 255).astype(np.uint8)


_LUT = _build_lut()


def grade(img):
    """teal shadows / warm highlights + gentle S-curve via a per-channel LUT, then +6% saturation"""
    u8 = np.clip(img, 0, 255).astype(np.uint8)
    x = cv2.LUT(u8, _LUT).astype(np.float32)
    g = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)[..., None]
    return np.clip(g + (x - g) * 1.06, 0, 255)


def bloom(img, threshold=0.70, amount=0.42):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA) / 255.0
    lum = small.max(axis=2, keepdims=True)
    bright = small * np.clip((lum - threshold) / (1 - threshold), 0, 1)
    b = cv2.GaussianBlur(bright, (0, 0), 3) * 0.6 + cv2.GaussianBlur(bright, (0, 0), 11) * 0.8
    b = b * np.array([0.92, 0.98, 1.10], np.float32)                           # warm halation
    b = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return np.clip(img + b * 255 * amount, 0, 255)


def grain(img, frame_idx, strength=5.0):
    n = cv2.resize(_GRAIN[frame_idx % len(_GRAIN)], (W, H), interpolation=cv2.INTER_LINEAR)
    lum = img.mean(axis=2, keepdims=True) / 255.0
    return np.clip(img + n[..., None] * strength * (1.15 - lum), 0, 255)


def aberration(img, amount):
    """amount 0..1 -> up to 6 px radial red/blue split"""
    if amount <= 0.01:
        return img
    s = 1 + 0.006 * amount
    c = (W / 2, H * 0.45)
    out = img.copy()
    M_r = cv2.getRotationMatrix2D(c, 0, s)
    M_b = cv2.getRotationMatrix2D(c, 0, 1 / s)
    out[..., 2] = cv2.warpAffine(img[..., 2], M_r, (W, H), borderMode=cv2.BORDER_REFLECT)
    out[..., 0] = cv2.warpAffine(img[..., 0], M_b, (W, H), borderMode=cv2.BORDER_REFLECT)
    return out


_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)


def light_leak(img, amount, side=1):
    """amount 0..1; side +1 = from the right, -1 = from the left"""
    if amount <= 0.01:
        return img
    cx = W * (1.05 if side > 0 else -0.05)
    d = np.sqrt(((_XX - cx) / (W * 0.75)) ** 2 + ((_YY - H * 0.35) / (H * 0.6)) ** 2)
    g = np.exp(-d ** 2 * 2.2)[..., None]
    col = np.array([90, 170, 255], np.float32) * 0.65 + np.array([232, 217, 0], np.float32) * 0.35
    return np.clip(img + g * col * amount * 0.9, 0, 255)
