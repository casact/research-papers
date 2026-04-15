# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_medical_provider_specialized_prompt (text: str) -> str:
  return f"""
You are processing Document: MEDICAL PROVIDER LETTER for workers' compensation claim analysis.

Extract the following for ACTUARIAL USE:

MEDICAL SEVERITY (for reserving):
- specific_diagnosis: Specific medical diagnosis with severity
- treatment_complexity: conservative/surgical/complex treatment needs
- diagnostic_certainty: definitive/probable/uncertain diagnosis
- complication_risk: low/medium/high risk of complications

COST PREDICTIONS (for reserving):
- treatment_duration_estimates: Expected duration of treatment
- specialist_care_requirements: Specialist consultations needed
- therapy_rehabilitation_needs: PT/OT requirements
- future_medical_necessity: Ongoing medical needs

DISABILITY ASSESSMENT (for reserving):
- work_restrictions_severity: mild/moderate/severe restrictions
- rtw_timeline_prediction: Timeline for return to work
- permanent_impairment_likelihood: unlikely/possible/likely/definite
- maximum_medical_improvement: Timeline to MMI

MEDICAL NECESSITY (for cost control):
- treatment_appropriateness: appropriate/questionable treatment
- alternative_treatments: Alternative options considered
- standard_of_care_compliance: Meets/exceeds/below standard

RISK STRATIFICATION:
- patient_compliance: high/medium/low compliance expected
- recovery_prognosis: excellent/good/fair/poor prognosis

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "medical_provider_letter",
    "extraction_confidence": 0.90,

    "medical_severity": {{
        "specific_diagnosis": "L2 compression fracture with trabecular disruption",
        "treatment_complexity": "conservative",
        "diagnostic_certainty": "definitive",
        "complication_risk": "medium"
    }},

    "cost_predictions": {{
        "treatment_duration_estimates": "6-12 months",
        "specialist_care_requirements": "orthopedic consultations needed",
        "therapy_rehabilitation_needs": "PT required",
        "future_medical_necessity": "ongoing monitoring and rehabilitation"
    }},

    "disability_assessment": {{
        "work_restrictions_severity": "severe",
        "rtw_timeline_prediction": "12-16 weeks for modified duty",
        "permanent_impairment_likelihood": "possible",
        "maximum_medical_improvement": "6-12 months"
    }},

    "medical_necessity": {{
        "treatment_appropriateness": "appropriate",
        "alternative_treatments": "No reasonable alternatives considered",
        "standard_of_care_compliance": "Meets standard"
    }},

    "risk_stratification": {{
        "patient_compliance": "high",
        "recovery_prognosis": "good"
    }}
}}

DOCUMENT TEXT:
{text}
"""