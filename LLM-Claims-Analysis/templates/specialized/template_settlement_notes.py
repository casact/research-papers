# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_settlement_notes_specialized_prompt (text: str) -> str:
  return f"""
You are processing Document: SETTLEMENT ADJUSTER NOTES for workers' compensation claim analysis.

Extract the following for ACTUARIAL USE:

ACTUAL COSTS (for reserving validation):
- total_medical_costs: Actual medical costs incurred
- total_wage_loss: Actual wage loss paid
- administrative_costs: Administrative and legal costs
- cost_development_vs_reserves: higher/lower/as_expected vs initial reserves

SETTLEMENT ANALYSIS (for ultimate cost prediction):
- settlement_value_range: Dollar range for settlement (e.g., "15000-25000")
- settlement_probability: high/medium/low probability of settlement
- negotiation_position_strength: strong/moderate/weak position
- resolution_timeline_estimate: Expected timeline to resolution

OUTCOME PREDICTORS (for development patterns):
- claim_stability: stable/volatile claim development
- litigation_risk: low/medium/high litigation risk
- medical_complications: none/minor/major complications
- rtw_success: successful/partial/failed return to work

PATTERN INDICATORS (for trend analysis):
- claim_development_speed: fast/average/slow development
- cost_escalation_factors: Factors driving cost increases
- reserve_adequacy: adequate/inadequate reserves
- closure_likelihood: high/medium/low likelihood of closure

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "settlement_adjuster_notes",
    "injury_severity": "moderate",
    "extraction_confidence": 0.85,

    "actual_costs": {{
        "total_medical_costs": 18500,
        "total_wage_loss": 12000,
        "administrative_costs": 3200,
        "cost_development_vs_reserves": "higher"
    }},

    "settlement_analysis": {{
        "settlement_value_range": "20000-30000", 
        "settlement_probability": "high",
        "negotiation_position_strength": "moderate",
        "resolution_timeline_estimate": "3_months"
    }},

    "outcome_predictors": {{
        "claim_stability": "stable",
        "litigation_risk": "low",
        "medical_complications": "minor",
        "rtw_success": "partial"
    }},

    "pattern_indicators": {{
        "claim_development_speed": "average",
        "cost_escalation_factors": ["medical_complications", "extended_recovery"],
        "reserve_adequacy": "adequate", 
        "closure_likelihood": "high"
    }}
}}

DOCUMENT TEXT:
{text}
"""