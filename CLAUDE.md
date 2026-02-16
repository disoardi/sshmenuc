# Linee Guida per lo Sviluppo

## Principi Generali
* **KISS** - Keep it simple, stupid
* **Razionalizzazione**: azioni ripetute vanno generalizzate e tradotte in funzioni comuni

## Lingua e Documentazione
- **Conversazioni**: sempre in italiano
- **Documentazione**: sempre in italiano (salvo indicazioni diverse)
- **Commenti nel codice**: sempre in inglese

## Working Style e Preferenze

> **IMPORTANTE**
> Per ogni attività di sviluppo segui i seguenti passi:
>
> 1. **Analizza** la richiesta e i file per avere un quadro completo
> 2. **Elabora** la soluzione di impatto minimo che soddisfa l'esigenza. Se sei nel dubbio esponi le soluzioni e chiedi come procedere
> 3. **Testa** sintassi e funzionalità ricordando di verificare la LOGICA della funzione implementata/modificata:
>    - Per questa attività se servono ambienti utilizza docker
>    - Se serve python usa poetry per gestire il virtual env
> 4. **Documenta**: se ha passato tutti i test compila la documentazione. Se fallisce anche solo un test ripeti il ciclo dal punto 1 applicandolo all'issue trovata
>    - Se superi le 3 iterazioni sulla stessa problematica fermati ed esponimi il problema
> 5. **Commit e Push**: su tutti i remote repo a meno di indicazioni diverse

### Best Practices
* **SEMPRE Chiedere Prima di Over-Engineering**
* **Escludere da git** qualsiasi file di configurazione specifico dell'ambiente di sviluppo:
  - Config dell'IDE
  - Config di Claude
  - Config di test
  - Al massimo creare dei file di esempio e committare quelli
* **Ogni modifica al codice** (fix, feature o altro) richiede revisione della documentazione
* **Ogni modifica a funzioni generali o comuni** richiede la ricerca e la verifica di tutti i punti in cui viene richiamata
* **Preferire ambienti isolati** per sviluppo e funzionamento:
  - Python: utilizzare virtual environment con poetry
  - Se presente docker o un ambiente di containerizzazione preferirlo sempre

## Bash Scripting Guidelines

### Template Structure
Tutti gli script bash devono seguire questa struttura (correttamente identata):

```bash
#!/usr/bin/env bash
################################################################################
# SCRIPT: <nome_script.sh>
# AUTHOR: <nome_autore>
# PURPOSE: <descrizione scopo script>
# DATE: <data creazione>
################################################################################

################################################################################
# IMPORT FUNCTIONS
################################################################################

# Source common libraries from bashLibraries (https://github.com/disoardi/bashLibraries)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common/logging.sh"
source "${SCRIPT_DIR}/lib/common/bash_libraries.sh"

# Source project-specific libraries
source "${SCRIPT_DIR}/lib/ansible_helpers.sh"  # example

################################################################################
# GLOBAL VARIABLES
################################################################################

# Define script-specific variables here

################################################################################
# SIGNAL HANDLING
################################################################################

# Cleanup function
cleanup() {
    einfo "Cleaning up..."
    # Add cleanup logic here
    exit 0
}

# Trap signals
trap cleanup SIGINT SIGTERM SIGQUIT

################################################################################
# FUNCTIONS
################################################################################

# Define script-specific functions here

################################################################################
# MAIN
################################################################################

main() {
    # Main script logic here
    :
}

# Execute main function
main "$@"
```

### Librerie Bash
* **Funzioni generiche utili** a più progetti vanno aggiunte alle [bashLibraries](https://github.com/disoardi/bashLibraries) sul repo remoto
* **Organizzazione librerie**:
  - `lib/common/`: funzioni NON legate al progetto specifico
  - `lib/`: funzioni specifiche al progetto
  - Questa distinzione crea un'alberatura chiara nella directory libs

## Gestione Ambienti

### Python
- Utilizzare **poetry** per gestire virtual environments
- Isolare sempre le dipendenze del progetto

### Docker
- Preferire sempre containerizzazione quando disponibile
- Utilizzare per ambienti di test e sviluppo

## Version Control
- Commit e push su tutti i remote repo salvo indicazioni diverse
- Escludere file di configurazione locale dal repository
- Utilizzare file di esempio per configurazioni quando necessario

## CI/CD Best Practices

### Testing in No-TTY Environments
- **Always mock functions that require terminal access**:
  - `os.getlogin()` - Use `@patch('os.getlogin', return_value='testuser')`
  - `input()` - Mock user input in tests
  - `readchar.readkey()` - Mock keyboard input
- **Test locally with CI environment**:
  - Set `CI=true` and `TERM=dumb` environment variables
  - Verify tests pass: `CI=true TERM=dumb poetry run pytest`
- **Docker testing**: Verify tests pass in Docker containers (simulates GitHub Actions)

### Docker/Container Compatibility
- **Never use system functions without fallback** in production code
- Functions that require TTY/interactive environment:
  - `os.getlogin()` - Add fallback to env vars and getpass
  - `input()` - May not work in non-interactive containers
  - `readchar.readkey()` - Requires TTY
  - Terminal size detection - Check availability first

**Standard fallback pattern**:
```python
def get_current_user() -> str:
    """Get username with Docker/container fallback."""
    try:
        return os.getlogin()
    except (OSError, AttributeError):
        pass

    # Environment variables
    user = os.getenv('USER') or os.getenv('USERNAME')
    if user:
        return user

    # Getpass module
    try:
        return getpass.getuser()
    except Exception:
        pass

    # Final safe default
    return 'user'
```

**Docker testing commands**:
```bash
# With TTY (interactive)
docker run --rm -it python:3.12 bash -c "pip install <package> && <command>"

# Without TTY (verify no-TTY compatibility)
docker run --rm python:3.12 bash -c "pip install <package> && <command>"
```

### GitHub CLI Authentication
- **For public projects on github.com**, authenticate gh CLI separately:
  ```bash
  gh auth status --hostname github.com  # Check authentication
  gh auth login --hostname github.com   # If not authenticated
  ```
- **Note**: Default authentication might be on GitHub Enterprise (e.g., github.dxc.com)
- **Required for**: Viewing workflows, creating releases, managing repository

### GitHub Actions Secrets
- **Document required secrets** in README or .github/README.md
- **Common secrets**:
  - `PYPI_TOKEN` - For PyPI publishing automation
  - `CODECOV_TOKEN` - For coverage reporting (private repos)
  - `NPM_TOKEN` - For npm package publishing
- **Configure at**: https://github.com/USER/REPO/settings/secrets/actions

## Release Process

### Pre-Release Checklist
1. **All tests passing** locally and on CI/CD
2. **Version consistency** across files:
   - `pyproject.toml` (or `package.json`)
   - `<package>/__init__.py` (Python) or `package.json` (Node.js)
   - `docs/conf.py` (if using Sphinx)
3. **CHANGELOG.md updated** with release date (not "Unreleased")
4. **README.md reflects current state** (badges, features, version)
5. **Documentation built successfully** (if applicable)

### Creating a Release

1. **Update CHANGELOG.md** with final release date:
   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD
   ```

2. **Commit changes**:
   ```bash
   git add CHANGELOG.md
   git commit -m "docs: update CHANGELOG for vX.Y.Z release"
   git push origin main
   ```

3. **Create annotated tag** with release notes:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z - Title

   Summary of major changes:
   - Feature A
   - Fix B
   - Improvement C

   See CHANGELOG.md for full details.
   "
   ```

4. **Push tag** to trigger workflows:
   ```bash
   git push origin vX.Y.Z
   ```

5. **Verify automated workflows**:
   - GitHub Release created (check releases page)
   - PyPI/npm package published (if configured)
   - Documentation deployed (if applicable)

### PyPI Publishing Pre-Flight

Before publishing to PyPI:

1. **Validate metadata format**:
   ```bash
   # Check for common issues
   grep -E "authors.*\.\@" pyproject.toml && echo "❌ Invalid email format" || echo "✅ Email OK"
   ```

2. **Build and validate package**:
   ```bash
   poetry build
   pip install twine
   twine check dist/*
   ```

3. **Test on TestPyPI** (recommended for first release):
   ```bash
   poetry config repositories.testpypi https://test.pypi.org/legacy/
   poetry publish -r testpypi
   pip install --index-url https://test.pypi.org/simple/ <package>
   ```

4. **Verify required secrets configured**:
   - `PYPI_TOKEN` for production PyPI
   - `TEST_PYPI_TOKEN` for TestPyPI (optional)

5. **Check workflow triggers**:
   - Verify `publish-pypi.yml` trigger conditions
   - Test manual trigger: `gh workflow run publish-pypi.yml`

### Post-Release Verification

- ✅ **GitHub Release**: https://github.com/USER/REPO/releases/tag/vX.Y.Z
- ✅ **Package published**: https://pypi.org/project/PACKAGE/X.Y.Z/ (or npm)
- ✅ **Documentation updated**: Check docs site if applicable
- ✅ **Assets included**: Verify wheel/tarball or other artifacts

### Rollback (if needed)

If release has critical issues:
1. Delete tag: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`
2. Delete GitHub release (if created)
3. Unpublish from PyPI/npm (if possible, or yank version)
4. Fix issues, increment patch version, release again

## Claude Code Marketplace - Linee Guida Specifiche

Questo repository è un **marketplace** per skills, agenti e script di Claude Code.

### Struttura Marketplace

```
.
├── skills/                    # Skills organizzate per categoria
│   ├── nome-skill/
│   │   ├── comando1/
│   │   │   └── SKILL.md
│   │   ├── comando2/
│   │   │   └── SKILL.md
│   │   ├── README.md
│   │   ├── EXAMPLE.md (opzionale)
│   │   └── examples/ (opzionale)
│   └── ...
│
├── agents/                    # Agenti specializzati
│   ├── nome-agente/
│   │   ├── agent.json
│   │   └── README.md
│   └── ...
│
├── scripts/                   # Script di utility
│   ├── script.sh
│   └── README.md
│
├── install.sh                 # Script installazione globale
├── CLAUDE.md                  # Questo file
└── README.md                  # Documentazione marketplace
```

### Sviluppo Nuova Skill

1. **Crea directory**: `skills/nome-categoria/nome-comando/`
2. **Crea SKILL.md**: Segui il formato con frontmatter YAML
3. **Testa localmente**: Copia in `~/.claude/skills/` e prova
4. **Documenta**: Crea README.md nella categoria
5. **Esempi**: Opzionalmente aggiungi EXAMPLE.md
6. **Commit**: Usa commit message chiaro (es. `feat(skills): add deploy command`)

### Frontmatter SKILL.md

```yaml
---
name: nome-comando
description: Descrizione breve del comando
disable-model-invocation: false  # true se non serve elaborazione AI
allowed-tools: Bash, Read, Write, Grep, Glob  # Tool permessi
argument-hint: [arg1] [arg2]  # Hint per argomenti (opzionale)
---
```

### Variabili Disponibili nelle Skills

- `${CLAUDE_SESSION_ID}` - ID sessione corrente
- `$ARGUMENTS` - Tutti gli argomenti passati
- `$ARGUMENTS[0]`, `$1` - Primo argomento
- `` !`comando` `` - Esecuzione comando shell (output sostituisce placeholder)

### Test Skills

Prima del commit:

```bash
# Copia skill in ~/.claude/skills/
cp -r skills/categoria/comando ~/.claude/skills/

# Testa in Claude Code
/nome-comando [argomenti]

# Verifica funzionamento
# Verifica output
# Verifica gestione errori
```

### Installazione Globale

Le skills in questo marketplace vanno installate **globalmente** in `~/.claude/skills/`:

```bash
# Manuale
cp -r skills/categoria/comando ~/.claude/skills/

# Con script
./install.sh
```

### Commit Messages per Marketplace

- `feat(skills): add session-manager` - Nuova skill
- `feat(agents): add deployment-agent` - Nuovo agente
- `feat(scripts): add backup script` - Nuovo script
- `fix(skills): correct save-session path` - Fix skill
- `docs(skills): update session-manager readme` - Documentazione
- `refactor(skills): optimize load-session` - Refactoring

### Documentazione Skill

Ogni skill category deve avere:
- ✅ `README.md` - Descrizione, installazione, utilizzo
- ✅ `SKILL.md` per ogni comando
- ⚠️ `EXAMPLE.md` - Esempio pratico (raccomandato)
- ⚠️ `examples/` - File di esempio (opzionale)
