#!/usr/bin/env python3
"""
Literature Radar - Paper Fetching Script
Fetches papers from multiple sources for omics/bioinformatics domains
"""

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import os
from urllib.parse import quote_plus

# Configuration
CONFIG_FILE = "run_config.json"
OUTPUT_FILE = "fetched_papers.json"

# API endpoints
EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
BIORXIV_BASE = "https://api.biorxiv.org/details/biorxiv"
MEDRXIV_BASE = "https://api.biorxiv.org/details/medrxiv"
ARXIV_BASE = "http://export.arxiv.org/api/query"

# Default domain queries
DEFAULT_QUERIES = {
    "Metabolomics": '(metabolomics OR metabolome OR "metabolic profiling" OR "LC-MS metabolomics" OR "GC-MS" OR "isotope tracing" OR fluxomics OR "single-cell metabolomics" OR "spatial metabolomics" OR "metabolite annotation")',
    "Lipidomics": '(lipidomics OR lipidome OR "shotgun lipidomics" OR "lipid isomer" OR "ion mobility" OR "oxidized lipids" OR "lipid signaling" OR "imaging mass spectrometry")',
    "Proteomics": '(proteomics OR DIA OR "data-independent acquisition" OR "single-cell proteomics" OR phosphoproteomics OR PTM OR "cross-linking mass spectrometry" OR "protein inference")',
    "Transcriptomics": '(transcriptomics OR scRNA-seq OR "single-cell RNA-seq" OR "spatial transcriptomics" OR Perturb-seq OR "long-read RNA" OR isoform OR "RNA velocity")',
    "Genomics": '(genomics OR "long-read sequencing" OR "structural variant" OR pangenome OR "single-cell multiome" OR "CRISPR screen" OR "GWAS fine-mapping")',
    "Bioinformatics": '(bioinformatics OR "multi-omics integration" OR "batch correction" OR "causal inference" OR "network biology" OR "pathway activity" OR "variant interpretation" OR benchmark)',
    "AI/Agents": '((LLM OR "large language model" OR agent OR "tool use" OR RAG OR "retrieval-augmented" OR autonomous OR "scientific discovery") AND (biology OR omics OR biomedical OR "drug discovery"))',
    "Disease Mechanism": '(("disease mechanism" OR pathogenesis OR causal OR endotype OR "cell-cell interaction" OR microenvironment OR immune OR fibrosis OR neurodegeneration OR "metabolic disease") AND (omics OR "single-cell" OR "multi-omics"))'
}


class PaperFetcher:
    def __init__(self, config: Dict):
        self.config = config
        self.run_date = datetime.strptime(config["run_date_utc"], "%Y-%m-%d")
        self.queries = config.get("query_dictionary", DEFAULT_QUERIES)
        self.results = {domain: [] for domain in self.queries.keys()}

    def calculate_date_range(self, days: int) -> tuple:
        """Calculate date range for query"""
        date_to = self.run_date
        date_from = date_to - timedelta(days=days)
        return date_from, date_to

    def fetch_europepmc(self, query: str, date_from: datetime, date_to: datetime, limit: int = 100) -> List[Dict]:
        """Fetch from Europe PMC"""
        print(f"  [EuropePMC] Searching...")
        papers = []

        try:
            date_from_str = date_from.strftime("%Y-%m-%d")
            date_to_str = date_to.strftime("%Y-%m-%d")

            # Europe PMC query format
            full_query = f'{query} AND (FIRST_PDATE:[{date_from_str} TO {date_to_str}])'

            params = {
                "query": full_query,
                "format": "json",
                "pageSize": min(limit, 1000),
                "cursorMark": "*",
                "synonym": "true"
            }

            response = requests.get(EUROPEPMC_BASE, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "resultList" in data and "result" in data["resultList"]:
                for item in data["resultList"]["result"]:
                    paper = {
                        "title": item.get("title", "Untitled") or "Untitled",
                        "authors": item.get("authorString", ""),
                        "date": item.get("firstPublicationDate", ""),
                        "venue": item.get("journalTitle", item.get("bookTitle", "")),
                        "doi": item.get("doi"),
                        "pmid": item.get("pmid"),
                        "pmcid": item.get("pmcid"),
                        "arxiv_id": None,
                        "link": f"https://europepmc.org/article/MED/{item.get('pmid', '')}" if item.get("pmid") else "",
                        "abstract": item.get("abstractText", ""),
                        "source": "EuropePMC",
                        "source_id": item.get("id", "")
                    }
                    papers.append(paper)

            print(f"    Found {len(papers)} papers")

        except Exception as e:
            print(f"    Error: {e}")

        return papers

    def fetch_pubmed(self, query: str, date_from: datetime, date_to: datetime, limit: int = 100) -> List[Dict]:
        """Fetch from PubMed"""
        print(f"  [PubMed] Searching...")
        papers = []

        try:
            # Step 1: Search for PMIDs
            date_from_str = date_from.strftime("%Y/%m/%d")
            date_to_str = date_to.strftime("%Y/%m/%d")

            search_query = f'{query} AND ("{date_from_str}"[PDAT] : "{date_to_str}"[PDAT])'

            search_params = {
                "db": "pubmed",
                "term": search_query,
                "retmax": limit,
                "retmode": "json",
                "sort": "pub_date"
            }

            search_response = requests.get(f"{PUBMED_BASE}/esearch.fcgi", params=search_params, timeout=30)
            search_response.raise_for_status()
            search_data = search_response.json()

            pmids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmids:
                print(f"    Found 0 papers")
                return papers

            # Step 2: Fetch details
            time.sleep(0.34)  # NCBI rate limit

            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml"
            }

            fetch_response = requests.get(f"{PUBMED_BASE}/efetch.fcgi", params=fetch_params, timeout=60)
            fetch_response.raise_for_status()

            # Parse XML
            root = ET.fromstring(fetch_response.content)

            for article in root.findall(".//PubmedArticle"):
                try:
                    medline = article.find(".//MedlineCitation")
                    pmid = medline.find(".//PMID").text if medline.find(".//PMID") is not None else None

                    article_node = medline.find(".//Article")
                    title_node = article_node.find(".//ArticleTitle") if article_node is not None else None
                    title = title_node.text if title_node is not None and title_node.text else "Untitled"

                    # Abstract
                    abstract_texts = article_node.findall(".//AbstractText")
                    abstract = " ".join([a.text for a in abstract_texts if a.text]) if abstract_texts else ""

                    # Authors
                    authors_list = article_node.findall(".//Author")
                    authors = ", ".join([
                        f"{a.find('.//LastName').text} {a.find('.//Initials').text}"
                        for a in authors_list
                        if a.find('.//LastName') is not None and a.find('.//Initials') is not None
                    ])

                    # Journal
                    journal = article_node.find(".//Journal/Title")
                    venue = journal.text if journal is not None else ""

                    # Date
                    pub_date = article_node.find(".//Journal/JournalIssue/PubDate")
                    year = pub_date.find(".//Year").text if pub_date.find(".//Year") is not None else ""
                    month = pub_date.find(".//Month").text if pub_date.find(".//Month") is not None else "01"
                    day = pub_date.find(".//Day").text if pub_date.find(".//Day") is not None else "01"

                    # Convert month name to number if needed
                    month_map = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "May": "05", "Jun": "06",
                                 "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"}
                    month = month_map.get(month, month) if month in month_map else (month if month.isdigit() else "01")

                    date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}" if year else ""

                    # DOI
                    doi_node = article.find(".//ArticleId[@IdType='doi']")
                    doi = doi_node.text if doi_node is not None else None

                    paper = {
                        "title": title,
                        "authors": authors,
                        "date": date_str,
                        "venue": venue,
                        "doi": doi,
                        "pmid": pmid,
                        "pmcid": None,
                        "arxiv_id": None,
                        "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                        "abstract": abstract,
                        "source": "PubMed",
                        "source_id": pmid
                    }
                    papers.append(paper)

                except Exception as e:
                    print(f"    Error parsing article: {e}")
                    continue

            print(f"    Found {len(papers)} papers")

        except Exception as e:
            print(f"    Error: {e}")

        return papers

    def fetch_biorxiv_medrxiv(self, query: str, date_from: datetime, date_to: datetime, server: str = "biorxiv", limit: int = 100) -> List[Dict]:
        """Fetch from bioRxiv or medRxiv"""
        print(f"  [{server}] Searching...")
        papers = []

        try:
            base_url = BIORXIV_BASE if server == "biorxiv" else MEDRXIV_BASE
            date_from_str = date_from.strftime("%Y-%m-%d")
            date_to_str = date_to.strftime("%Y-%m-%d")

            # bioRxiv API uses date range endpoint
            url = f"{base_url}/{date_from_str}/{date_to_str}/0/json"

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "collection" in data:
                for item in data["collection"]:
                    # Simple keyword matching (API doesn't support query)
                    title_abstract = (item.get("title", "") + " " + item.get("abstract", "")).lower()
                    query_terms = query.lower().replace("(", "").replace(")", "").replace('"', "").split(" or ")
                    query_terms = [t.strip() for t in query_terms if t.strip() and t.strip() != "and"]

                    # Check if any query term appears
                    if not any(term in title_abstract for term in query_terms if len(term) > 3):
                        continue

                    paper = {
                        "title": item.get("title", ""),
                        "authors": item.get("authors", ""),
                        "date": item.get("date", ""),
                        "venue": server,
                        "doi": item.get("doi"),
                        "pmid": None,
                        "pmcid": None,
                        "arxiv_id": None,
                        "link": f"https://www.{server}.org/content/{item.get('doi', '')}v1",
                        "abstract": item.get("abstract", ""),
                        "source": server,
                        "source_id": item.get("doi", "")
                    }
                    papers.append(paper)

                    if len(papers) >= limit:
                        break

            print(f"    Found {len(papers)} papers")

        except Exception as e:
            print(f"    Error: {e}")

        return papers

    def fetch_arxiv(self, query: str, date_from: datetime, date_to: datetime, limit: int = 100) -> List[Dict]:
        """Fetch from arXiv"""
        print(f"  [arXiv] Searching...")
        papers = []

        try:
            # arXiv query - add biology/bioinformatics categories
            categories = "(cat:q-bio.* OR cat:cs.AI OR cat:cs.LG OR cat:stat.ML)"
            search_query = f"({query}) AND {categories}"

            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }

            response = requests.get(ARXIV_BASE, params=params, timeout=30)
            response.raise_for_status()

            # Parse Atom XML
            root = ET.fromstring(response.content)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                published = entry.find("atom:published", ns)
                if published is not None:
                    pub_date = datetime.strptime(published.text[:10], "%Y-%m-%d")
                    if not (date_from <= pub_date <= date_to):
                        continue

                title_node = entry.find("atom:title", ns)
                title = title_node.text.replace("\n", " ").strip() if title_node is not None else ""

                summary_node = entry.find("atom:summary", ns)
                abstract = summary_node.text.replace("\n", " ").strip() if summary_node is not None else ""

                authors = ", ".join([
                    a.find("atom:name", ns).text
                    for a in entry.findall("atom:author", ns)
                    if a.find("atom:name", ns) is not None
                ])

                arxiv_id_node = entry.find("atom:id", ns)
                arxiv_id = arxiv_id_node.text.split("/abs/")[-1] if arxiv_id_node is not None else ""

                doi_node = entry.find("arxiv:doi", ns)
                doi = doi_node.text if doi_node is not None else None

                paper = {
                    "title": title,
                    "authors": authors,
                    "date": pub_date.strftime("%Y-%m-%d") if published is not None else "",
                    "venue": "arXiv",
                    "doi": doi,
                    "pmid": None,
                    "pmcid": None,
                    "arxiv_id": arxiv_id,
                    "link": f"https://arxiv.org/abs/{arxiv_id}",
                    "abstract": abstract,
                    "source": "arXiv",
                    "source_id": arxiv_id
                }
                papers.append(paper)

            print(f"    Found {len(papers)} papers")

        except Exception as e:
            print(f"    Error: {e}")

        return papers

    def deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """Remove duplicate papers based on identifiers and title similarity"""
        seen_ids = set()
        seen_titles = {}
        unique_papers = []

        for paper in papers:
            # Check identifiers
            ids = []
            if paper.get("doi"):
                ids.append(("doi", paper["doi"].lower()))
            if paper.get("pmid"):
                ids.append(("pmid", paper["pmid"]))
            if paper.get("arxiv_id"):
                ids.append(("arxiv", paper["arxiv_id"]))

            # Check if we've seen this ID
            id_match = False
            for id_type, id_val in ids:
                if (id_type, id_val) in seen_ids:
                    id_match = True
                    break

            if id_match:
                continue

            # Check title similarity (simple normalized match)
            # Skip if title is None or empty
            if not paper.get("title"):
                continue

            normalized_title = paper["title"].lower().strip()[:100]
            if normalized_title in seen_titles:
                # Merge sources
                existing = seen_titles[normalized_title]
                if paper["source"] not in existing.get("sources", []):
                    existing.setdefault("sources", [existing["source"]]).append(paper["source"])
                continue

            # Add to unique set
            for id_type, id_val in ids:
                seen_ids.add((id_type, id_val))
            seen_titles[normalized_title] = paper

            # Normalize source field to list
            paper["sources"] = [paper["source"]]
            unique_papers.append(paper)

        return unique_papers

    def fetch_domain(self, domain: str) -> None:
        """Fetch papers for a single domain across all time windows"""
        print(f"\n{'='*60}")
        print(f"Domain: {domain}")
        print(f"{'='*60}")

        query = self.queries.get(domain, "")
        if not query:
            print(f"No query defined for {domain}")
            return

        all_papers = []

        for window in self.config["time_windows"]:
            window_name = window["name"]
            days = window["days"]

            print(f"\nTime window: {window_name} ({days} days)")

            date_from, date_to = self.calculate_date_range(days)
            print(f"Date range: {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}")

            window_papers = []

            for source in self.config.get("source_priority", ["EuropePMC", "PubMed"]):
                if source == "EuropePMC":
                    papers = self.fetch_europepmc(query, date_from, date_to)
                elif source == "PubMed":
                    papers = self.fetch_pubmed(query, date_from, date_to)
                elif source == "bioRxiv":
                    papers = self.fetch_biorxiv_medrxiv(query, date_from, date_to, "biorxiv")
                elif source == "medRxiv":
                    papers = self.fetch_biorxiv_medrxiv(query, date_from, date_to, "medrxiv")
                elif source == "arXiv":
                    papers = self.fetch_arxiv(query, date_from, date_to)
                else:
                    continue

                # Tag with window
                for p in papers:
                    p["window"] = window_name

                window_papers.extend(papers)
                time.sleep(0.5)  # Rate limiting

            all_papers.extend(window_papers)
            print(f"Total for {window_name}: {len(window_papers)} papers")

        # Deduplicate
        unique_papers = self.deduplicate_papers(all_papers)
        print(f"\nTotal unique papers for {domain}: {len(unique_papers)}")

        self.results[domain] = unique_papers

    def run(self) -> Dict:
        """Run fetcher for all domains"""
        domains = self.config.get("domains", list(self.queries.keys()))

        for domain in domains:
            self.fetch_domain(domain)
            time.sleep(1)  # Rate limiting between domains

        return {
            "run_date_utc": self.config["run_date_utc"],
            "fetch_timestamp": datetime.utcnow().isoformat(),
            "config": self.config,
            "domains": self.results
        }


def main():
    # Load configuration
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found")
        print("Creating default configuration...")

        default_config = {
            "run_date_utc": datetime.utcnow().strftime("%Y-%m-%d"),
            "time_windows": [
                {"name": "last_2_days", "days": 2},
                {"name": "last_7_days", "days": 7},
                {"name": "last_30_days", "days": 30}
            ],
            "max_selected_per_domain": 10,
            "min_selected_per_domain": 3,
            "source_priority": ["EuropePMC", "PubMed", "bioRxiv", "medRxiv", "arXiv"],
            "strict_sources_only": True,
            "require_peer_reviewed": False,
            "include_review_articles": False,
            "novelty_lookback_days": 90,
            "output_detail_level": "standard"
        }

        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=2)

        print(f"Created {CONFIG_FILE}")
        return

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    print("Literature Radar - Paper Fetcher")
    print("="*60)
    print(f"Run date: {config['run_date_utc']}")
    print(f"Output file: {OUTPUT_FILE}")
    print("="*60)

    # Run fetcher
    fetcher = PaperFetcher(config)
    results = fetcher.run()

    # Save results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Results saved to {OUTPUT_FILE}")
    print(f"{'='*60}")

    # Summary
    print("\nSummary:")
    for domain, papers in results["domains"].items():
        print(f"  {domain}: {len(papers)} papers")


if __name__ == "__main__":
    main()
