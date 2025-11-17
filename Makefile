# UV-based Makefile for newsdedup

.PHONY: sync install upgrade clean shell lint bandit show-results tests all

# Sync dependencies from lock file
sync:
	uv sync

# Install the project and dependencies
install:
	uv sync --all-extras

# Upgrade all dependencies
upgrade:
	uv lock --upgrade
	uv sync

# Clean build artifacts
clean:
	find . -name "*.pyc" -exec rm -f {} \;
	rm -rf __pycache__ bandit .venv uv.lock
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Open a shell with the virtual environment activated
shell:
	uv run $(SHELL)

# Run linting tools
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff check --fix .
	uv run ruff format .

# Run bandit security checks
bandit:
	test -d bandit || mkdir bandit
	uv run bandit ./newsdedup.py > bandit/bandit-newsdedup.py.txt || true
	uv run bandit ./unstar.py > bandit/bandit-unstar.py.txt || true
	uv run bandit ./list_feeds.py > bandit/bandit-list_feeds.py.txt || true

# Show bandit results
show-results:
	grep -A2 "Test results:" bandit/* || echo "No bandit results found"

# Run all tests
tests: lint bandit

# Run everything
all: sync tests show-results
