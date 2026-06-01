"""Local knowledge base mapping ChEBI IDs to Reactome pathways."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Default data directory relative to project root
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class KnowledgeBase:
    """Manages the local mapping of ChEBI IDs to Reactome pathways and hierarchy."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self.pathway_hierarchy: Dict = {}  # nested dict of pathway tree
        self.metabolite_pathway_map: Dict[str, List[str]] = {}  # chebi_id -> [pathway_ids]
        self.pathway_details: Dict[str, Dict] = {}  # pathway_id -> {name, parent, top_level, ...}
        self._loaded = False

    @property
    def kb_file(self) -> Path:
        return self.data_dir / "reactome_metabolite_pathways.json"

    def load(self) -> bool:
        """Load bundled knowledge base from JSON. Returns True if successful."""
        if not self.kb_file.exists():
            print(f"[KnowledgeBase] File not found: {self.kb_file}")
            return False

        with open(self.kb_file) as f:
            data = json.load(f)

        self.pathway_hierarchy = data.get("pathway_hierarchy", {})
        self.metabolite_pathway_map = data.get("metabolite_pathway_map", {})
        self.pathway_details = data.get("pathway_details", {})
        self._loaded = True
        return True

    def save(self) -> None:
        """Save current knowledge base to JSON."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "pathway_hierarchy": self.pathway_hierarchy,
            "metabolite_pathway_map": self.metabolite_pathway_map,
            "pathway_details": self.pathway_details,
        }
        with open(self.kb_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[KnowledgeBase] Saved to {self.kb_file}")

    def get_pathways_for_metabolite(self, chebi_id: str) -> List[Dict]:
        """Return all pathways containing this metabolite."""
        pathway_ids = self.metabolite_pathway_map.get(chebi_id, [])
        return [
            {"pathway_id": pid, **self.pathway_details.get(pid, {"name": pid})}
            for pid in pathway_ids
        ]

    def get_all_metabolites_in_pathway(self, pathway_id: str) -> List[str]:
        """Return all ChEBI IDs associated with a pathway."""
        return [
            chebi_id
            for chebi_id, pathways in self.metabolite_pathway_map.items()
            if pathway_id in pathways
        ]

    def get_background_metabolite_count(self) -> int:
        """Total number of unique metabolites in the knowledge base."""
        return len(self.metabolite_pathway_map)

    def get_all_pathway_ids(self) -> List[str]:
        """Return all pathway IDs in the knowledge base."""
        return list(self.pathway_details.keys())

    def get_pathway_name(self, pathway_id: str) -> str:
        """Get display name for a pathway."""
        return self.pathway_details.get(pathway_id, {}).get("name", pathway_id)

    def get_top_level_for_pathway(self, pathway_id: str) -> Optional[str]:
        """Get the top-level category name for a pathway."""
        detail = self.pathway_details.get(pathway_id, {})
        top_id = detail.get("top_level_id")
        if top_id:
            return self.pathway_details.get(top_id, {}).get("name", top_id)
        return detail.get("top_level_name")

    def get_hierarchy_for_treemap(self) -> pd.DataFrame:
        """Return a flat table suitable for Plotly treemap.

        Columns: id, name, parent_name, top_level_name, level, metabolite_count
        """
        rows = []
        for pid, detail in self.pathway_details.items():
            n_metabolites = len(self.get_all_metabolites_in_pathway(pid))
            if n_metabolites == 0:
                continue
            rows.append({
                "id": pid,
                "name": detail.get("name", pid),
                "parent_name": detail.get("parent_name", ""),
                "top_level_name": detail.get("top_level_name", ""),
                "level": detail.get("level", 0),
                "metabolite_count": n_metabolites,
            })

        if not rows:
            return pd.DataFrame(columns=["id", "name", "parent_name", "top_level_name", "level", "metabolite_count"])
        return pd.DataFrame(rows)

    def summary(self) -> Dict:
        """Return summary statistics about the knowledge base."""
        return {
            "total_metabolites": len(self.metabolite_pathway_map),
            "total_pathways": len(self.pathway_details),
            "top_level_categories": len(self.pathway_hierarchy),
            "loaded": self._loaded,
        }
