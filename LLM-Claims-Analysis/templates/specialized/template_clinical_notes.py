# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_clinical_notes_specialized_prompt (text: str) -> str:
  return f"""
You are processing Document: CLINICAL NOTE for workers' compensation claim analysis.

Extract the following for ACTUARIAL USE:

MEDICAL ASSESSMENT (for clinical evaluation):
- primary_diagnosis: Primary medical diagnosis
- severity_assessment: minor/moderate/major/catastrophic severity
- treatment_provided: Type of treatment provided
- medications_prescribed: List of medications
- procedures_performed: Medical procedures done

PROGNOSIS FACTORS (for development prediction):
- expected_recovery_time: Expected recovery timeline
- complications_risk: low/medium/high risk of complications
- functional_limitations: Current functional restrictions
- work_capacity_assessment: Current work capacity

COST FACTORS (for reserving):
- treatment_complexity: simple/moderate/complex treatment
- ongoing_care_needs: Ongoing medical care requirements
- rehabilitation_requirements: PT/OT/rehab needs
- specialist_consultations_needed: Specialist referrals required

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "clinical_note",
    "injury_severity": "moderate",
    "extraction_confidence": 0.80,

    "medical_assessment": {{
        "primary_diagnosis": "acute_lower_back_strain",
        "severity_assessment": "moderate",
        "treatment_provided": "conservative_management",
        "medications_prescribed": ["ibuprofen", "muscle_relaxers"],
        "procedures_performed": ["physical_examination", "range_of_motion_testing"]
    }},

    "prognosis_factors": {{
        "expected_recovery_time": "4-6_weeks",
        "complications_risk": "low",
        "functional_limitations": "lifting restrictions, prolonged sitting limitations",
        "work_capacity_assessment": "light_duty_capable"
    }},

    "cost_factors": {{
        "treatment_complexity": "simple",
        "ongoing_care_needs": "follow_up_in_2_weeks",
        "rehabilitation_requirements": "physical_therapy_recommended",
        "specialist_consultations_needed": "orthopedic_if_no_improvement"
    }}
}}

DOCUMENT TEXT:
{text}
"""