# Infinite Collager V2

A browser-based infinite zoom collage machine. Upload up to 10 photos — the system generates collage compositions using a rule-based engine inspired by physical cut-and-paste collage art. Scroll to zoom into any region, and a new composition generates at depth, infinitely.

This is the final release of V2. Further development continues in a new repository.

---

## What it does

- Uploads up to 10 photos and preprocesses them (subject masking, color extraction, edge/variance maps)
- Generates collages by assigning images to roles (background, dominant, supporting, detail, strips) and cutting each with silhouette, tear, or geometric cuts
- Morphs stamps with stretch, compress, rotate, shear, and diagonal deformations
- Infinite scroll-zoom: zooming in generates a new composition at depth, tinted to match the region you zoomed into
- Zooming back out restores the previous layer
- 7 sliders control composition style in real time

---

## Requirements

- Python **3.10 or newer** (tested on 3.14)
- A modern browser (Chrome or Firefox recommended)

---

## Install — Windows

1. **Install Python** from [python.org](https://python.org) if you don't have it. During install, check "Add Python to PATH".

2. **Download or clone this repository** and open a terminal in the project folder:
   ```
   cd "infinite collager v2"
   ```

3. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
   > If `pip` isn't found, try `python -m pip install -r requirements.txt`

4. **Run:**
   ```
   python server.py
   ```
   Or double-click **`launch.bat`** — it starts the server and opens the browser automatically.

5. Open **http://localhost:6969** in your browser.

---

## Install — macOS

1. **Install Python 3** if you don't have it. The easiest way:
   ```
   brew install python
   ```
   Or download from [python.org](https://python.org).

2. **Clone or download this repository**, then open Terminal in the project folder:
   ```
   cd "infinite collager v2"
   ```

3. **Create a virtual environment** (recommended):
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

5. **Run:**
   ```
   python3 server.py
   ```

6. Open **http://localhost:6969** in your browser.

---

## Troubleshooting

**rembg / onnxruntime install fails:**
The subject masking library requires `onnxruntime`. If it fails to install (common on Python 3.13+), the system automatically falls back to OpenCV GrabCut for subject masks. Collages still work — silhouette cuts will just be less precise.

On some systems you may need to install it explicitly:
```
pip install "rembg[cpu]"
```

**Port already in use:**
Kill any process on port 6969, or edit the port in `server.py` (last line).

---

## How to Use

1. Click **Upload Photos** and select up to 10 images (JPEG/PNG)
2. Wait for each image to show **ready** — preprocessing runs automatically in the background
3. Click **Regenerate** to generate a collage
4. Adjust the 7 sliders to shape the composition style, then regenerate
5. **Scroll to zoom in** — a new composition generates at depth
6. Scroll back out to return to the previous layer

### Sliders

| Slider | Left end | Right end |
|--------|----------|-----------|
| Composition Mode | Single structured mode | Modes blend and drift |
| Background Presence | Full-bleed photo background | No background |
| Cut Style Bias | Silhouette & organic cuts | Geometric cuts |
| Morph Intensity | Original proportions | Heavy deformation |
| Density | Few large elements | Many overlapping fragments |
| Symmetry | Asymmetric | Mirrored across axis |
| Fragment Scatter | Aligned, minimal rotation | Wild rotation, chaotic |

Hover any slider name for a description.

### Per-image cut controls

Click the scissors icon on any uploaded image to open the **cut test panel** — a preview of every cut type applied to that image. Use the checkboxes on each tile to disable specific cuts or morphs for that image. Preferences are saved in the browser.

### Image priority

The **image priority weighting** toggle (off by default) makes images higher in the list appear more often in compositions. Drag to reorder. Top image is picked ~3× more than the bottom.

---

## Build Status

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

---

## Future Development

V2 is the foundation. The goal was always to build something that feels handmade and endlessly explorable — and V2 gets there. But there's a lot more left to realize.

The continuation (V3) picks up at Phase 6 and will focus on making the infinite zoom feel truly fractal rather than just generative — where zooming in reveals compositions that visually echo the layer above, borrowing shapes and silhouettes from what the camera just left. The physical transition between layers (currently a cross-dissolve) should feel like zooming into a fractal.

Other priorities for the next version:

- **Shape borrowing** — new compositions sample silhouettes from the previous layer's stamps, so the visual language carries through depth
- **Stamp caching and real-time response** — slider changes should feel instant; the current pipeline generates each stamp fresh every time
- **Physical transitions** — the zoom-through should feel like punching through a collage, not fading between two images
- **Detail clustering** — small stamps currently scatter randomly; they should group into dense zones worth zooming into
- **Breathing animation** — very slight, slow position drift on stamps over time, making the collage feel alive
- **Fullscreen and keyboard shortcuts**

The aesthetic north star stays the same

---

## Stack

- **Frontend:** single `index.html` — Canvas2D, WebSocket, no build step, no npm
- **Backend:** `server.py` — FastAPI + uvicorn on port 6969
- **Image processing:** OpenCV, rembg, Pillow, NumPy, scikit-learn, opensimplex (`engine/` module)

See `infinite-collager-v2-plan.md` for the full architecture and rule system.
