# Copilot Instructions — Agentic CxG Query

## What this project does

This is an agentic wrapper for generating **CELLxGENE census** queries from natural language.
It combines:

- **cxg-query-enhancer** — ontology-aware query expansion (SPARQL/Ubergraph)
- **gene_resolver** (local, `src/gene_resolver.py`) — gene name to Ensembl ID resolution
- **OLS4 MCP** — live ontology lookups (Cell Ontology, Uberon, MONDO, HsapDv, MmusDv)

## Key libraries

| Library | Purpose |
|---|---|
| `cxg-query-enhancer` | `enhance(query, organism=)` expands ontology terms in filter strings |
| `cellxgene-census` | `get_anndata()`, `get_obs()`, `get_highly_variable_genes()` |
| `gene_resolver` | `resolve_genes()`, `build_var_value_filter()` |

## Query filter syntax

Filters are Python expressions for cellxgene_census:

```python
"sex == 'female' and cell_type in ['T cell'] and tissue in ['lung']"
```

Supported columns: `cell_type`, `tissue`, `disease`, `development_stage`, `sex`,
and their `*_ontology_term_id` counterparts.

## Ontology mapping

| Category | Ontology | Column |
|---|---|---|
| Cell type | CL | `cell_type` |
| Tissue | UBERON | `tissue` |
| Disease | MONDO | `disease` |
| Dev stage | HsapDv / MmusDv | `development_stage` |

## Project layout

- `src/gene_resolver.py` — gene name resolution module
- `.claude/skills/cxg-query/SKILL.md` — Claude Code skill definition
- `.claude/agents/ontology-term-lookup.md` — ontology lookup agent
- `example_query.py` — usage examples
