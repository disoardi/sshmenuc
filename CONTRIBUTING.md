# Contributing to sshmenuc

Thank you for your interest in contributing to sshmenuc!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/disoardi/sshmenuc.git
   cd sshmenuc
   ```

2. **Install Poetry:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies:**
   ```bash
   poetry install
   ```

4. **Activate virtual environment:**
   ```bash
   poetry shell
   ```

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=sshmenuc --cov-report=html

# Run specific test file
poetry run pytest tests/core/test_navigation.py

# Run with verbose output
poetry run pytest -v
```

## Code Quality

Before submitting a PR, ensure your code passes all checks:

```bash
# Run all tests
poetry run pytest

# Check syntax
python -m py_compile sshmenuc/**/*.py
```

## Commit Message Convention

Use conventional commits format:
- `feat(module): add new feature`
- `fix(module): fix bug`
- `docs: update documentation`
- `test: add tests`
- `refactor: refactor code`
- `chore: update dependencies`

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `poetry run pytest`
6. Commit with conventional commit message
7. Push to your fork: `git push origin feature/my-feature`
8. Open a Pull Request against `main` branch

## Code Style

- Follow PEP 8
- Use type hints for all functions
- Write docstrings in Google style (English)
- Keep line length ≤ 100 characters
- Add tests for new features

## Questions?

Open an issue on GitHub or contact the maintainers.
