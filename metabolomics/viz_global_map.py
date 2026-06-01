"""Global function map visualizations: treemap, volcano plot, enrichment bar chart."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .knowledge_base import KnowledgeBase


def create_global_treemap(
    enrichment_results: pd.DataFrame,
    knowledge_base: KnowledgeBase,
    metabolite_names: dict = None,
) -> go.Figure:
    """Build a Plotly treemap showing the Reactome pathway hierarchy.

    Color = enrichment significance (-log10 padj), size = overlap count.
    Non-significant pathways shown in grey.
    Each tile shows the list of hit molecules on hover.
    """
    hierarchy_df = knowledge_base.get_hierarchy_for_treemap()
    if hierarchy_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No pathway data available", showarrow=False, font_size=20)
        return fig

    # Merge enrichment results
    if not enrichment_results.empty and "pathway_id" in enrichment_results.columns:
        merge_cols = ["pathway_id"]
        value_cols = ["padj", "overlap_count", "combined_score", "overlapping_metabolites"]
        available_cols = [c for c in value_cols if c in enrichment_results.columns]
        merged = hierarchy_df.merge(
            enrichment_results[merge_cols + available_cols],
            left_on="id",
            right_on="pathway_id",
            how="left",
        )
    else:
        merged = hierarchy_df.copy()
        merged["padj"] = 1.0
        merged["overlap_count"] = 0

    # Compute display values
    merged["neg_log10_padj"] = -np.log10(merged["padj"].fillna(1.0).clip(lower=1e-50))
    merged["display_size"] = merged.get("overlap_count", pd.Series(1, index=merged.index)).fillna(0).clip(lower=1).astype(int)

    # Build hit molecule list text for hover (wrap every 5 molecules)
    if "overlapping_metabolites" in merged.columns:
        def _format_hits(row):
            mets = row.get("overlapping_metabolites")
            if not isinstance(mets, list) or not mets:
                return "(no hits)"
            if metabolite_names:
                names = sorted(metabolite_names.get(m, m) for m in mets)
            else:
                names = sorted(mets)
            lines = []
            for i in range(0, len(names), 5):
                lines.append(", ".join(names[i:i + 5]))
            return "<br>".join(lines)
        merged["hit_molecules"] = merged.apply(_format_hits, axis=1)
    else:
        merged["hit_molecules"] = "(no data)"

    # Use only pathways that have metabolites
    merged = merged[merged["metabolite_count"] > 0].copy()
    if merged.empty:
        fig = go.Figure()
        fig.add_annotation(text="No pathways with metabolites found", showarrow=False, font_size=20)
        return fig

    # For treemap, we need: top_level_name / parent_name / name
    merged["mid_level"] = merged.apply(
        lambda r: r["parent_name"] if r["parent_name"] != r["top_level_name"] and r["parent_name"] else r["top_level_name"],
        axis=1,
    )

    fig = px.treemap(
        merged,
        path=[px.Constant("All Biological Functions"), "top_level_name", "mid_level", "name"],
        values="display_size",
        color="neg_log10_padj",
        color_continuous_scale=[
            [0.0, "#ffffff"],       # white (p >= 0.05, -log10 < 1.3)
            [0.325, "#ffffff"],     # white up to p=0.05 (-log10=1.3)
            [0.35, "#deebf7"],     # start coloring at p=0.05
            [0.5, "#9ecae1"],
            [0.7, "#4292c6"],
            [0.85, "#2171b5"],
            [1.0, "#08306b"],      # deepest blue at p=0.0001 (-log10=4)
        ],
        range_color=[0, 4],
        custom_data=["hit_molecules"],
    )

    fig.update_layout(
        title="Biological Function Map (Reactome Pathway Hierarchy)",
        margin=dict(t=50, l=10, r=10, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        coloraxis_colorbar=dict(
            title="-log10(FDR)",
            tickvals=[0, 1, 1.3, 2, 3, 4],
            ticktext=["NS", "0.1", "0.05", "0.01", "1e-3", "1e-4"],
        ),
        height=700,
    )
    fig.update_traces(
        textinfo="label+value",
        marker=dict(
            cornerradius=0,
            line=dict(width=0.3, color="black"),
            depthfade=False,
        ),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Overlap: %{value}<br>"
            "-log10(FDR): %{color:.2f}<br>"
            "<br><b>Hit molecules:</b><br>"
            "%{customdata[0]}"
            "<extra></extra>"
        ),
    )

    return fig


def create_volcano_plot(diff_results: pd.DataFrame) -> go.Figure:
    """Volcano plot: x = log2FC, y = -log10(padj).

    Colored by significance status: red (up), blue (down), grey (NS).
    """
    df = diff_results.copy()
    df["neg_log10_padj"] = -np.log10(df["padj"].clip(lower=1e-50))

    # Classify direction
    df["direction"] = "Not Significant"
    df.loc[df["significant"] & (df["log2_fc"] > 0), "direction"] = "Up"
    df.loc[df["significant"] & (df["log2_fc"] < 0), "direction"] = "Down"

    color_map = {"Up": "#e74c3c", "Down": "#3498db", "Not Significant": "#bdc3c7"}

    fig = px.scatter(
        df,
        x="log2_fc",
        y="neg_log10_padj",
        color="direction",
        color_discrete_map=color_map,
        hover_data={"chebi_id": True, "log2_fc": ":.2f", "padj": ":.2e"},
        category_orders={"direction": ["Up", "Down", "Not Significant"]},
    )

    # Add significance thresholds
    fig.add_hline(
        y=-np.log10(0.05), line_dash="dash", line_color="grey",
        annotation_text="FDR = 0.05",
    )
    fig.add_vline(x=np.log2(1.5), line_dash="dash", line_color="grey")
    fig.add_vline(x=-np.log2(1.5), line_dash="dash", line_color="grey")

    fig.update_layout(
        title="Volcano Plot: Differential Metabolite Abundance",
        xaxis_title="log2(Fold Change)",
        yaxis_title="-log10(FDR)",
        height=500,
        legend_title="Direction",
    )

    return fig


def create_enrichment_bar_chart(
    enrichment_results: pd.DataFrame,
    top_n: int = 20,
) -> go.Figure:
    """Horizontal bar chart of top enriched pathways.

    Bar length = -log10(FDR), color = enrichment score or overlap count.
    """
    if enrichment_results.empty:
        fig = go.Figure()
        fig.add_annotation(text="No enrichment results", showarrow=False, font_size=20)
        return fig

    df = enrichment_results.head(top_n).copy()
    df["neg_log10_padj"] = -np.log10(df["padj"].clip(lower=1e-50))

    # Truncate long pathway names
    df["display_name"] = df["pathway_name"].str[:50]

    # Color by overlap count or combined score
    color_col = "overlap_count" if "overlap_count" in df.columns else "neg_log10_padj"

    fig = px.bar(
        df.iloc[::-1],  # Reverse for top-to-bottom ordering
        x="neg_log10_padj",
        y="display_name",
        color=color_col,
        color_continuous_scale="YlOrRd",
        orientation="h",
        hover_data={
            "pathway_name": True,
            "padj": ":.2e",
            "overlap_count": True,
            "top_level_name": True,
        },
    )

    fig.update_layout(
        title=f"Top {top_n} Enriched Pathways",
        xaxis_title="-log10(FDR)",
        yaxis_title="",
        height=max(400, top_n * 25),
        coloraxis_colorbar_title="Overlap",
        margin=dict(l=300),
    )

    return fig


def create_metabolite_heatmap(
    data: pd.DataFrame,
    metadata: pd.DataFrame,
    diff_results: pd.DataFrame,
    top_n: int = 30,
    metabolite_names: dict = None,
) -> go.Figure:
    """Heatmap of top differential metabolites across samples.

    Rows = metabolites (ranked by significance), columns = samples.
    """
    # Select top significant metabolites
    sig = diff_results[diff_results["significant"]].head(top_n)
    if sig.empty:
        sig = diff_results.head(top_n)

    selected_ids = sig["chebi_id"].tolist()
    subset = data[selected_ids].copy()

    # Z-score normalize per metabolite
    subset = (subset - subset.mean()) / subset.std()

    # Sort columns by group
    order = metadata.sort_values("group")["sample_id"].tolist()
    order = [s for s in order if s in subset.index]
    subset = subset.loc[order]

    # Use metabolite names if provided
    y_labels = selected_ids
    if metabolite_names:
        y_labels = [metabolite_names.get(cid, cid) for cid in selected_ids]

    fig = go.Figure(data=go.Heatmap(
        z=subset.T.values,
        x=subset.index.tolist(),
        y=y_labels,
        colorscale=[
            [0.0, "#f7f7f7"],
            [0.25, "#fdd49e"],
            [0.5, "#fc8d59"],
            [0.75, "#d7301f"],
            [1.0, "#7f0000"],
        ],
        zmin=0,
        colorbar=dict(title="Abundance<br>(Z-score)"),
    ))

    fig.update_layout(
        title=f"Top {len(selected_ids)} Differential Metabolites (Z-score)",
        xaxis_title="Samples",
        yaxis_title="Metabolites",
        height=max(400, len(selected_ids) * 20),
    )

    return fig
