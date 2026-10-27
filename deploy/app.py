"""PrivacyGate web demo on Modal (CPU).

Serves one page (deploy/web/index.html) and POST /api/mask, which runs the
`full` pipeline with the best configuration: ensemble_pair "union" of
region-v5-2ep and region-v6-2ep-b8, name_threshold 0.1.

Weights live in the Modal Volume `privacygate-models` (never in the image or
the repo). Request text is never logged or stored; errors return codes only.

    modal run deploy/app.py::assemble_models   # once, after uploading parts
    modal deploy deploy/app.py
"""
import hashlib
import os
import threading
import time
from collections import deque
from pathlib import Path

import modal

APP_NAME = "privacygate"
MODELS = "/models"
PRIMARY = "region-v5-2ep"
PEER = "region-v6-2ep-b8"
SHA256 = {
    PRIMARY: "18c73d1c19e6394e9e74ac693caec2d6fd27b1948cb93c6c4a840a1832e5ae1d",
    PEER: "2cb47eb93d0ed5a6d64c323a83c105fdbcc604969a1298cc365511e96779634a",
}
OPTIONS = {"ensemble_pair": "union", "name_threshold": 0.1}
MAX_CHARS = 8000
RATE_PER_MIN = 20
TOKENIZER_ID = "google-bert/bert-base-multilingual-cased"
TOKENIZER_REV = "3f076fdb1ab68d5b2880cb87a0886f315b8146f8"

HERE = Path(__file__).resolve().parent

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.14.1", index_url="https://download.pytorch.org/whl/cpu")
    .pip_install(
        "transformers==5.18.0", "tokenizers==0.23.2", "safetensors==0.8.0",
        "huggingface_hub==1.33.0", "numpy==2.5.3", "phonenumberslite==9.0.40",
        "fastapi==0.115.12",
    )
    .env({"HF_HOME": "/root/hf", "PYTHONDONTWRITEBYTECODE": "1"})
    .run_commands(
        "python -c \"from huggingface_hub import snapshot_download; snapshot_download("
        f"'{TOKENIZER_ID}', revision='{TOKENIZER_REV}', "
        "allow_patterns=['config.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.txt'])\""
    )
    .env({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TRANSFORMERS_VERBOSITY": "error",
          "TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4"})
    .add_local_dir(HERE.parent / "privacygate", "/root/pg/privacygate", ignore=["**/__pycache__", "training"])
    .add_local_dir(HERE.parent / "configs", "/root/pg/configs")
    .add_local_dir(HERE / "web", "/root/web", ignore=[".env*", ".vercel", "vercel.json", ".gitignore", ".vercelignore"])
)

volume = modal.Volume.from_name("privacygate-models")
app = modal.App(APP_NAME, image=image)


@app.function(volumes={MODELS: volume}, timeout=1800)
def assemble_models():
    """Join uploaded parts into model.safetensors and verify sha256 (refuses mismatches)."""
    for name, digest in SHA256.items():
        target = Path(MODELS, name, "model.safetensors")
        if target.exists() and _sha256(target) == digest:
            print(name, "already ok")
            continue
        parts = sorted(Path(MODELS, "parts", name).glob("part.*"))
        if not parts:
            raise SystemExit(name + ": no parts")
        tmp = target.with_suffix(".part")
        with open(tmp, "wb") as out:
            for p in parts:
                out.write(p.read_bytes())
        if _sha256(tmp) != digest:
            tmp.unlink()
            raise SystemExit(name + ": sha256 mismatch")
        tmp.rename(target)
        print(name, "ok", len(parts), "parts")
    volume.commit()


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@app.cls(cpu=4, memory=6144, volumes={MODELS: volume}, enable_memory_snapshot=True,
         scaledown_window=300, max_containers=2, timeout=120)
@modal.concurrent(max_inputs=8)
class Web:
    @modal.enter(snap=True)
    def load(self):
        import sys
        import torch
        # Fix the thread count before the first inference. Changing it after a
        # forward pass (the old snap=False hook) could hang the container while
        # Modal was creating the memory snapshot, so every request timed out.
        torch.set_num_threads(4)
        sys.path.insert(0, "/root/pg")
        from privacygate.pipeline import run_pipeline
        self.run_pipeline = run_pipeline
        self.model_dir = str(Path(MODELS, PRIMARY))
        # Loads and caches both models; synthetic warm-up text only.
        result = run_pipeline("Contact Jane Example at jane@example.com.", "full", self.model_dir, OPTIONS)
        if result.get("status") != "ok":
            raise RuntimeError("warmup_failed")

    @modal.asgi_app()
    def web(self):
        from fastapi import FastAPI, Request
        from fastapi.responses import FileResponse, JSONResponse

        api = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        hits, lock = {}, threading.Lock()
        page = Path("/root/web/index.html")

        def limited(ip):
            now = time.time()
            with lock:
                q = hits.setdefault(ip, deque())
                while q and now - q[0] > 60:
                    q.popleft()
                if len(q) >= RATE_PER_MIN:
                    return True
                q.append(now)
                if len(hits) > 5000:
                    hits.clear()
            return False

        def reply(body, status=200):
            return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})

        @api.get("/")
        def index():
            return FileResponse(page, media_type="text/html", headers={"Cache-Control": "no-cache"})

        @api.get("/api/health")
        def health():
            return reply({"status": "ok"})

        @api.post("/api/mask")
        async def mask(request: Request):
            # Modal sets no X-Forwarded-For: the client is the peer address, or Vercel's
            # x-vercel-forwarded-for when the request comes through the Vercel /api rewrite.
            ip = (request.headers.get("x-vercel-forwarded-for") or "").split(",")[0].strip() \
                or (request.client.host if request.client else "?")
            if limited(ip):
                return reply({"status": "error", "error": "rate_limited"}, 429)
            try:
                body = await request.json()
                text = body.get("text") if isinstance(body, dict) else None
            except Exception:
                return reply({"status": "error", "error": "invalid_request"}, 400)
            if not isinstance(text, str) or not text.strip():
                return reply({"status": "error", "error": "empty_input"}, 400)
            if len(text) > MAX_CHARS:
                return reply({"status": "error", "error": "too_long", "max_chars": MAX_CHARS}, 413)
            start = time.perf_counter()
            try:
                from starlette.concurrency import run_in_threadpool
                result = await run_in_threadpool(self.run_pipeline, text, "full", self.model_dir, OPTIONS)
            except Exception:
                return reply({"status": "error", "error": "processing_error"}, 500)
            ms = round((time.perf_counter() - start) * 1000)
            if result.get("status") != "ok":
                return reply({"status": "blocked", "error": result.get("error", "blocked")}, 422)
            return reply({"status": "ok", "masked_text": result["masked_text"],
                          "entities": [{"start": e["start"], "end": e["end"], "label": e["label"]}
                                       for e in result["entities"]],
                          "ms": ms})

        return api
