# CI/CD Pipeline Setup

This document explains the Continuous Integration/Continuous Deployment (CI/CD) setup for the ESIA Extraction Pipeline.

## Overview

The CI/CD pipeline is configured using **GitHub Actions** and includes:

- **Automated Testing** with pytest
- **Code Quality Checks** (linting, formatting, type checking)
- **Security Scanning** for vulnerabilities
- **Pipeline Validation** to ensure all scripts are valid
- **Pre-commit Hooks** for local development

---

## GitHub Actions Workflow

The main CI/CD workflow is defined in `.github/workflows/ci.yml`.

### Jobs

#### 1. **Test** (`test`)
- Runs on Python 3.10, 3.11, and 3.12
- Installs dependencies from `requirements.txt`
- Executes pytest with coverage reporting
- Uploads coverage reports to Codecov (optional)

#### 2. **Lint** (`lint`)
- **Black**: Checks code formatting (120 char line length)
- **Flake8**: Lints for syntax errors and style issues
- **Pylint**: Advanced linting with complexity checks
- **Mypy**: Static type checking

#### 3. **Security** (`security`)
- **Safety**: Scans dependencies for known vulnerabilities
- **Bandit**: Scans Python code for security issues
- Generates security reports as artifacts

#### 4. **Pipeline Validation** (`pipeline-validation`)
- Validates Python syntax for all pipeline scripts
- Runs `test_llm_configuration.py` to check LLM setup

#### 5. **Build Status** (`build-status`)
- Aggregates results from all jobs
- Fails if critical jobs (test, validation) fail

---

## Running Tests Locally

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=. --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Specific Test Types

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

---

## Code Quality Tools

### Black (Code Formatting)

Format all Python files:
```bash
black .
```

Check formatting without changes:
```bash
black --check .
```

### Flake8 (Linting)

Run flake8:
```bash
flake8 . --max-line-length=120
```

### Pylint (Advanced Linting)

Run pylint on all Python files:
```bash
pylint **/*.py --max-line-length=120
```

### Mypy (Type Checking)

Run mypy:
```bash
mypy . --ignore-missing-imports
```

---

## Security Scanning

### Safety (Dependency Vulnerabilities)

Check for vulnerable dependencies:
```bash
safety check
```

### Bandit (Code Security)

Scan for security issues:
```bash
bandit -r . -f screen
```

Generate JSON report:
```bash
bandit -r . -f json -o bandit-report.json
```

---

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality.

### Installation

```bash
pip install pre-commit
pre-commit install
```

### Manual Execution

Run on all files:
```bash
pre-commit run --all-files
```

Run on staged files only:
```bash
pre-commit run
```

### What Gets Checked

- Trailing whitespace
- End-of-file fixers
- YAML/JSON validation
- Large file detection
- Private key detection
- Code formatting (Black)
- Import sorting (isort)
- Linting (Flake8)
- Security (Bandit)
- Type checking (Mypy)

---

## CI/CD Triggers

The workflow runs on:

- **Push** to `main`, `master`, `develop`, or `claude/**` branches
- **Pull requests** to `main`, `master`, `develop`
- **Manual trigger** via GitHub Actions UI

---

## Test Organization

Tests are organized in the `tests/` directory:

```
tests/
├── __init__.py
├── test_llm_config.py           # LLM configuration tests
├── test_esia_extractor.py       # Core extraction logic tests
└── test_pipeline_integration.py # Integration tests
```

### Test Markers

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_llm` - Tests requiring LLM API access

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | GitHub Actions workflow |
| `pytest.ini` | Pytest configuration |
| `.pre-commit-config.yaml` | Pre-commit hooks configuration |
| `.bandit` | Bandit security scanner configuration |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Git ignore patterns |

---

## Adding New Tests

1. Create test file in `tests/` directory (must start with `test_`)
2. Import the module you want to test
3. Write test functions (must start with `test_`)
4. Use pytest markers for categorization
5. Run tests locally before committing

Example:
```python
import pytest
from my_module import my_function

@pytest.mark.unit
def test_my_function():
    result = my_function(42)
    assert result == 84
```

---

## Troubleshooting

### Tests Failing Locally

1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Check Python version (3.10+): `python --version`
3. Clear pytest cache: `rm -rf .pytest_cache`
4. Run with verbose output: `pytest -vv`

### Pre-commit Hooks Failing

1. Check hook configuration: `pre-commit run --all-files`
2. Update hooks: `pre-commit autoupdate`
3. Clean hooks: `pre-commit clean`
4. Reinstall: `pre-commit uninstall && pre-commit install`

### CI/CD Workflow Failing

1. Check workflow logs in GitHub Actions UI
2. Verify all required secrets are set (API keys, etc.)
3. Test locally using act: `act -j test`
4. Check for syntax errors in `.github/workflows/ci.yml`

---

## Best Practices

1. **Run tests before committing**: `pytest`
2. **Format code before committing**: `black .`
3. **Fix linting issues**: `flake8 .`
4. **Keep dependencies updated**: Check for security vulnerabilities regularly
5. **Write tests for new features**: Aim for >80% code coverage
6. **Use meaningful commit messages**: Follow conventional commits

---

## Next Steps

- [ ] Set up Codecov for coverage tracking
- [ ] Add automated dependency updates (Dependabot/Renovate)
- [ ] Configure deployment workflows
- [ ] Add performance benchmarking
- [ ] Set up automated changelog generation

---

## Support

For issues or questions about the CI/CD setup:
1. Check GitHub Actions logs
2. Review test output locally
3. Consult pytest documentation: https://docs.pytest.org
4. Review GitHub Actions docs: https://docs.github.com/actions

