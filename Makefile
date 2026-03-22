.PHONY: help install-precommit install-dotfiles format check test typecheck context stats

# to fix `git grep` for users with PAGER set
PAGER=cat

# Use prek (faster Rust-based runner) if available, fall back to pre-commit
PRE_COMMIT := $(shell command -v prek 2>/dev/null || echo pre-commit)

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: install-precommit  ## Install all hooks and dependencies

install-precommit:  ## Install pre-commit hooks for repo
	$(PRE_COMMIT) install

install-dotfiles:  ## Install dotfiles for user, with global git hooks
	./dotfiles/install.sh

format:  ## Fix formatting (ruff)
	$(PRE_COMMIT) run ruff-format --all-files || true
	$(PRE_COMMIT) run end-of-file-fixer --all-files || true
	$(PRE_COMMIT) run trailing-whitespace --all-files || true

check:  ## Run all pre-commit hooks
	$(PRE_COMMIT) run --all-files

test:  ## Run tests (if any exist)
	@if [ -d tests ] && find tests -name '*.py' -not -name '__*' | grep -q .; then \
		python3 -m pytest tests/ -v; \
	else \
		echo "No tests found"; \
	fi

typecheck:  ## Run type checking (mypy)
	$(PRE_COMMIT) run mypy --all-files

context:  ## Generate context summary
	./scripts/context.sh

stats:  ## Show code statistics
	cloc . --by-file --exclude_dir gptme-contrib,.git,.mypy_cache,__pycache__
