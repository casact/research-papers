# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

def create_financial_category_prompt (document_text, document_type):
  """
  Optimized Financial Category Template for documents:
  - wage_statements, financial_records, business_interruption_documentation
  - loss_calculations, audit_reports, tax_returns, employment_verification
  - benefit_statements, payroll_records, economic_loss_reports
  """

  return f"""
You are processing a {document_type} for workers' compensation actuarial analysis.

Extract FINANCIAL INFORMATION for ACTUARIAL USE:

EARNINGS ANALYSIS (for benefit calculations and wage replacement):
- average_weekly_wage_calculation: dollar_amount_and_methodology
- wage_verification_reliability: high/medium/low/insufficient_documentation
- earnings_trend_pattern: increasing/stable/decreasing/irregular
- overtime_earnings_significance: none/minimal/moderate/substantial/primary_income
- multiple_employment_status: single_employer/concurrent_employment/seasonal_multiple

EMPLOYMENT STABILITY (for long-term benefit projections):
- job_tenure_stability: very_stable/stable/moderate/unstable/temporary
- industry_employment_outlook: growing/stable/declining/volatile
- skill_transferability: highly_transferable/transferable/limited/job_specific/obsolete
- career_advancement_potential: high/moderate/limited/none/declining
- economic_vulnerability_factors: none/age/education/location/industry_decline

FINANCIAL_PRESSURE_ASSESSMENT (for claim behavior prediction):
- debt_service_burden: low/moderate/high/excessive/unsustainable
- essential_expense_coverage: comfortable/adequate/tight/insufficient/crisis
- liquid_asset_availability: substantial/adequate/limited/minimal/none
- credit_access_status: excellent/good/fair/poor/no_access
- financial_stress_indicators: none/minimal/moderate/significant/severe

BENEFIT_OPTIMIZATION_ANALYSIS (for potential overpayment):
- workers_comp_vs_wages_ratio: less_than_wages/comparable/exceeds_net_wages/significantly_exceeds
- disability_benefits_coordination: none/ssi_ssd/other_disability/multiple_sources
- return_to_work_financial_incentive: strong/moderate/weak/neutral/disincentive
- benefit_duration_sensitivity: short_term_preferred/indifferent/long_term_preferred
- financial_recovery_motivation: high/moderate/mixed/low/counterproductive

ECONOMIC_LOSS_PROJECTIONS (for settlement and reserving):
- historical_earnings_reliability: excellent/good/adequate/questionable/poor
- future_earning_capacity_factors: positive/stable/declining/severely_impaired
- inflation_adjustment_needs: minimal/standard/above_average/significant
- economic_multiplier_factors: none/education/experience/geographic/industry
- life_expectancy_economic_factors: standard/enhanced/reduced/significantly_reduced

BUSINESS_IMPACT_ANALYSIS (for employer experience rating):
- business_size_impact: minimal/moderate/significant/severe/business_threatening
- key_person_value: routine_employee/important/critical/irreplaceable
- replacement_cost_factors: easy/moderate/difficult/very_difficult/impossible
- productivity_impact_duration: short_term/medium_term/long_term/permanent
- competitive_position_effect: none/minimal/moderate/significant/severe

Return ONLY valid JSON (use NESTED structure that matches the sections above):
{{
    "document_type": "{document_type}",
    "category": "financial",
    "extraction_confidence": 0.85,

    "earnings_analysis": {{
        "average_weekly_wage_calculation": {{"amount": 1250, "methodology": "52_week_average"}},
        "wage_verification_reliability": "high",
        "earnings_trend_pattern": "stable",
        "overtime_earnings_significance": "moderate",
        "multiple_employment_status": "single_employer"
    }},

    "employment_stability": {{
        "job_tenure_stability": "stable",
        "industry_employment_outlook": "stable",
        "skill_transferability": "transferable",
        "career_advancement_potential": "moderate",
        "economic_vulnerability_factors": "none"
    }},

    "financial_pressure_assessment": {{
        "debt_service_burden": "moderate",
        "essential_expense_coverage": "adequate",
        "liquid_asset_availability": "limited",
        "credit_access_status": "good",
        "financial_stress_indicators": "minimal"
    }},

    "benefit_optimization_analysis": {{
        "workers_comp_vs_wages_ratio": "less_than_wages",
        "disability_benefits_coordination": "none",
        "return_to_work_financial_incentive": "strong",
        "benefit_duration_sensitivity": "short_term_preferred",
        "financial_recovery_motivation": "high"
    }},

    "economic_loss_projections": {{
        "historical_earnings_reliability": "good",
        "future_earning_capacity_factors": "stable",
        "inflation_adjustment_needs": "standard",
        "economic_multiplier_factors": ["experience", "geographic"],
        "life_expectancy_economic_factors": "standard"
    }},

    "business_impact_analysis": {{
        "business_size_impact": "moderate",
        "key_person_value": "important",
        "replacement_cost_factors": "moderate",
        "productivity_impact_duration": "medium_term",
        "competitive_position_effect": "minimal"
    }},

    "key_financial_quotes": ["relevant financial excerpts that support analysis"],
    "actuarial_relevance_score": 0.90
}}

DOCUMENT TEXT:
{document_text}
"""