# Infinite Collager V2 — Complete Project Plan

*Reference document for building the Infinite Collager V2 in Claude Code. This document contains the full architecture, rule system, technical stack, file structure, and phased build plan.*

---

## 1. What This Project Is

A browser-based infinite zoom collage machine. The user uploads up to 10 photos. The system automatically generates collage compositions from those photos using a rule-based engine. The user scrolls to zoom into any region of the collage, and a new composition generates at depth — infinitely. The aesthetic goal is physical cut-and-paste collage art in the tradition of Gee Vaucher (Crass artwork), Magrudergrind album covers, and hand-made zine collage.

### Core Loop

1. User uploads photos (up to 10)
2. System generates an initial collage composition using the rule engine
3. User explores the collage — scrolling zooms in
4. When the user zooms deep enough, a new composition generates from the same image pool (and optionally from fragments of the previous composition)
5. The new composition inherits some tonal quality from the zoomed region, then diverges
6. Repeat infinitely

### What V2 Is NOT

- Not a fractal renderer
- Not a random image scatter
- Not a photo grid or mosaic
- Not an AI image generator

It is: **an automated collage artist that follows compositional rules derived from real collage practice.**

---

## 2. Aesthetic References

These specific works define the target aesthetic:

- **Gee Vaucher — "The Feeding of the 5000" (Crass):** Scenic/spatial composition. Silhouette-cut figures placed in architectural space. B&W with muted tones. Dense but readable.
- **Gee Vaucher — "Penis Envy" (Crass):** Radial composition. Central dominant figure with text strips and photo fragments radiating outward. Density gradient from sparse center to packed edges.
- **Gee Vaucher — "Stations of the Crass":** Frame-within-frame. Dense B&W mosaic border surrounding a sparser, color-tinted interior scene. Sub-compositions within compositions.
- **Magrudergrind — "Crusher":** Symmetric/mirrored composition. Elements reflected across vertical axis. Bold color background (red). Heraldic, iconic structure.
- **Hand-made zine collage (friend's piece):** Loose torn shapes. Single background photo fills canvas. Rough scissor cuts visible. Overlapping organic forms. Warm color tones.

### Key Aesthetic Principles

- Preserve original photo tones — no acid colors, no filters
- Images should look like photos, not digital artifacts
- Visible cut edges are desirable — the physicality of scissors
- Repetition of the same image in different roles is encouraged
- Every pixel should be covered UNLESS the composition deliberately breathes with negative space
- The collage should feel handmade, not procedurally generated

---

## 3. The Rule System — "Selection, Dissection, Connection"

Based on Mark Wagner's framework: every collage passes through three stages.

### 3.1 SELECTION — Choosing Source Material

**Image Pool:** Up to 10 uploaded photos. All stamps are drawn from this pool. Repetition is encouraged — the same image can appear many times in one composition in different roles (background, dominant element, thin strip, tiny fragment).

**Background Selection:** Each composition decides its background treatment:
- **Full-bleed photo crop** — one image from the pool, scaled/cropped to fill the canvas
- **Color wash** — a dominant color sampled from a pool image, or a heavily blurred/stretched image used as tonal ground
- **No background** — composition floats on empty canvas or solid color, letting the collage breathe
- Controlled by the **Background Presence slider** (full-bleed → none)

**Stamp Count:** Variable per composition. Not fixed at 16 like v1. A sparse composition might use 5-8 stamps. A dense one might use 30+. Controlled by the **Density slider**.

### 3.2 DISSECTION — How Stamps Are Cut

Each stamp is assigned a cut type. The **Cut Style Bias slider** influences which types dominate.

#### Cut Types

1. **Silhouette Cut**
   - Approximate subject extraction from the photo
   - The cut path follows the subject contour but with humanized imperfection:
     - Random displacement (wobble) along the path at varying frequencies
     - Occasional straight-line segments (where scissors changed direction)
     - Margin error — sometimes clips into subject, sometimes leaves background
   - Produces the visible scissor-line edge seen in real collage
   - Used for: figures, animals, objects, faces

2. **Loose Tear**
   - Blobby, organic shape that vaguely relates to content but deviates freely
   - Like someone tore the photo rather than cut it
   - Irregular edges, large deviations from subject contour
   - Used for: mid-scale accent pieces, texture elements

3. **Geometric Cut**
   - Rectangle, strip, triangle, wedge, polygon
   - Ignores subject content entirely — the cut is a deliberate shape imposed on the photo
   - Can be extremely thin (strips for radiating patterns, horizon lines)
   - Can be wide (blocks for mirrored compositions)
   - Used for: structural elements, borders, radiating patterns

4. **Raw Crop**
   - Simple rectangular region of the photo
   - No special cutting — just a window into the image
   - Used for: background fills, packed mosaic fragments, tiny detail pieces

#### Morphing / Deformation

In addition to cutting, stamps can be **morphed**:
- Compressed horizontally into tall thin slivers
- Compressed vertically into wide flat ribbons
- Stretched in any direction to create abstract forms
- A portrait squeezed into a column. A landscape stretched into a horizon line.
- The source image remains recognizable but physically transformed
- Controlled by the **Morph Intensity slider** (faithful proportions → extreme deformation)

#### Shape Borrowing

The silhouette shape from one image can be used as a **mask** for a different image's content. Example: extract the outline of a person from photo A, fill it with the texture/content of photo B. This creates uncanny collage juxtapositions.

### 3.3 CONNECTION — How Stamps Are Arranged

#### Compositional Modes

The **Composition Mode slider** controls which arrangement strategy governs the layout. At the structured end, one mode is chosen and committed to. At the experimental end, modes blend and drift.

1. **Scenic / Spatial**
   - Elements placed to suggest physical space and depth
   - Larger elements suggest background; figures are situated on surfaces
   - Spatial relationships between elements (figure stands on building, etc.)
   - Reference: Vaucher "Feeding of the 5000"

2. **Symmetric / Mirrored**
   - Elements reflected across a vertical (or horizontal) axis
   - 1-2 centered elements break the symmetry
   - Creates heraldic, iconic, mandala-like structures
   - The same source image flipped horizontally creates wings, frames, pillars
   - Reference: Magrudergrind "Crusher"

3. **Radial**
   - Elements fan outward from a central anchor point
   - Central dominant element surrounded by radiating strips/fragments
   - Density increases toward edges
   - Reference: Vaucher "Penis Envy"

4. **Framed / Bordered**
   - Dense border of small packed fragments
   - Sparser interior scene with larger elements
   - The border is its own sub-composition with its own rules
   - Reference: Vaucher "Stations of the Crass"

5. **Experimental / Hybrid**
   - Modes blend within a single composition
   - Symmetric center that breaks into scattered chaos at edges
   - Radial core that dissolves into scenic placement
   - No single governing logic — the composition drifts

#### Stamp Role Hierarchy

Every composition distributes stamps across these roles:

| Role | Count | Frame Coverage | Description |
|------|-------|---------------|-------------|
| Background | 0-1 | 100% (if present) | Full-bleed photo, color wash, or omitted |
| Dominant Element | 1-2 | 30-60% | The focal point. Usually silhouette or loose-tear cut |
| Supporting Elements | 2-6 | 10-30% each | Mid-scale accents. Create relationships with dominant |
| Texture/Detail Fragments | Many (5-20+) | 1-10% each | Packed or scattered small pieces. **These are zoom seeds** |
| Strips/Slivers | 0-many | Variable | Thin geometric cuts for structure: radiating lines, borders, horizon markers |

#### Layering Rules

- **Z-order is NOT strictly size-based.** Small elements can appear behind larger ones. The system should shuffle layering order per composition.
- **Overlapping is encouraged.** Elements should overlap each other — this is fundamental to collage.
- **Bleed is allowed.** Elements can extend beyond canvas edges.
- **Density zones exist.** A composition can have sparse regions and dense regions. The density gradient gives the eye a path to follow.

#### Placement Intelligence

Stamps are not placed purely randomly. The system should have awareness of:
- **Focal point bias:** Cluster important elements toward the composition's center of gravity
- **Edge awareness:** Prevent all stamps from clustering in one quadrant
- **Overlap management:** Ensure overlaps create interesting relationships, not just occlusion
- **Scale hierarchy:** The largest stamps occupy the most visually prominent positions (usually)
- **Breathing room:** When background is omitted, leave intentional negative space

---

## 4. The Zoom Mechanic

### How Zoom Works

The zoom is the core interaction. It must feel smooth and natural.

**Architecture:** The zoom and the collage generation are **decoupled**. Compositions are generated as discrete layers. The zoom is a visual transition between layers.

**Zoom Seeds:** Every composition scatters small, visually dense fragments (the "texture/detail" role) throughout. These are natural anchor points for zooming — they're interesting to look at and they become the bridge between compositions.

**Transition Behavior:**
1. User scrolls to zoom into a region
2. The current composition scales up (simple geometric zoom)
3. At a threshold zoom level, the system begins generating a new composition
4. The new composition emerges from within the zoomed region — visually, it "blossoms" out of the detail fragments
5. The new composition inherits tonal/color qualities from the zoomed region as a bridge
6. Then diverges into its own full arrangement

**New Composition Sources:**
- Primary: same image pool, re-cut and re-arranged with new random seeds
- Secondary: fragments of the previous composition can become stamps in the new one (collage of collage)
- The mix is random per zoom level

**Transition Style:**
- V1 used a per-pixel hash snap (organic region-by-region transition). This was a good idea but poorly executed.
- V2 should explore: the new composition assembling itself piece by piece (stamps appearing one at a time from depth), or a spatial dissolve where the previous composition breaks apart as the new one emerges.
- The transition must not feel like a simple alpha crossfade. It should feel physical — like tearing through paper to find more paper beneath.

---

## 5. Slider Control Surface

All sliders affect the rule engine. They can be adjusted in real-time and affect the next generated composition.

| Slider | Range | Left Extreme | Right Extreme |
|--------|-------|-------------|---------------|
| Composition Mode | Structured ↔ Experimental | Single mode, committed | Modes blend and drift |
| Background Presence | Full-bleed ↔ None | Always a full photo background | No background, collage breathes |
| Cut Style Bias | Silhouette ↔ Geometric | Mostly contour-following cuts | Mostly hard geometric shapes |
| Morph Intensity | Faithful ↔ Extreme | Original proportions preserved | Heavy stretching/compression |
| Density | Sparse ↔ Packed | Few large elements, breathing room | Many overlapping fragments, horror vacui |
| Symmetry | Asymmetric ↔ Mirrored | No symmetry | Full axis reflection |
| Fragment Scatter | Orderly ↔ Chaotic | Stamps aligned, minimal rotation | Wild rotation, chaotic placement |

Each slider is independent. The combinatorial space is enormous, which ensures the system doesn't repeat itself.

---

## 6. Technical Architecture

### Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Single `index.html` | Canvas rendering, zoom controls, UI sliders, WebGL display |
| Backend | Python (FastAPI or Flask) | Image processing, subject extraction, stamp generation, composition engine |
| Image Processing | OpenCV, rembg (or SAM), Pillow | Subject detection, mask generation, cut path creation, morphing |
| Communication | WebSocket or REST API | Frontend requests compositions, backend returns stamp data |
| Server | Python | Serves static files + API endpoints. Port 6969 |

### Why Python Backend (Not Pure Browser)

V1 tried to do everything in a GLSL shader. This was elegant but severely limiting:
- No subject extraction possible in a shader
- No content-aware cropping
- No irregular cut paths
- No morphing beyond simple aspect ratio changes
- Hash-based placement with no compositional intelligence

V2 moves the heavy lifting to Python:
- **rembg** or **Segment Anything (SAM)** for subject extraction
- **OpenCV** for edge detection, contour finding, mask manipulation
- **Pillow** for image cropping, scaling, morphing, composition
- **NumPy** for fast pixel operations

The browser handles display, zoom interaction, and slider UI. The backend handles all image intelligence.

### Processing Pipeline

```
USER UPLOADS PHOTOS
        │
        ▼
┌─────────────────────────────────┐
│  PREPROCESSING (one-time)       │
│                                 │
│  For each uploaded image:       │
│  ├─ Generate subject mask       │
│  │  (rembg / SAM)              │
│  ├─ Detect dominant colors      │
│  ├─ Compute content regions     │
│  │  (high-variance areas)       │
│  ├─ Generate edge map           │
│  └─ Store: original + mask +    │
│     metadata                    │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  COMPOSITION ENGINE             │
│  (called per zoom level)        │
│                                 │
│  Input: slider values + seed +  │
│         optional region context │
│                                 │
│  1. Read slider values          │
│  2. Select composition mode     │
│  3. Assign stamp roles          │
│  4. For each stamp:             │
│     ├─ Select source image      │
│     ├─ Select cut type          │
│     ├─ Generate cut path        │
│     │  (using mask + wobble)    │
│     ├─ Apply morphing           │
│     ├─ Determine position,      │
│     │  rotation, z-order        │
│     └─ Render stamp to RGBA     │
│  5. Composite all stamps        │
│  6. Return final image or       │
│     stamp data to frontend      │
└─────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────┐
│  FRONTEND DISPLAY               │
│                                 │
│  ├─ Render composition to       │
│  │  canvas (WebGL or Canvas2D)  │
│  ├─ Handle scroll zoom          │
│  ├─ At zoom threshold:          │
│  │  request new composition     │
│  │  from backend                │
│  ├─ Transition between layers   │
│  └─ Slider UI controls          │
└─────────────────────────────────┘
```

### Data Flow: Frontend ↔ Backend

**Option A: Full Image Compositing (Backend Renders)**
- Backend composites all stamps into a single image per zoom level
- Sends the finished image to the frontend (JPEG/PNG over WebSocket or HTTP)
- Frontend just displays and handles zoom
- **Pro:** Simpler frontend. Backend has full control over compositing.
- **Con:** Bandwidth. Image transfer per zoom level. Latency.

**Option B: Stamp Data (Frontend Renders)**
- Backend sends individual stamp images (RGBA PNGs) + placement data (position, rotation, scale, z-order) to frontend
- Frontend composites stamps on canvas using WebGL or Canvas2D
- **Pro:** Frontend can animate transitions. Stamps cached for reuse. More responsive.
- **Con:** More complex frontend. More data to transfer initially.

**Recommendation: Option B (Stamp Data).** This gives us the best zoom transitions, allows caching, and lets the frontend handle animation. The backend is the brain; the frontend is the display.

**Stamp Data Packet (JSON):**
```json
{
  "composition_id": "abc123",
  "background": {
    "type": "image" | "color" | "none",
    "image_data": "base64 or URL",
    "color": "#1a1a1a"
  },
  "stamps": [
    {
      "id": "stamp_001",
      "image_data": "base64 RGBA PNG (pre-cut, pre-morphed)",
      "position": { "x": 0.35, "y": 0.22 },
      "size": { "width": 0.45, "height": 0.38 },
      "rotation": 0.05,
      "z_order": 3,
      "role": "dominant",
      "source_image_index": 2
    }
  ],
  "seed": 48291,
  "slider_state": { ... },
  "tonal_hint": { "r": 142, "g": 128, "b": 115 }
}
```

Positions and sizes are normalized (0.0 to 1.0 = fraction of canvas). This makes zoom math trivial.

---

## 7. File Structure

```
infinite-collager-v2/
├── index.html              — Frontend: canvas, zoom, sliders, WebSocket client
├── server.py               — Python server: static files + API + WebSocket
├── engine/
│   ├── __init__.py
│   ├── preprocessor.py     — Image upload handling, mask generation, metadata
│   ├── compositor.py       — Main composition engine (Selection, Dissection, Connection)
│   ├── cutter.py           — Cut path generation (silhouette, tear, geometric, raw)
│   ├── morpher.py          — Image morphing/deformation
│   ├── placer.py           — Stamp placement logic per composition mode
│   ├── rules.py            — Rule definitions, slider interpretation, role assignment
│   └── utils.py            — Hash functions, color analysis, geometry helpers
├── static/
│   └── (served by server.py — index.html assets if needed)
├── uploads/                — User-uploaded images (runtime)
├── cache/                  — Preprocessed masks, stamps, compositions (runtime)
├── requirements.txt        — Python dependencies
├── launch.bat              — Windows launcher
├── launch.sh               — Linux/Mac launcher
├── CLAUDE.md               — Project instructions for Claude Code sessions
└── README.md               — User-facing documentation
```

---

## 8. Phased Build Plan

### Phase 0: Foundation (Do First)
**Goal:** Skeleton project with image upload, basic display, and communication working.

- [ ] Set up project directory structure
- [ ] Create `server.py` with FastAPI/Flask: static file serving on port 6969, WebSocket endpoint, image upload endpoint
- [ ] Create `index.html` with: canvas element, file upload UI, WebSocket client, basic slider UI (all 7 sliders)
- [ ] Implement image upload flow: user selects files → sends to backend → backend stores in `uploads/` → confirms receipt
- [ ] Backend returns a simple test image to canvas to confirm the pipeline works end-to-end
- [ ] Create `requirements.txt` with initial dependencies
- [ ] Create `CLAUDE.md` with project rules (carried from v1 + new v2 rules)

**Deliverable:** Upload photos, see a test image on canvas, sliders exist but don't do anything yet.

### Phase 1: Preprocessing Pipeline
**Goal:** Every uploaded image gets analyzed and prepared for stamp creation.

- [ ] Implement `preprocessor.py`:
  - Subject mask generation using `rembg` (U2Net model, no GPU required)
  - Dominant color extraction (k-means clustering on image pixels)
  - Content variance map (identify high-detail vs. blank regions)
  - Edge map generation (Canny edge detection via OpenCV)
  - Store all outputs in `cache/` as: `{image_hash}_mask.png`, `{image_hash}_edges.png`, `{image_hash}_meta.json`
- [ ] Wire preprocessing into upload flow: upload → preprocess → ready signal to frontend
- [ ] Frontend shows preprocessing progress indicator

**Deliverable:** Upload photos, backend processes them and generates masks/metadata. Can view masks in cache directory to verify quality.

### Phase 2: Cut Path Generation
**Goal:** Generate the four cut types with humanized edges.

- [ ] Implement `cutter.py`:
  - **Silhouette cut:** Take subject mask → find contour → apply wobble displacement along path → occasional straight segments → output RGBA image with transparent background
  - **Loose tear:** Generate random organic blob shape (Perlin noise boundary) → loosely bias toward subject mask → apply as clip mask → output RGBA
  - **Geometric cut:** Generate rectangle/strip/triangle/polygon from parameters → apply as clip mask → output RGBA
  - **Raw crop:** Simple rectangular crop → output RGBA
- [ ] Wobble algorithm: walk along contour, at each point add displacement = `perlin_noise(t * freq) * amplitude`. Amplitude and frequency controlled by randomness. Occasionally snap to straight line for 5-20 pixels (scissors direction change).
- [ ] Test all four cut types independently — generate sample stamps from test images

**Deliverable:** Given an image + cut type + parameters, produce a properly cut RGBA stamp. Visual verification that silhouette cuts look hand-cut, not digitally perfect.

### Phase 3: Morphing
**Goal:** Stamps can be stretched, compressed, and deformed.

- [ ] Implement `morpher.py`:
  - Horizontal compression/stretch (independent X scale)
  - Vertical compression/stretch (independent Y scale)
  - Combined deformations
  - Input: RGBA stamp image + morph parameters → Output: deformed RGBA stamp
- [ ] Morph parameters derived from Morph Intensity slider value + random variation
- [ ] Test: take a silhouette-cut figure, compress it into a tall thin sliver. Take a landscape crop, stretch it into a wide ribbon.

**Deliverable:** Morphing works on pre-cut stamps. Visual verification of deformation range.

### Phase 4: Composition Engine — Basic
**Goal:** Generate a complete collage composition from the image pool.

- [ ] Implement `rules.py`:
  - Interpret slider values into concrete parameters
  - Assign stamp roles (background, dominant, supporting, detail, strips) based on Density slider
  - Select composition mode based on Composition Mode slider
  - Determine stamp count per role

- [ ] Implement `placer.py` — placement logic for each composition mode:
  - **Scenic:** Place dominant element center-ish. Supporting elements distributed with size suggesting depth. Details scattered.
  - **Symmetric:** Calculate mirror axis. Place stamps on one side, mirror to other. Center 1-2 elements on axis.
  - **Radial:** Place dominant element at center. Fan supporting elements outward at varied angles. Pack details at periphery.
  - **Framed:** Generate dense border region with small fragments. Place larger elements in interior.
  - **Experimental:** Blend parameters from multiple modes with random weighting.

- [ ] Implement `compositor.py`:
  - Orchestrate the full pipeline: read sliders → assign roles → select images → cut stamps → morph stamps → place stamps → return stamp data packet
  - For each stamp: select source image from pool (weighted random, allowing repeats), select cut type (weighted by Cut Style Bias slider), generate cut, apply morph, compute placement

- [ ] Wire compositor to backend API: frontend requests composition → backend runs compositor → returns stamp data JSON → frontend renders stamps on canvas

**Deliverable:** Upload photos, adjust sliders, see a generated collage composition on canvas. The composition should visibly respond to slider changes.

### Phase 5: Zoom Interaction
**Goal:** Scroll to zoom, trigger new compositions at depth.

- [ ] Implement scroll zoom on frontend canvas:
  - Mouse wheel → geometric zoom centered on cursor position
  - Smooth zoom animation (not instant jump)
  - Track current zoom level and center position

- [ ] Implement zoom threshold detection:
  - When zoom exceeds a threshold (e.g., 2×), request a new composition from backend
  - Pass the current visible region's stamps/tonal info as context
  - Backend generates new composition, optionally incorporating fragments from previous level

- [ ] Implement layer management on frontend:
  - Current composition layer
  - Next composition layer (loading/ready)
  - Previous composition layer (cached for zoom-out)
  - At minimum: keep 3 layers in memory (previous, current, next)

- [ ] Implement transition between compositions:
  - The new composition emerges from within the zoomed region
  - Explore: spatial dissolve (per-region hash snap from v1), stamp-by-stamp assembly, paper-tear effect
  - Tonal bridge: new composition's initial color palette influenced by zoomed region

**Deliverable:** Upload photos → see collage → scroll to zoom → new collage generates at depth → repeat infinitely. Smooth transitions between levels.

### Phase 6: Shape Borrowing & Collage-of-Collage
**Goal:** Advanced stamp generation techniques.

- [ ] Implement shape borrowing in `cutter.py`:
  - Extract silhouette from image A
  - Use that silhouette as a clip mask for image B's content
  - Creates surreal juxtapositions (person-shaped window into a landscape, etc.)

- [ ] Implement composition fragment reuse:
  - When generating a new zoom level, optionally capture rectangular regions of the current composition
  - Use those captured regions as source "images" for the new composition
  - These meta-stamps create visual recursion — collage of collage

- [ ] Wire both into compositor as additional stamp source options

**Deliverable:** Compositions occasionally feature shape-borrowed stamps and meta-fragments from previous zoom levels.

### Phase 7: Polish & Performance
**Goal:** Make it feel good and run smoothly.

- [ ] Optimize stamp generation pipeline:
  - Cache preprocessed masks (already in Phase 1)
  - Cache commonly-used stamps (same image + same cut at different crops)
  - Pre-generate stamps for the next zoom level while user is still exploring current one
  - Profile and optimize bottlenecks (rembg is slow — run once per image, not per stamp)

- [ ] Frontend rendering optimization:
  - Use WebGL for stamp compositing if Canvas2D is too slow
  - Limit re-renders to zoom/slider changes
  - Texture atlas for stamp images to reduce draw calls

- [ ] Zoom-out support:
  - Cache previous composition layers
  - Scrolling backward restores previous composition (not generating a new one)

- [ ] UI polish:
  - Slider labels and value display
  - Loading indicators during composition generation
  - Keyboard shortcuts (reset zoom, regenerate, etc.)
  - Fullscreen mode

- [ ] Add subtle breathing animation (very slight position/rotation drift on stamps over time, as specified in v1 aesthetic goals)

**Deliverable:** Smooth, responsive, visually polished infinite collage experience.

---

## 9. Dependencies

### Python (requirements.txt)

```
fastapi>=0.100.0
uvicorn>=0.23.0
websockets>=11.0
opencv-python-headless>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
rembg>=2.0.50
scikit-learn>=1.3.0        # for k-means color clustering
noise>=1.2.2               # for Perlin noise (wobble paths)
```

### Frontend

No npm. No build step. Single `index.html`. External libraries loaded via CDN if needed (unlikely — Canvas2D/WebGL are native).

---

## 10. Workflow Rules (Carry Forward from V1)

1. **Present a written plan before any code changes. Wait for explicit approval.**
2. Never commit directly to `main` — use `feature/name` branches.
3. Push every branch to GitHub immediately after creating it.
4. After finishing: "Branch `feature/name` is ready. Test on device and let me know — I'll merge to main on your say-so."
5. Only merge after Pat confirms it works on device.
6. Never delete branches.
7. No co-author tags in commit messages.
8. Port 6969 always.
9. No npm, no build pipeline.
10. `index.html` is the single frontend file.
11. Backend code lives in `engine/` module.
12. Python dependencies go in `requirements.txt`.
13. **Always ask before writing code or files — never demo unprompted.**
14. **For bulk/repetitive tasks, prioritize full automation and offer scripting proactively.**

---

## 11. CLAUDE.md Template

This should be placed at the project root for Claude Code sessions:

```markdown
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
[UPDATE THIS AS WORK PROGRESSES]
```

---

## 12. Open Questions / Decisions to Make During Build

These don't need answers now — they'll be resolved during implementation:

1. **rembg vs SAM for subject extraction:** rembg is simpler and lighter. SAM is more accurate but heavier. Start with rembg, upgrade if quality is insufficient.
2. **WebSocket vs REST for composition delivery:** WebSocket is better for streaming stamp data incrementally. REST is simpler. Start with REST, upgrade to WebSocket if latency is a problem.
3. **Canvas2D vs WebGL for frontend rendering:** Canvas2D is simpler for compositing RGBA images. WebGL is faster for many overlapping transparent layers. Start with Canvas2D, upgrade if performance is insufficient.
4. **Transition animation specifics:** The exact visual transition between zoom levels needs experimentation. Build a simple crossfade first, iterate toward something more physical.
5. **Pre-generation strategy:** How far ahead to pre-generate the next zoom level. Depends on generation speed, which depends on stamp count and image processing time.
6. **Zoom-out depth:** How many previous layers to cache. Memory vs. experience tradeoff.

---

---

## 13. Build Log & Deviations

*Append entries here as implementation diverges from the plan or decisions are made.*

### 2026-04-08 — Phases 0–4 complete

**Phase 0 (Foundation):** Complete and confirmed working.

**Phase 1 (Preprocessing):** Complete and confirmed working.
- `rembg` requires installation as `rembg[cpu]` (not bare `rembg`) to pull in `onnxruntime`. Updated in `requirements.txt`.
- If `onnxruntime` has no wheel for the current Python version, `preprocessor.py` catches `SystemExit` (not just `Exception`) and falls back to an OpenCV GrabCut mask. GrabCut is rougher but functional.

**Phase 2 (Cut Path Generation):** Complete and confirmed working.
- `noise` package replaced with `opensimplex>=0.4.5`. API: `opensimplex.seed(n)`, `opensimplex.noise2(x, y)`.
- All four cut types in `engine/cutter.py`: silhouette, tear, geometric, raw.
- Post-confirmation iteration: silhouette wobble now seed-derived (amplitude/frequency vary widely per seed); loose tear uses independent rx/ry noise + spike perturbations; triangle is scalene/seeded; wedge apex placed at image corners for dramatic fan cuts.
- `/test-cuts/{image_id}` endpoint + frontend test panel for visual QA.

**Phase 3 (Morphing):** Complete and confirmed working.
- `engine/morpher.py`: compress_x, stretch_x, compress_y, stretch_y, rotate, flip_h, flip_v, diagonal_stretch, combined.
- `shear` type repurposed: cuts an irregular polygon fragment from the stamp (jagged edges, tight-cropped) rather than a geometric lean — user-confirmed as the preferred behavior.
- Morph test row added to the cut test panel.

**Phase 4 (Composition Engine):** Built (2026-04-08) — pipeline functional but NOT user-confirmed complete. Still in testing and iteration.
- `engine/rules.py`: interprets all 7 sliders into a CompositionSpec (mode, stamp counts, role breakdown, cut weights, morph probability/intensity, rotation range, bleed, symmetry).
- `engine/placer.py`: 5 placement modes — scenic, symmetric, radial, framed, experimental. Experimental blends two modes.
- `engine/compositor.py`: full pipeline — rules → role assignment → cut_stamp → morph_stamp → place → alpha-composite → RGB PIL Image.
- `server.py`: `_run_composition()` replaces the Phase 0/1 stub. Runs in `asyncio.to_thread`. Returns JPEG (Option A — single composited image, simpler than stamp packets).
- `Pillow.alpha_composite` used as instance method (`canvas.alpha_composite(layer)`) not class method — `dest` kwarg not supported in this version.

**Known issues / priorities for next session:**
- Generation speed: currently several seconds per composition. Need stamp caching and pre-generation to approach real-time.
- Detail stamps (tiny fragments) need intentional clustering and more experimental variety to create compelling zoom targets. Currently scatter randomly.

*End of V2 plan. This document is the single source of truth for the project architecture. Update it as decisions are made during the build.*
