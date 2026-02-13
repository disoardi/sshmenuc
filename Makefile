.PHONY: help install test coverage lint clean build run

help:
	@echo "Available commands:"
	@echo "  install    Install dependencies with Poetry"
	@echo "  test       Run tests"
	@echo "  coverage   Run tests with coverage report"
	@echo "  lint       Check code style"
	@echo "  clean      Clean build artifacts"
	@echo "  build      Build package"
	@echo "  run        Run sshmenuc"

install:
	poetry install

test:
	poetry run pytest -v

coverage:
	poetry run pytest --cov=sshmenuc --cov-report=html --cov-report=term

lint:
	poetry run python -m py_compile sshmenuc/**/*.py

clean:
	rm -rf dist/ build/ *.egg-info
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:
	poetry build

run:
	poetry run sshmenuc
