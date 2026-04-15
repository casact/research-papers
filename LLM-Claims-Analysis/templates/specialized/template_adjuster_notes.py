# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_adjuster_notes_specialized_prompt (text: str) -> str:
  return f"""
You are processing Document: ADJUSTER NOTES for workers' compensation claim analysis.

Extract the following for ACTUARIAL USE:

LIABILITY/COVERAGE (for all functions):
- liability_determination: clear/disputed/denied
- coverage_issues: none/minor/major coverage problems
- investigation_complexity: low/medium/high complexity

RESERVE SETTING DATA (for reserving):
- initial_reserve_amount: Dollar amount set initially
- medical_reserve_amount: Medical portion of reserve
- indemnity_reserve_amount: Wage loss portion  
- reserve_adequacy_assessment: adequate/inadequate initial reserves

CLAIM COMPLEXITY (for risk stratification):
- investigation_actions_required: Number/complexity of investigation steps
- witness_cooperation: cooperative/uncooperative/unavailable
- employer_cooperation: cooperative/uncooperative
- legal_involvement_potential: low/medium/high likelihood

COST DRIVERS (for reserving):
- treating_physician_specialty: Type of physician (primary/specialist)
- diagnostic_tests_ordered: Tests requested/completed
- treatment_protocol: conservative/aggressive approach
- rtw_timeline_estimate: Return to work timeline

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "adjuster_notes_initial",
    "injury_severity": "moderate", 
    "extraction_confidence": 0.80,

    "liability_coverage": {{
        "liability_determination": "clear",
        "coverage_issues": "none",
        "investigation_complexity": "medium"
    }},

    "reserve_setting_data": {{
        "initial_reserve_amount": 25000,
        "medical_reserve_amount": 15000,
        "indemnity_reserve_amount": 10000,
        "reserve_adequacy_assessment": "adequate"
    }},

    "claim_complexity": {{
        "investigation_actions_required": 3,
        "witness_cooperation": "cooperative",
        "employer_cooperation": "cooperative", 
        "legal_involvement_potential": "low"
    }},

    "cost_drivers": {{
        "treating_physician_specialty": "orthopedic_specialist",
        "diagnostic_tests_ordered": "MRI, X-ray",
        "treatment_protocol": "conservative",
        "rtw_timeline_estimate": "4_weeks"
    }}
}}

DOCUMENT TEXT:
{text}
"""