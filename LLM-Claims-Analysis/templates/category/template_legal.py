# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_legal_category_prompt (document_text, document_type):
  """
  Optimized Legal Category Template for documents:
  - attorney_correspondence, court_filings, depositions, expert_witness_reports
  - settlement_agreements, subrogation_files, legal_pleadings, arbitration_records
  """

  return f"""
You are processing a {document_type} for workers' compensation actuarial analysis.

Extract LEGAL INFORMATION for ACTUARIAL USE:

LIABILITY FRAMEWORK (for coverage and fault allocation):
- primary_liability_theory: workers_comp/third_party/product_liability/premises_liability
- fault_determination_status: established/disputed/pending/denied
- coverage_position: accepted/disputed/excluded/investigating
- compensability_ruling: compensable/non_compensable/pending/appealed
- subrogation_potential: none/possible/probable/active_pursuit

LITIGATION DYNAMICS (for claim management and costs):
- litigation_stage: pre_suit/filed/discovery/mediation/trial/appeal
- case_complexity: routine/moderate/complex/highly_complex
- attorney_involvement_level: monitoring/active_defense/aggressive_litigation
- motion_practice_intensity: minimal/moderate/active/extensive
- discovery_scope: limited/standard/extensive/contentious

DAMAGES FRAMEWORK (for reserving and settlement):
- claimed_damage_types: medical_only/wage_loss/permanent_disability/pain_suffering
- damage_calculation_method: actual_costs/economic_model/life_care_plan/jury_verdict_research
- settlement_demand_progression: initial/revised/final/no_demand
- settlement_authority_level: adjuster/supervisor/management/corporate
- trial_exposure_assessment: low/moderate/high/catastrophic

EXPERT TESTIMONY (for technical evaluation):
- medical_expert_alignment: supportive/neutral/adverse/conflicting
- vocational_expert_findings: supports_rtw/limited_capacity/total_disability
- economic_expert_methodology: conservative/moderate/aggressive/speculative
- causation_expert_opinions: definitive/probable/possible/disputed
- expert_credibility_assessment: strong/adequate/weak/damaged

RESOLUTION PROBABILITY (for settlement planning):
- settlement_likelihood_current: very_high/high/moderate/low/very_low
- settlement_timeline_estimate: immediate/3_months/6_months/1_year/trial_required
- mediation_potential: scheduled/likely/possible/declined/failed
- trial_risk_factors: venue/judge/jury_pool/case_facts/expert_testimony
- appellate_risk: minimal/moderate/high/automatic_appeal

COST PROJECTIONS (for defense expense reserves):
- defense_costs_to_date: dollar_amount_incurred
- projected_defense_costs: conservative/moderate/aggressive_estimate
- expert_witness_budget: minimal/standard/extensive/specialized
- trial_preparation_costs: discovery_only/standard_prep/complex_prep/multi_week_trial
- post_trial_costs: minimal/standard/appeal_likely/appellate_intensive

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "{document_type}",
    "category": "legal",
    "extraction_confidence": 0.80,

    "liability_framework": {{
        "primary_liability_theory": "workers_comp",
        "fault_determination_status": "established",
        "coverage_position": "accepted",
        "compensability_ruling": "compensable",
        "subrogation_potential": "possible"
    }},

    "litigation_dynamics": {{
        "litigation_stage": "discovery",
        "case_complexity": "complex",
        "attorney_involvement_level": "active_defense",
        "motion_practice_intensity": "moderate",
        "discovery_scope": "extensive"
    }},

    "damages_framework": {{
        "claimed_damage_types": ["medical_expenses", "wage_loss", "permanent_disability"],
        "damage_calculation_method": "economic_model",
        "settlement_demand_progression": "revised",
        "settlement_authority_level": "management",
        "trial_exposure_assessment": "moderate"
    }},

    "expert_testimony": {{
        "medical_expert_alignment": "neutral",
        "vocational_expert_findings": "limited_capacity",
        "economic_expert_methodology": "moderate",
        "causation_expert_opinions": "probable",
        "expert_credibility_assessment": "adequate"
    }},

    "resolution_probability": {{
        "settlement_likelihood_current": "moderate",
        "settlement_timeline_estimate": "6_months",
        "mediation_potential": "likely",
        "trial_risk_factors": ["case_facts", "expert_testimony"],
        "appellate_risk": "moderate"
    }},

    "cost_projections": {{
        "defense_costs_to_date": 45000,
        "projected_defense_costs": "moderate_estimate",
        "expert_witness_budget": "standard",
        "trial_preparation_costs": "standard_prep",
        "post_trial_costs": "standard"
    }},

    "key_legal_quotes": ["relevant legal excerpts that support analysis"],
    "actuarial_relevance_score": 0.85
}}

DOCUMENT TEXT:
{document_text}
"""