"""Retrieval evaluation harness for kosha's repo code search.

Measures recall@k, MRR and query latency for the current litesearch vector
pipeline (a SIMD flat-scan via the usearch SQLite extension -- not HNSW), so
the HNSW-vs-flat-scan and reranker decisions can be made on data instead of
guesswork.

It indexes kosha's own source (repo-only, deterministic, no package
downloads), runs every query in `eval/queries.py`, scores results against the
gold targets, prints a summary and writes `eval/results.json`.

Usage:
    python eval/bench.py            # incremental index, then evaluate
    python eval/bench.py --fresh    # rebuild the code index from scratch
    python eval/bench.py --verbose  # also print per-query ranks

The retriever is pluggable (`retrieve_fn` in `evaluate`): later experiments
(a usearch HNSW index, a rerank stage) plug in here and reuse the scoring and
the results.json baseline.
"""
import os, sys, json, time, argparse, statistics
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KMAX = 20


def build_index(fresh=False):
    "Index kosha's own source package into .kosha/code.db and return the Kosha instance."
    if fresh:
        db = REPO / '.kosha' / 'code.db'
        if db.exists(): db.unlink()
    from kosha.core import Kosha
    k = Kosha(dir=REPO)
    try: probe = k.emb_query("probe")
    except Exception: probe = None
    if probe is None or getattr(probe, 'size', 1) == 0:
        sys.exit("CodeRankEmbed embedder unavailable -- this harness needs the ONNX "
                 "model. Run where huggingface.co is reachable, or with the model "
                 "cached locally (kosha itself requires it to function).")
    # Index just the kosha/ package: the eval corpus is kosha's own source,
    # not the eval/ harness files.
    k.update_repo(REPO / 'kosha', embed=True, verbose=False)
    return k


def corpus_stats(k):
    "Index-level facts that bear on the HNSW decision: vector count, dim, db size."
    name = k.code_st.name
    try: n = k.codedb.q(f'select count(*) as n from {name}')[0]['n']
    except Exception: n = len(list(k.code_st()))
    emb = k.emb_query("probe query")
    dim = int(getattr(emb, 'shape', [len(emb)])[-1])
    dtype = str(getattr(emb, 'dtype', 'unknown'))
    db = Path(k.cp)
    from kosha.core import model
    return dict(chunks=n, dim=dim, dtype=dtype,
                db_mb=round(db.stat().st_size / 1e6, 2) if db.exists() else 0.0,
                model=model['model'])


def _relpath(p):
    p = str(p or '')
    try: rp = os.path.relpath(p, REPO)
    except ValueError: rp = p
    return rp.replace(os.sep, '/')


def _hit(result, gold):
    "True if a search result matches a gold target on both path and symbol."
    if _relpath(result.get('path', '')) != gold['path']: return False
    md = result.get('metadata') or {}
    modtail = (md.get('mod_name') or '').split('.')[-1]
    return gold['symbol'] in {md.get('name'), modtail}


def _rank_of_gold(results, golds):
    "1-based rank of the first result matching any gold target, or None."
    for i, r in enumerate(results, 1):
        if any(_hit(r, g) for g in golds): return i
    return None


def evaluate(k, queries, retrieve_fn=None, kmax=KMAX):
    "Run every query, return per-query rows (rank, latency)."
    from kosha.core import parseq
    retrieve_fn = retrieve_fn or (lambda q: list(k.repo_context(q, limit=kmax)))
    k.repo_context("warmup probe", limit=kmax)          # warm embedder + onnx session
    rows = []
    for e in queries:
        q, golds = e['q'], e['gold']
        bare, _ = parseq(q)
        t0 = time.perf_counter(); k.emb_query(bare); t_emb = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter(); res = retrieve_fn(q); t_search = (time.perf_counter() - t0) * 1000
        rows.append(dict(q=q, rank=_rank_of_gold(res, golds), n_results=len(res),
                          t_search_ms=round(t_search, 2), t_emb_ms=round(t_emb, 2)))
    return rows


def _pctl(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))], 2) if xs else 0.0


def metrics(rows, ks=(1, 5, 10, 20)):
    n = len(rows) or 1
    recall = {f'@{k}': round(sum(1 for r in rows if r['rank'] and r['rank'] <= k) / n, 3) for k in ks}
    mrr = round(sum(1.0 / r['rank'] for r in rows if r['rank']) / n, 3)
    search = [r['t_search_ms'] for r in rows]
    emb = [r['t_emb_ms'] for r in rows]
    return dict(queries=len(rows), recall=recall, mrr=mrr,
                search_ms={'p50': _pctl(search, .5), 'p95': _pctl(search, .95)},
                emb_ms={'p50': _pctl(emb, .5), 'p95': _pctl(emb, .95)})


def report(stats, m, rows, verbose=False):
    print('\n=== kosha retrieval eval ===')
    print(f"corpus : {stats['chunks']} chunks | dim {stats['dim']} ({stats['dtype']}) "
          f"| code.db {stats['db_mb']} MB")
    print(f"model  : {stats['model']}")
    print(f"queries: {m['queries']}\n")
    for k, v in m['recall'].items(): print(f"  recall{k:<5} {v:.3f}")
    print(f"  MRR@20     {m['mrr']:.3f}\n")
    print("latency (warm, ms):")
    print(f"  repo_context  p50 {m['search_ms']['p50']:>7}  p95 {m['search_ms']['p95']:>7}")
    print(f"  emb_query     p50 {m['emb_ms']['p50']:>7}  p95 {m['emb_ms']['p95']:>7}")
    print("  (SIMD vector-scan cost ~= repo_context - emb_query)\n")
    misses = [r for r in rows if not r['rank'] or r['rank'] > 10]
    if misses:
        print(f"weak queries (no hit in top-10) -- {len(misses)}:")
        for r in misses: print(f"  rank {str(r['rank'] or 'MISS'):>4}  {r['q']}")
    if verbose:
        print("\nper-query ranks:")
        for r in rows: print(f"  rank {str(r['rank'] or 'MISS'):>4}  {r['q']}")
    print()


def main():
    ap = argparse.ArgumentParser(description="kosha retrieval eval harness")
    ap.add_argument('--fresh', action='store_true', help="rebuild the code index from scratch")
    ap.add_argument('--kmax', type=int, default=KMAX, help="top-k to retrieve (default 20)")
    ap.add_argument('--verbose', action='store_true', help="print every query's rank")
    ap.add_argument('--json', default=str(Path(__file__).parent / 'results.json'),
                    help="path for the JSON results dump")
    args = ap.parse_args()

    sys.path.insert(0, str(REPO))
    from queries import QUERIES  # eval/ is on sys.path as the script's own dir

    k = build_index(fresh=args.fresh)
    stats = corpus_stats(k)
    rows = evaluate(k, QUERIES, kmax=args.kmax)
    m = metrics(rows)
    report(stats, m, rows, verbose=args.verbose)
    Path(args.json).write_text(json.dumps(dict(corpus=stats, metrics=m, queries=rows), indent=2))
    print(f"wrote {args.json}")


if __name__ == '__main__':
    main()
