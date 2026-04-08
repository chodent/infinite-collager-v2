# Infinite Collager V2

## What This Is
Infinite zoom collage machine. Python backend (FastAPI + image processing) serves
a single-file frontend (index.html) on port 6969. User uploads up to 10 photos,
system generates collage compositions using a rule engine. Scroll to zoom infinitely.

## Stack
- Frontend: index.html (Canvas2D/WebGL, sliders, WebSocket)
- Backend: server.py + engine/ module (FastAPI, OpenCV, rembg, Pillow)
- No npm. No build step. No frameworks.

## Run
pip install -r requirements.txt
python server.py
Open http://localhost:6969

## Rules
- Present plan before code. Wait for approval.
- feature/ branches only. Never commit to main.
- Push branches immediately. Merge only after device test confirmation.
- Never delete branches. No co-author tags.
- Port 6969 always.
- Ask before writing code — never demo unprompted.
- For bulk tasks, automate fully.

## Architecture
See infinite-collager-v2-plan.md for complete architecture,
rule system, and build phases.

## Key Directories
- engine/         — Python image processing + composition engine
- uploads/        — User-uploaded images (runtime, gitignored)
- cache/          — Preprocessed data (runtime, gitignored)
- index.html      — Entire frontend
- server.py       — Backend server

## Current Phase
Phases 0–3 complete and user-confirmed. Phase 4 (Composition Engine) is built but NOT complete — still in testing and iteration as of 2026-04-08. Do not advance to Phase 5 until Phase 4 is user-confirmed.

Phase 4 delivered:
- engine/rules.py      — slider values → CompositionSpec
- engine/placer.py     — 5 placement modes: scenic, symmetric, radial, framed, experimental
- engine/compositor.py — full pipeline: rules → cut → morph → place → PIL Image → JPEG
- server.py            — _run_composition() replaces stub, runs in asyncio.to_thread
- Output: single composited JPEG (Option A), no frontend changes needed

## Known Issues / Next Priorities
- Generation is slow (several seconds) — all cutting/morphing is synchronous per-stamp.
  Target: stamp cache + pre-generation to approach real-time slider response.
- Detail/tiny stamps need more intentional clustering and variety to create compelling
  zoom targets. Currently they scatter randomly — should group and feel worth exploring.

## Known Deviations from Plan
- `noise` package (Perlin) is incompatible with Python 3.14 — replaced with `opensimplex>=0.4.5` throughout. Use `opensimplex.seed(n)` + `opensimplex.noise2(x, y)`.
- `rembg` requires `rembg[cpu]` to pull in onnxruntime — requirements.txt already specifies `rembg[cpu]`. If onnxruntime still fails (e.g. no Python 3.14 wheel), preprocessor falls back to OpenCV GrabCut automatically.
- GrabCut fallback mask is rougher than rembg — silhouette cuts will be less precise until rembg is confirmed working.
- morpher.py `shear` type was repurposed: instead of a geometric lean, it cuts an irregular polygon fragment from the stamp (jagged edges, tight-cropped). This is intentional.
- Cut quality was iterated post-Phase 2: silhouette wobble is now seed-derived (amplitude/frequency vary), loose tear uses independent rx/ry noise + spikes, triangle is scalene seeded, wedge apex placed at image corners.
