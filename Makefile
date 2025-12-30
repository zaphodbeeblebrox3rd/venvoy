.PHONY: help install bootstrap install-dev test lint format clean build upload \
	docker-dev update upgrade

help:
	@echo "Available commands:"
	@echo "  bootstrap     - Install venvoy (containerized, no Python needed)"
	@echo "  install       - Install for development (requires Python)"
	@echo "  update        - Update venvoy to latest version"
	@echo "  upgrade       - Alias for update command"
	@echo "  docker-dev    - Run development environment in container"
	@echo "  test          - Run tests (containerized)"
	@echo "  lint          - Run linting (containerized)"
	@echo "  format        - Format code (containerized)"
	@echo "  clean         - Clean build artifacts"
	@echo "  build         - Build the package (containerized)"
	@echo "  check-package - Check package with twine"
	@echo "  upload-test   - Upload to TestPyPI (for testing)"
	@echo "  upload        - Upload to PyPI (production)"
	@echo "  publish       - Interactive publishing script"

# Recommended installation method - no Python needed on host
bootstrap:
	@echo "🚀 Running bootstrap installation (containerized)..."
	@if [ -f install.sh ]; then \
		bash install.sh; \
	else \
		curl -fsSL \
			https://raw.githubusercontent.com/zaphodbeeblebros3rd/venvoy/main/install.sh \
			| bash; \
	fi

# Development installation - requires Python on host
install:
	@echo "🚀 Installing venvoy for development..."
	@echo "🧹 Clearing Python bytecode cache..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@if command -v pip >/dev/null 2>&1; then \
		pip install -e .; \
		echo "✅ Installed for development"; \
	else \
		echo "❌ Python/pip not found. Use 'make bootstrap' instead:"; \
		echo "   make bootstrap"; \
		exit 1; \
	fi

# Run development environment in container
docker-dev:
	@echo "🐳 Starting containerized development environment..."
	@docker run --rm -it \
		-v $(PWD):/workspace \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-w /workspace \
		python:3.11-slim bash -c "\
			apt-get update && apt-get install -y git docker.io && \
			pip install -e . && \
			bash"

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Containerized test execution
test:
	@echo "🧪 Running tests in container..."
	@docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		python:3.11-slim bash -c "\
			pip install -e . && \
			pip install pytest pytest-cov && \
			pytest tests/ -v \
				--cov=src/venvoy \
				--cov-report=html \
				--cov-report=term"

# Containerized linting
lint:
	@echo "🔍 Running linting in container..."
	@docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		python:3.11-slim bash -c "\
			pip install -e . && \
			pip install flake8 mypy black isort && \
			flake8 --max-line-length=120 src/venvoy tests/ && \
			mypy src/venvoy && \
			black --check src/venvoy tests/ && \
			isort --check-only src/venvoy tests/"

# Containerized code formatting
format:
	@echo "✨ Formatting code in container..."
	@docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		python:3.11-slim bash -c "\
			pip install black isort && \
			black src/venvoy tests/ && \
			isort src/venvoy tests/"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Containerized package building
build: clean
	@echo "📦 Building package in container..."
	@docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		python:3.11-slim bash -c "\
			pip install build && \
			python -m build"

# Check package with twine
check-package: build
	@echo "🔍 Checking package with twine..."
	@docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		python:3.11-slim bash -c "\
			pip install twine && \
			python -m twine check dist/*"

# Upload to TestPyPI (for testing)
upload-test: check-package
	@echo "📤 Uploading to TestPyPI..."
	@docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		python:3.11-slim bash -c "\
			pip install twine && \
			python -m twine upload --repository testpypi dist/*"

# Upload to PyPI (production - requires credentials)
upload: check-package
	@echo "📤 Uploading to PyPI..."
	@docker run --rm \
		-v $(PWD):/workspace \
		-w /workspace \
		python:3.11-slim bash -c "\
			pip install twine && \
			python -m twine upload dist/*"

# Interactive publishing script
publish:
	@echo "🚀 Running interactive publishing script..."
	@python scripts/publish.py

# Update venvoy to latest version
update:
	@echo "🔄 Updating venvoy to latest version..."
	@if [ -f install.sh ]; then \
		bash install.sh; \
	else \
		curl -fsSL \
			https://raw.githubusercontent.com/zaphodbeeblebros3rd/venvoy/main/install.sh \
			| bash; \
	fi

# Alias for update command
upgrade: update 