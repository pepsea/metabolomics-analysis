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
    ppt_mode: bool = True,
    fig_scale: float = 1.0,
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
        ppt_mode: If True, use larger fonts/nodes for PowerPoint readability.
    """
    if not G or len(G.nodes) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No pathway graph data available.<br>Reactome API connection may be required.",
            showarrow=False, font_size=16,
        )
        fig.update_layout(title=pathway_name, height=500)
        return fig

    # --- Size presets for PPT vs screen (fonts are fixed; markers may scale) ---
    if ppt_mode:
        MET_MARKER_MAX = 36
        MET_MARKER_MIN = 14
        ENZ_MARKER_SIZE = 14   # fixed small diamond; never scales
        ENZ_LINE_WIDTH = 0.8   # thin border
        MET_FONT_SIZE = 14
        ENZ_FONT_SIZE = 12
        COMP_LABEL_SIZE = 16
        EDGE_WIDTH = 0.8
        ARROW_SIZE = 0.8
        ARROW_WIDTH = 0.8
        TITLE_SIZE = 22
        COLORBAR_FONT = 13
        STANDOFF = 20
        MET_LINE_WIDTH = 2.5
        BASE_WIDTH = 1200   # slightly smaller default than before
        BASE_HEIGHT = 580
        V_MARGINS = 110
    else:
        MET_MARKER_MAX = 22
        MET_MARKER_MIN = 10
        ENZ_MARKER_SIZE = 10   # fixed small diamond; never scales
        ENZ_LINE_WIDTH = 0.6   # thin border
        MET_FONT_SIZE = 9
        ENZ_FONT_SIZE = 8
        COMP_LABEL_SIZE = 11
        EDGE_WIDTH = 0.6
        ARROW_SIZE = 0.7
        ARROW_WIDTH = 0.7
        TITLE_SIZE = 16
        COLORBAR_FONT = 11
        STANDOFF = 12
        MET_LINE_WIDTH = 2
        BASE_WIDTH = 900
        BASE_HEIGHT = 480
        V_MARGINS = 80

    # --- Dynamic marker size based on node density (metabolites only) ---
    level_counts: dict = {}
    for pos in layout.values():
        level_counts[pos[0]] = level_counts.get(pos[0], 0) + 1
    max_nodes_per_level = max(level_counts.values()) if level_counts else 1

    avail_per_node = (BASE_HEIGHT - V_MARGINS) / max_nodes_per_level

    FILL_RATIO = 0.72
    if avail_per_node >= MET_MARKER_MAX / FILL_RATIO:
        MET_MARKER_SIZE = MET_MARKER_MAX
        fig_height = BASE_HEIGHT
    else:
        MET_MARKER_SIZE = max(MET_MARKER_MIN, int(avail_per_node * FILL_RATIO))
        if MET_MARKER_SIZE <= MET_MARKER_MIN:
            fig_height = max(BASE_HEIGHT,
                             int(max_nodes_per_level * (MET_MARKER_MIN / FILL_RATIO)) + V_MARGINS)
        else:
            fig_height = BASE_HEIGHT

    # Apply fig_scale to both dimensions (after density-based height is settled)
    fig_width = int(BASE_WIDTH * fig_scale)
    fig_height = int(fig_height * fig_scale)

    # --- Compute scale for label-collision detection ---
    _y_vals = [pos[1] for pos in layout.values()]
    _y_pad = 60 if ppt_mode else 40
    _y_data_range = (max(_y_vals) - min(_y_vals) + 2 * _y_pad) if len(_y_vals) > 1 else 1
    _scale = (fig_height - V_MARGINS) / _y_data_range  # data units → pixels

    # Vertical clearance a "top center" label needs above the node centre (data units):
    # half marker radius + font cap-height (≈ font_size * 1.4)
    _dy_clear = (MET_MARKER_SIZE / 2 + MET_FONT_SIZE * 1.4) / max(_scale, 0.01)

    # x-threshold: anything within half an x-step counts as "same or next level"
    _x_vals = [pos[0] for pos in layout.values()]
    _x_steps = sorted({round(x) for x in _x_vals})
    _dx_step = (_x_steps[1] - _x_steps[0]) if len(_x_steps) > 1 else 180

    def _best_textpos_met(nodes):
        """Return per-node textposition list for metabolites.

        Priority: "top center" → clear above?  yes → keep.
                  no → "middle right" → clear to right? yes → use.
                  no → "middle left" → clear to left? yes → use.
                  fallback → "top center".
        """
        all_xy = list(layout.values())

        def _any_node_in_box(cx, cy, dx_lo, dx_hi, dy_lo, dy_hi):
            return any(
                dx_lo < (px - cx) <= dx_hi and dy_lo < (py - cy) <= dy_hi
                for px, py in all_xy
            )

        pos_map = {}
        for n, _ in nodes:
            x, y = layout[n]
            # "top center" clears if no node within _dy_clear directly above
            if not _any_node_in_box(x, y,
                                     -_dx_step * 0.4, _dx_step * 0.4,
                                     0, _dy_clear):
                pos_map[n] = "top center"
            # "middle right": label goes to the right; clear if no node within
            # half x-step to the right at similar y
            elif not _any_node_in_box(x, y,
                                       0, _dx_step * 0.8,
                                       -_dy_clear * 0.5, _dy_clear * 0.5):
                pos_map[n] = "middle right"
            # "middle left": symmetric check to the left
            elif not _any_node_in_box(x, y,
                                       -_dx_step * 0.8, 0,
                                       -_dy_clear * 0.5, _dy_clear * 0.5):
                pos_map[n] = "middle left"
            else:
                pos_map[n] = "top center"   # graceful fallback

        return [pos_map[n] for n, _ in nodes]

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
                line=dict(color="#999999", width=2.0 if ppt_mode else 1.5, dash="dot"),
                layer="below",
            )

            # Compartment label: placed just ABOVE the bounding box (outside top edge)
            # so it never overlaps with node labels inside the box.
            label_gap = 12 if ppt_mode else 8
            fig.add_annotation(
                x=x_min + 10, y=y_max + label_gap,
                text=f"<b>{label}</b>",
                showarrow=False,
                font=dict(size=COMP_LABEL_SIZE, color="#444444"),
                xanchor="left", yanchor="bottom",
            )

    # --- Draw edges with arrows ---
    # All edges are flow edges (Met→Enz→Met or direct Met→Met)
    for u, v, edata in G.edges(data=True):
        if u not in layout or v not in layout:
            continue
        x0, y0 = layout[u]
        x1, y1 = layout[v]

        line_color = "#666666"
        line_dash = "solid"
        line_width = EDGE_WIDTH

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
            arrowsize=ARROW_SIZE,
            arrowwidth=ARROW_WIDTH,
            arrowcolor=line_color,
            opacity=0.7,
            standoff=STANDOFF,
        )

    # --- Metabolite nodes ---
    met_nodes = [(n, d) for n, d in G.nodes(data=True)
                 if d.get("type") == "metabolite" and n in layout]

    # --- Helper: alternating top/bottom label positions within each x-level ---
    def _alternating_textpos(nodes, default_top: bool = True):
        """Return a list of textposition strings, alternating top/bottom
        for nodes that share the same x-level (sorted by y, high→low).
        Nodes alone at their level keep the default position."""
        # Group by x-level
        by_level: dict = {}
        for n, _ in nodes:
            x = layout[n][0]
            by_level.setdefault(x, []).append(n)

        pos_map: dict = {}
        for x, group in by_level.items():
            # Sort by y descending (top of screen = highest y)
            group_sorted = sorted(group, key=lambda n: layout[n][1], reverse=True)
            for i, n in enumerate(group_sorted):
                pos_map[n] = "top center" if (i % 2 == 0) == default_top else "bottom center"
        return [pos_map[n] for n, _ in nodes]

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
            met_line_colors.append("black" if fc is not None else "#999999")

        fig.add_trace(go.Scatter(
            x=met_x, y=met_y,
            mode="markers+text",
            marker=dict(
                size=MET_MARKER_SIZE,
                color=met_colors,
                colorscale="RdBu_r",
                cmin=-3, cmax=3,
                line=dict(width=MET_LINE_WIDTH, color=met_line_colors),
                colorbar=dict(
                    title=dict(text="log2FC", font=dict(size=COLORBAR_FONT)),
                    x=1.02,
                    tickvals=[-3, -1.5, 0, 1.5, 3],
                    tickfont=dict(size=COLORBAR_FONT - 1),
                ),
            ),
            text=met_text,
            textposition=_best_textpos_met(met_nodes),
            textfont=dict(size=MET_FONT_SIZE, color="#222222"),
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
        enz_text = [d.get("name", n)[:25] for n, d in enz_nodes]
        enz_hover = [
            f"<b>{d.get('full_name', d.get('name', n))}</b><br>"
            f"Compartment: {d.get('compartment', '')}"
            for n, d in enz_nodes
        ]

        fig.add_trace(go.Scatter(
            x=enz_x, y=enz_y,
            mode="markers+text",
            marker=dict(
                size=ENZ_MARKER_SIZE,
                color="white",
                symbol="diamond",
                line=dict(width=ENZ_LINE_WIDTH, color="black"),
            ),
            text=enz_text,
            textposition=_alternating_textpos(enz_nodes, default_top=False),
            textfont=dict(size=ENZ_FONT_SIZE, color="#3a7ac0"),
            hovertext=enz_hover,
            hoverinfo="text",
            name="Enzymes",
        ))

    # --- Layout dimensions (width/height already computed above) ---
    all_x = [pos[0] for pos in layout.values()]
    all_y = [pos[1] for pos in layout.values()]
    x_pad = 100 if ppt_mode else 60
    y_pad = 60 if ppt_mode else 40

    layout_kwargs = dict(
        title=dict(
            text=f"Pathway Flow: {pathway_name}",
            font_size=TITLE_SIZE,
        ),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.8)",
            font=dict(size=13 if ppt_mode else 11),
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(all_x) - x_pad, max(all_x) + x_pad],
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            # Extra headroom above: compartment labels sit at y_max + label_gap
            # (label_gap=12/8), so ensure at least that much space above nodes.
            range=[min(all_y) - y_pad, max(all_y) + max(y_pad, 50)],
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        width=fig_width,
        height=fig_height,
        margin=dict(t=80, l=30, r=80, b=30) if ppt_mode else dict(t=60, l=20, r=60, b=20),
    )

    fig.update_layout(**layout_kwargs)

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
