r"""Search your repo and every installed package by meaning, then follow the call graph between them. Use it before you grep, open a source file, or write code a dependency already provides. Keyword search, vector search and a static call graph over local SQLite, with no LLM calls and no network.

## Start here

`Kosha()` opens two indexes, the repo index (`.kosha/code.db`) and the index of installed packages (`kosha/env.db` in the user data directory), plus the call graph over both. Check that they are current before trusting an answer, because code missing from a stale index looks the same as code that does not exist:

```python
from kosha import Kosha
k = Kosha()
k.status()
# {'files': 4, 'packages': 355, 'graph_nodes': 10630, 'stale_files': 0, 'stale_pkgs': {'httpx': '0.28.1'}, 'new_files': 0}
```

Sync only when something you need is stale. Computing embeddings for changed code is the one slow step:

```python
k.sync()                            # repo, stale packages and call graph
k.sync(embed=False)                 # store new chunks without embeddings: keyword search only, much faster
k.sync(pkgs=['httpx'], repo=False)  # one package
```

Then search. `context` is the default and searches both indexes; `env_context` and `repo_context` search one each and are faster:

```python
for r in k.env_context('atomic file write preserving permissions', limit=8):
    print(r['metadata']['mod_name'], r['metadata'].get('lineno'), r['content'][:120])
```

## Which call answers which question

| Question | Call |
|---|---|
| Is the index current? | `k.status()` |
| Does a dependency already do this? | `k.env_context('desc', limit=8)` |
| What pattern does this codebase use? | `k.context('desc', graph=True, limit=15)` |
| Repo only, no packages | `k.repo_context('desc')` |
| Look over many hits without their source | `k.context('desc', compact=True)` |
| Who calls this, what does it call, what are its peers? | `k.ni('fastcore.basics.merge')` |
| How do two nodes connect? | `k.short_path('a.fn', 'b.fn')` |
| What is within n calls of a node? | `k.neighbors('kosha.core.Kosha', depth=2)` |
| What does a package export? | `k.public_api('fastcore')` |
| Which functions of a package does the most code depend on? | `k.top_nodes('fastcore', k=5)` |
| How does package A reach package B? | `k.api_call_paths('kosha', 'litesearch')` |
| Which packages does a package import, layer by layer? | `k.dep_stack(['fastcore'], depth=2)` |
| Where should new code go? | `k.where_to_add('desc', limit=5)` |
| Search READMEs and other prose, not code | `k.docs_context('desc')` |

`pkg_context` searches package descriptions, one per indexed package, to find a package by what it does. `doc(Kosha)` lists every method with its signature; the table is a map, not the full reference. Indexing (`update_repo`, `update_pkgs`, `process_env`) and deleting (`nuke`, `rm_pkg`, `prune_old_pkgs`) are methods of the same class, but `sync` is the only one you normally need.

## Filters

Filters go inside the query string, next to the plain words, and work with `context`, `env_context` and `repo_context`.

| Token | Aliases | Example | Effect |
|---|---|---|---|
| `package:` | `pkg:`, `packages:`, `pkgs:` | `package:fastcore` | one package |
| `path:` | `dir:`, `folder:`, `paths:` | `path:xtras` | path contains the text |
| `file:` | `filename:`, `files:` | `file:xtras*` | path matches the glob |
| `lang:` | `ext:`, `extension:`, `langs:` | `lang:py` | language, by file extension |
| `type:` | `types:` | `type:FunctionDef` | kind of definition |

Separate several values with commas to accept any of them (`package:httpx,requests`). Every filter excludes code that does not match, and a trailing `!` (`package!:x`) means the same as without it. In `context`, a `package:` filter also skips the repo search. A package name written as a plain word, as in `k.context('fastcore atomic save')`, is not a filter: it ranks that package's hits higher, and other packages still appear.

A filter-shaped token with an unknown key is reported in `parseq(q)[1]['_unknown']`, and the command line prints a warning. The token is searched as plain text, so a typo such as `libr:litesearch` would otherwise return a full page of results that ignore the filter you meant.

## Reading a result

```python
{'content':  'def merge(*ds):\n    "Merge all dicts"\n    ...',
 'metadata': {'mod_name': 'fastcore.basics.merge',   # the name to pass to ni() and short_path()
              'path': '.../fastcore/basics.py', 'lineno': 655,
              'type': 'FunctionDef', 'package': 'fastcore',
              'public_api': True, 'docstring': 'Merge all dicts'},
 'pagerank': 0.00027, 'in_degree': 8, 'out_degree': 12,
 'callers': [...], 'callees': [...], 'co_dispatched': []}
```

`pagerank` measures how much code depends on a node. Changing a node with a high score affects more code, so look at its callers first. `callers` shows where the code is used, and `callees` shows what it uses that you might reuse.

`co_dispatched` is the least obvious field and often the most useful. It lists the functions assigned together with this one in a module-level list, dict or tuple: route tables, handler maps, plugin registries. When you add another handler, it names the existing ones and so shows where they are registered, without reading the glue code.

The graph fields appear only when `graph=True`, the default for `context`. `env_context` and `repo_context` return `content` and `metadata` only.

## The call graph

`k.graph` is the graph itself, a `CodeGraph` built from ast-grep static analysis plus Python AST rules for decorators, registrations and `@patch`. Besides the methods above it has `k.graph.ranked(k=10, module='fastcore')`, `k.graph.callers`, `k.graph.file2nodes` and `k.graph.co_dispatched`; `doc(k.graph)` lists them all.

Node names are the dotted `mod_name` from a hit's metadata. A name that is not in the graph gives an empty result, not an error, so an empty `short_path` means either that there is no path or that a node is not indexed. Check `k.ni(name)` before concluding that two pieces of code do not connect.

## Long-form docs

Code chunks suit code, not prose. `k.docs` is a separate index for READMEs and documentation folders, a litesearch `Index` that splits documents by heading. It is created the first time you use it:

```python
k.add_pkg_docs('fastcore')          # a package's full README
k.add_docs('path/to/docs')          # a folder, a file, or {title: text}
k.docs_context('how do I install')  # ranked sections, each with a node_id
k.docs.read(node_id)['text']        # one whole section
```

`docs_context(q, sections=False)` returns raw chunks instead. The docs index does not track staleness: adding a changed document again stores the new text but does not remove the old version.

## Reranking

`context`, `env_context`, `repo_context` and `pkg_context` take `rerank=True`, which reorders the hits with a flashrank cross-encoder, a small model that scores each hit against the query. The first call downloads the model. Reranking reorders what was retrieved and never adds to it.

It is off by default. It helps most when the query uses the same words as the target's docstring. When a query is phrased differently, the right code is usually missing from the candidates in the first place, and reordering cannot bring it back. `context` reranks only its final top hits; `env_context` and `repo_context` first retrieve a wider pool for the reranker to choose from.

## Outside Python

The same index can be reached in three other ways, for callers that are not Python processes:

- Command line: `kosha sync`, `kosha context 'query' --limit 10 --rerank`, `kosha ni <mod_name>`, `kosha public-api <pkg>`, and `--as-json` on any of them for JSON output.
- Daemon: `kosha daemon` keeps one embedding model loaded and reads `{"cmd": ..., "args": {...}}` requests as JSON lines on standard input, which saves the few seconds of loading on every call.
- MCP: `kosha-mcp` offers the same operations as MCP tools over stdio. If the host already has it configured, call those tools instead of importing anything.

## The indexes are litesearch databases

`k.codedb` and `k.envdb` are litesearch databases, so the whole litesearch API works on them: extra tables, raw SQL, custom stores.

```python
list(k.envdb.q("select content from store where json_extract(metadata,'$.mod_name') = ?", ['fastcore.basics.merge']))
summaries = k.envdb.get_store(name='summaries')   # for example, notes an agent writes about undocumented code
```

Embeddings are stored and read back as 16-bit floats. `kosha.core.cast_emb` enforces that, so a custom embedding function cannot write a wider type by mistake.

Docs: https://vedicreader.github.io/kosha/skill.html.md"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/05_skill.ipynb.

# %% auto #0
__all__ = ['Kosha', 'CodeGraph', 'pkg_url']

# %% ../nbs/05_skill.ipynb #1a2b811a
import kosha.core, kosha.graph
from .core import Kosha, pkg_url
from .graph import CodeGraph
from pyskills import allow

# Read-only surface only: sync/update_*/nuke/rm_pkg write to disk, so allowing them is the host's call.
allow({Kosha: ['status', 'context', 'env_context', 'repo_context', 'pkg_context', 'docs_context',
               'public_api', 'top_nodes', 'api_call_paths', 'dep_stack', 'where_to_add',
               'pkgs_in_env', 'pkgs2consider'],
       CodeGraph: ['node_info', 'node_infos', 'callers', 'callees', 'co_dispatched', 'neighbors',
                   'short_path', 'short_paths', 'ranked', 'file2nodes']},
      pkg_url)

_all_ = ['Kosha', 'CodeGraph', 'pkg_url']
