# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_claimant_statement_specialized_prompt (text: str) -> str:
  return f"""
You are processing Document: CLAIMANT STATEMENT for workers' compensation claim analysis.

Extract the following for ACTUARIAL USE:

CREDIBILITY ASSESSMENT (for claim validity):
- narrative_consistency: consistent/inconsistent with prior documents
- detail_level: high/medium/low detail and specificity
- emotional_appropriateness: appropriate/excessive/insufficient emotional response
- timeline_accuracy: accurate/inaccurate timeline of events

SOFT RISK FACTORS (for ratemaking):
- claimant_motivation_level: high/medium/low motivation to recover
- financial_pressure_indicators: high/medium/low/unknown financial pressure
- support_system_strength: strong/moderate/weak support system
- recovery_attitude: positive/neutral/negative attitude toward recovery

FRAUD INDICATORS (for claim integrity):
- story_consistency_score: high/medium/low consistency
- exaggeration_indicators: none/minor/moderate/significant exaggeration
- coaching_evidence: none/possible/likely coaching detected
- malingering_risk: low/medium/high risk of malingering

VALIDATION DATA (for quality control):
- fact_verification: facts match/contradict prior documents
- discrepancy_identification: Major discrepancies noted
- missing_information_gaps: Key information gaps identified

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "claimant_statement",
    "injury_severity": "moderate",
    "extraction_confidence": 0.75,

    "credibility_assessment": {{
        "narrative_consistency": "consistent",
        "detail_level": "high",
        "emotional_appropriateness": "appropriate",
        "timeline_accuracy": "accurate"
    }},

    "soft_risk_factors": {{
        "claimant_motivation_level": "high",
        "financial_pressure_indicators": "medium",
        "support_system_strength": "strong",
        "recovery_attitude": "positive"
    }},

    "fraud_indicators": {{
        "story_consistency_score": "high",
        "exaggeration_indicators": "none",
        "coaching_evidence": "none",
        "malingering_risk": "low"
    }},

    "validation_data": {{
        "fact_verification": "facts match prior documents",
        "discrepancy_identification": "no major discrepancies",
        "missing_information_gaps": "minor gaps in timeline"
    }}
}}

DOCUMENT TEXT:
{text}
"""