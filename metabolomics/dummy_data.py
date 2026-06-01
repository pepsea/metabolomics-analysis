"""Generate synthetic metabolomics datasets with known pathway perturbations."""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Hand-curated catalog of well-known metabolites with ChEBI IDs.
# Grouped by metabolic category for injecting pathway-specific perturbations.
METABOLITE_CATALOG = [
    # --- Amino acids (15) --- (using Reactome-specific charged ChEBI IDs)
    {"chebi_id": "CHEBI:57972", "name": "L-alanine", "category": "amino_acid", "pathways": ["Amino acid metabolism"]},
    {"chebi_id": "CHEBI:29985", "name": "L-glutamate", "category": "amino_acid", "pathways": ["Amino acid metabolism", "TCA cycle"]},
    {"chebi_id": "CHEBI:58359", "name": "L-glutamine", "category": "amino_acid", "pathways": ["Amino acid metabolism"]},
    {"chebi_id": "CHEBI:57427", "name": "L-leucine", "category": "amino_acid", "pathways": ["Amino acid metabolism", "Branched-chain amino acid metabolism"]},
    {"chebi_id": "CHEBI:57762", "name": "L-valine", "category": "amino_acid", "pathways": ["Amino acid metabolism", "Branched-chain amino acid metabolism"]},
    {"chebi_id": "CHEBI:58045", "name": "L-isoleucine", "category": "amino_acid", "pathways": ["Amino acid metabolism", "Branched-chain amino acid metabolism"]},
    {"chebi_id": "CHEBI:57844", "name": "L-methionine", "category": "amino_acid", "pathways": ["Amino acid metabolism", "Methionine cycle"]},
    {"chebi_id": "CHEBI:58095", "name": "L-phenylalanine", "category": "amino_acid", "pathways": ["Amino acid metabolism"]},
    {"chebi_id": "CHEBI:57912", "name": "L-tryptophan", "category": "amino_acid", "pathways": ["Amino acid metabolism", "Tryptophan metabolism"]},
    {"chebi_id": "CHEBI:57524", "name": "L-serine", "category": "amino_acid", "pathways": ["Amino acid metabolism"]},
    {"chebi_id": "CHEBI:57926", "name": "L-threonine", "category": "amino_acid", "pathways": ["Amino acid metabolism"]},
    {"chebi_id": "CHEBI:57305", "name": "Glycine", "category": "amino_acid", "pathways": ["Amino acid metabolism"]},
    {"chebi_id": "CHEBI:32682", "name": "L-arginine", "category": "amino_acid", "pathways": ["Amino acid metabolism", "Urea cycle"]},
    {"chebi_id": "CHEBI:57576", "name": "L-lysine", "category": "amino_acid", "pathways": ["Amino acid metabolism"]},
    {"chebi_id": "CHEBI:29991", "name": "L-aspartate", "category": "amino_acid", "pathways": ["Amino acid metabolism", "Urea cycle", "TCA cycle"]},

    # --- TCA cycle intermediates (10) ---
    {"chebi_id": "CHEBI:16947", "name": "Citrate", "category": "tca_cycle", "pathways": ["TCA cycle"]},
    {"chebi_id": "CHEBI:15562", "name": "Isocitrate", "category": "tca_cycle", "pathways": ["TCA cycle"]},
    {"chebi_id": "CHEBI:16810", "name": "2-Oxoglutarate", "category": "tca_cycle", "pathways": ["TCA cycle"]},
    {"chebi_id": "CHEBI:57292", "name": "Succinyl-CoA", "category": "tca_cycle", "pathways": ["TCA cycle"]},
    {"chebi_id": "CHEBI:30031", "name": "Succinate", "category": "tca_cycle", "pathways": ["TCA cycle"]},
    {"chebi_id": "CHEBI:29806", "name": "Fumarate", "category": "tca_cycle", "pathways": ["TCA cycle", "Urea cycle"]},
    {"chebi_id": "CHEBI:15589", "name": "L-Malate", "category": "tca_cycle", "pathways": ["TCA cycle"]},
    {"chebi_id": "CHEBI:16452", "name": "Oxaloacetate", "category": "tca_cycle", "pathways": ["TCA cycle", "Gluconeogenesis"]},
    {"chebi_id": "CHEBI:57288", "name": "Acetyl-CoA", "category": "tca_cycle", "pathways": ["TCA cycle", "Fatty acid oxidation"]},
    {"chebi_id": "CHEBI:16526", "name": "CO2", "category": "tca_cycle", "pathways": ["TCA cycle"]},

    # --- Glycolysis intermediates (10) --- (Reactome charged forms)
    {"chebi_id": "CHEBI:58225", "name": "Glucose-6-phosphate", "category": "glycolysis", "pathways": ["Glycolysis", "Pentose phosphate pathway"]},
    {"chebi_id": "CHEBI:57634", "name": "Fructose-6-phosphate", "category": "glycolysis", "pathways": ["Glycolysis"]},
    {"chebi_id": "CHEBI:32966", "name": "Fructose-1,6-bisphosphate", "category": "glycolysis", "pathways": ["Glycolysis"]},
    {"chebi_id": "CHEBI:59776", "name": "Glyceraldehyde-3-phosphate", "category": "glycolysis", "pathways": ["Glycolysis", "Pentose phosphate pathway"]},
    {"chebi_id": "CHEBI:57642", "name": "Dihydroxyacetone phosphate", "category": "glycolysis", "pathways": ["Glycolysis"]},
    {"chebi_id": "CHEBI:58272", "name": "3-Phosphoglycerate", "category": "glycolysis", "pathways": ["Glycolysis"]},
    {"chebi_id": "CHEBI:58289", "name": "2-Phosphoglycerate", "category": "glycolysis", "pathways": ["Glycolysis"]},
    {"chebi_id": "CHEBI:58702", "name": "Phosphoenolpyruvate", "category": "glycolysis", "pathways": ["Glycolysis", "Gluconeogenesis"]},
    {"chebi_id": "CHEBI:15361", "name": "Pyruvate", "category": "glycolysis", "pathways": ["Glycolysis", "TCA cycle"]},
    {"chebi_id": "CHEBI:24996", "name": "Lactate", "category": "glycolysis", "pathways": ["Glycolysis"]},

    # --- Nucleotides (8) --- (Reactome charged forms)
    {"chebi_id": "CHEBI:30616", "name": "ATP", "category": "nucleotide", "pathways": ["Purine metabolism", "Energy metabolism"]},
    {"chebi_id": "CHEBI:456216", "name": "ADP", "category": "nucleotide", "pathways": ["Purine metabolism", "Energy metabolism"]},
    {"chebi_id": "CHEBI:456215", "name": "AMP", "category": "nucleotide", "pathways": ["Purine metabolism"]},
    {"chebi_id": "CHEBI:37565", "name": "GTP", "category": "nucleotide", "pathways": ["Purine metabolism"]},
    {"chebi_id": "CHEBI:58223", "name": "UDP", "category": "nucleotide", "pathways": ["Pyrimidine metabolism"]},
    {"chebi_id": "CHEBI:46398", "name": "UTP", "category": "nucleotide", "pathways": ["Pyrimidine metabolism"]},
    {"chebi_id": "CHEBI:37563", "name": "CTP", "category": "nucleotide", "pathways": ["Pyrimidine metabolism"]},
    {"chebi_id": "CHEBI:16708", "name": "Adenine", "category": "nucleotide", "pathways": ["Purine metabolism"]},

    # --- Lipids / Fatty acids (10) ---
    {"chebi_id": "CHEBI:15756", "name": "Palmitic acid", "category": "lipid", "pathways": ["Fatty acid metabolism"]},
    {"chebi_id": "CHEBI:17268", "name": "Myristic acid", "category": "lipid", "pathways": ["Fatty acid metabolism"]},
    {"chebi_id": "CHEBI:30823", "name": "Stearic acid", "category": "lipid", "pathways": ["Fatty acid metabolism"]},
    {"chebi_id": "CHEBI:17351", "name": "Oleic acid", "category": "lipid", "pathways": ["Fatty acid metabolism"]},
    {"chebi_id": "CHEBI:17553", "name": "Linoleic acid", "category": "lipid", "pathways": ["Fatty acid metabolism", "Linoleic acid metabolism"]},
    {"chebi_id": "CHEBI:28842", "name": "Arachidonic acid", "category": "lipid", "pathways": ["Fatty acid metabolism", "Arachidonic acid metabolism"]},
    {"chebi_id": "CHEBI:16113", "name": "Cholesterol", "category": "lipid", "pathways": ["Cholesterol biosynthesis"]},
    {"chebi_id": "CHEBI:17855", "name": "Triglyceride", "category": "lipid", "pathways": ["Lipid metabolism"]},
    {"chebi_id": "CHEBI:64583", "name": "Sphingomyelin", "category": "lipid", "pathways": ["Sphingolipid metabolism"]},
    {"chebi_id": "CHEBI:17544", "name": "Ceramide", "category": "lipid", "pathways": ["Sphingolipid metabolism"]},

    # --- Urea cycle (5) ---
    {"chebi_id": "CHEBI:16199", "name": "Urea", "category": "urea_cycle", "pathways": ["Urea cycle"]},
    {"chebi_id": "CHEBI:18012", "name": "Citrulline", "category": "urea_cycle", "pathways": ["Urea cycle"]},
    {"chebi_id": "CHEBI:15729", "name": "Ornithine", "category": "urea_cycle", "pathways": ["Urea cycle"]},
    {"chebi_id": "CHEBI:32682", "name": "Argininosuccinate", "category": "urea_cycle", "pathways": ["Urea cycle"]},
    {"chebi_id": "CHEBI:58048", "name": "L-asparagine", "category": "urea_cycle", "pathways": ["Urea cycle"]},

    # --- Pentose phosphate pathway (5) --- (Reactome charged forms)
    {"chebi_id": "CHEBI:58759", "name": "6-Phosphogluconate", "category": "pentose_phosphate", "pathways": ["Pentose phosphate pathway"]},
    {"chebi_id": "CHEBI:58121", "name": "Ribulose-5-phosphate", "category": "pentose_phosphate", "pathways": ["Pentose phosphate pathway"]},
    {"chebi_id": "CHEBI:58273", "name": "Ribose-5-phosphate", "category": "pentose_phosphate", "pathways": ["Pentose phosphate pathway"]},
    {"chebi_id": "CHEBI:57737", "name": "Xylulose-5-phosphate", "category": "pentose_phosphate", "pathways": ["Pentose phosphate pathway"]},
    {"chebi_id": "CHEBI:58467", "name": "Erythrose-4-phosphate", "category": "pentose_phosphate", "pathways": ["Pentose phosphate pathway"]},

    # --- Cofactors and vitamins (7) --- (Reactome charged forms)
    {"chebi_id": "CHEBI:57540", "name": "NAD+", "category": "cofactor", "pathways": ["NAD metabolism", "Energy metabolism"]},
    {"chebi_id": "CHEBI:57945", "name": "NADH", "category": "cofactor", "pathways": ["NAD metabolism", "Energy metabolism"]},
    {"chebi_id": "CHEBI:58349", "name": "NADP+", "category": "cofactor", "pathways": ["NADP metabolism"]},
    {"chebi_id": "CHEBI:57783", "name": "NADPH", "category": "cofactor", "pathways": ["NADP metabolism"]},
    {"chebi_id": "CHEBI:57692", "name": "FAD", "category": "cofactor", "pathways": ["Riboflavin metabolism"]},
    {"chebi_id": "CHEBI:57287", "name": "Coenzyme A", "category": "cofactor", "pathways": ["Pantothenate metabolism"]},
    {"chebi_id": "CHEBI:16240", "name": "Hydrogen peroxide", "category": "cofactor", "pathways": ["Reactive oxygen species metabolism"]},

    # --- Bile acids (6) ---
    {"chebi_id": "CHEBI:29747", "name": "Cholic acid", "category": "bile_acid", "pathways": ["Bile acid metabolism"]},
    {"chebi_id": "CHEBI:36278", "name": "Chenodeoxycholic acid", "category": "bile_acid", "pathways": ["Bile acid metabolism"]},
    {"chebi_id": "CHEBI:9403", "name": "Taurocholic acid", "category": "bile_acid", "pathways": ["Bile acid metabolism"]},
    {"chebi_id": "CHEBI:36274", "name": "Glycocholic acid", "category": "bile_acid", "pathways": ["Bile acid metabolism"]},
    {"chebi_id": "CHEBI:16755", "name": "Deoxycholic acid", "category": "bile_acid", "pathways": ["Bile acid metabolism"]},
    {"chebi_id": "CHEBI:9411", "name": "Taurine", "category": "bile_acid", "pathways": ["Bile acid metabolism", "Amino acid metabolism"]},

    # --- Carnitines (5) ---
    {"chebi_id": "CHEBI:17126", "name": "L-Carnitine", "category": "carnitine", "pathways": ["Carnitine metabolism"]},
    {"chebi_id": "CHEBI:57321", "name": "Acetylcarnitine", "category": "carnitine", "pathways": ["Carnitine metabolism"]},
    {"chebi_id": "CHEBI:77637", "name": "Palmitoylcarnitine", "category": "carnitine", "pathways": ["Carnitine metabolism", "Fatty acid oxidation"]},
    {"chebi_id": "CHEBI:72558", "name": "Stearoylcarnitine", "category": "carnitine", "pathways": ["Carnitine metabolism", "Fatty acid oxidation"]},
    {"chebi_id": "CHEBI:73024", "name": "Oleoylcarnitine", "category": "carnitine", "pathways": ["Carnitine metabolism", "Fatty acid oxidation"]},

    # --- Organic acids (6) ---
    {"chebi_id": "CHEBI:30769", "name": "Creatinine", "category": "organic_acid", "pathways": ["Creatine metabolism"]},
    {"chebi_id": "CHEBI:16919", "name": "Creatine", "category": "organic_acid", "pathways": ["Creatine metabolism"]},
    {"chebi_id": "CHEBI:30839", "name": "Hippuric acid", "category": "organic_acid", "pathways": ["Benzoate metabolism"]},
    {"chebi_id": "CHEBI:30797", "name": "Indole-3-acetic acid", "category": "organic_acid", "pathways": ["Tryptophan metabolism"]},
    {"chebi_id": "CHEBI:16737", "name": "Creatine phosphate", "category": "organic_acid", "pathways": ["Creatine metabolism"]},
    {"chebi_id": "CHEBI:15603", "name": "L-Leucic acid", "category": "organic_acid", "pathways": ["Branched-chain amino acid metabolism"]},

    # --- Sugars and sugar alcohols (6) ---
    {"chebi_id": "CHEBI:17234", "name": "Glucose", "category": "sugar", "pathways": ["Glycolysis", "Gluconeogenesis"]},
    {"chebi_id": "CHEBI:28757", "name": "Fructose", "category": "sugar", "pathways": ["Fructose metabolism"]},
    {"chebi_id": "CHEBI:17659", "name": "Galactose", "category": "sugar", "pathways": ["Galactose metabolism"]},
    {"chebi_id": "CHEBI:16899", "name": "Sorbitol", "category": "sugar", "pathways": ["Polyol pathway"]},
    {"chebi_id": "CHEBI:16646", "name": "Myo-inositol", "category": "sugar", "pathways": ["Inositol phosphate metabolism"]},
    {"chebi_id": "CHEBI:17118", "name": "D-Ribose", "category": "sugar", "pathways": ["Pentose phosphate pathway"]},

    # --- Biogenic amines (6) ---
    {"chebi_id": "CHEBI:18243", "name": "Dopamine", "category": "biogenic_amine", "pathways": ["Catecholamine biosynthesis"]},
    {"chebi_id": "CHEBI:28790", "name": "Serotonin", "category": "biogenic_amine", "pathways": ["Tryptophan metabolism"]},
    {"chebi_id": "CHEBI:18357", "name": "Norepinephrine", "category": "biogenic_amine", "pathways": ["Catecholamine biosynthesis"]},
    {"chebi_id": "CHEBI:33568", "name": "Epinephrine", "category": "biogenic_amine", "pathways": ["Catecholamine biosynthesis"]},
    {"chebi_id": "CHEBI:18295", "name": "Histamine", "category": "biogenic_amine", "pathways": ["Histidine metabolism"]},
    {"chebi_id": "CHEBI:57947", "name": "L-DOPA", "category": "biogenic_amine", "pathways": ["Catecholamine biosynthesis"]},
]

# Mapping from pathway names used in the catalog to categories
PATHWAY_CATEGORIES = {
    "TCA cycle": "tca_cycle",
    "Glycolysis": "glycolysis",
    "Fatty acid metabolism": "lipid",
    "Fatty acid oxidation": "lipid",
    "Urea cycle": "urea_cycle",
    "Pentose phosphate pathway": "pentose_phosphate",
    "Amino acid metabolism": "amino_acid",
    "Purine metabolism": "nucleotide",
    "Pyrimidine metabolism": "nucleotide",
    "Sphingolipid metabolism": "lipid",
    "Cholesterol biosynthesis": "lipid",
    "Branched-chain amino acid metabolism": "amino_acid",
}


def get_metabolite_catalog() -> pd.DataFrame:
    """Return the full catalog of curated metabolites as a DataFrame."""
    df = pd.DataFrame(METABOLITE_CATALOG)
    # Deduplicate by chebi_id (keep first occurrence)
    df = df.drop_duplicates(subset="chebi_id", keep="first").reset_index(drop=True)
    return df


def _get_metabolites_for_pathway(pathway_name: str) -> List[str]:
    """Return list of ChEBI IDs belonging to a named pathway."""
    return [
        m["chebi_id"]
        for m in METABOLITE_CATALOG
        if pathway_name in m.get("pathways", [])
    ]


def generate_dummy_dataset(
    n_control: int = 10,
    n_treatment: int = 10,
    perturbed_pathways: Optional[List[str]] = None,
    perturbation_fold_change: float = 2.0,
    noise_level: float = 0.3,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Generate a synthetic metabolomics dataset with known pathway perturbations.

    Args:
        n_control: Number of control samples.
        n_treatment: Number of treatment samples.
        perturbed_pathways: List of pathway names to perturb (e.g. ["TCA cycle", "Glycolysis"]).
        perturbation_fold_change: Fold-change to inject for perturbed metabolites.
        noise_level: Standard deviation of log-normal noise.
        seed: Random seed for reproducibility.

    Returns:
        data: DataFrame (samples x metabolites), columns are ChEBI IDs.
        metadata: DataFrame with sample_id and group columns.
        ground_truth: Dict mapping pathway_name -> list of perturbed ChEBI IDs.
    """
    if perturbed_pathways is None:
        perturbed_pathways = ["TCA cycle", "Glycolysis", "Amino acid metabolism"]

    rng = np.random.default_rng(seed)

    catalog = get_metabolite_catalog()
    chebi_ids = catalog["chebi_id"].tolist()
    n_metabolites = len(chebi_ids)
    n_total = n_control + n_treatment

    # Generate base abundances (log-normal)
    log_means = rng.uniform(6, 12, size=n_metabolites)
    data = np.zeros((n_total, n_metabolites))
    for j in range(n_metabolites):
        data[:, j] = rng.lognormal(mean=log_means[j], sigma=noise_level, size=n_total)

    # Identify perturbed metabolites and inject fold-changes in treatment group
    ground_truth = {}
    for pathway in perturbed_pathways:
        perturbed_ids = _get_metabolites_for_pathway(pathway)
        ground_truth[pathway] = perturbed_ids
        for chebi_id in perturbed_ids:
            if chebi_id in chebi_ids:
                j = chebi_ids.index(chebi_id)
                # Apply fold-change to treatment samples with some variation
                fc_variation = rng.normal(
                    np.log2(perturbation_fold_change), 0.3, size=n_treatment
                )
                data[n_control:, j] *= 2 ** fc_variation

    # Build DataFrames
    sample_ids = [f"CTRL_{i+1:03d}" for i in range(n_control)] + [
        f"TREAT_{i+1:03d}" for i in range(n_treatment)
    ]
    groups = ["control"] * n_control + ["treatment"] * n_treatment

    data_df = pd.DataFrame(data, columns=chebi_ids, index=sample_ids)
    data_df.index.name = "sample_id"

    metadata_df = pd.DataFrame(
        {"sample_id": sample_ids, "group": groups}
    )

    return data_df, metadata_df, ground_truth
