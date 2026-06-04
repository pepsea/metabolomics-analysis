"""Metabolite-only pathway flow diagram (Plotly).

The flow is drawn purely with metabolites: nodes are metabolites coloured by
log2 fold-change, connected by directed arrows (substrate → product). The
catalysing enzyme for each reaction is available on edge hover. Subcellular
compartments are shown as horizontal background bands.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import networkx as nx
import plotly.graph_objects as go

from .pathway_graph import COMPARTMENT_COLORS, COMPARTMENT_LABELS


class _FlowFig:
    """Wrapper around a Plotly Figure.

    Plotly's interactive .show() depends on a JS renderer that is blank in
    some Jupyter setups. To display reliably everywhere, .show() renders a
    static PNG inline (via kaleido) instead. The underlying figure is exposed
    as .fig for interactive use, and all other attributes/methods
    (write_image, write_html, update_layout, ...) delegate to it.
    """

    def __init__(self, fig: go.Figure):
        self.fig = fig

    def show(self, scale: float = 2.0, *_a, **_k):
        try:
            from IPython.display import Image, display
            png = self.fig.to_image(format="png", scale=scale)
            display(Image(data=png))
        except Exception:
            # Fall back to interactive renderer if static export unavailable
            self.fig.show()

    def __getattr__(self, name):
        # Delegate everything else (write_image, write_html, layout, data, ...)
        return getattr(self.fig, name)


def create_pathway_flow_diagram(
    G: Optional[nx.DiGraph],
    layout: Dict[str, Tuple[float, float]],
    pathway_name: str,
    compartment_bounds: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
    ppt_mode: bool = True,
    fig_scale: float = 1.0,
) -> go.Figure:
    """Render a metabolite-only pathway flow diagram with Plotly.

    Args:
        G: NetworkX DiGraph (all nodes type='metabolite'; edges carry
           'reaction' and 'enzyme' attributes).
        layout: {node_id: (x, y)} from compute_compartment_layout.
        pathway_name: Title.
        compartment_bounds: {comp: (y_min, y_max, x_min, x_max)} bands.
        ppt_mode: Larger fonts/markers for PowerPoint.
        fig_scale: Uniform size multiplier (figure is fixed 16:9 landscape).

    Returns:
        plotly.graph_objects.Figure
    """
    # Fixed 16:9 landscape (PowerPoint widescreen proportions)
    fig_w = int(1200 * fig_scale)
    fig_h = int(675 * fig_scale)

    # ── Empty / error state ───────────────────────────────────────────────────
    if not G or len(G.nodes) == 0 or not layout:
        fig = go.Figure()
        fig.add_annotation(
            text="No pathway graph data available.<br>"
                 "Reactome API connection may be required.",
            showarrow=False, font=dict(size=16, color="#666"),
        )
        fig.update_layout(
            title=f"Pathway Flow: {pathway_name}",
            width=fig_w, height=fig_h,
            plot_bgcolor="white", paper_bgcolor="white",
        )
        return _FlowFig(fig)

    # ── Style presets ─────────────────────────────────────────────────────────
    if ppt_mode:
        MARKER_SIZE = 26
        MET_FONT    = 13
        COMP_FONT   = 14
        TITLE_FONT  = 20
        ARROW_SIZE  = 2.0
        ARROW_WIDTH = 1.3
    else:
        MARKER_SIZE = 18
        MET_FONT    = 10
        COMP_FONT   = 11
        TITLE_FONT  = 16
        ARROW_SIZE  = 1.6
        ARROW_WIDTH = 1.1

    fig = go.Figure()

    xs = [p[0] for p in layout.values()]
    ys = [p[1] for p in layout.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_rng = max(x_max - x_min, 1)
    y_rng = max(y_max - y_min, 1)

    # ── Compartment background bands ──────────────────────────────────────────
    if compartment_bounds:
        for comp, (cy0, cy1, cx0, cx1) in compartment_bounds.items():
            fig.add_shape(
                type="rect",
                x0=cx0, y0=cy0, x1=cx1, y1=cy1,
                fillcolor=COMPARTMENT_COLORS.get(comp, "#F5F5F5"),
                opacity=0.45,
                line=dict(color="#bbbbbb", width=1, dash="dot"),
                layer="below",
            )
            fig.add_annotation(
                x=cx0 + x_rng * 0.008, y=cy1,
                text=f"<b>{COMPARTMENT_LABELS.get(comp, comp)}</b>",
                showarrow=False, xanchor="left", yanchor="bottom",
                font=dict(size=COMP_FONT, color="#555555"),
            )

    # ── Edges: directed arrows (substrate → product) ──────────────────────────
    # Plotly annotation arrows draw both line and head; standoff leaves a gap
    # around each node marker so heads remain visible.
    standoff = MARKER_SIZE * 0.65
    edge_mx, edge_my, edge_hover = [], [], []
    for u, v, ed in G.edges(data=True):
        if u not in layout or v not in layout:
            continue
        x0, y0 = layout[u]
        x1, y1 = layout[v]
        fig.add_annotation(
            x=x1, y=y1, ax=x0, ay=y0,
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2,
            arrowsize=ARROW_SIZE, arrowwidth=ARROW_WIDTH,
            arrowcolor="#8a8a8a", opacity=0.8,
            standoff=standoff, startstandoff=standoff,
        )
        # Invisible midpoint marker carrying reaction/enzyme hover text
        enz = ed.get("enzyme") or ""
        rxn = ed.get("reaction") or ""
        parts = []
        if rxn:
            parts.append(f"<b>{rxn}</b>")
        if enz:
            parts.append(f"Enzyme: {enz}")
        if parts:
            edge_mx.append((x0 + x1) / 2)
            edge_my.append((y0 + y1) / 2)
            edge_hover.append("<br>".join(parts))

    if edge_mx:
        fig.add_trace(go.Scatter(
            x=edge_mx, y=edge_my, mode="markers",
            marker=dict(size=12, color="rgba(0,0,0,0)"),
            hovertext=edge_hover, hoverinfo="text",
            showlegend=False, name="reactions",
        ))

    # ── Metabolite label positions (avoid stacking overlap) ───────────────────
    col_counts: Dict[float, int] = {}
    for p in layout.values():
        col_counts[round(p[0])] = col_counts.get(round(p[0]), 0) + 1

    nodes = list(G.nodes)

    def _fc_of(n):
        return G.nodes[n].get("fold_change")

    def _textpos(n):
        # Multi-node columns → label to the right so vertical neighbours
        # don't collide; otherwise above the marker.
        return "middle right" if col_counts.get(round(layout[n][0]), 1) > 1 else "top center"

    def _hover(n):
        d = G.nodes[n]
        fc = d.get("fold_change")
        fc_s = f"{fc:.2f}" if fc is not None else "N/A (unmeasured)"
        return (f"<b>{d.get('full_name', d.get('name', n))}</b><br>"
                f"ChEBI: {d.get('chebi_id', '')}<br>"
                f"Compartment: {d.get('compartment', '')}<br>"
                f"log2FC: {fc_s}")

    measured = [n for n in nodes if _fc_of(n) is not None]
    unmeasured = [n for n in nodes if _fc_of(n) is None]

    # Unmeasured metabolites (grey)
    if unmeasured:
        fig.add_trace(go.Scatter(
            x=[layout[n][0] for n in unmeasured],
            y=[layout[n][1] for n in unmeasured],
            mode="markers+text",
            marker=dict(size=MARKER_SIZE, color="#dcdcdc",
                        line=dict(width=1.2, color="#999999")),
            text=[G.nodes[n].get("name", n) for n in unmeasured],
            textposition=[_textpos(n) for n in unmeasured],
            textfont=dict(size=MET_FONT, color="#333333"),
            hovertext=[_hover(n) for n in unmeasured],
            hoverinfo="text",
            name="Unmeasured",
            showlegend=False,
        ))

    # Measured metabolites (coloured by log2FC)
    if measured:
        fig.add_trace(go.Scatter(
            x=[layout[n][0] for n in measured],
            y=[layout[n][1] for n in measured],
            mode="markers+text",
            marker=dict(
                size=MARKER_SIZE,
                color=[_fc_of(n) for n in measured],
                colorscale="RdBu_r", cmin=-3, cmax=3,
                line=dict(width=1.6, color="black"),
                colorbar=dict(
                    title=dict(text="log2FC", font=dict(size=MET_FONT)),
                    tickvals=[-3, -1.5, 0, 1.5, 3],
                    tickfont=dict(size=MET_FONT - 1),
                    thickness=14, len=0.55, x=1.01,
                ),
            ),
            text=[G.nodes[n].get("name", n) for n in measured],
            textposition=[_textpos(n) for n in measured],
            textfont=dict(size=MET_FONT, color="#111111"),
            hovertext=[_hover(n) for n in measured],
            hoverinfo="text",
            name="Metabolite",
            showlegend=False,
        ))

    # ── Axes / layout (fixed landscape, equal-ish padding) ────────────────────
    x_pad = x_rng * 0.10 + 40
    y_pad_bot = y_rng * 0.12 + 30
    y_pad_top = y_rng * 0.16 + 45     # headroom for compartment labels

    fig.update_layout(
        title=dict(text=f"Pathway Flow: {pathway_name}",
                   font=dict(size=TITLE_FONT), x=0.01, xanchor="left"),
        width=fig_w, height=fig_h,
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=54, l=20, r=70, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   range=[x_min - x_pad, x_max + x_pad]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                   range=[y_min - y_pad_bot, y_max + y_pad_top]),
        hovermode="closest",
    )
    return _FlowFig(fig)


# ── Pathway summary table (Plotly) ────────────────────────────────────────────
def create_pathway_summary_table(
    enrichment_results: "pd.DataFrame",
    top_n: int = 10,
) -> go.Figure:
    """Create a summary table of top enriched pathways for selection."""
    import pandas as pd  # noqa: F401

    if enrichment_results is None or enrichment_results.empty:
        fig = go.Figure()
        fig.add_annotation(text="No enrichment results available.",
                           showarrow=False)
        return fig

    df = enrichment_results.head(top_n).copy()
    cols = [c for c in
            ["pathway_name", "top_level_name", "overlap_count",
             "pathway_size", "pvalue", "padj", "combined_score"]
            if c in df.columns]

    for fc in ["pvalue", "padj"]:
        if fc in df.columns:
            df[fc] = df[fc].map(lambda v: f"{v:.2e}")
    if "combined_score" in df.columns:
        df["combined_score"] = df["combined_score"].map(lambda v: f"{v:.3f}")

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[c.replace("_", " ").title() for c in cols],
            fill_color="#4a90d9",
            font=dict(color="white", size=12),
            align="left",
        ),
        cells=dict(
            values=[df[c].tolist() for c in cols],
            fill_color=[["#f7f9fc", "#eef2f8"] * (len(df) // 2 + 1)],
            align="left",
            font=dict(size=11),
        ),
    )])
    fig.update_layout(
        title="Top Enriched Pathways",
        margin=dict(t=50, l=10, r=10, b=10),
        height=min(400, 80 + len(df) * 30),
    )
    return fig
