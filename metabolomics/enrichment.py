"""Enrichment analysis: differential abundance, ORA, and enrichment scoring."""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from .knowledge_base import KnowledgeBase


def classify_metabolites(
    data: pd.DataFrame,
    metadata: pd.DataFrame,
    group_column: str = "group",
    control_label: str = "control",
    treatment_label: str = "treatment",
    fc_threshold: float = 1.5,
    pvalue_threshold: float = 0.05,
    test_type: str = "ttest",
) -> pd.DataFrame:
    """Perform differential abundance analysis between two groups.

    Args:
        data: DataFrame (samples x metabolites), columns are ChEBI IDs.
        metadata: DataFrame with sample_id and group columns.
        group_column: Column name for group labels.
        control_label: Label for control group.
        treatment_label: Label for treatment group.
        fc_threshold: Absolute fold-change threshold for significance.
        pvalue_threshold: Adjusted p-value threshold for significance.
        test_type: "ttest" (Welch's t-test) or "mann_whitney" (Mann-Whitney U).

    Returns:
        DataFrame with columns: chebi_id, mean_control, mean_treatment,
        log2_fc, pvalue, padj, significant.
    """
    control_mask = metadata[group_column] == control_label
    treatment_mask = metadata[group_column] == treatment_label

    control_ids = metadata.loc[control_mask, "sample_id"].tolist()
    treatment_ids = metadata.loc[treatment_mask, "sample_id"].tolist()

    control_data = data.loc[data.index.isin(control_ids)]
    treatment_data = data.loc[data.index.isin(treatment_ids)]

    results = []
    for chebi_id in data.columns:
        ctrl_vals = control_data[chebi_id].values
        treat_vals = treatment_data[chebi_id].values

        mean_ctrl = np.mean(ctrl_vals)
        mean_treat = np.mean(treat_vals)

        # Log2 fold change (add small constant to avoid log(0))
        epsilon = 1e-10
        log2_fc = np.log2((mean_treat + epsilon) / (mean_ctrl + epsilon))

        # Statistical test
        if test_type == "ttest":
            stat, pvalue = stats.ttest_ind(treat_vals, ctrl_vals, equal_var=False)
        else:  # mann_whitney
            stat, pvalue = stats.mannwhitneyu(
                treat_vals, ctrl_vals, alternative="two-sided"
            )

        results.append({
            "chebi_id": chebi_id,
            "mean_control": mean_ctrl,
            "mean_treatment": mean_treat,
            "log2_fc": log2_fc,
            "pvalue": pvalue,
        })

    df = pd.DataFrame(results)

    # Multiple testing correction (Benjamini-Hochberg)
    if len(df) > 0:
        _, padj, _, _ = multipletests(df["pvalue"].values, method="fdr_bh")
        df["padj"] = padj
    else:
        df["padj"] = []

    # Classify significance
    df["significant"] = (df["padj"] < pvalue_threshold) & (
        df["log2_fc"].abs() > np.log2(fc_threshold)
    )

    return df.sort_values("padj").reset_index(drop=True)


def over_representation_analysis(
    significant_metabolites: List[str],
    knowledge_base: KnowledgeBase,
    all_measured_metabolites: Optional[List[str]] = None,
    min_overlap: int = 2,
    min_pathway_size: int = 3,
    max_pathway_size: int = 500,
) -> pd.DataFrame:
    """Fisher's exact test for pathway over-representation.

    Args:
        significant_metabolites: ChEBI IDs of significantly changed metabolites.
        knowledge_base: Loaded KnowledgeBase instance.
        all_measured_metabolites: All measured ChEBI IDs (background set).
            If None, uses all metabolites in the knowledge base.
        min_overlap: Minimum number of significant metabolites in pathway to test.
        min_pathway_size: Minimum pathway size (in background) to test.
        max_pathway_size: Maximum pathway size (in background) to test.

    Returns:
        DataFrame with: pathway_id, pathway_name, top_level_name,
        overlap_count, pathway_size, bg_size, pvalue, padj, odds_ratio,
        overlapping_metabolites.
    """
    sig_set = set(significant_metabolites)

    if all_measured_metabolites is not None:
        bg_set = set(all_measured_metabolites)
        # Only consider metabolites that are in both the background and the KB
        bg_in_kb = bg_set & set(knowledge_base.metabolite_pathway_map.keys())
    else:
        bg_in_kb = set(knowledge_base.metabolite_pathway_map.keys())

    bg_size = len(bg_in_kb)
    sig_in_bg = sig_set & bg_in_kb
    n_sig = len(sig_in_bg)

    results = []
    for pathway_id in knowledge_base.get_all_pathway_ids():
        pathway_metabolites = set(knowledge_base.get_all_metabolites_in_pathway(pathway_id))
        # Intersect with background
        pathway_in_bg = pathway_metabolites & bg_in_kb
        pathway_size = len(pathway_in_bg)

        if pathway_size < min_pathway_size or pathway_size > max_pathway_size:
            continue

        # Overlap: significant AND in pathway
        overlap = sig_in_bg & pathway_in_bg
        overlap_count = len(overlap)

        if overlap_count < min_overlap:
            continue

        # 2x2 contingency table for Fisher's exact test:
        #                    In pathway    Not in pathway
        # Significant        a             b
        # Not significant    c             d
        a = overlap_count
        b = n_sig - overlap_count
        c = pathway_size - overlap_count
        d = bg_size - n_sig - c

        # Ensure non-negative values
        a = max(0, a)
        b = max(0, b)
        c = max(0, c)
        d = max(0, d)

        _, pvalue = stats.fisher_exact([[a, b], [c, d]], alternative="greater")
        odds_ratio = (a * d) / (b * c) if (b * c) > 0 else float("inf")

        results.append({
            "pathway_id": pathway_id,
            "pathway_name": knowledge_base.get_pathway_name(pathway_id),
            "top_level_name": knowledge_base.get_top_level_for_pathway(pathway_id) or "",
            "overlap_count": overlap_count,
            "pathway_size": pathway_size,
            "bg_size": bg_size,
            "pvalue": pvalue,
            "odds_ratio": odds_ratio,
            "overlapping_metabolites": sorted(list(overlap)),
        })

    df = pd.DataFrame(results)
    if len(df) > 0:
        _, padj, _, _ = multipletests(df["pvalue"].values, method="fdr_bh")
        df["padj"] = padj
    else:
        df["padj"] = []

    return df.sort_values("pvalue").reset_index(drop=True)


def enrichment_score(
    metabolite_fc: Dict[str, float],
    knowledge_base: KnowledgeBase,
) -> pd.DataFrame:
    """Compute quantitative enrichment score per pathway.

    For each pathway, the score is the mean absolute log2 fold-change
    of its member metabolites that are in the input data.

    Args:
        metabolite_fc: Dict of chebi_id -> log2 fold-change.
        knowledge_base: Loaded KnowledgeBase instance.

    Returns:
        DataFrame with: pathway_id, pathway_name, top_level_name,
        mean_abs_fc, median_abs_fc, n_members, score.
    """
    results = []
    for pathway_id in knowledge_base.get_all_pathway_ids():
        pathway_metabolites = knowledge_base.get_all_metabolites_in_pathway(pathway_id)
        # Get fold-changes for metabolites in this pathway
        fcs = [
            metabolite_fc[m] for m in pathway_metabolites if m in metabolite_fc
        ]
        if not fcs:
            continue

        abs_fcs = [abs(fc) for fc in fcs]
        results.append({
            "pathway_id": pathway_id,
            "pathway_name": knowledge_base.get_pathway_name(pathway_id),
            "top_level_name": knowledge_base.get_top_level_for_pathway(pathway_id) or "",
            "mean_abs_fc": np.mean(abs_fcs),
            "median_abs_fc": np.median(abs_fcs),
            "n_members": len(fcs),
            "score": np.mean(abs_fcs) * np.sqrt(len(fcs)),  # Weighted by sqrt(n)
        })

    return pd.DataFrame(results).sort_values("score", ascending=False).reset_index(drop=True)


def combine_results(
    ora_results: pd.DataFrame,
    fc_results: pd.DataFrame,
) -> pd.DataFrame:
    """Merge ORA results with fold-change enrichment scores.

    Returns unified table ranked by combined score.
    """
    if ora_results.empty or fc_results.empty:
        if not ora_results.empty:
            ora_results["combined_score"] = -np.log10(ora_results["padj"].clip(lower=1e-50))
            return ora_results
        return fc_results

    merged = ora_results.merge(
        fc_results[["pathway_id", "mean_abs_fc", "score"]],
        on="pathway_id",
        how="left",
    )
    merged["mean_abs_fc"] = merged["mean_abs_fc"].fillna(0)
    merged["score"] = merged["score"].fillna(0)

    # Combined score: -log10(padj) * (1 + mean_abs_fc)
    merged["neg_log10_padj"] = -np.log10(merged["padj"].clip(lower=1e-50))
    merged["combined_score"] = merged["neg_log10_padj"] * (1 + merged["mean_abs_fc"])

    return merged.sort_values("combined_score", ascending=False).reset_index(drop=True)
