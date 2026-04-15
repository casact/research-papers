# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_phone_transcript_specialized_prompt (text: str) -> str:
  return f"""
You are processing Document: PHONE TRANSCRIPT for workers' compensation claim analysis.

Extract the following for ACTUARIAL USE:

SEVERITY INDICATORS (for reserving):
- injury_type_and_body_part: Specific injury and affected body part
- initial_pain_level: Pain level 1-10 if mentioned  
- immediate_functional_limitations: Functional restrictions described
- emergency_care_required: true/false if ER/hospital mentioned

RISK FACTORS (for ratemaking):
- claimant_age_and_occupation: Age and job type information
- mechanism_of_injury: How injury occurred
- safety_protocol_compliance: full/partial/none/unknown
- equipment_involvement: Equipment involved in injury
- witness_availability: true/false if witnesses available

EARLY COST PREDICTORS (for reserving):
- hospital_er_treatment: true/false if hospital care mentioned
- specialist_referral: true/false if specialist mentioned
- surgery_potential: true/false if surgery discussed  
- work_absence_expected: Expected time off work

CLAIM CHARACTERISTICS (for risk stratification):
- claimant_cooperation_level: high/medium/low cooperation
- narrative_consistency: consistent/inconsistent story
- immediate_reporting: true/false if reported promptly
- family_financial_pressure: high/medium/low/unknown

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "phone_transcript",
    "injury_severity": "moderate",
    "extraction_confidence": 0.85,

    "severity_indicators": {{
        "injury_type_and_body_part": "lower back strain from lifting",
        "initial_pain_level": 7,
        "immediate_functional_limitations": "cannot lift, limited walking",
        "emergency_care_required": false
    }},

    "risk_factors": {{
        "claimant_age_and_occupation": {{"age": 34, "occupation": "concrete finisher"}},
        "mechanism_of_injury": "lifting_heavy_object",
        "safety_protocol_compliance": "partial",
        "equipment_involvement": "concrete vibrator",
        "witness_availability": true
    }},

    "early_cost_predictors": {{
        "hospital_er_treatment": true,
        "specialist_referral": true,
        "surgery_potential": false,
        "work_absence_expected": "2_weeks"
    }},

    "claim_characteristics": {{
        "claimant_cooperation_level": "high",
        "narrative_consistency": "consistent",
        "immediate_reporting": true,
        "family_financial_pressure": "low"
    }}
}}

DOCUMENT TEXT:
{text}
"""