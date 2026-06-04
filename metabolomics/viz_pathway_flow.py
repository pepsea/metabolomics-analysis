"""Pathway flow diagram visualization using Matplotlib.

Replaces the previous Plotly-based implementation to achieve reliable
compartment rendering and clearly visible arrowheads.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive; Jupyter shows via display()
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, Polygon, Rectangle
from matplotlib.colors import Normalize, to_rgba
from matplotlib.cm import ScalarMappable
import matplotlib.cm as mcm
import networkx as nx

from .pathway_graph import COMPARTMENT_COLORS, COMPARTMENT_LABELS


# ── Colour-map for fold-change ────────────────────────────────────────────────
_CMAP = mcm.RdBu_r
_NORM = Normalize(vmin=-3, vmax=3)


def _fc_color(fc):
    """Map log2 fold-change to an RGBA colour."""
    if fc is None:
        return (0.88, 0.88, 0.88, 1.0)   # light grey = unmeasured
    return _CMAP(_NORM(fc))


# ── Public wrapper ────────────────────────────────────────────────────────────
class _MplFig:
    """Thin wrapper so callers can use .show() and .write_image() as before."""

    def __init__(self, fig: plt.Figure):
        self._fig = fig

    # Jupyter: render to PNG and display as an image.
    # We force the "Agg" backend (no GUI), which disables IPython's inline
    # figure formatter — so display(fig) would print the text repr
    # "<Figure size ...>" instead of the image. Rendering to a PNG buffer and
    # displaying that via IPython.display.Image is backend-independent.
    def show(self, dpi: int = 110):
        import io
        try:
            from IPython.display import Image, display
        except ImportError:
            plt.show()
            return
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=dpi,
                          bbox_inches="tight", facecolor="white")
        plt.close(self._fig)
        buf.seek(0)
        display(Image(data=buf.getvalue()))

    # PNG / SVG export (scale maps to DPI multiplier on 100-dpi base)
    def write_image(self, path, scale: float = 1.0, **_kw):
        self._fig.savefig(str(path), dpi=int(100 * scale),
                          bbox_inches="tight", facecolor="white")

    # No-op for HTML (caller may try this for interactive export)
    def write_html(self, path, **_kw):
        png_path = str(path).rsplit(".", 1)[0] + ".png"
        self.write_image(png_path)

    @property
    def layout(self):
        w = self._fig.get_figwidth() * 100
        h = self._fig.get_figheight() * 100
        return type("_L", (), {"width": w, "height": h})()


# ── Main function ─────────────────────────────────────────────────────────────
def create_pathway_flow_diagram(
    G: Optional[nx.DiGraph],
    layout: Dict[str, Tuple[float, float]],
    pathway_name: str,
    compartment_bounds: Optional[Dict[str, Tuple[float, float, float, float]]] = None,
    ppt_mode: bool = True,
    fig_scale: float = 1.0,
) -> _MplFig:
    """Render a pathway flow diagram with Matplotlib.

    Args:
        G: NetworkX DiGraph (node attrs: type, name, compartment, fold_change).
        layout: {node_id: (x, y)} from compute_compartment_layout.
        pathway_name: Title string.
        compartment_bounds: {comp: (y_min, y_max, x_min, x_max)}.
        ppt_mode: Use larger fonts for PowerPoint.
        fig_scale: Overall size multiplier (1.0 = default).

    Returns:
        _MplFig wrapper with .show() and .write_image() methods.
    """
    # ── Empty / error state ───────────────────────────────────────────────────
    if not G or len(G.nodes) == 0 or not layout:
        fig, ax = plt.subplots(figsize=(10 * fig_scale, 4 * fig_scale))
        ax.text(0.5, 0.5,
                "No pathway graph data available.\n(Reactome API connection may be required.)",
                ha="center", va="center", fontsize=12, color="#666666",
                transform=ax.transAxes)
        ax.set_title(f"Pathway Flow: {pathway_name}", fontsize=14, pad=8)
        ax.axis("off")
        plt.tight_layout()
        return _MplFig(fig)

    # ── Font & style sizes ────────────────────────────────────────────────────
    if ppt_mode:
        MET_FONT   = 9
        ENZ_FONT   = 7
        COMP_FONT  = 9
        TITLE_FONT = 13
    else:
        MET_FONT   = 7
        ENZ_FONT   = 6
        COMP_FONT  = 7
        TITLE_FONT = 11

    # ── Layout geometry ───────────────────────────────────────────────────────
    all_x = [p[0] for p in layout.values()]
    all_y = [p[1] for p in layout.values()]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)

    x_range = max(x_max - x_min, 1)
    y_range = max(y_max - y_min, 1)

    # Padding in data units
    x_pad = x_range * 0.12 + 60
    y_pad_bot = y_range * 0.10 + 30
    y_pad_top = y_range * 0.20 + 50   # extra space for comp. labels above

    # Estimate y_spacing (min gap between nodes vertically)
    y_sorted = sorted(set(round(p[1]) for p in layout.values()))
    y_gaps = [y_sorted[i+1] - y_sorted[i] for i in range(len(y_sorted)-1)]
    y_spacing = min(y_gaps) if y_gaps else 100

    # Node sizes in data units
    # metabolite radius ≈ 28% of y_spacing; enzyme diamond half-size ≈ 12%
    met_r  = y_spacing * 0.28
    enz_hf = y_spacing * 0.12

    # ── Figure size from data aspect ratio ───────────────────────────────────
    data_w = x_range + 2 * x_pad
    data_h = y_range + y_pad_bot + y_pad_top

    base_fig_w = 12.0 * fig_scale   # inches
    fig_w = base_fig_w
    # Keep equal aspect so circles look round; cap height so dense (tall)
    # graphs stay viewable on screen instead of becoming enormous.
    fig_h = fig_w * (data_h / data_w)
    fig_h = max(3.5 * fig_scale, min(15.0 * fig_scale, fig_h))

    # ── Create figure ─────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_aspect("equal")
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad_bot, y_max + y_pad_top)
    ax.axis("off")
    ax.set_title(f"Pathway Flow: {pathway_name}",
                 fontsize=TITLE_FONT, fontweight="bold", pad=8)

    # ── Compartment backgrounds ───────────────────────────────────────────────
    if compartment_bounds:
        for comp, (cy_min, cy_max, cx_min, cx_max) in compartment_bounds.items():
            face = COMPARTMENT_COLORS.get(comp, "#F5F5F5")
            lbl  = COMPARTMENT_LABELS.get(comp, comp)
            rect = Rectangle(
                (cx_min, cy_min),
                cx_max - cx_min, cy_max - cy_min,
                facecolor=face, alpha=0.45,
                edgecolor="#999999", linewidth=0.8, linestyle="--",
                zorder=0,
            )
            ax.add_patch(rect)
            # Label just above the top edge of the box
            ax.text(
                cx_min + 6, cy_max + y_spacing * 0.08,
                lbl,
                fontsize=COMP_FONT, fontweight="bold", color="#555555",
                va="bottom", ha="left", zorder=5,
            )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _node_radius(node_id):
        """Return the visual radius of a node in data units."""
        ntype = G.nodes[node_id].get("type", "metabolite")
        return enz_hf if ntype == "enzyme" else met_r

    def _arrow(x0, y0, x1, y1, r0, r1):
        """Draw an arrow from node-edge to node-edge in data coordinates."""
        dx, dy = x1 - x0, y1 - y0
        dist = np.hypot(dx, dy)
        if dist < 1e-6:
            return
        ux, uy = dx / dist, dy / dist
        xs, ys = x0 + ux * r0, y0 + uy * r0
        xe, ye = x1 - ux * r1, y1 - uy * r1
        ax.annotate(
            "",
            xy=(xe, ye), xytext=(xs, ys),
            xycoords="data", textcoords="data",
            arrowprops=dict(
                arrowstyle="-|>",
                color="#555555",
                lw=0.7,
                mutation_scale=10,
                shrinkA=0, shrinkB=0,
            ),
            zorder=2,
        )

    # ── Edges ─────────────────────────────────────────────────────────────────
    for u, v in G.edges():
        if u not in layout or v not in layout:
            continue
        x0, y0 = layout[u]
        x1, y1 = layout[v]
        _arrow(x0, y0, x1, y1, _node_radius(u), _node_radius(v))

    # ── Metabolite nodes ──────────────────────────────────────────────────────
    met_nodes = [(n, d) for n, d in G.nodes(data=True)
                 if d.get("type") == "metabolite" and n in layout]

    # Label collision: "top center" unless node directly above is too close
    def _label_pos(n, x, y):
        above_close = any(
            0 < (layout[m][1] - y) <= y_spacing * 0.7
            for m in layout
            if abs(layout[m][0] - x) < y_spacing * 0.5 and m != n
        )
        if not above_close:
            return (x, y + met_r + y_spacing * 0.04, "center", "bottom")
        # check right side clear
        right_close = any(
            0 < (layout[m][0] - x) <= y_spacing * 0.9
            and abs(layout[m][1] - y) < y_spacing * 0.5
            for m in layout if m != n
        )
        if not right_close:
            return (x + met_r + y_spacing * 0.04, y, "left", "center")
        return (x - met_r - y_spacing * 0.04, y, "right", "center")

    for n, d in met_nodes:
        x, y = layout[n]
        fc   = d.get("fold_change")
        face = _fc_color(fc)
        edge_col = "black" if fc is not None else "#aaaaaa"
        lw = 1.2 if fc is not None else 0.6

        circ = Circle((x, y), met_r,
                       facecolor=face, edgecolor=edge_col,
                       linewidth=lw, zorder=3)
        ax.add_patch(circ)

        lx, ly, ha, va = _label_pos(n, x, y)
        ax.text(lx, ly, d.get("name", n),
                fontsize=MET_FONT, ha=ha, va=va,
                color="#111111", zorder=6,
                clip_on=True)

    # ── Enzyme nodes (small white diamond) ────────────────────────────────────
    enz_nodes = [(n, d) for n, d in G.nodes(data=True)
                 if d.get("type") == "enzyme" and n in layout]

    for n, d in enz_nodes:
        x, y = layout[n]
        h = enz_hf
        diamond = Polygon(
            [(x, y + h), (x + h, y), (x, y - h), (x - h, y)],
            closed=True,
            facecolor="white", edgecolor="black",
            linewidth=0.7, zorder=3,
        )
        ax.add_patch(diamond)
        ax.text(x, y - h - y_spacing * 0.03,
                d.get("name", n),
                fontsize=ENZ_FONT, ha="center", va="top",
                color="#444444", zorder=6, clip_on=True)

    # ── Colour-bar ────────────────────────────────────────────────────────────
    sm = ScalarMappable(cmap=_CMAP, norm=_NORM)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.45, aspect=18, pad=0.01,
                        fraction=0.03)
    cbar.set_label("log2FC", fontsize=MET_FONT + 1)
    cbar.ax.tick_params(labelsize=MET_FONT)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(facecolor="#d0d0d0", edgecolor="black",
                       linewidth=0.8, label="Metabolite (unmeasured)"),
        mpatches.Patch(facecolor=_fc_color(2.5), edgecolor="black",
                       linewidth=0.8, label="Metabolite (up-regulated)"),
        mpatches.Patch(facecolor=_fc_color(-2.5), edgecolor="black",
                       linewidth=0.8, label="Metabolite (down-regulated)"),
        mpatches.Patch(facecolor="white", edgecolor="black",
                       linewidth=0.7, label="Enzyme ◇"),
    ]
    ax.legend(handles=legend_handles, loc="upper right",
              fontsize=MET_FONT - 1, framealpha=0.8,
              handlelength=1.2, handleheight=1.0)

    plt.tight_layout()
    return _MplFig(fig)


# ── Pathway summary table (kept as Plotly for interactivity) ──────────────────
def create_pathway_summary_table(
    enrichment_results: "pd.DataFrame",
    top_n: int = 10,
) -> "go.Figure":
    """Create a summary table of top enriched pathways for selection."""
    import pandas as pd
    import plotly.graph_objects as go

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
