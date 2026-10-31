#!/usr/bin/env python3
"""Real-ESRGAN (general-x4v3, ONNX) on the head-and-shoulders area of every frame used in the reel.
The crop follows the tracked face. Results are stored at 2x source scale (x4 then area-downscaled),
with the crop position, for the compositor to blend into the 2x frame.
Usage: python3 sr_cache.py SOURCE.mp4 MODEL.onnx CACHE_DIR"""
import json, os, sys, time
import numpy as np, cv2, onnxruntime as ort
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import build_reel as R

src, model, cache = sys.argv[1:4]
R.SRC = src
CW, CH = 256, 320                      # crop in source pixels (head, hair, neck, shoulders top)
so = ort.SessionOptions(); so.intra_op_num_threads = os.cpu_count()
sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
for seg in R.SEGMENTS:
    d = os.path.join(cache, seg["id"]); os.makedirs(d, exist_ok=True)
    (tcx, tey, tfw), _ = R.track(seg)
    pos, t0 = {}, time.time()
    for i, fr in enumerate(R.read_segment(seg)):          # same graded frames as the compositor
        x0 = int(np.clip(round(tcx[i] - CW / 2), 0, R.SW - CW))
        y0 = int(np.clip(round(tey[i] - 0.45 * CH), 0, R.SH - CH))
        pos[i] = (x0, y0)
        out = os.path.join(d, f"{i:04d}.png")
        if os.path.exists(out):
            continue
        crop = fr[y0:y0 + CH, x0:x0 + CW, ::-1].astype(np.float32) / 255      # BGR -> RGB
        y = sess.run(None, {"x": crop.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
        y = cv2.resize(np.clip(y, 0, 1), (CW * 2, CH * 2), interpolation=cv2.INTER_AREA)
        cv2.imwrite(out, (y[:, :, ::-1] * 255 + 0.5).astype(np.uint8))
        if i % 60 == 0:
            print(f"{seg['id']} {i}/{seg['nf']}  {(time.time() - t0) / (i + 1):.2f}s/frame", flush=True)
    json.dump(pos, open(os.path.join(d, "pos.json"), "w"))
print("SR DONE", flush=True)
