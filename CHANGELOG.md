# Release notes

<!-- do not remove -->

## 0.1.15
- `process_env` embeds every chunk and package description with no embedding, in batches that each commit with their HNSW update, so an interrupted run resumes. Before, it filled the embedding column without updating the index, so the vectors were invisible to search. `kosha embed [--pkg] [--batch]` runs it. On a copy of a 304,000-row index it embedded 64,678 rows in 31 s.
- `update_pkg` with embeddings on also embeds a package's leftover NULL chunks, including when the package is already indexed at its version. A sync run with `embed=False` had left them NULL for good.
- `Kosha.prune_env(dry_run=False)` and `kosha prune [--dry-run]` remove a package's chunks when no known site-packages folder holds it at any version, and a `packages` row when none holds that exact version, then VACUUM and rebuild the HNSW index once. A chunk's `version` is the version it was first stored under, so it does not mark a stale chunk.
- The notebooks set `XDG_DATA_HOME` to a temporary folder, so running the test suite no longer writes to the shared index in `~/.local/share/kosha`.

## 0.1.14
- The package set comes from the pyproject of `Kosha.root`, read by the new `pyproject_deps(root)`. Before, `status`, `sync` and `env_pkg_versions` found the pyproject from the current folder, so `Kosha(dir=other)` run from elsewhere, as Leela's server does, indexed another project's packages or none.

## 0.1.13
- Installed packages are looked up in the project's own environment: the repo's `.venv`, else a `$VIRTUAL_ENV` inside the repo, plus folders its `.pth` files name. `env_path(root)` finds it and `Kosha.env_path` keeps it. Before, kosha used the interpreter it ran in, so `kosha sync` from the uv tool, or Leela's sync, failed on a project dependency with `pkg fastai is not in environment`. With no project environment, behaviour is as before.
- A symlink loop, dangling link or unreadable folder in the repo no longer stops `sync` or `status`, through litesearch 0.1.53.
- Needs litesearch 0.1.53.

## 0.1.12
- The code, package and package-description stores have an index on `json_extract(metadata,'$.name')`, created when a store is opened. A lookup by name no longer scans the store: 25 ms instead of 1.2 to 2.8 s on a 239,000-row package store.
- A repo chunk moved by an edit keeps its new `lineno`, through litesearch 0.1.52. An index written before this release is re-parsed once when it is opened, with `PRAGMA user_version` recording `CODE_FORMAT` 1. Embeddings are reused.
- `update_repo` skips a file that fails to parse and indexes the rest. Before, one empty notebook stopped every sync of the repo.
- `update_repo` drops the rows of a changed file that no longer yields chunks, such as a module cut down to imports and `__all__`.
- `update_repo` reads each file's mtime before parsing it, so an edit made during the parse is picked up by the next sync.
- Needs litesearch 0.1.52.

## 0.1.11
- `update_repo(files=...)` indexes only the listed paths and drops the ones that are gone; `watch_repo` and `kosha watch` no longer crash on the first change.
- `update_pkg` stores each package's description in `pkg_store` through the new `put_pkg_doc`, so `pkg_context` returns hits.
- `prune_old_versions` drops old chunks by their `package` column, and old descriptions too.
- `env_context` and `repo_context` drop the unused `wide` parameter; the keyword leg already ORs the query terms.
- The call graph parses a single batch in-process, so the docs build no longer breaks on Linux, where a spawned pool cannot load a notebook-defined function.
- `dev` is an extra, as nbdev's CI installs it, with the uv group pointing at it; needs nbdev 3.3.25.

## 0.1.10
- `sync(verbose=False)` and `update_pkgs(parallel=True, verbose=False)` show no progress bar. They used to write one to stdout whatever `verbose` said, which corrupted the output of a caller that prints JSON on stdout.
- Locks litesearch 0.1.40, as `pyproject.toml` already required.

## 0.1.9
- `rows` hands `code_row` the hit, not the leg name; the federated repo and env legs work again.

## 0.1.8
- `kosha.refactor`: `move_plan`, `replace_plan`, `extract`, `inline`, `top_symbols`, `module_of`, built on the index
- `from kosha import *` exports `refactor`
- `extract` binds comprehension targets before the element; a loop variable is no longer lifted as a parameter
- `dyn_edges` walks the AST once
- Code, env and package stores are stamped with the encoder; another embedder cannot be mixed in on reopen
- `mv_skill_md` honours `dir=` for the `.claude` copy
- `rrf_all` fuses the two legs
- `update_pkg` drops the `parallel=` that reached nothing
- Needs litesearch 0.1.35

## 0.1.7
kosha code rows

## 0.1.6
page ranks can be small. bumping rounding error from 5 to 12 

## 0.1.5
fixes page rank

## 0.1.4

removing pyan3 and using ast-grep

**`static_edges` is `ast-grep`, and `pyan3` is gone.** `pyan3` was last released in 2021, needed two
monkey-patches in `graph.py` to run at all, and still crashed on `networkx` with a third fault. Call
edges now come from an `ast-grep` walk plus resolution in Python: enclosing scope, then the module's
imports, then a name defined exactly once in the corpus. Over 400 files it is 10x, 31.5s to 3.2s. It
also drops the synthetic nodes `pyan3` invented. The node table falls from 19,974 to 4,948, and every
one that goes was an artefact rather than a definition.

Names reached through an attribute do not resolve by short name any more, `self.m()` excepted. Binding
`x.get()` to whichever unrelated `get` the corpus happened to hold was producing edges like
`basics.basic_repr -> xml.FT.list`. Builtins and method names are excluded from the unique-name
fallback for the same reason. An import statement binds a name rather than using one, so it no longer
makes an edge.

A third of `pyan3`'s edges are not reproduced, and most of that gap is its own duplication. It copied
each base-class edge onto every method of the subclass. It pointed constructor calls at
`Class.__init__`. It emitted self-recursion. The replacements are one class-level edge, the class
itself, and no self-edge.

**The hand-written `_fast_edges` pass is retired.** The new extractor is 2.3x the "fast" AST path it
existed to be, and finds twice the edges. `mode='fast'` and `mode='full'` run the same extraction now. `mode='full'` still fans batches out over a process pool. The default runs inline,
because an incremental sync is a handful of files.

**Extraction fans out over processes.** `_static_batch` is module-level and picklable now. Measured on
400 files: 4 threads 0.85x against serial, 4 processes 3.25x. The old `threadpool=True` was slower
than not fanning out at all.

**PageRank on the incremental path was wrong, not stale.** `_centrality(nodes)` narrowed `_pagerank`
to the changed nodes, which left every other node contributing zero and divided by the size of the
subset. Over 200 of 59,999 nodes the scores came back 46x inflated with 0/20 top-20 overlap against
the whole graph. `rank_results` and the "blast radius" advice in the MCP tools read that number.
PageRank now always scores the whole graph, as a `np.bincount` CSR matvec (3.8x, no new dependency,
19/20 top-20 overlap with the old maths). Degrees refresh through one `INSERT ... ON CONFLICT`, and
the PageRank recompute is gated behind a 10% move in the edge count.

**Co-dispatch groups merge.** `_add_dyn` scanned existing groups and broke at the first hit, so a pair
bridging two groups left them apart: `X = [a, b]` with `Y = (b, c)` gave two groups, not one. It is a
union-find now.

`ast-grep-py` replaces `pyan3` in the dependencies.

## 0.1.3
graph edges bug fix

## 0.1.2
bug fix with lexical scoping

## 0.1.1
kosha fast path

## 0.1.0
kosha release with litesearch Index, reranking

## 0.0.38
pkg extraction bug fix

## 0.0.37
sync pkgs like rishi[all]

## 0.0.36
make all legs optional

## 0.0.35
bump

## 0.0.34
release

## 0.0.33
kosha parallel sync with busy_timeout and pkg_parallel (experimental)

## 0.0.31
bug fix with remove

## 0.0.30
bump litesearch to fix ann latency bugbug



## 0.0.29
skip folder re, skip file re, find stale files, graph sync optionalstale fixes

## 0.0.28
mcp server (`kosha-mcp`), mcp as a core dep
- new `kosha-mcp` console script — exposes the index over MCP (stdio, or `--http` for Streamable HTTP)
- 14 tools: `status`, `sync`, `context`, `repo_context`, `env_context`, `where_to_add`, `node_info`, `neighbors`, `short_path`, `public_api`, `top_nodes`, `api_paths`, `dep_stack`, `pkg_url`
- `mcp` promoted from optional extra to a core dependency


## 0.0.27
bump


## 0.0.26
hnsw ann


## 0.0.25
boosting + denoising


## 0.0.24
fixes cli bug



## 0.0.23
code graph is parallel



## 0.0.22
static embedder



## 0.0.21
cli fix



## 0.0.20
make skills succinct



## 0.0.19
files processing for mono repos



## 0.0.18
update_repo bug fix and skill to use daemon as a start



## 0.0.17
codegraph chunking



## 0.0.16
cross package link, performance , force_graph



## 0.0.15
remove fastprogress, early stop with index



## 0.0.14
code graph bug fix



## 0.0.13
bind + partial graph add + stale pkg fix



## 0.0.12
bump



## 0.0.11
emb_doc and query within kosha class



## 0.0.10
claude install, where_to_add , skill fix, status



## 0.0.9
skills and index



## 0.0.8
api_paths and dynamic paths



## 0.0.7
public_api, cross pkg api pathsand moreapi_paths



## 0.0.6
async and pkg name fix



## 0.0.5
pkgs and sync in sync



## 0.0.4
tqdm and prune pkgs



## 0.0.3
doc fix 



## 0.0.2
kosha release



## 0.0.1
kosha initial initial
