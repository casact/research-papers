#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

################################################################################
# LLM Claims Analysis Pipeline - Setup Script
#
# This script sets up the development environment by:
# 1. Installing uv (Python package manager) if not present
# 2. Creating a Python virtual environment
# 3. Installing Python dependencies (root + backend)
# 4. Installing frontend dependencies (Node.js/npm)
# 5. Installing Ollama (if not present and on Linux/WSL)
# 6. Downloading recommended Ollama models
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

# Helper functions
print_header() {
    echo -e "\n${MAGENTA}===========================================================================${NC}"
    echo -e "${MAGENTA}$1${NC}"
    echo -e "${MAGENTA}===========================================================================${NC}\n"
}

print_step() {
    echo -e "${BLUE}==>${NC} ${CYAN}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

################################################################################
# VENV DETECTION LOGIC (identical in setup.sh and run.sh)
################################################################################

print_header "Step 1: Detecting Virtual Environment"

# Configure Analytics venv location (edit this path if different)
ANALYTICS_VENV="/path_to_environment/.venv"

# Priority 1: Already activated venv
if [ -n "$VIRTUAL_ENV" ]; then
    VENV_DIR="$VIRTUAL_ENV"
    print_success "Using already activated venv: $VENV_DIR"
    VENV_ALREADY_ACTIVE=true

# Priority 2: Environment variable override
elif [ -n "$LLM_VENV_PATH" ]; then
    VENV_DIR="$LLM_VENV_PATH"
    print_success "Using venv from LLM_VENV_PATH: $VENV_DIR"
    VENV_ALREADY_ACTIVE=false

# Priority 3: Analytics venv exists
elif [ -d "$ANALYTICS_VENV" ]; then
    VENV_DIR="$ANALYTICS_VENV"
    print_success "Found Analytics venv: $VENV_DIR"
    VENV_ALREADY_ACTIVE=false

# Priority 4: Local venv
else
    VENV_DIR="$SCRIPT_DIR/.venv"
    print_info "Using local venv: $VENV_DIR"
    VENV_ALREADY_ACTIVE=false
fi

################################################################################
# END VENV DETECTION LOGIC
################################################################################

# Check if venv exists and needs to be created
CREATE_VENV=false
if [ "$VENV_ALREADY_ACTIVE" = false ]; then
    if [ ! -f "$VENV_DIR/bin/python" ] && [ ! -f "$VENV_DIR/Scripts/python.exe" ]; then
        CREATE_VENV=true
        print_info "Virtual environment does not exist, will create it"
    else
        print_success "Virtual environment already exists"
    fi
fi

echo ""

################################################################################
# 2. Check and install uv
################################################################################

print_header "Step 2: Installing uv (Python Package Manager)"

if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version 2>&1 || echo "unknown")
    print_success "uv is already installed: $UV_VERSION"
else
    print_step "Installing uv..."

    # Install uv using the official installer
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"

    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version 2>&1 || echo "installed")
        print_success "uv installed successfully: $UV_VERSION"
    else
        print_error "Failed to install uv. Please install manually from https://github.com/astral-sh/uv"
        exit 1
    fi
fi

################################################################################
# 3. Create virtual environment if needed
################################################################################

print_header "Step 3: Setting Up Virtual Environment"

if [ "$CREATE_VENV" = true ]; then
    print_step "Creating virtual environment at: $VENV_DIR"

    # Create the venv
    uv venv "$VENV_DIR"

    if [ $? -eq 0 ]; then
        print_success "Virtual environment created successfully"
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
else
    print_info "Skipping venv creation (already exists)"
fi

# Activate the virtual environment if not already active
if [ "$VENV_ALREADY_ACTIVE" = false ]; then
    print_step "Activating virtual environment..."

    if [ -f "$VENV_DIR/Scripts/activate" ]; then
        # Windows (Git Bash)
        source "$VENV_DIR/Scripts/activate"
    elif [ -f "$VENV_DIR/bin/activate" ]; then
        # Linux/Mac
        source "$VENV_DIR/bin/activate"
    else
        print_error "Cannot find activation script in venv"
        exit 1
    fi

    print_success "Virtual environment activated"
else
    print_info "Virtual environment already activated, skipping activation"
fi

# Verify Python is available
if ! command -v python &> /dev/null; then
    print_error "Python not found in virtual environment"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1)
print_success "Python available: $PYTHON_VERSION"

echo ""

################################################################################
# 4. Install Python dependencies
################################################################################

print_header "Step 4: Installing Python Dependencies"

# Install root dependencies
if [ -f "requirements.txt" ]; then
    print_step "Installing root dependencies from requirements.txt..."

    # Use uv pip with the venv's python
    if [ -f "$VENV_DIR/bin/python" ]; then
        PYTHON_BIN="$VENV_DIR/bin/python"
    else
        PYTHON_BIN="$VENV_DIR/Scripts/python.exe"
    fi

    uv pip install -r requirements.txt --python "$PYTHON_BIN"

    if [ $? -eq 0 ]; then
        print_success "Root dependencies installed"
    else
        print_error "Failed to install root dependencies"
        exit 1
    fi
else
    print_warning "requirements.txt not found, skipping root dependencies"
fi

echo ""

# Install backend dependencies
if [ -f "app/backend/requirements.txt" ]; then
    print_step "Installing backend dependencies from app/backend/requirements.txt..."

    uv pip install -r app/backend/requirements.txt --python "$PYTHON_BIN"

    if [ $? -eq 0 ]; then
        print_success "Backend dependencies installed"
    else
        print_error "Failed to install backend dependencies"
        exit 1
    fi
else
    print_warning "app/backend/requirements.txt not found, skipping backend dependencies"
fi

echo ""

################################################################################
# 5. Install frontend dependencies
################################################################################

print_header "Step 5: Installing Frontend Dependencies"

if [ -d "app/frontend" ] && [ -f "app/frontend/package.json" ]; then
    print_step "Installing Node.js dependencies..."

    cd app/frontend

    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        print_error "npm not found. Please install Node.js 18+ from https://nodejs.org"
        exit 1
    fi

    NPM_VERSION=$(npm --version 2>&1)
    print_info "npm version: $NPM_VERSION"

    # Install dependencies
    npm install

    if [ $? -eq 0 ]; then
        print_success "Frontend dependencies installed"
    else
        print_error "Failed to install frontend dependencies"
        exit 1
    fi

    # Return to script directory
    cd ../..
else
    print_warning "app/frontend not found or package.json missing, skipping frontend setup"
fi

echo ""

################################################################################
# 6. Install Ollama
################################################################################

print_header "Step 6: Installing Ollama"

if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -n1 || echo "unknown")
    print_success "Ollama is already installed: $OLLAMA_VERSION"
else
    print_step "Ollama not found. Attempting to install..."

    # Detect OS
    OS_TYPE=$(uname -s)

    if [[ "$OS_TYPE" == "Linux" ]]; then
        print_info "Detected Linux/WSL system"
        print_step "Installing Ollama via official install script..."

        curl -fsSL https://ollama.com/install.sh | sh

        if command -v ollama &> /dev/null; then
            print_success "Ollama installed successfully"
        else
            print_error "Failed to install Ollama automatically"
            print_info "Please install manually from https://ollama.com/download"
            print_warning "Continuing without Ollama - you'll need to install it manually"
        fi
    else
        print_warning "Unsupported OS: $OS_TYPE"
        print_info "Please install Ollama manually from https://ollama.com/download"
    fi
fi

################################################################################
# 7. Download recommended Ollama models
################################################################################

if command -v ollama &> /dev/null; then
    print_header "Step 7: Downloading Recommended Ollama Models"

    # Check if Ollama service is running
    if ! pgrep -x "ollama" > /dev/null; then
        print_warning "Ollama service is not running"
        print_info "Starting Ollama service in the background..."

        # Try to start Ollama serve in background
        nohup ollama serve > /dev/null 2>&1 &
        OLLAMA_PID=$!

        # Wait a moment for service to start
        sleep 3

        if pgrep -x "ollama" > /dev/null; then
            print_success "Ollama service started (PID: $OLLAMA_PID)"
        else
            print_error "Failed to start Ollama service"
            print_info "Please run 'ollama serve' in a separate terminal before continuing"
            print_warning "Skipping model downloads"
        fi
    else
        print_success "Ollama service is running"
    fi

    # Only proceed with downloads if service is running
    if pgrep -x "ollama" > /dev/null; then
        # Recommended models for this pipeline
        RECOMMENDED_MODELS=(
            "qwen2.5:7b"    # Best balance for medical narratives and structured output
            "phi3:mini"     # Fast, efficient model for encounter classification
        )

        # Optional/Alternative models (commented out by default)
        # OPTIONAL_MODELS=(
        #     "qwen2.5:14b"   # Higher quality (larger)
        #     "mistral:7b"    # Alternative quality model
        #     "llama3.2:3b"   # Budget/speed option
        # )

        for model in "${RECOMMENDED_MODELS[@]}"; do
            print_step "Checking model: $model"

            # Check if model is already downloaded
            if ollama list | grep -q "^$model"; then
                print_success "Model $model is already downloaded"
            else
                print_step "Downloading model: $model (this may take several minutes)..."

                if ollama pull "$model"; then
                    print_success "Model $model downloaded successfully"
                else
                    print_error "Failed to download model: $model"
                    print_warning "You can download it later with: ollama pull $model"
                fi
            fi
        done

        print_info ""
        print_info "Installed models:"
        ollama list
    fi
else
    print_header "Step 7: Skipping Model Downloads"
    print_warning "Ollama is not installed, skipping model downloads"
fi

echo ""

################################################################################
# Setup Complete
################################################################################

print_header "Setup Complete!"

echo -e "${GREEN}Environment setup finished successfully!${NC}"
echo ""
echo -e "${GREEN}✓${NC} Virtual environment: ${CYAN}$VENV_DIR${NC}"
echo -e "${GREEN}✓${NC} Python dependencies installed"
echo -e "${GREEN}✓${NC} Frontend dependencies installed"
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓${NC} Ollama installed and configured"
fi
echo ""

print_info "Next steps:"
echo ""
echo "  1. Configure your LLM provider in config files:"
echo -e "     ${CYAN}config/1_data-process_fhir_bundle.yaml${NC}"
echo -e "     ${CYAN}config/2_add-documents.yaml${NC}"
echo ""
echo "  2. If using OpenAI, set your API key:"
echo -e "     ${CYAN}export OPENAI_API_KEY='your-api-key-here'${NC}"
echo ""
echo "  3. If using Ollama, ensure the service is running:"
echo -e "     ${CYAN}ollama serve${NC}"
echo ""
echo "  4. Start the web application:"
echo -e "     ${CYAN}./run.sh${NC}"
echo ""
echo "  5. Open your browser:"
echo -e "     ${CYAN}http://localhost:3000${NC}"
echo ""

# Show venv activation command for reference
if [ "$VENV_ALREADY_ACTIVE" = false ]; then
    echo -e "${BLUE}ℹ${NC} To manually activate the virtual environment:"
    if [ -f "$VENV_DIR/Scripts/activate" ]; then
        echo -e "   ${CYAN}source \"$VENV_DIR/Scripts/activate\"${NC}"
    else
        echo -e "   ${CYAN}source \"$VENV_DIR/bin/activate\"${NC}"
    fi
    echo ""
fi

# Show how to override venv location
echo -e "${BLUE}ℹ${NC} To use a different virtual environment:"
echo -e "   ${CYAN}export LLM_VENV_PATH=\"/path/to/your/venv\"${NC}"
echo -e "   Or activate your venv before running setup/run scripts"
echo ""
read -p "Press Enter to continue..."

print_success "Setup completed successfully! 🎉"
