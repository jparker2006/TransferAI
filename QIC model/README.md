# Query Intent Classifier (QIC)

A lightweight, fast, and accurate intent classifier that powers the **TransferAI** assistant (SMC → UCSD). The model is fine-tuned from `bert-base-uncased` using the *V2 QIC Data* set and achieves ≥ 0.85 weighted-F1 on the validation split.

---

## 🛠️  Setup

```bash
# 1️⃣  Create & activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# 2️⃣  Install dependencies
pip install -r requirements.txt
```

> **Note** `torch` CPU wheels are installed by default. If you have a CUDA-enabled GPU, install the matching PyTorch build before training to accelerate fine-tuning.


## ⚙️  Configuration

All hyper-parameters live in `src/config.yaml`. Edit the file or override values via CLI flags (see `--help`).

Key fields:

| Key | Default | Description |
|-----|---------|-------------|
| `model_name` | `bert-base-uncased` | HF model hub ID |
| `num_epochs` | `3` | Training epochs |
| `batch_size` | `16` | Per-device batch size |
| `learning_rate` | `2e-5` | AdamW LR |
| `weight_decay` | `0.01` | Weight decay |
| `max_length` | `128` | Max input tokens |
| `test_size` | `0.15` | Val split ratio |
| `output_dir` | `outputs` | Where artefacts are saved |


## 🏃‍♂️  Training

```bash
python -m src.train    # fine-tunes MiniLM (≈5 epochs)
# optional: export quantized ONNX for ultra-fast CPU inference
python scripts/export_onnx.py
```

# MiniLM + ONNX-INT8 latency
Running the exported model on an Intel i7 CPU with `onnxruntime` yields ~5 ms
per query.

Outputs:

```
outputs/
├── config.json          # snapshot of training config
├── metrics.json         # final eval metrics
├── pytorch_model.bin    # fine-tuned weights
├── tokenizer.json       # updated tokenizer (same as base)
├── label_encoder.pkl    # fitted sklearn LabelEncoder
└── ...
```


## 🔮  Inference

```bash
python src/infer.py "what GPA do I need to transfer to UCSD?"
# → gpa_requirement
```

The script auto-detects GPU/CPU and loads artefacts from `outputs/` (see config).


## 📈  Evaluation (optional)

To generate a confusion matrix on the validation split:

```bash
python src/evaluate.py  # optional stretch goal, not included by default
```


## 🧹  House-Keeping

A `.gitignore` is provided to exclude `outputs/`, virtual-envs, and byte-code caches.

---

© 2025 TransferAI 