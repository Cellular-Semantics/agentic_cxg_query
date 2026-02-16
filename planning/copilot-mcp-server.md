# Copilot Support via MCP Server

## Goal

Expose cxg-query functionality as an MCP server so VS Code Copilot (agent mode) can use the same tools that Claude Code uses today via skills/agents.

## Why MCP?

- **Reuses existing Python code** — no TypeScript needed
- **Works with Claude Code too** — one server, two clients (replace current skill-based approach if desired)
- **OLS4 is already an MCP server** — Copilot can call it directly for ontology lookups
- **Low maintenance** — no VS Code extension packaging/publishing

## Architecture

```
User (Copilot chat, agent mode)
  │
  ├── cxg-query MCP server (stdio, Python)
  │     ├── tool: enhance_query
  │     ├── tool: resolve_genes
  │     ├── tool: count_cells
  │     └── tool: get_anndata
  │
  └── OLS4 MCP server (HTTP, already exists)
        └── tool: search, fetch, searchClasses, ...
```

Copilot reads `.github/copilot-instructions.md` for domain knowledge (how to parse queries, which ontologies to use, the enhance() workflow) and `.vscode/mcp.json` for tool discovery.

## Implementation Plan

### 1. Create MCP server (`src/mcp_server.py`)

Use the `mcp` Python SDK with `FastMCP`.

**Tools to expose:**

| Tool | Parameters | Returns | Wraps |
|------|-----------|---------|-------|
| `enhance_query` | `query: str`, `organism: str` | Expanded filter string | `cxg_query_enhancer.enhance()` |
| `resolve_genes` | `genes: list[str]`, `organism: str` | List of `{symbol, ensembl_ids, is_ambiguous}` | `gene_resolver.resolve_genes()` |
| `count_cells` | `obs_filter: str`, `organism: str`, `columns: list[str]` | Cell count + value_counts per column | `cellxgene_census.get_obs()` |
| `get_anndata` | `obs_filter: str`, `organism: str`, `var_filter: str?`, `genes: list[str]?` | Path to saved `.h5ad` file | `cellxgene_census.get_anndata()` + auto-save |

Skeleton:

```python
from mcp.server.fastmcp import FastMCP
from cxg_query_enhancer import enhance
from gene_resolver import resolve_genes, build_var_value_filter
import cellxgene_census

mcp = FastMCP("cxg-query")

@mcp.tool()
def enhance_query(query: str, organism: str = "homo_sapiens") -> str:
    """Expand a CELLxGENE census filter string via ontology closure.

    Terms like 'T cell' are expanded to include all subtypes (CD4+, CD8+, etc.)
    and filtered to those present in the census.
    """
    return enhance(query, organism=organism)

@mcp.tool()
def resolve_genes_tool(genes: list[str], organism: str = "homo_sapiens") -> list[dict]:
    """Resolve gene symbols to Ensembl IDs for census var filtering."""
    matches = resolve_genes(genes, organism=organism)
    return [
        {"symbol": m.symbol, "ensembl_ids": m.ensembl_ids, "is_ambiguous": m.is_ambiguous}
        for m in matches
    ]

@mcp.tool()
def count_cells(obs_filter: str, organism: str = "Homo sapiens",
                columns: list[str] | None = None) -> dict:
    """Run a pre-flight cell count for a filter. Returns total count and
    value_counts for requested columns (zero-count categories excluded)."""
    with cellxgene_census.open_soma(census_version="latest") as census:
        obs_df = cellxgene_census.get_obs(
            census, organism=organism,
            value_filter=obs_filter,
            column_names=columns or ["cell_type", "tissue", "disease"]
        )
    result = {"total_cells": len(obs_df)}
    for col in obs_df.columns:
        counts = obs_df[col].value_counts()
        counts = counts[counts > 0]
        result[col] = counts.to_dict()
    return result

@mcp.tool()
def get_anndata(obs_filter: str, organism: str = "Homo sapiens",
                var_filter: str | None = None) -> str:
    """Fetch expression data from CELLxGENE census. Returns path to saved .h5ad file."""
    with cellxgene_census.open_soma(census_version="latest") as census:
        adata = cellxgene_census.get_anndata(
            census, organism=organism,
            obs_value_filter=obs_filter,
            var_value_filter=var_filter
        )
    path = f"outputs/query_result_{len(adata)}_cells.h5ad"
    adata.write_h5ad(path)
    return f"Saved {len(adata)} cells to {path}"

if __name__ == "__main__":
    mcp.run()
```

### 2. Add VS Code MCP config (`.vscode/mcp.json`)

```json
{
  "servers": {
    "cxg-query": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["src/mcp_server.py"]
    },
    "ols4": {
      "type": "http",
      "url": "http://www.ebi.ac.uk/ols4/api/mcp"
    }
  }
}
```

### 3. Update `.github/copilot-instructions.md`

Add domain knowledge that mirrors `SKILL.md`:

- How to parse natural language into biological entities
- Which ontologies map to which columns (CL → cell_type, UBERON → tissue, etc.)
- The enhance() workflow: lookup term via OLS4 → use exact label → pass to `enhance_query` tool
- Always include `is_primary_data == True`
- Development stage gotchas (exact labels, organism-specific ontologies)
- Zero-results fallback strategy

### 4. Add `mcp` dependency to `pyproject.toml`

```toml
dependencies = [
    "cxg-query-enhancer",
    "cellxgene-census",
    "mcp",
]
```

### 5. Update `setup.sh`

- Install the `mcp` dependency
- Validate MCP server starts correctly (quick smoke test)

### 6. Update README platform table

Change Copilot status from "Context only" to "Full support (MCP)" and add config column entry.

## Trade-offs vs Claude Code skill

| Aspect | Claude Code (skill) | Copilot (MCP) |
|--------|-------------------|---------------|
| Slash command | `/cxg-query` | Natural language in agent mode |
| Orchestration | Skill + subagent, tightly controlled | Copilot decides tool order, guided by instructions |
| Ontology lookup | Dedicated `ontology-term-lookup` subagent | Copilot calls OLS4 MCP directly |
| Dev stage labels | Skill warns about exact labels | Instructions warn, but less enforceable |
| Execution control | Skill runs validation loop | Copilot may need explicit prompting |

## Future: Unify Claude Code to also use MCP

Once the MCP server exists, Claude Code could also use it (via `.mcp.json`) instead of relying on the skill to inline Python. This would give a single source of truth for tool logic. The skill would become a thin orchestration layer that calls MCP tools.
