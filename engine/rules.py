"""
Rules — Phase 4
Interprets slider values into a concrete CompositionSpec that drives
the placer and compositor.

Public API:
    interpret_sliders(sliders, seed) -> dict  (CompositionSpec)

CompositionSpec keys:
    mode            : str   — scenic | symmetric | radial | framed | experimental
    stamp_count     : int   — total stamps (background excluded)
    role_counts     : dict  — {dominant, supporting, detail, strip}
    cut_weights     : dict  — {silhouette, tear, geometric, raw} per role
    morph_prob      : float — probability any given stamp is morphed
    morph_intensity : float — intensity fed to morph_stamp
    rotation_range  : float — max rotation in degrees
    allow_bleed     : bool  — stamps allowed to extend beyond canvas edges
    bg_type         : str   — photo | color | none
    symmetry        : bool  — mirror flag for placer
"""

import random


# ── Composition modes ─────────────────────────────────────────────────────────

_MODES = ["scenic", "symmetric", "radial", "framed", "experimental"]


def interpret_sliders(sliders: dict, seed: int) -> dict:
    """
    Convert the 7 slider values (each 0.0–1.0) into a CompositionSpec dict.
    """
    rng = random.Random(seed)

    cm   = float(sliders.get("composition_mode",    0.5))
    bp   = float(sliders.get("background_presence", 0.5))
    csb  = float(sliders.get("cut_style_bias",      0.5))
    mi   = float(sliders.get("morph_intensity",     0.5))
    dens = float(sliders.get("density",             0.5))
    sym  = float(sliders.get("symmetry",            0.0))
    fs   = float(sliders.get("fragment_scatter",    0.5))

    # ── Composition mode ──────────────────────────────────────────────────────
    # Low cm → committed to one structured mode.
    # High cm → experimental or random blend.
    if cm < 0.20:
        mode = "scenic"
    elif cm < 0.40:
        mode = "symmetric"
    elif cm < 0.60:
        mode = "radial"
    elif cm < 0.80:
        mode = "framed"
    else:
        mode = "experimental"

    # ── Background type ───────────────────────────────────────────────────────
    if bp > 0.75:
        bg_type = "none"
    elif bp > 0.35:
        bg_type = "color"
    else:
        bg_type = "photo"

    # ── Stamp count from density ──────────────────────────────────────────────
    # density 0 → 5 stamps, density 1 → 32 stamps
    total = max(5, int(5 + dens * 27))

    # ── Role counts ───────────────────────────────────────────────────────────
    dominant   = rng.randint(1, 2)
    strips     = int(dens * 4)               # 0–4 strips depending on density
    remaining  = total - dominant - strips
    supporting = max(1, int(remaining * 0.35))
    detail     = max(1, remaining - supporting)

    role_counts = {
        "dominant":   dominant,
        "supporting": supporting,
        "detail":     detail,
        "strip":      strips,
    }

    # ── Cut weights per role ──────────────────────────────────────────────────
    # csb 0 → silhouette-heavy; csb 1 → geometric-heavy
    sil_w  = max(0.05, 0.70 - csb * 0.60)
    tear_w = max(0.05, 0.20 - csb * 0.10)
    geo_w  = max(0.05, 0.05 + csb * 0.60)
    raw_w  = max(0.05, 0.05 + csb * 0.25)
    total_w = sil_w + tear_w + geo_w + raw_w

    cut_weights = {
        "dominant": {
            "silhouette": sil_w  / total_w,
            "tear":       tear_w / total_w,
            "geometric":  geo_w  / total_w,
            "raw":        raw_w  / total_w,
        },
        "supporting": {
            "silhouette": (sil_w * 0.6)  / total_w,
            "tear":       (tear_w * 1.2) / total_w,
            "geometric":  (geo_w * 1.3)  / total_w,
            "raw":        (raw_w * 0.9)  / total_w,
        },
        "detail": {
            "silhouette": 0.10,
            "tear":       0.20,
            "geometric":  0.35,
            "raw":        0.35,
        },
        "strip": {
            "silhouette": 0.0,
            "tear":       0.0,
            "geometric":  1.0,
            "raw":        0.0,
        },
    }

    # ── Morph parameters ──────────────────────────────────────────────────────
    # At mi=0: almost no morphing. At mi=1: most stamps morphed, heavily.
    morph_prob      = mi * 0.85
    morph_intensity = 0.15 + mi * 0.80

    # ── Rotation range ────────────────────────────────────────────────────────
    # fs 0 → stamps nearly aligned (±3°); fs 1 → wild rotation (±180°)
    rotation_range = 3.0 + fs * 177.0

    # ── Bleed ─────────────────────────────────────────────────────────────────
    allow_bleed = fs > 0.4

    # ── Symmetry ─────────────────────────────────────────────────────────────
    use_symmetry = sym > 0.5

    return {
        "mode":           mode,
        "bg_type":        bg_type,
        "stamp_count":    total,
        "role_counts":    role_counts,
        "cut_weights":    cut_weights,
        "morph_prob":     morph_prob,
        "morph_intensity": morph_intensity,
        "rotation_range": rotation_range,
        "allow_bleed":    allow_bleed,
        "symmetry":       use_symmetry,
    }
