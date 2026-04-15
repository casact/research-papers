# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_investigation_category_prompt (document_text, document_type):
  """
  Optimized Investigation Category Template for documents:
  - investigation_reports, surveillance_reports, witness_statements
  - scene_investigation, background_checks, fraud_investigation_reports
  - special_investigation_unit_reports, accident_reconstruction_reports
  """

  return f"""
You are processing a {document_type} for workers' compensation actuarial analysis.

Extract INVESTIGATION INFORMATION for ACTUARIAL USE:

INCIDENT VERIFICATION (for claim validity and causation):
- incident_occurrence_verification: confirmed/partially_confirmed/contradicted/cannot_determine
- timeline_consistency_analysis: fully_consistent/minor_discrepancies/major_contradictions/fabricated
- location_scene_consistency: verified/partially_verified/inconsistent/suspicious
- mechanism_plausibility: highly_plausible/plausible/questionable/implausible
- witness_corroboration_strength: strong/moderate/weak/contradictory/none

CREDIBILITY INDICATORS (for fraud assessment):
- claimant_credibility_rating: high/moderate/questionable/low/very_low
- statement_consistency_pattern: consistent/minor_variations/significant_changes/contradictory
- behavioral_observations: cooperative/evasive/defensive/hostile/coaching_evidence
- documentation_quality: complete/adequate/incomplete/suspicious/fabricated
- corroborating_evidence: strong/adequate/weak/absent/contradictory

FRAUD RISK ASSESSMENT (for claim integrity):
- fraud_indicators_count: none/minor/moderate/significant/extensive
- red_flag_severity: none/low/medium/high/critical
- financial_motivation_strength: none/minimal/moderate/strong/compelling
- prior_claim_history: none/normal/elevated/excessive/pattern_fraud
- collusion_potential: none/unlikely/possible/probable/evident

CAUSATION ANALYSIS (for work-relatedness):
- work_relatedness_evidence: definitive/probable/possible/doubtful/excluded
- alternative_causation_factors: none/unlikely/possible/probable/primary_cause
- pre_existing_condition_impact: none/minimal/contributory/primary/pre_existing_only
- temporal_relationship: immediate/delayed_reasonable/delayed_questionable/no_relationship
- exposure_documentation: well_documented/adequate/limited/poor/absent

INVESTIGATION QUALITY (for confidence assessment):
- investigation_thoroughness: comprehensive/adequate/limited/superficial/inadequate
- investigator_competence: highly_qualified/qualified/adequate/questionable/inadequate
- evidence_preservation: excellent/good/adequate/poor/compromised
- timeline_of_investigation: immediate/prompt/delayed/significantly_delayed/too_late
- methodology_appropriateness: best_practice/standard/adequate/questionable/flawed

RISK MITIGATION (for claim management):
- surveillance_findings: consistent_with_claims/minor_inconsistencies/major_inconsistencies/contradictory
- social_media_evidence: supports_claim/neutral/raises_questions/contradicts_claim
- employment_verification: confirmed/partially_confirmed/inconsistent/suspicious
- medical_consistency: consistent/minor_issues/significant_concerns/major_contradictions
- witness_reliability: highly_reliable/reliable/questionable/unreliable/compromised

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "{document_type}",
    "category": "investigation",
    "extraction_confidence": 0.80,

    "incident_verification": {{
        "incident_occurrence_verification": "confirmed",
        "timeline_consistency_analysis": "minor_discrepancies",
        "location_scene_consistency": "verified",
        "mechanism_plausibility": "plausible",
        "witness_corroboration_strength": "moderate"
    }},

    "credibility_indicators": {{
        "claimant_credibility_rating": "moderate",
        "statement_consistency_pattern": "minor_variations",
        "behavioral_observations": "cooperative",
        "documentation_quality": "adequate",
        "corroborating_evidence": "adequate"
    }},

    "fraud_risk_assessment": {{
        "fraud_indicators_count": "minor",
        "red_flag_severity": "low",
        "financial_motivation_strength": "minimal",
        "prior_claim_history": "normal",
        "collusion_potential": "unlikely"
    }},

    "causation_analysis": {{
        "work_relatedness_evidence": "probable",
        "alternative_causation_factors": "unlikely",
        "pre_existing_condition_impact": "contributory",
        "temporal_relationship": "immediate",
        "exposure_documentation": "adequate"
    }},

    "investigation_quality": {{
        "investigation_thoroughness": "adequate",
        "investigator_competence": "qualified",
        "evidence_preservation": "good",
        "timeline_of_investigation": "prompt",
        "methodology_appropriateness": "standard"
    }},

    "risk_mitigation": {{
        "surveillance_findings": "consistent_with_claims",
        "social_media_evidence": "neutral",
        "employment_verification": "confirmed",
        "medical_consistency": "consistent",
        "witness_reliability": "reliable"
    }},

    "key_investigation_quotes": ["relevant investigative excerpts that support analysis"],
    "actuarial_relevance_score": 0.85
}}

DOCUMENT TEXT:
{document_text}
"""