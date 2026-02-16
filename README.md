# ask-census

Natural-language queries for [CELLxGENE Census](https://chanzuckerberg.github.io/cellxgene-census/), powered by AI coding agents and ontology-aware term expansion.

## Quick Start

```bash
git clone https://github.com/Cellular-Semantics/ask-census.git
cd ask-census
./setup.sh          # creates .venv, installs deps, syncs configs, verifies OLS4
```

Then open the project in your AI coding agent and ask for what you need:

```
Get me female T cells in lung tissue
```

In Claude Code you can also use the `/cxg-query` skill shorthand:
```
/cxg-query female T cells in lung tissue
```

## Examples

Just describe what you want — the agent handles ontology lookups, term expansion, and code generation:

| You say | What happens |
|---|---|
| "female T cells in lung tissue" | Expands to 31 T cell subtypes across 13 lung structures → 301K cells |
| "expression of TP53 and BRCA1 in lung fibroblasts" | Resolves genes to Ensembl IDs, expands to 10 fibroblast subtypes → 199K cells x 2 genes |
| "how many macrophages are in kidney?" | "how many" triggers fast metadata-only mode (no expression matrix) |
| "highly variable genes in pancreatic beta cells" | "highly variable" triggers `get_highly_variable_genes()` mode |
| "run it: adult neurons from brain with Alzheimer's" | "run it" triggers direct execution with size estimate and auto-save |
| "snRNA-seq data from human heart" | Maps to `suspension_type == "nucleus"`, expands heart tissue terms |
| "10x 5' data from pediatric kidney" | Maps to all 10x 5' assay variants, enumerates child-age stages |

### Worked examples

Step-by-step walkthroughs showing the full agentic flow with real OLS4 lookups and Census cell counts:

- **[T cells in lung](examples/01_t_cells_in_lung.md)** — basic query, ontology expansion, pre-flight validation
- **[Gene expression in fibroblasts](examples/02_gene_expression_in_fibroblasts.md)** — gene resolution, var filtering, ambiguity handling
- **[Disease + development stage](examples/03_disease_and_development_stage.md)** — zero-results fallback loop, deprecated term detection
- **[snRNA-seq 10x pediatric kidney HVG](examples/04_snrnaseq_pediatric_kidney_hvg.md)** — assay filtering, suspension type, informal age terms, data availability

## Platform Support

| Platform | Status | Config |
|---|---|---|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Full support | `CLAUDE.md`, `.claude/skills/`, `.claude/agents/`, `.mcp.json` |
| [OpenAI Codex](https://openai.com/index/codex/) | Full support | `AGENTS.md`, `.codex/skills/`, `.codex/agents/`, `.codex/config.toml` |
| [GitHub Copilot](https://github.com/features/copilot) | Context only | `.github/copilot-instructions.md` |

Configs are synced automatically: `setup.sh` copies Claude Code skills and agents to `.codex/` and mirrors `CLAUDE.md` to `AGENTS.md`.

## How It Works

1. **You describe** the data you want in plain English
2. **The agent** parses your request into biological entities (cell types, tissues, diseases, genes, assays, stages)
3. **OLS4 MCP** resolves entities to ontology terms (CL, Uberon, MONDO, HsapDv/MmusDv)
4. **cxg-query-enhancer** expands terms to include all subtypes via Ubergraph, filtered to those present in Census
5. **gene_resolver** maps gene names to Ensembl IDs (with disambiguation for ambiguous names)
6. **cellxgene-census** retrieves the matching single-cell data

All queries automatically filter to `is_primary_data == True` to avoid duplicate cells across overlapping datasets.

## Features

- **Three API modes**: metadata exploration (`get_obs`), expression retrieval (`get_anndata`), and feature selection (`get_highly_variable_genes`) — automatically selected from intent keywords
- **Ontology expansion**: "T cell" automatically includes CD4+, CD8+, regulatory T cells, etc. (~31 subtypes); "lung" includes left lung, bronchus, lung epithelium, etc. (~13 structures)
- **Gene resolution**: gene symbols resolved to Ensembl IDs with automatic disambiguation (prefers protein_coding when ambiguous)
- **Assay filtering**: informal terms like "10x", "Smart-seq", "droplet-based" mapped to exact census labels from a cached lookup (~37 assays)
- **Suspension & tissue type**: filter by `suspension_type` (cell/nucleus) and `tissue_type` (tissue/organoid/cell culture)
- **Development stage handling**: exact ontology labels enforced, species-specific routing (HsapDv vs MmusDv), deprecated term detection, informal age terms enumerated
- **Pre-flight validation**: mandatory cell count before presenting results; zero-results trigger automatic relaxation loop
- **Size estimation**: download size estimate before large `get_anndata()` queries, with warnings for >500 MB
- **Code or execute**: generates reviewable code by default, or runs directly on request with auto-save to `outputs/`

## Project Structure

```
ask-census/
├── .claude/                    # Claude Code config (master for shared files)
│   ├── agents/ontology-term-lookup.md
│   └── skills/cxg-query/
│       ├── SKILL.md
│       └── references/         # grammar, templates, census field lookups
├── .codex/                     # OpenAI Codex config (synced by setup.sh)
├── .github/copilot-instructions.md
├── .mcp.json                   # OLS4 MCP server
├── src/
│   ├── gene_resolver.py        # Gene name → Ensembl ID resolution
│   └── refresh_census_fields.py
├── data/                       # Obsolete stage term lookups
├── tests/
├── examples/                   # Worked examples
├── planning/                   # Roadmap
├── outputs/                    # Query results (git-ignored)
├── setup.sh                    # One-command setup
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
