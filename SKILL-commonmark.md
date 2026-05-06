

# kosha — repo + package memory for coding agents

FTS5 + vector search + call graph over your repo and installed packages.
**Use this before Grep, Read, or web search** whenever the question is
about existing code or packages.

## How to invoke

``` python
from kosha import Kosha
k = Kosha()
k.sync(in_parallel=True)  # incremental — near-instant on repeat runs
```

Use `clikernel` if available (state persists, no re-import cost).
Otherwise `.venv/bin/python -c "..."`.

------------------------------------------------------------------------

## The decision loop

Every coding task runs through the same questions. Use kosha to answer
them before touching files.

<table>
<colgroup>
<col style="width: 62%" />
<col style="width: 37%" />
</colgroup>
<thead>
<tr>
<th>Question</th>
<th>Call</th>
</tr>
</thead>
<tbody>
<tr>
<td>Is the index fresh?</td>
<td><code>k.status()</code></td>
</tr>
<tr>
<td>Does this already exist in a dependency?</td>
<td><code>k.env_context('description', limit=8)</code></td>
</tr>
<tr>
<td>What pattern is used here / how is this done in the repo?</td>
<td><code>k.context('description', graph=True, limit=15)</code></td>
</tr>
<tr>
<td>Who calls this function, and what does it call?</td>
<td><code>k.ni('pkg.module.fn')</code></td>
</tr>
<tr>
<td>How does module A connect to module B?</td>
<td><code>k.short_path('a.fn', 'b.fn')</code></td>
</tr>
<tr>
<td>What is the real public API surface for a package?</td>
<td><code>k.public_api('pkg')</code></td>
</tr>
<tr>
<td>Where do I add my new code?</td>
<td><code>k.where_to_add('description', limit=5)</code></td>
</tr>
</tbody>
</table>

`context(q, graph=True)` is the right default for any task that touches
more than one module. `env_context` is for package-only searches (no
repo results, faster).

**Check status first.** If `stale_files > 0` or `stale_pkgs` is
non-empty, run `k.sync()` before querying — stale results look like
missing results.

------------------------------------------------------------------------

## Before writing code — always check first

``` python
# About to implement atomic file writes?
results = k.env_context('atomic write temp file permissions chmod', limit=8)
for r in results: print(r['metadata']['mod_name'], '\n', r['content'][:200])
# → surfaces fastcore.xtras.atomic_save — reuse it

# User says "fastcore has X" or "check xtras for Y" — use filters, not grep:
k.env_context('package:fastcore path:xtras atomic save', limit=10)

# Scoped to a specific package and path:
k.env_context('package:dockeasy type:FunctionDef run command', limit=10)
```

**Anti-pattern:** invoking this skill, then immediately grepping files.
`env_context` searches all installed packages semantically. Grep only
finds exact strings in files you already know to look in.

------------------------------------------------------------------------

## Filter syntax

Filters combine with natural language in one query string:

<table>
<thead>
<tr>
<th>Token</th>
<th>Example</th>
<th>Effect</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>package:name</code></td>
<td><code>package:fastcore</code></td>
<td>Restrict to one package</td>
</tr>
<tr>
<td><code>path:pattern</code></td>
<td><code>path:xtras</code></td>
<td>Restrict by path substring</td>
</tr>
<tr>
<td><code>file:glob</code></td>
<td><code>file:xtras*</code></td>
<td>Restrict by filename glob</td>
</tr>
<tr>
<td><code>lang:ext</code></td>
<td><code>lang:py</code></td>
<td>Filter by language</td>
</tr>
<tr>
<td><code>type:node</code></td>
<td><code>type:FunctionDef</code></td>
<td>Filter by AST node type</td>
</tr>
</tbody>
</table>

Bare package names in the query are auto-detected as package filters:

``` python
k.context('monsterui fasthtml card component', repo=False)  # restricts to those packages
```

------------------------------------------------------------------------

## Interpreting a result

``` python
{
  'content':  'def merge(*ds):\n    "Merge all dicts"\n    ...',
  'metadata': {
      'mod_name': 'fastcore.basics.merge',  # use this for ni() / short_path()
      'path':     '/path/to/fastcore/basics.py',
      'lineno':   655,
      'type':     'FunctionDef',
      'package':  'fastcore',               # env results only
  },
  'pagerank':      0.00027,  # centrality — higher = more load-bearing, touch carefully
  'in_degree':     8,
  'out_degree':    12,
  'callers':       ['fastcore.script.call_parse._f', ...],
  'callees':       ['fastcore.basics.NS.__iter__', ...],
  'co_dispatched': [],       # see below
}
```

**`pagerank` tells you blast radius.** High-pagerank nodes are
load-bearing — changes ripple widely.

------------------------------------------------------------------------

## Graph navigation

``` python
# Full structural picture of one node
info = k.ni('fastcore.basics.merge')
# info['callers']       — who calls this → where to hook in upstream
# info['callees']       — what it calls → what you can reuse downstream
# info['co_dispatched'] — registered peers (see below)

# Shortest call chain between two nodes
path = k.short_path('kosha.core.Kosha.sync', 'litesearch.core.search')

# Nodes within 2 hops
k.neighbors('kosha.core.Kosha', depth=2)

# Top-k nodes by PageRank for a package
k.graph.ranked(k=10, module='fastcore')

# Public API (respects __all__ + @patch methods)
k.public_api('fastcore')
k.public_api('fastcore.basics')  # scoped to submodule
```

### `co_dispatched` — the most non-obvious signal

Functions assigned together in the same list, dict, or tuple at module
level — route groups, handler tables, plugin registrations. When you
need to add a new handler, `co_dispatched` shows you which functions are
peers and where the registration lives, without reading the glue code.

``` python
k.ni('myapp.routes.get_user')['co_dispatched']
# → ['myapp.routes.create_user', 'myapp.routes.delete_user']
# These three are registered together → follow the same pattern, add yours at the same site
```

------------------------------------------------------------------------

## Compact mode — scan many results quickly

`context(q, compact=True)` returns slim dicts instead of full code
bodies — useful when you need to triage 15+ results before drilling in:

``` python
results = k.context('your task description', limit=20, compact=True)
for r in results:
    print(f"{r['mod_name']}  line {r['lineno']}  pagerank={r['pagerank']:.5f}")
    print(f"  {r['signature']}")
    if r['docstring']: print(f"  # {r['docstring'][:80]}")
# Once you've identified 2-3 candidates, use ni() to drill into them
```

------------------------------------------------------------------------

## Where to add new code

`where_to_add(description)` combines `context` + `co_dispatched` to
return `file:line` insertion points:

``` python
pts = k.where_to_add('add a new route handler', limit=5)
for p in pts:
    print(f"{p['path']}:{p['insert_after']}  ({p['node']})")
    if p['co_dispatched']: print(f"  peers: {p['co_dispatched'][:3]}")
# → tells you the exact file:line to add after, and which peers to pattern-match
```

------------------------------------------------------------------------

## Full structural plan (complex tasks)

``` python
from itertools import combinations

# 1. Find key functions with structural context
results = k.context('your task description', limit=20, graph=True)

# 2. Map call chains between the top results
nodes = [r['metadata']['mod_name'] for r in results[:8]]
paths = [p for a, b in combinations(nodes, 2) if (p := k.short_path(a, b))]
paths.sort(key=len)   # shortest = tightest coupling

# 3. Drill into join points
for node in nodes[:5]:
    info = k.ni(node)
    print(node, '| callers:', list(info['callers'])[:3], '| co_dispatched:', list(info['co_dispatched']))

# 4. Ground the plan in mod_name + lineno
for r in results[:5]:
    m = r['metadata']
    print(f"{m['mod_name']}  line {m.get('lineno','?')}  pagerank={r.get('pagerank',0):.5f}")
```

------------------------------------------------------------------------

## Daemon mode — use this in Claude Code sessions

The first kosha call in a session pays a ~3–5s embedding model
cold-start. Daemon mode starts one warm process and routes all
subsequent calls through it via JSON on stdin/stdout.

**Start once per session:**

``` bash
kosha daemon &
```

**Send requests:**

    → {"cmd":"context","args":{"q":"your task","limit":15,"graph":true}}
    ← {"ok":true,"result":[...]}

    → {"cmd":"env_context","args":{"q":"package:fastcore atomic save","limit":8}}
    ← {"ok":true,"result":[...]}

    → {"cmd":"ni","args":{"mod_name":"fastcore.basics.merge"}}
    ← {"ok":true,"result":{"callers":[...],"callees":[...],"co_dispatched":[]}}

    → {"cmd":"public_api","args":{"pkg":"fastcore"}}
    ← {"ok":true,"result":[...]}

    → {"cmd":"sync","args":{}}
    ← {"ok":true,"result":"synced"}

Available commands: `sync`, `context`, `repo_context`, `env_context`,
`ni`, `top_nodes`, `public_api`, `api_call_paths`, `status`,
`where_to_add`.

**Auto-start hook** (warm daemon available for every session):

``` json
{ "hooks": { "SessionStart": [{ "command": "kosha daemon &" }] } }
```

------------------------------------------------------------------------

## Quick reference

<table>
<colgroup>
<col style="width: 38%" />
<col style="width: 61%" />
</colgroup>
<thead>
<tr>
<th>Method</th>
<th>When to use</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>k.status()</code></td>
<td>Start of session — returns
<code>{files, packages, graph_nodes, stale_files, stale_pkgs}</code></td>
</tr>
<tr>
<td><code>k.context(q, graph=True)</code></td>
<td>Default: any task touching existing code</td>
</tr>
<tr>
<td><code>k.context(q, compact=True)</code></td>
<td>Triage many results — returns slim dicts, no full code bodies</td>
</tr>
<tr>
<td><code>k.env_context(q)</code></td>
<td>Package-only; faster when repo results aren’t needed</td>
</tr>
<tr>
<td><code>k.repo_context(q)</code></td>
<td>Repo-only; when you know the answer is in this codebase</td>
</tr>
<tr>
<td><code>k.ni(node)</code></td>
<td>After finding a node — understand its structural position</td>
</tr>
<tr>
<td><code>k.short_path(a, b)</code></td>
<td>How two modules connect</td>
</tr>
<tr>
<td><code>k.public_api(pkg)</code></td>
<td>What a package exports (not just what’s in
<code>__all__</code>)</td>
</tr>
<tr>
<td><code>k.where_to_add(description)</code></td>
<td>Find file:line insertion point for new code</td>
</tr>
<tr>
<td><code>k.api_call_paths(from_pkg, to_pkg)</code></td>
<td>Shortest paths from one package’s public API to another’s</td>
</tr>
</tbody>
</table>
