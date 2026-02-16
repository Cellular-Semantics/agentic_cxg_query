# Example: TP53 and BRCA1 expression in lung fibroblasts

A worked example showing gene name resolution, var filtering, and combined obs+var queries.

## The prompt

> Expression of TP53 and BRCA1 in lung fibroblasts

---

## Step 1: Parse the request

| Entity | Value | Category |
|---|---|---|
| Genes | TP53, BRCA1 | gene resolution |
| Cell type | fibroblast | `cell_type` (CL) |
| Tissue | lung | `tissue` (UBERON) |
| Organism | human (default) | — |

Keywords "expression" + gene names → `get_anndata()` mode with `var_value_filter`.

---

## Step 2: Ontology lookup

The agent queries OLS4 in parallel:

**fibroblast** → Cell Ontology
```
Best Match Found:
- Input Text: fibroblast
- Matched Term: fibroblast
- Ontology ID: CL:0000057
- Match Type: Exact label match
- Definition: A connective tissue cell which secretes an extracellular matrix rich in
  collagen and other macromolecules. Flattened and irregular in outline with branching
  processes; appear fusiform or spindle-shaped.
- Confidence: High
```

**lung** → Uberon
```
Best Match Found:
- Input Text: lung
- Matched Term: lung
- Ontology ID: UBERON:0002048
- Match Type: Exact label match
- Definition: Respiration organ that develops as an outpocketing of the esophagus.
- Confidence: High
```

---

## Step 3: Gene resolution

The agent runs `resolve_genes()` against the Census gene dictionary:

```python
from gene_resolver import resolve_genes, build_var_value_filter

matches = resolve_genes(["TP53", "BRCA1"], organism="homo_sapiens")
```

Results:
```
TP53  → ENSG00000141510 (protein_coding)     ✓ unambiguous
BRCA1 → ENSG00000012048 (protein_coding)     ✓ unambiguous
```

Both genes resolve cleanly. The agent builds the var filter:
```python
var_filter = build_var_value_filter(["ENSG00000141510", "ENSG00000012048"])
# → "feature_id in ['ENSG00000012048', 'ENSG00000141510']"
```

### What if a gene name were ambiguous?

Some gene names map to multiple Ensembl IDs across biotypes. For example, the name "TBCE" maps to both a protein_coding gene and a pseudogene. With `prefer_protein_coding=True` (the default), the resolver auto-selects the protein_coding entry and reports:

```
TBCE → ENSG00000284770 (protein_coding)     ✓ auto-resolved
       (also matched ENSG00000285053, lncRNA — skipped)
```

If both hits were protein_coding, the result is marked ambiguous and the agent asks you to pick.

---

## Step 4: Construct filters

**obs_value_filter:**
```python
'is_primary_data == True and cell_type in ["fibroblast"] and tissue in ["lung"]'
```

**var_value_filter:**
```python
"feature_id in ['ENSG00000012048', 'ENSG00000141510']"
```

---

## Step 5: Ontology expansion and pre-flight count

`enhance()` expands the obs filter:

**fibroblast** (CL:0000057) → 10 census-matched cell types:
> fibroblast, fibroblast of lung, alveolar type 1 fibroblast cell,
> alveolar adventitial fibroblast, bronchus fibroblast of lung,
> pulmonary interstitial fibroblast, adventitial fibroblast,
> mesothelial fibroblast, lung perichondrial fibroblast, hepatic stellate cell

**lung** (UBERON:0002048) → 13 census-matched tissue terms:
> lung, lung parenchyma, middle lobe of right lung, lower lobe of left lung,
> upper lobe of left lung, alveolus of lung, lingula of left lung,
> upper lobe of right lung, segmental bronchus, right lung,
> left lung, lower lobe of right lung, alveolar sac

Pre-flight count: **198,847 cells**

```
cell_type (10 unique):
  fibroblast                          50,656
  fibroblast of lung                  50,274
  alveolar type 1 fibroblast cell     49,036
  alveolar adventitial fibroblast     22,371
  bronchus fibroblast of lung         12,343
  pulmonary interstitial fibroblast    8,344
  adventitial fibroblast               5,418
  ... (3 more)
```

---

## Step 6: Generated code

```python
import cellxgene_census
from cxg_query_enhancer import enhance
from gene_resolver import resolve_genes, build_var_value_filter

# Resolve genes
matches = resolve_genes(["TP53", "BRCA1"], organism="homo_sapiens")
var_filter = build_var_value_filter(
    [eid for m in matches for eid in m.ensembl_ids]
)

# Build and expand obs filter
obs_filter = enhance(
    'is_primary_data == True and cell_type in ["fibroblast"] and tissue in ["lung"]',
    organism="homo_sapiens"
)

# Fetch expression data for just these 2 genes
with cellxgene_census.open_soma(census_version="latest") as census:
    adata = cellxgene_census.get_anndata(
        census,
        organism="Homo sapiens",
        obs_value_filter=obs_filter,
        var_value_filter=var_filter,
        obs_column_names=["cell_type", "tissue", "disease", "sex"]
    )

print(f"Retrieved {adata.shape[0]:,} cells x {adata.shape[1]:,} genes")
print(adata.obs.head())
print(adata.var)
```

**Agent summary:**
> Resolved terms:
> - Cell type: fibroblast (CL:0000057) — expands to 10 subtypes
> - Tissue: lung (UBERON:0002048) — expands to 13 structures
> - Genes: TP53 → ENSG00000141510, BRCA1 → ENSG00000012048
>
> Pre-flight count: 198,847 cells
>
> Note: Filtering to `is_primary_data == True` to exclude duplicate cells.
>
> Because only 2 genes are requested, the resulting AnnData will be small
> (198,847 cells x 2 genes) — safe to download directly.

---

## Why gene filtering matters

Without `var_value_filter`, `get_anndata()` downloads the full expression matrix (~60,000 genes per cell). With it, you get just the columns you need:

| Scenario | Matrix size | Download |
|---|---|---|
| All genes | 198,847 cells x 60,664 genes | ~9 GB sparse |
| 2 genes (TP53, BRCA1) | 198,847 cells x 2 genes | ~2 MB |

The gene resolver + var filter makes targeted expression queries practical.
