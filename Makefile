.PHONY: install-precommit install-dotfiles

# to fix `git grep` for users with PAGER set
PAGER=cat

install-precommit:  ## Install pre-commit hooks for repo
	pre-commit install

install-dotfiles:  ## Install dotfiles for user, with global git hooks
	./dotfiles/install.sh

stats:  ## Show code statistics
	cloc . --by-file --exclude_dir gptme-contrib,.git,.mypy_cache,__pycache__
