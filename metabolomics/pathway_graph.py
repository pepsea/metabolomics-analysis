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
        """Build a directed graph for a Reactome pathway.

        Each metabolite appears exactly once (deduplicated by ChEBI ID).
        Compartment info is stored as a node attribute.

        Nodes:
            - type='metabolite': chebi_id, name, compartment, fold_change
            - type='enzyme': name, compartment
        Edges:
            - substrate -> product (direct, no intermediate reaction nodes)
            - enzyme -> product (catalyst)
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

            # Collect enzyme/catalyst nodes for this reaction
            enzyme_ids = []
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
                    enz_name_full = activity.get("displayName", "Enzyme")
                    enz_compartment = _extract_compartment(enz_name_full)
                    enz_name = _clean_name(enz_name_full)
                    cat_id = f"enz_{activity.get('stId', enz_name)}"

                    if not G.has_node(cat_id):
                        G.add_node(
                            cat_id,
                            type="enzyme",
                            name=enz_name[:40],
                            full_name=enz_name,
                            compartment=enz_compartment,
                        )
                    enzyme_ids.append(cat_id)

            # Wire edges: Met → Enz → Met (enzyme in the middle of the flow)
            if enzyme_ids:
                for inp_id in input_ids:
                    for enz_id in enzyme_ids:
                        G.add_edge(inp_id, enz_id,
                                   reaction=_clean_name(reaction_name),
                                   reaction_id=reaction_id,
                                   role="substrate")
                for enz_id in enzyme_ids:
                    for out_id in output_ids:
                        G.add_edge(enz_id, out_id,
                                   reaction=_clean_name(reaction_name),
                                   reaction_id=reaction_id,
                                   role="product")
            else:
                # No enzyme: direct substrate → product edge
                for inp_id in input_ids:
                    for out_id in output_ids:
                        if inp_id != out_id:
                            G.add_edge(
                                inp_id, out_id,
                                reaction=_clean_name(reaction_name),
                                reaction_id=reaction_id,
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


def compute_compartment_layout(G: nx.DiGraph) -> Dict[str, Tuple[float, float]]:
    """Compute a flow-based landscape layout for a pathway graph.

    Nodes are arranged left-to-right by topological depth (BFS levels).
    At each depth level, metabolites occupy vertical lanes and enzymes sit
    between their upstream metabolites and downstream metabolites at the
    same x position (or slightly offset).  Compartment backgrounds are
    drawn as bounding boxes around the nodes that belong to them.
    """
    if len(G.nodes) == 0:
        return {}, {}

    total_nodes = len(G.nodes)

    # Adaptive spacing
    if total_nodes > 40:
        x_spacing = 130
        y_spacing = 80
    elif total_nodes > 20:
        x_spacing = 160
        y_spacing = 95
    else:
        x_spacing = 180
        y_spacing = 110

    # --- Assign topological levels via BFS from source nodes ---
    # Use longest-path levels so enzymes get a mid-point depth
    level: Dict[str, int] = {}
    try:
        for node in nx.topological_sort(G):
            preds = list(G.predecessors(node))
            if not preds:
                level[node] = 0
            else:
                level[node] = max(level.get(p, 0) for p in preds) + 1
    except nx.NetworkXUnfeasible:
        # Cycle fallback: BFS from roots
        roots = [n for n in G.nodes if G.in_degree(n) == 0]
        if not roots:
            roots = list(G.nodes)[:1]
        queue = list(roots)
        for n in roots:
            level[n] = 0
        visited = set(roots)
        while queue:
            cur = queue.pop(0)
            for nxt in G.successors(cur):
                if nxt not in visited:
                    level[nxt] = level[cur] + 1
                    visited.add(nxt)
                    queue.append(nxt)
        for n in G.nodes:
            if n not in level:
                level[n] = 0

    # Group nodes by level
    levels_map: Dict[int, List[str]] = {}
    for node, lv in level.items():
        levels_map.setdefault(lv, []).append(node)

    # Within each level: metabolites first, then enzymes (so enzymes
    # appear at the same x as their immediate successors)
    positions: Dict[str, Tuple[float, float]] = {}
    for lv, nodes in sorted(levels_map.items()):
        mets = sorted([n for n in nodes if G.nodes[n].get("type") == "metabolite"])
        enzs = sorted([n for n in nodes if G.nodes[n].get("type") == "enzyme"])
        ordered = mets + enzs
        n = len(ordered)
        # Centre the column vertically
        total_height = (n - 1) * y_spacing
        y_start = -total_height / 2
        for i, node in enumerate(ordered):
            x = lv * x_spacing
            y = y_start + i * y_spacing
            positions[node] = (x, y)

    # --- Build compartment bounding boxes ---
    compartment_bounds: Dict[str, Tuple[float, float, float, float]] = {}
    pad = 30
    for node, data in G.nodes(data=True):
        comp = data.get("compartment", "cytosol")
        if node not in positions:
            continue
        x, y = positions[node]
        if comp not in compartment_bounds:
            compartment_bounds[comp] = (y, y, x, x)  # y_min, y_max, x_min, x_max
        else:
            y_min, y_max, x_min, x_max = compartment_bounds[comp]
            compartment_bounds[comp] = (
                min(y_min, y), max(y_max, y),
                min(x_min, x), max(x_max, x),
            )

    # Add padding
    compartment_bounds = {
        comp: (y_min - pad, y_max + pad, x_min - pad, x_max + pad)
        for comp, (y_min, y_max, x_min, x_max) in compartment_bounds.items()
    }

    return positions, compartment_bounds
