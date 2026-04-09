import asyncio
import io
import uuid
import base64
from pathlib import Path
from typing import List

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from PIL import Image, ImageDraw
import numpy as np

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
CACHE_DIR = BASE_DIR / "cache"
UPLOADS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Infinite Collager V2")

# Connected WebSocket clients
active_connections: List[WebSocket] = []

# Uploaded images (runtime state)
uploaded_images: List[dict] = []


# ── Broadcast helper ───────────────────────────────────────────────────────────

async def broadcast(msg: dict):
    dead = []
    for ws in active_connections:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections.remove(ws)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=(BASE_DIR / "index.html").read_text(encoding="utf-8"))


@app.post("/upload")
async def upload_images(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    """Save uploaded images to uploads/ and kick off preprocessing for each."""
    results = []
    new_entries = []

    for file in files:
        if not file.content_type.startswith("image/"):
            continue
        if len(uploaded_images) + len(new_entries) >= 10:
            break

        image_id = str(uuid.uuid4())[:8]
        ext = Path(file.filename).suffix or ".jpg"
        save_path = UPLOADS_DIR / f"{image_id}{ext}"
        content = await file.read()
        save_path.write_bytes(content)

        entry = {
            "id": image_id,
            "filename": file.filename,
            "path": str(save_path),
            "status": "pending",   # pending → processing → ready | error
            "meta": None,
        }
        uploaded_images.append(entry)
        new_entries.append(entry)
        results.append({"id": image_id, "filename": file.filename})

    # Notify frontend of the new image list
    await broadcast({"type": "images_updated", "images": _serialized_images()})

    # Kick off preprocessing for each new image in background
    for entry in new_entries:
        background_tasks.add_task(_preprocess_task, entry)

    return JSONResponse({"uploaded": results, "total": len(uploaded_images)})


@app.get("/images")
async def list_images():
    return JSONResponse({"images": _serialized_images()})


@app.delete("/images")
async def clear_images():
    global uploaded_images
    for item in uploaded_images:
        try:
            Path(item["path"]).unlink(missing_ok=True)
        except Exception:
            pass
    uploaded_images = []
    await broadcast({"type": "images_updated", "images": []})
    return JSONResponse({"cleared": True})


@app.delete("/images/{image_id}")
async def delete_image(image_id: str):
    global uploaded_images
    entry = next((img for img in uploaded_images if img["id"] == image_id), None)
    if not entry:
        return JSONResponse({"error": "not found"}, status_code=404)
    try:
        Path(entry["path"]).unlink(missing_ok=True)
    except Exception:
        pass
    uploaded_images = [img for img in uploaded_images if img["id"] != image_id]
    await broadcast({"type": "images_updated", "images": _serialized_images()})
    return JSONResponse({"deleted": image_id})


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    await websocket.send_json({"type": "connected", "message": "Infinite Collager V2 ready"})
    # Send current image list immediately on connect
    await websocket.send_json({"type": "images_updated", "images": _serialized_images()})
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "request_composition":
                response = await asyncio.to_thread(
                    _run_composition,
                    data.get("sliders", {}),
                    data.get("seed"),
                    data.get("context_crop"),
                    data.get("tonal_hint"),
                    data.get("image_order"),
                    data.get("use_weights", True),
                    data.get("image_cut_prefs"),
                )
                await websocket.send_json(response)

            elif msg_type == "slider_change":
                await websocket.send_json({"type": "slider_ack", "sliders": data.get("sliders", {})})

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


# ── Preprocessing background task ──────────────────────────────────────────────

async def _preprocess_task(entry: dict):
    """Run preprocessing for one image. Sends WS progress messages."""
    image_id = entry["id"]
    image_path = Path(entry["path"])

    entry["status"] = "processing"
    await broadcast({
        "type": "preprocess_start",
        "image_id": image_id,
        "filename": entry["filename"],
    })

    loop = asyncio.get_event_loop()

    def progress_cb(step: int, total: int, message: str):
        asyncio.run_coroutine_threadsafe(
            broadcast({
                "type": "preprocess_progress",
                "image_id": image_id,
                "step": step,
                "total": total,
                "message": message,
            }),
            loop,
        )

    try:
        from engine.preprocessor import preprocess_image
        meta = await asyncio.to_thread(preprocess_image, image_path, CACHE_DIR, progress_cb)
        entry["status"] = "ready"
        entry["meta"] = meta
        await broadcast({
            "type": "preprocess_done",
            "image_id": image_id,
            "filename": entry["filename"],
            "meta": _safe_meta(meta),
        })
    except Exception as e:
        entry["status"] = "error"
        print(f"[server] preprocessing failed for {image_id}: {e}")
        await broadcast({
            "type": "preprocess_error",
            "image_id": image_id,
            "error": str(e),
        })


def _safe_meta(meta: dict) -> dict:
    """Strip file paths before sending meta over WebSocket."""
    safe = {k: v for k, v in meta.items() if not k.endswith("_path")}
    return safe


def _serialized_images() -> list:
    return [
        {
            "id": img["id"],
            "filename": img["filename"],
            "status": img["status"],
            "meta": _safe_meta(img["meta"]) if img.get("meta") else None,
        }
        for img in uploaded_images
    ]


# ── Phase 2: test-cuts endpoint ───────────────────────────────────────────────

@app.get("/test-cuts/{image_id}")
async def test_cuts(image_id: str):
    """Generate one stamp of each cut type for the given image. Visual QA for Phase 2."""
    entry = next(
        (img for img in uploaded_images if img["id"] == image_id and img["status"] == "ready"),
        None,
    )
    if not entry:
        return JSONResponse({"error": "image not found or not ready"}, status_code=404)

    results = await asyncio.to_thread(_generate_test_cuts, entry)
    return JSONResponse(results)


def _generate_test_cuts(entry: dict) -> dict:
    from engine.cutter  import cut_stamp
    from engine.morpher import morph_stamp

    image_path = entry["path"]
    meta       = entry["meta"]
    cuts       = {}

    cut_specs = [
        ("silhouette",      {},                              "silhouette"),
        ("tear",            {"scale": 0.45, "irregularity": 0.55}, "tear"),
        ("geometric",       {"shape": "rect"},               "geometric_rect"),
        ("geometric",       {"shape": "strip_h"},            "geometric_strip"),
        ("geometric",       {"shape": "triangle"},           "geometric_triangle"),
        ("geometric",       {"shape": "wedge"},              "geometric_wedge"),
        ("raw",             {},                              "raw"),
    ]

    for cut_type, params, label in cut_specs:
        try:
            stamp = cut_stamp(image_path, meta, cut_type, params)
            buf   = io.BytesIO()
            stamp.save(buf, format="PNG")
            data  = base64.b64encode(buf.getvalue()).decode()
            cuts[label] = f"data:image/png;base64,{data}"
        except Exception as e:
            cuts[label] = None
            print(f"[test-cuts] {label} failed: {e}")

    # ── Phase 3: morph examples (applied to silhouette cut) ──
    morph_specs = [
        ("compress_x",       0.85, "morph_compress_x"),
        ("stretch_x",        0.75, "morph_stretch_x"),
        ("rotate",           0.65, "morph_rotate"),
        ("diagonal_stretch", 0.75, "morph_diagonal_stretch"),
        ("shear",            0.72, "morph_shear"),
        ("combined",         0.75, "morph_combined"),
    ]

    try:
        base_stamp = cut_stamp(image_path, meta, "silhouette", {}, seed=42)
    except Exception:
        base_stamp = None

    for morph_type, intensity, label in morph_specs:
        if base_stamp is None:
            cuts[label] = None
            continue
        try:
            morphed = morph_stamp(base_stamp, {"morph_type": morph_type, "intensity": intensity}, seed=42)
            buf     = io.BytesIO()
            morphed.save(buf, format="PNG")
            data    = base64.b64encode(buf.getvalue()).decode()
            cuts[label] = f"data:image/png;base64,{data}"
        except Exception as e:
            cuts[label] = None
            print(f"[test-cuts] {label} failed: {e}")

    return cuts


# ── Phase 4 / 5: real composition ─────────────────────────────────────────────

def _run_composition(sliders: dict, seed=None,
                     context_crop_b64=None, tonal_hint=None,
                     image_order=None, use_weights=True,
                     image_cut_prefs=None) -> dict:
    """Synchronous: runs in asyncio.to_thread. Returns WS message dict."""
    from engine.compositor import compose

    ready = [img for img in uploaded_images if img["status"] == "ready"]
    if not ready:
        img_out = Image.new("RGB", (800, 600), (20, 18, 16))
        draw = ImageDraw.Draw(img_out)
        draw.text((20, 280), "No images ready — upload and wait for preprocessing",
                  fill=(100, 100, 100))
        buf = io.BytesIO()
        img_out.save(buf, format="JPEG", quality=88)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return {"type": "composition", "image": f"data:image/jpeg;base64,{encoded}"}

    pool = [{"path": img["path"], "meta": img["meta"], "id": img["id"],
             "disabled_cuts": list((image_cut_prefs or {}).get(img["id"], []))}
            for img in ready]

    # ── Image priority ordering + weights ──────────────────────────────────────
    image_weights = None
    if image_order and use_weights:
        rank_map = {iid: idx for idx, iid in enumerate(image_order)}
        n = len(pool)
        pool.sort(key=lambda p: rank_map.get(p.get("id", ""), n))
        if n == 1:
            image_weights = [1.0]
        else:
            image_weights = [3.0 - (3.0 - 0.4) * (i / (n - 1)) for i in range(n)]

    # ── Context crop: add visible viewport as an extra pool image ──────────────
    tmp_path = None
    if context_crop_b64:
        try:
            raw = context_crop_b64
            if "," in raw:
                raw = raw.split(",", 1)[1]
            img_bytes = base64.b64decode(raw)
            tmp_path  = CACHE_DIR / f"_ctx_{uuid.uuid4().hex[:8]}.jpg"
            tmp_path.write_bytes(img_bytes)
            pil_crop  = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            cw, ch    = pil_crop.size
            crop_np   = np.array(pil_crop)
            try:
                from engine.preprocessor import _dominant_colors
                dom_colors = _dominant_colors(crop_np, n_colors=3)
                mean_c     = crop_np.mean(axis=(0, 1))
                mean_dict  = {"r": int(mean_c[0]), "g": int(mean_c[1]), "b": int(mean_c[2])}
            except Exception:
                dom_colors = []
                mean_dict  = {"r": 128, "g": 128, "b": 128}
            tmp_meta = {
                "hash":           "ctx_temp",
                "width":          cw,
                "height":         ch,
                "dominant_colors": dom_colors,
                "mean_color":     mean_dict,
                "has_mask":       False,
                "subject_bbox":   {"x": 0, "y": 0, "w": cw, "h": ch},
                "mask_path":      None,
                "work_path":      str(tmp_path),
                "edges_path":     None,
                "variance_path":  None,
            }
            pool.append({"path": str(tmp_path), "meta": tmp_meta})
        except Exception as e:
            print(f"[server] context_crop failed: {e}")
            tmp_path = None

    try:
        result_img = compose(pool, sliders, seed=seed, canvas_w=1200, canvas_h=900,
                             tonal_hint=tonal_hint, image_weights=image_weights)
        buf = io.BytesIO()
        result_img.save(buf, format="JPEG", quality=88)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return {"type": "composition", "image": f"data:image/jpeg;base64,{encoded}"}
    except Exception as e:
        print(f"[compositor] compose failed: {e}")
        import traceback; traceback.print_exc()
        img_out = Image.new("RGB", (800, 600), (30, 10, 10))
        draw = ImageDraw.Draw(img_out)
        draw.text((20, 280), f"Composition error: {e}", fill=(200, 80, 80))
        buf = io.BytesIO()
        img_out.save(buf, format="JPEG", quality=88)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return {"type": "composition", "image": f"data:image/jpeg;base64,{encoded}"}
    finally:
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


if __name__ == "__main__":
    print("Starting Infinite Collager V2 on http://localhost:6969")
    uvicorn.run("server:app", host="0.0.0.0", port=6969, reload=True)
