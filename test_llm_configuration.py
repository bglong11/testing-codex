#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive LLM Configuration Test Script

Tests all supported LLM providers (Ollama, OpenAI, Anthropic, Gemini)
with detailed debugging output and diagnostics.

Usage:
    python test_llm_configuration.py [--provider PROVIDER] [--verbose]

Examples:
    python test_llm_configuration.py                    # Test all providers
    python test_llm_configuration.py --provider openai  # Test OpenAI only
    python test_llm_configuration.py --verbose          # Detailed output
"""


import sys
import io
import os
import time
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure UTF-8 output for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import dspy

# Determine repository root and .env path
SCRIPT_DIR = Path(__file__).resolve().parent
DOTENV_PATH = SCRIPT_DIR / ".env"
DOTENV_VALUES: Dict[str, str] = {}

def _strip_quotes(value: str) -> str:
    """Remove surrounding quotes from a dotenv value."""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value

def parse_dotenv_file(path: Path) -> Dict[str, str]:
    """Parse a dotenv file into a dict without relying on external dependencies."""
    entries: Dict[str, str] = {}
    if not path.exists():
        return entries

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()

        # Strip inline comments (only outside quotes)
        if "#" in value and not (value.startswith('"') or value.startswith("'")):
            value = value.split("#", 1)[0].strip()

        value = _strip_quotes(value)
        entries[key] = value

    return entries

def load_dotenv_entries(path: Path) -> Dict[str, str]:
    """Load dotenv entries into the environment, falling back when python-dotenv is unavailable."""
    parsed = parse_dotenv_file(path)
    if not parsed:
        return parsed

    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=True)
    except ImportError:
        for key, value in parsed.items():
            os.environ[key] = value
    else:
        for key, value in parsed.items():
            os.environ[key] = value

    return parsed

# Populate environment from .env file
DOTENV_VALUES = load_dotenv_entries(DOTENV_PATH)

API_KEY_PREFIXES = {
    "OPENAI_API_KEY": "sk-",
    "ANTHROPIC_API_KEY": "sk-",
    "GEMINI_API_KEY": "AIza"
}

def compare_with_dotenv(key: str, current_value: str, label: str):
    """Log when the resolved value differs from the .env definition."""
    expected = DOTENV_VALUES.get(key)
    if expected and expected != current_value:
        print(f"    ⚠ {label} from .env ({expected}) differs from resolved value ({current_value})")

def validate_api_key_format(env_key: str):
    """Ensure API key matches the expected prefix and formatting."""
    api_key = os.getenv(env_key)
    if not api_key:
        return

    prefix = API_KEY_PREFIXES.get(env_key)
    if prefix and not api_key.startswith(prefix):
        raise ValueError(
            f"{env_key} appears malformed; expected prefix '{prefix}', got '{api_key[:8]}...'."
        )

    if " " in api_key:
        raise ValueError(f"{env_key} should not contain spaces.")
# ============================================================================
# Utility Functions
# ============================================================================

def mask_api_key(api_key: str, show_chars: int = 8) -> str:
    """Mask API key for safe display, showing first N characters."""
    if not api_key or len(api_key) < show_chars:
        return "***" * 4
    return f"{api_key[:show_chars]}...{'*' * 12}"


def print_section(title: str, char: str = "=", width: int = 80):
    """Print a formatted section header."""
    print(f"\n{char * width}")
    print(title)
    print(f"{char * width}\n")


def print_subsection(title: str, char: str = "-", width: int = 80):
    """Print a formatted subsection header."""
    print(f"{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def get_env_value(key: str, default: str = None, mask: bool = False) -> str:
    """Safely get environment variable with optional masking."""
    value = os.getenv(key, default)
    if value and mask:
        value = mask_api_key(value)
    return value


def test_simple_prompt(lm, provider: str) -> Tuple[bool, str, float]:
    """Test simple LLM call to verify configuration."""
    try:
        start_time = time.time()

        # Simple prompt to test LLM is working
        response = lm(
            messages=[
                {
                    "role": "user",
                    "content": "What is 2+2? Answer with just the number."
                }
            ]
        )

        elapsed = time.time() - start_time

        return True, response, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return False, str(e), elapsed


# ============================================================================
# Provider-Specific Configuration Tests
# ============================================================================

def test_ollama_config(verbose: bool = False) -> Dict:
    """Test Ollama local configuration."""
    print_subsection("Testing Ollama Configuration")

    result = {
        "provider": "ollama",
        "status": "pending",
        "errors": [],
        "response_time": None
    }

    try:
        # Get configuration from environment
        model = os.getenv("OLLAMA_MODEL", "mistral:latest")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))

        print(f"  Environment:")
        print(f"    Model: {model}")
        print(f"    Base URL: {base_url}")
        print(f"    Temperature: {temperature}")
        print(f"    Max Tokens: {max_tokens}")

        # Check if Ollama service is running
        print(f"\n  Checking Ollama service...")
        try:
            import requests
            response = requests.get(f"{base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                print(f"    ✓ Ollama service running")
                models = response.json().get("models", [])
                print(f"    ✓ Found {len(models)} models available")

                # Check if our model is available
                model_names = [m.get("name", "") for m in models]
                if any(model in name for name in model_names):
                    print(f"    ✓ Model '{model}' is available")
                else:
                    print(f"    ⚠ Model '{model}' not found in: {model_names}")
        except Exception as e:
            result["errors"].append(f"Ollama service check failed: {e}")
            print(f"    ✗ Ollama service not accessible: {e}")

        # Try to create LM object
        print(f"\n  Creating LM object...")
        try:
            # Try dspy.OllamaLocal first (older API)
            lm = dspy.OllamaLocal(
                model=model,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except AttributeError:
            # Fall back to dspy.LM with ollama provider (newer API)
            print(f"    Note: Using dspy.LM with ollama provider")
            lm = dspy.LM(
                model=f"ollama/{model}",
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens
            )
        print(f"    ✓ LM object created")

        # Configure DSPy
        print(f"\n  Configuring DSPy...")
        dspy.configure(lm=lm)
        print(f"    ✓ DSPy configured")

        # Test simple prompt
        print(f"\n  Testing simple prompt...")
        success, response, elapsed = test_simple_prompt(lm, "ollama")
        result["response_time"] = elapsed

        if success:
            print(f"    ✓ Response received in {elapsed:.2f}s")
            print(f"    Response: {response[:100]}..." if len(response) > 100 else f"    Response: {response}")
            result["status"] = "success"
            print(f"\n  ✅ PASS: Ollama configuration successful")
        else:
            result["errors"].append(f"Prompt test failed: {response}")
            result["status"] = "failed"
            print(f"    ✗ Response failed: {response}")
            print(f"\n  ❌ FAIL: Ollama configuration failed")

    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        print(f"    ✗ Error: {e}")
        if verbose:
            traceback.print_exc()
        print(f"\n  ❌ FAIL: {str(e)[:100]}")

    return result


def test_openai_config(verbose: bool = False) -> Dict:
    """Test OpenAI configuration."""
    print_subsection("Testing OpenAI Configuration")

    result = {
        "provider": "openai",
        "status": "pending",
        "errors": [],
        "response_time": None
    }

    try:
        # Get configuration from environment
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2048"))

        print(f"  Environment:")
        print(f"    API Key: {mask_api_key(api_key)}")
        print(f"    Model: {model}")
        print(f"    Temperature: {temperature}")
        print(f"    Max Tokens: {max_tokens}")
        compare_with_dotenv("OPENAI_MODEL", model, "Model")

        # Validate API key
        print(f"\n  Validating API Key...")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        if api_key == "your-api-key-here":
            raise ValueError("OPENAI_API_KEY is placeholder value (your-api-key-here)")
        validate_api_key_format("OPENAI_API_KEY")
        print(f"    ✓ API key present and not placeholder")

        # Try to create LM object
        print(f"\n  Creating LM object...")
        lm = dspy.LM(
            model=f"openai/{model}",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )
        print(f"    ✓ LM object created")

        # Configure DSPy
        print(f"\n  Configuring DSPy...")
        dspy.configure(lm=lm)
        print(f"    ✓ DSPy configured")

        # Test simple prompt
        print(f"\n  Testing simple prompt...")
        success, response, elapsed = test_simple_prompt(lm, "openai")
        result["response_time"] = elapsed

        if success:
            print(f"    ✓ Response received in {elapsed:.2f}s")
            print(f"    Response: {response[:100]}..." if len(response) > 100 else f"    Response: {response}")
            result["status"] = "success"
            print(f"\n  ✅ PASS: OpenAI configuration successful")
        else:
            result["errors"].append(f"Prompt test failed: {response}")
            result["status"] = "failed"
            print(f"    ✗ Response failed: {response[:100]}")
            print(f"\n  ❌ FAIL: OpenAI configuration failed")

    except ValueError as e:
        result["status"] = "validation_error"
        result["errors"].append(str(e))
        print(f"    ✗ Validation error: {e}")
        print(f"\n  ❌ FAIL: {str(e)}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        error_str = str(e)
        if "401" in error_str or "authentication" in error_str.lower():
            print(f"    ✗ Authentication failed (invalid API key)")
            print(f"\n  ❌ FAIL: Invalid or expired API key")
        elif "401" in error_str or "quota" in error_str.lower():
            print(f"    ✗ API quota exceeded")
            print(f"\n  ❌ FAIL: API quota or rate limit exceeded")
        else:
            print(f"    ✗ Error: {error_str[:100]}")
            if verbose:
                traceback.print_exc()
            print(f"\n  ❌ FAIL: {error_str[:100]}")

    return result


def test_anthropic_config(verbose: bool = False) -> Dict:
    """Test Anthropic/Claude configuration."""
    print_subsection("Testing Anthropic Configuration")

    result = {
        "provider": "anthropic",
        "status": "pending",
        "errors": [],
        "response_time": None
    }

    try:
        # Get configuration from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        temperature = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048"))

        print(f"  Environment:")
        print(f"    API Key: {mask_api_key(api_key)}")
        print(f"    Model: {model}")
        print(f"    Temperature: {temperature}")
        print(f"    Max Tokens: {max_tokens}")

        # Validate API key
        print(f"\n  Validating API Key...")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        if api_key == "your-api-key-here":
            raise ValueError("ANTHROPIC_API_KEY is placeholder value (your-api-key-here)")
        validate_api_key_format("ANTHROPIC_API_KEY")
        print(f"    ✓ API key present and not placeholder")

        # Try to create LM object
        print(f"\n  Creating LM object...")
        lm = dspy.LM(
            model=f"anthropic/{model}",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )
        print(f"    ✓ LM object created")

        # Configure DSPy
        print(f"\n  Configuring DSPy...")
        dspy.configure(lm=lm)
        print(f"    ✓ DSPy configured")

        # Test simple prompt
        print(f"\n  Testing simple prompt...")
        success, response, elapsed = test_simple_prompt(lm, "anthropic")
        result["response_time"] = elapsed

        if success:
            print(f"    ✓ Response received in {elapsed:.2f}s")
            print(f"    Response: {response[:100]}..." if len(response) > 100 else f"    Response: {response}")
            result["status"] = "success"
            print(f"\n  ✅ PASS: Anthropic configuration successful")
        else:
            result["errors"].append(f"Prompt test failed: {response}")
            result["status"] = "failed"
            print(f"    ✗ Response failed: {response[:100]}")
            print(f"\n  ❌ FAIL: Anthropic configuration failed")

    except ValueError as e:
        result["status"] = "validation_error"
        result["errors"].append(str(e))
        print(f"    ✗ Validation error: {e}")
        print(f"\n  ❌ FAIL: {str(e)}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        error_str = str(e)
        if "401" in error_str or "authentication" in error_str.lower():
            print(f"    ✗ Authentication failed (invalid API key)")
            print(f"\n  ❌ FAIL: Invalid or expired API key")
        else:
            print(f"    ✗ Error: {error_str[:100]}")
            if verbose:
                traceback.print_exc()
            print(f"\n  ❌ FAIL: {error_str[:100]}")

    return result


def test_gemini_config(verbose: bool = False) -> Dict:
    """Test Google Gemini configuration."""
    print_subsection("Testing Gemini Configuration")

    result = {
        "provider": "gemini",
        "status": "pending",
        "errors": [],
        "response_time": None
    }

    try:
        # Get configuration from environment
        api_key = os.getenv("GEMINI_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-pro")
        temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))

        print(f"  Environment:")
        print(f"    API Key: {mask_api_key(api_key)}")
        print(f"    Model: {model}")
        print(f"    Temperature: {temperature}")
        print(f"    Max Tokens: {max_tokens}")

        # Validate API key
        print(f"\n  Validating API Key...")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        if api_key == "your-api-key-here":
            raise ValueError("GEMINI_API_KEY is placeholder value (your-api-key-here)")
        validate_api_key_format("GEMINI_API_KEY")
        print(f"    ✓ API key present and not placeholder")

        # Try to create LM object
        print(f"\n  Creating LM object...")
        lm = dspy.LM(
            model=f"gemini/{model}",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )
        print(f"    ✓ LM object created")

        # Configure DSPy
        print(f"\n  Configuring DSPy...")
        dspy.configure(lm=lm)
        print(f"    ✓ DSPy configured")

        # Test simple prompt
        print(f"\n  Testing simple prompt...")
        success, response, elapsed = test_simple_prompt(lm, "gemini")
        result["response_time"] = elapsed

        if success:
            print(f"    ✓ Response received in {elapsed:.2f}s")
            print(f"    Response: {response[:100]}..." if len(response) > 100 else f"    Response: {response}")
            result["status"] = "success"
            print(f"\n  ✅ PASS: Gemini configuration successful")
        else:
            result["errors"].append(f"Prompt test failed: {response}")
            result["status"] = "failed"
            print(f"    ✗ Response failed: {response[:100]}")
            print(f"\n  ❌ FAIL: Gemini configuration failed")

    except ValueError as e:
        result["status"] = "validation_error"
        result["errors"].append(str(e))
        print(f"    ✗ Validation error: {e}")
        print(f"\n  ❌ FAIL: {str(e)}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        error_str = str(e)
        if "401" in error_str or "authentication" in error_str.lower():
            print(f"    ✗ Authentication failed (invalid API key)")
            print(f"\n  ❌ FAIL: Invalid or expired API key")
        elif "invalid" in error_str.lower():
            print(f"    ✗ Invalid API key or model")
            print(f"\n  ❌ FAIL: Invalid API key")
        else:
            print(f"    ✗ Error: {error_str[:100]}")
            if verbose:
                traceback.print_exc()
            print(f"\n  ❌ FAIL: {error_str[:100]}")

    return result


# ============================================================================
# Main Test Orchestration
# ============================================================================

def run_all_provider_tests(specific_provider: str = None, verbose: bool = False) -> List[Dict]:
    """Run all provider configuration tests."""
    print_section("LLM Configuration Test Suite")
    if DOTENV_VALUES:
        print(f"Loaded {len(DOTENV_VALUES)} entries from {DOTENV_PATH}")
    else:
        print(f"  ⚠️  {DOTENV_PATH} not found or empty; relying on shell environment variables")
    print(f"Testing all LLM providers with detailed debugging output\n")

    results = []

    # Determine which providers to test
    providers_to_test = [specific_provider] if specific_provider else [
        "ollama",
        "openai",
        "anthropic",
        "gemini"
    ]

    # Run tests
    for provider in providers_to_test:
        if provider == "ollama":
            results.append(test_ollama_config(verbose))
        elif provider == "openai":
            results.append(test_openai_config(verbose))
        elif provider == "anthropic":
            results.append(test_anthropic_config(verbose))
        elif provider == "gemini":
            results.append(test_gemini_config(verbose))

    return results


def print_summary_report(results: List[Dict]):
    """Print comprehensive summary of all test results."""
    print_section("CONFIGURATION TEST SUMMARY")

    print("Provider Support:\n")

    for result in results:
        provider = result["provider"].capitalize()
        status = result["status"]
        response_time = result.get("response_time")

        if status == "success":
            time_str = f" - {response_time:.2f}s" if response_time else ""
            print(f"  ✅ {provider:12} PASS{time_str}")
        elif status == "failed":
            print(f"  ⚠️  {provider:12} FAIL (prompt test failed)")
        elif status == "validation_error":
            print(f"  ❌ {provider:12} FAIL (configuration error)")
        elif status == "error":
            print(f"  ❌ {provider:12} FAIL ({result['errors'][0][:40]}...)")
        else:
            print(f"  ❓ {provider:12} UNKNOWN")

    # Count results
    passed = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] != "success")
    total = len(results)

    print(f"\n{'':2} Total: {passed}/{total} providers functional")

    if passed == total:
        print(f"\n  ✅ Overall Status: ALL SYSTEMS GO")
    elif passed >= total // 2:
        print(f"\n  ⚠️  Overall Status: PARTIAL SUCCESS")
    else:
        print(f"\n  ❌ Overall Status: CRITICAL - Multiple providers failed")

    # Performance comparison
    successful = [r for r in results if r["response_time"] is not None]
    if successful:
        print(f"\nPerformance Ranking:")
        sorted_results = sorted(successful, key=lambda x: x["response_time"])
        for i, result in enumerate(sorted_results, 1):
            provider = result["provider"].capitalize()
            time_str = f"{result['response_time']:.2f}s"
            print(f"  {i}. {provider:12} {time_str}")

    # Recommendations
    print(f"\nRecommendations:")

    failed_providers = [r for r in results if r["status"] != "success"]
    if failed_providers:
        for result in failed_providers:
            provider = result["provider"].capitalize()
            error = result["errors"][0] if result["errors"] else "Unknown error"

            if "not set" in error:
                print(f"  - Add {result['provider'].upper()}_API_KEY to .env")
            elif "placeholder" in error:
                print(f"  - Update {result['provider'].upper()}_API_KEY in .env (current is placeholder)")
            elif "401" in error or "authentication" in error.lower():
                print(f"  - Check {result['provider'].upper()}_API_KEY validity")
            elif "Ollama" in provider and "not accessible" in error:
                print(f"  - Start Ollama service: ollama serve")
            elif "not found" in error.lower():
                print(f"  - Pull model: ollama pull {os.getenv('OLLAMA_MODEL', 'mistral:latest')}")

    if passed > 0:
        results_with_time = [r for r in results if r["response_time"] is not None and r["response_time"] > 0]
        if results_with_time:
            fastest = min(results_with_time, key=lambda x: x["response_time"])
            print(f"  - Fastest provider: {fastest['provider'].capitalize()} ({fastest['response_time']:.2f}s)")

    print()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test LLM provider configurations"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["ollama", "openai", "anthropic", "gemini"],
        help="Test specific provider only"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed error traces"
    )

    args = parser.parse_args()

    # Run tests
    results = run_all_provider_tests(args.provider, args.verbose)

    # Print summary
    print_summary_report(results)

    # Exit with appropriate code
    passed = sum(1 for r in results if r["status"] == "success")
    if passed == 0:
        sys.exit(1)
    elif passed < len(results):
        sys.exit(0)  # Partial success is acceptable
    else:
        sys.exit(0)  # Full success


if __name__ == "__main__":
    main()
