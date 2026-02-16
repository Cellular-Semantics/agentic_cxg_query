# Filter Expression Grammar

Formal grammar for `obs_value_filter` strings passed to `enhance()`. The filter is parsed by Python's `ast.parse(mode='eval')`, so it must be a valid Python expression — but only a subset of Python is meaningful.

**String quoting convention**: Always use **double quotes** for string literals inside the filter expression. Some census labels contain apostrophes (e.g. `10x 3' v3`) which break single-quoted strings. Double quotes avoid this issue and are equally valid Python.

---

## EBNF Grammar

```ebnf
filter       = condition { ("and" | "or") condition }
condition    = comparison | "(" filter ")"
comparison   = column "==" value
             | column "in" "[" value { "," value } "]"
             | column "==" literal       (* pass-through columns *)
column       = ontology_col | id_col | passthrough_col
value        = DOUBLE_QUOTED_STRING
literal      = DOUBLE_QUOTED_STRING | BOOLEAN

ontology_col      = "cell_type" | "tissue" | "tissue_general"
                  | "disease" | "development_stage"
id_col            = ontology_col "_ontology_term_id"
passthrough_col   = "sex" | "is_primary_data" | "assay" | "suspension_type" | "tissue_type"
```

---

## Column Reference

### Ontology-expanded columns (processed by `enhance()`)

These columns trigger SPARQL expansion — the input term is expanded to all subtypes + part_of relations, filtered to terms present in census.

| Column | ID variant | Ontology | Example label | Example ID |
|---|---|---|---|---|
| `cell_type` | `cell_type_ontology_term_id` | CL | `"T cell"` | `"CL:0000084"` |
| `tissue` | `tissue_ontology_term_id` | UBERON | `"lung"` | `"UBERON:0002048"` |
| `tissue_general` | `tissue_general_ontology_term_id` | UBERON | `"heart"` | `"UBERON:0000948"` |
| `disease` | `disease_ontology_term_id` | MONDO | `"COVID-19"` | `"MONDO:0100096"` |
| `development_stage` | `development_stage_ontology_term_id` | HsapDv / MmusDv | `"adult stage"` | `"HsapDv:0000258"` |

Label columns expand via `rdfs:label` match → subclass/part_of closure.
ID columns expand via direct IRI → subclass/part_of closure.

### Pass-through columns (forwarded to SOMA unmodified)

| Column | Valid values |
|---|---|
| `sex` | `"male"`, `"female"` |
| `is_primary_data` | `True`, `False` (Python booleans, not strings) |

### Agent-expanded columns (agent uses latent knowledge + `census_fields.json`)

Not ontology-expanded by `enhance()`. The agent reads `references/census_fields.json` to find exact census labels and constructs `assay in [...]` filters directly.

| Column | ID variant | Source | Valid values |
|---|---|---|---|
| `assay` | `assay_ontology_term_id` | EFO (lookup only) | See `census_fields.json` — ~37 assays |

**Assay synonym guidance** — map informal user terms to exact census labels from the lookup:

| User says | Map to census labels |
|---|---|
| "10x" / "chromium" | All `10x *` variants from lookup |
| "Smart-seq" | `Smart-seq`, `Smart-seq2`, `Smart-seq v4`, `Smart-seq3` |
| "droplet" / "droplet-based" | 10x variants + `Drop-seq` + `inDrop` + `microwell-seq` + ... |
| "plate-based" / "full-length" | Smart-seq family + CEL-seq family |
| "snRNA-seq" / "single-nucleus" | Combine with `suspension_type == "nucleus"` instead |
| "scRNA-seq" / "single-cell" | Combine with `suspension_type == "cell"` instead |

### Controlled vocabulary columns (fixed values, no lookup needed)

| Column | Valid values |
|---|---|
| `suspension_type` | `"cell"`, `"nucleus"`, `"na"` |
| `tissue_type` | `"tissue"`, `"organoid"`, `"cell culture"` |

---

## Operators

### Recognized by `enhance()` extractor

| Operator | Syntax | Behavior |
|---|---|---|
| `==` | `cell_type == "T cell"` | Single-value match. Rewritten to `in [...]` after expansion. |
| `in` | `tissue in ["lung", "heart"]` | Multi-value match. Each value expanded independently, results merged. |

### Boolean combinators

| Combinator | Precedence | Example |
|---|---|---|
| `and` | Higher | `cell_type == "T cell" and tissue == "lung"` |
| `or` | Lower | `tissue == "lung" or tissue == "heart"` |
| `()` | Explicit | `cell_type == "T cell" and (tissue == "lung" or tissue == "heart")` |

**Precedence**: `and` binds tighter than `or`. Use parentheses for `or` groups within `and` chains.

### NOT recognized by `enhance()` — silently ignored

These parse as valid Python but the extractor skips them — the comparison passes through to SOMA unchanged (no ontology expansion):

| Operator | Example | What happens |
|---|---|---|
| `!=` | `disease != "normal"` | Passes to SOMA literally. No expansion. |
| `not in` | `tissue not in ["blood"]` | Passes to SOMA literally. No expansion. |
| `>`, `<`, `>=`, `<=` | N/A | Not useful for census string columns. |

---

## Patterns

### Single condition
```python
'cell_type == "T cell"'
```

### Multiple conditions (AND)
```python
'is_primary_data == True and cell_type == "T cell" and tissue == "lung"'
```

### Multiple values for one column (IN)
```python
'cell_type in ["T cell", "B cell"]'
```

### OR with parentheses
```python
'is_primary_data == True and (tissue == "lung" or tissue == "heart")'
```

### ID-based filter (instead of label)
```python
'development_stage_ontology_term_id == "HsapDv:0000258"'
```

### Mixed label and ID columns
```python
'cell_type == "T cell" and disease_ontology_term_id == "MONDO:0100096"'
```

---

## Anti-patterns

| Pattern | Problem | Fix |
|---|---|---|
| `cell_type == 'T cell'` | Single quotes break on labels with apostrophes (e.g. `10x 3' v3`) | Use double quotes: `"T cell"` |
| `cell_type = "T cell"` | Single `=` (assignment) | Use `==` |
| `development_stage == "adult"` | Not an rdfs:label | Look up exact label: `"adult stage"` |
| `development_stage == "human adult stage"` | Not an rdfs:label | Use `"adult stage"` (no organism prefix) |
| `disease != "normal"` | `!=` skips expansion | Works as SOMA pass-through, but won't expand `normal` subtypes |
| `cell_type == "T cells"` | Plural — not an rdfs:label | Use singular: `"T cell"` |
| Missing `is_primary_data == True` | Duplicate cells counted | Always include unless user explicitly wants duplicates |
