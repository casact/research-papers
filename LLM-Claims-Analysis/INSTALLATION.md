# Installation Guide

## System Requirements

- Python 3.8+
- OpenAI API key from https://platform.openai.com/api-keys

## Installation

### Automated Setup (Optional)

```bash
# Linux/macOS - runs full setup automatically
./setup.sh
```

For manual installation, follow steps below:

### 1. Clone Repository

```bash
git clone <repository-url>
cd mdsight-llm-claims-analysis
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt
pip install -r app/backend/requirements.txt  # For web application
```

### 3. Configure API Key

```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### 4. Verify Installation

```bash
# Test scripts are accessible
python 1_data-process_fhir_bundle.py --help
python 4_analysis-analyze_claims.py --help
```

## Web Application (Optional)

```bash
# Install frontend dependencies
cd app/frontend
npm install
cd ../..

# Start backend
cd app/backend && python app.py

# Start frontend (separate terminal)
cd app/frontend && npm run dev
```

Visit `http://localhost:3000`

## Next Steps

- Review configuration files in `config/`
- See `USAGE.md` for running the pipeline

---

*This software was developed and implemented by MDSight, LLC with project management by Lieberthal & Associates, LLC and funding from the Casualty Actuarial Society. Licensed under MPL-2.0.*
