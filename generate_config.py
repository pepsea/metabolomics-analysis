#!/usr/bin/env python3
"""
Generate run_config.json with customizable options
"""

import json
from datetime import datetime
import sys

def generate_config(preset="default"):
    """Generate configuration based on preset"""

    base_config = {
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

    presets = {
        "default": base_config,

        "quick": {
            **base_config,
            "time_windows": [{"name": "last_2_days", "days": 2}],
            "max_selected_per_domain": 5,
            "min_selected_per_domain": 2,
        },

        "comprehensive": {
            **base_config,
            "time_windows": [
                {"name": "last_2_days", "days": 2},
                {"name": "last_7_days", "days": 7},
                {"name": "last_30_days", "days": 30},
                {"name": "last_90_days", "days": 90}
            ],
            "max_selected_per_domain": 15,
            "min_selected_per_domain": 5,
        },

        "peer_reviewed_only": {
            **base_config,
            "source_priority": ["EuropePMC", "PubMed"],
            "require_peer_reviewed": True,
        },

        "preprints_focus": {
            **base_config,
            "source_priority": ["bioRxiv", "medRxiv", "arXiv", "EuropePMC", "PubMed"],
        },

        "metabolomics_only": {
            **base_config,
            "domains": ["Metabolomics", "Lipidomics"],
        },

        "ai_focus": {
            **base_config,
            "domains": ["AI/Agents", "Bioinformatics"],
        },

        "weekly": {
            **base_config,
            "time_windows": [{"name": "last_7_days", "days": 7}],
        },

        "monthly": {
            **base_config,
            "time_windows": [{"name": "last_30_days", "days": 30}],
            "max_selected_per_domain": 20,
        }
    }

    return presets.get(preset, base_config)


def main():
    print("Literature Radar - Configuration Generator")
    print("=" * 60)

    # Show available presets
    presets = {
        "default": "Standard configuration (2/7/30 days, all domains)",
        "quick": "Quick scan (2 days only, 5 papers max)",
        "comprehensive": "Comprehensive scan (up to 90 days, 15 papers max)",
        "peer_reviewed_only": "Only peer-reviewed journals (no preprints)",
        "preprints_focus": "Prioritize preprints (bioRxiv, medRxiv first)",
        "metabolomics_only": "Metabolomics and Lipidomics only",
        "ai_focus": "AI/Agents and Bioinformatics only",
        "weekly": "Weekly report (7 days)",
        "monthly": "Monthly report (30 days, 20 papers max)"
    }

    if len(sys.argv) > 1:
        preset = sys.argv[1]
    else:
        print("\nAvailable presets:")
        for i, (name, desc) in enumerate(presets.items(), 1):
            print(f"{i:2d}. {name:20s} - {desc}")

        print("\nEnter preset name or number (default: 1): ", end="")
        choice = input().strip()

        if not choice:
            preset = "default"
        elif choice.isdigit():
            preset_list = list(presets.keys())
            idx = int(choice) - 1
            if 0 <= idx < len(preset_list):
                preset = preset_list[idx]
            else:
                print("Invalid choice, using default")
                preset = "default"
        else:
            preset = choice

    config = generate_config(preset)

    # Save to file
    output_file = "run_config.json"
    with open(output_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ Configuration saved to {output_file}")
    print(f"  Preset: {preset}")
    print(f"  Run date: {config['run_date_utc']}")
    print(f"  Time windows: {', '.join([w['name'] for w in config['time_windows']])}")
    if "domains" in config:
        print(f"  Domains: {', '.join(config['domains'])}")
    else:
        print(f"  Domains: All (8 domains)")
    print(f"  Max papers per domain: {config['max_selected_per_domain']}")
    print("\nYou can now run:")
    print("  ./run_literature_radar.sh")


if __name__ == "__main__":
    main()
