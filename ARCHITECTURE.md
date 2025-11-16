# Architecture Documentation

## System Overview

The ESIA Fact Extraction Pipeline is a modular, AI-powered document processing system designed to extract, categorize, and verify facts from Environmental and Social Impact Assessment documents.

## Design Principles

1. **Modularity** - Each step is independent and can run standalone
2. **Provider Agnostic** - Support multiple LLM providers with unified interface
3. **Resumability** - Long-running processes support checkpointing
4. **Traceability** - Full evidence trail from PDF to extracted facts
5. **Quality Focus** - Automated conflict detection and verification

## Component Architecture

### Layer 1: Pipeline Orchestration

**`run_extract_pipeline.py`**

Responsibilities:
- Coordinate execution of Steps 1-3
- Manage pipeline directory structure
- Handle file naming and timestamps
- Provide unified error handling

Flow:
```
1. Parse arguments (PDF path, output root)
2. Create timestamped pipeline directory
3. Sanitize and copy PDF with clean name
4. Execute Step 1 (PDF → Markdown)
5. Execute Step 2 (Markdown → Facts) with --provider openai
6. Execute Step 3 (Facts → Report) with --provider gemini
7. Print summary with file locations
```

Key Functions:
- `sanitize_name()` - Clean filenames for filesystem safety
- `prepare_clean_pdf()` - Copy PDF with sanitized name
- `run_command()` - Execute subprocess with error handling

### Layer 2: Processing Steps

#### Step 1: PDF to Markdown Conversion

**`step1_pdf_to_markdown.py`**

Technology: Docling library

Process:
```
PDF → DocumentConverter → Markdown Text → File
```

Key Features:
- Progress bar using tqdm
- UTF-8 encoding support
- Unique timestamped filenames
- Provider metadata tracking

Output: `<pdf_name>_<timestamp>.md`

#### Step 2: Fact Extraction

**`step2_extract_facts.py`**

Wrapper script that:
- Manages output directories
- Handles single file or directory input
- Calls `esia_extractor.py` subprocess
- Tracks pipeline metadata
- Verifies output completeness

Modes:
1. **Single File Mode** - Process one markdown file
2. **Directory Mode** - Process all .md files in directory
3. **Pipeline Root Mode** - Locate markdown in pipeline directory

Output Structure:
```
step2_output/
├── esia_mentions.csv           # All fact occurrences
├── esia_consolidated.csv       # Deduplicated facts
├── esia_replacement_plan.csv   # Document editing patterns
├── project_factsheet.csv       # Categorized facts
└── pipeline_metadata.json      # Processing metadata
```

Metadata Schema:
```json
{
  "source_markdown": "/path/to/document.md",
  "source_pdf_name": "document_name",
  "markdown_timestamp": "20250116_120000",
  "generated_at": "20250116_123000"
}
```

#### Step 3: Fact Analysis

**`step3_analyze_facts.py`**

DSPy-based analysis module that:
- Loads extracted facts from Step 2
- Deduplicates fact mentions
- Runs consolidation + verification through LLM
- Generates human-friendly markdown report

DSPy Modules:
- `ESIAFactChecker` - Main module
  - `CategorizeAndConsolidateFacts` - Signature for consolidation
  - `GenerateVerificationChecklist` - Signature for verification

Process:
```
CSV Facts → Deduplication → Structured Prompt → DSPy Module → Markdown Report
```

Output: `<pdf_name>_<timestamp>_verification_report.md`

### Layer 3: Core Extraction Engine

**`esia_extractor.py`**

The heart of the system - implements complete fact extraction workflow using DSPy.

#### 3.1 LLM Configuration

Function: `configure_llm()`

Supports:
- **Ollama** - Local models via HTTP API
- **OpenAI** - GPT models via API
- **Anthropic** - Claude models via API
- **Gemini** - Google models via API

Configuration sources (priority order):
1. Environment variables (highest)
2. `.env` file
3. Defaults

Provider-specific settings:
```python
{
    "provider": "openai|ollama|anthropic|gemini",
    "model": "gpt-4o-mini|mistral:latest|claude-haiku|gemini-pro",
    "temperature": 0.1,
    "max_tokens": 2048
}
```

#### 3.2 DSPy Signatures

**FactExtraction**
- Input: Text chunk from ESIA document
- Output: Structured text with fact blocks
- Format:
```
FACT: [name]
TYPE: [quantity|categorical]
VALUE: [value]
VALUE_NUM: [number]
UNIT: [unit]
EVIDENCE: [quote]
---
```

**FactCategorizationSignature**
- Input: fact_name, fact_value, fact_unit
- Output: category, subcategory, confidence, rationale
- Uses few-shot learning (8 examples)
- Implements intelligent caching

#### 3.3 Data Models

**Fact** (dataclass):
```python
@dataclass
class Fact:
    name: str              # Descriptive name
    type: str              # 'quantity' or 'categorical'
    value: str             # Raw value as text
    value_num: float       # Numeric value
    unit: str              # Original unit
    aliases: List[str]     # Alternative names
    evidence: str          # Source quote
    page: int              # Page number
    chunk_id: int          # Chunk identifier
    signature: str         # Canonicalized identifier
    normalized_value: float    # Value in canonical unit
    normalized_unit: str       # Canonical unit
```

#### 3.4 Text Processing Pipeline

**Chunking** (`chunk_markdown()`):
- Split by paragraphs (double newlines)
- Maximum 4000 characters per chunk
- Preserve paragraph boundaries
- Overlap handling for context

**Canonicalization** (`slugify()`):
- Unicode normalization (NFKD)
- Lowercase conversion
- ASCII transliteration
- Special character removal
- Underscore separation

Example: "Coal production (annual)" → "coal_production_annual"

#### 3.5 Unit Normalization System

**Unit Conversion Table** (`UNIT_CONVERSIONS`):

Categories:
- Mass: kg (base), t→1000, Mt→1000000, g→0.001
- Area: ha (base), km²→100, m²→0.0001, acres→0.404686
- Power: MW (base), kW→0.001, GW→1000
- Energy: MWh (base), kWh→0.001, GWh→1000
- Volume: L (base), m³→1000, mL→0.001
- Distance: km (base), m→0.001, cm→0.00001
- Temperature: degC (base)
- And many more...

Function: `normalize_unit(value, unit) → (normalized_value, canonical_unit)`

Example:
```python
normalize_unit(500, "hectares") → (500.0, "ha")
normalize_unit(2, "km²") → (200.0, "ha")
normalize_unit(1000, "t") → (1000000.0, "kg")
```

#### 3.6 Fact Extraction Process

**FactExtractor** class:

1. `extract_from_chunk(text, page, chunk_id)`:
   - Call DSPy with text chunk
   - Parse structured text output
   - Convert to Fact objects
   - Apply canonicalization
   - Normalize units
   - Return list of Facts

2. `_parse_structured_output(text)`:
   - Split by "---" separators
   - Extract key-value pairs
   - Validate required fields
   - Build fact dictionaries

#### 3.7 Fact Categorization

**FactCategorizer** (DSPy Module):

Features:
- Few-shot learning with 8 diverse examples
- Intelligent caching (cache key: name + unit)
- Confidence scoring (high/medium/low)
- Rationale generation

Cache Strategy:
- Key: `(fact_name.lower(), fact_unit.lower())`
- Ignores value to maximize cache hits
- Typical hit rate: 70-90%

Category Hierarchy:
```
Project Overview
  ├── Basic Info
  └── Timeline
Project Description
  ├── Financing
  ├── Capacity/Scale
  ├── Technology
  ├── Infrastructure
  └── Location
Environmental Impacts
  ├── Water
  ├── Air
  ├── Land
  ├── Biodiversity
  ├── Waste
  └── Emissions
[... and more ...]
```

#### 3.8 Clustering and Conflict Detection

**Clustering** (`cluster_facts()`):
- Group facts by signature
- Signature = slugified name
- Returns: `Dict[signature, List[Fact]]`

**Conflict Detection** (`detect_conflicts()`):
- Compare normalized values within cluster
- Tolerance: 2% relative difference
- Detect order-of-magnitude errors (×10)
- Return: `(has_conflict, description)`

Algorithm:
```python
if max_val - min_val > tolerance * min_val:
    ratio = max_val / min_val
    if 9 < ratio < 11:  # Likely ×10 error
        flag_magnitude_error()
    else:
        flag_value_conflict()
```

#### 3.9 Factsheet Generation

**FactsheetGenerator** class:

Process:
1. Organize facts by category/subcategory
2. Generate DataFrame with ordered columns
3. Calculate summary statistics
4. Export to CSV

Output Schema:
```
category | subcategory | fact_name | value | unit | occurrences | has_conflict | confidence | rationale | signature
```

Summary Statistics:
```json
{
    "total_facts": 150,
    "by_category": {
        "Project Overview": 15,
        "Environmental Impacts": 45,
        ...
    },
    "confidence_breakdown": {
        "high": 120,
        "medium": 25,
        "low": 5
    }
}
```

#### 3.10 Checkpoint Management

Functions:
- `save_checkpoint(output_dir, facts, processed_chunks)` - Pickle progress
- `load_checkpoint(output_dir)` - Resume from .checkpoint.pkl
- `clear_checkpoint(output_dir)` - Remove on completion

Checkpoint Data:
```python
{
    'facts': List[Fact],
    'processed_chunks': int,
    'timestamp': ISO datetime
}
```

Frequency: Every 5 chunks

#### 3.11 Main Pipeline

**`process_esia_document(markdown_path, output_dir, resume=True)`**

Phases:
```
[1/7] Configure LLM
[2/7] Load markdown
[3/7] Chunk text
[4/7] Extract facts (with progress bar, checkpoints)
[5/9] Cluster facts by signature
[6/9] Categorize facts (LLM with cache)
[7/9] Generate output tables
[8/9] Generate factsheet
[9/9] Save CSV files
```

Output Files:
1. `esia_mentions.csv` - All occurrences
2. `esia_consolidated.csv` - Deduplicated + conflicts
3. `esia_replacement_plan.csv` - Document editing patterns
4. `project_factsheet.csv` - Categorized facts

### Layer 4: Configuration Management

**`llm_config.py`**

Centralized configuration utilities for LLM providers.

Constants:
```python
SUPPORTED_PROVIDERS = ("ollama", "openai", "anthropic", "gemini")

STEP_ENV_VARS = {
    "step1": "LLM_PROVIDER_STEP1",
    "step2": "LLM_PROVIDER_STEP2",
    "step3": "LLM_PROVIDER_STEP3"
}

DEFAULT_PROVIDERS = {
    "step1": "ollama",
    "step2": "openai",
    "step3": "openai"
}

DEFAULT_PROVIDER_MODELS = {
    "ollama": "mistral:latest",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "gemini": "gemini-2.5-flash"
}
```

Functions:
- `resolve_provider_for_step(step_name, override)` - Determine provider
- `ensure_provider_credentials(provider)` - Validate API keys
- `get_model_for_provider(provider)` - Get configured model name

Resolution Order:
1. Command-line override
2. Step-specific env var (e.g., LLM_PROVIDER_STEP2)
3. General LLM_PROVIDER env var
4. Default for step

## Data Flow

### End-to-End Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        INPUT: PDF Document                        │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Step 1: Docling      │
                    │   PDF → Markdown       │
                    └───────────┬────────────┘
                                │
                        Markdown Text
                                │
                    ┌───────────▼────────────┐
                    │   Step 2: DSPy + LLM   │
                    │   Markdown → Facts     │
                    └───────────┬────────────┘
                                │
                    ┌───────────┴────────────┐
                    │                        │
            ┌───────▼────────┐     ┌────────▼────────┐
            │  Fact Objects  │     │  Categorization │
            │  (normalized)  │     │   (LLM-based)   │
            └───────┬────────┘     └────────┬────────┘
                    │                       │
                    └──────────┬────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   CSV Outputs        │
                    │   - Mentions         │
                    │   - Consolidated     │
                    │   - Factsheet        │
                    │   - Replacement Plan │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Step 3: DSPy + LLM │
                    │   Facts → Report     │
                    └──────────┬───────────┘
                               │
                ┌──────────────▼──────────────┐
                │  OUTPUT: Verification       │
                │  Report (Markdown)          │
                │  - Inconsistencies          │
                │  - Checklist                │
                │  - Consolidated Factsheet   │
                └─────────────────────────────┘
```

### Fact Extraction Detail

```
Markdown Text
     │
     ▼
┌─────────────────┐
│ Chunk (4000ch)  │
└────────┬────────┘
         │ (for each chunk)
         ▼
┌─────────────────┐
│ DSPy Predict    │ FactExtraction signature
│ (LLM call)      │ → Structured text output
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parse Output    │ Extract FACT blocks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Create Facts    │ Fact objects with metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Canonicalize    │ slugify() → signature
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Normalize Units │ Convert to canonical
└────────┬────────┘
         │
         ▼
    List[Fact]
```

## Performance Characteristics

### Throughput

Typical processing times (100-page ESIA):
- **Step 1 (PDF→MD)**: 2-5 minutes
- **Step 2 (Extraction)**:
  - Ollama (local): 30-60 minutes
  - OpenAI GPT-4: 15-30 minutes
  - Gemini Flash: 10-20 minutes
- **Step 3 (Analysis)**: 2-5 minutes

### Bottlenecks

1. **LLM API Calls** - Rate limits and latency
2. **Token Processing** - Large chunks → more tokens
3. **Network I/O** - Cloud provider latency

### Optimization Strategies

1. **Caching** - Categorization cache reduces calls by 70-90%
2. **Checkpointing** - Resume interrupted processes
3. **Batching** - Process chunks sequentially to avoid rate limits
4. **Local LLMs** - Use Ollama for development (no API costs)
5. **Parallel Documents** - Process multiple PDFs in parallel

## Error Handling

### Graceful Degradation

1. **Fact Extraction Errors**:
   - Continue processing remaining chunks
   - Log warning with chunk ID
   - Include partial results in output

2. **Categorization Errors**:
   - Track failed facts separately
   - Continue with successful categorizations
   - Report failures in summary

3. **Network Errors**:
   - Retry with exponential backoff
   - Save checkpoint before failing
   - Provide resume instructions

### Validation

1. **Output Verification**:
   - Check file existence
   - Validate file size (>10 bytes)
   - List directory contents on failure

2. **Metadata Tracking**:
   - Store source information
   - Track timestamps
   - Enable full traceability

## Extensibility

### Adding New Providers

1. Add to `llm_config.py`:
```python
SUPPORTED_PROVIDERS = (..., "new_provider")
DEFAULT_PROVIDER_MODELS["new_provider"] = "model-name"
CREDENTIAL_REQUIREMENTS["new_provider"] = "NEW_PROVIDER_API_KEY"
```

2. Add to `esia_extractor.configure_llm()`:
```python
elif provider == "new_provider":
    api_key = os.getenv("NEW_PROVIDER_API_KEY")
    model = get_model_for_provider(provider)
    lm = dspy.LM(model=f"new_provider/{model}", ...)
```

### Adding New Categories

Modify `FactCategorizationSignature` in `esia_extractor.py`:
```python
category: Literal[
    "Project Overview",
    ...,
    "New Category"  # Add here
]

subcategory: Literal[
    ...,
    "New Subcategory"  # Add here
]
```

Update `FactsheetGenerator.CATEGORY_ORDER`.

### Custom Output Formats

Extend output generation functions:
```python
def generate_custom_output(facts: List[Fact]) -> CustomFormat:
    # Your custom logic
    pass
```

## Security Considerations

1. **API Key Storage**:
   - Never commit `.env` to version control
   - Use environment variables in production
   - Rotate keys regularly

2. **Input Validation**:
   - Sanitize filenames
   - Validate file types
   - Check file sizes

3. **Output Sanitization**:
   - No code execution in outputs
   - Escape special characters in CSV
   - Validate regex patterns

## Testing

### LLM Configuration Testing

**`test_llm_configuration.py`**:
- Tests each provider configuration
- Validates API connectivity
- Verifies response format

Run:
```bash
python test_llm_configuration.py
```

### Manual Testing

1. **Small Document Test**:
```bash
python run_extract_pipeline.py small_test.pdf
```

2. **Provider Comparison**:
```bash
# Test with different providers
python step2_extract_facts.py test.md out_ollama --provider ollama
python step2_extract_facts.py test.md out_openai --provider openai
python step2_extract_facts.py test.md out_gemini --provider gemini
```

3. **Resume Testing**:
```bash
# Start extraction
python esia_extractor.py large.md output/
# Interrupt with Ctrl+C
# Resume
python esia_extractor.py large.md output/
```

## Future Enhancements

### Potential Improvements

1. **Parallel Chunk Processing** - Process multiple chunks concurrently
2. **Streaming Output** - Real-time fact display as extracted
3. **Interactive Verification** - UI for human-in-the-loop fact verification
4. **Multi-language Support** - Extract facts from non-English ESIAs
5. **Graph Database Integration** - Store facts in Neo4j for relationship analysis
6. **Automated Fact Linking** - Connect related facts across documents
7. **Confidence Scoring** - Per-fact extraction confidence
8. **Change Tracking** - Compare facts across document versions
9. **Export Formats** - JSON, XML, RDF for interoperability
10. **API Server** - REST API for programmatic access

### Scalability Roadmap

1. **Distributed Processing** - Celery/Ray for large-scale extraction
2. **Cloud Deployment** - Docker + Kubernetes for production
3. **Database Backend** - PostgreSQL for fact storage and querying
4. **Web Interface** - React frontend for document upload and visualization
5. **Batch Processing** - Process entire document collections
