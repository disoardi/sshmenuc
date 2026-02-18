# sshmenuc

[![PyPI version](https://badge.fury.io/py/sshmenuc.svg)](https://pypi.org/project/sshmenuc/)
[![PyPI downloads](https://img.shields.io/pypi/dm/sshmenuc.svg)](https://pypi.org/project/sshmenuc/)
[![CI](https://github.com/disoardi/sshmenuc/workflows/CI/badge.svg)](https://github.com/disoardi/sshmenuc/actions)
[![Documentation](https://github.com/disoardi/sshmenuc/workflows/Documentation/badge.svg)](https://github.com/disoardi/sshmenuc/actions)
[![Coverage](https://codecov.io/gh/disoardi/sshmenuc/branch/main/graph/badge.svg)](https://codecov.io/gh/disoardi/sshmenuc)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## Overview

sshmenuc is a complete rewrite of the original sshmenu tool, implemented as an object‑oriented Python application. The project has been redesigned around classes and clear separation of concerns to make the codebase easier to extend, maintain and test.

## Documentation

📚 **Complete documentation is available at: [https://disoardi.github.io/sshmenuc/](https://disoardi.github.io/sshmenuc/)**

- [Installation Guide](https://disoardi.github.io/sshmenuc/installation.html)
- [Configuration Reference](https://disoardi.github.io/sshmenuc/configuration.html)
- [Usage Guide](https://disoardi.github.io/sshmenuc/usage.html)
- [API Documentation](https://disoardi.github.io/sshmenuc/api/core.html)
- [Contributing](https://disoardi.github.io/sshmenuc/contributing.html)

## Description

sshmenuc provides an interactive terminal menu to browse, filter and launch SSH (and cloud CLI) connections. It supports nested groups of hosts, per‑host metadata (user, connection type, identity file / certkey) and launching different connection commands (e.g., ssh, gcloud ssh inside Docker).

### Key Features

- 🔐 **Interactive configuration editor** - Add, edit, delete, and rename targets and connections directly from the menu
- 📁 **Nested host groups** - Organize connections hierarchically
- 🖥️ **Multiple connection support** - Launch up to 6 connections in tmux split panes
- 🎨 **Colorized terminal UI** - Clear visual feedback and navigation
- 🔑 **SSH key support** - Per-host identity file configuration
- 🐳 **Docker/Cloud CLI** - Support for gcloud ssh and other connection types
- ✅ **Comprehensive testing** - 108 tests ensuring reliability

**Security Note**: sshmenuc intentionally does NOT store or persist plain‑text passwords. If a password is required, either remember it at runtime or use a secure password manager / SSH keys. Password history or in‑app password storage is not supported by design for security reasons.

## Requirements

- Python 3.9+
- Dependencies: readchar, clint, docker
  - These are declared in pyproject.toml for packaging

## New Modular Structure

```
sshmenuc/
├── __init__.py
├── __main__.py          # Module entry point
├── main.py              # Application entry point
├── core/                # Core business logic
│   ├── __init__.py
│   ├── base.py          # Common base class BaseSSHMenuC
│   ├── config.py        # ConnectionManager (CRUD operations)
│   ├── config_editor.py # ConfigEditor (interactive editing)
│   ├── navigation.py    # ConnectionNavigator (menu & keyboard)
│   └── launcher.py      # SSHLauncher (tmux & SSH)
├── ui/                  # User interface
│   ├── __init__.py
│   ├── colors.py        # Color management (Colors)
│   └── display.py       # Menu rendering (MenuDisplay)
└── utils/               # Common utilities
    ├── __init__.py
    └── helpers.py       # Helper functions
```

## Common Base Class

### `BaseSSHMenuC` (core/base.py)

Abstract class providing common functionality to all other classes:

- **Configuration management**: Loading, saving, validation
- **Logging setup**: Base logging system configuration
- **Utility methods**: Directory creation, data structure validation
- **Template Method pattern**: Abstract `validate_config()` method to implement

#### Shared Functionality:
- `load_config()`: JSON configuration loading and normalization
- `save_config()`: Configuration saving
- `get_config()` / `set_config()`: Configuration getter/setter
- `has_global_hosts()`: Check for hosts presence in configuration
- `_create_config_directory()`: Configuration directory creation

## Derived Classes

### 1. `ConnectionManager` (core/config.py)
Extends `BaseSSHMenuC` for configuration management:
- CRUD operations on targets and connections
- Specific validation for configuration structures
- Methods to create, modify, delete targets and connections

### 2. `ConfigEditor` (core/config_editor.py)
Interactive configuration editor (uses `ConnectionManager`):
- Form-based target and connection editing
- Add, edit, delete, rename operations
- User-friendly prompts and confirmations
- Integrated keyboard shortcuts (a/e/d/r keys)

### 3. `ConnectionNavigator` (core/navigation.py)
Extends `BaseSSHMenuC` for menu navigation:
- Main navigation loop
- User input handling (arrows, space, enter)
- Multiple selection with markers
- Integration with `MenuDisplay` for rendering
- Integrated `ConfigEditor` for inline editing

### 4. `SSHLauncher` (core/launcher.py)
Standalone class for connection launching:
- tmux session management (single and multiple)
- SSH command construction with parameters
- Session name sanitization
- Multiple connection launching with split panes

## UI Components

### `Colors` (ui/colors.py)
- ANSI color constants definitions
- Text coloring helper methods
- Semantic methods (`success()`, `warning()`, `error()`)

### `MenuDisplay` (ui/display.py)
- Table and menu rendering
- Header, row, footer management
- Multiple selection and marker support
- Complete separation of display logic

## Utilities

### `helpers.py` (utils/helpers.py)
- Argument parser setup
- Logging configuration
- Host entry validation
- Generic support functions

## Installation

### Install from PyPI (Recommended)

The easiest way to install sshmenuc is directly from PyPI:

```bash
pip install sshmenuc
```

Or to install a specific version:

```bash
pip install sshmenuc==1.1.0
```

### Install from Source (Development)

For development or to install from source:

1. Clone the repository:
```bash
git clone https://github.com/disoardi/sshmenuc.git
cd sshmenuc
```

2. Install with Poetry:
```bash
poetry install
```

3. Or install in editable mode with pip:
```bash
pip install -e .
```

### Development with Poetry

1. Install Poetry: https://python-poetry.org/docs/#installation

2. Create/install environment and dependencies:
```bash
poetry install
```

3. Activate Poetry virtualenv:
```bash
poetry shell
# or run commands without activating:
poetry run python -m sshmenuc
```

### Running the Application

```bash
# As a module (recommended)
python -m sshmenuc

# Direct execution
python sshmenuc/main.py

# With arguments
python -m sshmenuc -c /path/to/config.json -l debug
```

## Configuration Reference

The configuration file (`~/.config/sshmenuc/config.json`) uses the following structure:

```json
{
  "targets": [
    {
      "Group Name": [
        { <host entry> },
        { <host entry> }
      ]
    }
  ]
}
```

### Host Entry Fields

| Campo | Tipo | Default | Descrizione |
|---|---|---|---|
| `friendly` | string | **required** | Nome visualizzato nel menu |
| `host` | string | **required** | Hostname, IP o nome container |
| `user` | string | current user | Username per la connessione |
| `port` | integer | `22` | Porta SSH |
| `certkey` | string | — | Path alla chiave privata SSH (es. `~/.ssh/id_rsa`) |
| `extra_args` | string | — | Argomenti SSH aggiuntivi (es. `"-t bash"`, `"-o StrictHostKeyChecking=no"`) |
| `connection_type` | string | `ssh` | Tipo connessione: `ssh`, `gssh` (Google Cloud), `docker` |
| `zone` | string | — | Zona cloud (solo `gssh`) |
| `project` | string | — | Progetto cloud (solo `gssh`) |
| `command` | string | — | Comando custom (solo `docker`, es. `"docker exec -it"`) |

### Esempi

```json
{
  "targets": [
    {
      "Production": [
        {
          "friendly": "web-01",
          "host": "web01.example.com",
          "user": "admin",
          "port": 22,
          "certkey": "~/.ssh/prod_key"
        },
        {
          "friendly": "jump-host",
          "host": "jump.example.com",
          "user": "admin",
          "extra_args": "-t bash"
        }
      ]
    },
    {
      "Docker": [
        {
          "friendly": "nginx",
          "host": "nginx_container",
          "command": "docker exec -it",
          "connection_type": "docker"
        }
      ]
    }
  ]
}
```

> **Tip**: usa `sshmenuc -c /path/to/config.json` per specificare un file di configurazione alternativo.

## Refactoring Benefits

### 1. **Separation of Concerns**
- Each class has a specific, well-defined responsibility
- UI separated from business logic
- Configuration isolated from navigation

### 2. **Reusability**
- Base class provides common functionality
- UI components reusable in other contexts
- SSH launcher usable independently

### 3. **Testability**
- Smaller, focused classes
- Injectable dependencies
- Well-defined public methods for unit testing

### 4. **Extensibility**
- Easy to add new connection types
- Template Method pattern for customizations
- Modular structure for new features

### 5. **Maintainability**
- Logically organized code
- Reduced code duplication
- Clear interfaces between modules

## Migration Guide

### Using the New Structure:

```python
# Instead of importing everything from one file
from sshmenuc.core import ConnectionManager, ConnectionNavigator
from sshmenuc.ui import Colors, MenuDisplay
from sshmenuc.utils import setup_logging

# Create objects with common inheritance
config_manager = ConnectionManager("config.json")
navigator = ConnectionNavigator("config.json")

# Both inherit from BaseSSHMenuC
assert isinstance(config_manager, BaseSSHMenuC)
assert isinstance(navigator, BaseSSHMenuC)
```

### Breaking Changes in v1.1.0
- Original monolithic `sshmenuc.py` has been removed
- Entry point is now `main.py` with modular structure
- All functionality maintained through new class-based architecture
- Configuration format remains compatible

## Testing

The project includes comprehensive test coverage:

- **102 tests** across all modules
- **69% code coverage** (targeting 90%+)
- **CI/CD integration** with GitHub Actions
- **Multi-version testing** on Python 3.9, 3.10, 3.11, 3.12

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=sshmenuc --cov-report=html

# Run specific test file
poetry run pytest tests/core/test_navigation.py -v
```

### Test Examples

```python
# Base class testing
def test_base_config_loading():
    manager = ConnectionManager("test_config.json")
    assert manager.validate_config()

# Isolated UI component testing
def test_colors():
    colors = Colors()
    assert colors.success("test").startswith("\033[92m")

# Launcher testing with mocks
def test_ssh_launcher():
    launcher = SSHLauncher("test.com", "user")
    assert launcher.host == "test.com"
```

## Contributing

Contributions are welcome. Typical workflow:

1. Fork the repository
2. Create a feature branch:
```bash
git checkout -b feature/my-change
```
3. Implement changes, add tests and update documentation
4. Commit and push your branch:
```bash
git commit -am "Describe change"
git push origin feature/my-change
```
5. Open a Pull Request against the main repository

Please follow the existing code style and include tests for new functionality where appropriate.

## License

This project is licensed under GPLv3. See the LICENSE file for details.

## Project Status

**Version 1.1.0** - Production Ready ✅

- ✅ **Available on PyPI**: `pip install sshmenuc`
- ✅ Complete modular refactoring with OOP design
- ✅ Comprehensive test suite (102 tests, 69% coverage)
- ✅ Full API documentation with Sphinx
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Interactive configuration editor
- ✅ Python 3.9+ support

## Future Enhancements

Potential improvements for future versions:

1. **Observer pattern for UI events**
   - Decouple UI event handling from business logic
   - Enable plugin-based event listeners

2. **Dependency injection framework**
   - Improve testability and flexibility
   - Enable runtime component swapping

3. **Enhanced features**
   - SSH connection pooling
   - Session history and favorites
   - Advanced filtering and search
   - Custom key bindings

Contributions and suggestions are welcome!