#!/usr/bin/env python3
"""Per-frame person matting (ISNet, ONNX) for every frame used in the reel.
Writes 8-bit alpha PNGs at 2x source resolution: <cache>/<SEG>/<frame>.png
Usage: python3 matte.py SOURCE.mp4 MODEL.onnx CACHE_DIR"""
import os, subprocess, sys, time
import numpy as np, cv2, onnxruntime as ort
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import build_reel as R          # reuse the cut list (SEGMENTS) and frame reader

src, model, cache = sys.argv[1:4]
R.SRC = src
so = ort.SessionOptions(); so.intra_op_num_threads = os.cpu_count()
sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
inp = sess.get_inputs()[0].name
for seg in R.SEGMENTS:
    d = os.path.join(cache, seg["id"]); os.makedirs(d, exist_ok=True)
    t0 = time.time()
    for i, fr in enumerate(R.read_segment(seg, vf="null")):
        out = os.path.join(d, f"{i:04d}.png")
        if os.path.exists(out):
            continue
        x = cv2.resize(fr, (1024, 1024), interpolation=cv2.INTER_LINEAR)[:, :, ::-1].astype(np.float32)
        x = ((x - 128) / 256).transpose(2, 0, 1)[None]
        a = sess.run(["output"], {inp: x})[0][0, 0]
        a = cv2.resize(np.clip(a, 0, 1), (2 * R.SW, 2 * R.SH), interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(out, (np.clip(a, 0, 1) * 255).astype(np.uint8))
        if i % 50 == 0:
            print(f"{seg['id']} {i}/{seg['nf']}  {(time.time() - t0) / (i + 1):.2f}s/frame", flush=True)
print("MATTING DONE", flush=True)
