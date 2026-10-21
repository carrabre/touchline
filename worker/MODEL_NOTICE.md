# Ball detector

RF-DETR Nano COCO weights and RF-DETR are by Roboflow, under Apache License 2.0.
Source: https://github.com/roboflow/rf-detr (rfdetr Python package 1.11.2).
Official checkpoint: https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth

The worker uses an ONNX export at 384px, batch 1, with dynamic INT8 per-channel
quantization of MatMul weights (onnxruntime 1.31.0). It uses sparse COCO class 37,
`sports ball`. The original checkpoint is not a soccer-goal classifier.

Export SHA-256: `06b14d3e39b133b8466e330b4c417dd81c3ef9c3f900fbd918811b579356698c`
Quantized asset SHA-256: `6ae077607df147ff3024f046f2e974a8bfe55b4e776c08f5b719fd61617f5568`

Store the 34,154,725-byte quantized asset at the `ASSET` key in net_goals.py in the
configured media bucket. The worker checks its SHA-256 before opening it. The
binary is outside Git; deployment must preserve that S3 object. Apache license
is included in RF_DETR_LICENSE.txt. The discovery/verifier integration is
Touchline code. Ultralytics was used only in offline diagnostics and is not a
runtime dependency or deployed model.
