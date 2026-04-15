#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

################################################################################
# LLM Claims Analysis Pipeline - Run Script
#
# This script starts the development servers:
# 1. Detects and activates the virtual environment
# 2. Starts Flask backend server (port 5000)
# 3. Starts Vite frontend dev server (port 3000)
################################################################################

# Error handler - runs when script fails
error_handler() {
    echo ""
    echo "========================================" >&2
    echo "ERROR: Setup failed at line $1" >&2
    echo "========================================" >&2
    echo ""
    echo "Press Enter to close..."
    read -p ""
    exit 1
}

# Trap errors
trap 'error_handler $LINENO' ERR

# set -e  # Exit on error

# Get script directory and change to it
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Script location: $SCRIPT_DIR"
echo "📍 Running from: $(pwd)"
echo ""

cd "$SCRIPT_DIR"
echo "✓ Changed to script directory"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

################################################################################
# VENV DETECTION LOGIC (identical in setup.sh and run.sh)
################################################################################

echo "🔍 Detecting virtual environment..."
echo ""

# Configure Analytics venv location (edit this path if different)
ANALYTICS_VENV="/path_to_environment/.venv"

# Priority 1: Already activated venv
if [ -n "$VIRTUAL_ENV" ]; then
    VENV_DIR="$VIRTUAL_ENV"
    echo -e "${GREEN}✓${NC} Using already activated venv: ${CYAN}$VENV_DIR${NC}"
    VENV_ALREADY_ACTIVE=true

# Priority 2: Environment variable override
elif [ -n "$LLM_VENV_PATH" ]; then
    VENV_DIR="$LLM_VENV_PATH"
    echo -e "${GREEN}✓${NC} Using venv from LLM_VENV_PATH: ${CYAN}$VENV_DIR${NC}"
    VENV_ALREADY_ACTIVE=false

# Priority 3: Analytics venv exists
elif [ -d "$ANALYTICS_VENV" ]; then
    VENV_DIR="$ANALYTICS_VENV"
    echo -e "${GREEN}✓${NC} Found Analytics venv: ${CYAN}$VENV_DIR${NC}"
    VENV_ALREADY_ACTIVE=false

# Priority 4: Local venv
else
    VENV_DIR="$SCRIPT_DIR/.venv"
    echo -e "${CYAN}ℹ${NC} Using local venv: ${CYAN}$VENV_DIR${NC}"
    VENV_ALREADY_ACTIVE=false
fi

################################################################################
# END VENV DETECTION LOGIC
################################################################################

# Check if venv exists
if [ ! -f "$VENV_DIR/bin/python" ] && [ ! -f "$VENV_DIR/Scripts/python.exe" ]; then
    echo -e "${RED}✗${NC} Virtual environment not found at: ${CYAN}$VENV_DIR${NC}"
    echo ""
    echo -e "${YELLOW}Please run setup first:${NC}"
    echo -e "  ${CYAN}./setup.sh${NC}"
    echo ""
    exit 1
fi

# Activate the virtual environment if not already active
if [ "$VENV_ALREADY_ACTIVE" = false ]; then
    if [ -f "$VENV_DIR/Scripts/activate" ]; then
        # Windows (Git Bash)
        source "$VENV_DIR/Scripts/activate"
    elif [ -f "$VENV_DIR/bin/activate" ]; then
        # Linux/Mac
        source "$VENV_DIR/bin/activate"
    else
        echo -e "${RED}✗${NC} Cannot find activation script in venv"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "${CYAN}ℹ${NC} Virtual environment already activated"
fi

echo ""

################################################################################
# Kill any existing processes on ports 3000 and 5000
################################################################################

echo "🧹 Checking for existing processes on ports 3000 and 5000..."

# Kill processes on port 3000
if command -v lsof &> /dev/null; then
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
elif command -v netstat &> /dev/null; then
    # Windows fallback using netstat
    PIDS=$(netstat -ano | grep :3000 | awk '{print $5}' | sort -u)
    for pid in $PIDS; do
        taskkill //PID $pid //F 2>/dev/null || true
    done
    PIDS=$(netstat -ano | grep :5000 | awk '{print $5}' | sort -u)
    for pid in $PIDS; do
        taskkill //PID $pid //F 2>/dev/null || true
    done
fi

sleep 1
echo -e "${GREEN}✓${NC} Ports cleared"
echo ""

################################################################################
# Trap to clean up background processes on exit
################################################################################

cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null || true
    # Frontend runs in foreground, will be killed automatically
    exit 0
}

trap cleanup EXIT INT TERM

################################################################################
# Start servers
################################################################################

echo "🚀 Starting LLM Claims Analysis Pipeline (Development Mode)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Servers:"
echo "   • Frontend (dev): http://localhost:3000"
echo "   • Backend API:    http://localhost:5000/api"
echo ""
echo "🔥 Hot reload enabled on frontend"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if backend exists
if [ ! -f "app/backend/app.py" ]; then
    echo -e "${RED}✗${NC} Backend not found at: app/backend/app.py"
    echo ""
    echo "Please ensure you're in the correct directory and setup was completed."
    exit 1
fi

# Check if frontend exists
if [ ! -d "app/frontend" ]; then
    echo -e "${RED}✗${NC} Frontend not found at: app/frontend/"
    echo ""
    echo "Please ensure you're in the correct directory and setup was completed."
    exit 1
fi

# Start backend in background
echo "🌐 Starting Flask backend..."
python app/backend/app.py &
BACKEND_PID=$!

# Give backend time to start
sleep 2

# Check if backend started successfully
if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo -e "${RED}✗${NC} Backend failed to start"
    echo ""
    echo "Check for errors above. Common issues:"
    echo "  • Missing dependencies (run ./setup.sh)"
    echo "  • Port 5000 already in use"
    echo "  • Python errors in app.py"
    exit 1
fi

echo -e "${GREEN}✓${NC} Backend started (PID: $BACKEND_PID)"
echo ""

# Start frontend dev server in foreground
echo "🎨 Starting Vite dev server..."
echo ""

cd app/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${RED}✗${NC} Frontend dependencies not installed"
    echo ""
    echo "Please run setup first:"
    echo "  ./setup.sh"
    exit 1
fi

# Run npm dev (this runs in foreground)
npm run dev

# If npm exits, cleanup will be called automatically by trap

echo ""
read -p "Press Enter to continue..."
