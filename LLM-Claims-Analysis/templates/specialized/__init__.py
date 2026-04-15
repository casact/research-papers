# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# =============================================================================
# prompt_templates/specialized/__init__.py
# =============================================================================

"""
Specialized prompt templates for the 6 core document types.
These templates are highly optimized for specific document formats.
"""

from .template_phone_transcript import create_phone_transcript_specialized_prompt
from .template_adjuster_notes import create_adjuster_notes_specialized_prompt
from .template_medical_provider import create_medical_provider_specialized_prompt
from .template_settlement_notes import create_settlement_notes_specialized_prompt
from .template_claimant_statement import create_claimant_statement_specialized_prompt
from .template_clinical_notes import create_clinical_notes_specialized_prompt

__all__ = [
    'create_phone_transcript_specialized_prompt',
    'create_adjuster_notes_specialized_prompt',
    'create_medical_provider_specialized_prompt',
    'create_settlement_notes_specialized_prompt',
    'create_claimant_statement_specialized_prompt',
    'create_clinical_notes_specialized_prompt'
]