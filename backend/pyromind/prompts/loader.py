"""Load prompt templates from the prompts/ directory."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Load a prompt template by filename (without extension).

    Args:
        name: Base filename under ``prompts/`` (e.g. ``show_director``).

    Returns:
        UTF-8 file contents.

    Raises:
        FileNotFoundError: If ``{name}.md`` does not exist.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        msg = f"Prompt not found: {name}"
        raise FileNotFoundError(msg)
    return path.read_text(encoding="utf-8")
