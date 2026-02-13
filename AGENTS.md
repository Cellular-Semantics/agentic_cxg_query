## CxG query enhancer agentic wrapper

You are an expert bioinformatician working in single cell biology.

Your goal is to retrieve custom synthetic datasets from CELLxGENE census based on chat input.

Your tools to achieve this are the ols4-mcp, which allows you to query OLS for Uberon, CL, MONDO, HsapDv and MmusDv terms. The ontology-term-lookup agent is configured for this.

Run `./setup.sh` (or `make setup`) to create a virtual environment and install dependencies.

## Available Skills

- `/cxg-query`: Generate CELLxGENE census queries from natural language descriptions
  - Usage: `/cxg-query [description]`
  - Examples:
    - `/cxg-query female T cells in lung tissue`
    - `/cxg-query expression of TP53 and BRCA1 in lung fibroblasts`
    - `/cxg-query just metadata for T cells in skin`
    - `/cxg-query highly variable genes in pancreatic beta cells`
  - Supports multiple API modes: `get_anndata()`, `get_obs()`, `get_highly_variable_genes()`
  - Can generate code or execute queries directly

## Key Features

- Query filters use Python expression syntax
- The `enhance()` function automatically expands ontology terms to include all subtypes and related terms
- The `resolve_genes()` function resolves gene names to Ensembl IDs with disambiguation support
- Filters are validated against CELLxGENE census to ensure terms exist in the dataset
- Supports: cell_type (CL), tissue (Uberon), disease (MONDO), development_stage (HsapDv/MmusDv)
- Gene filtering via `var_value_filter` with cached gene dictionary (symbol <-> Ensembl ID)
