# -*- coding: utf-8 -*-
"""
ESIA Fact Extraction System using DSPy and Qwen2.5:7B-Instruct

This module implements the complete workflow for extracting, canonicalizing,
and quality-checking facts from ESIA markdown documents.
"""

import dspy
import sys
import io
import json
import re
import os
import pandas as pd
from typing import List, Dict, Any, Optional, Literal
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
import unicodedata
import pickle
from datetime import datetime

# Configure UTF-8 output for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Try to import tqdm for progress bar
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Note: Install 'tqdm' for progress bar: pip install tqdm")

def _load_llm_env():
    """Load `.env` if present so environment values are available to LLM helpers."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file, verbose=False, override=False)
        except ImportError:
            pass


def peek_llm_configuration():
    """Return the provider/model that will be used for the next LLM configuration."""
    _load_llm_env()
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "mistral:latest")
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4")
    elif provider == "anthropic":
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
    elif provider == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-pro")
    else:
        model = None
    return provider, model


LLM_PROVIDER_DISPLAY_NAMES = {
    "ollama": "Ollama",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
}


# ============================================================================
# DSPy Configuration
# ============================================================================

def configure_llm():
    """
    Configure DSPy to use any supported LLM provider.

    Supports multiple providers:
    - ollama (local, free): Mistral, Qwen, etc.
    - openai (cloud): GPT-4, GPT-3.5-turbo
    - anthropic (cloud): Claude 3 variants
    - gemini (cloud): Google Gemini

    Configuration via .env file or environment variables.
    Default: ollama with mistral:latest
    """
    _load_llm_env()

    # Determine which provider to use
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    print(f"🤖 Configuring LLM:")
    print(f"   Provider: {provider}")

    # ========================================================================
    # OLLAMA (Local)
    # ========================================================================
    if provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "mistral:latest")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))

        print(f"   Model: {model}")
        print(f"   Base URL: {base_url}")
        print(f"   Temperature: {temperature}")
        print(f"   Max tokens: {max_tokens}")

        lm = dspy.LM(
            f"ollama_chat/{model}",
            api_base=base_url,
            api_key="",
            temperature=temperature,
            max_tokens=max_tokens
        )

    # ========================================================================
    # OPENAI (Cloud)
    # ========================================================================
    elif provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your-api-key-here":
            raise ValueError(
                "OPENAI_API_KEY not set in .env file. "
                "Get it from https://platform.openai.com/"
            )

        model = os.getenv("OPENAI_MODEL", "gpt-4")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "2048"))

        print(f"   Model: {model}")
        print(f"   Temperature: {temperature}")
        print(f"   Max tokens: {max_tokens}")

        # Use DSPy's LM with OpenAI
        lm = dspy.LM(
            model=f"openai/{model}",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )

    # ========================================================================
    # ANTHROPIC/CLAUDE (Cloud)
    # ========================================================================
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "your-api-key-here":
            raise ValueError(
                "ANTHROPIC_API_KEY not set in .env file. "
                "Get it from https://console.anthropic.com/"
            )

        model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        temperature = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048"))

        print(f"   Model: {model}")
        print(f"   Temperature: {temperature}")
        print(f"   Max tokens: {max_tokens}")

        # Use DSPy's LM with Anthropic/Claude
        lm = dspy.LM(
            model=f"anthropic/{model}",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )

    # ========================================================================
    # GOOGLE GEMINI (Cloud)
    # ========================================================================
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your-api-key-here":
            raise ValueError(
                "GEMINI_API_KEY not set in .env file. "
                "Get it from https://ai.google.dev/"
            )

        model = os.getenv("GEMINI_MODEL", "gemini-pro")
        temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
        max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))

        print(f"   Model: {model}")
        print(f"   Temperature: {temperature}")
        print(f"   Max tokens: {max_tokens}")

        # Use DSPy's LM with Gemini
        lm = dspy.LM(
            model=f"gemini/{model}",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )

    # ========================================================================
    # UNKNOWN PROVIDER
    # ========================================================================
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            "Supported: ollama, openai, anthropic, gemini"
        )

    # Configure DSPy with the selected model
    dspy.configure(lm=lm)
    return lm


# ============================================================================
# DSPy Signatures
# ============================================================================

class FactExtraction(dspy.Signature):
    """Extract quantitative and categorical facts from ESIA text.

    Think step by step:
    1. Read the text carefully
    2. Identify quantitative facts (numbers with units) and categorical facts (classifications)
    3. For each fact, output in this EXACT format (one fact per block, separated by ---)

    FORMAT FOR EACH FACT:
    FACT: [Short descriptive name]
    TYPE: [quantity or categorical]
    VALUE: [The value as text]
    VALUE_NUM: [Numeric value, 0 for categorical]
    UNIT: [Unit of measurement, empty for categorical]
    EVIDENCE: [Direct quote from text]
    ---

    Example output:
    FACT: Project area
    TYPE: quantity
    VALUE: 500
    VALUE_NUM: 500
    UNIT: hectares
    EVIDENCE: The project will cover an area of 500 hectares
    ---
    """
    text = dspy.InputField(desc="Text chunk from ESIA document")
    output = dspy.OutputField(
        desc="Facts in structured text format. One fact per block. Separate blocks with ---"
    )


class FactCategorizationSignature(dspy.Signature):
    """Intelligently categorize an ESIA fact into logical project section.

    Use domain knowledge to assign facts to appropriate categories and subcategories.
    For ambiguous facts, choose the most relevant category based on context."""

    fact_name: str = dspy.InputField(
        desc="Name/title of the extracted fact (e.g., 'Project area', 'Annual CO2 emissions')"
    )
    fact_value: str = dspy.InputField(
        desc="The value of the fact (e.g., '500', 'yes', 'coal-fired')"
    )
    fact_unit: str = dspy.InputField(
        desc="Unit of measurement if numeric (e.g., 'ha', 'MW', 'tonnes/yr'). Empty string for categorical."
    )

    category: Literal[
        "Project Overview",
        "Project Description",
        "Environmental Impacts",
        "Social Impacts",
        "Economic Impacts",
        "Health & Safety",
        "Governance & Management",
        "Risks & Issues"
    ] = dspy.OutputField(
        desc="Primary category for this fact"
    )

    subcategory: Literal[
        # Project Overview (2)
        "Basic Info", "Timeline",
        # Project Description (5)
        "Financing", "Capacity/Scale", "Technology", "Infrastructure", "Location",
        # Environmental Impacts (6)
        "Water", "Air", "Land", "Biodiversity", "Waste", "Emissions",
        # Social Impacts (4)
        "Employment", "Resettlement", "Community", "Cultural",
        # Economic Impacts (3)
        "Investment", "Revenue", "Local Procurement",
        # Health & Safety (3)
        "Occupational", "Public Health", "Emergency",
        # Governance & Management (3)
        "Institutional", "Monitoring", "Engagement",
        # Risks & Issues (3)
        "Identified Risks", "Uncertainties", "Conflicts"
    ] = dspy.OutputField(
        desc="Specific subcategory within the primary category"
    )

    confidence: Literal["high", "medium", "low"] = dspy.OutputField(
        desc="Confidence level in the categorization (high=clear fit, medium=reasonable fit, low=ambiguous)"
    )

    rationale: str = dspy.OutputField(
        desc="Brief explanation for the categorization decision (1 sentence)"
    )


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Fact:
    """Represents a single extracted fact"""
    name: str
    type: str  # 'quantity' or 'categorical'
    value: str
    value_num: float
    unit: str
    aliases: List[str]
    evidence: str
    page: int
    chunk_id: int
    signature: str = ""
    normalized_value: float = 0.0
    normalized_unit: str = ""


# ============================================================================
# Unit Normalization
# ============================================================================

UNIT_CONVERSIONS = {
    # Mass
    'kg': ('kg', 1.0),
    't': ('kg', 1000.0),
    'tonne': ('kg', 1000.0),
    'tonnes': ('kg', 1000.0),
    'ton': ('kg', 1000.0),
    'tons': ('kg', 1000.0),
    'mt': ('kg', 1000.0),
    'Mt': ('kg', 1000000.0),
    'g': ('kg', 0.001),
    'mg': ('kg', 0.000001),

    # Mass rate
    't/yr': ('kg/yr', 1000.0),
    'Mt/yr': ('kg/yr', 1000000.0),
    'tonnes/year': ('kg/yr', 1000.0),
    'kg/yr': ('kg/yr', 1.0),

    # Area
    'ha': ('ha', 1.0),
    'hectare': ('ha', 1.0),
    'hectares': ('ha', 1.0),
    'km²': ('ha', 100.0),
    'km2': ('ha', 100.0),
    'm²': ('ha', 0.0001),
    'm2': ('ha', 0.0001),
    'acre': ('ha', 0.404686),
    'acres': ('ha', 0.404686),

    # Power
    'MW': ('MW', 1.0),
    'kW': ('MW', 0.001),
    'GW': ('MW', 1000.0),
    'W': ('MW', 0.000001),

    # Energy
    'MWh': ('MWh', 1.0),
    'kWh': ('MWh', 0.001),
    'GWh': ('MWh', 1000.0),
    'MWh/yr': ('MWh/yr', 1.0),

    # Volume
    'L': ('L', 1.0),
    'l': ('L', 1.0),
    'mL': ('L', 0.001),
    'ml': ('L', 0.001),
    'm³': ('L', 1000.0),
    'm3': ('L', 1000.0),

    # Concentration
    'mg/L': ('mg/L', 1.0),
    'mg/l': ('mg/L', 1.0),
    'g/L': ('mg/L', 1000.0),
    'ppm': ('mg/L', 1.0),  # Approximate for water
    'mg/Nm³': ('mg/Nm3', 1.0),
    'mg/Nm3': ('mg/Nm3', 1.0),

    # Distance
    'km': ('km', 1.0),
    'm': ('km', 0.001),
    'cm': ('km', 0.00001),
    'mm': ('km', 0.000001),

    # Flow rate
    'm³/s': ('m3/s', 1.0),
    'm3/s': ('m3/s', 1.0),
    'L/s': ('m3/s', 0.001),
    'ML/d': ('m3/s', 0.01157407),  # Million liters per day to m³/s
    'ML/day': ('m3/s', 0.01157407),
    'Nm³/h': ('Nm3/h', 1.0),  # Normal cubic meters per hour
    'Nm3/h': ('Nm3/h', 1.0),

    # Energy rate (annual)
    'GWh/yr': ('MWh/yr', 1000.0),
    'kWh/yr': ('MWh/yr', 0.001),
    'TWh/yr': ('MWh/yr', 1000000.0),

    # Chemistry
    '%S': ('%', 1.0),  # Sulfur percentage
    'pH': ('pH', 1.0),
    'ppb': ('mg/L', 0.001),  # Parts per billion (approximate for water)
    'µg/L': ('mg/L', 0.001),  # Micrograms per liter
    'ug/L': ('mg/L', 0.001),

    # Temperature
    '°C': ('degC', 1.0),
    'degC': ('degC', 1.0),
    'C': ('degC', 1.0),

    # Pressure
    'kPa': ('kPa', 1.0),
    'MPa': ('kPa', 1000.0),
    'Pa': ('kPa', 0.001),
    'bar': ('kPa', 100.0),

    # Time
    'hours': ('hours', 1.0),
    'h': ('hours', 1.0),
    'days': ('days', 1.0),
    'd': ('days', 1.0),
    'years': ('years', 1.0),
    'yr': ('years', 1.0),
    'y': ('years', 1.0),

    # Dimensionless
    '%': ('%', 1.0),
    'percent': ('%', 1.0),
}


def normalize_unit(value: float, unit: str) -> tuple[float, str]:
    """
    Normalize a value and unit to canonical base units

    Args:
        value: Numeric value
        unit: Unit string

    Returns:
        Tuple of (normalized_value, canonical_unit)
    """
    unit_clean = unit.strip()

    if unit_clean in UNIT_CONVERSIONS:
        canonical_unit, conversion_factor = UNIT_CONVERSIONS[unit_clean]
        return value * conversion_factor, canonical_unit

    # If unit not found, return as-is
    return value, unit_clean


# ============================================================================
# Canonicalization
# ============================================================================

def slugify(text: str) -> str:
    """
    Convert text to a stable signature slug

    Example: "Coal production (annual)" -> "coal_production_annual"
    """
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    # Convert to lowercase
    text = text.lower()

    # Remove special characters, keep alphanumeric and spaces
    text = re.sub(r'[^\w\s-]', '', text)

    # Replace spaces and hyphens with underscores
    text = re.sub(r'[-\s]+', '_', text)

    # Remove leading/trailing underscores
    text = text.strip('_')

    return text


# ============================================================================
# Text Chunking
# ============================================================================

def chunk_markdown(text: str, max_chars: int = 4000) -> List[str]:
    """
    Split markdown text into manageable chunks

    Args:
        text: Full markdown text
        max_chars: Maximum characters per chunk

    Returns:
        List of text chunks
    """
    # Split by double newlines (paragraphs)
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_len = len(para)

        if current_length + para_len > max_chars and current_chunk:
            # Save current chunk and start new one
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_length = para_len
        else:
            current_chunk.append(para)
            current_length += para_len + 2  # +2 for \n\n

    # Add remaining chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


# ============================================================================
# Fact Extraction
# ============================================================================

class FactExtractor:
    """Extracts facts from ESIA documents using DSPy with structured text output"""

    def __init__(self):
        self.extractor = dspy.Predict(FactExtraction)

    def _parse_structured_output(self, text_output: str) -> List[Dict[str, str]]:
        """
        Parse structured text format into fact dictionaries.

        Expected format:
        FACT: [name]
        TYPE: [type]
        VALUE: [value]
        VALUE_NUM: [number]
        UNIT: [unit]
        EVIDENCE: [quote]
        ---

        Returns:
            List of fact dictionaries
        """
        facts_list = []
        # Split by --- to separate fact blocks
        blocks = text_output.split('---')

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            fact_dict = {}
            lines = block.split('\n')

            for line in lines:
                line = line.strip()
                if ':' not in line:
                    continue

                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()

                if key == 'fact':
                    fact_dict['name'] = value
                elif key == 'type':
                    fact_dict['type'] = value.lower()
                elif key == 'value':
                    fact_dict['value'] = value
                elif key == 'value_num':
                    try:
                        fact_dict['value_num'] = float(value) if value else 0
                    except ValueError:
                        fact_dict['value_num'] = 0
                elif key == 'unit':
                    fact_dict['unit'] = value
                elif key == 'evidence':
                    fact_dict['evidence'] = value

            # Only add if we have minimum required fields
            if 'name' in fact_dict and 'type' in fact_dict:
                # Set defaults for optional fields
                fact_dict.setdefault('value', '')
                fact_dict.setdefault('value_num', 0)
                fact_dict.setdefault('unit', '')
                fact_dict.setdefault('evidence', '')
                fact_dict.setdefault('aliases', [])
                facts_list.append(fact_dict)

        return facts_list

    def extract_from_chunk(self, text: str, page: int, chunk_id: int) -> List[Fact]:
        """
        Extract facts from a single text chunk using structured text output

        Args:
            text: Text chunk
            page: Page number
            chunk_id: Chunk identifier

        Returns:
            List of extracted Fact objects
        """
        try:
            # Call DSPy to extract facts - returns structured text
            result = self.extractor(text=text)
            text_output = result.output

            # Check if empty or None
            if not text_output or text_output.strip() == "":
                return []

            # Parse structured text output
            facts_list = self._parse_structured_output(text_output)

            if not facts_list:
                return []

            # Convert to Fact objects
            facts = []
            for fact_dict in facts_list:
                try:
                    # Create Fact object
                    fact = Fact(
                        name=fact_dict.get('name', ''),
                        type=fact_dict.get('type', 'quantity'),
                        value=fact_dict.get('value', ''),
                        value_num=fact_dict.get('value_num', 0),
                        unit=fact_dict.get('unit', ''),
                        aliases=fact_dict.get('aliases', []),
                        evidence=fact_dict.get('evidence', ''),
                        page=page,
                        chunk_id=chunk_id
                    )

                    # Canonicalize
                    fact.signature = slugify(fact.name)

                    # Normalize units
                    fact.normalized_value, fact.normalized_unit = normalize_unit(
                        fact.value_num, fact.unit
                    )

                    facts.append(fact)
                except Exception as e:
                    print(f"Warning: Could not parse fact {fact_dict} in chunk {chunk_id}: {e}")
                    continue

            return facts

        except Exception as e:
            print(f"Error extracting facts from chunk {chunk_id}: {e}")
            import traceback
            traceback.print_exc()
            return []


# ============================================================================
# Fact Categorization
# ============================================================================

class FactCategorizer(dspy.Module):
    """Uses LLM to categorize extracted facts into logical project sections.

    Implements few-shot learning with diverse examples to guide categorization
    across different ESIA fact types and project scenarios.

    Uses dspy.Predict for straightforward mapping task (not ChainOfThought).
    """

    def __init__(self):
        super().__init__()
        self.categorizer = dspy.Predict(FactCategorizationSignature)
        self._cache = {}  # Cache for previously categorized facts
        self._cache_hits = 0  # Track cache hit rate
        self._cache_misses = 0  # Track cache misses
        self._add_examples()

    def _add_examples(self):
        """Add diverse few-shot examples for better categorization.

        Examples span different project types and demonstrate confidence scoring.
        """
        examples = [
            # Example 1: Solar - Capacity (high confidence)
            dspy.Example(
                fact_name="Installed solar capacity",
                fact_value="500",
                fact_unit="MW",
                category="Project Description",
                subcategory="Capacity/Scale",
                confidence="high",
                rationale="Solar capacity is a core project descriptor."
            ),

            # Example 2: Mining - Direct employment (clear category)
            dspy.Example(
                fact_name="Direct permanent employment",
                fact_value="450",
                fact_unit="people",
                category="Social Impacts",
                subcategory="Employment",
                confidence="high",
                rationale="Employment figures are social impact indicators."
            ),

            # Example 3: Emissions (environmental impact)
            dspy.Example(
                fact_name="Annual CO2 emissions",
                fact_value="250000",
                fact_unit="tonnes/yr",
                category="Environmental Impacts",
                subcategory="Emissions",
                confidence="high",
                rationale="CO2 emissions directly measure environmental impact."
            ),

            # Example 4: Construction timeline (project description)
            dspy.Example(
                fact_name="Construction duration",
                fact_value="36",
                fact_unit="months",
                category="Project Description",
                subcategory="Timeline",
                confidence="high",
                rationale="Timeline is part of project description."
            ),

            # Example 5: Categorical fact (technology type)
            dspy.Example(
                fact_name="Technology type",
                fact_value="open-pit mining",
                fact_unit="",
                category="Project Description",
                subcategory="Technology",
                confidence="high",
                rationale="Mining method is core project technology descriptor."
            ),

            # Example 6: Ambiguous fact (medium confidence)
            dspy.Example(
                fact_name="Land affected",
                fact_value="1200",
                fact_unit="ha",
                category="Environmental Impacts",
                subcategory="Land",
                confidence="medium",
                rationale="Could be environmental or social; treating as environmental footprint."
            ),

            # Example 7: Cost/Economic (Investment category)
            dspy.Example(
                fact_name="Project capital cost",
                fact_value="1500",
                fact_unit="million USD",
                category="Economic Impacts",
                subcategory="Investment",
                confidence="high",
                rationale="Capital expenditure is primary economic indicator."
            ),

            # Example 8: Low confidence example (genuinely ambiguous)
            dspy.Example(
                fact_name="Community interaction meetings held",
                fact_value="25",
                fact_unit="events",
                category="Governance & Management",
                subcategory="Engagement",
                confidence="low",
                rationale="Could be social impacts or governance; unclear without more context."
            ),
        ]

        self.categorizer.demos = examples

    def forward(self, fact_name: str, fact_value: str, fact_unit: str = "") -> Dict[str, str]:
        """Categorize a single fact with caching support.

        Cache key uses fact name and unit (ignores value to allow value variations).
        This avoids redundant LLM calls for the same fact type across multiple occurrences.

        Args:
            fact_name: Name of the fact (e.g., "Annual CO2 emissions")
            fact_value: Value of the fact (e.g., "250000")
            fact_unit: Unit if applicable (e.g., "tonnes/yr"), empty string if categorical

        Returns:
            Dictionary with keys: category, subcategory, confidence, rationale
        """
        # Create cache key from fact name and unit (ignores value)
        cache_key = (fact_name.lower().strip(), fact_unit.lower().strip())

        # Check cache
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]

        # Cache miss - call LLM
        self._cache_misses += 1
        result = self.categorizer(
            fact_name=fact_name,
            fact_value=fact_value,
            fact_unit=fact_unit
        )

        categorization = {
            "category": result.category,
            "subcategory": result.subcategory,
            "confidence": result.confidence,
            "rationale": result.rationale
        }

        # Store in cache
        self._cache[cache_key] = categorization

        return categorization

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache hit/miss statistics.

        Returns:
            Dictionary with hits, misses, and hit_rate
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0

        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate": hit_rate,
            "cache_size": len(self._cache)
        }


# ============================================================================
# Clustering and Conflict Detection
# ============================================================================

def cluster_facts(facts: List[Fact]) -> Dict[str, List[Fact]]:
    """
    Group facts by signature

    Args:
        facts: List of all extracted facts

    Returns:
        Dictionary mapping signature to list of facts
    """
    clusters = defaultdict(list)
    for fact in facts:
        clusters[fact.signature].append(fact)
    return dict(clusters)


def detect_conflicts(cluster: List[Fact], tolerance: float = 0.02) -> tuple[bool, str]:
    """
    Detect conflicts within a cluster of facts

    Args:
        cluster: List of facts with same signature
        tolerance: Relative difference threshold (default 2%)

    Returns:
        Tuple of (has_conflict, conflict_description)
    """
    if len(cluster) <= 1:
        return False, ""

    # Get normalized values
    values = [f.normalized_value for f in cluster if f.normalized_value > 0]

    if len(values) <= 1:
        return False, ""

    min_val = min(values)
    max_val = max(values)

    # Check for significant difference
    if min_val > 0:
        rel_diff = (max_val - min_val) / min_val
        if rel_diff > tolerance:
            # Check for order-of-magnitude errors
            ratio = max_val / min_val
            if 9 < ratio < 11 or 0.09 < ratio < 0.11:
                return True, f"Potential ×10 error: {min_val} vs {max_val}"
            else:
                return True, f"Conflicting values: {min_val} to {max_val} ({rel_diff*100:.1f}% diff)"

    return False, ""


# ============================================================================
# Factsheet Generation
# ============================================================================

class FactsheetGenerator:
    """Aggregates categorized facts into a project factsheet.

    Organizes facts by category/subcategory and generates output suitable for
    inclusion in ESIA documents.
    """

    # Category order for consistent output
    CATEGORY_ORDER = [
        "Project Overview",
        "Project Description",
        "Environmental Impacts",
        "Social Impacts",
        "Economic Impacts",
        "Health & Safety",
        "Governance & Management",
        "Risks & Issues"
    ]

    def __init__(self, categorized_facts: List[Dict[str, Any]]):
        """Initialize with list of facts that include categorization data.

        Args:
            categorized_facts: List of fact dicts with keys:
                - signature, name, value, unit, occurrences, has_conflict, confidence, rationale
        """
        self.categorized_facts = categorized_facts
        self.organized_facts = self._organize_by_category()

    def _organize_by_category(self) -> Dict[str, Dict[str, List[Dict]]]:
        """Group facts by category and subcategory.

        Returns:
            Nested dict: {category: {subcategory: [facts]}}
        """
        organized = {}
        for fact in self.categorized_facts:
            cat = fact.get("category", "Risks & Issues")
            subcat = fact.get("subcategory", "Uncertainties")

            if cat not in organized:
                organized[cat] = {}
            if subcat not in organized[cat]:
                organized[cat][subcat] = []

            organized[cat][subcat].append(fact)

        return organized

    def generate_factsheet_df(self) -> pd.DataFrame:
        """Generate factsheet DataFrame for CSV output.

        Returns:
            DataFrame with columns:
            - category, subcategory, fact_name, value, unit, occurrences,
              has_conflict, confidence, rationale, signature

            Ordered by category and subcategory.
        """
        rows = []

        for category in self.CATEGORY_ORDER:
            if category not in self.organized_facts:
                continue

            subcategories = self.organized_facts[category]

            for subcategory in sorted(subcategories.keys()):
                facts = subcategories[subcategory]

                for fact in facts:
                    rows.append({
                        "category": category,
                        "subcategory": subcategory,
                        "fact_name": fact.get("name", ""),
                        "value": fact.get("value", ""),
                        "unit": fact.get("unit", ""),
                        "occurrences": fact.get("occurrences", 1),
                        "has_conflict": fact.get("has_conflict", False),
                        "confidence": fact.get("confidence", "medium"),
                        "rationale": fact.get("rationale", ""),
                        "signature": fact.get("signature", "")
                    })

        return pd.DataFrame(rows)

    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics for the factsheet.

        Returns:
            Dict with counts by category and total facts.
        """
        summary = {
            "total_facts": len(self.categorized_facts),
            "by_category": {},
            "confidence_breakdown": {
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }

        for category in self.organized_facts:
            count = sum(len(facts) for facts in self.organized_facts[category].values())
            summary["by_category"][category] = count

        for fact in self.categorized_facts:
            conf = fact.get("confidence", "medium")
            if conf in summary["confidence_breakdown"]:
                summary["confidence_breakdown"][conf] += 1

        return summary


# ============================================================================
# Output Generation
# ============================================================================

def generate_facts_table(facts: List[Fact]) -> pd.DataFrame:
    """Generate the detailed facts table (all occurrences)"""
    data = []
    for fact in facts:
        data.append({
            'signature': fact.signature,
            'name': fact.name,
            'type': fact.type,
            'value_raw': fact.value,
            'value_num': fact.value_num,
            'unit_raw': fact.unit,
            'value_normalized': fact.normalized_value,
            'unit_normalized': fact.normalized_unit,
            'aliases': '; '.join(fact.aliases),
            'evidence': fact.evidence,
            'page': fact.page,
            'chunk_id': fact.chunk_id
        })
    return pd.DataFrame(data)


def generate_consolidated_table(clusters: Dict[str, List[Fact]]) -> pd.DataFrame:
    """Generate consolidated facts with conflict detection"""
    data = []
    for signature, cluster in clusters.items():
        has_conflict, conflict_desc = detect_conflicts(cluster)

        normalized_values = [f.normalized_value for f in cluster if f.normalized_value > 0]

        data.append({
            'signature': signature,
            'name': cluster[0].name,
            'type': cluster[0].type,
            'occurrences': len(cluster),
            'min_value': min(normalized_values) if normalized_values else 0,
            'max_value': max(normalized_values) if normalized_values else 0,
            'unit_canonical': cluster[0].normalized_unit,
            'has_conflict': has_conflict,
            'conflict_description': conflict_desc,
            'aliases': '; '.join(set([a for f in cluster for a in f.aliases]))
        })

    return pd.DataFrame(data)


def generate_replacement_plan(clusters: Dict[str, List[Fact]]) -> pd.DataFrame:
    """Generate replacement plan for document editing"""
    data = []
    for signature, cluster in clusters.items():
        # Create regex patterns
        name_escaped = re.escape(cluster[0].name.lower())

        patterns = [
            f"({name_escaped})\\s*(?:of|:|=)?\\s*\\d[\\d\\.,]*\\s*(?:[a-zµ/]+)?",
            f"({name_escaped})\\s*\\(\\s*\\d[\\d\\.,]*\\s*(?:[a-zµ/]+)?\\s*\\)"
        ]

        data.append({
            'signature': signature,
            'name': cluster[0].name,
            'first_occurrence_page': min(f.page for f in cluster),
            'first_occurrence_evidence': cluster[0].evidence,
            'regex_patterns': ' | '.join(patterns),
            'replacement_rule': f"Keep '{cluster[0].name}' only; remove numeric values; optionally append <{signature}>",
            'occurrences': len(cluster)
        })

    return pd.DataFrame(data)


# ============================================================================
# Checkpoint Management
# ============================================================================

def save_checkpoint(output_dir: str, all_facts: List[Fact], processed_chunks: int):
    """Save progress checkpoint"""
    checkpoint_path = Path(output_dir) / ".checkpoint.pkl"
    checkpoint_data = {
        'facts': all_facts,
        'processed_chunks': processed_chunks,
        'timestamp': datetime.now().isoformat()
    }
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(checkpoint_data, f)


def load_checkpoint(output_dir: str) -> Optional[Dict]:
    """Load progress checkpoint if exists"""
    checkpoint_path = Path(output_dir) / ".checkpoint.pkl"
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"  Warning: Could not load checkpoint: {e}")
    return None


def clear_checkpoint(output_dir: str):
    """Remove checkpoint file"""
    checkpoint_path = Path(output_dir) / ".checkpoint.pkl"
    if checkpoint_path.exists():
        checkpoint_path.unlink()


# ============================================================================
# Main Pipeline
# ============================================================================

def process_esia_document(markdown_path: str, output_dir: str = ".", resume: bool = True):
    """
    Complete pipeline for ESIA fact extraction

    Args:
        markdown_path: Path to input markdown file
        output_dir: Directory for output CSV files
        resume: If True, resume from checkpoint if available
    """
    print("=" * 80)
    print("ESIA Fact Extraction Pipeline")
    print("=" * 80)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Check for checkpoint
    checkpoint = None
    start_chunk = 0
    all_facts = []

    if resume:
        checkpoint = load_checkpoint(output_dir)
        if checkpoint:
            all_facts = checkpoint['facts']
            start_chunk = checkpoint['processed_chunks']
            print(f"\n[RESUME] Found checkpoint with {len(all_facts)} facts from {start_chunk} chunks")
            print(f"         Last saved: {checkpoint['timestamp']}")
            response = input("         Resume from checkpoint? (y/n): ").lower()
            if response != 'y':
                checkpoint = None
                all_facts = []
                start_chunk = 0
                print("         Starting fresh extraction...")

    # Configure LLM
    provider, model = peek_llm_configuration()
    provider_label = LLM_PROVIDER_DISPLAY_NAMES.get(provider, provider.title())
    description = f"{model} via {provider_label}" if model else provider_label
    print(f"\n[1/7] Configuring {description} for better error tracking...")
    configure_llm()

    # Load markdown
    print(f"\n[2/7] Loading markdown from {markdown_path}...")
    with open(markdown_path, 'r', encoding='utf-8') as f:
        text = f.read()
    print(f"  Loaded {len(text)} characters")

    # Chunk text
    print("\n[3/7] Chunking text...")
    chunks = chunk_markdown(text, max_chars=4000)
    print(f"  Created {len(chunks)} chunks")

    if start_chunk > 0:
        print(f"  Resuming from chunk {start_chunk + 1}/{len(chunks)}")

    # Extract facts
    print("\n[4/7] Extracting facts from chunks...")
    extractor = FactExtractor()

    # Determine which chunks to process
    chunks_to_process = chunks[start_chunk:]

    # Use tqdm if available, otherwise simple loop
    if TQDM_AVAILABLE:
        chunk_iterator = tqdm(enumerate(chunks_to_process, start=start_chunk),
                             total=len(chunks_to_process),
                             desc="Processing chunks",
                             unit="chunk")
    else:
        chunk_iterator = enumerate(chunks_to_process, start=start_chunk)

    try:
        for i, chunk in chunk_iterator:
            if not TQDM_AVAILABLE:
                print(f"  Processing chunk {i+1}/{len(chunks)}...", end='\r')

            facts = extractor.extract_from_chunk(chunk, page=i+1, chunk_id=i)
            all_facts.extend(facts)

            # Save checkpoint every 5 chunks
            if (i + 1) % 5 == 0:
                save_checkpoint(output_dir, all_facts, i + 1)

        # Clear the progress line
        if not TQDM_AVAILABLE:
            print(" " * 80, end='\r')

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Saving checkpoint...")
        save_checkpoint(output_dir, all_facts, i + 1)
        print(f"  Checkpoint saved. Resume by running the same command.")
        print(f"  Processed {i + 1}/{len(chunks)} chunks so far.")
        return
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        print("  Saving checkpoint...")
        save_checkpoint(output_dir, all_facts, i + 1 if 'i' in locals() else start_chunk)
        raise

    print(f"\n  Extracted {len(all_facts)} total facts")

    # Cluster facts
    print("\n[5/9] Clustering facts by signature...")
    clusters = cluster_facts(all_facts)
    print(f"  Found {len(clusters)} unique fact signatures")

    # Categorize facts
    print("\n[6/9] Categorizing facts by project section...")
    try:
        categorizer = FactCategorizer()
        categorized_facts = []
        failed_facts = []

        # Use tqdm for progress tracking
        for signature, facts in tqdm(clusters.items(), desc="  Categorizing", unit=" facts"):
            # Get representative fact for categorization
            example_fact = facts[0]

            try:
                # Categorize using LLM (uses cache for similar facts)
                categorization = categorizer(
                    fact_name=example_fact.name,
                    fact_value=example_fact.value,
                    fact_unit=example_fact.unit
                )

                # Create categorized fact entry
                categorized_fact = {
                    "signature": signature,
                    "name": example_fact.name,
                    "value": example_fact.value,
                    "unit": example_fact.unit,
                    "normalized_value": example_fact.normalized_value,
                    "normalized_unit": example_fact.normalized_unit,
                    "occurrences": len(facts),
                    "has_conflict": any(
                        len(set(f.normalized_value for f in cluster if f.type == 'quantity')) > 1
                        for cluster in [facts]
                    ),
                    "category": categorization["category"],
                    "subcategory": categorization["subcategory"],
                    "confidence": categorization["confidence"],
                    "rationale": categorization["rationale"]
                }

                categorized_facts.append(categorized_fact)

            except Exception as fact_error:
                # Log failed fact but continue with others
                failed_facts.append({
                    "signature": signature,
                    "name": example_fact.name,
                    "error": str(fact_error)
                })

        # Print summary statistics
        print(f"  Categorized {len(categorized_facts)} unique facts")
        if failed_facts:
            print(f"  Failed to categorize {len(failed_facts)} facts (see details below)")

        # Print cache statistics
        cache_stats = categorizer.get_cache_stats()
        if cache_stats['total'] > 0:
            print(f"  Cache: {cache_stats['hits']}/{cache_stats['total']} hits ({cache_stats['hit_rate']*100:.1f}%)")

        # Print confidence breakdown
        print(f"  Confidence: "
              f"{sum(1 for f in categorized_facts if f['confidence'] == 'high')} high, "
              f"{sum(1 for f in categorized_facts if f['confidence'] == 'medium')} medium, "
              f"{sum(1 for f in categorized_facts if f['confidence'] == 'low')} low")

        # Log failed facts details if any
        if failed_facts:
            print("  Failed facts:")
            for failed in failed_facts[:5]:  # Show first 5 failures
                print(f"    - {failed['name']}: {failed['error'][:60]}...")
            if len(failed_facts) > 5:
                print(f"    ... and {len(failed_facts) - 5} more")

    except Exception as e:
        print(f"  Warning: Categorization failed: {e}")
        print("  Proceeding without categorization...")
        categorized_facts = []

    # Generate outputs
    print("\n[7/9] Generating output tables...")

    facts_df = generate_facts_table(all_facts)
    consolidated_df = generate_consolidated_table(clusters)
    replacement_df = generate_replacement_plan(clusters)

    # Generate factsheet if categorization succeeded
    factsheet_df = None
    if categorized_facts:
        print("\n[8/9] Generating factsheet...")
        try:
            factsheet_gen = FactsheetGenerator(categorized_facts)
            factsheet_df = factsheet_gen.generate_factsheet_df()
            summary = factsheet_gen.generate_summary()

            print(f"  Organized into {len(summary['by_category'])} categories:")
            for cat in FactsheetGenerator.CATEGORY_ORDER:
                if cat in summary['by_category']:
                    count = summary['by_category'][cat]
                    print(f"    - {cat}: {count} facts")
        except Exception as e:
            print(f"  Warning: Factsheet generation failed: {e}")
            factsheet_df = None

    # Save outputs
    print("\n[9/9] Saving CSV files...")
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    facts_csv = output_path / "esia_mentions.csv"
    consolidated_csv = output_path / "esia_consolidated.csv"
    replacement_csv = output_path / "esia_replacement_plan.csv"
    factsheet_csv = output_path / "project_factsheet.csv"

    facts_df.to_csv(facts_csv, index=False)
    consolidated_df.to_csv(consolidated_csv, index=False)
    replacement_df.to_csv(replacement_csv, index=False)

    print(f"  [OK] {facts_csv}")
    print(f"  [OK] {consolidated_csv}")
    print(f"  [OK] {replacement_csv}")

    if factsheet_df is not None:
        factsheet_df.to_csv(factsheet_csv, index=False)
        print(f"  [OK] {factsheet_csv}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total facts extracted: {len(all_facts)}")
    print(f"Unique signatures: {len(clusters)}")

    if len(all_facts) > 0 and 'has_conflict' in consolidated_df.columns:
        conflicts = consolidated_df[consolidated_df['has_conflict'] == True]
        print(f"Conflicts detected: {len(conflicts)}")

        if len(conflicts) > 0:
            print("\nConflicting facts:")
            for _, row in conflicts.iterrows():
                print(f"  - {row['name']}: {row['conflict_description']}")
    else:
        print("Conflicts detected: 0")

    # Clear checkpoint on successful completion
    clear_checkpoint(output_dir)

    print("\n" + "=" * 80)
    print("Pipeline complete!")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python esia_extractor.py <markdown_file> [output_dir]")
        print("\nExample:")
        print("  python esia_extractor.py sample_esia.md ./output")
        sys.exit(1)

    markdown_file = sys.argv[1]

    # Determine output directory
    if len(sys.argv) > 2:
        # Output directory provided as command-line argument
        output_directory = sys.argv[2]
    else:
        # Prompt user for output directory (with fallback for non-interactive environments)
        print("\n" + "=" * 80)
        print("ESIA Fact Extraction - Output Configuration")
        print("=" * 80)

        # Get input file name for default output directory
        input_file_path = Path(markdown_file)
        default_output = f"output_{input_file_path.stem}"

        print(f"\nInput file: {input_file_path.name}")
        print(f"Default output directory: {default_output}/")

        # Try to prompt for custom output directory
        try:
            user_input = input(f"\nEnter output directory (default: {default_output}): ").strip()
            if user_input:
                output_directory = user_input
            else:
                output_directory = default_output
        except EOFError:
            # Non-interactive environment (e.g., Claude Code web)
            # Use default output directory
            output_directory = default_output
            print(f"\n(Non-interactive mode - using default)")

        print(f"\n✓ Output will be saved to: {output_directory}/")
        print("=" * 80 + "\n")

    process_esia_document(markdown_file, output_directory)
