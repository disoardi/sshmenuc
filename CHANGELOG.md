# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - feature/config-remote-sync

### Added
- **Remote Config Sync**: Manage SSH config via a private Git repository
  - AES-256-GCM encryption with Scrypt key derivation (passphrase-based)
  - Automatic pull on startup, push after every config save
  - Local encrypted backup (`config.json.enc`) always kept in sync - works offline
  - Conflict detection with diff display and interactive resolution (L/R/Abort)
  - `[s]` key in menu to view sync status and trigger manual sync
  - Sync status label displayed in menu header (`SYNC:OK`, `SYNC:OFFLINE`, etc.)
- **Export command** (`--export FILE`): Decrypt and materialize config in plaintext
  - Use `sshmenuc --export /path/to/output.json` to export to file
  - Use `sshmenuc --export -` to print to stdout
- **Offline resilience**: If remote Git is unreachable, app uses local encrypted backup transparently with visible warning

### Configuration
- Add `~/.config/sshmenuc/sync.json` to enable sync (see `sync.json.example`)
- Without `sync.json`, the app runs normally without sync (no changes to existing behavior)

### Dependencies
- Added `cryptography >= 42.0` for AES-256-GCM encryption

## [1.1.1] - 2026-02-16

### Fixed
- **Docker/Container compatibility**: Fixed `OSError` when running in Docker or no-TTY environments
  - Added `get_current_user()` helper function with multiple fallback methods
  - Replaced all `os.getlogin()` calls with `get_current_user()` (navigation.py, launcher.py)
  - Fallback chain: `os.getlogin()` → `os.getenv('USER')` → `getpass.getuser()` → `'user'`
- **PyPI metadata**: Corrected author email format (removed invalid period before @)

### Changed
- Enhanced error handling for username detection in containerized environments
- Improved cross-platform compatibility for user detection

## [1.1.0] - 2026-02-13

### Added
- **Interactive Config Editor**: Integrated CRUD operations directly in navigation menu
  - Add targets and connections with 'a' key
  - Edit connections with 'e' key
  - Delete targets/connections with 'd' key
  - Rename targets with 'r' key
  - Form-based input with validation and confirmation prompts
- **Sphinx Documentation**: Complete API documentation published on GitHub Pages
  - Installation, configuration, and usage guides
  - Full API reference with autodoc
  - Keyboard shortcuts reference
  - Contributing guidelines
- **GitHub Pages**: Automated documentation deployment workflow
- Comprehensive test coverage (102 tests, 69% coverage)
- Type hints improvements with Optional and return types
- Constants for magic numbers (MAX_MARKED_SELECTIONS, MAX_TMUX_PANES)
- PyPI publishing automation workflow
- GitHub Releases automation workflow
- Pre-commit hooks configuration
- .editorconfig for consistent code style
- Makefile for common development tasks
- CONTRIBUTING.md and config.example.json

### Changed
- **All docstrings and comments translated to English** (CLAUDE.md compliance)
- Improved error handling with specific exception types
- Replaced os.system() with subprocess.run() for better security
- Updated menu instructions to show editing commands
- Refactored config.py with helper methods (_get_target_key, _find_target)
- README updated with current project status and documentation links
- Removed poetry.lock from .gitignore (should be committed)

### Fixed
- **Version mismatch**: synchronized __init__.py (0.1.0 → 1.1.0) with pyproject.toml
- **Critical bug in get_previous_node()**: added target aggregation logic matching get_node()
- **CI/CD test failures**: mocked os.getlogin() in tests requiring tty access
- Fixed print_menu() to properly call display.print_table()
- Added missing docs/api/core.rst for Sphinx build

### Documentation
- Complete Sphinx documentation site at https://disoardi.github.io/sshmenuc/
- Updated README with badges (CI, Documentation, Coverage)
- Added "Project Status" and "Future Enhancements" sections
- Documented all breaking changes in v1.1.0

### Technical Improvements
- Code refactoring to eliminate duplication
- Enhanced type safety across codebase
- Improved test coverage for launcher and navigation modules
- Better error messages with debug logging
- CI/CD pipeline with multi-version testing (Python 3.9-3.12)

## [1.0.0] - 2024-XX-XX

### Added
- Complete OOP refactoring with modular architecture (core/ui/utils)
- Support for tmux sessions with automatic session management
- Support for multiple connections with split panes
- Attach to existing tmux sessions
- GitHub Actions CI/CD pipeline
- Mock support for no-tty environments

### Changed
- Migrated from monolithic to modular structure
- Enhanced code organization and maintainability

## [0.0.4] - 2024-XX-XX

### Changed
- Pre-release improvements and bug fixes
