# Roadmap

## Concrete Proposals

These are well-understood features with clear implementation paths.

### Dataset provenance in query output

Join query results against the census datasets table (`census["census_info"]["datasets"]`) to surface:
- `collection_name` (study name)
- `collection_doi` (paper DOI)
- `dataset_title`
- Portal URL: `https://cellxgene.cziscience.com/collections/{collection_id}`

**Implementation**: After any `get_obs()` or `get_anndata()` call, auto-join on `dataset_id` and display a provenance summary (unique datasets, DOIs). Could be a small utility function in `src/`.

### Assay and donor metadata in default column set

Add `assay`, `suspension_type`, and `donor_id` to the default `column_names` / `obs_column_names` in skill templates. These are commonly needed for downstream QC and batch-effect analysis.

### Mouse organism support improvements

Development stage expansion for mouse (`MmusDv`) is less tested than human. Verify and add test cases for common mouse developmental queries (embryonic day ranges, postnatal stages, adult).

### Skill config sync: Claude <-> Codex

Currently `setup.sh` syncs `.claude/agents/` -> `.codex/agents/`. Consider also syncing relevant parts of skill instructions if Codex gains skill-like support, or maintaining a shared `agents/` directory at project root with build-time copies.

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
