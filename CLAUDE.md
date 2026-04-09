# Infinite Collager V2

## What This Is
Infinite zoom collage machine. Python backend (FastAPI + image processing) serves
a single-file frontend (index.html) on port 6969. User uploads up to 10 photos,
system generates collage compositions using a rule engine. Scroll to zoom infinitely.

**V2 is complete and final.** Phases 0–5.5 are all shipped and user-confirmed.
Future development (Phases 6–7 and beyond) continues in a new repository.

## Stack
- Frontend: index.html (Canvas2D, sliders, WebSocket)
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

## Build Status — All Phases Complete

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Foundation — server, canvas, upload, WebSocket, sliders | Done |
| 1 | Preprocessing — subject masks, colors, edge/variance maps | Done |
| 2 | Cut path generation — silhouette, tear, geometric, raw | Done |
| 3 | Morphing — stretch, compress, rotate, shear, diagonal | Done |
| 4 | Composition engine — role assignment, layout, blend modes | Done |
| 5 | Infinite zoom — scroll zoom, layer transitions, tonal continuity | Done |
| 5.5 | QOL — per-image delete, cut prefs, drag ordering, tooltips | Done |
| 6 | Shape borrowing & collage-of-collage | Future repo |
| 7 | Polish & performance | Future repo |

## Known Issues (carried forward to new repo)
- Generation is slow (several seconds per composition). Pre-generation at 2× buys time
  but slider-triggered regeneration is still noticeably slow. Target: stamp caching.
- Detail/tiny stamps scatter randomly — no intentional clustering. Should group to create
  compelling zoom targets.
- Transition is a cross-dissolve. Plan called for something more physical ("like tearing
  through paper"). Deferred to Phase 7.
- Infinite zoom is functional but the aesthetic continuity between layers is loose.
  Option B (stamp packet transitions) would make it feel truly fractal.

## Deviations from Plan

### Dependencies
- `noise` package (Perlin) is incompatible with Python 3.14 — replaced with `opensimplex>=0.4.5`
  throughout. Use `opensimplex.seed(n)` + `opensimplex.noise2(x, y)`.
- `rembg` requires `rembg[cpu]` to pull in onnxruntime — requirements.txt specifies this.
  If onnxruntime fails (no wheel for Python version), preprocessor falls back to OpenCV
  GrabCut automatically. GrabCut masks are rougher; silhouette cuts are less precise.

### Cut / Morph behaviour
- morpher.py `shear` type was repurposed: instead of a geometric lean, it cuts an irregular
  polygon fragment from the stamp (jagged edges, tight-cropped). Intentional deviation.
- Cut quality was iterated post-Phase 2: silhouette wobble is seed-derived (amplitude and
  frequency vary per seed), loose tear uses independent rx/ry noise + spikes, triangle is
  scalene seeded, wedge apex placed at image corners.
- `_load_mask` in cutter.py resizes the cached mask to match the work image dimensions —
  necessary because the mask is stored at original resolution but stamps are generated from
  a 900px-max working copy.

### Phase scope changes
- Option A (single JPEG per layer) retained throughout Phase 5. Plan recommended switching
  to Option B (stamp packets) for transitions; deferred to Phase 7 / new repo.
- Context crop (visible viewport fed back as a pool image) was originally Phase 6 scope —
  pulled forward into Phase 5 as it is core to the fractal continuity effect.
- Zoom thresholds: pre-gen triggers at 2×, transition fires at 3.5×, zoom-out at 0.5×.
  Plan specified only a single threshold; these values are implementation decisions.
- Zoom-out layer restoration was Phase 7 scope — built in Phase 5 (below 0.5× triggers
  reverse cross-dissolve back to the previous layer from layerStack[]).
- tonal_hint system (sample average colour from visible crop → bias new composition's
  background) not in the original plan. Added in Phase 5 for colour continuity.

### Phase 5.5 additions (not in original plan)
- Per-image delete button (DELETE /images/{id} endpoint)
- Per-image cut type preferences stored as disabled-key sets in localStorage, propagated
  through server pool → compositor → placer per-stamp assignment
- Draggable image ordering with optional priority weighting (top ~3×, bottom ~0.4×),
  off by default
- Slider hover tooltips via CSS [data-tooltip]::after pseudo-element
- Cut test panel redesigned: per-tile checkboxes replace global filter bar
