# Example: Female T cells in lung tissue

A walkthrough of the full agentic query flow — from natural language to downloaded data.

## The prompt

> Get me female T cells in lung tissue

This works identically across platforms:

| Platform | How to invoke |
|---|---|
| Claude Code | `/cxg-query female T cells in lung tissue` |
| Codex | "Get me female T cells in lung tissue" (the agent reads AGENTS.md) |
| Copilot | "Get me female T cells in lung tissue" (reads copilot-instructions.md) |

---

## Step 1: Parse the request

The agent identifies:

| Entity | Value | Category |
|---|---|---|
| Sex | female | `sex` |
| Cell type | T cell | `cell_type` (CL) |
| Tissue | lung | `tissue` (UBERON) |
| Organism | human (default) | — |

No genes mentioned, no disease, no development stage.
Intent: no special keywords → defaults to `get_anndata()`.

---

## Step 2: Ontology lookup (OLS4 MCP)

The agent queries OLS4 to confirm the terms exist and get their IDs:

**T cell** → Cell Ontology
```
Best Match Found:
- Matched Term: T cell
- Ontology ID: CL:0000084
- Match Type: exact label
- Confidence: High
```

**lung** → Uberon
```
Best Match Found:
- Matched Term: lung
- Ontology ID: UBERON:0002048
- Match Type: exact label
- Confidence: High
```

These are straightforward lookups. For harder cases (e.g. "MSN" could mean medium spiny neuron or the gene MSN), the agent would disambiguate.

---

## Step 3: Construct the filter

The agent builds:

```python
"is_primary_data == True and sex == 'female' and cell_type in ['T cell'] and tissue in ['lung']"
```

Key decisions:
- `is_primary_data == True` added automatically (de-duplication)
- Labels used, not IDs — `enhance()` will expand them
- `in [...]` syntax even for single values — consistent pattern

---

## Step 4: Ontology expansion

`enhance()` expands each term in two stages:

**Stage A — Ontology closure (Ubergraph SPARQL)**: For each label, query Ubergraph for all subclasses and `part_of` descendants. This is a pure ontology operation — it returns every term in the hierarchy below your input.

**Stage B — Census filtering**: The raw ontology expansion is then intersected with terms that actually appear in the CELLxGENE Census dataset. This removes terms that are ontologically valid but have no cells annotated with them in Census. For example, Uberon might define dozens of lung sub-structures, but only those that curators have actually used to annotate cells will appear in the final filter.

**T cell** (CL:0000084):
- Ubergraph returns ~150+ CL descendants (every T cell subtype in the ontology)
- Census filtering narrows to ~76 terms (only those with annotated cells)
> T cell, CD4-positive alpha-beta T cell, CD8-positive alpha-beta T cell,
> regulatory T cell, gamma-delta T cell, natural killer T cell,
> mucosal associated invariant T cell, ...

**lung** (UBERON:0002048):
- Ubergraph returns many Uberon parts and substructures
- Census filtering narrows to ~15 terms
> lung, left lung, right lung, lung epithelium, bronchus,
> upper lobe of left lung, lower lobe of right lung, ...

The enhanced filter is much longer but captures the full biological scope — and every term in it is guaranteed to match cells in Census.

---

## Step 5: Generated code

The agent presents:

```python
import cellxgene_census
from cxg_query_enhancer import enhance

obs_filter = enhance(
    "is_primary_data == True and sex == 'female' and cell_type in ['T cell'] and tissue in ['lung']",
    organism="homo_sapiens"
)

with cellxgene_census.open_soma(census_version="latest") as census:
    adata = cellxgene_census.get_anndata(
        census,
        organism="Homo sapiens",
        obs_value_filter=obs_filter,
        obs_column_names=[
            "cell_type", "tissue", "disease",
            "development_stage", "sex"
        ]
    )

print(f"Retrieved {adata.shape[0]:,} cells x {adata.shape[1]:,} genes")
print(adata.obs.head())
```

**Summary provided by agent:**
> Resolved terms:
> - Cell type: T cell (CL:0000084)
> - Tissue: lung (UBERON:0002048)
>
> Note: Filtering to `is_primary_data == True` to exclude duplicate cells across overlapping datasets.
>
> Without `enhance()`: ~71,000 cells (exact label match only)
> With `enhance()`: ~700,000 cells (includes all T cell subtypes in all lung structures)

---

## Step 6: Direct execution (optional)

If you said "run it" or "execute", the agent would:

1. **Pre-flight estimate** — run a quick `get_obs()` count:
   ```
   Estimated: 712,345 cells x 60,664 genes
   Estimated download size: ~3,200 MB (sparse), up to ~16,000 MB (dense)
   ```
2. **Warn** — this is a large query (>500 MB sparse), suggest adding gene filters
3. **Proceed on confirmation** — fetch and auto-save:
   ```
   Saved to outputs/female_Tcell_lung_20250213_143022.h5ad
   ```

---

## What if I wanted just metadata?

> /cxg-query how many female T cells are in lung tissue?

The "how many" keyword triggers `get_obs()` mode instead:

```python
with cellxgene_census.open_soma(census_version="latest") as census:
    obs_df = cellxgene_census.get_obs(
        census,
        organism="Homo sapiens",
        value_filter=obs_filter,  # note: value_filter, not obs_value_filter
        column_names=["cell_type", "tissue", "sex", "dataset_id"]
    )
print(f"Found {len(obs_df):,} cells")
```

This returns a DataFrame of cell metadata — fast, lightweight, no expression matrix.
