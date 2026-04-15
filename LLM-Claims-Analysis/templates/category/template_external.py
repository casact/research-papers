# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_external_category_prompt (document_text, document_type):
  """
  Optimized External Category Template for documents:
  - police_reports, weather_reports, news_articles, government_records
  - regulatory_correspondence, environmental_assessments, traffic_reports
  - public_records, municipal_reports, third_party_documentation
  """

  return f"""
You are processing a {document_type} for workers' compensation actuarial analysis.

Extract EXTERNAL INFORMATION for ACTUARIAL USE:

ENVIRONMENTAL_CONDITIONS (for causation and contributing factors):
- weather_impact_assessment: no_impact/minor_impact/moderate_impact/significant_impact/primary_factor
- visibility_lighting_conditions: optimal/good/fair/poor/hazardous
- road_surface_conditions: optimal/good/fair/poor/hazardous
- temperature_exposure_factors: comfortable/challenging/difficult/extreme/life_threatening
- seasonal_environmental_factors: none/minor/moderate/significant/extreme

THIRD_PARTY_LIABILITY (for subrogation and fault allocation):
- third_party_involvement_level: none/minimal/moderate/significant/primary_cause
- third_party_fault_evidence: none/minimal/moderate/strong/definitive
- subrogation_recovery_potential: none/low/moderate/high/excellent
- product_liability_indicators: none/possible/probable/strong/definitive
- premises_liability_factors: none/possible/probable/strong/definitive

OFFICIAL_DETERMINATIONS (for liability support):
- law_enforcement_fault_finding: no_fault_assigned/claimant_fault/third_party_fault/shared_fault/investigation_pending
- regulatory_violation_findings: none/minor/moderate/serious/willful
- government_agency_conclusions: supports_claim/neutral/raises_questions/contradicts_claim/denies_claim
- citation_enforcement_actions: none/warnings/fines/criminal_charges/license_suspension
- official_cause_determination: supports_work_relation/neutral/questions_work_relation/non_work_related

PUBLIC_SAFETY_CONTEXT (for risk assessment and pattern analysis):
- hazard_identification: none/temporary/ongoing/systemic/widespread
- public_warning_systems: not_applicable/adequate/inadequate/absent/failed
- emergency_response_adequacy: excellent/good/adequate/poor/failed
- incident_prevention_measures: comprehensive/adequate/minimal/absent/ignored
- similar_incident_pattern: isolated/rare/occasional/frequent/epidemic

DOCUMENTATION_RELIABILITY (for evidence quality):
- official_report_completeness: comprehensive/complete/adequate/incomplete/minimal
- investigation_methodology_quality: excellent/good/standard/questionable/poor
- evidence_collection_adequacy: comprehensive/adequate/limited/poor/compromised
- witness_interview_quality: thorough/adequate/limited/superficial/absent
- report_timeliness: immediate/prompt/standard/delayed/significantly_delayed

EXTERNAL_CORROBORATION (for claim validation):
- independent_verification_level: multiple_sources/single_source/limited/minimal/none
- media_coverage_accuracy: accurate/mostly_accurate/some_inaccuracies/inaccurate/misleading
- public_record_consistency: fully_consistent/mostly_consistent/some_inconsistencies/inconsistent/contradictory
- expert_third_party_opinions: strongly_supportive/supportive/neutral/questioning/contradictory
- community_witness_reliability: highly_reliable/reliable/mixed/questionable/unreliable

BROADER_IMPACT_FACTORS (for trend and pattern analysis):
- incident_frequency_pattern: isolated/rare/periodic/increasing/chronic_problem
- geographic_risk_concentration: isolated_location/local_area/regional/statewide/national_pattern
- seasonal_temporal_patterns: no_pattern/seasonal/cyclical/trending/crisis_period
- industry_wide_implications: company_specific/local_industry/industry_wide/cross_industry/systemic
- regulatory_response_adequacy: proactive/responsive/reactive/delayed/inadequate

SYSTEMIC_FACTORS (for experience rating implications):
- infrastructure_adequacy: excellent/good/adequate/poor/failing
- maintenance_inspection_history: excellent/good/adequate/concerning/poor
- known_hazard_management: proactive/responsive/reactive/inadequate/negligent
- public_private_coordination: excellent/good/adequate/poor/absent
- risk_communication_effectiveness: excellent/good/adequate/poor/failed

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{
  "document_type": "{document_type}",
    "category": "external",
    "extraction_confidence": 0.75,

    "environmental_conditions": {
  "weather_impact_assessment": "moderate_impact",
        "visibility_lighting_conditions": "poor",
        "road_surface_conditions": "fair",
        "temperature_exposure_factors": "challenging",
        "seasonal_environmental_factors": "moderate"
    },

    "third_party_liability": {
  "third_party_involvement_level": "significant",
        "third_party_fault_evidence": "strong",
        "subrogation_recovery_potential": "high",
        "product_liability_indicators": "none",
        "premises_liability_factors": "possible"
    },

    "official_determinations": {
  "law_enforcement_fault_finding": "third_party_fault",
        "regulatory_violation_findings": "moderate",
        "government_agency_conclusions": "supports_claim",
        "citation_enforcement_actions": "fines",
        "official_cause_determination": "supports_work_relation"
    },

    "public_safety_context": {
  "hazard_identification": "temporary",
        "public_warning_systems": "adequate",
        "emergency_response_adequacy": "good",
        "incident_prevention_measures": "adequate",
        "similar_incident_pattern": "rare"
    },

    "documentation_reliability": {
  "official_report_completeness": "complete",
        "investigation_methodology_quality": "good",
        "evidence_collection_adequacy": "adequate",
        "witness_interview_quality": "adequate",
        "report_timeliness": "prompt"
    },

    "external_corroboration": {
  "independent_verification_level": "single_source",
        "media_coverage_accuracy": "mostly_accurate",
        "public_record_consistency": "mostly_consistent",
        "expert_third_party_opinions": "supportive",
        "community_witness_reliability": "reliable"
    },

    "broader_impact_factors": {
  "incident_frequency_pattern": "rare",
        "geographic_risk_concentration": "isolated_location",
        "seasonal_temporal_patterns": "no_pattern",
        "industry_wide_implications": "company_specific",
        "regulatory_response_adequacy": "responsive"
    },

    "systemic_factors": {
  "infrastructure_adequacy": "adequate",
        "maintenance_inspection_history": "good",
        "known_hazard_management": "responsive",
        "public_private_coordination": "adequate",
        "risk_communication_effectiveness": "good"
    },

    "key_external_quotes": ["relevant external excerpts that support analysis"],
    "actuarial_relevance_score": 0.75
}

DOCUMENT TEXT:
{document_text}
"""