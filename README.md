# Agentic CxG Query

Natural-language queries for [CELLxGENE Census](https://chanzuckerberg.github.io/cellxgene-census/), powered by AI coding agents and ontology-aware term expansion.

## Quick Start

```bash
git clone https://github.com/Cellular-Semantics/agentic-cxg-query.git
cd agentic-cxg-query
./setup.sh          # creates .venv, installs deps, verifies OLS4
```

Then open the project in your AI coding agent and start querying:

```
/cxg-query female T cells in lung tissue
```

## How It Works

1. **You describe** the data you want in plain English
2. **The agent** parses your request into biological entities (cell types, tissues, diseases, genes)
3. **OLS4 MCP** resolves entities to ontology terms (CL, Uberon, MONDO, HsapDv/MmusDv)
4. **cxg-query-enhancer** expands terms to include all subtypes via Ubergraph
5. **gene_resolver** maps gene names to Ensembl IDs (with disambiguation)
6. **cellxgene-census** retrieves the matching single-cell data

All queries automatically filter to `is_primary_data == True` to avoid duplicate cells across overlapping datasets.

## Platform Support

| Platform | Status | Config |
|---|---|---|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Full support | `CLAUDE.md`, `.claude/skills/`, `.claude/agents/` |
| [OpenAI Codex](https://openai.com/index/codex/) | Full support | `AGENTS.md`, `.codex/agents/`, `.codex/config.toml` |
| [GitHub Copilot](https://github.com/features/copilot) | Context only | `.github/copilot-instructions.md` |

## Features

- **Three API modes**: metadata exploration (`get_obs`), expression retrieval (`get_anndata`), and feature selection (`get_highly_variable_genes`)
- **Ontology expansion**: "T cell" automatically includes CD4+, CD8+, regulatory T cells, etc.
- **Gene resolution**: gene symbols resolved to Ensembl IDs with automatic disambiguation of ambiguous names
- **De-duplication**: filters to primary data by default, avoiding duplicate cells across overlapping datasets
- **Size estimation**: pre-flight cell count and download size estimate before large `get_anndata()` queries
- **Auto-save**: direct execution results saved to `outputs/` with descriptive filenames (`.h5ad` or `.parquet`)
- **Code or execute**: generates reviewable code by default, or runs directly on request

## Examples

```bash
# Metadata exploration (get_obs)
/cxg-query just metadata for T cells in skin

# Expression data with gene filtering (get_anndata)
/cxg-query expression of TP53 and BRCA1 in lung fibroblasts

# Highly variable genes (get_highly_variable_genes)
/cxg-query highly variable genes in pancreatic beta cells

# Complex multi-condition query
/cxg-query medium spiny neurons from adult human brain

# Direct execution
/cxg-query run it: female macrophages in kidney with diabetes
```

## Direct Python Usage

```python
import cellxgene_census
from cxg_query_enhancer import enhance
from gene_resolver import resolve_genes, build_var_value_filter

# Build and expand the obs filter
obs_filter = enhance(
    "cell_type in ['T cell'] and tissue in ['lung']",
    organism="homo_sapiens"
)

# Resolve genes to Ensembl IDs
matches = resolve_genes(["TP53", "BRCA1"], organism="homo_sapiens")
var_filter = build_var_value_filter(
    [eid for m in matches for eid in m.ensembl_ids]
)

# Fetch from census
with cellxgene_census.open_soma(census_version="latest") as census:
    adata = cellxgene_census.get_anndata(
        census,
        organism="Homo sapiens",
        obs_value_filter=obs_filter,
        var_value_filter=var_filter,
    )
print(f"{adata.shape[0]:,} cells x {adata.shape[1]:,} genes")
```

## Project Structure

```
agentic-cxg-query/
├── .claude/                    # Claude Code config (master for shared files)
│   ├── agents/ontology-term-lookup.md
│   └── skills/cxg-query/SKILL.md
├── .codex/                     # OpenAI Codex config (synced by setup.sh)
│   ├── agents/ontology-term-lookup.md
│   └── config.toml
├── .github/copilot-instructions.md
├── .mcp.json                   # OLS4 MCP server
├── src/gene_resolver.py        # Gene name → Ensembl ID resolution
├── tests/test_gene_resolver.py
├── planning/ROADMAP.md         # Feature roadmap
├── outputs/                    # Query results (git-ignored)
├── example_query.py            # Usage examples
├── setup.sh                    # One-command setup (also syncs agent configs)
├── Makefile                    # setup, test, check-mcp, clean
└── pyproject.toml
```

## Contributing

1. Fork this repo (or use it as a template)
2. `./setup.sh`
3. Make your changes
4. `make test`

## References

- [CELLxGENE Census](https://chanzuckerberg.github.io/cellxgene-census/)
- [cxg-query-enhancer](https://github.com/Cellular-Semantics/cxg-query-enhancer)
- [OLS4 (Ontology Lookup Service)](https://www.ebi.ac.uk/ols4/)
- [Ubergraph](https://github.com/INCATools/ubergraph)

## License

MIT
