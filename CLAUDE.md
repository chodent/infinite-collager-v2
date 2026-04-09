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
Phases 0–4 complete (Phase 4 built and iterated but not formally user-confirmed).
Phase 5 (Infinite Zoom) built 2026-04-08. Not yet user-confirmed — currently in testing.
Do not advance to Phase 6 until Phase 5 is user-confirmed.

Phase 5 delivered:
- index.html    — full layer system (currentLayer/nextLayer/layerStack[]), cursor-centred
                  zoom + pan, requestAnimationFrame render loop, pre-gen at 2×,
                  transition trigger at 3.5×, 600ms eased cross-dissolve (in + out),
                  zoom-out reverse transition below 0.5×, context_crop + tonal_hint capture
- server.py     — request_composition accepts context_crop (base64 JPEG) and tonal_hint;
                  crop decoded, preprocessed, added to pool as ephemeral entry, cleaned up
- engine/compositor.py — compose() accepts tonal_hint; passed to _make_background()
                         which strongly biases background colour toward hint

## Known Issues / Next Priorities
- Generation is slow (several seconds) — all cutting/morphing is synchronous per-stamp.
  The pre-generation at 2× buys time, but slider-triggered regeneration is still slow.
  Target: stamp cache to approach real-time slider response.
- Detail/tiny stamps need more intentional clustering and variety to create compelling
  zoom targets. Currently they scatter randomly — should group and feel worth exploring.
- Transition is a cross-dissolve. Plan called for something more physical ("like tearing
  through paper"). Physical transition deferred to Phase 7 polish.

## Known Deviations from Plan
- `noise` package (Perlin) is incompatible with Python 3.14 — replaced with `opensimplex>=0.4.5`
  throughout. Use `opensimplex.seed(n)` + `opensimplex.noise2(x, y)`.
- `rembg` requires `rembg[cpu]` to pull in onnxruntime — requirements.txt already specifies
  `rembg[cpu]`. If onnxruntime still fails (e.g. no Python 3.14 wheel), preprocessor falls
  back to OpenCV GrabCut automatically.
- GrabCut fallback mask is rougher than rembg — silhouette cuts will be less precise until
  rembg is confirmed working.
- morpher.py `shear` type was repurposed: instead of a geometric lean, it cuts an irregular
  polygon fragment from the stamp (jagged edges, tight-cropped). This is intentional.
- Cut quality was iterated post-Phase 2: silhouette wobble is now seed-derived
  (amplitude/frequency vary), loose tear uses independent rx/ry noise + spikes,
  triangle is scalene seeded, wedge apex placed at image corners.
- Option A (single JPEG per layer) retained throughout Phase 5. Plan recommended switching
  to Option B (stamp packets) for transitions; this is deferred to Phase 7.
- Context crop (visible viewport as pool image) was originally Phase 6 scope — pulled
  forward into Phase 5 as it is core to the fractal continuity effect.
- Zoom thresholds: pre-gen triggers at 2×, transition fires at 3.5×, zoom-out at 0.5×.
  Plan specified only a single threshold; these values are implementation decisions.
- Zoom-out layer restoration was Phase 7 scope in the plan — built in Phase 5 (below 0.5×
  triggers reverse cross-dissolve back to the previous layer from layerStack[]).
- tonal_hint system (sample avg colour from visible crop → bias new composition's background)
  not in the original plan. Added in Phase 5 to create colour continuity across zoom levels.
