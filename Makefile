.PHONY: install-precommit install-dotfiles

# to fix `git grep` for users with PAGER set
PAGER=cat

install-precommit:  ## Install pre-commit hooks for repo
	pre-commit install

install-dotfiles:  ## Install dotfiles for user, with global git hooks
	./dotfiles/install.sh
