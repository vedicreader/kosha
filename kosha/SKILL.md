---
name: kosha
description: >
  Surface repo code and installed package snippets before writing new code.
  Run at the start of any task that touches existing patterns or packages.
  Skip when it's a small change and you know the exact file to look at.
---

# kosha: repo and package memory for coding agents

FTS5 + vector search + call graph over your repo and installed packages.
**Use before Grep, Read, or web search** whenever the question is about existing code or packages.

## When to use / skip

**Use when** you're about to `Read` a source file to learn an API, `grep` for a
function/pattern, check whether a dependency already does something, or decide where
new code goes. Do not skip because you know where to look. Knowing the file does not
tell you what already exists elsewhere.

**Skip when** the path is a known config/lockfile (not code), the task is pure file
structure, or you already have the relevant kosha results in context.

## Invoke

Start the daemon once per session. It avoids the embedding startup on every call (see the timing table under Methods):

```bash
kosha daemon &
```

In-process (`uv run kosha` > `clikernel` if available > `.venv/bin/python`):

```python
from kosha import Kosha
k = Kosha()
k.status()   # call first; returns {files, packages, graph_nodes, stale_files, stale_pkgs}
k.sync(in_parallel=True)   # only if files or packages you need are stale; a stale index looks like missing code
```

**Quick scan.** Run this before you open any file:

```python
for r in k.env_context('description of what you want', limit=10):
    print(r['metadata']['mod_name'], r['metadata'].get('lineno',''), r['content'][:120])
```

## Methods

| Question | Call |
|----------|------|
| Is the index fresh? | `k.status()` |
| Does this exist in a dependency? (package-only, faster) | `k.env_context('desc', limit=8)` |
| Find an existing repo pattern (default; adds repo results and the call graph) | `k.context('desc', graph=True, limit=15)` |
| Repo-only search | `k.repo_context('desc')` |
| Triage many results without full code bodies | `k.context('desc', compact=True)` |
| Who calls this / what does it call / registered peers? | `k.ni('pkg.mod.fn')` |
| How do two nodes connect? | `k.short_path('a.fn', 'b.fn')` |
| What's a package's real public API? (`__all__` + `@patch`) | `k.public_api('pkg')` |
| Where do I add new code? (returns `file:line` insertion points) | `k.where_to_add('desc', limit=5)` |
| Rebuild call graph without re-embedding (for example after a kosha update) | `k.sync(embed=False)` |
| Search long-form docs (READMEs) rather than code | `k.docs_context('desc')` |

Use `context(q, graph=True)` by default once a task touches more than one module.
`env_context` is a semantic similarity search over text. Pass any description, snippet,
or function name.

`rerank=True` on any of the search calls reorders the results with a cross-encoder, a model that scores each result against the query. It reorders
what was retrieved and never adds to it.

The table lists the measured times. The file does not record the measurement conditions.

| step | measured time |
|---|---|
| Embedding startup without the daemon | 3 to 5 s |
| `rerank=True` | 15 to 35 ms |

## Filter syntax

Filters combine with natural language in one query string; bare package names auto-detect as `package:`.

| Token | Example | Effect |
|-------|---------|--------|
| `package:name` (`pkg:`) | `package:fastcore` | Restrict to one package |
| `path:pattern` (`dir:`) | `path:xtras` | Restrict by path substring |
| `file:glob` | `file:xtras*` | Restrict by filename glob |
| `lang:ext` (`ext:`) | `lang:py` | Filter by language |
| `type:node` | `type:FunctionDef` | Filter by AST node type |

An unrecognised key is not dropped. The key stays part of the text query and kosha searches it against every package. The CLI prints a warning. In Python, check
`parseq(q)[1]['_unknown']`.

## Reading a result

```python
{'content': 'def merge(...): ...',
 'metadata': {'mod_name': 'fastcore.basics.merge',  # use for ni()/short_path()
              'path': '...', 'lineno': 655, 'type': 'FunctionDef', 'package': 'fastcore'},
 'pagerank': 0.00027,          # PageRank score; a higher score means greater importance in the call graph
 'callers': [...], 'callees': [...],
 'co_dispatched': [...]}
```

**`co_dispatched`** lists the other functions in the function's co-dispatch group. Module-level lists, tuples and dictionary values define these groups (route groups, handler
tables, plugin registries). Groups that share a function are merged. When you add a new handler, it shows the peers to pattern-match
and where the registration lives, without reading the glue code.

## Pointers

- **MCP server:** if `kosha-mcp` is configured in the host (`claude mcp add kosha -- uv run kosha-mcp`),
  the same operations are available as MCP tools (`status`, `context`, `env_context`, `node_info`,
  `where_to_add`, `public_api`, `api_paths`, ...). Call those directly instead of the
  in-process API.
- **Daemon protocol:** send JSON `{"cmd": "...", "args": {...}}` on stdin. Commands: `sync`,
  `context`, `repo_context`, `env_context`, `ni`, `top_nodes`, `public_api`, `api_call_paths`,
  `status`, `where_to_add`, `short_path`, `neighbors`, `dep_stack`, `nuke`.
- **Package docs:** `from kosha.core import pkg_url` returns the repo or docs URL. Give it to WebFetch (or
  fossick if installed) for usage examples, or to WebSearch for changelogs. nbdev docs anchor on
  the function name (`#fn`); GitHub → `read_gh_file`.
- **`k.codedb` / `k.envdb` are `litesearch.Database` objects.** The full litesearch API (custom
  stores, raw SQL) works directly. See the `/litesearch` skill.
