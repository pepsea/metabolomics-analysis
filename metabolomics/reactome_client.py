"""Reactome REST API wrapper with file-based caching."""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

REACTOME_CONTENT_BASE = "https://reactome.org/ContentService"
REACTOME_ANALYSIS_BASE = "https://reactome.org/AnalysisService"

# Rate limit: 0.2s between requests
_RATE_LIMIT_SECONDS = 0.2
# Cache TTL: 1 week
_CACHE_TTL_SECONDS = 7 * 24 * 3600


class ReactomeClient:
    """Client for Reactome Content Service and Analysis Service APIs."""

    def __init__(self, cache_dir: str = "data/cache"):
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _cache_key(self, url: str, params: Optional[dict] = None) -> str:
        """Generate a cache filename from URL and params."""
        key_str = url + (json.dumps(params, sort_keys=True) if params else "")
        return hashlib.md5(key_str.encode()).hexdigest() + ".json"

    def _cached_get(
        self, url: str, params: Optional[dict] = None, ttl_seconds: int = _CACHE_TTL_SECONDS
    ) -> Optional[dict]:
        """GET with file-based caching. Returns None on failure."""
        cache_file = self.cache_dir / self._cache_key(url, params)

        # Check cache
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < ttl_seconds:
                with open(cache_file) as f:
                    return json.load(f)

        # Fetch from API
        self._rate_limit()
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # Write cache
            with open(cache_file, "w") as f:
                json.dump(data, f)
            return data
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"[ReactomeClient] GET {url} failed: {e}")
            # Return stale cache if available
            if cache_file.exists():
                with open(cache_file) as f:
                    return json.load(f)
            return None

    def get_top_level_pathways(self, species: str = "9606") -> Optional[List[Dict]]:
        """Get all top-level pathways for a species (9606 = Homo sapiens)."""
        url = f"{REACTOME_CONTENT_BASE}/data/pathways/top/{species}"
        return self._cached_get(url)

    def get_pathway_hierarchy(self, species: str = "9606") -> Optional[List[Dict]]:
        """Get full nested event hierarchy for a species."""
        url = f"{REACTOME_CONTENT_BASE}/data/eventsHierarchy/{species}"
        return self._cached_get(url)

    def get_pathway_contained_events(self, pathway_id: str) -> Optional[List[Dict]]:
        """Get all sub-events (reactions) within a pathway."""
        url = f"{REACTOME_CONTENT_BASE}/data/pathway/{pathway_id}/containedEvents"
        return self._cached_get(url)

    def get_event_participants(self, event_id: str) -> Optional[List[Dict]]:
        """Get participating physical entities for a reaction/event."""
        url = f"{REACTOME_CONTENT_BASE}/data/event/{event_id}/participatingPhysicalEntities"
        return self._cached_get(url)

    def get_entity_component_of(self, entity_id: str) -> Optional[List[Dict]]:
        """Get pathways that contain a given entity (by dbId or stId)."""
        url = f"{REACTOME_CONTENT_BASE}/data/entity/{entity_id}/componentOf"
        return self._cached_get(url)

    def get_pathway_detail(self, pathway_id: str) -> Optional[Dict]:
        """Get detailed info about a single pathway."""
        url = f"{REACTOME_CONTENT_BASE}/data/query/{pathway_id}"
        return self._cached_get(url)

    def search_by_chebi(self, chebi_id: str) -> Optional[Dict]:
        """Search Reactome for a ChEBI identifier."""
        # Strip prefix if present
        numeric_id = chebi_id.replace("CHEBI:", "")
        url = f"{REACTOME_CONTENT_BASE}/search/query"
        params = {"query": f"CHEBI:{numeric_id}", "types": "ReferenceEntity", "cluster": "true"}
        return self._cached_get(url, params)

    def get_low_level_pathways_for_entity(
        self, entity_id: str, species: str = "Homo sapiens"
    ) -> Optional[List[Dict]]:
        """Get all lowest-level pathways containing a given entity."""
        url = f"{REACTOME_CONTENT_BASE}/data/pathways/low/entity/{entity_id}"
        params = {"species": species}
        return self._cached_get(url, params)

    def run_enrichment_analysis(
        self, identifiers: List[str], species: str = "Homo sapiens", include_disease: bool = False
    ) -> Optional[Dict]:
        """Submit ChEBI IDs for over-representation analysis via Reactome Analysis Service.

        Args:
            identifiers: List of ChEBI IDs (e.g., ["CHEBI:16947", "CHEBI:30031"]).
            species: Species name.
            include_disease: Whether to include disease pathways.

        Returns:
            Analysis result dict with 'pathways' list, or None on failure.
        """
        self._rate_limit()
        url = f"{REACTOME_ANALYSIS_BASE}/identifiers/projection"
        params = {
            "interactors": "false",
            "species": species,
            "sortBy": "ENTITIES_PVALUE",
            "order": "ASC",
            "resource": "TOTAL",
            "includeDisease": str(include_disease).lower(),
        }
        # Format: one identifier per line
        data = "\n".join(identifiers)

        cache_file = self.cache_dir / self._cache_key(url + data, params)
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < _CACHE_TTL_SECONDS:
                with open(cache_file) as f:
                    return json.load(f)

        try:
            resp = self.session.post(
                url,
                headers={"Content-Type": "text/plain"},
                params=params,
                data=data,
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
            with open(cache_file, "w") as f:
                json.dump(result, f)
            return result
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"[ReactomeClient] Enrichment analysis failed: {e}")
            if cache_file.exists():
                with open(cache_file) as f:
                    return json.load(f)
            return None

    def get_reaction_detail(self, reaction_id: str) -> Optional[Dict]:
        """Get full detail of a reaction including inputs, outputs, catalysts."""
        url = f"{REACTOME_CONTENT_BASE}/data/query/{reaction_id}"
        params = {"enhanced": "true"}
        return self._cached_get(url, params)

    def get_participants_for_pathway(self, pathway_id: str) -> Optional[Dict]:
        """Get all participating molecules for a pathway."""
        url = f"{REACTOME_CONTENT_BASE}/data/participants/{pathway_id}"
        return self._cached_get(url)
