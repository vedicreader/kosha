---
name: kosha
description: >
  Repo + installed-package memory (FTS5 + vector + call graph). Invoke at the
  start of any task that touches existing repo code or third-party package APIs.
---

# kosha — repo + package memory for coding agents

## Setup

```python
from kosha import Kosha
Kosha(install_skill=True)        # one-time per project: writes .agents/skills/kosha/SKILL.md
k = Kosha(); k.sync()             # once per session — incremental on repeat
```

## The four-step workflow

Run the steps in order. Skip any step that doesn't apply (see *When to skip* below).

### Step 1 — Inventory (cache once per project)

Build a map of **what's installed and what each package exposes**, then write it to
`.kosha/env_map.md` so future sessions read the file instead of re-querying.

```python
from pathlib import Path
cache = Path('.kosha/env_map.md')
if cache.exists():
    env_map = cache.read_text()                       # reuse — no DB hits
else:
    pkgs   = k.pkgs_in_env(pyproject=True)            # [{name, version}, ...]
    layers = k.dep_stack(seeds=[p['name'] for p in pkgs], depth=2)  # BFS, ordered by coupling
    lines  = [f"# Env map\n## Layers\n"] + [f"- L{i}: {sorted(l)}" for i,l in enumerate(layers)]
    for p in pkgs:
        api = k.public_api(p['name'], limit=30)        # public surface + docstrings
        lines += [f"\n## {p['name']} ({p['version']})"] + \
                 [f"- `{r['mod_name']}` — {(r.get('docstring') or '').splitlines()[0][:80]}" for r in api]
    cache.write_text('\n'.join(lines))
    env_map = cache.read_text()
```

### Step 2 — Disambiguate (ask the user when packages overlap)

If the task names a domain ("payments", "ui", "http client") and several installed
packages could plausibly serve it, **ask the user which to use** before searching deeper.

```python
hits = k.env_context('toast notification', limit=30, graph=False)   # cheap, no graph enrichment
by_pkg = {}
for r in hits: by_pkg.setdefault(r['metadata'].get('package'), []).append(r)
candidates = sorted(by_pkg, key=lambda p: -len(by_pkg[p]))[:4]
# If len(candidates) > 1 with comparable hit counts, present them to the user and wait.
# Otherwise, proceed to Step 3 with the single dominant package.
```

### Step 3 — Narrow (one graph-enriched call)

Once the package set is known, run `context()` **once** with a `package:` filter.
The result is already enriched with `pagerank`, `callers`, `callees`, `co_dispatched` —
do **not** loop and call `ni()` afterwards.

```python
results = k.context('toast notification package:monsterui', limit=10)
for r in results:
    m = r['metadata']
    print(f"{m['mod_name']}  L{m.get('lineno','?')}  pr={r.get('pagerank',0):.4f}  "
          f"callers={list(r['callers'])[:2]}  callees={list(r['callees'])[:2]}")
```

### Step 4 — Trace (only when you need cross-package or entry-point info)

```python
k.api_call_paths('myapp', 'fasthtml', k=15)   # how myapp reaches into fasthtml
k.short_path('myapp.routes.checkout', 'stripe.Webhook.construct_event')  # specific pair
k.top_nodes('fasthtml', k=5)                  # entry points to read first when learning a pkg
k.neighbors('myapp.payments.verify', depth=2) # everything within 2 hops
```

## When to skip steps

| Situation | Steps to run |
|---|---|
| Trivial "how does X work" lookup in a known package | Step 3 only |
| First time working in this repo / env | 1 → 3 |
| Task names a domain, multiple packages could fit | 1 → 2 → 3 |
| Task spans packages, or you need entry points | 1 → 3 → 4 |

## Filter syntax

Add `key:value` tokens anywhere in a query. Plurals + comma lists supported.

| Token | Example | Effect |
|---|---|---|
| `package:name` | `package:fasthtml` | Restrict env search to one package |
| `file:glob` | `file:routes*` | Restrict repo results by filename |
| `path:pattern` | `path:api/*` | Restrict repo results by path |
| `lang:ext` | `lang:py` | Filter by language |
| `type:node` | `type:FunctionDef` | Filter by AST node type |

`env_context` also auto-detects bare package names appearing as plain query tokens
(`'render table fasthtml'` → adds `package:fasthtml`).

## Result fields

Each result from `context()` is a dict. Inspect with `dir(r)` / `r.keys()`. Fields:

- `content` — the code snippet
- `metadata` — `{mod_name, path, lineno, type, package?, docstring?}`
- `pagerank`, `in_degree`, `out_degree` — graph centrality
- `callers`, `callees` — adjacent nodes in the call graph
- `co_dispatched` — siblings registered together (route groups, handler tables) — follow this pattern when adding a new handler

## API

| Call | Purpose |
|---|---|
| `k.sync(pkgs=None, dir=None, in_parallel=False, force=False)` | Index repo + env packages + call graph |
| `k.context(q, limit=50, graph=True)` | Fan-out repo+env search, graph-enriched |
| `k.repo_context(q)` / `k.env_context(q)` | Single-store search |
| `k.pkgs_in_env(pyproject=True)` | Indexed packages (intersect with installed env) |
| `k.public_api(pkg, limit=200)` | Public API entries (`__all__` + `@patch`) with docstrings |
| `k.top_nodes(pkg, k=5)` | Top public-API nodes by PageRank |
| `k.dep_stack(seeds, depth=1)` | BFS dep layers, ordered by coupling |
| `k.api_call_paths(from_pkg, to_pkg, k=15)` | Shortest call paths between two packages' public APIs |
| `k.ni(node)` | Node info: callers, callees, co_dispatched, pagerank |
| `k.short_path(a, b)` / `k.neighbors(node, depth)` | Direct graph traversal |
| `k.graph.ranked(k=10, module='pkg')` | Top nodes by PageRank |
| `k.gn(where=...)` / `k.ge(where=...)` | Direct `graph_nodes` / `graph_edges` queries |
| `k.watch_repo()` / `k.nuke()` | Live re-index / drop databases |
| `pkg_url(pkg)` | Best web URL for an installed package (for WebFetch) |

## CLI

For shell harnesses (Copilot CLI, Claude Code hooks). Markdown by default; `--as_json` for piping.

```bash
kosha sync
kosha context "embed a query" --limit 10
kosha context "embed a query" --as_json | jq '.[].metadata.mod_name'
kosha public-api fastcore
kosha api-paths kosha litesearch --k 10
kosha ni "fastcore.basics.merge"
# Full list: kosha (no args) prints all subcommands
```

## Database locations

- `.kosha/code.db` — repo code chunks + embeddings (project-local)
- `.kosha/graph.db` — call graph (project-local)
- `$XDG_DATA_HOME/kosha/env.db` — installed packages (shared across repos)

## Harness install

```bash
# Project-local (default; auto-discovered by Claude Code, Continue.dev, Cursor, Copilot):
#   .agents/skills/kosha/SKILL.md   ← written by Kosha(install_skill=True)
# Claude Code global (all projects on this machine):
mkdir -p ~/.claude/skills/kosha && cp .agents/skills/kosha/SKILL.md ~/.claude/skills/kosha/
# Other harnesses: place SKILL.md at the path the harness scans (e.g. .continue/skills/kosha/).
```
