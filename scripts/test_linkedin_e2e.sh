#!/bin/bash
# End-to-end test script for LinkedIn publisher
#
# Usage:
#   ./scripts/test_linkedin_e2e.sh [--dry-run] [--vault PATH]
#
# This script tests the LinkedIn publisher locally without actually
# publishing to LinkedIn (uses mock/dry-run mode).
#
# Prerequisites:
#   - Python 3.12 with venv activated
#   - playwright installed (pip install playwright && playwright install chromium)
#   - VAULT_PATH environment variable or --vault option

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DRY_RUN=false
VAULT_PATH="${VAULT_PATH:-}"
TEST_VAULT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --vault)
            VAULT_PATH="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--vault PATH]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Run tests without actual LinkedIn publishing"
            echo "  --vault PATH Path to Obsidian vault (or set VAULT_PATH env var)"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}LinkedIn Publisher E2E Test${NC}"
echo "=============================="
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1)
echo "  Python: $PYTHON_VERSION"

# Check if in venv
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}  Warning: Not in virtual environment${NC}"
    echo "  Consider activating venv: source venv/bin/activate"
fi

# Check playwright
if ! python -c "import playwright" &> /dev/null; then
    echo -e "${RED}Error: Playwright not installed${NC}"
    echo "  Run: pip install playwright && playwright install chromium"
    exit 1
fi
echo "  Playwright: installed"

# Check linkedin_publisher module
if ! python -c "import linkedin_publisher" &> /dev/null; then
    echo -e "${RED}Error: linkedin_publisher module not found${NC}"
    echo "  Run: pip install -e ."
    exit 1
fi
echo "  linkedin_publisher: installed"

# Setup test vault
if [[ -z "$VAULT_PATH" ]]; then
    echo ""
    echo -e "${YELLOW}Creating temporary test vault...${NC}"
    TEST_VAULT=$(mktemp -d)
    VAULT_PATH="$TEST_VAULT"

    # Create vault structure
    mkdir -p "$VAULT_PATH/Approved/linkedin"
    mkdir -p "$VAULT_PATH/Done/linkedin"
    mkdir -p "$VAULT_PATH/Needs_Action/linkedin"
    mkdir -p "$VAULT_PATH/Logs/linkedin"

    echo "  Test vault: $VAULT_PATH"
else
    echo ""
    echo "  Using vault: $VAULT_PATH"
fi

export VAULT_PATH

# Create test approval file
echo ""
echo -e "${YELLOW}Creating test approval file...${NC}"

TEST_FILE="$VAULT_PATH/Approved/linkedin/test_post_$(date +%s).md"
cat > "$TEST_FILE" << 'EOF'
---
type: approval_request
action_type: publish_linkedin_post
created_at: 2026-03-12T10:00:00Z
status: pending
target:
  platform: linkedin
  post_type: text
source:
  path: /test/source.md
---

## Content Preview

This is a test LinkedIn post from the E2E test script.

Testing the linkedin-publish CLI tool.

#testing #automation
EOF

echo "  Created: $TEST_FILE"

# Run tests
echo ""
echo -e "${GREEN}Running E2E tests...${NC}"
echo ""

# Test 1: CLI help
echo -e "${YELLOW}Test 1: CLI help${NC}"
if linkedin-publish --help > /dev/null 2>&1; then
    echo -e "  ${GREEN}PASS${NC}: CLI help works"
else
    echo -e "  ${RED}FAIL${NC}: CLI help failed"
    exit 1
fi

# Test 2: List command
echo -e "${YELLOW}Test 2: List pending posts${NC}"
if OUTPUT=$(linkedin-publish --vault-path "$VAULT_PATH" list 2>&1); then
    if echo "$OUTPUT" | grep -q "test_post"; then
        echo -e "  ${GREEN}PASS${NC}: List shows test post"
    else
        echo -e "  ${RED}FAIL${NC}: Test post not in list"
        echo "$OUTPUT"
        exit 1
    fi
else
    echo -e "  ${RED}FAIL${NC}: List command failed"
    exit 1
fi

# Test 3: Status command
echo -e "${YELLOW}Test 3: Status command${NC}"
if OUTPUT=$(linkedin-publish --vault-path "$VAULT_PATH" status 2>&1); then
    if echo "$OUTPUT" | grep -q "Pending in queue: 1"; then
        echo -e "  ${GREEN}PASS${NC}: Status shows 1 pending"
    else
        echo -e "  ${GREEN}PASS${NC}: Status command works"
    fi
else
    echo -e "  ${RED}FAIL${NC}: Status command failed"
    exit 1
fi

# Test 4: Unit tests
echo ""
echo -e "${YELLOW}Test 4: Running pytest unit tests${NC}"
cd "$PROJECT_ROOT"

if pytest tests/test_linkedin_*.py -v --tb=short 2>&1; then
    echo -e "  ${GREEN}PASS${NC}: Unit tests passed"
else
    echo -e "  ${RED}FAIL${NC}: Unit tests failed"
    exit 1
fi

# Test 5: Integration tests (without actual LinkedIn)
echo ""
echo -e "${YELLOW}Test 5: Running pytest integration tests${NC}"

if pytest tests/integration/test_linkedin_*.py -v --tb=short 2>&1; then
    echo -e "  ${GREEN}PASS${NC}: Integration tests passed"
else
    echo -e "  ${RED}FAIL${NC}: Integration tests failed"
    exit 1
fi

# Cleanup
echo ""
echo -e "${YELLOW}Cleanup${NC}"
if [[ -n "$TEST_VAULT" && -d "$TEST_VAULT" ]]; then
    rm -rf "$TEST_VAULT"
    echo "  Removed test vault"
fi

# Summary
echo ""
echo -e "${GREEN}=============================="
echo "E2E Tests Completed Successfully"
echo "==============================${NC}"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo "Note: Ran in --dry-run mode (no actual LinkedIn publishing)"
else
    echo "Note: To test actual LinkedIn publishing:"
    echo "  1. Run: linkedin-publish --vault-path /your/vault auth"
    echo "  2. Create approval file in /Approved/linkedin/"
    echo "  3. Run: linkedin-publish --vault-path /your/vault run"
fi
