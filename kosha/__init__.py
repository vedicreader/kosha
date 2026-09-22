"""kosha (कोश) — a treasury of your repo and environment context for coding agents. FTS5 + vector search + call graph, no LLMs required.

Modules:

- `kosha.cli`: Single `kosha` entry point with subcommands for shell-based harnesses. Default output is readable markdown; pass `--as-json` for JSON (piping/harnesses).
- `kosha.core`: Kosha is a tool for building a context for code generation based on your repo and environment. It uses a vector database to store code snippets and their embeddings, allowing you to search for relevant code based on natural language queries. The core functionality includes managing the database, updating package metadata, embedding code snippets, and performing context-aware searches.
- `kosha.skill`: Search your repo and every installed package by meaning, then walk the call graph that connects them — reach for this before you grep, open a source file, or write code a dependency already provides. FTS5 keyword search, vector search and a static call graph over local SQLite: no LLM calls, no network, answers in milliseconds."""

__version__ = "0.1.9"
from .core import *
from .graph import *
from .refactor import *
