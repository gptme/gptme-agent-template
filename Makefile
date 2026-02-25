.PHONY: install-precommit install-dotfiles format check test typecheck context stats

# to fix `git grep` for users with PAGER set
PAGER=cat

install: install-precommit  ## Install all hooks and dependencies

install-precommit:  ## Install pre-commit hooks for repo
	pre-commit install

install-dotfiles:  ## Install dotfiles for user, with global git hooks
	./dotfiles/install.sh

format:  ## Fix formatting (ruff)
	pre-commit run ruff-format --all-files || true
	pre-commit run end-of-file-fixer --all-files || true
	pre-commit run trailing-whitespace --all-files || true

check:  ## Run all pre-commit hooks
	pre-commit run --all-files

test:  ## Run tests (if any exist)
	@if [ -d tests ] && find tests -name '*.py' -not -name '__*' | grep -q .; then \
		python3 -m pytest tests/ -v; \
	else \
		echo "No tests found"; \
	fi

typecheck:  ## Run type checking (mypy)
	pre-commit run mypy --all-files

context:  ## Generate context summary
	./scripts/context.sh

stats:  ## Show code statistics
	cloc . --by-file --exclude_dir gptme-contrib,.git,.mypy_cache,__pycache__
