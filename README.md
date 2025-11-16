# ESIA Fact Extraction Pipeline

An automated system for extracting, analyzing, and verifying facts from Environmental and Social Impact Assessment (ESIA) documents using AI-powered document processing.

## Overview

This pipeline processes ESIA PDFs through three main stages:
1. **PDF to Markdown Conversion** - Convert PDF documents to structured markdown
2. **Fact Extraction** - Extract quantitative and categorical facts using LLMs
3. **Fact Analysis** - Analyze extracted facts for inconsistencies and generate verification reports

## Architecture

```
┌─────────────────┐
│   PDF Document  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Step 1      │  PDF → Markdown (Docling)
│ step1_pdf_to_   │
│   markdown.py   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Step 2      │  Markdown → Facts (DSPy + LLM)
│ step2_extract_  │  - Extract facts
│    facts.py     │  - Categorize by project section
└────────┬────────┘  - Generate factsheet
         │
         ▼
┌─────────────────┐
│     Step 3      │  Facts → Verification Report
│ step3_analyze_  │  - Detect inconsistencies
│    facts.py     │  - Generate checklist
└─────────────────┘
```

## Key Components

### Core Pipeline Files

- **`run_extract_pipeline.py`** - Orchestrates all three steps in sequence
- **`step1_pdf_to_markdown.py`** - PDF conversion using Docling library
- **`step2_extract_facts.py`** - Fact extraction wrapper and output management
- **`step3_analyze_facts.py`** - Fact analysis and verification report generation
- **`esia_extractor.py`** - Core extraction engine using DSPy
- **`llm_config.py`** - Centralized LLM provider configuration

### Supporting Files

- **`test_llm_configuration.py`** - Tests LLM provider configurations
- **`activate_venv.sh`** / **`activate_venv.ps1`** - Virtual environment activation scripts

## Features

### Multi-Provider LLM Support

The system supports multiple LLM providers, configurable per-step:

- **Ollama** (local, free) - Mistral, Qwen, etc.
- **OpenAI** (cloud) - GPT-4, GPT-4o-mini, GPT-3.5-turbo
- **Anthropic** (cloud) - Claude models (Sonnet, Haiku)
- **Google Gemini** (cloud) - Gemini Pro, Gemini Flash

### Intelligent Fact Extraction

**Quantitative Facts:**
- Values with units (area, emissions, costs, etc.)
- Unit normalization (converts to canonical units)
- Conflict detection for inconsistent values

**Categorical Facts:**
- Technology types, project classifications
- Stakeholder categories
- Environmental classifications

### Advanced Categorization

Facts are automatically categorized into:
- Project Overview (Basic Info, Timeline)
- Project Description (Financing, Capacity/Scale, Technology, Infrastructure, Location)
- Environmental Impacts (Water, Air, Land, Biodiversity, Waste, Emissions)
- Social Impacts (Employment, Resettlement, Community, Cultural)
- Economic Impacts (Investment, Revenue, Local Procurement)
- Health & Safety (Occupational, Public Health, Emergency)
- Governance & Management (Institutional, Monitoring, Engagement)
- Risks & Issues (Identified Risks, Uncertainties, Conflicts)

### Output Products

**Step 1 Outputs:**
- Markdown conversion of PDF

**Step 2 Outputs:**
- `esia_mentions.csv` - All fact occurrences with evidence
- `esia_consolidated.csv` - Deduplicated facts with conflict detection
- `esia_replacement_plan.csv` - Regex patterns for document editing
- `project_factsheet.csv` - Categorized facts by project section
- `pipeline_metadata.json` - Processing metadata

**Step 3 Outputs:**
- `<document>_<timestamp>_verification_report.md` - Human-friendly verification checklist

## Installation

### Prerequisites

- Python 3.10+
- Virtual environment support
- (Optional) Ollama for local LLM inference

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd testing-codex
```

2. Create and activate virtual environment:
```bash
# Linux/Mac
python -m venv .venv
source .venv/bin/activate
# or use: source activate_venv.sh

# Windows
python -m venv .venv
.venv\Scripts\activate
# or use: .\activate_venv.ps1
```

3. Install dependencies:
```bash
pip install -r requirements.txt  # If requirements.txt exists
# or manually install:
pip install dspy-ai docling pandas tqdm python-dotenv
```

4. Configure LLM providers (create `.env` file):
```bash
# General provider selection
LLM_PROVIDER=openai  # or ollama, anthropic, gemini

# Provider-specific settings
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Or for local Ollama
OLLAMA_MODEL=mistral:latest
OLLAMA_BASE_URL=http://localhost:11434

# Or for Anthropic
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Or for Gemini
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.5-flash

# Per-step provider override (optional)
LLM_PROVIDER_STEP1=ollama
LLM_PROVIDER_STEP2=openai
LLM_PROVIDER_STEP3=gemini
```

## Usage

### Full Pipeline

Run all three steps automatically:

```bash
python run_extract_pipeline.py <path-to-pdf>
```

Example:
```bash
python run_extract_pipeline.py "Mufindi+Paper+Mills-ESIA+Update_20240524_Final+Report.pdf"
```

This creates a timestamped directory in `pipeline_runs/` with all outputs.

### Individual Steps

#### Step 1: PDF to Markdown

```bash
python step1_pdf_to_markdown.py <input.pdf>
python step1_pdf_to_markdown.py <input.pdf> --output-dir custom_output/
```

#### Step 2: Fact Extraction

```bash
python step2_extract_facts.py <markdown-file> <output-dir>
python step2_extract_facts.py markdown_outputs/document.md ./output --provider openai
python step2_extract_facts.py --pipeline-root ./pipeline_runs/my_project
```

#### Step 3: Verification Analysis

```bash
python step3_analyze_facts.py <step2-output-dir>
python step3_analyze_facts.py ./output --provider gemini
python step3_analyze_facts.py --pipeline-root ./pipeline_runs/my_project
```

### Direct Fact Extraction

For advanced usage, you can call the core extractor directly:

```bash
python esia_extractor.py <markdown-file> [output-dir]
```

## Configuration

### LLM Provider Configuration

Configuration is hierarchical:
1. Command-line `--provider` flag (highest priority)
2. Step-specific environment variable (e.g., `LLM_PROVIDER_STEP2`)
3. General `LLM_PROVIDER` environment variable
4. Default provider (varies by step)

### Provider Credentials

**OpenAI:**
- Requires: `OPENAI_API_KEY`
- Get from: https://platform.openai.com/

**Anthropic:**
- Requires: `ANTHROPIC_API_KEY`
- Get from: https://console.anthropic.com/

**Gemini:**
- Requires: `GEMINI_API_KEY`
- Get from: https://ai.google.dev/

**Ollama:**
- No API key required
- Install from: https://ollama.ai/
- Start service: `ollama serve`

### Unit Normalization

The system automatically normalizes units to canonical forms:
- Mass: kg (from t, tonne, ton, g, mg)
- Area: ha (from km², m², acres)
- Power: MW (from kW, GW, W)
- Energy: MWh (from kWh, GWh)
- And many more...

See `esia_extractor.py:UNIT_CONVERSIONS` for full list.

## Technical Details

### DSPy Integration

The system uses DSPy for structured LLM interactions:
- **Signatures** - Define input/output structure
- **Modules** - Compose signatures into workflows
- **Few-shot learning** - Examples guide categorization

Key signatures:
- `FactExtraction` - Extract facts from text chunks
- `FactCategorizationSignature` - Categorize facts into project sections
- `CategorizeAndConsolidateFacts` - Consolidate fact mentions
- `GenerateVerificationChecklist` - Identify inconsistencies

### Fact Processing Pipeline

1. **Chunking** - Markdown split into 4000-character chunks
2. **Extraction** - LLM extracts facts from each chunk
3. **Canonicalization** - Facts normalized (slugify names, normalize units)
4. **Clustering** - Group facts by signature (normalized name)
5. **Conflict Detection** - Identify value discrepancies (>2% tolerance)
6. **Categorization** - Assign category/subcategory with confidence
7. **Factsheet Generation** - Organize into structured outputs

### Checkpoint Support

Step 2 supports resumable processing:
- Automatically saves progress every 5 chunks
- Resume from checkpoint on interrupt (Ctrl+C)
- Checkpoint stored in `.checkpoint.pkl`

### Caching Strategy

Categorization uses intelligent caching:
- Cache key: `(fact_name, unit)` - ignores value
- Avoids redundant LLM calls for similar facts
- Reports cache hit rate in output

## Output File Formats

### esia_mentions.csv

All extracted fact occurrences with full traceability:
```
signature, name, type, value_raw, value_num, unit_raw, value_normalized, unit_normalized, aliases, evidence, page, chunk_id
```

### esia_consolidated.csv

Deduplicated facts with conflict detection:
```
signature, name, type, occurrences, min_value, max_value, unit_canonical, has_conflict, conflict_description, aliases
```

### project_factsheet.csv

Categorized facts organized by project section:
```
category, subcategory, fact_name, value, unit, occurrences, has_conflict, confidence, rationale, signature
```

### verification_report.md

Human-friendly markdown report with:
1. Actionable verification checklist (prioritized inconsistencies)
2. Comprehensive factsheet (consolidated facts for reference)

## Directory Structure

```
testing-codex/
├── run_extract_pipeline.py        # Main pipeline orchestrator
├── step1_pdf_to_markdown.py       # Step 1: PDF conversion
├── step2_extract_facts.py         # Step 2: Fact extraction wrapper
├── step3_analyze_facts.py         # Step 3: Analysis and verification
├── esia_extractor.py              # Core extraction engine (DSPy)
├── llm_config.py                  # LLM provider configuration
├── test_llm_configuration.py      # LLM configuration tester
├── activate_venv.sh               # Linux/Mac venv activation
├── activate_venv.ps1              # Windows venv activation
├── .env                           # Configuration (not in repo)
├── .gitignore                     # Git ignore rules
├── markdown_outputs/              # Step 1 outputs (gitignored)
├── pipeline_runs/                 # Full pipeline runs (gitignored)
│   └── <document_name>_<timestamp>/
│       ├── <document>.pdf         # Source PDF (sanitized name)
│       ├── <document>_<timestamp>.md  # Converted markdown
│       └── step2_output/          # Step 2 outputs
│           ├── esia_mentions.csv
│           ├── esia_consolidated.csv
│           ├── esia_replacement_plan.csv
│           ├── project_factsheet.csv
│           ├── pipeline_metadata.json
│           └── <document>_<timestamp>_verification_report.md
└── output/                        # Manual outputs (gitignored)
```

## Examples

### Example 1: Process Single PDF with OpenAI

```bash
# Set up environment
export OPENAI_API_KEY="sk-..."
export LLM_PROVIDER="openai"

# Run full pipeline
python run_extract_pipeline.py my_esia_document.pdf

# Outputs created in: pipeline_runs/my_esia_document_<timestamp>/
```

### Example 2: Process with Local Ollama

```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull mistral:latest

# Set environment
export LLM_PROVIDER="ollama"
export OLLAMA_MODEL="mistral:latest"

# Run pipeline
python run_extract_pipeline.py my_esia_document.pdf
```

### Example 3: Mixed Providers (Different per Step)

```bash
# Use Ollama for conversion, OpenAI for extraction, Gemini for analysis
export LLM_PROVIDER_STEP1="ollama"
export LLM_PROVIDER_STEP2="openai"
export LLM_PROVIDER_STEP3="gemini"
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."

python run_extract_pipeline.py my_esia_document.pdf
```

## Troubleshooting

### Common Issues

**Import Error: docling not found**
```bash
pip install docling
```

**Import Error: dspy not found**
```bash
pip install dspy-ai
```

**Ollama connection refused**
```bash
# Start Ollama service
ollama serve

# Check it's running
curl http://localhost:11434
```

**API Key errors**
- Ensure `.env` file exists with correct API keys
- Check that keys are not wrapped in quotes
- Verify keys are valid at provider console

**LLM timeouts or truncation**
- Increase max_tokens in `.env`:
```
OPENAI_MAX_TOKENS=4096
GEMINI_MAX_TOKENS=8192
```

**Checkpoint recovery**
- If extraction is interrupted, re-run the same command
- System will ask if you want to resume from checkpoint
- To force fresh start, delete `.checkpoint.pkl`

## Performance Tips

1. **Use local LLMs (Ollama) for development** - No API costs, fast iteration
2. **Use cloud LLMs for production** - Better accuracy, larger context windows
3. **Chunk size optimization** - Adjust `max_chars` in `chunk_markdown()` for your LLM
4. **Parallel processing** - Process multiple documents separately in parallel
5. **Cache utilization** - Categorization cache reduces LLM calls by ~70-90%

## License

[Specify your license here]

## Contributing

[Specify contribution guidelines here]

## Contact

[Specify contact information here]
