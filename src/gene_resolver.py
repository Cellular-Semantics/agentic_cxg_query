"""Gene name / Ensembl ID resolution against CELLxGENE Census var data.

Provides a cached bidirectional mapping between gene symbols and Ensembl IDs,
with disambiguation support for ambiguous gene names (preferring protein_coding
entries when requested).
"""

from __future__ import annotations

import logging
import os
import pickle
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Sequence

import cellxgene_census

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class GeneMatch:
    """Result of resolving a single gene query (name or Ensembl ID)."""

    query: str
    ensembl_ids: List[str] = field(default_factory=list)
    canonical_name: Optional[str] = None
    is_ambiguous: bool = False
    feature_types: List[str] = field(default_factory=list)


@dataclass
class GeneDict:
    """Bidirectional gene mapping built from census var data."""

    name_to_ids: Dict[str, List[str]] = field(default_factory=dict)
    id_to_name: Dict[str, str] = field(default_factory=dict)
    id_to_feature_type: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Census gene dictionary (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _get_gene_dict(census_version: str = "latest",
                   organism: str = "homo_sapiens") -> GeneDict:
    """Fetch the gene var table from census and build a :class:`GeneDict`.

    Results are cached both in-memory (LRU) and on disk as a pickle file
    under ``.cache/``, following the same pattern as ``_get_census_terms``
    in ``enhancer.py``.
    """
    cache_dir = ".cache"
    os.makedirs(cache_dir, exist_ok=True)
    safe_organism = re.sub(r"[\W_]+", "", organism)
    cache_filename = f"{census_version}_{safe_organism}_gene_dict.pkl"
    cache_path = os.path.join(cache_dir, cache_filename)

    # --- Try local pickle cache ---
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as fh:
                logger.info("Loading cached gene dict from %s", cache_path)
                return pickle.load(fh)
        except (pickle.UnpicklingError, EOFError) as exc:
            logger.warning("Cache file %s corrupted, refetching. Error: %s",
                           cache_path, exc)

    # --- Fetch from census ---
    logger.info("Fetching gene var table from CELLxGENE Census (%s / %s)...",
                census_version, organism)
    census_organism = organism.replace(" ", "_").lower()

    gd = GeneDict()

    try:
        with cellxgene_census.open_soma(census_version=census_version) as census:
            organism_data = census["census_data"].get(census_organism)
            if not organism_data:
                logger.warning("Organism '%s' not found in census.", census_organism)
                return gd

            var_df = (
                organism_data["ms"]["RNA"]
                .var.read(
                    column_names=["feature_id", "feature_name", "feature_type"],
                )
                .concat()
                .to_pandas()
            )

        for _, row in var_df.iterrows():
            ens_id = row["feature_id"]
            name = row["feature_name"]
            ftype = row["feature_type"]

            norm = name.upper()
            gd.name_to_ids.setdefault(norm, []).append(ens_id)
            gd.id_to_name[ens_id] = name
            gd.id_to_feature_type[ens_id] = ftype

        # --- Persist to disk ---
        with open(cache_path, "wb") as fh:
            pickle.dump(gd, fh)
        logger.info("Saved gene dict to cache: %s", cache_path)

    except Exception as exc:
        logger.error("Error fetching gene var table: %s", exc)

    return gd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_ENSEMBL_PATTERN = re.compile(r"^ENS[A-Z]*G\d+$", re.IGNORECASE)


def resolve_genes(
    gene_names: Sequence[str],
    organism: str = "homo_sapiens",
    census_version: str = "latest",
    prefer_protein_coding: bool = True,
) -> List[GeneMatch]:
    """Resolve a list of gene names / Ensembl IDs to :class:`GeneMatch` objects.

    Parameters
    ----------
    gene_names:
        Gene symbols (e.g. ``"TP53"``) or Ensembl IDs (e.g. ``"ENSG00000141510"``).
    organism:
        Census organism string.
    census_version:
        Census version to use.
    prefer_protein_coding:
        When a gene name maps to multiple Ensembl IDs and exactly one is
        ``protein_coding``, auto-select it and mark the result as non-ambiguous.

    Returns
    -------
    List of :class:`GeneMatch`, one per input name (order preserved).
    """
    gd = _get_gene_dict(census_version, organism)
    results: List[GeneMatch] = []

    for raw in gene_names:
        query = raw.strip()

        # --- Ensembl ID passthrough ---
        if _ENSEMBL_PATTERN.match(query):
            ens_upper = query.upper()
            name = gd.id_to_name.get(ens_upper)
            ftype = gd.id_to_feature_type.get(ens_upper)
            if name is not None:
                results.append(GeneMatch(
                    query=query,
                    ensembl_ids=[ens_upper],
                    canonical_name=name,
                    is_ambiguous=False,
                    feature_types=[ftype] if ftype else [],
                ))
            else:
                # Unknown Ensembl ID — still pass it through
                results.append(GeneMatch(
                    query=query,
                    ensembl_ids=[ens_upper],
                    canonical_name=None,
                    is_ambiguous=False,
                    feature_types=[],
                ))
            continue

        # --- Name-based lookup ---
        norm = query.upper()
        ids = gd.name_to_ids.get(norm)

        if not ids:
            results.append(GeneMatch(query=query))
            continue

        ftypes = [gd.id_to_feature_type.get(i, "") for i in ids]

        if len(ids) == 1:
            results.append(GeneMatch(
                query=query,
                ensembl_ids=list(ids),
                canonical_name=gd.id_to_name.get(ids[0], query),
                is_ambiguous=False,
                feature_types=ftypes,
            ))
            continue

        # Ambiguous — try protein_coding disambiguation
        if prefer_protein_coding:
            pc_ids = [i for i, ft in zip(ids, ftypes) if ft == "protein_coding"]
            if len(pc_ids) == 1:
                results.append(GeneMatch(
                    query=query,
                    ensembl_ids=pc_ids,
                    canonical_name=gd.id_to_name.get(pc_ids[0], query),
                    is_ambiguous=False,
                    feature_types=["protein_coding"],
                ))
                continue

        # Still ambiguous
        results.append(GeneMatch(
            query=query,
            ensembl_ids=list(ids),
            canonical_name=gd.id_to_name.get(ids[0], query),
            is_ambiguous=True,
            feature_types=ftypes,
        ))

    return results


def build_var_value_filter(ensembl_ids: Sequence[str]) -> str:
    """Build a ``var_value_filter`` string for CELLxGENE census API calls.

    Parameters
    ----------
    ensembl_ids:
        Ensembl gene IDs (e.g. ``["ENSG00000141510"]``).

    Returns
    -------
    A filter expression such as ``"feature_id in ['ENSG00000141510']"``,
    or an empty string if *ensembl_ids* is empty.
    """
    unique = sorted(set(ensembl_ids))
    if not unique:
        return ""
    quoted = ", ".join(f"'{eid}'" for eid in unique)
    return f"feature_id in [{quoted}]"
