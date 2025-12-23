# Contributing to GenAI Telemetry

Thank you for your interest in contributing to GenAI Telemetry! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We're all here to build something useful together.

## Getting Started

### Setting Up Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kamalsinghbisht/genai-telemetry.git
   cd genai-telemetry
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests:**
   ```bash
   pytest
   ```

## Development Workflow

### Code Style

We use the following tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **Ruff** for linting
- **mypy** for type checking

Run all formatters and linters:
```bash
black genai_telemetry tests
isort genai_telemetry tests
ruff check genai_telemetry tests
mypy genai_telemetry
```

### Testing

- Write tests for all new features
- Ensure existing tests pass before submitting PR
- Aim for >80% code coverage

```bash
pytest --cov=genai_telemetry --cov-report=html
```

### Commit Messages

Use clear, descriptive commit messages:

- `feat: Add new Prometheus histogram metrics`
- `fix: Resolve thread safety issue in batch processing`
- `docs: Update README with Loki configuration`
- `test: Add unit tests for OTLP exporter`

## Adding a New Exporter

1. Create a new file in `genai_telemetry/exporters/`:
   ```python
   # genai_telemetry/exporters/myplatform.py
   from genai_telemetry.exporters.base import BaseExporter
   
   class MyPlatformExporter(BaseExporter):
       def __init__(self, ...):
           ...
       
       def export(self, span_data: dict) -> bool:
           # Send span_data to your platform
           ...
   ```

2. Add to `exporters/__init__.py`:
   ```python
   from genai_telemetry.exporters.myplatform import MyPlatformExporter
   ```

3. Add to `core/telemetry.py` in `_create_exporter()`:
   ```python
   elif exporter_type == "myplatform":
       return MyPlatformExporter(...)
   ```

4. Update main `__init__.py` with the export

5. Add tests in `tests/test_exporters.py`

6. Update README with usage example

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests and linters
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows project style
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or clearly documented)

## Reporting Issues

When reporting bugs, please include:

- Python version
- Package version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/stack traces

## Questions?

Feel free to open an issue for questions or discussions. We're happy to help!

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
