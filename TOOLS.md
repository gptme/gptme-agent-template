# Tools

Bob has the tools enabled in gptme, and can in addition use the following tools in his workspace.


## Search & Navigation

The workspace provides several ways to search and navigate content:

- Quick search:
  ```sh
  # Find files containing term
  git grep -li <query>

  # Show matching lines
  git grep -i <query>
  ```
- Detailed search with context:
  ```sh
  # Show matching lines
  ./scripts/search.sh "<query>"

  # Show with context
  ./scripts/search.sh "<query>" 1
  ```
- Common locations:
  - tasks/ - Task details
  - journal/ - Daily updates
  - knowledge/ - Documentation

It can often be a good idea to start with a quick search to get an overview, and then use the detailed search to get more context.

Avoid direct use of `grep` or `find` commands, as they may not respect `.gitignore` rules.


## Sharing & Collaboration

The workspace is private to Bob and Erik.

The following tools are available for collaboration:

- [Email](./email/README.md): (WIP) For external communication
- Git
  - When committing, remember to add `Co-authored-by: Bob <bob@superuserlabs.org>` to the commit message.
- GitHub: Can be used to share gists, using `gh gist create <file> -d "<description>"`
  - Contents will be available to anyone with the link, but not searchable/listable unless `--public` is used.
- Website: Can be used to share information publicly
