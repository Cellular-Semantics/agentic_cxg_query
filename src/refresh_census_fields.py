#!/usr/bin/env python3
"""Query CELLxGENE Census for field values and save a JSON lookup file.

Generates: .claude/skills/cxg-query/references/census_fields.json

Usage:
    python src/refresh_census_fields.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import cellxgene_census

OUTPUT_PATH = Path(".claude/skills/cxg-query/references/census_fields.json")


def get_field_counts(census, organism: str, column: str, id_column: str | None = None):
    """Get value counts for a column across an organism, optionally pairing with ID column."""
    cols = [column]
    if id_column:
        cols.append(id_column)

    obs_df = cellxgene_census.get_obs(
        census,
        organism=organism,
        value_filter="is_primary_data == True",
        column_names=cols,
    )

    if id_column:
        counts = obs_df.groupby([column, id_column], observed=True).size().reset_index(name="cells")
        return counts
    else:
        counts = obs_df[column].value_counts()
        counts = counts[counts > 0]
        return counts


def main():
    with cellxgene_census.open_soma(census_version="latest") as census:
        summary = census["census_info"]["summary"].read().concat().to_pandas().set_index("label")
        census_version = summary.loc["census_build_date", "value"]

        # --- Assay (with ontology IDs, combined across organisms) ---
        assay_totals = {}
        for organism in ["Homo sapiens", "Mus musculus"]:
            counts = get_field_counts(census, organism, "assay", "assay_ontology_term_id")
            for _, row in counts.iterrows():
                key = (row["assay"], row["assay_ontology_term_id"])
                assay_totals[key] = assay_totals.get(key, 0) + row["cells"]

        assay_list = [
            {"label": label, "id": term_id, "cells": int(cells)}
            for (label, term_id), cells in assay_totals.items()
        ]
        assay_list.sort(key=lambda x: x["cells"], reverse=True)

        # --- Suspension type (simple list) ---
        susp_all = set()
        for organism in ["Homo sapiens", "Mus musculus"]:
            counts = get_field_counts(census, organism, "suspension_type")
            susp_all.update(counts.index.tolist())
        suspension_types = sorted(susp_all)

        # --- Tissue type (simple list) ---
        tt_all = set()
        for organism in ["Homo sapiens", "Mus musculus"]:
            counts = get_field_counts(census, organism, "tissue_type")
            tt_all.update(counts.index.tolist())
        tissue_types = sorted(tt_all)

    result = {
        "census_version": census_version,
        "generated": datetime.now(timezone.utc).isoformat(),
        "assay": assay_list,
        "suspension_type": suspension_types,
        "tissue_type": tissue_types,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {OUTPUT_PATH} ({len(assay_list)} assays, census {census_version})")


if __name__ == "__main__":
    main()
