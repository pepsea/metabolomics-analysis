"""Build directed pathway graphs from Reactome reaction data."""

import re
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from .reactome_client import ReactomeClient

# Ubiquitous metabolites to collapse/hide (they appear in nearly every reaction)
UBIQUITOUS_CHEBI_IDS = {
    "CHEBI:15377",  # H2O (water)
    "CHEBI:15378",  # H+ (hydron)
    "CHEBI:30616",  # ATP(4-)
    "CHEBI:456216", # ADP(3-)
    "CHEBI:456215", # AMP(2-)
    "CHEBI:15422",  # ATP (generic)
    "CHEBI:16761",  # ADP (generic)
    "CHEBI:16027",  # AMP (generic)
    "CHEBI:57540",  # NAD(1-)
    "CHEBI:57945",  # NADH(2-)
    "CHEBI:58349",  # NADP(3-)
    "CHEBI:57783",  # NADPH(4-)
    "CHEBI:57692",  # FAD(3-)
    "CHEBI:58307",  # FADH2
    "CHEBI:57287",  # CoA(4-)
    "CHEBI:17154",  # Coenzyme A (generic)
    "CHEBI:16526",  # CO2
    "CHEBI:43474",  # Pi (hydrogenphosphate)
    "CHEBI:33019",  # PPi (pyrophosphate)
    "CHEBI:18420",  # Mg2+
    "CHEBI:29103",  # K+
}

# Canonical compartment ordering (outside → inside cell)
COMPARTMENT_ORDER = [
    "extracellular region",
    "plasma membrane",
    "cytosol",
    "endoplasmic reticulum membrane",
    "endoplasmic reticulum lumen",
    "Golgi membrane",
    "Golgi lumen",
    "mitochondrial outer membrane",
    "mitochondrial intermembrane space",
    "mitochondrial inner membrane",
    "mitochondrial matrix",
    "peroxisomal matrix",
    "nuclear envelope",
    "nucleoplasm",
]

# Short display labels for compartments
COMPARTMENT_LABELS = {
    "extracellular region": "Extracellular",
    "plasma membrane": "Plasma Membrane",
    "cytosol": "Cytosol",
    "endoplasmic reticulum membrane": "ER Membrane",
    "endoplasmic reticulum lumen": "ER Lumen",
    "Golgi membrane": "Golgi Membrane",
    "Golgi lumen": "Golgi Lumen",
    "mitochondrial outer membrane": "Mito. Outer Membrane",
    "mitochondrial intermembrane space": "Mito. IMS",
    "mitochondrial inner membrane": "Mito. Inner Membrane",
    "mitochondrial matrix": "Mitochondrial Matrix",
    "peroxisomal matrix": "Peroxisome",
    "nuclear envelope": "Nuclear Envelope",
    "nucleoplasm": "Nucleoplasm",
}

# Colors for compartments
COMPARTMENT_COLORS = {
    "extracellular region": "#E8F5E9",
    "plasma membrane": "#C8E6C9",
    "cytosol": "#FFF8E1",
    "endoplasmic reticulum membrane": "#E3F2FD",
    "endoplasmic reticulum lumen": "#BBDEFB",
    "Golgi membrane": "#F3E5F5",
    "Golgi lumen": "#E1BEE7",
    "mitochondrial outer membrane": "#FBE9E7",
    "mitochondrial intermembrane space": "#FFCCBC",
    "mitochondrial inner membrane": "#FF8A65",
    "mitochondrial matrix": "#FFE0B2",
    "peroxisomal matrix": "#F0F4C3",
    "nuclear envelope": "#D7CCC8",
    "nucleoplasm": "#EFEBE9",
}


def _extract_compartment(display_name: str) -> str:
    """Extract compartment from Reactome display name like 'pyruvate [cytosol]'."""
    match = re.search(r'\[([^\]]+)\]', display_name)
    return match.group(1) if match else "cytosol"


def _clean_name(display_name: str) -> str:
    """Remove compartment bracket and trim from display name."""
    name = re.sub(r'\s*\[.*?\]\s*$', '', display_name).strip()
    return name


class PathwayGraphBuilder:
    """Build NetworkX directed graphs from Reactome pathway data."""

    def __init__(self, client: ReactomeClient):
        self.client = client

    def build_pathway_graph(
        self,
        pathway_id: str,
        metabolite_fc: Optional[Dict[str, float]] = None,
        hide_ubiquitous: bool = True,
    ) -> Optional[nx.DiGraph]:
        """Build a metabolite-only directed flow graph for a Reactome pathway.

        The flow is represented purely by metabolites: for each reaction,
        every substrate is connected directly to every product. Enzymes are
        NOT nodes — the catalysing enzyme name is stored on the edge so it
        can be shown on hover.

        Nodes (all type='metabolite'):
            chebi_id, name, full_name, compartment, fold_change
        Edges (substrate -> product):
            reaction, reaction_id, enzyme  (enzyme = catalyst name, may be "")
        """
        events = self.client.get_pathway_contained_events(pathway_id)
        if not events:
            return None

        G = nx.DiGraph()

        for event in events:
            if isinstance(event, int):
                event = self.client.get_reaction_detail(str(event))
                if not event or not isinstance(event, dict):
                    continue

            schema_class = event.get("schemaClass", "")
            if schema_class not in ("Reaction", "BlackBoxEvent"):
                continue

            reaction_id = event.get("stId", "")
            reaction_name = event.get("displayName", "Unknown reaction")

            detail = self.client.get_reaction_detail(reaction_id)
            if not detail:
                continue

            # Collect input and output node IDs for this reaction
            input_ids = []
            output_ids = []

            for inp in detail.get("input", []):
                if isinstance(inp, int):
                    inp = self.client.get_reaction_detail(str(inp))
                    if not inp or not isinstance(inp, dict):
                        continue
                node_id = self._add_entity_node(
                    G, inp, metabolite_fc, hide_ubiquitous
                )
                if node_id:
                    input_ids.append(node_id)

            for out in detail.get("output", []):
                if isinstance(out, int):
                    out = self.client.get_reaction_detail(str(out))
                    if not out or not isinstance(out, dict):
                        continue
                node_id = self._add_entity_node(
                    G, out, metabolite_fc, hide_ubiquitous
                )
                if node_id:
                    output_ids.append(node_id)

            # Collect catalysing enzyme name(s) — stored on edges, not as nodes
            enzyme_names = []
            for cat in detail.get("catalystActivity", []):
                activity = cat.get("physicalEntity")
                if not activity:
                    cat_dbid = cat.get("dbId")
                    if cat_dbid:
                        cat_detail = self.client.get_reaction_detail(str(cat_dbid))
                        if cat_detail:
                            activity = cat_detail.get("physicalEntity")

                if activity:
                    if isinstance(activity, int):
                        activity = self.client.get_reaction_detail(str(activity))
                    if not activity or not isinstance(activity, dict):
                        continue
                    enzyme_names.append(_clean_name(activity.get("displayName", "Enzyme")))

            enzyme_label = ", ".join(dict.fromkeys(enzyme_names))  # dedup, keep order

            # Metabolite-only flow: connect each substrate directly to each product
            for inp_id in input_ids:
                for out_id in output_ids:
                    if inp_id != out_id:
                        G.add_edge(
                            inp_id, out_id,
                            reaction=_clean_name(reaction_name),
                            reaction_id=reaction_id,
                            enzyme=enzyme_label,
                        )

        # Remove isolated nodes
        isolated = list(nx.isolates(G))
        G.remove_nodes_from(isolated)

        return G if len(G.nodes) > 0 else None

    def _add_entity_node(
        self,
        G: nx.DiGraph,
        entity: dict,
        metabolite_fc: Optional[Dict[str, float]],
        hide_ubiquitous: bool,
    ) -> Optional[str]:
        """Add a metabolite node. Returns node_id or None if skipped."""
        display_name = entity.get("displayName", "Unknown")
        st_id = entity.get("stId", display_name)

        # Extract compartment and clean name
        compartment = _extract_compartment(display_name)
        clean = _clean_name(display_name)

        # Try to extract ChEBI ID from referenceEntity
        chebi_id = None
        ref = entity.get("referenceEntity")
        if ref:
            if ref.get("databaseName") == "ChEBI":
                chebi_id = f"CHEBI:{ref.get('identifier', '')}"

        # If no referenceEntity in the reaction response, query entity detail
        if not chebi_id and st_id and st_id.startswith("R-"):
            entity_detail = self.client.get_reaction_detail(st_id)
            if entity_detail:
                ref = entity_detail.get("referenceEntity")
                if ref and ref.get("databaseName") == "ChEBI":
                    chebi_id = f"CHEBI:{ref.get('identifier', '')}"

        if hide_ubiquitous and chebi_id and chebi_id in UBIQUITOUS_CHEBI_IDS:
            return None

        # Node ID = ChEBI ID + compartment so the same molecule in different
        # compartments gets separate nodes (important for transport reactions).
        if chebi_id:
            node_id = f"{chebi_id}_{compartment}" if compartment else chebi_id
        else:
            node_id = f"met_{st_id}"

        fc = None
        if metabolite_fc and chebi_id:
            fc = metabolite_fc.get(chebi_id)

        if not G.has_node(node_id):
            G.add_node(
                node_id,
                type="metabolite",
                name=clean[:35],
                full_name=clean,
                chebi_id=chebi_id or "",
                compartment=compartment,
                fold_change=fc,
            )

        return node_id

    def simplify_graph(self, G: nx.DiGraph, max_nodes: int = 60) -> nx.DiGraph:
        """Simplify graph by removing isolated nodes and limiting size."""
        isolated = list(nx.isolates(G))
        G.remove_nodes_from(isolated)

        if len(G.nodes) <= max_nodes:
            return G

        # Keep metabolites with highest connectivity
        degree_sorted = sorted(G.degree(), key=lambda x: x[1], reverse=True)
        keep_nodes = {n for n, _ in degree_sorted[:max_nodes]}

        for node, _ in degree_sorted[:max_nodes // 2]:
            keep_nodes.update(G.neighbors(node))
            keep_nodes.update(G.predecessors(node))

        keep_list = list(keep_nodes)[:max_nodes]
        return G.subgraph(keep_list).copy()


def compute_compartment_layout(G: nx.DiGraph):
    """Compute a compartment-banded, left-to-right flow layout.

    Design (metabolite-only flow):
      * x = topological depth (BFS longest-path) → flow runs left to right.
      * y = compartment band. Each compartment becomes a horizontal band,
        stacked top-to-bottom in canonical (outside → inside) order. Bands
        never overlap.
      * Within a (compartment, depth) cell, multiple metabolites stack
        vertically, centred in the band.

    Returns:
        (positions, compartment_bounds)
        positions: {node_id: (x, y)}
        compartment_bounds: {compartment: (y_min, y_max, x_min, x_max)}
            — full-width horizontal bands.
    """
    from collections import defaultdict, deque

    if len(G.nodes) == 0:
        return {}, {}

    n_total = len(G.nodes)
    if n_total > 40:
        x_spacing, y_spacing = 170, 72
    elif n_total > 20:
        x_spacing, y_spacing = 200, 88
    else:
        x_spacing, y_spacing = 240, 104

    # --- Topological depth (longest path from a source) ---
    level: Dict[str, int] = {}
    try:
        for node in nx.topological_sort(G):
            preds = list(G.predecessors(node))
            level[node] = 0 if not preds else max(level.get(p, 0) for p in preds) + 1
    except nx.NetworkXUnfeasible:
        roots = [n for n in G.nodes if G.in_degree(n) == 0] or [next(iter(G.nodes))]
        dq = deque(roots)
        for r in roots:
            level[r] = 0
        seen = set(roots)
        while dq:
            cur = dq.popleft()
            for s in G.successors(cur):
                if s not in seen:
                    level[s] = level[cur] + 1
                    seen.add(s)
                    dq.append(s)
        for n in G.nodes:
            level.setdefault(n, 0)

    depths = sorted(set(level.values()))
    max_depth = max(depths) if depths else 0

    # --- Compartments present, in canonical order ---
    comps = list({G.nodes[n].get("compartment", "cytosol") for n in G.nodes})

    def _ckey(c):
        try:
            return COMPARTMENT_ORDER.index(c)
        except ValueError:
            return 999
    comps.sort(key=_ckey)

    # --- Nodes per (compartment, depth) cell ---
    cell: Dict[Tuple[str, int], List[str]] = defaultdict(list)
    for n in G.nodes:
        c = G.nodes[n].get("compartment", "cytosol")
        cell[(c, level[n])].append(n)

    # Rows each band needs = max nodes in any single depth column of that band
    band_rows = {
        c: max([len(cell[(c, d)]) for d in depths] + [1]) for c in comps
    }

    # --- Assign positions, stacking bands downward ---
    positions: Dict[str, Tuple[float, float]] = {}
    compartment_bounds: Dict[str, Tuple[float, float, float, float]] = {}

    x_left = -x_spacing * 0.45
    x_right = max_depth * x_spacing + x_spacing * 0.45
    gap_between_bands = y_spacing * 0.7
    band_pad = y_spacing * 0.45

    cur_top = 0.0
    for c in comps:
        rows = band_rows[c]
        band_height = (rows - 1) * y_spacing
        band_top = cur_top
        band_bottom = cur_top - band_height
        band_center = (band_top + band_bottom) / 2.0

        for d in depths:
            grp = sorted(cell[(c, d)])
            k = len(grp)
            if k == 0:
                continue
            sub_h = (k - 1) * y_spacing
            y0 = band_center + sub_h / 2.0
            for i, node in enumerate(grp):
                positions[node] = (d * x_spacing, y0 - i * y_spacing)

        compartment_bounds[c] = (
            band_bottom - band_pad,   # y_min
            band_top + band_pad,      # y_max
            x_left,                   # x_min
            x_right,                  # x_max
        )
        cur_top = band_bottom - gap_between_bands

    return positions, compartment_bounds
