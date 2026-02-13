"""
Example script demonstrating the cxg-query-enhancer with cellxgene_census.

This script shows how to:
1. Construct a query filter for CELLxGENE census
2. Use the enhance() function to expand ontology terms
3. Use resolve_genes() to map gene names to Ensembl IDs
4. Retrieve data from the census using different API modes
"""

import logging
from cxg_query_enhancer import enhance
from gene_resolver import resolve_genes, build_var_value_filter

# Setup logging to see what the enhancer is doing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def example_simple_query():
    """
    Example: Simple query for female T cells in lung tissue.

    This demonstrates how the enhancer expands:
    - 'T cell' to include all T cell subtypes (CD4+, CD8+, regulatory T cells, etc.)
    - 'lung' to include all lung parts and structures
    """
    logger.info("=" * 60)
    logger.info("Example 1: Female T cells in lung tissue")
    logger.info("=" * 60)

    # Original query - simple and concise
    original_query = "sex == 'female' and cell_type in ['T cell'] and tissue in ['lung']"

    logger.info(f"\nOriginal query:\n{original_query}\n")

    # Enhanced query - automatically expanded to include all subtypes
    enhanced_query = enhance(original_query, organism="homo_sapiens")

    logger.info(f"\nEnhanced query:\n{enhanced_query}\n")

    return enhanced_query


def example_disease_query():
    """
    Example: Macrophages from kidney with diabetes.

    This demonstrates expansion of:
    - 'macrophage' to include alveolar macrophages, Kupffer cells, etc.
    - 'kidney' to include renal cortex, nephron, etc.
    - 'diabetes mellitus' to include type 1, type 2, etc.
    """
    logger.info("=" * 60)
    logger.info("Example 2: Macrophages from kidney with diabetes")
    logger.info("=" * 60)

    original_query = (
        "cell_type in ['macrophage'] and "
        "tissue in ['kidney'] and "
        "disease in ['diabetes mellitus']"
    )

    logger.info(f"\nOriginal query:\n{original_query}\n")

    enhanced_query = enhance(original_query, organism="homo_sapiens")

    logger.info(f"\nEnhanced query:\n{enhanced_query}\n")

    return enhanced_query


def example_developmental_stage_query():
    """
    Example: Adult neurons from brain.

    This demonstrates expansion of:
    - 'neuron' to include all neuron subtypes
    - 'brain' to include all brain structures
    - 'adult' to include all adult developmental stages
    """
    logger.info("=" * 60)
    logger.info("Example 3: Adult neurons from brain")
    logger.info("=" * 60)

    original_query = (
        "cell_type in ['neuron'] and "
        "tissue in ['brain'] and "
        "development_stage in ['adult']"
    )

    logger.info(f"\nOriginal query:\n{original_query}\n")

    # Note: organism parameter is critical for development_stage queries!
    enhanced_query = enhance(original_query, organism="homo_sapiens")

    logger.info(f"\nEnhanced query:\n{enhanced_query}\n")

    return enhanced_query


def example_gene_filtering():
    """
    Example: Gene filtering with resolve_genes().

    This demonstrates how to:
    - Resolve gene names to Ensembl IDs
    - Handle ambiguous gene names
    - Build a var_value_filter for use with get_anndata()
    """
    logger.info("=" * 60)
    logger.info("Example 4: Gene filtering (TP53, BRCA1, CD4)")
    logger.info("=" * 60)

    gene_names = ["TP53", "BRCA1", "CD4"]

    logger.info(f"\nResolving genes: {gene_names}")

    # NOTE: This requires census access on first run (results are cached).
    # Uncomment below to run:
    #
    # matches = resolve_genes(gene_names, organism="homo_sapiens")
    # for m in matches:
    #     status = "AMBIGUOUS" if m.is_ambiguous else "OK"
    #     logger.info(f"  {m.query} -> {m.ensembl_ids} [{status}]")
    #
    # all_ids = [eid for m in matches for eid in m.ensembl_ids]
    # var_filter = build_var_value_filter(all_ids)
    # logger.info(f"\nvar_value_filter: {var_filter}")

    code_example = '''
from cxg_query_enhancer import enhance
from gene_resolver import resolve_genes, build_var_value_filter
import cellxgene_census

# 1. Resolve gene names to Ensembl IDs
matches = resolve_genes(["TP53", "BRCA1", "CD4"], organism="homo_sapiens")
for m in matches:
    print(f"  {m.query} -> {m.ensembl_ids} (ambiguous={m.is_ambiguous})")

# 2. Build var filter
all_ids = [eid for m in matches for eid in m.ensembl_ids]
var_filter = build_var_value_filter(all_ids)

# 3. Combine with obs filter
obs_filter = enhance(
    "cell_type in ['fibroblast'] and tissue in ['lung']",
    organism="homo_sapiens"
)

# 4. Fetch expression data for specific genes
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
'''

    print("\nCode example (gene filtering + obs filtering):")
    print(code_example)

    return code_example


def example_usage_with_census():
    """
    Example showing how to use the enhanced query with cellxgene_census.

    NOTE: This is commented out by default because it requires downloading
    census data. Uncomment to actually fetch data.
    """
    print("\n" + "=" * 60)
    print("Example: Using enhanced query with cellxgene_census")
    print("=" * 60)

    code_example = '''
import cellxgene_census
from cxg_query_enhancer import enhance

# Construct your query
query = "sex == 'female' and cell_type in ['T cell'] and tissue in ['lung']"

# Enhance it to include all subtypes
enhanced_query = enhance(query, organism="homo_sapiens")

# Use it with cellxgene_census
with cellxgene_census.open_soma(census_version="latest") as census:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter=enhanced_query,
        obs_column_names=[
            "cell_type",
            "tissue",
            "disease",
            "sex",
            "development_stage"
        ]
    )

    print(f"Retrieved {len(adata)} cells")
    print(adata.obs.head())
'''

    print("\nCode example:")
    print(code_example)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("CELLxGENE Census Query Enhancer - Examples")
    print("=" * 80)

    # Run examples
    example_simple_query()
    print("\n")

    example_disease_query()
    print("\n")

    example_developmental_stage_query()
    print("\n")

    example_gene_filtering()
    print("\n")

    example_usage_with_census()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
