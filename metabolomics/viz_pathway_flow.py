"""Pathway flow diagram visualization with compartment-aware layout."""

from typing import Dict, Optional, Tuple

import networkx as nx
import plotly.graph_objects as go

from .pathway_graph import COMPARTMENT_COLORS, COMPARTMENT_LABELS


def create_pathway_flow_diagram(
    G: nx.DiGraph,
    layout: Dict[str, Tuple[float, float]],
    pathway_name: str,
    compartment_bounds: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
) -> go.Figure:
    """Render a pathway as an interactive flow diagram with compartment regions.

    Compartments are drawn as colored rectangular regions.
    Metabolites are placed in organized grids within each compartment.
    Each molecule appears only once. Directed arrows show reaction flow.

    Node styling:
        - Metabolites: circles, colored by fold-change (RdBu diverging)
        - Enzymes: squares, light blue

    Args:
        G: NetworkX DiGraph with node attributes (type, compartment, fold_change, etc.)
        layout: Dict of node_id -> (x, y) positions.
        pathway_name: Display name for the title.
        compartment_bounds: Dict of compartment -> (y_min, y_max, x_min, x_max).
    """
    if not G or len(G.nodes) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No pathway graph data available.<br>Reactome API connection may be required.",
            showarrow=False, font_size=16,
        )
        fig.update_layout(title=pathway_name, height=500)
        return fig

    fig = go.Figure()

    # --- Draw compartment regions ---
    if compartment_bounds:
        for comp_name, (y_min, y_max, x_min, x_max) in compartment_bounds.items():
            color = COMPARTMENT_COLORS.get(comp_name, "#F5F5F5")
            label = COMPARTMENT_LABELS.get(comp_name, comp_name)

            # Draw filled rectangle for compartment
            fig.add_shape(
                type="rect",
                x0=x_min, y0=y_min, x1=x_max, y1=y_max,
                fillcolor=color,
                opacity=0.5,
                line=dict(color="#999999", width=1.5, dash="dot"),
                layer="below",
            )

            # Compartment label
            fig.add_annotation(
                x=x_min + 5, y=y_min + 5,
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=11, color="#555555"),
                xanchor="left", yanchor="top",
            )

    # --- Draw edges with arrows ---
    # Group edges by type for different styling
    for u, v, edata in G.edges(data=True):
        if u not in layout or v not in layout:
            continue
        x0, y0 = layout[u]
        x1, y1 = layout[v]

        is_catalyst = edata.get("role") == "catalyst"
        line_color = "#90CAF9" if is_catalyst else "#888888"
        line_dash = "dot" if is_catalyst else "solid"
        line_width = 1.0 if is_catalyst else 1.5

        # Draw edge line
        fig.add_trace(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=line_width, color=line_color, dash=line_dash),
            hoverinfo="none",
            showlegend=False,
        ))

        # Arrow annotation
        fig.add_annotation(
            x=x1, y=y1,
            ax=x0, ay=y0,
            xref="x", yref="y",
            axref="x", ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.0,
            arrowwidth=1.5,
            arrowcolor=line_color,
            opacity=0.7,
            standoff=12,  # stop arrow before node center
        )

    # --- Metabolite nodes ---
    met_nodes = [(n, d) for n, d in G.nodes(data=True)
                 if d.get("type") == "metabolite" and n in layout]

    if met_nodes:
        met_x = [layout[n][0] for n, _ in met_nodes]
        met_y = [layout[n][1] for n, _ in met_nodes]
        met_colors = []
        met_text = []
        met_hover = []
        met_line_colors = []

        for n, d in met_nodes:
            fc = d.get("fold_change")
            met_colors.append(fc if fc is not None else 0)
            met_text.append(d.get("name", n))
            chebi = d.get("chebi_id", "")
            comp = d.get("compartment", "")
            fc_str = f"{fc:.2f}" if fc is not None else "N/A"
            met_hover.append(
                f"<b>{d.get('full_name', d.get('name', n))}</b><br>"
                f"ChEBI: {chebi}<br>"
                f"Compartment: {comp}<br>"
                f"log2FC: {fc_str}"
            )
            # Highlight measured metabolites with thicker border
            met_line_colors.append("black" if fc is not None else "#999999")

        fig.add_trace(go.Scatter(
            x=met_x, y=met_y,
            mode="markers+text",
            marker=dict(
                size=22,
                color=met_colors,
                colorscale="RdBu_r",
                cmin=-3, cmax=3,
                line=dict(width=2, color=met_line_colors),
                colorbar=dict(
                    title="log2FC",
                    x=1.02,
                    tickvals=[-3, -1.5, 0, 1.5, 3],
                ),
            ),
            text=met_text,
            textposition="top center",
            textfont=dict(size=9, color="#333333"),
            hovertext=met_hover,
            hoverinfo="text",
            name="Metabolites",
        ))

    # --- Enzyme nodes ---
    enz_nodes = [(n, d) for n, d in G.nodes(data=True)
                 if d.get("type") == "enzyme" and n in layout]

    if enz_nodes:
        enz_x = [layout[n][0] for n, _ in enz_nodes]
        enz_y = [layout[n][1] for n, _ in enz_nodes]
        enz_text = [d.get("name", n)[:20] for n, d in enz_nodes]
        enz_hover = [
            f"<b>{d.get('full_name', d.get('name', n))}</b><br>"
            f"Compartment: {d.get('compartment', '')}"
            for n, d in enz_nodes
        ]

        fig.add_trace(go.Scatter(
            x=enz_x, y=enz_y,
            mode="markers+text",
            marker=dict(
                size=16,
                color="#a8d8ea",
                symbol="square",
                line=dict(width=1.5, color="#4a90d9"),
            ),
            text=enz_text,
            textposition="bottom center",
            textfont=dict(size=8, color="#4a90d9"),
            hovertext=enz_hover,
            hoverinfo="text",
            name="Enzymes",
        ))

    # --- Layout ---
    # Compute axis range from all positions
    all_x = [pos[0] for pos in layout.values()]
    all_y = [pos[1] for pos in layout.values()]
    x_pad = 80
    y_pad = 60

    fig.update_layout(
        title=dict(
            text=f"Pathway Flow: {pathway_name}",
            font_size=16,
        ),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.8)",
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(all_x) - x_pad, max(all_x) + x_pad],
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(all_y) - y_pad, max(all_y) + y_pad],
            autorange="reversed",  # top-to-bottom flow
        ),
        plot_bgcolor="white",
        height=max(500, len(G.nodes) * 15 + 200),
        margin=dict(t=80, l=20, r=80, b=20),
    )

    return fig


def create_pathway_summary_table(
    enrichment_results: "pd.DataFrame",
    top_n: int = 10,
) -> go.Figure:
    """Create a summary table of top enriched pathways for selection."""
    import pandas as pd

    if enrichment_results.empty:
        fig = go.Figure()
        fig.add_annotation(text="No enriched pathways", showarrow=False, font_size=16)
        return fig

    df = enrichment_results.head(top_n)

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Pathway", "Category", "Overlap", "FDR", "Score"],
            fill_color="#2c3e50",
            font=dict(color="white", size=12),
            align="left",
        ),
        cells=dict(
            values=[
                df["pathway_name"].str[:45],
                df["top_level_name"].str[:20],
                df["overlap_count"],
                df["padj"].apply(lambda x: f"{x:.2e}"),
                df.get("combined_score", df.get("score", pd.Series(0))).apply(lambda x: f"{x:.1f}"),
            ],
            fill_color=[["#f8f9fa", "#ffffff"] * (len(df) // 2 + 1)],
            align="left",
            font_size=11,
        ),
    )])

    fig.update_layout(
        title="Top Enriched Pathways (click row to view flow diagram)",
        height=max(300, 40 * top_n),
        margin=dict(t=40, l=10, r=10, b=10),
    )

    return fig
