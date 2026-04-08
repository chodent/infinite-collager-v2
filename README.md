# Infinite Collager V2

A browser-based infinite zoom collage machine. Upload up to 10 photos, and the system generates collage compositions using a rule-based engine inspired by physical cut-and-paste collage art. Scroll to zoom into any region — a new composition generates at depth, infinitely.

---

## Install & Run

**Requirements:** Python 3.x (tested on 3.14)

```
python -m pip install -r requirements.txt
python server.py
```

Then open **http://localhost:6969** in your browser.

Or double-click **launch.bat** (Windows) — opens the browser automatically.

---

## How to Use

1. Click **Upload Photos** and select up to 10 images
2. Wait for the preprocessing indicator to show **ready** for each image
3. Adjust the 7 sliders to shape the composition style
4. Click **Regenerate** to generate a collage
5. Scroll to zoom in — new compositions generate at depth

### Sliders

| Slider | Left | Right |
|--------|------|-------|
| Composition Mode | Single structured mode | Modes blend and drift |
| Background Presence | Full-bleed photo background | No background |
| Cut Style Bias | Silhouette cuts | Geometric cuts |
| Morph Intensity | Original proportions | Heavy deformation |
| Density | Few large elements | Many overlapping fragments |
| Symmetry | Asymmetric | Mirrored across axis |
| Fragment Scatter | Aligned, minimal rotation | Wild rotation, chaotic |

---

## Build Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Foundation — server, canvas, upload, WebSocket, sliders | Done |
| 1 | Preprocessing — subject masks, dominant colors, edge/variance maps | Done |
| 2 | Cut path generation — silhouette, tear, geometric, raw crop | Done |
| 3 | Morphing — stretch, compress, rotate, shear, diagonal, combined | Done |
| 4 | Composition engine — full collage layout from image pool | In Progress |
| 5 | Zoom interaction — scroll zoom, layer transitions | Pending |
| 6 | Shape borrowing & collage-of-collage | Pending |
| 7 | Polish & performance | Pending |

---

## Stack

- **Frontend:** single `index.html` — Canvas2D, WebSocket, no build step
- **Backend:** `server.py` — FastAPI on port 6969
- **Image processing:** OpenCV, rembg, Pillow, NumPy (`engine/` module)

See `infinite-collager-v2-plan.md` for the full architecture document.
