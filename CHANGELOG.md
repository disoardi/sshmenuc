# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.3] - 2026-02-26

### Added
- **`[c]` → contesto → `[i]` Reimport da file in chiaro**: permette di reimportare un config JSON
  in chiaro nel contesto corrente senza uscire dall'app. Il file viene cifrato con la passphrase
  della sessione, salvato nel backup `.enc` locale e opzionalmente pushato al remote.
  Se il contesto è attivo, la configurazione in memoria viene aggiornata immediatamente.
- **Eliminazione file sorgente dopo import**: dopo aver importato un file in chiaro (wizard
  `--add-context` o reimport da UI), l'app chiede se eliminare il file originale (default: sì).
- **Sub-menu per i contesti nel `[c]`**: selezionando un contesto ora si apre un sub-menu con
  `[m]` (Modifica parametri sync) e `[i]` (Reimport da file), invece di procedere direttamente
  alla modifica.

## [1.3.2] - 2026-02-26

### Fixed
- **False conflict detection in zero-plaintext mode** (`startup_pull`): after the first
  successful sync, the plaintext `config.json` is deleted. On subsequent startups,
  `_hash_config_file()` returned `""` (file not found) which incorrectly triggered the
  "both sides changed" conflict dialog on every run. Fixed by restoring `_config_data`
  from the local `.enc` backup before the conflict check, so the local hash is computed
  correctly from the actual local state.

## [1.3.1] - 2026-02-26

### Fixed
- `[c]` → "Modifica sync": aggiunto campo `remote_file` come campo modificabile interattivamente
  - Consente di correggere il nome del file remoto (es. da `config.json.enc` a `isp.enc`) senza editare `contexts.json` a mano
  - Il file precedente nel repo remoto non viene rimosso automaticamente (farlo manualmente con `git rm`)

## [1.3.0] - 2026-02-26

### Added

#### Context Management from UI (`[c]` key)
- **New `[c]` key** in the menu: opens a context management panel (visible only in multi-context mode)
  - **Add a new context**: interactive wizard (same as `--add-context`) without leaving the app
    - Configure remote URL, branch, remote file, local repo path
    - Optionally trigger an immediate first encrypted push
    - Offer to switch to the new context immediately after creation
  - **Edit sync config** of any existing context (active or not):
    - Change `remote_url` and/or `branch` interactively
    - If editing the active context, the SyncManager is reinitialized in-session immediately
- **`[c]manage`** label added to the menu instruction bar alongside `[x]ctx:NAME`

### Refactored
- `_add_context_wizard()` extracted from `main.py` into `sshmenuc/contexts/wizard.py` as `add_context_wizard()`
  - `main.py` now imports from `wizard.py` (no functional change for CLI users)
  - `navigation.py` can now call `add_context_wizard()` without circular imports
- `_switch_to_context(name)` extracted from `_handle_context_switch()` into a reusable private method
  - Reused by both `[x]` (switch) and `[c]` (new context → offer switch)

### Added to ContextManager
- `update_sync_config(name, partial_cfg)`: merge-updates sync fields (e.g. `remote_url`, `branch`) of a context without touching metadata like `last_sync` and `last_config_hash`

## [1.2.0] - 2026-02-20

### Added

#### Multi-Context Profiles
- **Named contexts** (`~/.config/sshmenuc/contexts.json`): Manage multiple independent SSH profiles (e.g. `home`, `work`, `isp`)
  - Each context has its own remote repo, branch, passphrase and local cache
  - `[x]` key in menu to switch context interactively at runtime
  - Auto-selects context on startup (or prompts when more than one is configured)
- **`--add-context NAME`** wizard: Interactive CLI to create a new encrypted context from an existing `config.json`
- **Auto-import**: On first run in multi-context mode, legacy `config.json` is automatically copied to the active context's local cache
- **Migration dialog**: If a plaintext `config.json` exists at the default path with no `.enc` yet, the app offers to convert it to a named context on first launch

#### Remote Config Sync
- Sync your SSH config across multiple machines using a private Git repository
  - AES-256-GCM + Scrypt encryption (passphrase-based)
  - Automatic pull on startup, push after every config save
  - Local encrypted backup (`config.json.enc`) always kept in sync — works offline
  - Conflict detection with diff display and interactive resolution (L/R/Abort)
  - `[s]` key in menu to view sync status, trigger manual sync, or launch guided setup
  - Sync status label displayed in menu header (`SYNC:OK`, `SYNC:OFFLINE`, `SYNC:NO-BACKUP`)
- **Export command** (`--export FILE`): Decrypt and export config to plaintext
  - `sshmenuc --export /path/to/output.json` — export to file
  - `sshmenuc --export -` — print to stdout
- **Offline resilience**: If the remote Git is unreachable, the app falls back to the local encrypted backup transparently

#### Zero-Plaintext-On-Disk Mode
- When sync is configured, **`config.json` is never written to disk**
  - On startup: the `.enc` file is decrypted into RAM; no plaintext file is created
  - On save: the config is encrypted directly to `.enc` (no plaintext intermediate file)
  - Any stale `config.json` is automatically removed after the first successful decrypt
  - Offline mode: local `.enc` is decrypted in-memory when the remote is unreachable
- Two simultaneous instances each decrypt independently (Unix process isolation)
- Passphrase verified on every startup, including when the remote reports no changes (`NO_CHANGE`)

#### Host Entry Improvements
- **`extra_args`** field: Pass arbitrary SSH arguments per host (e.g. `"-t bash"`, `"-o StrictHostKeyChecking=no"`)
  - Propagated to both single and multi-host (tmux) connections
- **Host entry validation** at config load: warns on invalid `extra_args` (not `shlex`-parseable) and out-of-range `port` values; does not abort, allows partial use of valid entries

### Configuration
- `~/.config/sshmenuc/sync.json` — single-file sync (backward compatible)
- `~/.config/sshmenuc/contexts.json` — multi-context registry
- Without either file, the app runs with no sync (no changes to existing behavior)

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
