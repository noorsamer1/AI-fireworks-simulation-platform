"""Factory for LangChain chat models (OpenRouter, Ollama, Anthropic)."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

import pyromind.config as _pm_config


def get_llm(temperature: float | None = None, seed: int | None = None):
    """Return a configured chat model for the active `llm_provider` setting.

    Args:
        temperature: Overrides ``settings.llm_temperature`` when set.
        seed: Overrides ``settings.llm_seed`` when set (OpenRouter / Ollama).

    Returns:
        A LangChain ``BaseChatModel`` instance.

    Raises:
        ValueError: If ``llm_provider`` is not recognized.
    """
    s_cfg = _pm_config.settings
    t = temperature if temperature is not None else s_cfg.llm_temperature
    s = seed if seed is not None else s_cfg.llm_seed
    if s_cfg.llm_provider == "openrouter":
        return ChatOpenAI(
            base_url=s_cfg.openrouter_base_url,
            api_key=s_cfg.openrouter_api_key,
            model=s_cfg.openrouter_model,
            temperature=t,
            seed=s,
            max_tokens=s_cfg.llm_max_tokens,
            default_headers={
                "HTTP-Referer": "https://pyromind.app",
                "X-Title": "PyroMind",
            },
        )
    if s_cfg.llm_provider == "ollama":
        return ChatOllama(
            base_url=s_cfg.ollama_base_url,
            model=s_cfg.ollama_model,
            temperature=t,
            seed=s,
            num_predict=s_cfg.llm_max_tokens,
        )
    if s_cfg.llm_provider == "anthropic":
        return ChatAnthropic(
            api_key=s_cfg.anthropic_api_key,
            model=s_cfg.anthropic_model,
            temperature=t,
            max_tokens=s_cfg.llm_max_tokens,
        )
    raise ValueError(f"Unknown LLM provider: {s_cfg.llm_provider}")
