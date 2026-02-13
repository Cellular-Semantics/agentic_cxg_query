# CELLxGENE Query Filter Skill - Overview

## What Was Created

I've created a Claude Code skill (`/cxg-query`) that generates CELLxGENE census query filters from natural language descriptions. The skill integrates:

1. **OLS4 MCP**: For looking up ontology terms
2. **cxg-query-enhancer**: For automatic term expansion
3. **cellxgene-census**: For data retrieval

## Files Created/Modified

### New Files

1. **`.claude/skills/cxg-query.md`** - The skill definition that guides Claude in generating query filters
2. **`README.md`** - Complete project documentation
3. **`example_query.py`** - Working examples showing how to use the enhancer
4. **`SKILL_OVERVIEW.md`** - This file

### Modified Files

1. **`pyproject.toml`** - Added dependencies (cxg-query-enhancer, cellxgene-census)
2. **`CLAUDE.md`** - Updated project instructions with skill information

## How to Use the Skill

### Basic Usage

```bash
# In Claude Code, simply type:
/cxg-query female T cells in lung tissue
```

The skill will:
1. Parse your natural language description
2. Find appropriate ontology terms using OLS4
3. Generate a valid Python expression for the query filter
4. Show you how to use it with cellxgene_census
5. Explain what the enhanced query will retrieve

### Example Queries

```bash
/cxg-query medium spiny neurons from adult human brain
/cxg-query macrophages from kidney with diabetes mellitus
/cxg-query CD4+ T cells from blood
/cxg-query embryonic neurons from mouse cortex
```

## How It Works

### Query Filter Syntax

The skill generates Python expressions compatible with cellxgene_census:

```python
# Simple equality
"sex == 'female'"

# List membership
"cell_type in ['T cell', 'B cell']"

# Multiple conditions
"sex == 'female' and cell_type in ['T cell'] and tissue in ['lung']"
```

### Automatic Expansion

When you use the `enhance()` function, it automatically expands terms:

```python
from cxg_query_enhancer import enhance

# Original query
query = "cell_type in ['T cell'] and tissue in ['lung']"

# Enhanced query expands:
# - 'T cell' → CD4+ T cell, CD8+ T cell, regulatory T cell, etc. (76 terms)
# - 'lung' → left lung, right lung, bronchus, etc. (15 terms)
enhanced = enhance(query, organism="homo_sapiens")
```

### Full Example

```python
import cellxgene_census
from cxg_query_enhancer import enhance

# Your natural language description becomes:
query = "sex == 'female' and cell_type in ['T cell'] and tissue in ['lung']"

# Use with census
with cellxgene_census.open_soma(census_version="latest") as census:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter=enhance(query, organism="homo_sapiens"),
        obs_column_names=["cell_type", "tissue", "sex"]
    )

print(f"Retrieved {len(adata)} cells")
# Without enhance: ~71,000 cells
# With enhance: ~700,000 cells
```

## Supported Categories

| Category | Ontology | Column Name | Example Terms |
|----------|----------|-------------|---------------|
| Cell type | Cell Ontology (CL) | `cell_type` | T cell, neuron, macrophage |
| Tissue | Uberon | `tissue` | lung, kidney, brain |
| Disease | MONDO | `disease` | diabetes mellitus, cancer |
| Dev stage | HsapDv/MmusDv | `development_stage` | adult, embryonic |
| Sex | N/A | `sex` | male, female |

## Testing the Setup

Run the example script to see the enhancer in action:

```bash
python example_query.py
```

This will show you three examples of query enhancement without actually downloading census data.

## Key Concepts

### 1. Ontology-Aware Expansion

The enhancer uses Ubergraph (a knowledge graph of biomedical ontologies) to find:
- **Subclasses**: "macrophage" → "alveolar macrophage", "Kupffer cell"
- **Part-of relationships**: "kidney" → "renal cortex", "nephron"

### 2. Census Filtering

Only terms that actually exist in the CELLxGENE census dataset are included in the expanded query. This ensures your query will return results.

### 3. Organism-Specific

The `organism` parameter is critical for:
- Development stage queries (HsapDv vs MmusDv)
- Census filtering (ensuring terms exist for the target species)

## Advanced Usage

### Using Ontology IDs Directly

```python
query = "cell_type_ontology_term_id in ['CL:0000084']"
enhanced = enhance(query, organism="homo_sapiens")
```

### Disabling Census Filtering

```python
# Get pure ontology expansion without census filtering
enhanced = enhance(query, census_version=None)
```

### Specifying Categories

```python
# Only expand specific categories
enhanced = enhance(
    query,
    categories=["cell_type", "tissue"],
    organism="homo_sapiens"
)
```

## Troubleshooting

### Issue: "No ontology term found"

**Solution**: Try alternative phrasings:
- "T cell" vs "T lymphocyte"
- "lung" vs "pulmonary"
- "kidney" vs "renal"

### Issue: "Organism parameter required"

**Solution**: Always specify organism when using development_stage:
```python
enhance(query, organism="homo_sapiens")  # or "mus_musculus"
```

### Issue: Query returns no results

**Possible causes**:
1. Terms don't exist in census for that organism
2. Try removing one constraint at a time to identify the issue
3. Use `census_version=None` to see the full ontology expansion

## Next Steps

1. **Try the skill**: Use `/cxg-query` with your own descriptions
2. **Run examples**: Execute `python example_query.py`
3. **Build queries**: Start retrieving data from CELLxGENE census
4. **Explore examples**: See `example_query.py` for usage patterns

## Resources

- [CELLxGENE Census Documentation](https://chanzuckerberg.github.io/cellxgene-census/)
- [cxg-query-enhancer GitHub](https://github.com/Cellular-Semantics/cxg-query-enhancer)
- [Cell Ontology (CL)](http://obofoundry.org/ontology/cl.html)
- [Uberon Anatomy Ontology](http://obofoundry.org/ontology/uberon.html)
- [MONDO Disease Ontology](http://obofoundry.org/ontology/mondo.html)

## Feedback

If you encounter issues or have suggestions for improving the skill, please let me know!
