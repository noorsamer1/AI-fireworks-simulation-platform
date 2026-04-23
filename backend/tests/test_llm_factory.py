"""LLM factory wiring tests (no network calls)."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_openai import ChatOpenAI

from pyromind.config import Settings


def test_get_llm_openrouter_returns_chatopenai(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenRouter provider yields a ChatOpenAI instance with a dummy key."""
    from pyromind.llm import get_llm

    monkeypatch.setattr(
        "pyromind.config.settings",
        Settings(
            db_path=str(tmp_path / "llm.sqlite"),
            llm_provider="openrouter",
            openrouter_api_key="sk-dummy-not-used",
        ),
    )
    llm = get_llm()
    assert isinstance(llm, ChatOpenAI)
