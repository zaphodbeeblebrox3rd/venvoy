.PHONY: help install install-dev test lint format clean build upload

help:
	@echo "Available commands:"
	@echo "  install     - Install the package"
	@echo "  install-dev - Install development dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  clean       - Clean build artifacts"
	@echo "  build       - Build the package"
	@echo "  upload      - Upload to PyPI"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v --cov=src/venvoy --cov-report=html --cov-report=term

lint:
	flake8 src/venvoy tests/
	mypy src/venvoy
	black --check src/venvoy tests/
	isort --check-only src/venvoy tests/

format:
	black src/venvoy tests/
	isort src/venvoy tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

upload: build
	python -m twine upload dist/* 