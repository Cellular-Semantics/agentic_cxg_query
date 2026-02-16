# Roadmap

## User story

As a biologist/bioinformatician I want to pull relevant data from CELLxGENE census, based on some combination of cell type, tissue, disease and stage
in order to carry out my analysis. 
I want to specify what counts as relevant data in free text and have an agent generate code for me to query CELLxGENE or pull data directly for me.
I have limited prior knowledge of what data is in the Census and how it is annotated, so I want an agent to generate suitable filters with relevant ontology terms and to explore whether the resulting filters return sufficient numbers of cells in order to be useful for me.  If the filter returns no cells, I would like the agent to automatically explore relaxing those filters to find ones that do return cells. Examples could include choosing a broader age/stage filter, a more general tissue, cell type or disease term, or dropping one of the criteria.  This should be an initial exploration rather than an exhustive one.

I would like the agentic session to run quickly and efficiently.

## Multi-framework support

- Setup script should sync skills from claude
- Add support for copilot 
	- .vscode config
	- What else?

## Testing framework:

 - Pass free text query to a set of subagents (3-5?) and assess how well results (accross replicates) suport the use case.

## Future extensions

These are well-understood features with clear implementation paths.

### Support non-model organisms (marmoset, macaque, chimpanzee)

Census includes 3 additional species beyond human/mouse: *Callithrix jacchus* (1.7M cells), *Macaca mulatta* (2.9M cells), and *Pan troglodytes* (158K cells). These use generic UBERON life-stage terms (`prime adult stage`, `juvenile stage`, etc.) rather than species-specific ontologies (HsapDv/MmusDv). Requires updating `cxg_query_enhancer` to handle UBERON-based dev stages and routing to the correct organism collection.

### Support query/filter by assay and suspension type

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
