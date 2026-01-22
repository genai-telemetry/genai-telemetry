# Contributing to GenAI Telemetry

Thank you for your interest in contributing to GenAI Telemetry! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Contributions](#making-contributions)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Developer Certificate of Origin](#developer-certificate-of-origin)

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. 

## Getting Started

### Ways to Contribute

- **Report Bugs**: Open an issue describing the bug
- **Suggest Features**: Open an issue with your idea
- **Improve Documentation**: Fix typos, add examples, clarify explanations
- **Submit Code**: Fix bugs, implement features, improve performance
- **Help Others**: Answer questions in issues and discussions
- **Add Exporters**: Implement new exporter backends

### First-Time Contributors

Look for issues labeled:
- `good first issue` - Simple issues for newcomers
- `help wanted` - Issues where we need assistance
- `documentation` - Documentation improvements

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- pip

### Setting Up Your Environment

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/genai-telemetry.git
cd genai-telemetry

# Add upstream remote
git remote add upstream https://github.com/genai-telemetry/genai-telemetry.git

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Verify setup
pytest
```

### Project Structure

```
genai-telemetry/
├── genai_telemetry/       # Main package
│   ├── __init__.py        # Package initialization, public API
│   └── ...
├── core/                   # Core telemetry manager
├── decorators/             # Tracing decorators
├── exporters/              # Exporter implementations
│   ├── splunk/
│   ├── elasticsearch/
│   ├── opentelemetry/
│   └── ...
├── utils/                  # Utility functions
├── examples/               # Usage examples
├── tests/                  # Test suite
├── docs/                   # Documentation
└── pyproject.toml          # Project configuration
```

## Making Contributions

### Creating a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create a feature branch
git checkout -b feature/your-feature-name
# Or for bug fixes
git checkout -b fix/issue-description
```

### Commit Messages

Follow conventional commit format:

```
type(scope): short description

Longer description if needed.

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, missing semi-colons)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or correcting tests
- `chore`: Build process or auxiliary tool changes

**Examples:**
```
feat(exporters): add Loki exporter support

Implements Grafana Loki exporter with batching support.

Fixes #45
```

```
fix(decorators): correct token extraction for Anthropic responses

The token count was being read from wrong field in Claude responses.

Fixes #78
```

## Pull Request Process

1. **Ensure your code passes all tests:**
   ```bash
   pytest
   ```

2. **Ensure code quality:**
   ```bash
   ruff check .
   mypy genai_telemetry/
   ```

3. **Update documentation** if needed

4. **Add/update tests** for your changes

5. **Sign your commits** (see DCO section below)

6. **Create the Pull Request:**
   - Fill out the PR template completely
   - Link related issues
   - Add appropriate labels
   - Request review from maintainers

7. **Address review feedback:**
   - Make requested changes
   - Push additional commits
   - Re-request review when ready

8. **Merge:**
   - PRs require at least one maintainer approval
   - All CI checks must pass
   - Squash and merge is preferred

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use [ruff](https://github.com/astral-sh/ruff) for linting
- Maximum line length: 100 characters
- Use type hints for all public functions

### Code Quality Tools

```bash
# Linting
ruff check .

# Type checking
mypy genai_telemetry/

# Formatting
ruff format .
```

### Example Code Style

```python
from typing import Any, Dict, Optional

def trace_llm_call(
    model_name: str,
    model_provider: str,
    *,
    track_tokens: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator to trace LLM calls.

    Args:
        model_name: Name of the model being called.
        model_provider: Provider of the model (e.g., 'openai', 'anthropic').
        track_tokens: Whether to extract and track token usage.
        metadata: Additional metadata to include in traces.

    Returns:
        Decorated function that traces LLM calls.

    Example:
        >>> @trace_llm_call("gpt-4", "openai")
        ... def chat(prompt: str) -> str:
        ...     return client.chat(prompt)
    """
    # Implementation
    ...
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=genai_telemetry --cov-report=html

# Run specific test file
pytest tests/test_decorators.py

# Run specific test
pytest tests/test_decorators.py::test_trace_llm

# Run with verbose output
pytest -v
```

### Writing Tests

- Place tests in `tests/` directory
- Mirror the source structure
- Use descriptive test names
- Include docstrings explaining test purpose

```python
import pytest
from genai_telemetry import trace_llm

class TestTraceLLM:
    """Tests for the trace_llm decorator."""

    def test_basic_tracing(self):
        """Verify basic LLM call tracing works correctly."""
        @trace_llm(model_name="gpt-4", model_provider="openai")
        def mock_llm_call():
            return "response"
        
        result = mock_llm_call()
        assert result == "response"
        # Additional assertions...

    def test_token_extraction_openai(self):
        """Verify token extraction from OpenAI responses."""
        # Test implementation
        ...
```

## Documentation

### Updating Documentation

- Keep docstrings up to date
- Update README.md for significant changes
- Add examples for new features
- Update API reference docs

### Building Documentation

```bash
cd docs
pip install -r requirements.txt
make html
# View at docs/_build/html/index.html
```

## Developer Certificate of Origin

All contributions must be signed off to indicate you have the right to submit the code.

### What is DCO?

The [Developer Certificate of Origin (DCO)](https://developercertificate.org/) is a lightweight way for contributors to certify that they wrote or have the right to submit the code.

### How to Sign Off

Add `-s` or `--signoff` to your git commit:

```bash
git commit -s -m "feat: add new feature"
```

This adds a line to your commit message:
```
Signed-off-by: Your Name <your.email@example.com>
```

### Setting Up Automatic Sign-off

Configure git to always sign off:

```bash
# Set your name and email
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Create an alias for signed commits
git config --global alias.ci 'commit -s'
```

### Fixing Missing Sign-offs

If you forgot to sign off:

```bash
# For the last commit
git commit --amend -s

# For multiple commits, interactive rebase
git rebase -i HEAD~N  # N = number of commits
# Mark commits as 'edit', then amend each with -s
```

## Questions?

- Open a [GitHub Discussion](https://github.com/genai-telemetry/genai-telemetry/discussions)
- Join our Slack channel (via LF AI Slack)
- Email: info@genai-telemetry.io

---

Thank you for contributing to GenAI Telemetry! 🎉
