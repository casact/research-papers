# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# =============================================================================
# prompt_templates/__init__.py
# =============================================================================

# Import all template functions and orchestrator
from .orchestrator import CategoryTemplateOrchestrator

# Specialized templates
from .specialized.template_phone_transcript import create_phone_transcript_specialized_prompt
from .specialized.template_adjuster_notes import create_adjuster_notes_specialized_prompt
from .specialized.template_medical_provider import create_medical_provider_specialized_prompt
from .specialized.template_settlement_notes import create_settlement_notes_specialized_prompt
from .specialized.template_claimant_statement import create_claimant_statement_specialized_prompt
from .specialized.template_clinical_notes import create_clinical_notes_specialized_prompt

# Category templates
from .category.template_medical import create_medical_category_prompt
from .category.template_legal import create_legal_category_prompt
from .category.template_investigation import create_investigation_category_prompt
from .category.template_workplace import create_workplace_category_prompt
from .category.template_financial import create_financial_category_prompt
from .category.template_external import create_external_category_prompt

# Universal template
from .universal.template_universal import create_universal_fallback_prompt

__all__ = [
  'CategoryTemplateOrchestrator',

  # Specialized templates
  'create_phone_transcript_specialized_prompt',
  'create_adjuster_notes_specialized_prompt',
  'create_medical_provider_specialized_prompt',
  'create_settlement_notes_specialized_prompt',
  'create_claimant_statement_specialized_prompt',
  'create_clinical_notes_specialized_prompt',

  # Category templates
  'create_medical_category_prompt',
  'create_legal_category_prompt',
  'create_investigation_category_prompt',
  'create_workplace_category_prompt',
  'create_financial_category_prompt',
  'create_external_category_prompt',

  # Universal template
  'create_universal_fallback_prompt'
]