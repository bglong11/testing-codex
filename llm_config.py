from __future__ import annotations

"""Central utilities for selecting and validating LLM providers per pipeline step."""

from typing import Dict, Literal
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    _LLM_ENV_PATH = Path(__file__).parent / ".env"
    if _LLM_ENV_PATH.exists():
        load_dotenv(dotenv_path=_LLM_ENV_PATH, override=False)
except ImportError:
    pass

SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic", "gemini")

STEP_ENV_VARS: Dict[str, str] = {
    "step1": "LLM_PROVIDER_STEP1",
    "step2": "LLM_PROVIDER_STEP2",
    "step3": "LLM_PROVIDER_STEP3",
}

DEFAULT_PROVIDERS: Dict[str, str] = {
    "step1": "ollama",
    "step2": "openai",
    "step3": "openai",
}

MODEL_ENV_VARS: Dict[str, str] = {
    "ollama": "OLLAMA_MODEL",
    "openai": "OPENAI_MODEL",
    "anthropic": "ANTHROPIC_MODEL",
    "gemini": "GEMINI_MODEL",
}

DEFAULT_PROVIDER_MODELS: Dict[str, str] = {
    "ollama": "mistral:latest",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "gemini": "gemini-2.5-flash",
}

CREDENTIAL_REQUIREMENTS: Dict[str, Literal[False, str]] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama": False,
}

PROVIDER_ERROR_TEMPLATES: Dict[str, str] = {
    "openai": "OpenAI provider selected but OPENAI_API_KEY is not set in the environment.",
    "anthropic": "Anthropic provider selected but ANTHROPIC_API_KEY is not set in the environment.",
    "gemini": "Gemini provider selected but GEMINI_API_KEY is not set in the environment.",
}


def resolve_provider_for_step(step_name: str, override: str | None = None) -> str:
    """Determine which provider should run for the given pipeline step."""

    key = step_name.lower()
    if key not in STEP_ENV_VARS:
        raise ValueError(f"Unknown step name: {step_name}")

    if override:
        provider = override.strip().lower()
    else:
        provider = os.getenv(STEP_ENV_VARS[key])
        if provider:
            provider = provider.lower()
        else:
            provider = os.getenv("LLM_PROVIDER")
            if provider:
                provider = provider.lower()

    if not provider:
        provider = DEFAULT_PROVIDERS.get(key, "ollama")

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported LLM provider '{provider}'. Supported providers: {', '.join(SUPPORTED_PROVIDERS)}"
        )

    return provider


def ensure_provider_credentials(provider: str) -> None:
    """Raise if essential API keys or settings are missing for the requested provider."""

    normalized = provider.lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported provider '{provider}'. Supported: {', '.join(SUPPORTED_PROVIDERS)}"
        )

    requirement = CREDENTIAL_REQUIREMENTS.get(normalized)
    if requirement and not os.getenv(requirement):
        template = PROVIDER_ERROR_TEMPLATES.get(normalized)
        raise ValueError(template or f"Missing credentials for provider '{normalized}'")


def get_model_for_provider(provider: str) -> str:
    """Return the configured model name (env override or default) for a provider."""

    normalized = provider.lower()
    env_var = MODEL_ENV_VARS.get(normalized)
    if env_var and os.getenv(env_var):
        return os.getenv(env_var)
    return DEFAULT_PROVIDER_MODELS.get(normalized, "")
