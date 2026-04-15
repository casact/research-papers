# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_medical_category_prompt (document_text, document_type):
  """
  Optimized Medical Category Template for documents:
  - hospital_discharge_summary, ime_report, physical_therapy_notes
  - psychiatric_evaluation, pharmacy_records, diagnostic_test_results
  - specialist_consultation_notes, rehabilitation_reports, nursing_notes
  """

  return f"""
You are processing a {document_type} for workers' compensation actuarial analysis.

Extract MEDICAL INFORMATION for ACTUARIAL USE:

CLINICAL SEVERITY (for reserving and development):
- primary_diagnosis: Specific medical diagnosis with ICD codes if available
- diagnostic_certainty: definitive/probable/uncertain/rule_out
- injury_severity_clinical: minor/moderate/major/catastrophic based on medical evidence
- comorbidity_impact: none/minimal/moderate/significant impact from pre-existing conditions
- complications_present: none/minor/major complications identified

TREATMENT REQUIREMENTS (for cost prediction):
- current_treatment_phase: acute/subacute/chronic/maintenance
- treatment_modalities: conservative/surgical/multimodal/experimental
- medication_complexity: none/simple/moderate/complex medication regimen
- procedure_intensity: outpatient/inpatient/intensive/surgical
- specialist_involvement: none/single/multiple/coordinated_care

FUNCTIONAL STATUS (for disability assessment):
- current_functional_capacity: normal/mildly_impaired/moderately_impaired/severely_impaired
- work_related_restrictions: none/light_duty/modified_duty/unable_to_work
- activities_daily_living: independent/assisted/dependent
- mobility_status: unrestricted/ambulatory_aids/wheelchair/bedbound
- cognitive_function_impact: none/mild/moderate/severe

RECOVERY INDICATORS (for development patterns):
- treatment_response: excellent/good/poor/non_responsive
- recovery_trajectory: improving/stable/declining/fluctuating
- maximum_medical_improvement: achieved/expected_6months/expected_1year/unlikely
- permanent_impairment_potential: none/minimal/moderate/significant
- recurrence_risk: low/moderate/high

COST DRIVERS (for financial projections):
- ongoing_care_intensity: minimal/moderate/intensive/lifelong
- equipment_needs: none/basic/moderate/extensive
- home_health_requirements: none/occasional/regular/continuous
- facility_care_needs: none/outpatient/inpatient/long_term
- pharmaceutical_costs: low/moderate/high/specialty_drugs

CARE COORDINATION (for management complexity):
- provider_team_size: single/small/moderate/large_multidisciplinary
- care_setting_complexity: single/multiple/coordinated/fragmented
- patient_compliance_factors: excellent/good/fair/poor
- family_support_system: strong/adequate/limited/absent
- care_barriers: none/transportation/financial/language/cognitive

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "{document_type}",
    "category": "medical",
    "extraction_confidence": 0.85,

    "clinical_severity": {{
        "primary_diagnosis": "L2 compression fracture with neurological involvement",
        "diagnostic_certainty": "definitive",
        "injury_severity_clinical": "major",
        "comorbidity_impact": "moderate",
        "complications_present": "minor"
    }},

    "treatment_requirements": {{
        "current_treatment_phase": "subacute",
        "treatment_modalities": "conservative",
        "medication_complexity": "moderate",
        "procedure_intensity": "outpatient",
        "specialist_involvement": "multiple"
    }},

    "functional_status": {{
        "current_functional_capacity": "moderately_impaired",
        "work_related_restrictions": "modified_duty",
        "activities_daily_living": "independent",
        "mobility_status": "ambulatory_aids",
        "cognitive_function_impact": "none"
    }},

    "recovery_indicators": {{
        "treatment_response": "good",
        "recovery_trajectory": "improving",
        "maximum_medical_improvement": "expected_6months",
        "permanent_impairment_potential": "minimal",
        "recurrence_risk": "low"
    }},

    "cost_drivers": {{
        "ongoing_care_intensity": "moderate",
        "equipment_needs": "basic",
        "home_health_requirements": "occasional",
        "facility_care_needs": "outpatient",
        "pharmaceutical_costs": "moderate"
    }},

    "care_coordination": {{
        "provider_team_size": "moderate",
        "care_setting_complexity": "multiple",
        "patient_compliance_factors": "good",
        "family_support_system": "adequate",
        "care_barriers": "transportation"
    }},

    "key_medical_quotes": ["relevant medical excerpts that support analysis"],
    "actuarial_relevance_score": 0.90
}}

DOCUMENT TEXT:
{document_text}
"""