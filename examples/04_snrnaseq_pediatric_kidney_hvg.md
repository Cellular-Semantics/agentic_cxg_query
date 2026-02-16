# Example: Highly variable genes in snRNA-seq 10x pediatric kidney

A worked example showing assay filtering, suspension type, informal age term enumeration, HVG mode, and data availability limitations.

## The prompt

> Highly variable genes in snRNA-seq 10x data from pediatric kidney

---

## Step 1: Parse the request

| Entity | Value | Category |
|---|---|---|
| Tissue | kidney | `tissue` (UBERON) |
| Assay | 10x (all variants) | `assay` (agent-expanded) |
| Suspension type | nucleus (snRNA-seq) | `suspension_type` |
| Dev stage | pediatric (informal) | `development_stage` (HsapDv) |
| Organism | human (implied by "pediatric") | — |

Keywords "highly variable genes" → `get_highly_variable_genes()` mode.

**Organism confirmation**: The agent detects a development stage ("pediatric") without an explicit organism. Since "pediatric" is a human-centric term, the agent asks:

> A development stage was mentioned but no organism was specified.
> "Pediatric" typically refers to human children. Should I use **Homo sapiens** (HsapDv)?

User confirms human.

---

## Step 2: Ontology lookup

**kidney** → Uberon
```
Best Match Found:
- Input Text: kidney
- Matched Term: kidney
- Ontology ID: UBERON:0002113
- Match Type: Exact label match
- Definition: A paired organ of the urinary tract that produces urine and maintains
  bodily fluid homeostasis, blood pressure, pH levels, red blood cell production
  and skeleton mineralization.
- Confidence: High
```

---

## Step 3: Assay and suspension type resolution

These are **not** ontology lookups — the agent uses latent knowledge and the cached `census_fields.json` to map informal terms to exact census labels.

**"snRNA-seq"** → The agent maps this to `suspension_type == "nucleus"` rather than filtering by assay name. Single-nucleus RNA-seq is defined by the suspension type (nucleus vs cell), not the sequencing platform.

**"10x"** → The agent reads `references/census_fields.json` and finds all 10x variants:

```
10x assays in census (9 variants):
  10x 3' v3                          63,030,361 cells
  10x 3' v2                          17,478,337 cells
  10x 5' v2                           5,601,285 cells
  10x 5' v1                           4,824,442 cells
  10x multiome                        3,687,890 cells
  10x 5' transcription profiling      1,802,991 cells
  10x 3' transcription profiling        658,954 cells
  10x gene expression flex              101,856 cells
  10x 3' v1                             95,377 cells
```

The agent constructs `assay in ["10x 3' v3", "10x 3' v2", ...]` with all 9 variants. Note the double-quote convention — labels like `10x 3' v3` contain apostrophes that would break single-quoted strings.

---

## Step 4: Development stage — informal age term

"Pediatric" doesn't map to a single HsapDv term. The agent uses latent knowledge of age ranges to enumerate year-based stages:

> "pediatric" typically refers to ages 0–14 years

```python
development_stage in [
    "newborn human stage",
    "infant stage",
    "1-year-old stage",
    "2-year-old stage",
    "3-year-old stage",
    ...
    "14-year-old stage"
]
```

Each of these is an exact HsapDv label that `enhance()` can expand. This is a case where the agent bridges informal language and formal ontology — no single OLS4 lookup would return "pediatric".

---

## Step 5: Construct the filter

```python
'is_primary_data == True and tissue in ["kidney"] and suspension_type == "nucleus" and assay in ["10x 3\' v3", "10x 3\' v2", "10x 3\' v1", "10x 5\' v2", "10x 5\' v1", "10x multiome", "10x 5\' transcription profiling", "10x 3\' transcription profiling", "10x gene expression flex"] and development_stage in ["newborn human stage", "infant stage", "1-year-old stage", "2-year-old stage", "3-year-old stage", "4-year-old stage", "5-year-old stage", "6-year-old stage", "7-year-old stage", "8-year-old stage", "9-year-old stage", "10-year-old stage", "11-year-old stage", "12-year-old stage", "13-year-old stage", "14-year-old stage"]'
```

Key points:
- `suspension_type` and `assay` are pass-through columns — not expanded by `enhance()`, forwarded to SOMA as-is
- `tissue` and `development_stage` are ontology-expanded by `enhance()`
- The long `assay in [...]` and `development_stage in [...]` lists are constructed by the agent, not by `enhance()`

---

## Step 6: Pre-flight count — limited data

```
Found 2,109 cells

assay (1 unique):
  10x 3' v3    2,109

tissue (1 unique):
  renal medulla    2,109

development_stage (1 unique):
  14-year-old stage    2,109

cell_type (43 unique):
  kidney loop of Henle thick ascending limb epithelial cell     898
  kidney loop of Henle thin descending limb epithelial cell     364
  renal medullary fibroblast                                    190
  kidney collecting duct principal cell                         137
  vasa recta ascending limb cell                                 79
  ... (38 more)
```

The agent flags a concern:

> Only 2,109 cells match this query. All come from a single dataset (10x 3' v3, renal medulla, 14-year-old).
> `get_highly_variable_genes()` may not produce reliable results with so few cells.
>
> For context, dropping the pediatric age restriction gives **1,513,517 cells** across 3 assays (10x multiome, 10x 3' v3, 10x 5' v1) and 4 tissue regions (cortex of kidney, renal medulla, kidney, renal papilla).
>
> Options:
> 1. Proceed with 2,109 pediatric cells (limited statistical power)
> 2. Drop age restriction — use all snRNA-seq 10x kidney data (1.5M cells)
> 3. Broaden to include young adults (add 15–25 year stages)

---

## Step 7: Generated code (option 1 — pediatric only)

```python
import cellxgene_census
from cxg_query_enhancer import enhance

# Pediatric stages (0-14 years)
pediatric_stages = [
    "newborn human stage", "infant stage",
    "1-year-old stage", "2-year-old stage", "3-year-old stage",
    "4-year-old stage", "5-year-old stage", "6-year-old stage",
    "7-year-old stage", "8-year-old stage", "9-year-old stage",
    "10-year-old stage", "11-year-old stage", "12-year-old stage",
    "13-year-old stage", "14-year-old stage",
]
stage_filter = ", ".join(f'"{s}"' for s in pediatric_stages)

# 10x assay variants
assay_filter = ', '.join([
    '"10x 3\' v3"', '"10x 3\' v2"', '"10x 3\' v1"',
    '"10x 5\' v2"', '"10x 5\' v1"', '"10x multiome"',
    '"10x 5\' transcription profiling"',
    '"10x 3\' transcription profiling"',
    '"10x gene expression flex"',
])

obs_filter = enhance(
    f'is_primary_data == True and '
    f'tissue in ["kidney"] and '
    f'suspension_type == "nucleus" and '
    f'assay in [{assay_filter}] and '
    f'development_stage in [{stage_filter}]',
    organism="homo_sapiens"
)

with cellxgene_census.open_soma(census_version="latest") as census:
    hvg_df = cellxgene_census.get_highly_variable_genes(
        census,
        organism="Homo sapiens",
        obs_value_filter=obs_filter,
        n_top_genes=2000
    )

print(f"Found {len(hvg_df)} highly variable genes")
print(hvg_df.head(20))
```

**Agent summary:**
> Resolved terms:
> - Tissue: kidney (UBERON:0002113) — expands to 4 structures
> - Assay: 9 x 10x variants (from census_fields.json)
> - Suspension type: nucleus (snRNA-seq)
> - Dev stage: 16 pediatric HsapDv stages (newborn through 14-year-old)
>
> Pre-flight count: 2,109 cells (limited — single dataset)
>
> Note: `get_highly_variable_genes()` uses `obs_value_filter=` (not `value_filter=`).
> Consider broadening the query if results are noisy due to low cell count.

---

## Key takeaways

1. **Assay filtering is agent-expanded, not ontology-expanded** — the agent reads `census_fields.json` and maps informal terms ("10x") to exact labels. `enhance()` passes `assay` through unchanged.
2. **Suspension type distinguishes snRNA-seq from scRNA-seq** — use `suspension_type == "nucleus"` rather than trying to filter by assay name.
3. **Informal age terms require enumeration** — "pediatric" doesn't exist in any ontology. The agent bridges this gap by listing individual year-based HsapDv stages.
4. **Data availability varies** — pediatric kidney snRNA-seq is sparse in Census (2,109 cells). The agent proactively checks and suggests alternatives rather than letting the user discover this downstream.
5. **HVG mode** uses `get_highly_variable_genes()` with `obs_value_filter=` (same parameter name as `get_anndata()`, different from `get_obs()` which uses `value_filter=`).
