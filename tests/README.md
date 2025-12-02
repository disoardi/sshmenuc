# sshmenuc Tests

This directory contains comprehensive tests for the refactored sshmenuc application.

## Test Structure

```
tests/
├── conftest.py          # Pytest configuration and fixtures
├── core/                # Tests for core business logic
│   ├── test_base.py     # BaseSSHMenuC tests
│   ├── test_config.py   # ConnectionManager tests
│   ├── test_navigation.py # ConnectionNavigator tests
│   └── test_launcher.py # SSHLauncher tests
├── ui/                  # Tests for UI components
│   ├── test_colors.py   # Colors class tests
│   └── test_display.py  # MenuDisplay tests
└── utils/               # Tests for utility functions
    └── test_helpers.py  # Helper functions tests
```

## Running Tests

### Run all tests
```bash
poetry run pytest -v
```

### Run specific test modules
```bash
poetry run pytest tests/core/test_config.py -v
poetry run pytest tests/ui/ -v
```

### Run with coverage
```bash
poetry run pytest --cov=sshmenuc --cov-report=html
```

### Run specific test functions
```bash
poetry run pytest tests/core/test_base.py::TestBaseSSHMenuC::test_load_config_valid_file -v
```

## Test Categories

- **Unit Tests**: Test individual functions and methods in isolation
- **Integration Tests**: Test interaction between components
- **Mock Tests**: Use mocks for external dependencies (subprocess, file system)

## Fixtures

The `conftest.py` file provides shared fixtures:

- `temp_config_file`: Temporary JSON config file for testing
- `sample_host_entry`: Valid host entry dictionary
- `sample_hosts_list`: List of host entries for group testing

## Coverage

Tests aim for high coverage of:
- Core business logic (config management, navigation, SSH launching)
- UI components (colors, display rendering)
- Utility functions (argument parsing, logging, validation)
- Error handling and edge cases