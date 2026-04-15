# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

"""
Actuarial Definition Loader
Loads and manages variable definitions for LLM claims analysis pipeline
Handles smart prompt injection with tiered detail levels
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import logging


class ClassVariableDefinitions:
  """
  Loads and formats actuarial variable definitions for prompt injection

  Features:
  - Loads definitions from YAML file
  - Provides tiered detail levels (comprehensive, standard, minimal)
  - Smart document-specific variable filtering for Stage 1
  - Complete variable definitions for Stage 2
  - Formatting for prompt injection
  - Validation support (warnings only, no auto-correction)
  """

  def __init__ (self, definitions_path: str = None):
    """
    Initialize the definition loader

    Args:
        definitions_path: Path to YAML definitions file (optional)
    """
    # Initialize logger
    self.logger = logging.getLogger(self.__class__.__name__)

    if definitions_path is None:
      # Default: Look for YAML file in the same directory as this module
      module_dir = Path(__file__).parent
      self.definitions_path = module_dir / "module_variable_definitions.yaml"
    else:
      self.definitions_path = Path(definitions_path)

    self.definitions = self._load_definitions()
    self.doc_mapping = self.definitions.get('document_variable_mapping', {})

    # Variable counts for logging
    stage1_count = len(self.definitions.get('stage1_variables', {}))
    stage2_count = len(self.definitions.get('stage2_variables', {}))
    total_count = stage1_count + stage2_count

    self.logger.info(
      f"✅ ActuarialDefinitionLoader: Loaded {total_count} variable definitions "
      f"(Stage 1: {stage1_count}, Stage 2: {stage2_count})"
    )

  # LOADING & INITIALIZATION

  def _load_definitions (self) -> Dict:
    """Load definitions from YAML file"""
    try:
      with open(self.definitions_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
    except Exception as e:
      raise RuntimeError(f"Failed to load definitions from {self.definitions_path}: {e}")

  def _count_variables (self) -> int:
    """Count total variables defined"""
    stage1 = len(self.definitions.get('stage1_variables', {}))
    stage2 = len(self.definitions.get('stage2_variables', {}))
    return stage1 + stage2

  # STAGE 1: Document-Specific Variable Access

  def get_stage1_variables_for_document (
    self,
    document_type: str,
    include_secondary: bool = True
  ) -> List[str]:
    """
    Get list of variable names relevant to a document type

    Args:
        document_type: Type of document (e.g., 'phone_transcript')
        include_secondary: Whether to include secondary variables

    Returns:
        List of variable names
    """
    mapping = self.doc_mapping.get(document_type, {})
    variables = mapping.get('primary_variables', [])

    if include_secondary:
      variables.extend(mapping.get('secondary_variables', []))

    return variables

  def get_stage1_definition (self, variable_name: str) -> Optional[Dict]:
    """Get complete definition for a Stage 1 variable"""
    return self.definitions.get('stage1_variables', {}).get(variable_name)

  def format_stage1_definition (
    self,
    variable_name: str,
    detail_level: str = "standard"
  ) -> str:
    """
    Format a Stage 1 variable definition for prompt injection

    Args:
        variable_name: Name of the variable
        detail_level: "comprehensive", "standard", or "minimal"

    Returns:
        Formatted definition text
    """
    defn = self.get_stage1_definition(variable_name)
    if not defn:
      return f"  • {variable_name}: Definition not found"

    tier = defn.get('tier', 3)

    # Determine actual detail level based on tier
    if detail_level == "auto":
      if tier == 1:
        detail_level = "comprehensive"
      elif tier == 2:
        detail_level = "standard"
      else:
        detail_level = "minimal"

    parts = [f"  📌 {variable_name}"]
    parts.append(f"     {defn.get('description', 'No description')}")

    if detail_level == "minimal":
      # Just name and description
      if defn.get('data_type'):
        parts.append(f"     Type: {defn['data_type']}")

    elif detail_level == "standard":
      # Standard detail: rules and basic examples
      if defn.get('data_type'):
        parts.append(f"     Type: {defn['data_type']}")

      if defn.get('extraction_rules'):
        parts.append("     Extraction Rules:")
        for rule in defn['extraction_rules']:
          parts.append(f"       - {rule}")

      if defn.get('valid_values'):
        parts.append(f"     Valid Values: {', '.join(defn['valid_values'])}")

      if defn.get('examples') and len(defn['examples']) > 0:
        ex = defn['examples'][0]  # Show first example only
        parts.append(f"     Example: {ex.get('scenario', 'Example')}")
        if 'output' in ex:
          parts.append(f"       → Output: {ex['output']}")

    elif detail_level == "comprehensive":
      # Comprehensive: everything including wrong examples
      if defn.get('data_type'):
        parts.append(f"     Type: {defn['data_type']}")
        if defn.get('unit'):
          parts.append(f"     Unit: {defn['unit']}")

      if defn.get('extraction_rules'):
        parts.append("     Extraction Rules:")
        for rule in defn['extraction_rules']:
          parts.append(f"       • {rule}")

      if defn.get('valid_values'):
        parts.append(f"     Valid Values: {', '.join(defn['valid_values'])}")

      if defn.get('calculation_method'):
        parts.append(f"     Calculation: {defn['calculation_method']}")

      # Validation rules
      if defn.get('validation'):
        val = defn['validation']
        parts.append("     Validation:")
        if 'min_value' in val:
          parts.append(f"       Min: {val['min_value']}")
        if 'max_value' in val:
          parts.append(f"       Max: {val['max_value']}")
        if val.get('rationale_required'):
          parts.append("       Rationale: REQUIRED")

      # Examples with right and wrong
      if defn.get('examples'):
        parts.append("     Examples:")
        for ex in defn['examples']:
          parts.append(f"       📘 {ex.get('scenario', 'Scenario')}:")
          if 'input' in ex:
            parts.append(f"          Input: \"{ex['input']}\"")
          if 'output' in ex:
            parts.append(f"          ✅ Output: {ex['output']}")
          if 'rationale' in ex:
            parts.append(f"          Rationale: {ex['rationale']}")
          if 'wrong_output' in ex:
            parts.append(f"          ❌ Wrong: {ex['wrong_output']}")
          if 'correct_output' in ex:
            parts.append(f"          ✅ Correct: {ex['correct_output']}")
          if 'why_wrong' in ex:
            parts.append(f"          Why Wrong: {ex['why_wrong']}")
          parts.append("")

      # Critical rules
      if defn.get('critical_rule'):
        parts.append(f"     🚨 CRITICAL RULE:")
        parts.append(f"        {defn['critical_rule']}")

      # Consistency checks
      if defn.get('consistency_checks'):
        parts.append("     Consistency Checks:")
        for check in defn['consistency_checks']:
          if isinstance(check, dict):
            parts.append(f"       ✓ {check.get('check', '')}")
          else:
            parts.append(f"       ✓ {check}")

    return '\n'.join(parts)

  def build_stage1_definitions_section (
    self,
    document_type: str,
    mode: str = "tiered"
  ) -> str:
    """
    Build complete definitions section for Stage 1 prompt

    Args:
        document_type: Type of document being processed
        mode: "tiered" (use tier-based detail), "full" (all comprehensive),
              "critical_only" (tier 1 only)

    Returns:
        Formatted definitions section for prompt
    """
    parts = [
      # "═══════════════════════════════════════════════════════════",
      f"📋 VARIABLE DEFINITIONS FOR {document_type.upper()}",

      f"Definition Version: {self.definitions.get('metadata', {}).get('version', '1.0')}",
      "These definitions guide your extraction for this document type.",
      ""
    ]

    # Get relevant variables for this document type
    relevant_vars = self.get_stage1_variables_for_document(document_type)

    if not relevant_vars:
      parts.append("No specific variables defined for this document type.")
      parts.append("Use general extraction guidelines.")
      return '\n'.join(parts)

    # Group by tier
    tier1_vars = []
    tier2_vars = []
    tier3_vars = []

    for var_name in relevant_vars:
      defn = self.get_stage1_definition(var_name)
      if defn:
        tier = defn.get('tier', 3)
        if tier == 1:
          tier1_vars.append(var_name)
        elif tier == 2:
          tier2_vars.append(var_name)
        else:
          tier3_vars.append(var_name)

    # Format based on mode
    if mode == "tiered":
      # Tier 1: Comprehensive
      if tier1_vars:
        parts.append("🔴 CRITICAL VARIABLES (Extract with highest accuracy):")
        parts.append("")
        for var in tier1_vars:
          parts.append(self.format_stage1_definition(var, "comprehensive"))
          parts.append("")

      # Tier 2: Standard
      if tier2_vars:
        parts.append("🟡 IMPORTANT VARIABLES:")
        parts.append("")
        for var in tier2_vars:
          parts.append(self.format_stage1_definition(var, "standard"))
          parts.append("")

      # Tier 3: Minimal
      if tier3_vars:
        parts.append("🟢 BASIC VARIABLES:")
        parts.append("")
        for var in tier3_vars:
          parts.append(self.format_stage1_definition(var, "minimal"))
          parts.append("")

    elif mode == "critical_only":
      # Only Tier 1 variables
      if tier1_vars:
        parts.append("🔴 CRITICAL VARIABLES:")
        parts.append("")
        for var in tier1_vars:
          parts.append(self.format_stage1_definition(var, "comprehensive"))
          parts.append("")

    else:  # mode == "full"
      parts.append("All Relevant Variables (showing tier summaries):")
      parts.append("")
      for var_name in relevant_vars:
        defn = self.get_stage1_definition(var_name)
        if defn:
          parts.append(f"  • {var_name}: {defn.get('description', 'No description')}")

    # parts.append("═══════════════════════════════════════════════════════════")
    return '\n'.join(parts)

  def build_stage1_definitions_section_condensed (self, document_type: str) -> str:
    """
    Build CONDENSED definitions section for logging (not for LLM)

    Shows only:
    - Variable names
    - Types
    - No extraction rules, examples, or rationale requirements

    Args:
        document_type: Document type identifier

    Returns:
        Condensed formatted definitions for display
    """
    variables = self.get_stage1_variables_for_document(document_type)

    if not variables:
      return f"[No definitions for document type: {document_type}]"

    parts = [
      "─" * 63,
      f"📋 VARIABLE DEFINITIONS FOR {document_type.upper()} (condensed)",
      "─" * 63,
      f"Definition Version: {self.definitions.get('metadata', {}).get('version', '1.0')}",
      ""
    ]

    # Group by tier
    tier1_vars = [v for v in variables if v.get('tier') == 1]
    tier2_vars = [v for v in variables if v.get('tier') == 2]
    tier3_vars = [v for v in variables if v.get('tier') == 3]

    if tier1_vars:
      parts.append("🔴 TIER 1 - CRITICAL VARIABLES:")
      for var in tier1_vars:
        var_name = var.get('name', 'unknown')
        var_type = var.get('type', 'unknown')
        parts.append(f"  • {var_name} ({var_type})")
      parts.append("")

    if tier2_vars:
      parts.append("🟡 TIER 2 - IMPORTANT VARIABLES:")
      for var in tier2_vars:
        var_name = var.get('name', 'unknown')
        var_type = var.get('type', 'unknown')
        parts.append(f"  • {var_name} ({var_type})")
      parts.append("")

    if tier3_vars:
      parts.append("🟢 TIER 3 - SUPPORTING VARIABLES:")
      for var in tier3_vars:
        var_name = var.get('name', 'unknown')
        var_type = var.get('type', 'unknown')
        parts.append(f"  • {var_name} ({var_type})")
      parts.append("")

    parts.append(f"Total: {len(variables)} variables")
    parts.append("─" * 63)

    return '\n'.join(parts)

  # STAGE 2: Aggregated Variable Access

  def get_stage2_definition (self, variable_name: str) -> Optional[Dict]:
    """Get complete definition for a Stage 2 variable"""
    return self.definitions.get('stage2_variables', {}).get(variable_name)

  def format_stage2_definition (
    self,
    variable_name: str,
    detail_level: str = "auto"
  ) -> str:
    """
    Format a Stage 2 variable definition for prompt injection

    Args:
        variable_name: Name of the variable
        detail_level: "comprehensive", "standard", "minimal", or "auto"

    Returns:
        Formatted definition text
    """
    defn = self.get_stage2_definition(variable_name)
    if not defn:
      return f"  • {variable_name}: Definition not found"

    tier = defn.get('tier', 3)

    # Auto-select detail level based on tier
    if detail_level == "auto":
      if tier == 1:
        detail_level = "comprehensive"
      elif tier == 2:
        detail_level = "standard"
      else:
        detail_level = "minimal"

    parts = [f"  📊 {variable_name}"]
    parts.append(f"     {defn.get('description', 'No description')}")

    if detail_level == "minimal":
      if defn.get('data_type'):
        parts.append(f"     Type: {defn['data_type']}")

    elif detail_level == "standard":
      if defn.get('data_type'):
        parts.append(f"     Type: {defn['data_type']}")

      if defn.get('valid_values'):
        parts.append(f"     Valid Values: {', '.join(defn['valid_values'])}")

      if defn.get('aggregation_rules'):
        agg = defn['aggregation_rules']
        if 'logic' in agg:
          parts.append(f"     Aggregation: {agg['logic']}")

      if defn.get('examples') and len(defn['examples']) > 0:
        ex = defn['examples'][0]
        parts.append(f"     Example: {ex.get('scenario', 'Example')}")
        if 'output' in ex:
          parts.append(f"       → {ex['output']}")

    elif detail_level == "comprehensive":
      # Full detail for Tier 1 variables
      if defn.get('data_type'):
        parts.append(f"     Type: {defn['data_type']}")
        if defn.get('unit'):
          parts.append(f"     Unit: {defn['unit']}")

      if defn.get('valid_values'):
        parts.append(f"     Valid Values: {', '.join(defn['valid_values'])}")

      # Aggregation rules (critical for Stage 2)
      if defn.get('aggregation_rules'):
        agg = defn['aggregation_rules']
        parts.append("     Aggregation Rules:")

        if 'priority_logic' in agg:
          parts.append("       Priority Logic:")
          for line in agg['priority_logic'].strip().split('\n'):
            parts.append(f"         {line.strip()}")

        if 'logic' in agg:
          parts.append(f"       Logic: {agg['logic']}")

      # Source priority
      if defn.get('source_priority'):
        parts.append("     Source Priority:")
        for priority, source_info in sorted(defn['source_priority'].items()):
          if isinstance(source_info, dict):
            parts.append(f"       {priority}. {source_info.get('field', 'N/A')}")
            if 'condition' in source_info:
              parts.append(f"          Condition: {source_info['condition']}")
          else:
            parts.append(f"       {priority}. {source_info}")

      # Validation
      if defn.get('validation'):
        val = defn['validation']
        parts.append("     Validation:")
        if 'min_value' in val:
          parts.append(f"       Min: {val['min_value']}")
        if 'max_value' in val:
          parts.append(f"       Max: {val['max_value']}")
        if val.get('must_align_with_category'):
          parts.append("       Must align with category range")
        if val.get('rationale_required'):
          parts.append("       Rationale: REQUIRED")

      # Examples with Stage 1 data
      if defn.get('examples'):
        parts.append("     Examples:")
        for ex in defn['examples']:
          parts.append(f"       📘 {ex.get('scenario', 'Scenario')}:")

          if 'stage1_data' in ex:
            parts.append("         Stage 1 Data:")
            for key, val in ex['stage1_data'].items():
              parts.append(f"           - {key}: {val}")

          if 'correct_output' in ex:
            parts.append(f"         ✅ Correct Output: {ex['correct_output']}")
          if 'correct_category' in ex:
            parts.append(f"         ✅ Correct Category: {ex['correct_category']}")
          if 'rationale' in ex:
            parts.append(f"         Rationale: {ex['rationale']}")

          if 'wrong_output' in ex:
            parts.append(f"         ❌ Wrong Output: {ex['wrong_output']}")
          if 'why_wrong' in ex:
            parts.append(f"         Why Wrong: {ex['why_wrong']}")

          parts.append("")

      # Critical rules
      if defn.get('critical_rule'):
        parts.append(f"     🚨 CRITICAL RULE:")
        parts.append(f"        {defn['critical_rule']}")

      # Critical validation (for ultimate_cost_category)
      if defn.get('critical_validation'):
        parts.append(f"     🚨 CRITICAL VALIDATION:")
        for line in defn['critical_validation'].strip().split('\n'):
          parts.append(f"        {line.strip()}")

      # Consistency checks
      if defn.get('consistency_checks'):
        parts.append("     Validation Checks:")
        for check in defn['consistency_checks']:
          if isinstance(check, dict):
            check_rule = check.get('check', '')
            parts.append(f"       ✓ {check_rule}")
          else:
            parts.append(f"       ✓ {check}")

    return '\n'.join(parts)

  def build_stage2_definitions_section (self, mode: str = "tiered") -> str:
    """
    Build complete definitions section for Stage 2 prompt

    Args:
        mode: "tiered", "full", or "critical_only"

    Returns:
        Formatted definitions section
    """
    parts = [
      # "═══════════════════════════════════════════════════════════",
      "📋 STAGE 2: ACTUARIAL VARIABLE DEFINITIONS FOR AGGREGATION",

      f"Definition Version: {self.definitions.get('metadata', {}).get('version', '1.0')}",
      "These definitions guide how to aggregate Stage 1 features into final actuarial variables.",
      ""
    ]

    # Get all Stage 2 variables
    stage2_vars = self.definitions.get('stage2_variables', {})

    # Group by tier
    tier1_vars = []
    tier2_vars = []
    tier3_vars = []

    for var_name, defn in stage2_vars.items():
      tier = defn.get('tier', 3)
      if tier == 1:
        tier1_vars.append(var_name)
      elif tier == 2:
        tier2_vars.append(var_name)
      else:
        tier3_vars.append(var_name)

    if mode == "tiered":
      # Tier 1: Comprehensive (most important for Stage 2)
      if tier1_vars:
        parts.append("🔴 CRITICAL ACTUARIAL VARIABLES (Highest accuracy required):")
        parts.append("")
        for var in tier1_vars:
          parts.append(self.format_stage2_definition(var, "comprehensive"))
          parts.append("")

      # Tier 2: Standard
      if tier2_vars:
        parts.append("🟡 IMPORTANT RISK & MANAGEMENT VARIABLES:")
        parts.append("")
        for var in tier2_vars:
          parts.append(self.format_stage2_definition(var, "standard"))
          parts.append("")

      # Tier 3: Minimal
      if tier3_vars:
        parts.append("🟢 ADMINISTRATIVE VARIABLES:")
        parts.append("")
        for var in tier3_vars:
          parts.append(self.format_stage2_definition(var, "minimal"))
          parts.append("")

    elif mode == "critical_only":
      # Only Tier 1
      if tier1_vars:
        parts.append("🔴 CRITICAL ACTUARIAL VARIABLES:")
        parts.append("")
        for var in tier1_vars:
          parts.append(self.format_stage2_definition(var, "comprehensive"))
          parts.append("")

    else:  # mode == "full"
      parts.append("All Stage 2 Variables (showing tier summaries):")
      for var_name in stage2_vars.keys():
        defn = self.get_stage2_definition(var_name)
        parts.append(f"  • {var_name}: {defn.get('description', 'No description')}")

    # parts.append("═══════════════════════════════════════════════════════════")
    return '\n'.join(parts)

  def build_stage2_definitions_section_condensed (self) -> str:
    """
    Build CONDENSED Stage 2 definitions section for logging

    Returns:
        Condensed formatted definitions for display
    """
    stage2_vars = self.definitions.get('stage2_final_variables', [])

    if not stage2_vars:
      return "[No Stage 2 definitions available]"

    parts = [
      "═" * 63,
      "📋 STAGE 2: ACTUARIAL VARIABLE DEFINITIONS (condensed)",
      "═" * 63,
      f"Definition Version: {self.definitions.get('metadata', {}).get('version', '1.0')}",
      ""
    ]

    # Group by tier
    tier1_vars = [v for v in stage2_vars if v.get('tier') == 1]
    tier2_vars = [v for v in stage2_vars if v.get('tier') == 2]
    tier3_vars = [v for v in stage2_vars if v.get('tier') == 3]

    if tier1_vars:
      parts.append("🔴 TIER 1 - CRITICAL VARIABLES:")
      for var in tier1_vars:
        var_name = var.get('name', 'unknown')
        var_type = var.get('type', 'unknown')
        parts.append(f"  • {var_name} ({var_type})")
      parts.append("")

    if tier2_vars:
      parts.append("🟡 TIER 2 - IMPORTANT VARIABLES:")
      for var in tier2_vars:
        var_name = var.get('name', 'unknown')
        var_type = var.get('type', 'unknown')
        parts.append(f"  • {var_name} ({var_type})")
      parts.append("")

    if tier3_vars:
      parts.append("🟢 TIER 3 - SUPPORTING VARIABLES:")
      for var in tier3_vars:
        var_name = var.get('name', 'unknown')
        var_type = var.get('type', 'unknown')
        parts.append(f"  • {var_name} ({var_type})")
      parts.append("")

    parts.append(f"Total: {len(stage2_vars)} variables")
    parts.append("═" * 63)

    return '\n'.join(parts)

  def get_feature_importance (self, variable_name: str) -> Dict[str, float]:
    """
    Get feature_importance mappings for a Stage 2 variable.

    Returns dict mapping "document_type.stage1_var_name" -> importance_score

    Example:
        {
            "settlement_adjuster_notes.settlement_amount": 1.0,
            "medical_provider_letter.total_medical_cost": 0.85,
            "adjuster_notes_initial.initial_reserve_amount": 0.5
        }

    Args:
        variable_name: Stage 2 variable name

    Returns:
        Dict of feature importance scores, empty dict if not defined
    """
    stage2_vars = self.definitions.get('stage2_variables', {})

    if variable_name not in stage2_vars:
      return {}

    var_def = stage2_vars[variable_name]
    feature_importance = var_def.get('feature_importance', {})

    # Validate and log
    if feature_importance:
      self.logger.debug(
        f"Feature importance for {variable_name}: {len(feature_importance)} sources defined"
      )

      # Validate format (should be document_type.var_name: score)
      for key, score in feature_importance.items():
        if '.' not in key:
          self.logger.warning(
            f"Invalid feature_importance key '{key}' for {variable_name} - "
            f"should be 'document_type.stage1_var_name'"
          )

        if not isinstance(score, (int, float)) or score < 0 or score > 1:
          self.logger.warning(
            f"Invalid importance score {score} for {key} in {variable_name} - "
            f"should be float between 0.0 and 1.0"
          )

    return feature_importance

  # VALIDATION SUPPORT

  # def get_validation_rules (self, variable_name: str, stage: int = 1) -> Dict:
  #   """
  #   Get validation rules for a variable
  #
  #   Args:
  #       variable_name: Name of variable
  #       stage: 1 or 2
  #
  #   Returns:
  #       Dictionary of validation rules
  #   """
  #   if stage == 1:
  #     defn = self.get_stage1_definition(variable_name)
  #   else:
  #     defn = self.get_stage2_definition(variable_name)
  #
  #   if defn:
  #     return defn.get('validation', {})
  #   return {}
  #
  # def get_consistency_checks (self, variable_name: str, stage: int = 1) -> List:
  #   """
  #   Get consistency checks for a variable
  #
  #   Args:
  #       variable_name: Name of variable
  #       stage: 1 or 2
  #
  #   Returns:
  #       List of consistency check rules
  #   """
  #   if stage == 1:
  #     defn = self.get_stage1_definition(variable_name)
  #   else:
  #     defn = self.get_stage2_definition(variable_name)
  #
  #   if defn:
  #     return defn.get('consistency_checks', [])
  #   return []

  def validate_feature_importance_keys (self):
    """Validate that all feature_importance keys reference valid Stage 1 variables"""
    errors = []

    for stage2_var, defn in self.definitions['stage2_variables'].items():
      feature_imp = defn.get('feature_importance', {})

      for key in feature_imp.keys():
        if '.' in key:  # Document-specific format
          doc_type, var_name = key.split('.', 1)

          # Check document type exists
          if doc_type not in self.doc_mapping:
            errors.append(f"{stage2_var}: Unknown document type '{doc_type}' in key '{key}'")
            continue

          # Check variable is in that document's mapping
          doc_vars = self.doc_mapping[doc_type].get('primary_variables', [])
          doc_vars += self.doc_mapping[doc_type].get('secondary_variables', [])

          if var_name not in doc_vars:
            errors.append(
              f"{stage2_var}: Variable '{var_name}' not in "
              f"document_variable_mapping for '{doc_type}'"
            )

    if errors:
      self.logger.error("\n⚠️  VALIDATION ERRORS IN FEATURE_IMPORTANCE:")
      for error in errors:
        self.logger.error(f"  - {error}")
      return False

    self.logger.debug("✅ ActuarialDefinitionLoader: All feature_importance keys validated successfully")
    return True

  def validate_extraction (
    self,
    variable_name: str,
    value: Any,
    stage: int
  ) -> tuple[bool, list[str]]:
    """
    Validate an extracted variable value against its definition

    Args:
        variable_name: Name of the variable
        value: Extracted value to validate
        stage: Processing stage (1 or 2)

    Returns:
        (is_valid, warnings) - warnings list is empty if valid
    """
    warnings = []

    # Get definition
    if stage == 1:
      defn = self.get_stage1_definition(variable_name)
    else:
      defn = self.get_stage2_definition(variable_name)

    if not defn:
      warnings.append(f"No definition found for variable: {variable_name}")
      return False, warnings

    # Handle rationale wrapper
    if isinstance(value, dict) and 'value' in value:
      actual_value = value['value']
    else:
      actual_value = value

    # Check if value is None/empty
    if actual_value is None or actual_value == '':
      return True, []  # Empty values are allowed

    # Validate data type
    expected_type = defn.get('data_type')
    if expected_type:
      type_valid, type_warnings = self._validate_type(
        actual_value, expected_type, variable_name
      )
      if not type_valid:
        warnings.extend(type_warnings)

    # Validate against valid_values if specified
    valid_values = defn.get('valid_values')
    if valid_values and actual_value not in valid_values:
      warnings.append(
        f"{variable_name}: value '{actual_value}' not in valid values {valid_values}"
      )

    # Validate numeric ranges
    validation = defn.get('validation', {})
    if validation:
      range_warnings = self._validate_numeric_range(
        actual_value, validation, variable_name
      )
      warnings.extend(range_warnings)

    is_valid = len(warnings) == 0
    return is_valid, warnings

  def _validate_type (
    self,
    value: Any,
    expected_type: str,
    variable_name: str
  ) -> tuple[bool, list[str]]:
    """Validate value type"""
    warnings = []

    type_checks = {
      'string': str,
      'number': (int, float),
      'integer': int,
      'float': float,
      'boolean': bool,
      'array': list,
      'date': str  # Dates are strings in ISO format
    }

    expected_python_type = type_checks.get(expected_type)
    if expected_python_type and not isinstance(value, expected_python_type):
      warnings.append(
        f"{variable_name}: expected type {expected_type}, got {type(value).__name__}"
      )
      return False, warnings

    return True, warnings

  def _validate_numeric_range (
    self,
    value: Any,
    validation: dict,
    variable_name: str
  ) -> list[str]:
    """Validate numeric value against min/max ranges"""
    warnings = []

    if not isinstance(value, (int, float)):
      return warnings

    min_value = validation.get('min_value')
    max_value = validation.get('max_value')

    if min_value is not None and value < min_value:
      warnings.append(
        f"{variable_name}: value {value} below minimum {min_value}"
      )

    if max_value is not None and value > max_value:
      warnings.append(
        f"{variable_name}: value {value} above maximum {max_value}"
      )

    return warnings

  def validate_stage2_consistency (
    self,
    actuarial_variables: Dict
  ) -> tuple[bool, list[str]]:
    """
    Validate cross-variable consistency in Stage 2 output

    Args:
        actuarial_variables: Complete Stage 2 actuarial variables dict

    Returns:
        (is_valid, warnings)
    """
    warnings = []

    # Get cross-variable validation rules from definitions
    cross_rules = self.definitions.get('cross_variable_validation', {})

    # For now, just return True - can be expanded with specific rules
    # from the YAML definitions file

    return len(warnings) == 0, warnings

  def validate_ultimate_cost_category (
    self,
    prediction: float,
    category: str
  ) -> tuple[bool, str]:
    """
    Validate that ultimate_cost_category matches prediction

    Args:
        prediction: Ultimate cost prediction value
        category: Selected category

    Returns:
        (is_valid, message)
    """
    category_ranges = {
      "<25K": (0, 25000),
      "25K-50K": (25000, 50000),
      "50K-100K": (50000, 100000),
      "100K-150K": (100000, 150000),
      ">150K": (150000, float('inf'))
    }

    if category not in category_ranges:
      return False, f"Invalid category: {category}"

    min_val, max_val = category_ranges[category]

    if min_val <= prediction < max_val:
      return True, "Category matches prediction"
    else:
      return False, (
        f"MISMATCH: Prediction ${prediction:,.0f} does NOT fall in "
        f"category '{category}' range (${min_val:,.0f} - ${max_val:,.0f})"
      )

  def get_expected_category_for_amount (self, amount: float) -> str:
    """Get the correct category for a given amount"""
    if amount < 25000:
      return "<25K"
    elif amount < 50000:
      return "25K-50K"
    elif amount < 100000:
      return "50K-100K"
    elif amount < 150000:
      return "100K-150K"
    else:
      return ">150K"

  # UTILITY METHODS

  def get_definition_version (self) -> str:
    """Get the version of the definitions"""
    return self.definitions.get('metadata', {}).get('version', 'unknown')

  # def get_related_variables (self, variable_name: str, stage: int) -> List[str]:
  #   """Get list of variables related to this one"""
  #   if stage == 1:
  #     defn = self.get_stage1_definition(variable_name)
  #   else:
  #     defn = self.get_stage2_definition(variable_name)
  #
  #   if defn:
  #     return defn.get('related_variables', [])
  #   return []

  def get_all_stage1_variables (self) -> List[str]:
    """Get list of all Stage 1 variable names"""
    return list(self.definitions.get('stage1_variables', {}).keys())

  def get_all_stage2_variables (self) -> List[str]:
    """Get list of all Stage 2 variable names"""
    return list(self.definitions.get('stage2_variables', {}).keys())

  def get_cross_variable_validation_rules (self) -> Dict:
    """Get cross-variable validation rules"""
    return self.definitions.get('cross_variable_validation', {})
