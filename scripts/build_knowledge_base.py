#!/usr/bin/env python3
"""Build the local Reactome knowledge base by querying the Reactome API.

This script fetches the pathway hierarchy and metabolite-pathway mappings
from Reactome's Content Service, then saves them as a local JSON file.

Usage:
    python scripts/build_knowledge_base.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from metabolomics.reactome_client import ReactomeClient
from metabolomics.knowledge_base import KnowledgeBase


def _extract_chebi_ids_from_participants(participants: list) -> list:
    """Extract ChEBI IDs from Reactome participant entities."""
    chebi_ids = []
    if not participants:
        return chebi_ids

    for participant in participants:
        # Navigate through different entity types
        chebi_id = _find_chebi_in_entity(participant)
        if chebi_id:
            chebi_ids.append(chebi_id)
    return chebi_ids


def _find_chebi_in_entity(entity: dict) -> str | None:
    """Recursively find ChEBI ID in a Reactome entity dict."""
    if not isinstance(entity, dict):
        return None

    # Check for direct ChEBI reference
    ref = entity.get("referenceEntity")
    if ref:
        db_name = ref.get("databaseName", "")
        identifier = ref.get("identifier", "")
        if db_name == "ChEBI" and identifier:
            return f"CHEBI:{identifier}"

    # Check crossReference field
    for xref in entity.get("crossReference", []):
        if xref.get("databaseName") == "ChEBI":
            return f"CHEBI:{xref.get('identifier', '')}"

    # Check members of complex/set entities
    for member in entity.get("hasMember", []):
        result = _find_chebi_in_entity(member)
        if result:
            return result

    for component in entity.get("hasComponent", []):
        result = _find_chebi_in_entity(component)
        if result:
            return result

    return None


def build_pathway_hierarchy(client: ReactomeClient) -> tuple[dict, dict]:
    """Build the pathway hierarchy tree and pathway details dict.

    Returns:
        (hierarchy_dict, pathway_details_dict)
    """
    print("[Build] Fetching pathway hierarchy...")
    hierarchy_raw = client.get_pathway_hierarchy()
    if not hierarchy_raw:
        print("[Build] ERROR: Failed to fetch pathway hierarchy.")
        return {}, {}

    pathway_details = {}
    hierarchy = {}

    def _process_node(node: dict, parent_id: str = "", parent_name: str = "",
                      top_level_id: str = "", top_level_name: str = "", level: int = 0):
        st_id = node.get("stId", "")
        name = node.get("name", "")
        node_type = node.get("type", "")

        # Only process Pathway nodes (not Reaction, etc.)
        if node_type not in ("Pathway", "TopLevelPathway"):
            return

        if level == 0:
            top_level_id = st_id
            top_level_name = name

        pathway_details[st_id] = {
            "name": name,
            "parent_id": parent_id,
            "parent_name": parent_name,
            "top_level_id": top_level_id,
            "top_level_name": top_level_name,
            "level": level,
            "type": node_type,
        }

        if level == 0:
            hierarchy[st_id] = {"name": name, "children": {}}

        children = node.get("children", [])
        for child in children:
            _process_node(
                child,
                parent_id=st_id,
                parent_name=name,
                top_level_id=top_level_id,
                top_level_name=top_level_name,
                level=level + 1,
            )

    for top_node in hierarchy_raw:
        _process_node(top_node)

    print(f"[Build] Found {len(pathway_details)} pathways in {len(hierarchy)} top-level categories.")
    return hierarchy, pathway_details


def build_metabolite_pathway_map(
    client: ReactomeClient, pathway_details: dict
) -> dict[str, list[str]]:
    """Map ChEBI IDs to pathways by querying Reactome for each pathway's participants.

    Strategy: Query the lowest-level pathways (leaves with no children that are pathways)
    for their participating molecules, extract ChEBI IDs.
    """
    metabolite_pathway_map: dict[str, list[str]] = {}

    # Find leaf pathways (those not referenced as parent by any other pathway)
    parent_ids = {d.get("parent_id") for d in pathway_details.values() if d.get("parent_id")}
    leaf_pathways = [pid for pid in pathway_details if pid not in parent_ids]

    # Limit to metabolism-related pathways for efficiency
    metabolism_pathways = [
        pid for pid in leaf_pathways
        if pathway_details[pid].get("top_level_name", "") in (
            "Metabolism",
            "Metabolism of proteins",
            "Signal Transduction",
            "Immune System",
            "Hemostasis",
            "Transport of small molecules",
            "Neuronal System",
        )
    ]

    # If too few, use all leaf pathways
    if len(metabolism_pathways) < 50:
        metabolism_pathways = leaf_pathways

    print(f"[Build] Querying {len(metabolism_pathways)} leaf pathways for metabolite participants...")

    for i, pid in enumerate(metabolism_pathways):
        if i % 50 == 0:
            print(f"[Build] Progress: {i}/{len(metabolism_pathways)} pathways...")

        participants = client.get_participants_for_pathway(pid)
        if not participants:
            continue

        chebi_ids = set()
        if isinstance(participants, list):
            for entry in participants:
                if isinstance(entry, dict):
                    for ref in entry.get("refEntities", []):
                        schema = ref.get("schemaClass", "")
                        identifier = ref.get("identifier", "")
                        st_id = ref.get("stId", "")
                        # ReferenceMolecule with chebi stId or numeric identifier
                        if schema == "ReferenceMolecule" and identifier:
                            chebi_ids.add(f"CHEBI:{identifier}")
                        elif st_id.startswith("chebi:"):
                            chebi_ids.add(f"CHEBI:{st_id.split(':')[1]}")

        for chebi_id in chebi_ids:
            if chebi_id not in metabolite_pathway_map:
                metabolite_pathway_map[chebi_id] = []
            if pid not in metabolite_pathway_map[chebi_id]:
                metabolite_pathway_map[chebi_id].append(pid)

            # Also add ancestor pathways
            current = pid
            while current:
                parent = pathway_details.get(current, {}).get("parent_id", "")
                if parent and parent in pathway_details:
                    if parent not in metabolite_pathway_map[chebi_id]:
                        metabolite_pathway_map[chebi_id].append(parent)
                    current = parent
                else:
                    break

    print(f"[Build] Mapped {len(metabolite_pathway_map)} unique metabolites to pathways.")
    return metabolite_pathway_map


def main():
    print("=" * 60)
    print("Building Reactome Knowledge Base")
    print("=" * 60)

    client = ReactomeClient(cache_dir=str(project_root / "data" / "cache"))
    kb = KnowledgeBase(data_dir=str(project_root / "data"))

    # Step 1: Build hierarchy
    hierarchy, pathway_details = build_pathway_hierarchy(client)
    if not pathway_details:
        print("[Build] FATAL: No pathways found. Check network connectivity.")
        sys.exit(1)

    kb.pathway_hierarchy = hierarchy
    kb.pathway_details = pathway_details

    # Step 2: Build metabolite-pathway mappings
    metabolite_map = build_metabolite_pathway_map(client, pathway_details)
    kb.metabolite_pathway_map = metabolite_map

    # Step 3: Save
    kb.save()

    # Step 4: Print summary
    summary = kb.summary()
    print("\n" + "=" * 60)
    print("Knowledge Base Summary:")
    print(f"  Top-level categories: {summary['top_level_categories']}")
    print(f"  Total pathways:       {summary['total_pathways']}")
    print(f"  Mapped metabolites:   {summary['total_metabolites']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
