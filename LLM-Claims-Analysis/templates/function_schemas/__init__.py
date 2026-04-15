# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# templates/function_schemas/__init__.py

"""
Function schemas for LLM function calling / structured output.

This package contains JSON schema definitions used to enforce structured output
from LLM API calls:

- Stage 1 schemas: Document-specific extraction schemas (one per document type)
- Stage 2 schema: Final aggregation schema (stage2_aggregation.json)

These schemas are loaded by ClassLoadFunctionSchemas in the main processing pipeline
and passed to the LLM API via function calling to ensure JSON compliance.
"""

__all__ = []

# Note: Schemas are JSON files, not Python modules, so there are no imports.
# This __init__.py file serves to:
# 1. Make function_schemas a proper Python package
# 2. Provide package-level documentation
# 3. Maintain consistency with sibling directories (category/, specialized/, universal/)