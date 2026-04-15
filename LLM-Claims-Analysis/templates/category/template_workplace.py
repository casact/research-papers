# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_workplace_category_prompt (document_text, document_type):
  """
  Optimized Workplace Category Template for documents:
  - employer_incident_reports, safety_training_records, job_descriptions
  - return_to_work_documentation, osha_reports, workplace_safety_inspections
  - employee_handbook_excerpts, disciplinary_records, ergonomic_assessments
  """

  return f"""
You are processing a {document_type} for workers' compensation actuarial analysis.

Extract WORKPLACE INFORMATION for ACTUARIAL USE:

JOB RISK PROFILE (for ratemaking and risk assessment):
- physical_demand_level: sedentary/light/medium/heavy/very_heavy
- hazard_exposure_categories: chemical/biological/physical/ergonomic/psychosocial
- environmental_risk_factors: indoor_controlled/outdoor_variable/extreme_conditions/multiple_locations
- equipment_machinery_risk: minimal/moderate/significant/high_risk/specialized_equipment
- height_confined_space_risk: none/minimal/moderate/significant/extreme

SAFETY PROGRAM EFFECTIVENESS (for experience modification):
- safety_training_comprehensiveness: comprehensive/adequate/basic/minimal/absent
- safety_training_frequency: continuous/regular/periodic/infrequent/none
- safety_equipment_adequacy: comprehensive/adequate/basic/inadequate/absent
- safety_protocol_enforcement: strict/consistent/inconsistent/minimal/none
- safety_culture_strength: strong/moderate/developing/weak/poor

INCIDENT CAUSATION (for prevention and liability):
- primary_cause_category: human_error/equipment_failure/environmental/procedural/organizational
- contributing_factors: none/single/multiple/systemic/complex_interaction
- preventability_assessment: easily_preventable/preventable/difficult_to_prevent/unpreventable
- similar_incident_history: none/rare/occasional/frequent/chronic_problem
- root_cause_depth: surface_level/intermediate/comprehensive/systemic_analysis

REGULATORY COMPLIANCE (for liability and penalties):
- osha_compliance_status: full_compliance/minor_violations/serious_violations/willful_violations
- industry_standard_adherence: exceeds/meets/partially_meets/below_standard/non_compliant
- regulatory_inspection_history: clean/minor_issues/moderate_concerns/serious_violations/pattern_violations
- required_corrections_status: not_applicable/completed/in_progress/overdue/ignored
- citation_severity_level: none/other_than_serious/serious/willful/repeat_violation

EMPLOYEE FACTORS (for individual risk assessment):
- experience_tenure: very_experienced/experienced/moderate/new/inexperienced
- training_completion_status: fully_current/mostly_current/partially_current/expired/never_completed
- performance_history: excellent/good/satisfactory/marginal/poor
- safety_record: excellent/good/average/concerning/poor
- physical_fitness_job_match: excellent/good/adequate/marginal/inadequate

RETURN_TO_WORK_CAPACITY (for disability management):
- modified_duty_availability: comprehensive_program/good_options/limited_options/minimal/none
- accommodation_capability: fully_accommodating/very_accommodating/moderately_accommodating/limited/unable
- employer_cooperation_level: excellent/good/adequate/reluctant/uncooperative
- union_labor_relations: very_supportive/supportive/neutral/challenging/adversarial
- job_modification_feasibility: highly_feasible/feasible/somewhat_feasible/difficult/impossible

ORGANIZATIONAL FACTORS (for claim outcomes):
- management_safety_commitment: exceptional/strong/adequate/weak/poor
- employee_morale_engagement: high/good/adequate/low/poor
- communication_effectiveness: excellent/good/adequate/poor/very_poor
- incident_reporting_culture: open_proactive/open/adequate/reluctant/suppressive
- claim_history_pattern: excellent/good/average/concerning/poor

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "{document_type}",
    "category": "workplace",
    "extraction_confidence": 0.80,

    "job_risk_profile": {{
        "physical_demand_level": "heavy",
        "hazard_exposure_categories": ["physical", "ergonomic"],
        "environmental_risk_factors": "outdoor_variable",
        "equipment_machinery_risk": "significant",
        "height_confined_space_risk": "minimal"
    }},

    "safety_program_effectiveness": {{
        "safety_training_comprehensiveness": "adequate",
        "safety_training_frequency": "regular",
        "safety_equipment_adequacy": "adequate",
        "safety_protocol_enforcement": "consistent",
        "safety_culture_strength": "moderate"
    }},

    "incident_causation": {{
        "primary_cause_category": "human_error",
        "contributing_factors": "multiple",
        "preventability_assessment": "preventable",
        "similar_incident_history": "rare",
        "root_cause_depth": "intermediate"
    }},

    "regulatory_compliance": {{
        "osha_compliance_status": "minor_violations",
        "industry_standard_adherence": "meets",
        "regulatory_inspection_history": "minor_issues",
        "required_corrections_status": "completed",
        "citation_severity_level": "other_than_serious"
    }},

    "employee_factors": {{
        "experience_tenure": "experienced",
        "training_completion_status": "mostly_current",
        "performance_history": "good",
        "safety_record": "good",
        "physical_fitness_job_match": "adequate"
    }},

    "return_to_work_capacity": {{
        "modified_duty_availability": "good_options",
        "accommodation_capability": "very_accommodating",
        "employer_cooperation_level": "good",
        "union_labor_relations": "supportive",
        "job_modification_feasibility": "feasible"
    }},

    "organizational_factors": {{
        "management_safety_commitment": "strong",
        "employee_morale_engagement": "good",
        "communication_effectiveness": "adequate",
        "incident_reporting_culture": "open",
        "claim_history_pattern": "average"
    }},

    "key_workplace_quotes": ["relevant workplace excerpts that support analysis"],
    "actuarial_relevance_score": 0.85
}}

DOCUMENT TEXT:
{document_text}
"""