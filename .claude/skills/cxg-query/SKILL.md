---
name: cxg-query
description: Generate CELLxGENE census queries from natural language — supports gene filtering, multiple API modes, and direct execution
user-invocable: true
---

# CELLxGENE Census Query Generator

## Description
Generate CELLxGENE census queries from natural language descriptions. This skill constructs valid query filters with automatic ontology term expansion and gene name resolution, supporting multiple census API modes (`get_anndata()`, `get_obs()`, `get_highly_variable_genes()`).

## Usage
```
/cxg-query [natural language description of desired data]
```

## Examples
- `/cxg-query female T cells in lung tissue`
- `/cxg-query expression of TP53 and BRCA1 in lung fibroblasts`
- `/cxg-query just metadata for T cells in skin`
- `/cxg-query highly variable genes in pancreatic beta cells`
- `/cxg-query medium spiny neurons from adult human brain`

---

## Instructions

You are helping to construct a CELLxGENE census query from natural language input. Follow these steps in order.

### Step 1: Parse the natural language input

Extract the following from the user's request:

- **Sex**: female, male
- **Cell type**: any cell type (e.g., "T cells", "neurons", "macrophages")
- **Tissue/Anatomy**: any tissue or anatomical structure (e.g., "lung", "brain", "kidney")
- **Disease**: any disease or condition (e.g., "diabetes", "cancer")
- **Development stage**: any developmental stage (e.g., "adult", "embryonic")
- **Organism**: human or mouse (default to human if not specified)
- **Genes**: any gene names or Ensembl IDs (e.g., "TP53", "BRCA1", "ENSG00000141510")
- **Intent keywords**: look for cues about what the user wants:
  - "metadata", "cell counts", "how many" → `get_obs()` mode
  - gene names, "expression", "counts matrix" → `get_anndata()` mode
  - "highly variable", "HVG", "variable genes" → `get_highly_variable_genes()` mode
  - If unclear, default to `get_anndata()`

### Step 2: Find ontology terms

For each biological entity identified (cell type, tissue, disease, development stage), use the ontology-term-lookup agent to find the appropriate ontology term:

- **Cell types**: Search in Cell Ontology (CL)
- **Tissues**: Search in Uberon (UBERON)
- **Diseases**: Search in MONDO
- **Development stages**: Search in HsapDv (human) or MmusDv (mouse)

**IMPORTANT**: When searching for terms, try multiple phrasings if the first search doesn't yield good results. For example:
- "T cell" vs "T lymphocyte"
- "lung" vs "pulmonary"
- "kidney" vs "renal"

Use the Task tool with subagent_type=ontology-term-lookup for each term lookup.

### Step 3: Resolve gene names (if any)

If the user mentioned any gene names or Ensembl IDs, resolve them using the gene resolver:

```python
from gene_resolver import resolve_genes, build_var_value_filter

matches = resolve_genes(["TP53", "BRCA1"], organism="homo_sapiens")
```

For each result, check:
- **`is_ambiguous`**: If True, inform the user which Ensembl IDs matched and their `feature_types`. Ask which they want, or note that `protein_coding` was auto-selected if `prefer_protein_coding=True` resolved it.
- **Empty `ensembl_ids`**: Gene not found — inform the user and suggest checking the spelling.

Then build the var filter from all resolved Ensembl IDs:
```python
all_ids = [eid for m in matches for eid in m.ensembl_ids]
var_filter = build_var_value_filter(all_ids)
```

### Step 4: Construct the obs_value_filter

Build a Python expression string using these rules:

**Valid column names** (CELLxGENE census schema):
- `sex`: `'male'` or `'female'` (lowercase)
- `cell_type`: ontology label (e.g., `'T cell'`)
- `cell_type_ontology_term_id`: ontology ID (e.g., `'CL:0000084'`)
- `tissue` / `tissue_ontology_term_id`: tissue terms
- `tissue_general` / `tissue_general_ontology_term_id`: broader tissue category
- `disease` / `disease_ontology_term_id`: disease terms
- `development_stage` / `development_stage_ontology_term_id`: dev stage terms

**Syntax rules**:
- Use `==` for single values: `sex == 'female'`
- Use `in [...]` for multiple values: `cell_type in ['T cell', 'B cell']`
- Use `and` to combine conditions
- Always use single quotes for string values
- Prefer labels over IDs (the enhancer will expand them)

### Step 5: Determine output mode

Ask the user (or infer from context when obvious):

1. **API mode** — which census function to use:
   | Keyword clues | API mode | When to use |
   |---|---|---|
   | "metadata", "cell count", "how many" | `get_obs()` | Exploring metadata, counting cells |
   | gene names, "expression", "matrix" | `get_anndata()` | Retrieving expression data |
   | "HVG", "highly variable", "variable genes" | `get_highly_variable_genes()` | Feature selection |

2. **Execution mode** — generate code vs execute directly:
   - If the user says "run it", "execute", "fetch" → execute directly
   - If the user says "show code", "generate" → generate code only
   - If ambiguous, ask

**Size warning**: For broad `get_anndata()` queries (no gene filter, broad cell type), warn the user that this may download a very large dataset. Suggest running `get_obs()` first to estimate cell count.

### Step 6: Present the result

Use the appropriate template based on the chosen API mode.

---

#### Template A: `get_obs()` (metadata only)

```python
import cellxgene_census
from cxg_query_enhancer import enhance

obs_filter = enhance(
    "[obs_value_filter]",
    organism="[homo_sapiens or mus_musculus]"
)

with cellxgene_census.open_soma(census_version="latest") as census:
    obs_df = cellxgene_census.get_obs(
        census,
        organism="[Homo sapiens or Mus musculus]",
        value_filter=obs_filter,
        column_names=[
            "cell_type", "tissue", "disease",
            "development_stage", "sex", "dataset_id"
        ]
    )

print(f"Found {len(obs_df):,} cells")
print(obs_df.head())
```

**Note**: `get_obs()` uses the parameter name `value_filter=` (not `obs_value_filter`).

---

#### Template B: `get_anndata()` (expression data)

```python
import cellxgene_census
from cxg_query_enhancer import enhance

obs_filter = enhance(
    "[obs_value_filter]",
    organism="[homo_sapiens or mus_musculus]"
)

with cellxgene_census.open_soma(census_version="latest") as census:
    adata = cellxgene_census.get_anndata(
        census,
        organism="[Homo sapiens or Mus musculus]",
        obs_value_filter=obs_filter,
        var_value_filter="[var_value_filter or omit if no genes]",
        obs_column_names=[
            "cell_type", "tissue", "disease",
            "development_stage", "sex"
        ]
    )

print(f"Retrieved {adata.shape[0]:,} cells x {adata.shape[1]:,} genes")
print(adata.obs.head())
```

If no genes were specified, omit the `var_value_filter` parameter entirely.

---

#### Template C: `get_highly_variable_genes()` (HVG)

```python
import cellxgene_census
from cxg_query_enhancer import enhance

obs_filter = enhance(
    "[obs_value_filter]",
    organism="[homo_sapiens or mus_musculus]"
)

with cellxgene_census.open_soma(census_version="latest") as census:
    hvg_df = cellxgene_census.get_highly_variable_genes(
        census,
        organism="[Homo sapiens or Mus musculus]",
        obs_value_filter=obs_filter,
        n_top_genes=2000
    )

print(f"Found {len(hvg_df)} highly variable genes")
print(hvg_df.head(20))
```

---

#### Direct execution template

When the user wants you to run the query directly:

1. Execute the code using the Bash tool with Python
2. Show the shape and `.head()` preview
3. Offer to save results to `outputs/` directory

---

### Important Notes

1. **Organism parameter**: Always include the organism parameter when using `enhance()`, especially for development_stage queries
2. **Term not found**: If an ontology term cannot be found, suggest alternative phrasings or inform the user
3. **Multiple values**: If the user specifies multiple values for a category (e.g., "T cells and B cells"), use the `in [...]` syntax
4. **Enhancement**: The `enhance()` function will automatically:
   - Expand "T cell" to include all T cell subtypes (CD4+, CD8+, regulatory T cells, etc.)
   - Expand "lung" to include all lung parts (left lung, right lung, bronchus, etc.)
   - Expand diseases to include all subtypes
   - Filter results to only include terms present in CELLxGENE Census
5. **Gene resolution**: The `resolve_genes()` function handles:
   - Case-insensitive gene name lookup
   - Ensembl ID passthrough
   - Disambiguation of ambiguous names (preferring protein_coding)
   - 325 gene names in census are ambiguous across biotypes; the resolver handles this automatically

### Error Handling

- **Ambiguous ontology terms**: Ask the user to clarify (e.g., "Did you mean 'neuron' or 'neural cell'?")
- **Ambiguous gene names**: Report which Ensembl IDs matched and their biotypes; ask user to pick or accept the protein_coding default
- **Gene not found**: Suggest checking spelling or trying an alias
- **Term not found**: Suggest checking the ontology or using a different term
- **Invalid syntax**: Explain the correct syntax and provide examples

### Ontology Terms Found (include in output)

Always list the resolved terms:
- Cell type: [term label] ([term ID])
- Tissue: [term label] ([term ID])
- Disease: [term label] ([term ID])
- Development stage: [term label] ([term ID])
- Genes: [gene symbol] → [Ensembl ID] ([feature_type])
