# kosha's part in the search consolidation

Full review and roadmap: [`litesearch/docs/consolidation.md`](https://github.com/Karthik777/litesearch/blob/main/docs/consolidation.md).

The split: litesearch owns retrieval. kosha owns everything that mentions a function, a file
path or a symbol. Code in kosha that would work the same on a corpus of PDFs belongs in
litesearch.

## Done

The proposed queries `anchor`, `similar`, `peers` and `code_clusters` are not implemented. They were
specified here and registered as MCP tools, but `Kosha` never implemented them. The tools raised
`AttributeError` on call. They are removed from `mcp.py` and `SKILL.md`. Retrieval consolidation continues below.

## Next

1. **Code trees** (`kosha.tree`). `litesearch.tree` builds a document tree from headings; code's
   tree is `package > module > class > function`. kosha already holds every piece of it
   (`mod_name`, `lineno`, `type`). When kosha writes nodes from the AST into the same `nodes` schema,
   `db.toc('litesearch')` prints a package outline, `db.read()` returns a whole class, and
   `db.sections()` groups code hits by module.
2. **Split `rank_results`.** Three rules are generic: the score increase for files with several matching chunks, the score reduction for repeated results from one file, and the result-selection loop. Move them to litesearch. Symbol-query detection, identifier stem
   boosts, test and compatibility path penalties, and the score increase for named packages stay here.
3. **Better cluster labels for code.** c-TF-IDF on code names clusters after unique identifiers
   (`integrate_4, integrate_6, ...`) because IDF rewards unique identifiers. Stripping numeric
   suffixes and preferring the shared stem needs a tokeniser argument and no new algorithm.
