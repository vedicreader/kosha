---
name: kosha
description: >
  Surface repo code and installed package snippets before writing new code.
  Run at the start of any task that touches existing patterns or packages.
---

# kosha — repo + package memory for coding agents

FTS5 + vector search + call graph over your repo and installed packages. Results include
callers, callees, and PageRank. No LLMs required.

## Setup

**One-time per project:**
```python
from kosha import Kosha
Kosha(install_skill=True)   # writes .agents/skills/kosha/SKILL.md
```

**Once per session** (incremental — fast on repeat):
```python
k = Kosha()
k.sync(pkgs=['fasthtml', 'fastcore'])  # repo code + packages + call graph
```

## Orchestration patterns

### Pattern 1 — Quick lookup
*Simple "how does X work?" questions about existing code or packages.*

```python
results = k.context('how do I embed a query', limit=10)
for r in results:
    print(r['metadata']['mod_name'], r['content'][:120])
```

### Pattern 2 — Before writing code
*Any task that adds or modifies behaviour. Run before touching files.*

```python
# 1. Get relevant snippets enriched with call graph
results = k.context('your task description', limit=15, graph=True)

# 2. Read structural position of each result
for r in results:
    print(r['metadata']['mod_name'],
          '| pagerank:', r['pagerank'],
          '| callers:', r['callers'],
          '| callees:', r['callees'])

# 3. Write code that fits the existing patterns
```

### Pattern 3 — Full structural plan
*Complex tasks, unfamiliar codebases, anything touching multiple modules.*

```python
from itertools import combinations

# Step 1: identify relevant packages + dependency tree
tc = k.task_context('your task description', depth=2)
# tc['packages']   — ranked packages relevant to the query
# tc['dep_layers'] — BFS dep layers ordered by coupling strength

# Step 2: find key functions, enriched with graph data
results = k.context('your task description', limit=20, graph=True)

# Step 3: map call chains between the top results
nodes = [r['metadata']['mod_name'] for r in results[:8]]
paths = [p for a, b in combinations(nodes, 2) if (p := k.short_path(a, b))]
paths.sort(key=len)   # shortest = tightest coupling

# Step 4: drill into join points
for node in nodes[:5]:
    info = k.ni(node)
    # info['callers']       — who calls this → where to hook in upstream
    # info['callees']       — what it calls → what you can reuse downstream
    # info['co_dispatched'] — registered peers → pattern to follow for new routes/handlers

# Step 5: write a plan grounded in mod_name + lineno
for r in results[:5]:
    m = r['metadata']
    print(f"{m['mod_name']}  line {m.get('lineno', '?')}  pagerank={r.get('pagerank', 0):.5f}")
```

> **`co_dispatched`** — functions assigned together in the same list/dict at module level (route
> groups, plugin registrations, handler tables). Tells you where to add a new handler without
> reading all the glue code.

## What a graph-enriched result looks like

```python
{
  'content':  'def merge(*ds):\n    "Merge all dicts"\n    return {k:v for d in ds ...}',
  'metadata': {
      'mod_name': 'fastcore.basics.merge',   # fully-qualified — use for ni() / short_path()
      'path':     '/path/to/fastcore/basics.py',
      'lineno':   655,
      'type':     'FunctionDef',
      'package':  'fastcore',                # env results only
  },
  # structural position
  'pagerank':      0.00027,  # centrality — higher = more load-bearing
  'in_degree':     8,        # number of callers
  'out_degree':    12,       # number of callees
  'callers':       ['fastcore.script.call_parse._f', ...],
  'callees':       ['fastcore.basics.NS.__iter__', ...],
  'co_dispatched': [],
}
```

## Filter syntax

| Token | Example | Effect |
|-------|---------|--------|
| `package:name` | `package:fasthtml` | Restrict env search to one package |
| `file:glob` | `file:routes*` | Restrict repo results by filename |
| `path:pattern` | `path:api/*` | Restrict repo results by path |
| `lang:ext` | `lang:py` | Filter by language |
| `type:node` | `type:FunctionDef` | Filter by AST node type |

Plural and comma-separated values work: `packages:fastcore,litesearch paths:basics,core`

## Graph API

| Call | Returns |
|------|---------|
| `k.ni(node)` | Full node info: meta + callers + callees + co_dispatched |
| `k.short_path(a, b)` | Shortest call chain between two nodes |
| `k.neighbors(node, depth=2)` | All nodes within N hops |
| `k.graph.ranked(k=10, module='pkg')` | Top-k nodes by PageRank |
| `k.public_api(module='pkg', min_callees=0)` | Public entry points (in_degree=0) with docstrings |
| `k.gn(where='node like "%X%"')` | Direct graph_nodes table query |
| `k.ge(where='caller like "%X%"')` | Direct graph_edges table query |

## Full API

| Method | Purpose |
|--------|---------|
| `k.sync(pkgs, dir)` | One-shot sync: repo + packages + graph |
| `k.context(q, limit, graph)` | Fan-out search, graph-enriched |
| `k.repo_context(q, limit)` | Repo only |
| `k.env_context(q, limit)` | Packages only |
| `k.task_context(q, depth)` | Packages + dep stack |
| `k.watch_repo()` | Live incremental re-index on file changes |
| `k.nuke()` | Drop all databases |
| `pkg_url(pkg)` | Best web URL for an installed package (from importlib.metadata) |

## Database locations

- `.kosha/code.db` — repo code chunks + embeddings (project-local)
- `.kosha/graph.db` — call graph (project-local)
- `$XDG_DATA_HOME/kosha/env.db` — installed packages (global, shared across repos)

## Harness installation

**Project-local** (auto-discovered by most harnesses, commit alongside code):
```python
Kosha(install_skill=True)   # → .agents/skills/kosha/SKILL.md
```

**Claude Code — global** (available in all projects):
```bash
mkdir -p ~/.claude/skills/kosha
cp .agents/skills/kosha/SKILL.md ~/.claude/skills/kosha/SKILL.md
```

**Other harnesses**: place SKILL.md wherever the harness discovers agent skills
(`.agents/skills/`, `.continue/skills/`, or configure path in harness settings).
