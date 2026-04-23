"""
ShowDirectorAgent — turns AudioAnalysis + UserConstraints into ShowPlan.

Uses LLM with structured JSON output. Temperature 0.7, seeded.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from pyromind.agents.base import agent_node
from pyromind.graph.state import ShowState
from pyromind.llm import get_llm
from pyromind.models.audio import AudioAnalysis, Section
from pyromind.models.plan import PlanSection, ShowPlan
from pyromind.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
_EXAMPLES_PATH = Path(__file__).resolve().parents[1] / "prompts" / "show_director_examples.json"


def _load_few_shot_examples() -> list[dict[str, Any]]:
    raw = _EXAMPLES_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        msg = "show_director_examples.json must be a JSON array"
        raise ValueError(msg)
    return data


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse the first top-level JSON object from model output."""
    s = text.strip()
    if "```" in s:
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        msg = "no JSON object found in model output"
        raise ValueError(msg)
    return json.loads(s[start : end + 1])


def _normalize_budget(plan_dict: dict[str, Any]) -> dict[str, Any]:
    """Scale ``budget_distribution`` to sum to 1.0 when within tolerance."""
    bd = plan_dict.get("budget_distribution")
    if not isinstance(bd, dict) or not bd:
        return plan_dict
    vals = {str(k): float(v) for k, v in bd.items()}
    total = sum(vals.values())
    if total <= 0:
        return plan_dict
    diff = abs(1.0 - total)
    if diff < 0.05:
        scale = 1.0 / total
        plan_dict = {**plan_dict, "budget_distribution": {k: v * scale for k, v in vals.items()}}
        if diff > 1e-6:
            logger.warning("Normalized budget_distribution from %s to 1.0", total)
    return plan_dict


def _sync_arc_to_audio(plan_dict: dict[str, Any], n_sections: int) -> dict[str, Any]:
    """Trim or pad ``arc`` so length matches ``n_sections``."""
    arc = plan_dict.get("arc")
    if not isinstance(arc, list) or n_sections <= 0:
        return plan_dict
    if len(arc) == n_sections:
        return plan_dict
    if len(arc) > n_sections:
        plan_dict = {**plan_dict, "arc": arc[:n_sections]}
        logger.warning("Trimmed plan arc from %s to %s sections", len(arc), n_sections)
        return plan_dict
    last = arc[-1] if arc else {}
    pad = []
    for i in range(len(arc), n_sections):
        template = dict(last) if isinstance(last, dict) else {}
        template["audio_section_index"] = i
        template.setdefault("intent", "continuation")
        template.setdefault("intensity", 0.5)
        template.setdefault("density_per_min", 12)
        template.setdefault("dominant_colors", [])
        template.setdefault("preferred_effect_families", ["shell"])
        template.setdefault("avoid", [])
        pad.append(template)
    plan_dict = {**plan_dict, "arc": list(arc) + pad}
    logger.warning("Padded plan arc from %s to %s sections", len(arc), n_sections)
    return plan_dict


def _mood_labels(mood_vector: list[float]) -> str:
    if not mood_vector:
        return "(no mood vector)"
    parts = [f"dim{i}={v:.2f}" for i, v in enumerate(mood_vector[:12])]
    return "; ".join(parts)


def _sections_summary(sections: list[Section]) -> str:
    lines = []
    for s in sections:
        lines.append(
            f"- [{s.label}] {s.start_s:.1f}-{s.end_s:.1f}s energy={s.energy:.2f} novelty={s.novelty:.2f}"
        )
    return "\n".join(lines) if lines else "(no sections)"


def _build_user_message(state: ShowState) -> str:
    """Build the user-turn payload for the ShowDirector LLM (concise)."""
    audio = state.get("audio")
    if isinstance(audio, dict):
        audio = AudioAnalysis.model_validate(audio)
    if not isinstance(audio, AudioAnalysis):
        return json.dumps({"error": "missing_audio"})
    uc = state["user_constraints"]
    n = len(audio.sections)
    payload = {
        "song": {
            "duration_s": audio.duration_s,
            "tempo_bpm": audio.tempo_bpm,
            "key": audio.key,
            "mode": audio.mode,
            "downbeats_count": len(audio.downbeats_s),
            "sections_count": n,
            "sections": _sections_summary(audio.sections),
            "mood_vector": _mood_labels(audio.mood_vector),
        },
        "constraints": {
            "budget_tier": uc.budget_tier,
            "mood_tags": uc.mood_tags,
            "color_palette": uc.color_palette,
            "finale_style": uc.finale_style,
            "calibers_allowed": uc.calibers_allowed,
            "site": {
                "width_m": uc.site.width_m,
                "depth_m": uc.site.depth_m,
                "max_ceiling_m": uc.site.max_ceiling_m,
                "audience_distance_m": uc.site.audience_distance_m,
            },
        },
        "instruction": (
            f"Produce a ShowPlan JSON with exactly {n} arc entries "
            f"(audio_section_index 0..{n - 1}). budget_distribution must sum to 1.0."
        ),
    }
    return json.dumps(payload, indent=2)


def _build_messages(system_prompt: str, examples: list[dict[str, Any]], user_msg: str) -> list:
    messages: list = [SystemMessage(content=system_prompt)]
    for ex in examples:
        messages.append(
            HumanMessage(
                content=json.dumps(
                    {
                        "audio_summary": ex["audio_summary"],
                        "user_constraints": ex["user_constraints"],
                    },
                    indent=2,
                )
            )
        )
        messages.append(AIMessage(content=json.dumps(ex["show_plan"])))
    messages.append(HumanMessage(content=user_msg))
    return messages


@agent_node("show_director")
def show_director_node(state: ShowState) -> ShowState:
    """Build a validated :class:`ShowPlan` from audio + constraints via LLM."""
    audio = state.get("audio")
    if audio is None:
        errs = list(state.get("errors", [])) + ["show_director: missing audio analysis"]
        return {**state, "errors": errs}
    if isinstance(audio, dict):
        audio = AudioAnalysis.model_validate(audio)
    n_sections = len(audio.sections)
    if n_sections == 0:
        errs = list(state.get("errors", [])) + ["show_director: audio has zero sections"]
        return {**state, "errors": errs}

    t0 = time.perf_counter()
    logger.info("[show_director] starting (sections=%s)", n_sections)

    system = load_prompt("show_director")
    examples = _load_few_shot_examples()
    user_msg = _build_user_message(state)
    messages = _build_messages(system, examples, user_msg)
    seed = int(state.get("seed", 42))
    llm = get_llm(temperature=0.7, seed=seed)
    strict_reminder = (
        "\n\nYour previous reply was not valid JSON. Output ONLY one JSON object for ShowPlan, "
        "no markdown, no commentary."
    )
    last_err = ""
    for attempt in range(MAX_RETRIES + 1):
        try:
            logger.info(
                "[show_director] LLM call %s/%s...",
                attempt + 1,
                MAX_RETRIES + 1,
            )
            msgs = messages if attempt == 0 else messages + [HumanMessage(content=strict_reminder)]
            resp = llm.invoke(msgs)
            content = resp.content
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part) for part in content
                )
            raw = _extract_json_object(str(content))
            raw = _normalize_budget(raw)
            raw = _sync_arc_to_audio(raw, n_sections)
            plan = ShowPlan.model_validate(raw)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            logger.info("[ShowDirector] plan produced: %s", plan.model_dump_json(indent=2))
            logger.info("[show_director] plan parsed successfully")
            logger.info("[show_director] completed in %sms", elapsed_ms)
            return {**state, "plan": plan}
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            last_err = str(exc)
            logger.warning("show_director parse attempt %s failed: %s", attempt + 1, exc)
            if attempt < MAX_RETRIES:
                logger.warning(
                    "[show_director] JSON parse failed, retrying (%s/%s): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    last_err,
                )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.error("[show_director] failed after %sms: %s", elapsed_ms, last_err)
    errs = list(state.get("errors", [])) + [f"show_director: failed after retries: {last_err}"]
    return {**state, "errors": errs}
