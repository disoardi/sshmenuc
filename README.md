# sshmenuc

sshmenuc is a complete rewrite of the original sshmenu tool, implemented as an object‑oriented Python application. The project is redesigned around classes and clear separation of concerns to make the codebase easier to extend, maintain and test.

## Description

sshmenuc provides an interactive terminal menu to browse, filter and launch SSH (and cloud CLI) connections. It supports nested groups of hosts, per‑host metadata (user, connection type, identity file / certkey) and launching different connection commands (e.g., ssh, gcloud ssh inside Docker).

Important: sshmenuc intentionally does NOT store or persist plain‑text passwords. If a password is required, either remember it at runtime or use a secure password manager / SSH keys. Password history or in‑app password storage is not supported by design for security reasons.

## Requirements

- Python 3.8+
- Dependencies (example): readchar, clint, docker
  - These should be declared in pyproject.toml or requirements.txt for packaging.

## Install (buildable pip package)

1. Ensure a packaging config is present (pyproject.toml recommended). Example metadata and dependencies must be declared there.

2. Install build tooling:
```bash
python -m pip install --upgrade build twine
```

3. Build source and wheel distributions:
```bash
python -m build      # creates files in ./dist
# or explicitly:
python -m build --sdist --wheel
```

4. Install locally:
```bash
# install built wheel
python -m pip install dist/sshmenuc-<version>-py3-none-any.whl

# or install in editable mode for development
python -m pip install -e .
```

5. To publish to PyPI:
```bash
python -m pip install --upgrade twine
python -m twine upload dist/*
```

## Development with Poetry

1. Install Poetry (if not already installed): follow https://python-poetry.org/docs/#installation

2. Create / install the environment and dependencies:
```bash
poetry install
```

3. Activate the Poetry virtualenv:
```bash
poetry shell
```
or run commands without activating the shell:
```bash
poetry run python -m build
poetry run pytest
```

## Contributing

Contributions are welcome. Typical workflow:

1. Fork the repository.
2. Create a feature branch:
```bash
git checkout -b feature/my-change
```
3. Implement your changes, add tests and update documentation.
4. Commit and push your branch to your fork:
```bash
git commit -am "Describe change"
git push origin feature/my-change
```
5. Open a Pull Request against the main repository. Describe the change, rationale and any backwards‑incompatible effects.

Please follow the existing code style and include tests for new functionality where appropriate.

## License

This project is licensed under GPLv3. See the LICENSE file for details.
