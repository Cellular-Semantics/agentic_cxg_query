# Example: Kidney macrophages with diabetes in adults

A worked example combining disease ontology, development stage, and the zero-results fallback loop.

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
Best Match Found:
- Input Text: macrophage
- Matched Term: macrophage
- Ontology ID: CL:0000235
- Match Type: Exact label match
- Definition: A mononuclear phagocyte present in variety of tissues, typically
  differentiated from monocytes, capable of phagocytosing a variety of extracellular
  particulate material, including immune complexes, microorganisms, and dead cells.
- Confidence: High
```

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

**diabetes mellitus** → MONDO
```
Best Match Found:
- Input Text: diabetes mellitus
- Matched Term: diabetes mellitus
- Ontology ID: MONDO:0005015
- Match Type: Exact label match
- Definition: A metabolic disorder characterized by abnormally high blood sugar levels
  due to diminished production of insulin or insulin resistance/desensitization.
- Confidence: High
```

**adult** → HsapDv

The user said "adult", but that's not an exact ontology label. The agent searches OLS4 for "adult stage" in HsapDv and finds two matches:

```
Multiple Matches Found (ranked):

1. Matched Term: adult stage | ID: HsapDv:0000258 | Match Type: Exact label match
   Definition: Human developmental stage that refers to a sexually mature human.
   Deprecated: No (verified against data/obsolete_hsapdv.tsv)
   Confidence: High

2. Matched Term: adult stage | ID: HsapDv:0000087 | Match Type: Exact label match
   Deprecated: Yes (found in data/obsolete_hsapdv.tsv)
   Confidence: N/A (obsolete term — do not use)

Recommendation: Use HsapDv:0000258 with exact label "adult stage"
```

The exact label `"adult stage"` is critical — `enhance()` matches on exact `rdfs:label` values. Using `"adult"` or `"human adult stage"` would silently fail to expand. The deprecation check catches the obsolete HsapDv:0000087 and routes to the active replacement.

---

## Step 3: Construct the filter

```python
'is_primary_data == True and cell_type in ["macrophage"] and tissue in ["kidney"] and disease in ["diabetes mellitus"] and development_stage in ["adult stage"]'
```

All four categories use their exact OLS4 label.

---

## Step 4: Pre-flight count — zero results!

The agent runs the mandatory cell count and gets:

```
Found 0 cells
```

This triggers the **zero-results fallback loop**. The agent doesn't just suggest relaxations — it actually runs each variant and reports the counts:

| Relaxation | Cells |
|---|---|
| Original (all 4 constraints) | 0 |
| Drop disease | **62,041** |
| Drop development_stage | 0 |
| Drop disease + development_stage | 66,338 |

Dropping disease alone yields 62,041 cells. The agent reports:

> The combination of diabetes mellitus + kidney macrophages returns zero cells.
> This is because the Census kidney datasets are annotated with related but distinct
> disease terms (chronic kidney disease, renal cell carcinoma, acute kidney failure)
> rather than "diabetes mellitus" itself.
>
> Dropping the disease filter gives 62,041 adult kidney macrophages. Here's what
> diseases are present in that set:

```
disease (8 unique):
  normal                               18,639
  nonpapillary renal cell carcinoma    18,597
  chronic kidney disease               11,866
  acute kidney failure                  6,759
  clear cell renal carcinoma            4,186
  kidney oncocytoma                     1,857
  chromophobe renal cell carcinoma        129
  kidney benign neoplasm                    8
```

The agent then lets the user choose: use the relaxed filter, or substitute a specific disease from the list.

---

## Step 5: Revised filter and expansion

After the user opts to drop the disease filter, `enhance()` expands:

**macrophage** (CL:0000235) → 5 census-matched cell types:
> macrophage, kidney resident macrophage, cycling macrophage,
> alternatively activated macrophage, kidney interstitial alternatively activated macrophage

**kidney** (UBERON:0002113) → 5 census-matched tissue terms:
> kidney, cortex of kidney, renal medulla, renal papilla, renal pelvis

**adult stage** (HsapDv:0000258) → 47 census-matched development stages:
> sixth decade stage (22,780), seventh decade stage (9,811),
> fifth decade stage (9,052), eighth decade stage (7,728),
> fourth decade stage (2,911), ... (individual year stages from 29y through 79y)

---

## Step 6: Generated code

```python
import cellxgene_census
from cxg_query_enhancer import enhance

obs_filter = enhance(
    'is_primary_data == True and '
    'cell_type in ["macrophage"] and '
    'tissue in ["kidney"] and '
    'development_stage in ["adult stage"]',
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
for col in ["cell_type", "tissue", "disease"]:
    counts = adata.obs[col].value_counts()
    counts = counts[counts > 0]
    print(f"\n{col} ({len(counts)} unique):")
    print(counts.to_string())
```

**Agent summary:**
> Resolved terms:
> - Cell type: macrophage (CL:0000235) — expands to 5 subtypes
> - Tissue: kidney (UBERON:0002113) — expands to 5 structures
> - Dev stage: adult stage (HsapDv:0000258) — expands to 47 terms
> - Disease: dropped (original "diabetes mellitus" returned 0 cells)
>
> Pre-flight count: 62,041 cells
>
> Note: Filtering to `is_primary_data == True` to exclude duplicate cells.
>
> Warning: This is a broad query (all genes). Estimated download: ~62K cells x ~60K genes.
> Consider adding gene filters to reduce download size.

---

## Tips for development stage queries

Development stages require care because the user's phrasing rarely matches the exact ontology label:

1. **Always look up via OLS4** — `"adult"` is not a label; `"adult stage"` is. `enhance()` uses exact `rdfs:label` matching, so a wrong label silently fails (no expansion, no error).
2. **Check for deprecated terms** — HsapDv has obsolete terms (e.g. HsapDv:0000087) that share labels with active terms. The agent checks `data/obsolete_hsapdv.tsv` to avoid them.
3. **Labels vary by organism** — human uses HsapDv, mouse uses MmusDv. The agent confirms species when a stage is mentioned without an explicit organism.
4. **Informal terms** like "pediatric", "juvenile", "child" don't map to a single ontology term. For these, the agent enumerates year-based stages:
   > "pediatric" → `"2-year-old stage"`, `"3-year-old stage"`, ..., `"14-year-old stage"`

This is where the agentic approach adds value — the agent bridges informal language and formal ontology labels via OLS4 lookup, ensuring `enhance()` always gets the exact label it needs.
