# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# =========================================================================
# category/__init__.py
# =========================================================================

"""
Contents of category/__init__.py:
This file makes the directory a Python package and provides clean imports.
"""

from .template_medical import create_medical_category_prompt
from .template_legal import create_legal_category_prompt
from .template_investigation import create_investigation_category_prompt
from .template_workplace import create_workplace_category_prompt
from .template_financial import create_financial_category_prompt
from .template_external import create_external_category_prompt

__all__ = [
    'create_medical_category_prompt',
    'create_legal_category_prompt',
    'create_investigation_category_prompt',
    'create_workplace_category_prompt',
    'create_financial_category_prompt',
    'create_external_category_prompt',
]