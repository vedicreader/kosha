# Decisions

This page lists the decisions that a maintainer must know. Each entry gives the decision, the reason, the date or version, and the place in the code.
The release notes are in [CHANGELOG.md](../CHANGELOG.md). The agent guide is `kosha/SKILL.md`, made by `nbs/05_skill.ipynb`.
The old split note with litesearch (`docs/consolidation.md`) is in the git history.

## The split with litesearch

- **litesearch owns retrieval. kosha owns code.** kosha keeps all that knows a function, a file path or a symbol. Code that works the same on a corpus of PDFs goes to litesearch, as an upstream patch and a new floor in `pyproject.toml`. kosha does not wrap or copy it.
  Why: one search engine for all the owner's apps, and easy upkeep. (2 Aug 2026; owner, 1 Nov 2026) `pyproject.toml` (`litesearch>=0.1.61`), `kosha/core.py` imports from `litesearch.utils`.
- **Only real MCP tools.** `anchor`, `similar`, `peers` and `code_clusters` were registered but never written. They are gone from `mcp.py` and `SKILL.md`. Add a tool only with its code and a test. `kosha/mcp.py`.

## Index and stores

- **Three stores in one Kosha.** The code store holds the repo, the package store holds the env packages, and `k.docs` is a litesearch `Index` for READMEs and other prose, split by heading. `Kosha.docs` in `kosha/core.py`.
- **A store is stamped with its encoder.** A store opened with another embedder fails. You cannot mix vectors. (0.1.8) `encoder_id` in `Kosha.__init__`.
- **`CODE_FORMAT` in `PRAGMA user_version`.** When the parse output changes, raise `CODE_FORMAT`. An older index then parses its files again one time and keeps its embeddings. Now 2 (stored imports). (0.1.12, 0.1.16) `CODE_FORMAT` in `kosha/core.py`.
- **JSON indexes on the metadata.** Each store has an index on `json_extract(metadata,'$.name')`, and the code and package stores have `idx_store_lang` on `$.lang`.
  Why: a name lookup went from 1.2 to 2.8 s down to 25 ms; a `lang:py` search from 105 ms to 10 ms. (0.1.12, 0.1.18) `LANG_INDEX` in `kosha/core.py`.
- **The packages come from the project.** kosha reads the pyproject of `Kosha.root` (`pyproject_deps`) and the project's own `.venv` (`env_path`), not the interpreter it runs in.
  Why: the uv tool and Leela's server run kosha from another folder. (0.1.13, 0.1.14) `kosha/core.py`.
- **`sys_wide=False` means "indexed at the installed version".** (0.1.21) `pkgs2consider` in `kosha/core.py`.
- **Parallel writes need a busy timeout.** `update_pkgs(parallel=True)` refuses to run without `Kosha(busy_timeout=...)`. litesearch commits in batches of 1,000 rows. (0.0.33, 0.1.17) `update_pkgs` in `kosha/core.py`.
- **Embedding can run later.** `process_env` (`kosha embed`) fills NULL embeddings in batches. Each batch commits with its HNSW update, so a stopped run resumes. (0.1.15) `kosha/core.py`.
- **Partial syncs touch only their part.** `update_repo(dir=...)` and `update_repo(files=...)` delete only the rows under that folder or of those files. A file that fails to parse is skipped. (0.1.11, 0.1.12, 0.1.16) `kosha/core.py`.

## Code graph

- **Call edges come from `ast-grep`, not `pyan3`.** The resolver uses the enclosing scope, then the module imports, then a name that is defined one time in the corpus. Builtins, method names and attribute calls (other than `self.m()`) do not resolve by short name.
  Why: `pyan3` needed monkey-patches and made false edges. `ast-grep` is 10 times faster (400 files: 31.5 s to 3.2 s). (0.1.4) `kosha/graph.py`.
- **Batches run in processes, not threads.** On 400 files, 4 threads gave 0.85x and 4 processes gave 3.25x. One batch runs in the same process, because a spawned pool cannot load a notebook function on Linux CI. (0.1.4, 0.1.11) `_static_batch` and `parallel(..., threadpool=False)` in `kosha/graph.py`.
- **PageRank always scores the whole graph.** It is a `np.bincount` matvec. It runs again only when the edge count moves by more than 10 %. Degrees refresh each sync.
  Why: a PageRank on only the changed nodes gave scores 46 times too high. (0.1.4) `_pagerank` and `_centrality(tol=0.1)` in `kosha/graph.py`.
- **Co-dispatch groups use union-find**, so a pair that joins two groups merges them. (0.1.4) `_uf_find` in `kosha/graph.py`.
- **A sync skips a file by its content hash**, not its mtime. A file that changes during a sync parses again next time. (0.1.16) `_hash_files` and `_stale` in `kosha/graph.py`.

## Ranking

- **`rank_results` reorders the RRF hits for code.** It boosts symbol and file-name matches, gives a small boost to files with many hits, and gives a penalty to tests and to repeated hits from one file. The graph's PageRank is not a ranking input.
  (Graph-aware reranking, 15 Jul 2026) `rank_results` in `kosha/graph.py`.
- **A package name in the query is a soft boost, not a filter.** `package:fastcore` or a bare package name multiplies the score of that package's hits. Other packages still show. (Jul 2026) `_boost_package` in `kosha/graph.py`.
- **`rerank=True` is opt-in.** It reorders the top hits with a flashrank cross-encoder. `kosha/core.py`, `kosha/graph.py`.

## Tests and release

- **Tests never write to the shared index.** Each notebook sets `XDG_DATA_HOME` to a temporary folder. (0.1.15) `nbs/00_core.ipynb`, `nbs/01_graph.ipynb`, `nbs/03_cli.ipynb`.
- **Output that is JSON stays clean.** `verbose=False` shows no progress bar, and `kosha sync --as-json` prints only JSON. (0.1.10, 0.1.16)
- **The build is hatchling.** Change `pyproject.toml`, not `MANIFEST.in`. `dev` is an extra, because nbdev's CI installs it. The local nbdev must match CI (`nbdev>=3.3.25`). (0.1.11)
