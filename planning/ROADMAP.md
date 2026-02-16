# Roadmap

## User story

As a biologist/bioinformatician I want to pull relevant data from CELLxGENE census, based on some combination of cell type, tissue, disease and stage
in order to carry out my analysis.
I want to specify what counts as relevant data in free text and have an agent generate code for me to query CELLxGENE or pull data directly for me.
I have limited prior knowledge of what data is in the Census and how it is annotated, so I want an agent to generate suitable filters with relevant ontology terms and to explore whether the resulting filters return sufficient numbers of cells in order to be useful for me.  If the filter returns no cells, I would like the agent to automatically explore relaxing those filters to find ones that do return cells. Examples could include choosing a broader age/stage filter, a more general tissue, cell type or disease term, or dropping one of the criteria.  This should be an initial exploration rather than an exhustive one.

I would like the agentic session to run quickly and efficiently.

---

## Implemented

### Core query generation (skill + agent)

- `/cxg-query` skill parses natural language into biological entities and constructs filter expressions
- `ontology-term-lookup` agent resolves terms via OLS4 MCP (CL, UBERON, MONDO, HsapDv, MmusDv) with alternative phrasing, synonym matching, and deprecation checks
- Three API modes auto-selected by intent: `get_obs()`, `get_anndata()`, `get_highly_variable_genes()`
- `is_primary_data == True` added automatically for de-duplication

### Ontology expansion

- `enhance()` expands terms via Ubergraph subclass + part_of closure, filtered to census-present terms
- Handles both label-based and ID-based expansion
- Formal EBNF grammar for filter expressions with double-quote convention (handles apostrophes in labels like `10x 3' v3`)

### Gene resolution

- `gene_resolver.py`: bidirectional mapping between gene symbols and Ensembl IDs
- Protein_coding disambiguation for ambiguous gene names
- Cached on disk (pickle) and in memory (LRU)
- `build_var_value_filter()` constructs var filter strings
- Unit tests (`tests/test_gene_resolver.py`)

### Assay, suspension type, and tissue type filtering

- `census_fields.json` cached lookup (~37 assays with cell counts, suspension types, tissue types)
- `refresh_census_fields.py` regenerates from live census
- Informal assay term mapping (e.g. "10x" → all `10x *` variants, "droplet-based" → 10x + Drop-seq + inDrop + ...)
- `suspension_type` (cell/nucleus) and `tissue_type` (tissue/organoid/cell culture) as controlled vocabulary columns

### Development stage handling

- Exact rdfs:label enforcement (agent warns about `"adult"` vs `"adult stage"`)
- Species-specific routing (HsapDv for human, MmusDv for mouse)
- Organism confirmation prompt when stage mentioned without species
- Static obsolete-term lookups (`data/obsolete_hsapdv.tsv`, `data/obsolete_mmusdv.tsv`) refreshed from Ubergraph
- Informal age terms (e.g. "pediatric", "child") mapped to year-based HsapDv stages

### Pre-flight validation and zero-results fallback

- Mandatory cell count before presenting final query
- Zero-results trigger automatic relaxation loop (broaden disease → cell type → tissue → stage)
- Categorical dtype handling (filter zero-count categories from census category columns)

### Size estimation and direct execution

- Download size estimate (sparse/dense) before large `get_anndata()` queries
- Warnings for >500 MB, strong warnings for >5 GB
- Auto-save to `outputs/` with descriptive filenames (.h5ad or .parquet)

### Multi-framework support

- **Claude Code**: full skill + agent setup (`.claude/skills/`, `.claude/agents/`, `.mcp.json`)
- **OpenAI Codex**: full support (`.codex/skills/`, `.codex/agents/`, `.codex/config.toml`)
- **GitHub Copilot**: context-only via `.github/copilot-instructions.md`
- `setup.sh` syncs configs from `.claude/` → `.codex/` and `CLAUDE.md` → `AGENTS.md`

### Setup and tooling

- `setup.sh`: one-command setup (venv, deps, import verification, census field refresh, OLS4 check, obsolete stage refresh, config sync)
- `Makefile`: setup, test, check-mcp, clean
- Worked examples in `examples/`

---

## In Progress

### Full Copilot support via MCP server

Expose core functionality as an MCP server so VS Code Copilot (agent mode) can use the same tools. See `planning/copilot-mcp-server.md` for implementation plan.

- MCP server (`src/mcp_server.py`) with tools: `enhance_query`, `resolve_genes`, `count_cells`, `get_anndata`
- `.vscode/mcp.json` for Copilot agent mode
- Enriched `copilot-instructions.md` with domain knowledge from `SKILL.md`

---

## Future extensions

These are well-understood features with clear implementation paths.

### Support non-model organisms (marmoset, macaque, chimpanzee)

Census includes 3 additional species beyond human/mouse: *Callithrix jacchus* (1.7M cells), *Macaca mulatta* (2.9M cells), and *Pan troglodytes* (158K cells). These use generic UBERON life-stage terms (`prime adult stage`, `juvenile stage`, etc.) rather than species-specific ontologies (HsapDv/MmusDv). Requires updating `cxg_query_enhancer` to handle UBERON-based dev stages and routing to the correct organism collection.

### Dataset provenance in query output

Join query results against the census datasets table (`census["census_info"]["datasets"]`) to surface:
- `collection_name` (study name)
- `collection_doi` (paper DOI)
- `dataset_title`
- Portal URL: `https://cellxgene.cziscience.com/collections/{collection_id}`

**Implementation**: After any `get_obs()` or `get_anndata()` call, auto-join on `dataset_id` and display a provenance summary (unique datasets, DOIs). Could be a small utility function in `src/`.

### Assay and donor metadata in default column set

Add `assay`, `suspension_type`, and `donor_id` to the default `column_names` / `obs_column_names` in skill templates. These are commonly needed for downstream QC and batch-effect analysis.

---

## Experimental Proposals

These require further investigation and may not be feasible or practical.

### Author cell type annotations

**Problem**: The census only contains harmonized CL ontology labels. Original author-provided cell type annotations (e.g. `author_cell_type`) are only available in the source H5AD files hosted on CELLxGENE Discover.

**Current state of knowledge**:
- Census `get_obs()` returns ~25 standardized columns; no author annotations
- The Discover REST API (`/v1/collections/{id}`, `/v1/datasets/{id}`) returns dataset-level metadata only, not cell-level obs
- Author annotations live in the individual H5AD files, downloadable via `cellxgene_census.download_source_h5ad(dataset_id)`
- `gget cellxgene` with `meta_only=True` may retrieve obs metadata from Discover datasets (needs testing)

**Possible approaches (ranked by feasibility)**:
1. **Targeted H5AD obs-only download** -- After a census query, identify the unique `dataset_id`s in results, download only those H5ADs, read just `.obs` (using `anndata.read_h5ad(path, backed='r')`), and join author annotations back. Avoids loading expression matrices into memory but still requires full file downloads.
2. **gget meta_only** -- Test whether `gget.cellxgene(meta_only=True)` returns author annotation columns and whether it can be filtered to specific datasets. If so, this could be a lighter-weight path.
3. **Pre-built author annotation index** -- Build and cache a mapping of `(dataset_id, cell_barcode) -> author_cell_type` for commonly queried datasets. High upfront cost but fast at query time.
4. **Lobby for census schema change** -- Request that CZI add an `author_cell_type` column to the census obs table. Low probability but highest value.

**Open questions**:
- How consistent is the column naming across datasets? (`author_cell_type` vs `cell_type_original` vs custom names)
- What fraction of census datasets include author annotations?
- Is the cell barcode / soma_joinid mapping stable enough for reliable joins?

### Semantic query understanding

Move beyond keyword-based intent detection to understand more complex queries:
- "Compare T cells between healthy and diseased lung" (implies two queries + differential)
- "What cell types express TP53 in the brain?" (implies broad query + groupby)
- "Find datasets with at least 1000 neurons" (implies metadata aggregation)

This would require the skill to generate multi-step analysis workflows, not just single census API calls.

### Integration with scanpy/scvi workflows

Generate complete analysis pipelines beyond just data retrieval:
- QC filtering (mito%, gene counts)
- Normalization and log-transform
- Dimensionality reduction (PCA, UMAP)
- Clustering and marker gene identification

This would make the tool useful for end-to-end exploratory analysis, not just data access.
