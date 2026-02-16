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

## How It Works

1. **You describe** the data you want in plain English
2. **The agent** parses your request into biological entities (cell types, tissues, diseases, genes, assays, stages)
3. **OLS4 MCP** resolves entities to ontology terms (CL, Uberon, MONDO, HsapDv/MmusDv)
4. **cxg-query-enhancer** expands terms to include all subtypes via Ubergraph, filtered to those present in Census
5. **gene_resolver** maps gene names to Ensembl IDs (with disambiguation for ambiguous names)
6. **cellxgene-census** retrieves the matching single-cell data

All queries automatically filter to `is_primary_data == True` to avoid duplicate cells across overlapping datasets.

## Platform Support

| Platform | Status | Config |
|---|---|---|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | Full support | `CLAUDE.md`, `.claude/skills/`, `.claude/agents/`, `.mcp.json` |
| [OpenAI Codex](https://openai.com/index/codex/) | Full support | `AGENTS.md`, `.codex/skills/`, `.codex/agents/`, `.codex/config.toml` |
| [GitHub Copilot](https://github.com/features/copilot) | Context only | `.github/copilot-instructions.md` |

Configs are synced automatically: `setup.sh` copies Claude Code skills and agents to `.codex/` and mirrors `CLAUDE.md` to `AGENTS.md`.

## Features

- **Three API modes**: metadata exploration (`get_obs`), expression retrieval (`get_anndata`), and feature selection (`get_highly_variable_genes`) — automatically selected from intent keywords
- **Ontology expansion**: "T cell" automatically includes CD4+, CD8+, regulatory T cells, etc. (~76 subtypes); "lung" includes left lung, bronchus, lung epithelium, etc. (~15 structures)
- **Gene resolution**: gene symbols resolved to Ensembl IDs with automatic disambiguation (prefers protein_coding when ambiguous)
- **Assay filtering**: informal terms like "10x", "Smart-seq", "droplet-based" mapped to exact census labels from a cached lookup (~37 assays)
- **Suspension & tissue type**: filter by `suspension_type` (cell/nucleus) and `tissue_type` (tissue/organoid/cell culture)
- **Development stage handling**: exact ontology labels enforced (e.g. `"adult stage"` not `"adult"`), species-specific routing (HsapDv vs MmusDv), deprecated term detection via static lookup
- **Pre-flight validation**: mandatory cell count before presenting results; zero-results trigger automatic relaxation loop
- **Size estimation**: download size estimate before large `get_anndata()` queries, with warnings for >500 MB
- **De-duplication**: filters to primary data by default, avoiding duplicate cells across overlapping datasets
- **Auto-save**: direct execution results saved to `outputs/` with descriptive filenames (`.h5ad` or `.parquet`)
- **Code or execute**: generates reviewable code by default, or runs directly on request
- **Formal grammar**: filter expressions follow a documented EBNF grammar with double-quote convention (handles labels containing apostrophes like `10x 3' v3`)

## Examples

Just describe what you want — the agent handles ontology lookups, term expansion, and code generation:

| You say | What happens |
|---|---|
| "female T cells in lung tissue" | Looks up T cell (CL) + lung (UBERON), expands to ~76 cell types and ~15 tissue terms |
| "expression of TP53 and BRCA1 in lung fibroblasts" | Resolves gene names to Ensembl IDs, builds both obs and var filters |
| "how many macrophages are in kidney?" | "how many" triggers metadata-only `get_obs()` mode — fast, no expression matrix |
| "highly variable genes in pancreatic beta cells" | "highly variable" triggers `get_highly_variable_genes()` mode |
| "run it: adult neurons from brain with Alzheimer's" | "run it" triggers direct execution with pre-flight size estimate and auto-save |
| "snRNA-seq data from human heart" | Maps to `suspension_type == "nucleus"`, expands heart tissue terms |
| "10x 5' data from pediatric kidney" | Maps to all `10x 5'` assay variants, enumerates child-age HsapDv stages |

### Worked examples

Step-by-step walkthroughs of the full agentic flow:

- **[T cells in lung](examples/01_t_cells_in_lung.md)** — basic query, ontology expansion, generated code
- **[Gene expression in fibroblasts](examples/02_gene_expression_in_fibroblasts.md)** — gene resolution, var filtering, ambiguity handling
- **[Disease + development stage](examples/03_disease_and_development_stage.md)** — multi-ontology, dev stage strategies, informal age terms


## Project Structure

```
ask-census/
├── .claude/                    # Claude Code config (master for shared files)
│   ├── agents/ontology-term-lookup.md  # Ontology lookup agent (OLS4 MCP)
│   └── skills/cxg-query/
│       ├── SKILL.md            # Main skill definition
│       └── references/
│           ├── grammar.md      # EBNF filter grammar + column reference
│           ├── templates.md    # Code templates for all 3 API modes
│           └── census_fields.json  # Cached assay/suspension/tissue lookups
├── .codex/                     # OpenAI Codex config (synced by setup.sh)
│   ├── agents/
│   ├── skills/
│   └── config.toml             # Codex MCP server config
├── .github/copilot-instructions.md  # GitHub Copilot context
├── .mcp.json                   # OLS4 MCP server (Claude Code + Codex)
├── src/
│   ├── gene_resolver.py        # Gene name → Ensembl ID resolution
│   └── refresh_census_fields.py  # Regenerate census_fields.json from live census
├── data/
│   ├── obsolete_hsapdv.tsv     # Static obsolete HsapDv terms (from Ubergraph)
│   ├── obsolete_mmusdv.tsv     # Static obsolete MmusDv terms
│   └── refresh_obsolete_stages.sh  # Regenerate obsolete term lookups
├── tests/test_gene_resolver.py
├── examples/                   # Worked examples (agentic session walkthroughs)
├── planning/                   # Roadmap and implementation plans
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
