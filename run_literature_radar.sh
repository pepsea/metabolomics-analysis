#!/bin/bash

# Literature Radar Orchestrator - Main Runner Script
# This script orchestrates the complete workflow

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONFIG_FILE="run_config.json"
FETCHED_FILE="fetched_papers.json"
OUTPUT_DIR="outputs"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  Literature Radar Orchestrator${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check if required packages are installed
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! python3 -c "import anthropic" 2>/dev/null; then
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install -r requirements.txt
fi

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY environment variable not set${NC}"
    echo ""
    echo "Please set your API key:"
    echo "  export ANTHROPIC_API_KEY='your-api-key'"
    echo ""
    echo "Or add it to a .env file:"
    echo "  echo 'ANTHROPIC_API_KEY=your-api-key' > .env"
    echo "  source .env"
    exit 1
fi

# Create default config if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}Creating default configuration...${NC}"
    python3 fetch_papers.py
fi

echo -e "${GREEN}✓ Environment ready${NC}"
echo ""

# Step 1: Fetch papers
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  Step 1: Fetching papers from academic databases${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

python3 fetch_papers.py

if [ ! -f "$FETCHED_FILE" ]; then
    echo -e "${RED}Error: Paper fetching failed - $FETCHED_FILE not created${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Papers fetched successfully${NC}"

# Count fetched papers
TOTAL_PAPERS=$(python3 -c "
import json
with open('$FETCHED_FILE', 'r') as f:
    data = json.load(f)
total = sum(len(papers) for papers in data['domains'].values())
print(total)
")

echo -e "${GREEN}  Total papers retrieved: $TOTAL_PAPERS${NC}"
echo ""

# Step 2: Process papers
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  Step 2: Processing and selecting papers with Claude${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

python3 process_papers.py

if [ ! -d "$OUTPUT_DIR" ] || [ -z "$(ls -A $OUTPUT_DIR 2>/dev/null)" ]; then
    echo -e "${RED}Error: Paper processing failed - no outputs created${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Papers processed successfully${NC}"

# Summary
echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Find the latest output files
LATEST_JSON=$(ls -t $OUTPUT_DIR/literature_radar_*.json 2>/dev/null | head -1)
LATEST_MD=$(ls -t $OUTPUT_DIR/literature_radar_*.md 2>/dev/null | head -1)

if [ -n "$LATEST_JSON" ]; then
    python3 -c "
import json

with open('$LATEST_JSON', 'r') as f:
    data = json.load(f)

print(f\"Run date: {data['run_date_utc']}\")
print(f\"Time windows: {', '.join([w['name'] for w in data['time_windows']])}\")
print(\"\")
print(\"Selected papers by domain:\")

total_selected = 0
for domain in data['domains']:
    selected = len(domain.get('selected', []))
    retrieved = domain['stats']['retrieved']
    total_selected += selected
    print(f\"  {domain['domain']:20s}: {selected:2d} / {retrieved:3d} papers\")

print(\"\")
print(f\"Total selected: {total_selected} papers\")
"

    echo ""
    echo -e "${GREEN}✓ Complete!${NC}"
    echo ""
    echo -e "Output files:"
    echo -e "  JSON: ${YELLOW}$LATEST_JSON${NC}"
    echo -e "  Markdown: ${YELLOW}$LATEST_MD${NC}"
    echo ""
    echo "Next steps:"
    echo "  - Review the report: open $LATEST_MD"
    echo "  - Share with your team"
    echo "  - Schedule next run (daily/weekly)"
    echo ""
else
    echo -e "${RED}Error: No output files found${NC}"
fi
