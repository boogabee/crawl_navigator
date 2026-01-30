#!/bin/bash
# Quick test runner script for DCSS Bot

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== DCSS Bot Test Suite ===${NC}\n"

# Activate virtual environment if available
if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment activated${NC}\n"
fi

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"
python3 -c "import pytest; import loguru; import pexpect; import blessed" && \
    echo -e "${GREEN}✓ All dependencies available${NC}\n" || \
    (echo -e "${YELLOW}✗ Missing dependencies. Run: pip install -r requirements.txt${NC}" && exit 1)

# Run compilation check
echo -e "${BLUE}Verifying Python syntax...${NC}"
python3 -m py_compile *.py tests/*.py && \
    echo -e "${GREEN}✓ All files compile${NC}\n" || exit 1

# Run tests
echo -e "${BLUE}Running test suite...${NC}"
if [ "$1" == "-v" ]; then
    pytest tests/ -v
elif [ "$1" == "-k" ]; then
    pytest tests/ -k "$2" -v
elif [ "$1" == "-m" ]; then
    pytest tests/ -m "$2" -v
else
    pytest tests/ -q
fi

echo -e "\n${GREEN}✓ Test run complete${NC}"
