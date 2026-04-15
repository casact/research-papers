# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# =============================================================================
# prompt_templates/universal/__init__.py
# =============================================================================

"""
Universal fallback prompt template for unknown document types.
Handles any document type not covered by specialized or category templates.
"""

from .template_universal import create_universal_fallback_prompt

__all__ = [
    'create_universal_fallback_prompt'
]