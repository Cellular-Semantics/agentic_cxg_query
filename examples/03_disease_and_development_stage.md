# Example: Kidney macrophages with diabetes in adults

A worked example combining disease ontology, development stage, and a multi-ontology expansion.

## The prompt

> Macrophages from adult kidney with diabetes mellitus

---

## Step 1: Parse the request

| Entity | Value | Category |
|---|---|---|
| Cell type | macrophage | `cell_type` (CL) |
| Tissue | kidney | `tissue` (UBERON) |
| Disease | diabetes mellitus | `disease` (MONDO) |
| Dev stage | adult | `development_stage` (HsapDv) |
| Organism | human (default) | — |

No genes, no sex filter. Default → `get_anndata()`.

---

## Step 2: Ontology lookups

Four lookups run in parallel via the ontology-term-lookup agent:

**macrophage** → Cell Ontology
```
- Matched Term: macrophage
- Ontology ID: CL:0000235
```

**kidney** → Uberon
```
- Matched Term: kidney
- Ontology ID: UBERON:0002113
```

**diabetes mellitus** → MONDO
```
- Matched Term: diabetes mellitus
- Ontology ID: MONDO:0005015
```

**adult** → HsapDv

The user said "adult", but that's not an exact ontology label. The agent searches OLS4 for "adult stage" in HsapDv and finds:
```
- Matched Term: adult stage
- Ontology ID: HsapDv:0000258
- Definition: sexually mature human (starts at 15 years)
```

The exact label `"adult stage"` is critical — `enhance()` matches on exact `rdfs:label` values. Using `"adult"` or `"human adult stage"` would silently fail to expand.

---

## Step 3: Construct the filter

```python
"is_primary_data == True and cell_type in ['macrophage'] and tissue in ['kidney'] and disease in ['diabetes mellitus'] and development_stage in ['adult stage']"
```

All four categories use their exact OLS4 label. `enhance()` expands labels and IDs equally well — the key is using the **exact** label, not a paraphrase.

---

## Step 4: What enhance() expands

For each category, `enhance()` first queries Ubergraph for all subclass + `part_of` descendants, then filters to only terms present in the Census dataset (see [Example 01](01_t_cells_in_lung.md#step-4-ontology-expansion) for details on this two-stage process).

**macrophage** (CL:0000235) → ~25 terms:
> macrophage, alveolar macrophage, Kupffer cell, microglial cell,
> tissue-resident macrophage, inflammatory macrophage,
> peritoneal macrophage, ...

**kidney** (UBERON:0002113) → ~30 terms:
> kidney, renal cortex, renal medulla, nephron, glomerulus,
> proximal tubule, loop of Henle, collecting duct, ...

**diabetes mellitus** (MONDO:0005015) → ~15 terms:
> diabetes mellitus, type 1 diabetes mellitus, type 2 diabetes mellitus,
> gestational diabetes, maturity-onset diabetes of the young, ...

**adult stage** (HsapDv:0000258) → ~103 terms:
> adult stage, young adult stage, middle aged stage, late adult stage,
> early adulthood stage, prime adult stage, 20-year-old stage,
> 30-year-old stage, ... (individual year stages from 15y through 111y)

---

## Step 5: Generated code

```python
import cellxgene_census
from cxg_query_enhancer import enhance

obs_filter = enhance(
    "is_primary_data == True and "
    "cell_type in ['macrophage'] and "
    "tissue in ['kidney'] and "
    "disease in ['diabetes mellitus'] and "
    "development_stage in ['adult stage']",
    organism="homo_sapiens"
)

with cellxgene_census.open_soma(census_version="latest") as census:
    adata = cellxgene_census.get_anndata(
        census,
        organism="Homo sapiens",
        obs_value_filter=obs_filter,
        obs_column_names=[
            "cell_type", "tissue", "disease",
            "development_stage", "sex", "dataset_id"
        ]
    )

print(f"Retrieved {adata.shape[0]:,} cells x {adata.shape[1]:,} genes")
print(adata.obs["cell_type"].value_counts().head(10))
print(adata.obs["disease"].value_counts())
```

**Agent summary:**
> Resolved terms:
> - Cell type: macrophage (CL:0000235) — expands to ~25 subtypes
> - Tissue: kidney (UBERON:0002113) — expands to ~30 structures
> - Disease: diabetes mellitus (MONDO:0005015) — expands to ~15 subtypes
> - Dev stage: adult stage (HsapDv:0000258) — expands to ~103 terms
>
> Note: Filtering to `is_primary_data == True` to exclude duplicate cells.
>
> Warning: This is a broad query (all genes, multiple expanded categories).
> Consider running `get_obs()` first to estimate cell count, or add gene
> filters to reduce download size.

---

## Tips for development stage queries

Development stages require care because the user's phrasing rarely matches the exact ontology label:

1. **Always look up via OLS4** — `"adult"` is not a label; `"adult stage"` is. `enhance()` uses exact `rdfs:label` matching, so a wrong label silently fails (no expansion, no error).
2. **Labels vary by organism** — human uses HsapDv, mouse uses MmusDv. The OLS4 lookup resolves this.
3. **Informal terms** like "pediatric", "juvenile", "child" don't map to a single ontology term. For these, the agent enumerates year-based stages:
   > "pediatric" → `'2-year-old stage'`, `'3-year-old stage'`, ..., `'14-year-old stage'`

This is where the agentic approach adds value — the agent bridges informal language and formal ontology labels via OLS4 lookup, ensuring `enhance()` always gets the exact label it needs.
