# LLM Claims Analysis

AI-powered pipeline for processing medical claims data through FHIR bundles and multi-stage actuarial analysis.

## Overview

Four-stage processing pipeline:

1. **FHIR Processing** - Convert FHIR bundles to structured JSON
2. **Document Generation** - Create synthetic supporting documents
3. **Text Aggregation** - Consolidate documents into unified claim files
4. **Claims Analysis** - Two-stage extraction and synthesis of actuarial variables

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY="your-key"

# Run pipeline
python 4_analysis-analyze_claims.py
```

**Alternative**: Use `./run.sh` (Linux/macOS) or `run.bat` (Windows) to start the web application.

## Pipeline Scripts

- `1_data-process_fhir_bundle.py` - FHIR to JSON conversion
- `2_data-add_documents.py` - Synthetic document generation
- `3_process-combine_text_to_json.py` - Text consolidation
- `4_analysis-analyze_claims.py` - Two-stage claims analysis

## Configuration

YAML configuration files in `config/` directory:
- `1_data-process_fhir_bundle.yaml`
- `2_data-add_documents.yaml`
- `3_process-combine_text_to_json.yaml`
- `4_analysis-analyze_claims.yaml`

## Requirements

- Python 3.8+
- OpenAI API key
- See `requirements.txt` for dependencies

## Documentation

- Installation: See `INSTALLATION.md`
- Usage: See `USAGE.md`
- Configuration: Edit YAML files in `config/`

---

## Credits

**Development Team**
- **MDSight, LLC** - Software development and implementation
- **Lieberthal & Associates, LLC** - Project Management

**Funding**
This project was developed with funding from the **Casualty Actuarial Society (CAS)** research program.

## License

This project is released under the **Mozilla Public License 2.0 (MPL-2.0)** in accordance with CAS research requirements.

- Allows both academic and commercial applications
- Ensures attribution to original research
- File-level copyleft license
- See `LICENSE` file for full terms
- See `AUTHORS.md` for contributor information
