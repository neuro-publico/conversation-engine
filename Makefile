.PHONY: help install lint format test test-cov clean

# Default target
help:
	@echo "Conversational Engine - Available commands:"
	@echo ""
	@echo "  make install     - Install all dependencies"
	@echo "  make lint        - Run linting checks (black, isort, flake8)"
	@echo "  make format      - Format code with black and isort"
	@echo "  make test        - Run all tests"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo "  make clean       - Remove cache and build files"
	@echo ""

# Install dependencies
install:
	pip install -r requirements.txt

# Run linting checks
lint:
	@echo "Checking code formatting with Black..."
	black --check --line-length 120 app/ tests/
	@echo ""
	@echo "Checking import sorting with isort..."
	isort --check-only --profile black --line-length 120 app/ tests/
	@echo ""
	@echo "Running flake8..."
	flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=120 --statistics --ignore=E501,W503,E203
	@echo ""
	@echo "All lint checks passed! ✓"

# Format code
format:
	@echo "Formatting code with Black..."
	black --line-length 120 app/ tests/
	@echo ""
	@echo "Sorting imports with isort..."
	isort --profile black --line-length 120 app/ tests/
	@echo ""
	@echo "Code formatted! ✓"

# Run tests
test:
	pytest tests/ -v --tb=short

# Run tests with coverage
test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

# Run only unit tests
test-unit:
	pytest tests/unit -v --tb=short

# Run only integration tests
test-integration:
	pytest tests/integration -v --tb=short

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	@echo "Cleaned! ✓"

# Run the application locally
run:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000
