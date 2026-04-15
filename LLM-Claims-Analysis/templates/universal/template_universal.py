# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_universal_fallback_prompt (document_text, document_type):
  """
  Universal Fallback Template for any document type not covered by specialized
  or category templates. This template focuses on core actuarial concepts
  that could be present in any type of document.
  """

  return f"""
You are processing a {document_type} for workers' compensation actuarial analysis.

This document type is not in our specialized categories. Extract ANY actuarial-relevant information you find, focusing on these universal concepts:

FINANCIAL IMPACT INDICATORS (extract if present):
- Cost estimates, amounts, financial projections of any kind
- Revenue/income loss indicators
- Expense categories and magnitudes
- Budget impact or financial planning information
- Insurance coverage amounts or limits

RISK ASSESSMENT FACTORS (extract if present):
- Risk factors, hazards, contributing causes
- Safety violations, compliance issues  
- Likelihood indicators for adverse outcomes
- Probability assessments or risk ratings
- Vulnerability or exposure factors

SEVERITY/COMPLEXITY INDICATORS (extract if present):
- Severity descriptors (minor/moderate/major/severe/catastrophic)
- Complexity factors requiring special handling
- Complicating circumstances or aggravating factors
- Scale or magnitude indicators
- Impact intensity descriptions

TIMELINE/DEVELOPMENT FACTORS (extract if present):
- Duration estimates, recovery timelines
- Development speed indicators (fast/slow progression)
- Milestone dates and deadlines
- Sequence of events or chronological factors
- Temporal patterns or timing issues

LIABILITY/COVERAGE FACTORS (extract if present):
- Responsibility/fault indicators
- Coverage applicability issues
- Dispute potential or contested matters
- Legal or regulatory compliance factors
- Contractual obligations or exclusions

OUTCOME PREDICTORS (extract if present):
- Resolution probability indicators
- Success/failure likelihood factors
- Recovery or improvement potential
- Stability or volatility indicators
- Predictive factors for claim development

QUALITY/RELIABILITY INDICATORS (extract if present):
- Credibility or reliability assessments
- Data quality or completeness indicators
- Verification or validation information
- Accuracy or precision measures
- Confidence levels or uncertainty factors

Return ONLY valid JSON (only include sections where you found relevant information):
{{
    "document_type": "{document_type}",
    "category": "universal",
    "extracted_features": {{
        // Only include features actually found in the document
        // Do not force categories that aren't present

        "financial_indicators": [
            // Any financial amounts, costs, or economic impacts found
        ],
        "risk_factors": [
            // Any risk elements, hazards, or contributing factors found  
        ],
        "severity_indicators": [
            // Any severity or magnitude descriptors found
        ],
        "timeline_factors": [
            // Any duration, timing, or developmental information found
        ],
        "liability_indicators": [
            // Any fault, responsibility, or coverage factors found
        ],
        "outcome_predictors": [
            // Any prognostic or predictive information found
        ],
        "quality_reliability_factors": [
            // Any credibility, accuracy, or reliability indicators found
        ]
    }},
    "key_actuarial_quotes": [
        // Most relevant text excerpts that support actuarial analysis
    ],
    "document_summary": "Brief summary of what this document contributes to claim understanding",
    "actuarial_relevance_score": 0.0-1.0,  // How relevant is this document for actuarial purposes?
    "extraction_confidence": 0.0-1.0      // How confident are you in the extractions?
}}

DOCUMENT TEXT:
{document_text}
"""
