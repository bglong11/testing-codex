"""Tests for LLM configuration module"""
import pytest
from llm_config import (
    resolve_provider_for_step,
    ensure_provider_credentials,
    get_model_for_provider,
    SUPPORTED_PROVIDERS,
    DEFAULT_PROVIDERS,
)


class TestLLMConfig:
    """Test suite for LLM configuration utilities"""

    @pytest.mark.unit
    def test_supported_providers(self):
        """Test that supported providers are defined"""
        assert len(SUPPORTED_PROVIDERS) > 0
        assert "ollama" in SUPPORTED_PROVIDERS
        assert "openai" in SUPPORTED_PROVIDERS
        assert "anthropic" in SUPPORTED_PROVIDERS
        assert "gemini" in SUPPORTED_PROVIDERS

    @pytest.mark.unit
    def test_default_providers_defined(self):
        """Test that default providers are defined for each step"""
        assert "step1" in DEFAULT_PROVIDERS
        assert "step2" in DEFAULT_PROVIDERS
        assert "step3" in DEFAULT_PROVIDERS

    @pytest.mark.unit
    def test_resolve_provider_with_override(self):
        """Test provider resolution with explicit override"""
        provider = resolve_provider_for_step("step1", override="openai")
        assert provider == "openai"

    @pytest.mark.unit
    def test_resolve_provider_fallback(self):
        """Test provider resolution falls back to defaults"""
        provider = resolve_provider_for_step("step1", override=None)
        assert provider in SUPPORTED_PROVIDERS

    @pytest.mark.unit
    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError"""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            resolve_provider_for_step("step1", override="invalid_provider")

    @pytest.mark.unit
    def test_get_model_for_provider(self):
        """Test model retrieval for providers"""
        for provider in SUPPORTED_PROVIDERS:
            model = get_model_for_provider(provider)
            assert isinstance(model, str)
            assert len(model) > 0

    @pytest.mark.unit
    def test_ensure_provider_credentials_ollama(self):
        """Test that ollama doesn't require credentials"""
        # Should not raise
        ensure_provider_credentials("ollama")


class TestProviderValidation:
    """Test provider validation logic"""

    @pytest.mark.unit
    def test_invalid_step_name(self):
        """Test that invalid step name raises error"""
        with pytest.raises(ValueError, match="Unknown step name"):
            resolve_provider_for_step("invalid_step")

    @pytest.mark.unit
    @pytest.mark.parametrize("step", ["step1", "step2", "step3"])
    def test_all_steps_resolve(self, step):
        """Test that all valid steps can resolve a provider"""
        provider = resolve_provider_for_step(step)
        assert provider in SUPPORTED_PROVIDERS
