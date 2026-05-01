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
# Or sync all pyproject.toml deps including transitive:
k.sync(in_parallel=True, depth=2)
```

**Fast re-sync after package changes** (avoids re-embedding already-indexed rows):
```python
from kosha import env_pkg_versions
k.update_pkgs(set(env_pkg_versions()), embed=False, force=True)  # update files, skip embedding
k.process_env()                                                    # embed only new rows (embedding IS NULL)
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

# Step 1: find key functions, enriched with graph data
results = k.context('your task description', limit=20, graph=True)

# Step 2: map call chains between the top results
nodes = [r['metadata']['mod_name'] for r in results[:8]]
paths = [p for a, b in combinations(nodes, 2) if (p := k.short_path(a, b))]
paths.sort(key=len)   # shortest = tightest coupling

# Step 3: drill into join points
for node in nodes[:5]:
    info = k.ni(node)
    # info['callers']       — who calls this → where to hook in upstream
    # info['callees']       — what it calls → what you can reuse downstream
    # info['co_dispatched'] — registered peers → pattern to follow for new routes/handlers

# Step 4: write a plan grounded in mod_name + lineno
for r in results[:5]:
    m = r['metadata']
    print(f"{m['mod_name']}  line {m.get('lineno', '?')}  pagerank={r.get('pagerank', 0):.5f}")
```

> **`co_dispatched`** — functions assigned together in the same list/dict at module level (route
> groups, plugin registrations, handler tables). Tells you where to add a new handler without
> reading all the glue code.

### Pattern 4 — Onboard an unfamiliar codebase (first session)
*New repo, new package, or starting fresh after a long break.*

```python
k = Kosha(); k.sync()

# 1. Find the most structurally load-bearing nodes
hubs = k.top_nodes('mypackage', k=5)
for node in hubs:
    info = k.ni(node)
    print(node, '| callers:', list(info['callers'])[:3])

# 2. Discover hidden coupling — the architectural gotchas
for s in k.surprising_connections(top_n=5):
    print(s['caller'], '→', s['callee'],
          f"kind={s['kind']} surprise={s['surprise_score']} emb_dist={s['embedding_distance']}")

# 3. What changed since last session?
d = k.graph_diff()
if d['new_nodes']: print('New entry points:', d['new_nodes'][:5])

# 4. Find semantic peers for a key function (cross-package, embedding-space)
peers = k.find_similar('mypackage.core.process', k=5)
# → surfaces analogous patterns in fastcore, litesearch, etc. that graphify can't find
for p in peers:
    print(p['metadata'].get('mod_name'), p['content'][:80])
```

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

`env_context` also **auto-detects package names** from plain query tokens — words in the query that
match installed package names are automatically added as package filters. So
`k.context('payments page monsterui fasthtml', repo=False)` restricts to monsterui and fasthtml
results when those packages are installed, and returns nothing if they are not.

## Graph API

| Call | Returns |
|------|---------|
| `k.ni(node)` | Full node info: meta + callers + callees + co_dispatched |
| `k.short_path(a, b)` | Shortest call chain between two nodes |
| `k.neighbors(node, depth=2)` | All nodes within N hops |
| `k.graph.ranked(k=10, module='pkg')` | Top-k nodes by PageRank |
| `k.public_api(pkg)` | Public API entries for pkg (respects `__all__` + `@patch` methods) |
| `k.public_api('pkg.module')` | Public API scoped to a submodule |
| `k.api_call_paths(from_pkg, to_pkg, k=15)` | Dict `{to_node: path}` of shortest call paths from `from_pkg` public API to `to_pkg` public API |
| `k.top_nodes(pkg, k=5)` | Top-k public API nodes for pkg ranked by PageRank |
| `k.gn(where='node like "%X%"')` | Direct graph_nodes table query |
| `k.ge(where='caller like "%X%"')` | Direct graph_edges table query |

## Analytical methods (graphify-inspired + embedding-enhanced)

| Call | Returns |
|------|---------|
| `k.graph_diff()` | Delta since last sync: new/removed nodes+edges, PageRank shifts |
| `k.find_similar(node, k=10)` | k most embedding-similar nodes — semantic peers with no call-graph edge required |
| `k.surprising_connections(top_n=10)` | Cross-module edges ranked by structural + semantic (embedding distance) surprise |

`find_similar` is kosha's unique advantage: because every chunk has a CodeRankEmbed vector, it surfaces
parallel implementations and analogous patterns across packages that graphify (AST-only) cannot find.

## Full API

| Method | Purpose |
|--------|---------|
| `k.sync(pkgs, dir, in_parallel)` | One-shot sync: repo + packages + graph; `in_parallel=True` for concurrent sync |
| `k.context(q, limit, graph)` | Fan-out search, graph-enriched |
| `k.repo_context(q, limit)` | Repo only |
| `k.env_context(q, limit)` | Packages only; auto-detects package names in query tokens |
| `k.dep_stack(seeds, depth)` | BFS over pkg_deps from seed packages, ordered by coupling strength |
| `k.update_pkgs(pkgs, embed, force)` | Re-sync package files; `embed=False` skips embedding (fast metadata-only update) |
| `k.process_env()` | Embed only env rows with `embedding IS NULL` |
| `env_pkg_versions(pyproject, depth)` | Dict `{pkg: version}` for installed packages; traverses transitive deps if `depth > 0` |
| `pkg_trans_deps(seeds, depth)` | BFS over importlib.metadata requires; returns seeds + all transitive deps |
| `k.watch_repo()` | Live incremental re-index on file changes |
| `k.nuke()` | Drop all databases |
| `pkg_url(pkg)` | Best web URL for an installed package (from importlib.metadata) |

## Database locations

- `.kosha/code.db` — repo code chunks + embeddings (project-local)
- `.kosha/graph.db` — call graph (project-local)
- `$XDG_DATA_HOME/kosha/env.db` — installed packages (global, shared across repos)

## CLI

Shell access to all kosha functionality. Default output is markdown; `--as_json` for JSON piping.

```bash
kosha sync                                      # index repo + env + call graph
kosha context "embed a query" --limit 10        # fan-out search
kosha context "embed a query" --as_json         # JSON output for piping
kosha repo-context "parse filters"              # repo only
kosha env-context "fastcore store_attr"         # packages only
kosha ni "kosha.core.Kosha"                     # node info: callers, callees, pagerank
kosha public-api fastcore                       # public API for a package
kosha api-paths kosha litesearch --k 10         # call paths between packages
kosha dep-stack --seeds kosha --depth 2         # BFS dependency layers
kosha top-nodes fastcore --k 5                  # top PageRank nodes
kosha watch                                     # live re-index (blocking)
kosha diff                                      # show graph delta since last sync
kosha find-similar fastcore.basics.merge --k 5 # semantic peers (embedding-space neighbors)
kosha surprising --top_n 10                     # surprising cross-module connections
kosha daemon                                    # persistent kernel (see Daemon mode below)
```

## Daemon mode (recommended for harnesses)

Avoids the ~3-5s embedding model cold-start on every CLI call. Start once per session; all
subsequent `kosha` calls route through the warm process.

```bash
kosha daemon   # blocks; reads newline-delimited JSON from stdin, writes to stdout
```

Protocol:
```
→ stdin:  {"cmd":"context","args":{"query":"your task","limit":15,"graph":true}}
← stdout: {"ok":true,"result":[...]}

→ stdin:  {"cmd":"graph_diff","args":{}}
← stdout: {"ok":true,"result":{"new_nodes":[...],"removed_nodes":[...],"pagerank_shifts":[...]}}

→ stdin:  {"cmd":"find_similar","args":{"node":"fastcore.basics.merge","k":5}}
← stdout: {"ok":true,"result":[...]}
```

Available daemon commands: `sync`, `context`, `repo_context`, `env_context`, `ni`,
`graph_diff`, `find_similar`, `surprising`, `top_nodes`, `public_api`, `api_call_paths`.

**Claude Code — session-start hook** (warm daemon for all kosha calls in a session):
```json
{ "hooks": { "SessionStart": [{ "command": "kosha daemon &" }] } }
```

## pyskills

kosha registers as a [pyskill](https://github.com/AnswerDotAI/pyskills) for Python-native LLM hosts (e.g. solveit):

```python
from pyskills.core import list_pyskills, doc
list_pyskills()        # discovers 'kosha.skill' without importing it
import kosha.skill
doc(kosha.skill)       # full API overview
doc(kosha.skill.Kosha) # class detail with all method signatures
```

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
