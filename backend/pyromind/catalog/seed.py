"""Hand-authored generic seed effects (no manufacturer names or SKUs)."""

from __future__ import annotations

import json
from typing import Any

COLORS = ["red", "green", "blue", "gold", "silver", "white", "purple", "orange"]
FAMILIES = ["shell", "comet", "mine", "cake", "candle", "ground"]
BURST_LABELS = [
    "chrysanthemum",
    "peony",
    "willow",
    "crossette",
    "brocade",
    "ring",
    "strobe",
    "crackle",
]
SHELL_CALIBERS = [1, 2, 3, 4, 5, 6, 8]


def _shell_physics(caliber: int) -> dict[str, Any]:
    """Approximate rise height, burst size, and timing for spherical shells."""
    height_m = float(min(220, max(20, caliber * 25)))
    burst_radius_m = float(min(95, max(8, caliber * 7.5)))
    duration_s = round(3.0 + (caliber % 5) * 0.35, 2)
    lift_time_ms = int(caliber * 72)
    prefire_ms = lift_time_ms + 280 + (caliber % 3) * 40
    return {
        "height_m": height_m,
        "burst_radius_m": burst_radius_m,
        "duration_s": duration_s,
        "lift_time_ms": lift_time_ms,
        "prefire_ms": prefire_ms,
    }


def _ground_family_physics(kind: str) -> dict[str, Any]:
    """Low-altitude ground display timing."""
    base = {
        "height_m": 2.5 if kind == "ground" else 8.0,
        "burst_radius_m": 12.0 if kind == "mine" else 18.0,
        "duration_s": 4.2,
        "lift_time_ms": 0,
        "prefire_ms": 120,
    }
    if kind == "candle":
        base.update({"height_m": 25.0, "burst_radius_m": 4.0, "duration_s": 45.0, "prefire_ms": 0})
    if kind == "cake":
        base.update({"height_m": 35.0, "burst_radius_m": 22.0, "duration_s": 28.0, "prefire_ms": 80})
    if kind == "comet":
        base.update({"height_m": 55.0, "burst_radius_m": 6.0, "duration_s": 2.4, "lift_time_ms": 0, "prefire_ms": 40})
    return base


def _build_seed_effects() -> list[dict[str, Any]]:
    """Construct exactly 50 catalog rows satisfying family, caliber, and color rules."""
    rows: list[dict[str, Any]] = []

    # Spherical shells — one row per listed caliber (7 sizes), varied burst motifs and colors.
    shell_colors = [COLORS[i % len(COLORS)] for i in range(len(SHELL_CALIBERS))]
    for caliber, burst, color in zip(
        SHELL_CALIBERS,
        BURST_LABELS[: len(SHELL_CALIBERS)],
        shell_colors,
        strict=True,
    ):
        phys = _shell_physics(caliber)
        rows.append(
            {
                "name": f"{caliber}-inch {color} {burst} aerial shell",
                "family": "shell",
                "caliber_in": caliber,
                "colors": json.dumps([color]),
                "duration_s": phys["duration_s"],
                "height_m": phys["height_m"],
                "burst_radius_m": phys["burst_radius_m"],
                "prefire_ms": phys["prefire_ms"],
                "lift_time_ms": phys["lift_time_ms"],
                "sound_level": "medium",
                "recommended_use": "sky burst",
                "description": (
                    f"Generic {caliber}-inch spherical shell with {burst} break "
                    f"and dominant {color} stars. Training-grade timing profile."
                ),
                "vdl_params_json": json.dumps({"break_style": burst, "dominant_hue": color}),
                "source": "generative",
                "license": "pyromind-internal",
                "provenance_url": None,
                "redistributable": 1,
            }
        )

    # Guarantee at least three appearances per named color (24 color-focused rows).
    color_cycle = COLORS * 3
    burst_cycle = BURST_LABELS * 3
    for k in range(24):
        color = color_cycle[k]
        burst = burst_cycle[k]
        family = FAMILIES[(k + 2) % len(FAMILIES)]
        caliber = None if family != "shell" else [3, 4, 5][k % 3]
        phys = _shell_physics(caliber) if caliber else _ground_family_physics(family)
        label = f"{family} {burst}" if family != "shell" else f"{caliber}-inch {burst}"
        rows.append(
            {
                "name": f"{color.title()} {label} display",
                "family": family,
                "caliber_in": caliber,
                "colors": json.dumps([color, "gold" if color != "gold" else "silver"]),
                "duration_s": phys["duration_s"],
                "height_m": phys["height_m"],
                "burst_radius_m": phys["burst_radius_m"],
                "prefire_ms": phys["prefire_ms"],
                "lift_time_ms": phys.get("lift_time_ms", 0),
                "sound_level": "low" if family in {"candle", "ground"} else "medium",
                "recommended_use": "mid-show texture",
                "description": (
                    f"Hand-authored generic {family} with {burst} motif; primary color {color}. "
                    "No proprietary supplier data."
                ),
                "vdl_params_json": json.dumps({"pattern": burst, "hue_primary": color}),
                "source": "generative",
                "license": "pyromind-internal",
                "provenance_url": None,
                "redistributable": 1,
            }
        )

    # Remaining rows to reach 50 while balancing families and combinations.
    while len(rows) < 50:
        n = len(rows)
        family = FAMILIES[n % len(FAMILIES)]
        color = COLORS[(n * 3) % len(COLORS)]
        burst = BURST_LABELS[n % len(BURST_LABELS)]
        caliber = [4, 5, 6][n % 3] if family == "shell" else None
        phys = _shell_physics(caliber) if caliber else _ground_family_physics(family)
        rows.append(
            {
                "name": f"{color} {burst} {family} sequence #{n - 31}",
                "family": family,
                "caliber_in": caliber,
                "colors": json.dumps([color, COLORS[(n + 1) % len(COLORS)]]),
                "duration_s": round(phys["duration_s"] + 0.05 * (n % 4), 2),
                "height_m": phys["height_m"],
                "burst_radius_m": phys["burst_radius_m"],
                "prefire_ms": phys["prefire_ms"],
                "lift_time_ms": phys.get("lift_time_ms", 0),
                "sound_level": "medium",
                "recommended_use": "layered sky",
                "description": (
                    f"Generic {family} choreography element using {burst} visual language "
                    f"with {color} emphasis."
                ),
                "vdl_params_json": json.dumps({"burst": burst, "tone": color}),
                "source": "generative",
                "license": "pyromind-internal",
                "provenance_url": None,
                "redistributable": 1,
            }
        )

    return rows[:50]


SEED_EFFECTS: list[dict[str, Any]] = _build_seed_effects()
