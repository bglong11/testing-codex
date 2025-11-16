# Contributing to ESIA Fact Extraction Pipeline

Thank you for your interest in contributing to this project! This document provides guidelines and information for contributors.

## Code of Conduct

Please be respectful and professional in all interactions. We aim to create a welcoming environment for all contributors.

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check existing issues to avoid duplicates
2. Verify you're using the latest version
3. Test with different LLM providers to isolate the issue

Include in your bug report:
- Python version
- Operating system
- LLM provider and model
- Complete error message and stack trace
- Minimal reproducible example
- Expected vs actual behavior

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
1. Check if the feature already exists or is planned
2. Provide clear use cases
3. Describe expected behavior
4. Consider implementation complexity

### Pull Requests

#### Before Submitting

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Test your changes thoroughly
4. Update documentation as needed
5. Follow code style guidelines (see below)

#### Submission Process

1. Push to your fork: `git push origin feature/your-feature-name`
2. Create a pull request with:
   - Clear title and description
   - Reference to related issues
   - Summary of changes
   - Testing performed
   - Screenshots (if UI changes)

#### Review Process

- Maintainers will review your PR
- Address feedback and requested changes
- Keep discussion professional and constructive
- Be patient - reviews may take time

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv, virtualenv, conda)

### Environment Setup

1. Clone your fork:
```bash
git clone https://github.com/YOUR-USERNAME/testing-codex.git
cd testing-codex
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt  # If exists
# or
pip install dspy-ai docling pandas tqdm python-dotenv
```

4. Install development dependencies:
```bash
pip install pytest black flake8 mypy
```

5. Set up pre-commit hooks (optional):
```bash
pip install pre-commit
pre-commit install
```

## Code Style Guidelines

### Python Style

Follow PEP 8 with these specific guidelines:

**Formatting:**
- Line length: 100 characters maximum
- Indentation: 4 spaces (no tabs)
- Encoding: UTF-8
- String quotes: Prefer double quotes for user-facing strings

**Naming Conventions:**
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

**Imports:**
- Standard library first
- Third-party libraries second
- Local imports third
- Alphabetical within each group

Example:
```python
import sys
from pathlib import Path
from typing import List

import dspy
import pandas as pd

from llm_config import configure_llm
```

**Documentation:**
- Docstrings for all public functions/classes
- Type hints for function signatures
- Inline comments for complex logic

Example:
```python
def extract_facts(text: str, chunk_id: int) -> List[Fact]:
    """Extract facts from a text chunk.

    Args:
        text: Text chunk from ESIA document
        chunk_id: Unique identifier for this chunk

    Returns:
        List of extracted Fact objects with evidence
    """
    # Implementation...
```

### Code Formatting

Use `black` for automatic formatting:
```bash
black *.py
```

Use `flake8` for linting:
```bash
flake8 *.py --max-line-length=100
```

Use `mypy` for type checking:
```bash
mypy *.py
```

## Testing Guidelines

### Writing Tests

1. **Test Coverage**: Aim for >80% coverage on new code
2. **Test Structure**: Use pytest framework
3. **Test Naming**: `test_<function_name>_<scenario>`
4. **Test Location**: Create `tests/` directory

Example test:
```python
# tests/test_unit_normalization.py
import pytest
from esia_extractor import normalize_unit

def test_normalize_unit_mass_conversion():
    """Test mass unit conversion from tonnes to kg."""
    value, unit = normalize_unit(2.5, "tonnes")
    assert value == 2500.0
    assert unit == "kg"

def test_normalize_unit_unknown_unit():
    """Test that unknown units pass through unchanged."""
    value, unit = normalize_unit(100, "custom_unit")
    assert value == 100.0
    assert unit == "custom_unit"
```

### Running Tests

Run all tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

Run specific test:
```bash
pytest tests/test_unit_normalization.py::test_normalize_unit_mass_conversion
```

### Test Categories

1. **Unit Tests**: Test individual functions
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test full pipeline with sample data
4. **Provider Tests**: Test each LLM provider configuration

## Documentation Guidelines

### Code Documentation

- All public functions need docstrings
- Use Google or NumPy docstring format
- Include examples for complex functions

Example:
```python
def chunk_markdown(text: str, max_chars: int = 4000) -> List[str]:
    """Split markdown text into manageable chunks.

    Chunks are created by splitting on paragraph boundaries (double
    newlines) while respecting the maximum character limit.

    Args:
        text: Full markdown text to chunk
        max_chars: Maximum characters per chunk (default: 4000)

    Returns:
        List of text chunks, each <= max_chars

    Example:
        >>> text = "Para 1\\n\\nPara 2\\n\\nPara 3"
        >>> chunks = chunk_markdown(text, max_chars=10)
        >>> len(chunks)
        3
    """
```

### Documentation Files

Update relevant documentation when making changes:

- **README.md**: User-facing overview, installation, usage
- **ARCHITECTURE.md**: System design, component details
- **CONTRIBUTING.md**: This file - contribution guidelines
- **Inline Comments**: Complex algorithms and business logic

### Documentation Standards

- Use clear, concise language
- Include code examples
- Provide context and rationale
- Keep formatting consistent
- Update version information

## Commit Guidelines

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(extraction): Add support for table extraction

Implement table parsing in FactExtractor to extract facts
from markdown tables in addition to text paragraphs.

Closes #123
```

```
fix(normalization): Correct km² to hectare conversion

The conversion factor was incorrect (should be 100, not 10).
Added test case to prevent regression.
```

### Commit Practices

- Keep commits atomic (one logical change)
- Write descriptive messages
- Reference issues when applicable
- Sign commits if possible

## Feature Development Workflow

### Adding New Provider Support

1. Update `llm_config.py`:
   - Add to `SUPPORTED_PROVIDERS`
   - Add default model
   - Add credential requirements

2. Update `esia_extractor.py`:
   - Add provider configuration in `configure_llm()`
   - Test with sample document

3. Update `step3_analyze_facts.py`:
   - Add provider configuration in `configure_dspy()`

4. Test:
   - Verify API connectivity
   - Run full pipeline with new provider
   - Compare output quality

5. Document:
   - Update README.md with provider info
   - Add configuration example
   - Note any limitations

### Adding New Fact Categories

1. Update `esia_extractor.py`:
   - Modify `FactCategorizationSignature`
   - Add to category and subcategory literals
   - Update few-shot examples if needed

2. Update `FactsheetGenerator`:
   - Add to `CATEGORY_ORDER`

3. Test:
   - Verify categorization works
   - Check factsheet generation
   - Validate CSV output

4. Document:
   - Update category list in README.md
   - Add examples of fact types

### Improving Extraction Accuracy

1. **Modify DSPy Signatures**:
   - Enhance instructions
   - Add examples
   - Adjust output format

2. **Tune LLM Parameters**:
   - Test different models
   - Adjust temperature
   - Increase max_tokens

3. **Enhance Preprocessing**:
   - Improve chunking strategy
   - Better text cleaning
   - Smarter context preservation

4. **Measure Impact**:
   - Compare before/after results
   - Calculate precision/recall
   - Get user feedback

## Common Development Tasks

### Adding a New Output Format

```python
# In esia_extractor.py

def generate_json_output(facts: List[Fact], output_path: Path) -> None:
    """Generate JSON output format for facts.

    Args:
        facts: List of extracted facts
        output_path: Path to save JSON file
    """
    data = [
        {
            "name": fact.name,
            "value": fact.value,
            "unit": fact.unit,
            "evidence": fact.evidence,
            "page": fact.page
        }
        for fact in facts
    ]

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

### Adding Progress Reporting

```python
# Use tqdm for progress bars
from tqdm import tqdm

for item in tqdm(items, desc="Processing", unit="item"):
    process(item)
```

### Implementing New Validation

```python
def validate_fact_consistency(facts: List[Fact]) -> List[str]:
    """Validate fact consistency and return list of issues.

    Args:
        facts: List of facts to validate

    Returns:
        List of validation error messages
    """
    issues = []

    # Your validation logic
    for fact in facts:
        if fact.value_num < 0 and fact.type == "quantity":
            issues.append(f"Negative value for {fact.name}: {fact.value_num}")

    return issues
```

## Release Process

### Version Numbering

Follow Semantic Versioning (SemVer):
- MAJOR.MINOR.PATCH
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Checklist

1. Update version in relevant files
2. Update CHANGELOG.md
3. Run full test suite
4. Update documentation
5. Create git tag: `git tag -a v1.0.0 -m "Release 1.0.0"`
6. Push tag: `git push origin v1.0.0`
7. Create GitHub release with notes

## Getting Help

### Resources

- **Documentation**: Check README.md and ARCHITECTURE.md
- **Issues**: Browse existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions

### Contact

- Create an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Tag maintainers for urgent issues

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Acknowledgments

Contributors will be acknowledged in:
- README.md Contributors section
- Release notes
- Git commit history

Thank you for contributing!
