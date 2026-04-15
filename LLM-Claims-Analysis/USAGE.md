# Usage Guide

## Pipeline Overview

1. **Script 1**: FHIR Bundle Processor
2. **Script 2**: Synthetic Document Generator
3. **Script 3**: Text Aggregator
4. **Script 4**: Claims Analyzer (two-stage)

## Basic Usage

Default directories are configured in `config/*.yaml` files.

## Quick Test (Process 1 Claim)

For testing, use `--limit 1` to process a single claim:

```bash
python 1_data-process_fhir_bundle.py --limit 1
python 2_data-add_documents.py --limit 1
python 3_process-combine_text_to_json.py --limit 1
python 4_analysis-analyze_claims.py --limit 1
```

### Script 1: FHIR Processing

```bash
python 1_data-process_fhir_bundle.py
```

### Script 2: Document Generation

```bash
python 2_data-add_documents.py
```

### Script 3: Text Aggregation

```bash
python 3_process-combine_text_to_json.py
```

### Script 4: Claims Analysis

```bash
# Full pipeline (Stage 1 + Stage 2)
python 4_analysis-analyze_claims.py

# Stage 1 only
python 4_analysis-analyze_claims.py --mode stage1

# Stage 2 only
python 4_analysis-analyze_claims.py --mode stage2
```

## Command Options (Optional)

All options override defaults from `config/*.yaml`:

| Option | Description | Example |
|--------|-------------|---------|
| `--input-dir` | Override input directory | `--input-dir ./custom_input` |
| `--output-dir` | Override output directory | `--output-dir ./custom_output` |
| `--limit` | Limit claims processed | `--limit 10` |
| `--mode` | Processing mode (Script 4) | `--mode stage1` |

## Input Format

### FHIR Bundles
- Standard FHIR R4 JSON format
- Must include Patient, Encounter, and DocumentReference resources

### JSON Files
```json
{
  "claim_id": "WC2024001",
  "patient_initials": "jd",
  "encounters": [
    {
      "encounter_id": "enc_001",
      "document_type": "phone_transcript",
      "clinical_note": "Patient called...",
      "encounter_date": "2024-01-15"
    }
  ]
}
```

## Output Structure

```
output/
├── 1_data-process_fhir_bundle/  # Script 1 output
├── 2_data-add_documents/        # Script 2 output
├── 3_process-combine_text_to_json/  # Script 3 output
└── 4_analysis-analyze_claims/
    ├── stage1/                  # Stage 1 extractions
    ├── stage2/                  # Stage 2 final results
    └── logs/
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Configuration Error |
| 2 | Input/Output Error |
| 3 | Processing Error |
| 4 | Validation Error |

---

*This software was developed and implemented by MDSight, LLC with project management by Lieberthal & Associates, LLC and funding from the Casualty Actuarial Society. Licensed under MPL-2.0.*
