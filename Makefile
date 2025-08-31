# Makefile for napari-mcp testing and development

.PHONY: help install test test-fast test-parallel test-gui test-all coverage lint format security clean

# Variables
PYTHON := python3
UV := uv
PYTEST := $(UV) run pytest
RUFF := $(UV) run ruff
WORKERS := auto

# Default target
help:
	@echo "napari-mcp Development Commands"
	@echo "================================"
	@echo "install          - Install all dependencies including test extras"
	@echo "test             - Run standard test suite"
	@echo "test-fast        - Run quick smoke tests"
	@echo "test-parallel    - Run tests in parallel"
	@echo "test-gui         - Run GUI tests with real napari"
	@echo "test-all         - Run all tests including GUI"
	@echo "test-coverage    - Run tests with coverage report"
	@echo "test-benchmark   - Run performance benchmarks"
	@echo "lint             - Run all linting checks"
	@echo "format           - Auto-format code"
	@echo "security         - Run security checks"
	@echo "clean            - Clean all generated files"
	@echo "analyze          - Analyze test performance"

# Installation
install:
	$(UV) sync --all-extras
	$(UV) pip install -e .
	pre-commit install

# Testing targets
test:
	$(PYTEST) tests/ -v -m "not realgui" --tb=short

test-fast:
	$(PYTEST) tests/test_tools.py tests/test_integration.py::TestBasicIntegration -v -x --tb=short

test-parallel:
	$(PYTEST) tests/ -v -m "not realgui" -n $(WORKERS) --dist loadscope --tb=short

test-gui:
	@echo "Running GUI tests..."
	RUN_REAL_NAPARI_TESTS=1 QT_QPA_PLATFORM=offscreen PYTEST_QT_API=pyqt6 \
		$(PYTEST) tests/ -v -m realgui --tb=short

test-all: test-parallel test-gui

test-coverage:
	$(PYTEST) tests/ -v -m "not realgui" \
		-n $(WORKERS) \
		--cov=napari_mcp \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-fail-under=70
	@echo "Coverage report: file://$(PWD)/htmlcov/index.html"

test-benchmark:
	$(PYTEST) tests/ -v -m "not realgui" \
		--benchmark-only \
		--benchmark-autosave \
		--benchmark-compare

# Code quality
lint:
	@echo "Running linting checks..."
	$(RUFF) check src/ tests/
	$(RUFF) format --check src/ tests/
	$(UV) run mypy src/napari_mcp/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	$(RUFF) check --fix src/ tests/
	$(RUFF) format src/ tests/

security:
	@echo "Running security checks..."
	$(UV) run bandit -r src/ --skip B110,B101,B102,B307
	$(UV) run safety check

# Analysis
analyze:
	@echo "Analyzing test performance..."
	$(PYTHON) scripts/analyze_test_performance.py

organize:
	@echo "Analyzing test organization..."
	$(PYTHON) scripts/organize_tests.py

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf .tox/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage.*" -delete

# CI simulation
ci-local:
	@echo "Simulating CI pipeline locally..."
	$(MAKE) clean
	$(MAKE) install
	$(MAKE) lint
	$(MAKE) security
	$(MAKE) test-parallel
	$(MAKE) test-coverage

# Development workflow
dev: format lint test-fast
	@echo "Quick development check complete!"

# Pre-commit simulation
pre-commit: format lint test-fast
	@echo "Pre-commit checks passed!"

# Show current test statistics
stats:
	@echo "Test Statistics:"
	@echo "----------------"
	@find tests -name "test_*.py" | wc -l | xargs echo "Test files:"
	@grep -r "def test_" tests/ | wc -l | xargs echo "Test functions:"
	@grep -r "@pytest.mark.realgui" tests/ | wc -l | xargs echo "GUI tests:"
	@grep -r "@pytest.mark.slow" tests/ | wc -l | xargs echo "Slow tests:"
