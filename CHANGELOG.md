# Changelog

All notable changes to the ESIA Fact Extraction Pipeline will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation (README.md, ARCHITECTURE.md, CONTRIBUTING.md)
- Project overview and installation instructions
- Detailed architecture documentation
- Contributing guidelines for developers
- Support for multiple LLM providers (Ollama, OpenAI, Anthropic, Gemini)
- Three-step pipeline for ESIA document processing
- Automated fact extraction with DSPy
- Intelligent fact categorization with caching
- Unit normalization system
- Conflict detection for inconsistent values
- Checkpoint support for resumable processing
- Verification report generation

### Features

#### Step 1: PDF to Markdown
- PDF conversion using Docling
- UTF-8 encoding support
- Timestamped output files
- Progress bar visualization

#### Step 2: Fact Extraction
- LLM-based fact extraction
- Quantitative and categorical fact support
- 8 category hierarchy with 29 subcategories
- Unit normalization to canonical forms
- Fact clustering by signature
- Conflict detection (2% tolerance)
- CSV output formats:
  - esia_mentions.csv (all occurrences)
  - esia_consolidated.csv (deduplicated)
  - project_factsheet.csv (categorized)
  - esia_replacement_plan.csv (editing patterns)
- Checkpoint support (save every 5 chunks)
- Cache optimization for categorization (70-90% hit rate)

#### Step 3: Fact Analysis
- DSPy-based analysis module
- Inconsistency detection
- Verification checklist generation
- Markdown report output
- Prioritized action items

#### Configuration
- Per-step provider configuration
- Environment variable support
- .env file support
- Hierarchical configuration resolution
- Default model selection per provider

### Infrastructure
- Pipeline orchestration script
- Directory structure management
- File naming conventions
- Metadata tracking
- Error handling and validation

## [0.1.0] - Initial Development

### Core Components
- PDF to Markdown conversion
- Fact extraction engine
- LLM integration
- Basic categorization
- Output generation

---

## Release Notes Template

### Version X.Y.Z - YYYY-MM-DD

#### Added
- New features

#### Changed
- Changes to existing functionality

#### Deprecated
- Soon-to-be removed features

#### Removed
- Removed features

#### Fixed
- Bug fixes

#### Security
- Security improvements
