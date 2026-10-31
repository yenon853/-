#!/usr/bin/env python3
"""Rebuild Real-ESRGAN general-x4v3 (SRVGGNetCompact) from its TensorFlow.js graph
(npm @plotdb/upscaler, models/realesrgan/general_fast-64) as an ONNX model.
Usage: python3 sr_onnx.py MODEL_DIR OUT.onnx"""
import base64, json, os, sys
import numpy as np
import onnx
from onnx import helper, numpy_helper, TensorProto

src, out = sys.argv[1], sys.argv[2]
d = json.load(open(os.path.join(src, "model.json")))
# read all weights from the binary shards in manifest order
blob = b"".join(open(os.path.join(src, p), "rb").read() for m in d["weightsManifest"] for p in m["paths"])
W, off = {}, 0
for m in d["weightsManifest"]:
    for w in m["weights"]:
        q = (w.get("quantization") or {}).get("dtype")
        dt = {"float16": np.float16, "float32": np.float32, "int32": np.int32}[q or w["dtype"]]
        n = int(np.prod(w["shape"])) if w["shape"] else 1
        a = np.frombuffer(blob, dt, n, off).reshape(w["shape"])
        W[w["name"]] = a.astype(np.float32) if dt == np.float16 else a
        off += n * np.dtype(dt).itemsize      # weights are stored as float16

nodes, inits = [], []
x = "x"                                  # NCHW float32, RGB 0..1
convs = [n for n in d["modelTopology"]["node"] if n["op"] == "_FusedConv2D"]
for k, n in enumerate(convs):
    kern, bias = W[n["input"][1]], W[n["input"][2]]
    ops = [base64.b64decode(s).decode() for s in n["attr"]["fused_ops"]["list"]["s"]]
    kw, kb = f"w{k}", f"b{k}"
    inits += [numpy_helper.from_array(np.ascontiguousarray(kern.transpose(3, 2, 0, 1)), kw),
              numpy_helper.from_array(bias.astype(np.float32), kb)]
    y = f"c{k}"
    nodes.append(helper.make_node("Conv", [x, kw, kb], [y], pads=[1, 1, 1, 1], kernel_shape=[3, 3]))
    if "Prelu" in ops:
        a = W[n["input"][3]].reshape(-1, 1, 1).astype(np.float32)
        inits.append(numpy_helper.from_array(a, f"a{k}"))
        nodes.append(helper.make_node("PRelu", [y, f"a{k}"], [f"p{k}"]))
        y = f"p{k}"
    x = y
nodes.append(helper.make_node("DepthToSpace", [x], ["d2s"], blocksize=4, mode="DCR"))
inits.append(numpy_helper.from_array(np.array([1, 1, 4, 4], np.float32), "scales"))
nodes.append(helper.make_node("Resize", ["x", "", "scales"], ["up"], mode="nearest",
                              coordinate_transformation_mode="half_pixel", nearest_mode="round_prefer_floor"))
nodes.append(helper.make_node("Add", ["d2s", "up"], ["y"]))
g = helper.make_graph(nodes, "realesr_general_x4v3",
                      [helper.make_tensor_value_info("x", TensorProto.FLOAT, [1, 3, "h", "w"])],
                      [helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 3, "H", "W"])], inits)
m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 17)])
m.ir_version = 8                          # readable by older onnxruntime builds
onnx.checker.check_model(m)
onnx.save(m, out)
print("saved", out, len(convs), "convs")
