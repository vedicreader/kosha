# Release notes

<!-- do not remove -->

## 0.1.0

Semble-inspired upgrade (speed, ranking, integrations) — kosha keeps its call-graph moat:

- **`fast` profile is the new default**: static `potion-code-16M` embeddings (Model2Vec) —
  millisecond CPU indexing/queries, no transformer inference. The previous CodeRankEmbed ONNX
  embedder is now `KOSHA_PROFILE=accurate`. Existing indexes warn on model mismatch;
  re-embed with `k.sync(force=True)`.
- **Code-aware rerank after RRF** (`kosha.rank`): definition-of-symbol boost, identifier stem
  overlap, pagerank, public_api, same-file coherence, noise penalty (tests/examples/shims),
  docstring presence. Adaptive: symbol-like queries get full graph priors, natural-language
  queries keep RRF ordering mostly intact. Tunable via `rerank(weights=...)`; disable with
  `context(rerank=False)`.
- **Identifier subtoken matching**: camelCase/snake_case stems are indexed in chunk metadata
  and symbol tokens in queries are expanded (`parseConfig` ⇄ `parse_config`).
- **`find_related(path, line)`**: chunks semantically similar to the code at a location, plus
  its call-graph neighborhood (CLI: `kosha find-related`, also an MCP tool).
- **MCP server**: `kosha mcp` (stdio, zero deps). `kosha install` now also writes `.mcp.json`
  (Claude Code) and `.cursor/mcp.json` (Cursor), with hints for Codex/OpenCode.
- **Auto-sync**: `context()` incrementally re-indexes changed repo files first (throttled,
  `KOSHA_AUTOSYNC=0` to disable).
- **`.gitignore` / `.koshaignore` respected** at index time (repo store and call graph).
- **Token-savings telemetry**: `kosha savings` reports tokens saved vs reading matched files
  in full (disable logging with `KOSHA_SAVINGS=0`).
- **Eval harness** (`kosha.bench`, CLI `kosha bench [--compare]`): self-retrieval NDCG@10 /
  Recall@k / MRR for A/B-ing rerank, profiles, and chunking changes.
- `Kosha(profile=..., db_dir=...)` for profile selection and index isolation.

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


