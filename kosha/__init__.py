"""kosha (कोश) — a treasury of your repo and environment context for coding agents. FTS5 + vector search + call graph, no LLMs required.

Modules:

- `kosha.cli`: The `kosha` shell command: every index and graph query as a subcommand.
- `kosha.core`: Index your repository and its installed packages, then search them by meaning or by keyword.
- `kosha.skill`: Search your repo and every installed package by meaning, then follow the call graph between them. Use it before you grep, open a source file, or write code a dependency already provides. Keyword search, vector search and a static call graph over local SQLite, with no LLM calls and no network."""

__version__ = "0.1.12"
from .core import *
from .graph import *
from .refactor import *
