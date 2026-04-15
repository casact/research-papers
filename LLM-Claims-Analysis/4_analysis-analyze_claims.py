# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

"""
LLM Claims Analysis with Two-Stage Processing - Script 4
Complete rewrite integrating modern infrastructure pattern from Scripts 1 & 2
Maintains exact compatibility with existing input/output formats and dataclasses

Exit Codes:
0 - Success
1 - Configuration error (missing config file, invalid YAML, missing API keys)
2 - Input/Output error (missing directories, file access issues)
3 - Processing error (LLM API failures, JSON parsing errors)
4 - Validation error (invalid JSON schema, missing required fields)

Usage Examples:
  python 4_analysis-analyze_claims.py --mode pipeline
  python 4_analysis-analyze_claims.py --mode pipeline --limit 5 --verbose
  python 4_analysis-analyze_claims.py --mode stage1 --input-dir ./data
"""

import json
import re

import yaml
import os
import sys
import logging
import time
import argparse
import traceback
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime, timedelta
from llm_providers import ClassCreateLLM
from time import sleep, perf_counter

from definitions.module_variable_definitions import ClassVariableDefinitions

# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_IO_ERROR = 2
EXIT_PROCESSING_ERROR = 3
EXIT_VALIDATION_ERROR = 4


class ClassConfig:
  """Centralized configuration management for Claims Analysis"""

  def __init__ (self, config_path: Optional[str] = None):
    self.config_path = config_path
    self.script_dir = Path(__file__).parent.resolve()
    self.config = self._load_config(config_path)

  def _load_config (self, config_path: Optional[str]) -> Dict:
    """Load claims analysis specific configuration file"""
    if config_path is None:
      config_file = self.script_dir / "config" / "4_analysis-analyze_claims.yaml"
    else:
      config_path_obj = Path(config_path)
      config_file = config_path_obj if config_path_obj.is_absolute() else self.script_dir / config_path

    print(f"🔧 Loading config from: {config_file}", file=sys.stderr)

    if not config_file.exists():
      print(f"❌ Config file not found at: {config_file}", file=sys.stderr)
      print("📝 Please create the 4_analysis-analyze_claims.yaml file", file=sys.stderr)
      print("   Use the provided configuration template", file=sys.stderr)
      sys.exit(EXIT_CONFIG_ERROR)

    try:
      with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

      # Validate required sections
      required_sections = ['api_settings', 'processing', 'logging', 'document_types',
                           'shared_settings']
      for section in required_sections:
        if section not in config:
          print(f"❌ Missing required config section: {section}", file=sys.stderr)

          sys.exit(EXIT_CONFIG_ERROR)

      print(f"✅ Config loaded successfully", file=sys.stderr)

      return config

    except Exception as e:
      print(f"❌ Error loading config: {e}", file=sys.stderr)

      sys.exit(EXIT_CONFIG_ERROR)

  def get_api_settings (self) -> Dict:
    return self.config['api_settings']

  def get_logging_settings (self) -> Dict:
    return self.config['logging']

  def get_processing_settings (self) -> Dict:
    return self.config['processing']

  def get_document_types (self) -> Dict:
    return self.config['document_types']

  def get_cloud_storage_settings (self) -> Dict:
    return self.config.get('cloud_storage', {})

  def get_output_structure (self) -> Dict:
    return self.config.get('output_structure', {})

  def get_filename_templates (self) -> Dict:
    return self.config.get('filename_templates', {})

  def get_stage1_settings (self) -> Dict:
    return self.config.get('stage1_settings', {})

  def get_stage2_settings (self) -> Dict:
    return self.config.get('stage2_settings', {})

  # Shared Settings (Used by both stages)
  def get_shared_settings (self) -> Dict:
    """Get shared settings used by both Stage 1 and Stage 2"""
    return self.config.get('shared_settings', {})

  def get_rationale_settings (self) -> Dict:
    """
    Get rationale system configuration (from shared_settings)
    The rationale system applies to both stages:
    - Stage 1: Rationale explains extraction from a single document
    - Stage 2: Rationale explains aggregation across multiple documents
    """
    shared = self.get_shared_settings()
    return shared.get('rationale_system', {})

  def get_templates_dir (self) -> str:
    """Get templates directory (from shared_settings)"""
    shared = self.get_shared_settings()
    return shared.get('templates_dir', 'templates')

  def get_temporal_weighting (self) -> Dict:
    """Get temporal weighting configuration"""
    return self.config.get('temporal_weighting', {
      'enabled': True,
      'missing_date_factor': 0.7
    })

  def get_compound_scoring (self) -> Dict:
    """Get compound scoring configuration"""
    return self.config.get('compound_scoring', {
      'enabled': True,
      'missing_importance_default': 0.5
    })

  def get_quality_control_settings (self) -> Dict:
    """Get quality control settings"""
    return self.config.get('quality_control', {})

  def get_validation_settings (self) -> Dict:
    """Get validation settings"""
    return self.config.get('validation', {})


class ClassLogger:
  """Streamlined logging with configurable debug options"""

  def __init__ (self, config: ClassConfig, json_mode: bool = False):
    self.config = config
    self.json_mode = json_mode
    self.log_settings = config.get_logging_settings()

    # Setup logger
    self.logger = logging.getLogger('ClaimsAnalysis')
    log_level = getattr(logging, self.log_settings.get('level', 'INFO'))
    self.logger.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_format = self.log_settings.get('console_format',
                                           '%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(logging.Formatter(console_format))
    self.logger.addHandler(console_handler)

    # Debug options
    debug_opts = self.log_settings.get('debug_options', {})
    self.show_api_prompts = debug_opts.get('show_api_prompts', False)
    self.show_api_responses = debug_opts.get('show_api_responses', False)
    self.show_stage1_details = debug_opts.get('show_stage1_details', False)
    self.show_stage2_details = debug_opts.get('show_stage2_details', False)
    self.show_variable_definitions = debug_opts.get('show_variable_definitions', True)
    self.max_prompt_chars = debug_opts.get('max_prompt_chars', 2000)
    self.max_response_chars = debug_opts.get('max_response_chars', 1500)

  def _truncate (self, text: str, max_chars: int) -> str:
    """Truncate text for display"""
    if len(text) <= max_chars:
      return text
    return text[:max_chars] + f"... [truncated, {len(text)} total chars]\n"

  def info (self, message: str):
    self.logger.info(message)

  def success (self, message: str):
    self.logger.info(f"✅ {message}")

  def warning (self, message: str):
    self.logger.warning(message)

  def error (self, message: str):
    self.logger.error(message)

  def debug (self, message: str):
    """Debug logging - only shows when log level is DEBUG"""
    self.logger.debug(message)

  def _emit_json (self, event_type: str, data: Dict):
    """Emit JSON event to stdout"""
    if self.json_mode:
      event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        **data
      }
      print(json.dumps(event), flush=True)

  def progress (self, message: str, current: int = None, total: int = None, **kwargs):
    """Log progress with optional JSON event"""
    self.logger.info(message)
    if self.json_mode and current is not None and total is not None:
      self._emit_json('progress', {
        'message': message,
        'current': current,
        'total': total,
        **kwargs
      })

  def milestone (self, message: str, status: str = 'info', **kwargs):
    """Log milestone with optional JSON event"""
    if status == 'success':
      self.logger.info(f"✅ {message}")
    elif status == 'error':
      self.logger.error(f"❌ {message}")
    elif status == 'warning':
      self.logger.warning(f"⚠️ {message}")
    else:
      self.logger.info(f"📍 {message}")

    if self.json_mode:
      self._emit_json('milestone', {
        'message': message,
        'status': status,
        **kwargs
      })

  def stats (self, data: Dict):
    """Log statistics with JSON event"""
    if self.json_mode:
      self._emit_json('stats', data)

  def _condense_definitions_in_prompt (self, prompt: str) -> str:
    """
    Replace verbose variable definitions with condensed summary

    This method looks for the variable definitions section in the prompt
    and replaces it with a condensed version showing just counts and tiers.
    The full definitions are still sent to the LLM - this only affects logging.

    Args:
        prompt: Full prompt with embedded definitions

    Returns:
        Prompt with condensed definitions section
    """
    import re

    # Pattern to match Stage 1 definitions section
    # Matches: ───── header ───── content ─────
    stage1_pattern = (
      r'(─{59,})\n'  # Opening separator (59+ dashes)
      r'📋 VARIABLE DEFINITIONS FOR ([A-Z_]+)\n'  # Header with doc type
      r'(─{59,})\n'  # Second separator
      r'(.*?)'  # All content (non-greedy) - this is the definitions
      r'(─{59,})'  # Closing separator
    )

    # Pattern to match Stage 2 definitions section
    # Matches: ═════ header ═════ content ═════
    stage2_pattern = (
      r'(═{59,})\n'  # Opening separator (59+ equal signs)
      r'📋 STAGE 2: ACTUARIAL VARIABLE DEFINITIONS.*?\n'  # Header
      r'(═{59,})\n'  # Second separator
      r'(.*?)'  # All content (non-greedy) - this is the definitions
      r'(═{59,})'  # Closing separator
    )

    # Try Stage 1 pattern first
    stage1_match = re.search(stage1_pattern, prompt, re.DOTALL)

    if stage1_match:
      doc_type = stage1_match.group(2)  # Extract document type
      full_definitions = stage1_match.group(4)  # Extract full definitions content

      # Count variables by looking for variable markers
      # Variables are typically marked with 📌 or as list items
      var_names = re.findall(r'  📌 (\w+)', full_definitions)
      if not var_names:  # Fallback: count any indented field names
        var_names = re.findall(r'^\s{2,}(\w+):', full_definitions, re.MULTILINE)

      total_vars = len(set(var_names))  # Use set to avoid duplicates

      # Count tier markers
      tier1_markers = len(re.findall(r'(🔴|TIER 1|CRITICAL)', full_definitions, re.IGNORECASE))
      tier2_markers = len(re.findall(r'(🟡|TIER 2|IMPORTANT)', full_definitions, re.IGNORECASE))
      tier3_markers = len(re.findall(r'(🟢|TIER 3|SUPPORTING)', full_definitions, re.IGNORECASE))

      # Estimate variables per tier (rough heuristic)
      if tier1_markers > 0:
        tier1_vars = total_vars // 3
        tier2_vars = total_vars // 3
        tier3_vars = total_vars - tier1_vars - tier2_vars
      else:
        tier1_vars = tier2_vars = tier3_vars = total_vars // 3

      # Build condensed replacement
      condensed = [
        "─" * 60,
        f"📋 VARIABLE DEFINITIONS FOR {doc_type} (condensed)",
        "─" * 60,
        "Definition Version: 1.0",
        ""
      ]

      if tier1_markers > 0:
        condensed.append(f"🔴 TIER 1 - CRITICAL VARIABLES: {tier1_vars} variables")
      if tier2_markers > 0:
        condensed.append(f"🟡 TIER 2 - IMPORTANT VARIABLES: {tier2_vars} variables")
      if tier3_markers > 0:
        condensed.append(f"🟢 TIER 3 - SUPPORTING VARIABLES: {tier3_vars} variables")

      condensed.extend([
        "",
        f"Total: {total_vars} variables defined",
        "[Full definitions sent to LLM - condensed here for readability]",
        "─" * 60
      ])

      # Replace the full definitions with condensed version
      return re.sub(stage1_pattern, '\n'.join(condensed), prompt, flags=re.DOTALL)

    # Try Stage 2 pattern
    stage2_match = re.search(stage2_pattern, prompt, re.DOTALL)

    if stage2_match:
      full_definitions = stage2_match.group(3)  # Extract full definitions content

      # Count variables
      var_names = re.findall(r'  📌 (\w+)', full_definitions)
      if not var_names:
        var_names = re.findall(r'^\s{2,}(\w+):', full_definitions, re.MULTILINE)

      total_vars = len(set(var_names))

      # Estimate tiers
      tier1_vars = total_vars // 3
      tier2_vars = total_vars // 3
      tier3_vars = total_vars - tier1_vars - tier2_vars

      # Build condensed replacement
      condensed = [
        "═" * 60,
        "📋 STAGE 2: ACTUARIAL VARIABLE DEFINITIONS (condensed)",
        "═" * 60,
        "",
        f"🔴 TIER 1 - CRITICAL: {tier1_vars} variables",
        f"🟡 TIER 2 - IMPORTANT: {tier2_vars} variables",
        f"🟢 TIER 3 - SUPPORTING: {tier3_vars} variables",
        "",
        f"Total: {total_vars} final actuarial variables",
        "[Full definitions sent to LLM - condensed here for readability]",
        "═" * 60
      ]

      # Replace the full definitions with condensed version
      return re.sub(stage2_pattern, '\n'.join(condensed), prompt, flags=re.DOTALL)

    # No definitions section found - return prompt as-is
    return prompt

  def debug_api_prompt (self, prompt: str, stage: str):
    """Show API prompt if debug enabled, with optional condensed definitions"""
    if not (self.show_api_prompts and self.logger.level == logging.DEBUG):
      return

    display_prompt = prompt

    # If show_variable_definitions is False, condense the definitions section
    if not self.show_variable_definitions:
      display_prompt = self._condense_definitions_in_prompt(prompt)

    # Apply max_prompt_chars truncation if set
    if self.max_prompt_chars > 0:
      display_prompt = self._truncate(display_prompt, self.max_prompt_chars)

    self.logger.debug(f"{'-' * 60}\nPROMPT for {stage}:\n\n{display_prompt}")

  def debug_api_response (self, response: str, stage: str):
    """Show API response if debug enabled"""
    if self.show_api_responses and self.logger.level == logging.DEBUG:
      truncated = self._truncate(response, self.max_response_chars)
      # self.logger.debug("")
      self.logger.debug(f"{'-' * 60}\nRESPONSE for {stage}:\n\n{truncated}")

  def debug_stage1 (self, message: str):
    """Stage 1 specific debug logging"""
    if self.show_stage1_details and self.logger.level == logging.DEBUG:
      self.logger.debug(f"[STAGE1] {message}")

  def debug_stage2 (self, message: str):
    """Stage 2 specific debug logging"""
    if self.show_stage2_details and self.logger.level == logging.DEBUG:
      self.logger.debug(f"[STAGE2] {message}")


class ClassTrackMetrics:
  """Comprehensive statistics and performance tracking"""

  def __init__ (self, logger: ClassLogger):
    self.logger = logger
    self.start_time = perf_counter()

    # Initialize statistics structure (matching Script 2)
    self.stats = {
      # File processing
      "files_processed": 0,
      "files_successful": 0,
      "files_failed": 0,
      "claims_processed": 0,

      # Stage processing
      "stage1_documents_processed": 0,
      "stage1_documents_successful": 0,
      "stage1_documents_failed": 0,
      "stage2_aggregations_processed": 0,
      "stage2_aggregations_successful": 0,
      "stage2_aggregations_failed": 0,

      # Cost tracking
      "total_cost": 0.0,
      "cost_by_stage": {
        "stage1": 0.0,
        "stage2": 0.0
      },
      "cost_by_document_type": {},

      # Token usage tracking
      "token_usage": {
        "total_input": 0,
        "total_output": 0,
        "total_usage": 0,
        "by_stage": {
          "stage1": {"input": 0, "output": 0, "total": 0},
          "stage2": {"input": 0, "output": 0, "total": 0}
        },
        "by_document_type": {}
      },

      # Processing times
      "processing_times": {},
      "stage_processing_times": {
        "stage1": [],
        "stage2": []
      },

      # Success rates
      "generation_success_rates": {
        "stage1": {},
        "stage2": {"successful": 0, "attempted": 0}
      },

      # Method tracking
      "method_usage": {
        "function_calling": {"success": 0, "total": 0, "cost": 0.0} #,
        # "text_fallback": {"success": 0, "total": 0, "cost": 0.0}
      }
    }

  def record_api_call (self, api_response: Dict, stage: str, document_type: str = None,
                       method: str = "function_calling", success: bool = True):
    """Record comprehensive API call metrics"""
    usage = api_response.get('usage', {})
    input_tokens = usage.get('prompt_tokens', 0)
    output_tokens = usage.get('completion_tokens', 0)
    cost = api_response.get('cost', 0.0)

    # Update token usage
    self.stats['token_usage']['total_input'] += input_tokens
    self.stats['token_usage']['total_output'] += output_tokens
    self.stats['token_usage']['total_usage'] += (input_tokens + output_tokens)

    # Update by stage - FIX: Ensure 'total' is calculated
    self.stats['token_usage']['by_stage'][stage]['input'] += input_tokens
    self.stats['token_usage']['by_stage'][stage]['output'] += output_tokens
    self.stats['token_usage']['by_stage'][stage]['total'] = (
      self.stats['token_usage']['by_stage'][stage]['input'] +
      self.stats['token_usage']['by_stage'][stage]['output']
    )
    # Update by document type if provided
    if document_type:
      if document_type not in self.stats['token_usage']['by_document_type']:
        self.stats['token_usage']['by_document_type'][document_type] = {
          "input": 0, "output": 0, "total": 0
        }
      self.stats['token_usage']['by_document_type'][document_type]['input'] += input_tokens
      self.stats['token_usage']['by_document_type'][document_type]['output'] += output_tokens
      # FIX: Calculate total
      self.stats['token_usage']['by_document_type'][document_type]['total'] = (
        self.stats['token_usage']['by_document_type'][document_type]['input'] +
        self.stats['token_usage']['by_document_type'][document_type]['output']
      )

    # Update cost tracking
    self.stats['total_cost'] += cost
    self.stats['cost_by_stage'][stage] += cost

    if document_type:
      if document_type not in self.stats['cost_by_document_type']:
        self.stats['cost_by_document_type'][document_type] = 0.0
      self.stats['cost_by_document_type'][document_type] += cost

    # Update method tracking
    self.stats['method_usage'][method]['total'] += 1
    self.stats['method_usage'][method]['cost'] += cost
    if success:
      self.stats['method_usage'][method]['success'] += 1

  def record_token_usage (self, usage: Dict, context: str, doc_type: str = None):
    """
    Record token usage with business context

    Args:
      usage: Token usage dict with prompt_tokens, completion_tokens, total_tokens
      context: Processing stage (e.g., "stage1", "stage2", "document_analysis")
      doc_type: Document type if applicable (e.g., "phone_transcript")
    """
    # Extract tokens
    input_tokens = usage.get('prompt_tokens', 0)
    output_tokens = usage.get('completion_tokens', 0)
    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)

    # Update global totals
    self.stats['token_usage']['total_input'] += input_tokens
    self.stats['token_usage']['total_output'] += output_tokens
    self.stats['token_usage']['total_usage'] += total_tokens

    # Track by stage
    if context in self.stats['token_usage']['by_stage']:
      self.stats['token_usage']['by_stage'][context]['input'] += input_tokens
      self.stats['token_usage']['by_stage'][context]['output'] += output_tokens
      self.stats['token_usage']['by_stage'][context]['total'] += total_tokens

    # Track by document type
    if doc_type:
      if doc_type not in self.stats['token_usage']['by_document_type']:
        self.stats['token_usage']['by_document_type'][doc_type] = {
          'input': 0, 'output': 0, 'total': 0
        }
      self.stats['token_usage']['by_document_type'][doc_type]['input'] += input_tokens
      self.stats['token_usage']['by_document_type'][doc_type]['output'] += output_tokens
      self.stats['token_usage']['by_document_type'][doc_type]['total'] += total_tokens

  def record_processing_time (self, stage: str, duration: float):
    """Record processing time for specific stage"""
    self.stats['stage_processing_times'][stage].append(duration)

  def record_stage1_success (self, document_type: str, success: bool):
    """Record Stage 1 document processing success"""
    if document_type not in self.stats['generation_success_rates']['stage1']:
      self.stats['generation_success_rates']['stage1'][document_type] = {
        "successful": 0, "attempted": 0
      }

    self.stats['generation_success_rates']['stage1'][document_type]['attempted'] += 1
    if success:
      self.stats['generation_success_rates']['stage1'][document_type]['successful'] += 1
      self.stats['stage1_documents_successful'] += 1
    else:
      self.stats['stage1_documents_failed'] += 1

  def record_stage2_success (self, success: bool):
    """Record Stage 2 aggregation success"""
    self.stats['generation_success_rates']['stage2']['attempted'] += 1
    if success:
      self.stats['generation_success_rates']['stage2']['successful'] += 1
      self.stats['stage2_aggregations_successful'] += 1
    else:
      self.stats['stage2_aggregations_failed'] += 1

  def get_processing_rate (self) -> float:
    """Get claims processed per minute"""
    elapsed = perf_counter() - self.start_time
    if elapsed > 0:
      return (self.stats['claims_processed'] / elapsed) * 60
    return 0.0

  def get_api_rate (self) -> float:
    """Get API calls per minute"""
    elapsed = perf_counter() - self.start_time
    total_calls = (self.stats['stage1_documents_processed'] +
                   self.stats['stage2_aggregations_processed'])
    if elapsed > 0:
      return (total_calls / elapsed) * 60
    return 0.0

  def get_token_efficiency (self) -> float:
    """Get tokens per dollar efficiency"""
    if self.stats['total_cost'] > 0:
      return self.stats['token_usage']['total_usage'] / self.stats['total_cost']
    return 0.0

  def get_success_rate (self, stage: str, doc_type: str = None) -> float:
    """Get success rate for specific stage/document type"""
    if stage == "stage1" and doc_type:
      rates = self.stats['generation_success_rates']['stage1'].get(doc_type, {})
      if rates.get('attempted', 0) > 0:
        return (rates['successful'] / rates['attempted']) * 100
    elif stage == "stage2":
      rates = self.stats['generation_success_rates']['stage2']
      if rates['attempted'] > 0:
        return (rates['successful'] / rates['attempted']) * 100
    return 0.0

  def print_comprehensive_summary (self):
    """Print detailed metrics summary with ALL breakdowns (matching Script 2)"""
    self.logger.info("\n" + "=" * 60)
    self.logger.info("📊 COMPREHENSIVE PROCESSING SUMMARY")

    # Files and claims summary
    total_files = self.stats['files_processed']
    success_files = self.stats['files_successful']
    if total_files > 0:
      success_rate = (success_files / total_files) * 100
      self.logger.info(f"📁 Files: {success_files}/{total_files} successful ({success_rate:.1f}%)")
    self.logger.info(f"📄 Claims analyzed: {self.stats['claims_processed']}")

    # Processing time and rates
    elapsed = perf_counter() - self.start_time
    self.logger.info(f"⏱️  Total processing time: {elapsed:.2f}s")

    actual_api_calls = 0

    if 'method_usage' in self.stats and self.stats['method_usage']:
      # Sum up all API calls across all methods (function_calling, text_fallback, etc.)
      for method, data in self.stats['method_usage'].items():
        actual_api_calls += data.get('total', 0)

      # Fallback: if method tracking somehow failed, use stage document counts
      # (this should rarely happen, but provides a safety net)
    if actual_api_calls == 0:
      actual_api_calls = (self.stats.get('stage1_documents_processed', 0) +
                          self.stats.get('stage2_aggregations_processed', 0))

    self.logger.info(f"📞 Total API calls: {actual_api_calls}")

    # Cost and tokens
    self.logger.info(f"💰 Total cost: ${self.stats['total_cost']:.4f}")
    total_tokens = self.stats['token_usage']['total_usage']
    input_tokens = self.stats['token_usage']['total_input']
    output_tokens = self.stats['token_usage']['total_output']
    self.logger.info(
      f"🎯 Total tokens: {total_tokens:,} ({input_tokens:,} input + {output_tokens:,} output)")

    # Stage breakdown
    self.logger.info("\n" + "=" * 60)
    self.logger.info("🔄 STAGE BREAKDOWN:")

    # Stage 1
    stage1_docs = self.stats['stage1_documents_processed']
    stage1_success = self.stats['stage1_documents_successful']
    stage1_failed = self.stats['stage1_documents_failed']
    if stage1_docs > 0:
      stage1_rate = (stage1_success / stage1_docs) * 100
      self.logger.info("Stage 1 (Feature Extraction):")
      self.logger.info(f"  📄 Documents processed: {stage1_docs}")
      self.logger.info(f"  ✅ Successful: {stage1_success} ({stage1_rate:.1f}%)")
      if stage1_failed > 0:
        self.logger.info(f"  ❌ Failed: {stage1_failed}")
      self.logger.info(f"  💰 Cost: ${self.stats['cost_by_stage']['stage1']:.4f}")

      stage1_times = self.stats['stage_processing_times']['stage1']
      if stage1_times:
        avg_time = sum(stage1_times) / len(stage1_times)
        self.logger.info(f"  ⏱️  Avg time: {avg_time:.1f}s/document")

    # Stage 2
    stage2_agg = self.stats['stage2_aggregations_processed']
    stage2_success = self.stats['stage2_aggregations_successful']
    if stage2_agg > 0:
      stage2_rate = (stage2_success / stage2_agg) * 100
      self.logger.info("\nStage 2 (Aggregation):")
      self.logger.info(f"  📄 Claims aggregated: {stage2_agg}")
      self.logger.info(f"  ✅ Successful: {stage2_success} ({stage2_rate:.1f}%)")
      self.logger.info(f"  💰 Cost: ${self.stats['cost_by_stage']['stage2']:.4f}")

      stage2_times = self.stats['stage_processing_times']['stage2']
      if stage2_times:
        avg_time = sum(stage2_times) / len(stage2_times)
        self.logger.info(f"  ⏱️  Avg time: {avg_time:.1f}s/claim")

    # Performance metrics
    self.logger.info("\n" + "=" * 60)
    self.logger.info("📈 PERFORMANCE METRICS:")
    claims_per_min = self.get_processing_rate()
    api_per_min = self.get_api_rate()
    tokens_per_dollar = self.get_token_efficiency()

    self.logger.info(f"⚡ Claims/minute: {claims_per_min:.1f}")
    if stage1_docs > 0 and elapsed > 0:
      docs_per_min = (stage1_docs / elapsed) * 60
      self.logger.info(f"📋 Documents/minute: {docs_per_min:.1f}")
    self.logger.info(f"📞 API calls/minute: {api_per_min:.1f}")
    if tokens_per_dollar > 0:
      self.logger.info(f"💎 Tokens/dollar: {tokens_per_dollar:,.0f} tokens/$")

    if self.stats['claims_processed'] > 0:
      avg_cost = self.stats['total_cost'] / self.stats['claims_processed']
      avg_time = elapsed / self.stats['claims_processed']
      self.logger.info(f"💵 Avg cost/claim: ${avg_cost:.4f}")
      self.logger.info(f"â° Avg time/claim: {avg_time:.1f}s")

    # Cost breakdown by document type
    if self.stats['cost_by_document_type']:
      self.logger.info("\n" + "=" * 60)
      self.logger.info("💰 COST BREAKDOWN BY DOCUMENT TYPE:")
      for doc_type, cost in sorted(self.stats['cost_by_document_type'].items(),
                                   key=lambda x: x[1], reverse=True):
        # Calculate calls for this doc type
        stage1_rates = self.stats['generation_success_rates']['stage1'].get(doc_type, {})
        calls = stage1_rates.get('attempted', 0)
        if calls > 0:
          avg_cost = cost / calls
          doc_name = doc_type.replace('_', ' ').title()
          self.logger.info(f"  {doc_name}: ${cost:.4f} ({calls} calls, ${avg_cost:.4f}/call)")

    # Token usage by document type
    if self.stats['token_usage']['by_document_type']:
      self.logger.info("\n" + "=" * 60)
      self.logger.info("🎯 TOKEN USAGE BY DOCUMENT TYPE:")
      for doc_type, tokens in sorted(self.stats['token_usage']['by_document_type'].items(),
                                     key=lambda x: x[1]['input'] + x[1]['output'],
                                     reverse=True):
        total = tokens['input'] + tokens['output']
        doc_name = doc_type.replace('_', ' ').title()
        self.logger.info(f"  {doc_name}: {total:,} ({tokens['input']:,} → {tokens['output']:,})")

    # Document type success rates
    if self.stats['generation_success_rates']['stage1']:
      self.logger.info("\n" + "=" * 60)
      self.logger.info("📊 DOCUMENT TYPE SUCCESS RATES:")
      for doc_type, rates in sorted(self.stats['generation_success_rates']['stage1'].items()):
        if rates['attempted'] > 0:
          success_rate = (rates['successful'] / rates['attempted']) * 100
          doc_name = doc_type.replace('_', ' ').title()
          self.logger.info(
            f"  {doc_name}: {rates['successful']}/{rates['attempted']} ({success_rate:.1f}%)")

    # Method success rates
    self.logger.info("\n" + "=" * 60)
    self.logger.info("🔧 METHOD SUCCESS RATES:")
    for method, stats in self.stats['method_usage'].items():
      if stats['total'] > 0:
        success_rate = (stats['success'] / stats['total']) * 100
        method_name = method.replace('_', ' ').title()
        self.logger.info(f"  {method_name}: {success_rate:.1f}% success "
                         f"({stats['success']}/{stats['total']}), "
                         f"{stats['total']} calls, ${stats['cost']:.4f}")


class ClassAPIClient:
  """Centralized OpenAI API client with retry logic and cost tracking"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger
    self.api_settings = config.get_api_settings()

    # Create provider using factory (OpenAI or Ollama)
    try:
      self.provider = ClassCreateLLM.create_provider(self.api_settings, logger)
      provider_name = self.api_settings.get('provider', 'openai')
    except Exception as e:
      self.logger.error(f"LLM Provider - {provider_name} - Failed to initialize - {e}")
      raise

    # Initialize tracking variables
    self.total_cost = 0.0
    self.total_calls = 0
    self.total_tokens = 0
    self.total_input_tokens = 0
    self.total_output_tokens = 0

    # Retry settings from config
    self.max_retries = self.api_settings.get('retry_count', 3)
    self.base_delay = self.api_settings.get('retry_delay_base', 2)

    # Pricing configuration
    provider_name = self.api_settings.get('provider', 'openai')
    provider_config = self.api_settings.get(provider_name, {})
    self.pricing = provider_config.get('pricing', {})

    self.logger.info(
      f"LLM Provider - {provider_name} - Initialized with {self.max_retries} max retries")

  def _calculate_cost (self, usage: Dict) -> float:
    """Calculate cost for API call"""
    input_tokens = usage.get('prompt_tokens', 0)
    output_tokens = usage.get('completion_tokens', 0)

    input_cost = (input_tokens / 1000) * self.input_cost_per_1k
    output_cost = (output_tokens / 1000) * self.output_cost_per_1k

    return input_cost + output_cost

  def call_llm_with_function (
    self,
    messages: List[Dict],
    function_schema: Dict,
    function_name: str,
    model: str = None,
    call_type: str = "function_call",
    max_tokens: int = None,
    temperature: float = None  # ✅ Changed from 0.7
  ) -> Dict:
    """
    Make function call with retry logic, cost tracking, and token tracking

    This is the main method used throughout Script 4 for structured LLM calls
    """
    # Determine which model to use based on call_type
    if model is None:
      provider_name = self.api_settings.get('provider', 'openai')
      provider_config = self.api_settings.get(provider_name, {})
      models = provider_config.get('models', {})
      if call_type == "Stage1" or call_type.startswith("Stage1_"):
        model = models.get('stage1')
      elif call_type == "Stage2" or call_type.startswith("aggregation_"):
        model = models.get('stage2')
      if not model:
        model = models.get('default', 'gpt-4o-mini-2024-07-18')

    if max_tokens is None or temperature is None:
      if call_type == "Stage1" or call_type.startswith("Stage1_"):
        stage_settings = self.config.get_stage1_settings()
        if max_tokens is None:
          max_tokens = stage_settings.get('max_tokens', 2000)
        if temperature is None:
          temperature = stage_settings.get('temperature', 0.7)

      elif call_type == "Stage2" or call_type.startswith("aggregation_"):
        stage_settings = self.config.get_stage2_settings()
        if max_tokens is None:
          max_tokens = stage_settings.get('max_tokens', 3000)
        if temperature is None:
          temperature = stage_settings.get('temperature', 0.7)
      else:
        if max_tokens is None:
          max_tokens = 2000
        if temperature is None:
          temperature = 0.7

    # Log the function call
    self.logger.debug(f"Function call: {function_name} ({call_type})")

    response = self.provider.call_llm_with_function(
      messages=messages,
      schema=function_schema,
      function_name=function_name,
      model=model,
      max_tokens=max_tokens,
      temperature=temperature,
      call_type=call_type
    )

    # Check if call was successful
    if not response.get('success', False):
      error_msg = response.get('error', 'Unknown error')
      self.logger.error(f"Function call failed: {error_msg}")
      return {
        'success': False,
        'error': error_msg,
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
        'cost': 0.0
      }

    # Extract results
    result = response['function_args']
    usage = response['usage']
    cost = response['cost']
    response_time = response['response_time']

    # Update APIClient tracking
    self.total_cost += cost
    self.total_calls += 1
    self.total_tokens += usage['total_tokens']
    self.total_input_tokens += usage['prompt_tokens']
    self.total_output_tokens += usage['completion_tokens']

    # Log stats
    self.logger.debug("-" * 60)
    self.logger.debug(f"Function call successful: {function_name}")
    self.logger.debug(f"  Model: {response['model']}")
    self.logger.debug(f"  Tokens: {usage['prompt_tokens']} → {usage['completion_tokens']}")
    self.logger.debug(f"  Cost: ${cost:.6f}")
    self.logger.debug(f"  Time: {response_time:.2f}s")

    return {
      'success': True,
      'result': result,
      'usage': usage,
      'cost': cost,
      'response_time': response_time,
      'model': response['model']
    }

  def get_stats_summary (self) -> Dict:
    """Get comprehensive statistics summary"""
    return {
      'total_cost': self.total_cost,
      'total_calls': self.total_calls,
      'total_tokens': self.total_tokens,
      'total_input_tokens': self.total_input_tokens,
      'total_output_tokens': self.total_output_tokens,
      'average_cost_per_call': self.total_cost / max(self.total_calls, 1),
      'average_tokens_per_call': self.total_tokens / max(self.total_calls, 1)
    }


class ClassCloudStorage:
  """Google Cloud Storage integration - match Scripts 1-3 pattern"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger
    self.cloud_settings = config.get_cloud_storage_settings()

    # Cloud metrics tracking
    self.cloud_metrics = {
      "uploads": 0,
      "downloads": 0,
      "total_bytes_uploaded": 0,
      "total_bytes_downloaded": 0,
      "total_gb_transferred": 0.0,
      "estimated_cost": 0.0,
      "operation_times": []
    }

    # Initialize client if enabled
    self.client = None
    self.bucket = None

    if self.cloud_settings.get('enabled', False):
      self._initialize_client()
    else:
      self.logger.info("☁️  Cloud storage disabled (set cloud_storage.enabled=true to enable)")

  def _initialize_client (self):
    """Initialize Google Cloud Storage client"""
    try:
      # Conditional import - only load google-cloud-storage if actually using it
      from google.cloud import storage

      project_id = self.cloud_settings.get('project_id')
      bucket_name = self.cloud_settings.get('bucket_name')
      credentials_path = self.cloud_settings.get('credentials_path')

      if not project_id or not bucket_name:
        self.logger.warning("Cloud storage enabled but project_id or bucket_name missing")
        return

      # Set credentials if provided
      if credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

      # Initialize client
      self.client = storage.Client(project=project_id)
      self.bucket = self.client.bucket(bucket_name)

      self.logger.success(f"Cloud storage initialized: {bucket_name}")

    except Exception as e:
      self.logger.error(f"Failed to initialize cloud storage: {e}")
      self.client = None
      self.bucket = None

  def upload_file (self, local_path: str, cloud_path: str) -> bool:
    """Upload file to cloud storage"""
    if not self.client or not self.bucket:
      return False

    try:
      start_time = perf_counter()

      # Get file size
      file_size = Path(local_path).stat().st_size

      # Upload
      blob = self.bucket.blob(cloud_path)
      blob.upload_from_filename(local_path)

      # Update metrics
      duration = perf_counter() - start_time
      self.cloud_metrics["uploads"] += 1
      self.cloud_metrics["total_bytes_uploaded"] += file_size
      self.cloud_metrics["operation_times"].append(duration)

      # Update cost estimate (rough: $0.020 per GB for standard storage)
      gb_uploaded = file_size / (1024 ** 3)
      self.cloud_metrics["total_gb_transferred"] += gb_uploaded
      self.cloud_metrics["estimated_cost"] += gb_uploaded * 0.020

      self.logger.debug(f"Uploaded to cloud: {cloud_path} ({file_size / 1024:.1f}KB)")
      return True

    except Exception as e:
      self.logger.error(f"Cloud upload failed: {e}")
      return False

  def download_file (self, cloud_path: str, local_path: str) -> bool:
    """Download file from cloud storage"""
    if not self.client or not self.bucket:
      return False

    try:
      start_time = perf_counter()

      # Download
      blob = self.bucket.blob(cloud_path)
      blob.download_to_filename(local_path)

      # Get file size
      file_size = Path(local_path).stat().st_size

      # Update metrics
      duration = perf_counter() - start_time
      self.cloud_metrics["downloads"] += 1
      self.cloud_metrics["total_bytes_downloaded"] += file_size
      self.cloud_metrics["operation_times"].append(duration)

      # Update cost estimate
      gb_downloaded = file_size / (1024 ** 3)
      self.cloud_metrics["total_gb_transferred"] += gb_downloaded
      self.cloud_metrics["estimated_cost"] += gb_downloaded * 0.001  # Data egress cost

      self.logger.debug(f"Downloaded from cloud: {cloud_path} ({file_size / 1024:.1f}KB)")
      return True

    except Exception as e:
      self.logger.error(f"Cloud download failed: {e}")
      return False

  def upload_json (self, data: Dict, cloud_path: str) -> bool:
    """Upload JSON data directly to cloud"""
    if not self.client or not self.bucket:
      return False

    try:
      start_time = perf_counter()

      # Convert to JSON string
      json_str = json.dumps(data, indent=2)
      json_bytes = json_str.encode('utf-8')
      file_size = len(json_bytes)

      # Upload
      blob = self.bucket.blob(cloud_path)
      blob.upload_from_string(json_str, content_type='application/json')

      # Update metrics
      duration = perf_counter() - start_time
      self.cloud_metrics["uploads"] += 1
      self.cloud_metrics["total_bytes_uploaded"] += file_size
      self.cloud_metrics["operation_times"].append(duration)

      gb_uploaded = file_size / (1024 ** 3)
      self.cloud_metrics["total_gb_transferred"] += gb_uploaded
      self.cloud_metrics["estimated_cost"] += gb_uploaded * 0.020

      self.logger.debug(f"Uploaded JSON to cloud: {cloud_path} ({file_size / 1024:.1f}KB)")
      return True

    except Exception as e:
      self.logger.error(f"Cloud JSON upload failed: {e}")
      return False

  def download_json (self, cloud_path: str) -> Optional[Dict]:
    """Download and parse JSON from cloud"""
    if not self.client or not self.bucket:
      return None

    try:
      start_time = perf_counter()

      # Download as string
      blob = self.bucket.blob(cloud_path)
      json_str = blob.download_as_text()

      # Parse JSON
      data = json.loads(json_str)

      # Update metrics
      duration = perf_counter() - start_time
      file_size = len(json_str.encode('utf-8'))
      self.cloud_metrics["downloads"] += 1
      self.cloud_metrics["total_bytes_downloaded"] += file_size
      self.cloud_metrics["operation_times"].append(duration)

      gb_downloaded = file_size / (1024 ** 3)
      self.cloud_metrics["total_gb_transferred"] += gb_downloaded
      self.cloud_metrics["estimated_cost"] += gb_downloaded * 0.001

      self.logger.debug(f"Downloaded JSON from cloud: {cloud_path} ({file_size / 1024:.1f}KB)")
      return data

    except Exception as e:
      self.logger.error(f"Cloud JSON download failed: {e}")
      return None

  def get_cloud_metrics (self) -> Dict:
    """Get cloud storage metrics"""
    return self.cloud_metrics.copy()

  def print_cloud_summary (self):
    """Print cloud storage metrics summary"""
    if not self.client:
      return

    metrics = self.cloud_metrics

    if metrics["uploads"] == 0 and metrics["downloads"] == 0:
      return

    self.logger.info("\n" + "=" * 60)
    self.logger.info("☁️  CLOUD STORAGE METRICS:")
    self.logger.info(f"📤 Uploads: {metrics['uploads']}")
    self.logger.info(f"📥 Downloads: {metrics['downloads']}")
    self.logger.info(f"💾 Data transferred: {metrics['total_gb_transferred']:.3f} GB")
    self.logger.info(f"💰 Estimated cloud cost: ${metrics['estimated_cost']:.4f}")

    if metrics["operation_times"]:
      avg_time = sum(metrics["operation_times"]) / len(metrics["operation_times"])
      total_time = sum(metrics["operation_times"])
      self.logger.info(f"⏱️  Total cloud operation time: {total_time:.2f}s")
      self.logger.info(f"⏱️  Avg operation time: {avg_time:.2f}s")


class ClassLoadSchemas:
  """Load and manage function calling schemas for hybrid API calls"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger

    # Get settings from the three tiers
    self.shared_settings = config.get_shared_settings()
    self.stage1_settings = config.get_stage1_settings()
    self.stage2_settings = config.get_stage2_settings()

    # Get templates directory
    templates_dir = self.shared_settings.get('templates_dir', 'templates')
    self.templates_path = Path(__file__).parent / templates_dir
    self.schemas_path = self.templates_path / 'function_schemas'

    # Cache for loaded schemas
    self.schema_cache = {}

    # self.logger.debug(f"Loader - Function Schema - Initialized: {self.schemas_path}")

  def load_stage1_schema (self, document_type: str) -> Optional[Dict]:
    """Load Stage 1 function schema for specific document type"""

    # Check cache first
    cache_key = f"stage1_{document_type}"
    if cache_key in self.schema_cache:
      return self.schema_cache[cache_key]

    # Get schema filename from config
    doc_types = self.config.get_document_types()
    if document_type not in doc_types:
      self.logger.warning(f"Unknown document type: {document_type}")
      return None

    doc_config = doc_types[document_type]
    schema_file = doc_config.get('function_schema_file')

    if not schema_file:
      self.logger.warning(f"No function schema configured for {document_type}")
      return None

    # Load schema file
    schema_path = self.schemas_path / schema_file

    try:
      with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

      # Inject rationale fields if enabled (uses shared rationale config)
      schema = self._inject_rationale_fields(schema, document_type)

      # Cache and return
      self.schema_cache[cache_key] = schema
      self.logger.debug(f"Loaded Stage 1 schema: {schema_file}")
      return schema

    except FileNotFoundError:
      self.logger.error(f"Schema file not found: {schema_path}")
      return None
    except json.JSONDecodeError as e:
      self.logger.error(f"Invalid JSON in schema {schema_file}: {e}")
      return None
    except Exception as e:
      self.logger.error(f"Error loading schema {schema_file}: {e}")
      return None

  def load_stage2_schema (self) -> Optional[Dict]:
    """Load Stage 2 aggregation function schema"""

    # Check cache
    cache_key = "stage2_aggregation"
    if cache_key in self.schema_cache:
      return self.schema_cache[cache_key]

    # Get schema filename from config
    schema_file = self.stage2_settings.get('function_schema_file', 'stage2_aggregation.json')
    schema_path = self.schemas_path / schema_file

    try:
      with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

      # Inject rationale fields for Stage 2 (uses shared rationale config)
      schema = self._inject_stage2_rationale_fields(schema)

      # Cache and return
      self.schema_cache[cache_key] = schema
      self.logger.debug(("-" * 60))
      self.logger.debug(f"Loaded Stage 2 schema: {schema_file}")
      return schema

    except FileNotFoundError:
      self.logger.error(f"Schema file not found: {schema_path}")
      return None
    except json.JSONDecodeError as e:
      self.logger.error(f"Invalid JSON in schema {schema_file}: {e}")
      return None
    except Exception as e:
      self.logger.error(f"Error loading schema {schema_file}: {e}")
      return None

  def _inject_rationale_fields (self, schema: Dict, document_type: str) -> Dict:
    """
    Inject rationale fields into Stage 1 function schema based on shared configuration

    Rationale system modes:
    - 'full': Add rationale to ALL fields
    - 'selective': Add rationale only to specified fields
    - 'disabled': No rationale fields added
    """
    # Get rationale config from shared settings
    rationale_config = self.config.get_rationale_settings()

    if not rationale_config.get('enabled', True):
      return schema

    mode = rationale_config.get('mode', 'selective')
    selective_fields = rationale_config.get('selective_fields', [])

    # Clone schema to avoid modifying cached version
    schema = json.loads(json.dumps(schema))

    # Navigate to structured_features in parameters
    try:
      params = schema['parameters']
      props = params['properties']

      if 'structured_features' in props:
        features = props['structured_features']['properties']

        # Process each field
        for field_name, field_def in features.items():
          should_add_rationale = False

          if mode == 'full':
            should_add_rationale = True
          elif mode == 'selective':
            should_add_rationale = field_name in selective_fields

          if should_add_rationale:
            # Convert simple field to rationale object
            if field_def.get('type') != 'object':
              original_def = field_def.copy()

              # Create rationale wrapper
              features[field_name] = {
                "type": "object",
                "properties": {
                  "value": original_def,
                  "rationale": {
                    "type": "string",
                    "description": f"Explain how this value was determined. If verbatim from document, provide exact excerpt with citation."
                  },
                  "rationale_type": {
                    "type": "string",
                    "enum": ["verbatim", "derived"],
                    "description": "Type of extraction: verbatim (exact quote) or derived (calculated/inferred)"
                  },
                  "source_document": {
                    "type": "string",
                    "description": f"Document type this value came from: {document_type}"
                  },
                  "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence score from 0.0 to 1.0"
                  }
                },
                "required": ["value", "rationale", "rationale_type", "source_document",
                             "confidence"]
              }

      return schema

    except KeyError as e:
      self.logger.warning(f"Could not inject rationale fields: missing key {e}")
      return schema

  def _inject_stage2_rationale_fields (self, schema: Dict) -> Dict:
    """
    Inject rationale fields into Stage 2 schema using shared configuration

    FIXED: Now properly handles nested structure of actuarial_variables
    """

    # Get rationale config from shared settings
    rationale_config = self.config.get_rationale_settings()

    if not rationale_config.get('enabled', True):
      self.logger.debug("Rationale system disabled, skipping Stage 2 injection")
      return schema

    # Clone schema to avoid modifying cached version
    schema = json.loads(json.dumps(schema))

    # Track by category for consolidated logging
    category_vars = {}

    try:
      params = schema['parameters']
      props = params['properties']

      # Process actuarial_variables
      if 'actuarial_variables' in props:
        actuarial_vars = props['actuarial_variables']

        # Check if actuarial_variables has nested properties (categories)
        if 'properties' in actuarial_vars:
          categories = actuarial_vars['properties']

          self.logger.debug(f"Found {len(categories)} actuarial variable categories")

          # Process each category (reserving_variables, ratemaking_variables, etc.)
          for category_name, category_def in categories.items():
            if isinstance(category_def, dict) and 'properties' in category_def:

              self.logger.debug(f"Processing category: {category_name}")

              # Track variable names for this category
              var_names = []

              # NOW inject rationale into actual variables within each category
              variables = category_def['properties']

              for var_name, var_def in variables.items():
                # Only inject if not already an object with rationale
                if var_def.get('type') != 'object' or 'rationale' not in var_def.get('properties',
                                                                                     {}):
                  original_def = var_def.copy()

                  # Create rationale wrapper
                  variables[var_name] = {
                    "type": "object",
                    "properties": {
                      "value": original_def,
                      "rationale": {
                        "type": "string",
                        "description": "Explain aggregation logic across Stage 1 features. If conflicts exist, list all conflicting values and explain resolution."
                      },
                      "rationale_type": {
                        "type": "string",
                        "enum": ["aggregated", "conflict_resolved"],
                        "description": "Type: 'aggregated' (normal) or 'conflict_resolved' (conflicts found)"
                      },
                      "stage1_sources": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "document_type": {"type": "string"},
                            "stage1_feature": {"type": "string"},
                            "value": {"type": "string"},
                            "confidence": {"type": "number"}
                          }
                        },
                        "description": "List all Stage 1 features that informed this decision"
                      },
                      "conflicting_sources": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "source": {"type": "string"},
                            "value": {"type": "string"},
                            "stage1_doc_id": {"type": "string"}
                          }
                        },
                        "description": "If conflicts exist, list all conflicting values with sources"
                      },
                      "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Overall confidence in this aggregated value"
                      }
                    },
                    "required": ["value", "rationale", "rationale_type", "stage1_sources",
                                 "confidence"]
                  }

                  # Track variable name
                  var_names.append(var_name)

                  # Only log individual variables at DEBUG level
                  # self.logger.debug(f"  ✅ Injected rationale for {category_name}.{var_name}")

              # Store for summary
              category_vars[category_name] = var_names

      # Consolidated INFO logging - one line per category
      self.logger.info('-' * 60)
      self.logger.info("📝 Stage 2 rationale injection complete:")
      for category_name, var_names in category_vars.items():
        var_list = ", ".join(var_names)
        self.logger.info(f"  • {category_name}: ({len(var_names)} variables)")
        self.logger.info(f"    {var_list}")

      return schema


    except KeyError as e:
      self.logger.warning(f"Could not inject Stage 2 rationale fields: missing key {e}")
      import traceback
      self.logger.warning(traceback.format_exc())
      return schema
    except Exception as e:
      self.logger.error(f"Error during Stage 2 rationale injection: {e}")
      import traceback
      self.logger.error(traceback.format_exc())
      return schema


class ClassLoadTemplates:
  """Load template files for prompt building"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger

    # Get settings
    self.shared_settings = config.get_shared_settings()
    self.stage1_settings = config.get_stage1_settings()
    self.stage2_settings = config.get_stage2_settings()

    # Get templates directory from shared settings
    templates_dir = self.shared_settings.get('templates_dir', 'templates')
    self.templates_path = Path(__file__).parent / templates_dir

    self.category_dir = self.templates_path / 'category'
    self.specialized_dir = self.templates_path / 'specialized'

    self.logger.debug(f"Loader - Template - Initialized: {self.templates_path}")

  def load_category_template (self, category_name: str) -> Optional[str]:
    """Load category template"""
    template_file = self.category_dir / category_name

    if not template_file.exists():
      self.logger.warning(f"Category template not found: {template_file}")
      return None

    try:
      with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
      return content

    except Exception as e:
      self.logger.error(f"Error loading category template {category_name}: {e}")
      return None

  def load_specialized_template (self, document_type: str) -> Optional[str]:
    """Load specialized template for document type"""
    doc_types = self.config.get_document_types()

    if document_type not in doc_types:
      return None

    doc_config = doc_types[document_type]
    template_file_name = doc_config.get('specialized_template')

    if not template_file_name:
      return None

    template_file = self.specialized_dir / template_file_name

    if not template_file.exists():
      self.logger.warning(f"Specialized template not found: {template_file}")
      return None

    try:
      with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
      return content

    except Exception as e:
      self.logger.error(f"Error loading specialized template {document_type}: {e}")
      return None

  def load_orchestrator_template (self) -> Optional[str]:
    """Load universal orchestrator template (Stage 2)"""

    orchestrator_file = self.stage2_settings.get('orchestrator_file', 'universal/orchestrator.py')
    template_file = self.templates_path / orchestrator_file

    if not template_file.exists():
      self.logger.warning(f"Orchestrator template not found: {template_file}")
      return None

    try:
      with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()
      return content

    except Exception as e:
      self.logger.error(f"Error loading orchestrator template: {e}")
      return None


class ClassBuildPrompt:
  """Build prompts for Stage 1 and Stage 2 processing"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger
    self.rationale_config = config.get_rationale_settings()

    # Initialize definition loader
    self.definition_loader = ClassVariableDefinitions()
    # self.logger.info(f"✅ PromptBuilder initialized with definitions v{self.definition_loader.get_definition_version()}")

  def build_stage1_prompt (self, document_text: str, document_type: str,
                           category_template: Optional[str] = None,
                           specialized_template: Optional[str] = None) -> str:
    """
    Build Stage 1 extraction prompt

    Injects relevant variable definitions for this document type
    Combines category and specialized templates with document text
    Adds rationale instructions if enabled
    """

    # Base prompt
    prompt_parts = []

    # Add system context
    prompt_parts.append(
      f"You are an expert actuarial analyst specializing in workers' compensation claims analysis.\n"
      f"Extract specific features from this {document_type} for actuarial modeling and reserving.\n\n"
    )

    # Inject variable definitions for this document type
    definitions_section = self.definition_loader.build_stage1_definitions_section(
      document_type=document_type,
      mode="tiered"  # Comprehensive for Tier 1, Standard for Tier 2, Minimal for Tier 3
      # mode = "relevant"  # Only inject relevant variables
    )

    prompt_parts.append(definitions_section)
    prompt_parts.append("\n")

    # Add rationale instructions if enabled
    if self.rationale_config.get('enabled', True):
      mode = self.rationale_config.get('mode', 'selective')

      if mode == 'full':
        prompt_parts.append(
          "CRITICAL RATIONALE REQUIREMENT:\n"
          "For EVERY extracted field, you must provide:\n"
          "1. value: The extracted/derived value\n"
          "2. rationale: Detailed explanation of how the value was determined\n"
          "3. rationale_type: 'verbatim' (exact quote), 'derived' (calculated/inferred), "
          "4. source_document: Document type where value was found\n"
          "5. confidence: Score from 0.0 to 1.0 indicating certainty\n\n"
          "For verbatim extractions, provide the exact document excerpt with citation.\n"
          "For derived values, explain your calculation or inference methodology.\n\n"
          "Follow the extraction rules specified in the variable definitions above.\n\n"
        )
      elif mode == 'selective':
        selective_fields = self.rationale_config.get('selective_fields', [])
        if selective_fields:
          # Filter to only those relevant to this document
          relevant_vars = self.definition_loader.get_stage1_variables_for_document(document_type)
          doc_selective_fields = [f for f in selective_fields if f in relevant_vars]

          if doc_selective_fields:
            fields_str = ', '.join(doc_selective_fields)
            prompt_parts.append(
              f"RATIONALE REQUIREMENT FOR KEY FIELDS:\n"
              f"For these critical fields: {fields_str}\n"
              f"Provide detailed rationale explaining how each value was determined.\n"
              f"Include rationale_type, source_document, and confidence score.\n"
              f"Follow the extraction rules and examples in the definitions above.\n\n"
            )

    # Add category context if available
    if category_template:
      prompt_parts.append("CATEGORY CONTEXT:\n")
      prompt_parts.append(f"{category_template}\n\n")

    # Add specialized instructions if available
    if specialized_template:
      prompt_parts.append("SPECIALIZED EXTRACTION INSTRUCTIONS:\n")
      template_lines = specialized_template.split('\n')
      cleaned_template = '\n'.join(template_lines[2:])
      prompt_parts.append(f"{cleaned_template}\n\n")
      # prompt_parts.append(f"{specialized_template}\n\n")

    # Add document text
    prompt_parts.append(f"DOCUMENT TYPE: {document_type}\n\n")
    prompt_parts.append(f"DOCUMENT TEXT:\n{document_text}\n\n")

    # Output format instruction
    prompt_parts.append(
      "Return structured data using the function calling schema provided.\n"
      "Ensure all required fields are populated with accurate information.\n"
      "Follow the variable definitions and extraction rules specified above.\n"
    )

    return ''.join(prompt_parts)

  def build_stage2_prompt (self, stage1_features: List[Dict], claim_id: str) -> str:
    """
    Build Stage 2 aggregation prompt

    Combines all Stage 1 features and instructs LLM to aggregate into final variables
    Includes complete variable definitions with examples
    Includes conflict detection instructions
    """

    prompt_parts = []

    # System context
    prompt_parts.append(
      "You are an expert actuarial analyst performing final claim analysis.\n"
      "Aggregate Stage 1 features from multiple documents into final actuarial variables.\n\n"
    )

    # Inject Stage 2 variable definitions (tiered approach)

    definitions_section = self.definition_loader.build_stage2_definitions_section(
      mode="tiered"  # Comprehensive for Tier 1, Standard for Tier 2, Minimal for Tier 3
    )
    prompt_parts.append(definitions_section)
    prompt_parts.append("\n")

    # Conflict detection with strict enforcement

    prompt_parts.append(
      "CONFLICT DETECTION AND RESOLUTION:\n"
      "When you encounter different values for the same variable across documents:\n"
      "1. Identify the conflict explicitly in your rationale\n"
      "2. List ALL conflicting values with their source documents\n"
      "3. Explain your resolution logic (which value you chose and why)\n"
      "4. Set rationale_type to 'conflict_resolved'\n"
      "5. Include all conflicting sources in the conflicting_sources array\n\n"

      "Resolution priorities (STRICTLY ENFORCE):\n"
      "1. Actual costs > Projected/estimated costs\n"
      "2. Settlement/final documents > Initial assessments\n"
      "3. Most recent information > Older information\n"
      "4. Objective measurements > Subjective assessments\n"
      "5. Higher confidence sources > Lower confidence sources\n\n"
      "6. Follow source_priority specified in each variable's definition\n\n"
    )

    # ========== CRITICAL RULE ==========
    prompt_parts.append(
      "🚨 CRITICAL FOR SETTLING CLAIMS:\n"
      "   When claim_closure_status is 'closed_settled' or 'pending_settlement':\n"
      "   - ultimate_cost_prediction MUST EQUAL settlement_amount\n"
      "   - Do NOT add speculative future costs\n"
      "   - Settlement amount IS the ultimate cost\n\n"
    )

    # Add rationale instructions
    if self.rationale_config.get('enabled', True):
      prompt_parts.append(
        "RATIONALE REQUIREMENTS:\n"
        "For each final actuarial variable:\n"
        "1. value: The final aggregated value\n"
        "2. rationale: Explain how you synthesized Stage 1 features into this value\n"
        "   - Reference the aggregation_rules from the variable definition\n"
        "   - For cost variables: State exact dollar amounts and show category alignment\n"
        "   - For conflicts: List all conflicting values and explain resolution per priority rules\n"
        "3. rationale_type: 'aggregated' or 'conflict_resolved'\n"
        "4. stage1_sources: List all Stage 1 features that informed this decision\n"
        "5. conflicting_sources: If conflicts exist, list all conflicting values\n"
        "6. confidence: Overall confidence in this aggregated value\n\n"

        "CRITICAL: Follow the aggregation rules and examples in each variable's definition above.\n"
        "Pay special attention to the comprehensive examples for Tier 1 variables.\n\n"
      )

    # Add Stage 1 features
    prompt_parts.append(f"CLAIM ID: {claim_id}\n\n")
    prompt_parts.append("STAGE 1 FEATURES FROM ALL DOCUMENTS:\n\n")

    for i, features in enumerate(stage1_features, 1):
      doc_type = features.get('document_type', 'unknown')
      prompt_parts.append(f"Document {i} ({doc_type}):\n")
      prompt_parts.append(json.dumps(features, indent=2))
      prompt_parts.append("\n\n")

    # VALIDATION CHECKLIST
    prompt_parts.append(
      "VALIDATION CHECKLIST (verify before returning):\n"
      "□ Does ultimate_cost_prediction fall within ultimate_cost_category range?\n"
      "□ Is ultimate_cost_prediction >= total_incurred_cost?\n"
      "□ For settling claims: does ultimate_cost_prediction == settlement_amount?\n"
      "□ Does injury_severity_category align with ultimate_cost_category?\n\n"
    )

    # Output instructions
    prompt_parts.append(
      "Aggregate these Stage 1 features into final actuarial variables.\n"
      "Use the function calling schema to return structured output.\n"
      "Include comprehensive aggregated_narrative summarizing the claim.\n"
      "\n"
      "🔍 PRE-SUBMISSION VALIDATION CHECKLIST:\n"
      "Before returning your response, verify against the variable definitions:\n"
      "\n"
      "✓ Cost Variables:\n"
      "  - ultimate_cost_prediction matches ultimate_cost_category range?\n"
      "  - For settling claims: Did I use settlement_amount (not speculation)?\n"
      "  - Cost category mathematically correct? (e.g., $65K → 50K-100K)\n"
      "\n"
      "✓ Aggregation Rules:\n"
      "  - Followed source_priority for each variable?\n"
      "  - Applied resolution priorities for conflicts?\n"
      "  - Used correct aggregation_rules from definitions?\n"
      "\n"
      "✓ Rationales:\n"
      "  - All Tier 1 variables have comprehensive rationales?\n"
      "  - Rationales reference actual values from Stage 1?\n"
      "  - Conflicts properly documented with all sources?\n"
      "\n"
      "✓ Consistency:\n"
      "  - No contradictions between related variables?\n"
      "  - Severity/risk levels align across categories?\n"
      "  - Ultimate cost >= incurred cost?\n"
    )

    return ''.join(prompt_parts)

  def build_stage2_prompt_with_scores (self, stage1_features: List[Dict], claim_id: str) -> str:
    """
    Build Stage 2 aggregation prompt WITH compound score guidance.

    Shows LLM:
    - Ranked sources by compound score
    - Score breakdown for each source
    - Clear guidance to prefer higher scores (but allow overrides)

    Args:
        stage1_features: List of Stage1DocumentFeatures dicts (with compound_scores)
        claim_id: Claim identifier

    Returns:
        Complete Stage 2 prompt string with score guidance
    """

    # If compound scoring disabled, use regular prompt
    if not self.config.config.get('compound_scoring', {}).get('enabled', True):
      return self.build_stage2_prompt(stage1_features, claim_id)

    prompt_parts = []

    # System context
    prompt_parts.append(
      "You are an expert actuarial analyst performing final claim analysis.\n"
      "Aggregate Stage 1 features from multiple documents into final actuarial variables.\n\n"
    )

    # Add compound scoring explanation
    prompt_parts.append(
      "═══════════════════════════════════════════════════════════════\n"
      "COMPOUND PRIORITY SCORES - SOURCE RANKING SYSTEM\n"
      "═══════════════════════════════════════════════════════════════\n\n"
      "Each extracted feature has a COMPOUND PRIORITY SCORE calculated as:\n\n"
      "  compound_score = document_weight × confidence × recency × feature_importance\n\n"
      "WHERE:\n"
      "  • document_weight: Authority of document type (0.6-1.0)\n"
      "      - Settlement docs: 1.0 (highest authority)\n"
      "      - Medical provider: 0.95-1.0 (professional clinical)\n"
      "      - Adjuster notes: 0.85-0.9 (professional assessment)\n"
      "      - Phone transcripts: 0.6-0.7 (initial report)\n\n"
      "  • confidence: LLM extraction confidence (0.0-1.0)\n"
      "      - How confident Stage 1 was in extracting this value\n\n"
      "  • recency: Age-based temporal decay (0.6-1.0)\n"
      "      - Recent (<30d): 1.0\n"
      "      - Medium (<90d): 0.9\n"
      "      - Aging (<180d): 0.8\n"
      "      - Old (<365d): 0.7\n"
      "      - Very old (>365d): 0.6\n\n"
      "  • feature_importance: Variable-specific source preference (0.0-1.0)\n"
      "      - Which document types are best for THIS specific variable\n"
      "      - Actual values: 0.95-1.0\n"
      "      - Professional estimates: 0.85-0.95\n"
      "      - Preliminary values: 0.5-0.7\n"
      "      - Initial reports: 0.3-0.5\n\n"
      "GUIDANCE FOR YOU:\n"
      "  ✓ PREFER higher-scored sources when aggregating\n"
      "  ✓ Sources are ranked by score (RANK 1 = highest score)\n"
      "  ✓ YOU MAY OVERRIDE if you have good reason:\n"
      "      - Business logic requires it (actual > estimate)\n"
      "      - You detect clear error or inconsistency\n"
      "      - Multiple lower-scored sources agree against highest\n"
      "      - Domain knowledge suggests otherwise\n"
      "  ✓ If you override, EXPLAIN WHY in your rationale\n\n"
      "═══════════════════════════════════════════════════════════════\n\n"
    )

    # Add variable definitions
    definitions_section = self.definition_loader.build_stage2_definitions_section(mode="tiered")
    prompt_parts.append(definitions_section)
    prompt_parts.append("\n")

    # Group features by variable for scoring display
    features_by_variable = {}
    for doc in stage1_features:
      doc_type = doc['document_type']
      doc_id = doc['document_id']

      for var_name, var_data in doc.get('extracted_features', {}).items():
        if var_name not in features_by_variable:
          features_by_variable[var_name] = []

        features_by_variable[var_name].append({
          'document_type': doc_type,
          'document_id': doc_id,
          'value': var_data.get('value'),
          'confidence': var_data.get('confidence', 0.5),
          'rationale': var_data.get('rationale', ''),
          'document_date': doc.get('document_date'),
          'document_age_days': doc.get('document_age_days'),
          'compound_scores': var_data.get('compound_scores', {})
        })

    # Format each variable with scored sources
    prompt_parts.append(f"CLAIM ID: {claim_id}\n\n")
    prompt_parts.append("═══════════════════════════════════════════════════════════════\n")
    prompt_parts.append("STAGE 1 FEATURES - RANKED BY COMPOUND SCORE\n")
    prompt_parts.append("═══════════════════════════════════════════════════════════════\n\n")

    for var_name in sorted(features_by_variable.keys()):
      sources = features_by_variable[var_name]

      # Filter only sources with compound scores
      sources_with_scores = [s for s in sources if s.get('compound_scores')]

      if not sources_with_scores:
        continue

      # Already sorted by rank in CompoundScorer
      sources_with_scores.sort(
        key=lambda x: x['compound_scores'].get('rank_among_sources', 999)
      )

      prompt_parts.append(f"{'─' * 63}\n")
      prompt_parts.append(f"VARIABLE: {var_name}\n")
      prompt_parts.append(f"{'─' * 63}\n\n")

      for source in sources_with_scores:
        scores = source['compound_scores']
        rank = scores.get('rank_among_sources', '?')

        prompt_parts.append(f"[RANK {rank}] {source['document_type']}\n")
        prompt_parts.append(f"  └─ Compound Score: {scores['compound_score']:.4f}\n")
        prompt_parts.append(f"     • Value: {source['value']}\n")
        prompt_parts.append(f"     • Score Breakdown:\n")
        prompt_parts.append(f"        - document_weight:    {scores['document_weight']:.3f}\n")
        prompt_parts.append(f"        - confidence_score:   {scores['confidence_score']:.3f}\n")
        prompt_parts.append(f"        - recency_factor:     {scores['recency_factor']:.3f}\n")
        prompt_parts.append(f"        - feature_importance: {scores['feature_importance']:.3f}\n")

        if source.get('document_date'):
          prompt_parts.append(f"     • Document Date: {source['document_date']}")
          if source.get('document_age_days') is not None:
            prompt_parts.append(f" ({source['document_age_days']} days old)")
          prompt_parts.append("\n")

        if source.get('rationale'):
          prompt_parts.append(f"     • Stage 1 Rationale: {source['rationale'][:150]}...\n")

        prompt_parts.append("\n")

      prompt_parts.append("\n")

    prompt_parts.append("═══════════════════════════════════════════════════════════════\n\n")

    # Add standard Stage 2 instructions
    prompt_parts.append(
      "YOUR TASK:\n"
      "1. Review all ranked sources for each variable\n"
      "2. PREFER highest-scored sources (RANK 1) when aggregating\n"
      "3. Apply aggregation rules from variable definitions\n"
      "4. If you override highest score, EXPLAIN in rationale\n"
      "5. Ensure logical consistency across related variables\n"
      "6. Provide confidence scores and comprehensive rationales\n\n"
    )

    # Add validation checklist
    prompt_parts.append(
      "VALIDATION CHECKLIST:\n"
      "  ✓ Values: Reasonable and within expected ranges?\n"
      "  ✓ Aggregation: Followed source ranking guidance?\n"
      "  ✓ Rationales: Explained score overrides if any?\n"
      "  ✓ Consistency: No contradictions between variables?\n"
      "  ✓ Confidence: Scores reflect data quality and agreement?\n\n"
    )

    prompt_parts.append(
      "\n⚠️ CRITICAL COST VALIDATION:\n"
      "  • If ultimate_cost_prediction = $118,000:\n"
      "     → ultimate_cost_category MUST be '100K-150K' (the $118K falls in $100K-$150K range)\n"
      "  • Always verify cost falls within category range\n"
      "  • Category boundaries (FROM YOUR SCHEMA):\n"
      "     - <25K: $0 to $24,999\n"
      "     - 25K-50K: $25,000 to $49,999\n"
      "     - 50K-100K: $50,000 to $99,999\n"
      "     - 100K-150K: $100,000 to $149,999\n"
      "     - >150K: $150,000+\n\n"
    )

    return ''.join(prompt_parts)


class ClassExtractDate:
  """
  Extracts dates from document text with multiple format support.
  Returns the LATEST date found (preference for most recent).
  """

  def __init__ (self, logger):
    self.logger = logger

    # Date patterns (ordered by specificity)
    self.patterns = [
      # ISO format: 2024-10-15
      (r'\b(\d{4})-(\d{2})-(\d{2})\b', '%Y-%m-%d'),
      # US format: 10/15/2024, 10-15-2024
      (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', '%m/%d/%Y'),
      # Written: October 15, 2024
      (
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b',
        '%B %d %Y'),
      # Short month: Oct 15, 2024
      (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b',
       '%b %d %Y'),
      # Date: label patterns
      (r'(?:Date|Dated|As of|Created|Document Date):\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
       '%B %d %Y'),
      (
        r'(?:Date|Dated|As of|Created|Document Date):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})', '%m/%d/%Y'),
    ]

  def extract_date (self, document_text: str, document_type: str) -> Optional[str]:
    """
    Extract document date from text. Returns latest date found.

    Args:
        document_text: Full document text
        document_type: Type of document (for logging)

    Returns:
        ISO format date string (YYYY-MM-DD) or None
    """
    if not document_text:
      self.logger.warning(f"Empty document text for {document_type}")
      return None

    found_dates = []

    # Try each pattern
    for pattern, date_format in self.patterns:
      matches = re.finditer(pattern, document_text, re.IGNORECASE)

      for match in matches:
        try:
          # Extract matched text
          date_str = match.group(0)

          # Clean up the matched string
          # Remove labels like "Date:", "As of:", etc.
          date_str = re.sub(r'^(?:Date|Dated|As of|Created|Document Date):\s*', '', date_str,
                            flags=re.IGNORECASE)

          # Parse date
          parsed_date = datetime.strptime(date_str.strip(), date_format)
          found_dates.append(parsed_date)

        except ValueError:
          continue

    if found_dates:
      # Return LATEST date (most recent)
      latest_date = max(found_dates)
      iso_date = latest_date.strftime('%Y-%m-%d')

      self.logger.debug(
        f"Extracted date for {document_type}: {iso_date} (from {len(found_dates)} candidates)")
      return iso_date

    self.logger.warning(f"No date found in {document_type}, will use fallback")
    return None

  def calculate_age_days (self, document_date: Optional[str]) -> Optional[int]:
    """Calculate document age in days from today"""
    if not document_date:
      return None

    try:
      doc_date = datetime.fromisoformat(document_date)
      age_days = (datetime.now() - doc_date).days
      return max(0, age_days)  # No negative ages
    except:
      return None

  def _parse_date_string (self, date_str: str) -> Optional[datetime]:
    """Parse various date formats"""
    formats = [
      '%Y-%m-%d',
      '%m/%d/%Y',
      '%m-%d-%Y',
      '%d/%m/%Y',
      '%B %d, %Y',
      '%b %d, %Y',
      '%m/%d/%y',
    ]

    for fmt in formats:
      try:
        return datetime.strptime(date_str, fmt)
      except ValueError:
        continue

    return None


@dataclass
class ClassOutputStage1:
  """
  Stage 1 output dataclass - with rationale support
  PRESERVES all original fields for compatibility
  """

  document_id: str
  document_type: str
  extracted_features: Dict[str, Any]
  narrative_analysis: str
  confidence_score: float
  processing_metadata: Dict[str, Any]

  # Original preserved fields
  extraction_confidence: float = 0.0
  processing_notes: str = ""
  stage1_method: str = "function_calling"
  input_source: str = "unknown"

  document_date: Optional[str] = None
  document_age_days: Optional[int] = None
  document_weight: float = 0.8
  recency_factor: float = 1.0

  def to_dict (self) -> Dict:
    """Convert to dictionary for JSON serialization"""
    return asdict(self)


@dataclass
class ClassOutputStage2:
  """
  Stage 2 output dataclass - with rationale support
  PRESERVES all original fields for compatibility
  """
  claim_id: str
  processing_timestamp: str
  actuarial_variables: Dict[str, Any]
  aggregated_narrative: str
  confidence_scores: Dict[str, float]
  cost_predictions: Dict[str, Any]
  risk_assessment: Dict[str, Any]

  # Metadata
  encounters_processed: int
  stage2_method: str = "function_calling_aggregation"
  input_source: str = "stage1_features"
  quality_flags: List[str] = field(default_factory=list)

  def to_dict (self) -> Dict:
    """Convert to dictionary for JSON serialization"""
    return asdict(self)


# class DocumentDateExtractor:
#   """Extract dates from document text"""
#
#   def __init__ (self, logger: SimpleLogger):
#     self.logger = logger
#
#   def extract_date (self, document_text: str, document_type: str) -> Optional[str]:
#     """
#     Extract date from document text
#     Returns ISO date string (YYYY-MM-DD) or None
#     """
#     patterns = [
#       r'Date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
#       r'(\d{4}-\d{2}-\d{2})',
#       r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
#       r'(\w+\s+\d{1,2},?\s*\d{4})',
#     ]
#
#     for pattern in patterns:
#       match = re.search(pattern, document_text, re.IGNORECASE)
#       if match:
#         date_str = match.group(1)
#         parsed_date = self._parse_date_string(date_str)
#         if parsed_date:
#           return parsed_date.isoformat().split('T')[0]
#
#     return None
#
#   def _parse_date_string (self, date_str: str) -> Optional[datetime]:
#     """Parse various date formats"""
#     formats = [
#       '%Y-%m-%d',
#       '%m/%d/%Y',
#       '%m-%d-%Y',
#       '%d/%m/%Y',
#       '%B %d, %Y',
#       '%b %d, %Y',
#       '%m/%d/%y',
#     ]
#
#     for fmt in formats:
#       try:
#         return datetime.strptime(date_str, fmt)
#       except ValueError:
#         continue
#
#     return None
#
#   def calculate_age_days (self, document_date: str) -> int:
#     """Calculate age in days from ISO date string"""
#     doc_date = datetime.fromisoformat(document_date)
#     return (datetime.now() - doc_date).days


class ClassCalculateScore:
  """
  Calculates compound priority scores for Stage 1 features.

  Formula: compound_score = doc_weight × confidence × recency × importance

  Handles:
  - Recency factor calculation (stepped decay)
  - Document-specific overrides
  - Missing value defaults (granular: feature > document > program)
  - Score logging and breakdown
  """

  def __init__ (self, config, definition_loader, logger):
    self.config = config
    self.definition_loader = definition_loader
    self.logger = logger

    # Load configurations
    self.temporal_config = config.get_temporal_weighting()
    self.scoring_config = config.get_compound_scoring()
    self.document_types = config.get_document_types()

    # self.logger.info("✅ CompoundScorer initialized")

  def calculate_recency_factor (self, document_date: Optional[str], document_type: str) -> float:
    """
    Calculate recency factor based on document age.

    Args:
        document_date: ISO format date string
        document_type: Document type (for overrides)

    Returns:
        Recency factor (0.6 - 1.0)
    """
    if not self.temporal_config.get('enabled', True):
      return 1.0

    # Check for document-specific override
    overrides = self.temporal_config.get('document_overrides', {})
    if document_type in overrides:
      override = overrides[document_type]
      if override.get('decay_function') == 'none':
        factor = override.get('fixed_factor', 1.0)
        self.logger.debug(f"Using override recency for {document_type}: {factor}")
        return factor

    # Handle missing date
    if not document_date:
      factor = self.temporal_config.get('missing_date_factor', 0.7)
      self.logger.debug(f"Missing date for {document_type}, using default: {factor}")
      return factor

    # Calculate age and apply decay
    try:
      doc_date = datetime.fromisoformat(document_date)
      age_days = (datetime.now() - doc_date).days
      factor = self._stepped_decay(age_days)
      self.logger.debug(f"Recency for {document_type} ({age_days} days old): {factor}")
      return factor
    except:
      factor = self.temporal_config.get('missing_date_factor', 0.7)
      self.logger.warning(f"Invalid date format for {document_type}, using default: {factor}")
      return factor

  def _stepped_decay (self, age_days: int) -> float:
    """Apply stepped decay function based on age thresholds"""
    thresholds = self.temporal_config.get('stepped_decay', {}).get('thresholds', [])

    for threshold in thresholds:
      if age_days <= threshold['days']:
        return threshold['factor']

    # Default fallback if no threshold matches
    return 0.6

  def get_confidence_default (self, document_type: str, var_name: str) -> float:
    """
    Get default confidence with granular fallback:
    1. Feature-specific default (from definitions)
    2. Document-specific default (from config)
    3. Program-level default (from scoring_config)
    """
    # Level 1: Feature-specific (from definitions)
    # Try Stage 1 first, then Stage 2
    var_def = self.definition_loader.get_stage1_definition(var_name)
    if not var_def:
      var_def = self.definition_loader.get_stage2_definition(var_name)

    if var_def and 'default_confidence' in var_def:
      return var_def['default_confidence']

    # Level 2: Document-specific (from config)
    doc_config = self.document_types.get(document_type, {})
    if 'default_confidence' in doc_config:
      return doc_config['default_confidence']

    # Level 3: Program-level fallback
    return self.scoring_config.get('missing_confidence_default', 0.5)

  def calculate_compound_scores_for_claim (
    self,
    stage1_features: List[Dict],
    claim_id: str
  ) -> List[Dict]:
    """
    Calculate compound scores for all features in a claim.
    ... (rest of docstring)
    """
    if not self.scoring_config.get('enabled', True):
      self.logger.info("Compound scoring disabled, skipping")
      return stage1_features

    self.logger.info(f"📊 Calculating compound scores for claim {claim_id}")

    # Build variable-to-category mapping once
    var_to_category = self._build_variable_category_map()

    # Group features by variable name
    features_by_variable = {}

    for doc_features in stage1_features:
      doc_type = doc_features['document_type']
      doc_id = doc_features['document_id']

      for var_name, var_data in doc_features.get('extracted_features', {}).items():
        if var_name not in features_by_variable:
          features_by_variable[var_name] = []

        if not isinstance(var_data, dict):
          self.logger.debug(
            f"Skipping {var_name} - not a structured feature (type: {type(var_data).__name__})"
          )
          continue

        # Collect source info
        source = {
          'document_type': doc_type,
          'document_id': doc_id,
          'document_weight': doc_features.get('document_weight', 0.8),
          'recency_factor': doc_features.get('recency_factor', 1.0),
          'document_date': doc_features.get('document_date'),
          'document_age_days': doc_features.get('document_age_days'),
          'var_name': var_name,
          'var_data': var_data
        }

        features_by_variable[var_name].append(source)

    # Calculate compound scores for each variable
    for var_name, sources in features_by_variable.items():
      # Get category for this variable
      category = var_to_category.get(var_name, "unknown")
      category_display = category.replace('_variables', '').replace('_', ' ').title()

      # Get feature importance mappings from definitions
      feature_importances = self.definition_loader.get_feature_importance(var_name)
      has_feature_importance = bool(feature_importances)

      # Calculate scores for each source
      for source in sources:
        doc_type = source['document_type']

        # Build feature key: document_type.var_name
        feature_key = f"{doc_type}.{var_name}"

        # Get importance (with fallbacks)
        importance = feature_importances.get(
          feature_key,
          feature_importances.get(var_name,
                                  self.scoring_config.get('missing_importance_default', 0.5))
        )

        # Get confidence (with granular fallback)
        confidence = source['var_data'].get('confidence')
        if confidence is None:
          confidence = self.get_confidence_default(doc_type, var_name)

        # Get other components
        doc_weight = source['document_weight']
        recency = source['recency_factor']

        # Calculate compound score
        compound_score = doc_weight * confidence * recency * importance

        # Add compound_scores breakdown to var_data
        source['var_data']['compound_scores'] = {
          'document_weight': round(doc_weight, 3),
          'confidence_score': round(confidence, 3),
          'recency_factor': round(recency, 3),
          'feature_importance': round(importance, 3),
          'compound_score': round(compound_score, 4),
        }

      # Rank sources by compound score (high to low)
      sources.sort(key=lambda x: x['var_data']['compound_scores']['compound_score'], reverse=True)

      # Get category for this variable
      category = var_to_category.get(var_name, "unknown")

      # Group features by variable name
      features_by_variable = {}

      # Format display name
      if category == 'document_specific':
        category_display = "Document Field"
      elif category == 'unknown':
        category_display = "Unknown"
      else:
        category_display = category.replace('_variables', '').replace('_', ' ').title()

      # Add rank to each source
      min_score = self.scoring_config.get('minimum_compound_score', 0.0)
      for rank, source in enumerate(sources, 1):
        source['var_data']['compound_scores']['rank_among_sources'] = rank

        if rank == 1:
          cs = source['var_data']['compound_scores']
          importance_note = "" if has_feature_importance else "without feature importance"

          below_minimum_msg = f" ⚠️ (below minimum {min_score})" if cs['compound_score'] < min_score else ""
          self.logger.debug(
            f"{category_display} - {var_name} ({importance_note}): Top Source = {source['document_type']} "
            f"(Document weight {cs['document_weight']:.2f} , Recency {cs['recency_factor']:.2f} , "  # ×
            f"Confidence {cs['confidence_score']:.2f} , Importance {cs['feature_importance']:.2f} => Compound Score: {cs['compound_score']:.2f} {below_minimum_msg}"
          )


    self.logger.info(f"✅ Compound scores calculated for {len(features_by_variable)} variables")
    return stage1_features

  def _build_variable_category_map (self) -> Dict[str, str]:
    """Build mapping of variable names to their categories from definitions"""
    var_map = {}

    try:
      # Get stage2 variables (these have actuarial categories)
      stage2_vars = self.definition_loader.definitions.get('stage2_variables', {})

      for var_name, var_def in stage2_vars.items():
        category = var_def.get('category', 'unknown')
        # Ensure it ends with _variables
        if not category.endswith('_variables'):
          category = f"{category}_variables"
        var_map[var_name] = category

      # For document-specific variables (like claim_number, date_of_loss, etc.)
      # that appear in document_variable_mapping but not in stage2_variables
      doc_mapping = self.definition_loader.definitions.get('document_variable_mapping', {})

      for doc_type, var_lists in doc_mapping.items():
        for var_list_type in ['primary_variables', 'supporting_variables']:
          var_list = var_lists.get(var_list_type, [])
          for var_name in var_list:
            if var_name not in var_map:
              # Mark as document-specific (not an actuarial category)
              var_map[var_name] = 'document_specific'

      self.logger.debug(f"Built category map for {len(var_map)} variables")

    except Exception as e:
      self.logger.warning(f"Could not build variable category map: {e}")

    return var_map


class ClassProcessStage1:
  """
  Stage 1: Document-specific feature extraction

  Processes each document type separately using:
  - Document-specific function schemas
  - Category + specialized templates
  - Hybrid function calling + rich text
  - Configurable rationale system
  """

  def __init__ (self, config: ClassConfig, logger: ClassLogger,
                api_client: ClassAPIClient, metrics: ClassTrackMetrics):
    self.config = config
    self.logger = logger
    self.api_client = api_client
    self.metrics = metrics

    # Initialize supporting components
    self.schema_loader = ClassLoadSchemas(config, logger)
    self.template_loader = ClassLoadTemplates(config, logger)
    self.prompt_builder = ClassBuildPrompt(config, logger)

    # Initialize date extractor
    self.date_extractor = ClassExtractDate(logger)

    # Initialize compound scorer (needs definition_loader from prompt_builder)
    self.compound_scorer = ClassCalculateScore(config, self.prompt_builder.definition_loader, logger)

    # self.logger.info("✅ Stage1Processor: Date extraction and compound scoring enabled")

    # Settings
    self.stage1_settings = config.get_stage1_settings()
    self.document_types = config.get_document_types()
    self.api_settings = config.get_api_settings()
    self.validation_settings = config.get_validation_settings()

    # Date extractor
    self.date_extractor = ClassExtractDate(logger)

    self.logger.info("✅ Stage 1 Processor initialized")

  def stage1_process_one_document (self, document_text: str, document_type: str,
                                   document_id: str) -> Optional[ClassOutputStage1]:
    """
    Process a single document through Stage 1 extraction

    Returns:
        Stage1DocumentFeatures object with extracted features and rationale
    """
    start_time = perf_counter()

    self.logger.debug_stage1(f"Processing encounter: {document_type} - {document_id}")

    try:
      # Get document type configuration
      if document_type not in self.document_types:
        self.logger.warning(f"Unknown document type: {document_type}")
        return None

      doc_config = self.document_types[document_type]

      # Load function schema
      function_schema = self.schema_loader.load_stage1_schema(document_type)
      if not function_schema:
        self.logger.error(f"Failed to load function schema for {document_type}")
        return None

      # Load templates
      category = doc_config.get('category_template')
      category_template = None
      if category:
        category_template = self.template_loader.load_category_template(category)

      specialized_template = self.template_loader.load_specialized_template(document_type)

      # Build prompt (full version for LLM)
      prompt = self.prompt_builder.build_stage1_prompt(
        document_text=document_text,
        document_type=document_type,
        category_template=category_template,
        specialized_template=specialized_template
      )

      # Make API call with function calling
      self.logger.debug_stage1(f"Making API call for {document_type}")
      response = self.api_client.call_llm_with_function(
        messages=[{"role": "user", "content": prompt}],
        function_schema=function_schema,
        function_name=function_schema['name'],
        model=None,
        max_tokens=None,
        temperature=None,
        call_type=f"Stage1_{document_type}"
      )

      # Record metrics
      success = response.get('success', False)
      self.metrics.record_api_call(
        api_response=response,
        stage='stage1',
        document_type=document_type,
        method='function_calling',
        success=success
      )
      self.metrics.record_stage1_success(document_type, success)

      # Record token usage
      if success:
        usage = response.get('usage', {})
        self.metrics.record_token_usage(
          usage=usage,
          context='stage1',
          doc_type=document_type
        )

      if not success:
        self.logger.error(f"API call failed for {document_id}: {response.get('error')}")
        return None

      # Extract using 'result' key
      result = response['result']  # ✅ Correct for Script 4
      usage = response['usage']
      cost = response['cost']
      model = response['model']

      # Debug log response
      self.logger.debug_api_response(
        json.dumps(result, indent=2),  # ✅ Full structured output
        f"Parsed {document_type}"
      )

      # Validate before proceeding (if enabled)
      if self.validation_settings.get('validate_stage1_schema', True):
        if not self._validate_extraction_result(result, document_type):
          self.logger.error(f"Validation failed for {document_type}")
          return None

      # Validate rationale presence (if enabled)
      if self.validation_settings.get('validate_rationale_presence', False):
        if not self._validate_rationale_presence(result, document_type):
          self.logger.warning(f"Rationale validation warning for {document_type}")

      # Validate source citations (if enabled)
      if self.validation_settings.get('require_source_citations', False):
        if not self._validate_source_citations(result, document_type):
          self.logger.warning(f"Source citation validation warning for {document_type}")

      # NORMALIZE FEATURES
      overall_confidence = result.get('confidence_metadata', {}).get('overall_confidence', 0.8)

      normalized_features = self._normalize_extracted_features(
          structured_features=result.get('structured_features', {}),
          document_type=document_type,
          overall_confidence=overall_confidence
      )

      self.logger.debug_stage1(f"Normalized {len(normalized_features)} features for {document_type}")


      # Extract document date
      document_date = self.date_extractor.extract_date(document_text, document_type)
      document_age_days = self.date_extractor.calculate_age_days(
        document_date) if document_date else None

      # Calculate document weight (from config)
      doc_type_config = self.document_types.get(document_type, {})
      document_weight = doc_type_config.get('weight', 0.8)

      # Calculate recency factor
      recency_factor = self.compound_scorer.calculate_recency_factor(document_date, document_type)

      # Log temporal info
      if document_date:
        self.logger.info(

          f"📅 {document_type}: date={document_date}, "
          f"age={document_age_days}d, recency={recency_factor:.2f}"
        )
      else:
        self.logger.warning(f"📅 {document_type}: No date found, recency={recency_factor:.2f}")

      # Build enhanced Stage1DocumentFeatures object
      features = ClassOutputStage1(
        document_id=document_id,
        document_type=document_type,
        extracted_features=normalized_features,
        narrative_analysis=result.get('narrative_analysis', ''),
        confidence_score=overall_confidence,
        processing_metadata={
          'api_cost': response.get('cost', 0.0),
          'tokens_used': response.get('usage', {}),
          'processing_time': perf_counter() - start_time,
          'model': model,
          'temperature': self.config.get_stage1_settings().get('temperature', 0.7),
          'function_schema': function_schema.get('name')
          # 'date_metadata': date_metadata
        },
        extraction_confidence=result.get('confidence_metadata', {}).get('overall_confidence', 0.0),
        processing_notes=f"Processed with {model} using function calling",
        stage1_method='function_calling',
        input_source='text_document',
        # NEW FIELDS
        document_date=document_date,
        document_age_days=document_age_days,
        document_weight=document_weight,
        recency_factor=recency_factor
      )

      # Record processing time
      duration = perf_counter() - start_time
      self.metrics.record_processing_time('stage1', duration)

      self.logger.debug_stage1(
        f"Successfully processed encounter: {document_id} in {duration:.2f}s")

      return features

    except Exception as e:
      self.logger.error(f"Error processing document {document_id}: {e}")
      self.metrics.record_stage1_success(document_type, False)
      return None

  def _validate_extraction_result (self, data: Dict, document_type: str) -> bool:
    """Validate extracted data has required fields and structure"""
    try:
      # Check that we got a dictionary with some content
      if not data or not isinstance(data, dict):
        self.logger.error(f"Invalid data structure for {document_type}")
        return False

      # Check that we have at least some fields (not empty)
      if len(data) < 2:
        self.logger.error(f"Insufficient data in {document_type}: only {len(data)} fields")
        return False

      # Check content has reasonable length (not just empty strings)
      total_content = str(data)
      if len(total_content) < 50:
        self.logger.error(f"Data too short for {document_type}: {len(total_content)} chars")
        return False

      return True

    except Exception as e:
      self.logger.error(f"Validation error for {document_type}: {e}")
      return False

  def _validate_rationale_presence (self, data: Dict, document_type: str) -> bool:
    """Validate that rationale fields are present in extracted data"""
    try:
      # Check if rationale system is enabled
      rationale_settings = self.config.get_rationale_settings()
      if not rationale_settings.get('enabled', False):
        return True  # Skip validation if rationale system is disabled

      structured_features = data.get('structured_features', {})
      if not structured_features:
        self.logger.warning(f"No structured features found for rationale validation in {document_type}")
        return False

      # Count how many features have rationale
      features_with_rationale = 0
      total_features = 0

      for var_name, var_data in structured_features.items():
        if isinstance(var_data, dict):
          total_features += 1
          if 'rationale' in var_data or 'reasoning' in var_data:
            features_with_rationale += 1

      # Require at least 50% of features to have rationale
      if total_features > 0:
        rationale_percentage = features_with_rationale / total_features
        if rationale_percentage < 0.5:
          self.logger.warning(
            f"Low rationale coverage in {document_type}: "
            f"{features_with_rationale}/{total_features} features ({rationale_percentage:.0%})"
          )
          return False

      return True

    except Exception as e:
      self.logger.error(f"Rationale validation error for {document_type}: {e}")
      return False

  def _validate_source_citations (self, data: Dict, document_type: str) -> bool:
    """Validate that source citations are present in extracted data"""
    try:
      # Check for source_documents field
      source_docs = data.get('source_documents', [])
      if not source_docs or len(source_docs) == 0:
        self.logger.warning(f"No source citations found in {document_type}")
        return False

      return True

    except Exception as e:
      self.logger.error(f"Source citation validation error for {document_type}: {e}")
      return False

  # Add these methods to the Stage1Processor class in Script 4

  def _normalize_extracted_features (self, structured_features: Dict, document_type: str,
                                     overall_confidence: float = 0.8) -> Dict:
    """
    Normalize extracted features to ensure consistent structure for Stage 2.

    Handles all data types from Stage 1 schemas:
    - Primitive types (string, number, boolean)
    - Arrays (list of strings or objects)
    - Nested objects
    - Already-structured features (pass-through)
    """
    normalized = {}

    for var_name, var_data in structured_features.items():
      # Check if already in structured format
      if isinstance(var_data, dict) and 'value' in var_data:
        normalized[var_name] = var_data
        continue

      # Normalize primitive/complex values
      field_confidence = self._calculate_field_confidence(
        var_data, var_name, overall_confidence
      )

      rationale_type = self._determine_rationale_type(var_data, var_name)

      normalized[var_name] = {
        'value': var_data,
        'confidence': field_confidence,
        'rationale': f"Extracted from {document_type}",
        'rationale_type': rationale_type,
        'source_document': document_type
      }

    return normalized

  def _calculate_field_confidence (self, value: any, field_name: str,
                                   base_confidence: float) -> float:
    """Calculate field-specific confidence based on value completeness and type"""

    # Missing/empty values
    if value is None:
      return max(0.2, base_confidence * 0.3)

    if isinstance(value, str) and value.strip() == '':
      return max(0.3, base_confidence * 0.4)

    if isinstance(value, list) and len(value) == 0:
      return max(0.3, base_confidence * 0.5)

    if isinstance(value, dict) and len(value) == 0:
      return max(0.3, base_confidence * 0.5)

    # Boolean values (often inferred)
    if isinstance(value, bool):
      return max(0.7, base_confidence * 0.9)

    # Numeric values
    if isinstance(value, (int, float)):
      # Boost confidence for financial data
      if any(keyword in field_name.lower() for keyword in ['amount', 'reserve', 'cost', 'payment']):
        return min(1.0, base_confidence * 1.1)
      return base_confidence

    # Arrays with multiple items
    if isinstance(value, list) and len(value) > 1:
      return min(1.0, base_confidence * 1.05)

    # Nested objects with multiple fields
    if isinstance(value, dict) and len(value) > 2:
      return min(1.0, base_confidence * 1.05)

    return base_confidence

  def _determine_rationale_type (self, value: any, field_name: str) -> str:
    """Determine rationale type based on field characteristics"""

    # Boolean fields are typically inferred
    if isinstance(value, bool):
      return 'inferred'

    # Numeric calculations are derived
    if isinstance(value, (int, float)) and any(
      keyword in field_name.lower()
      for keyword in ['delay', 'duration', 'age', 'count', 'percentage']
    ):
      return 'derived'

    # Amounts and dates are typically verbatim
    if any(keyword in field_name.lower() for keyword in [
      'amount', 'date', 'number', 'claim_number', 'policy'
    ]):
      return 'verbatim'

    # Arrays and complex objects are extracted
    if isinstance(value, (list, dict)):
      return 'extracted'

    return 'extracted'

  def stage1_process_all_documents (self, claim_data: Dict) -> List[ClassOutputStage1]:
    """
    Process all documents for a claim through Stage 1

    Args:
        claim_data: Claim JSON with encounters list

    Returns:
        List of Stage1DocumentFeatures objects
    """
    claim_id = claim_data.get('claim_id', 'unknown')
    encounters = claim_data.get('encounters', [])

    self.logger.info(f"Processing {len(encounters)} documents for claim id")

    stage1_results = []

    for i, encounter in enumerate(encounters, 1):
      document_type = encounter.get('document_type', 'unknown')
      document_text = (
        encounter.get('document_text') or  # Script 3 format
        encounter.get('clinical_note') or  # Script 1 (FHIR)
        encounter.get('notes') or  # Script 2 (synthetic docs)
        encounter.get('text') or  # Generic fallback
        ''  # Empty string as last resort
      )
      # document_text = encounter.get('document_text', encounter.get('text', ''))
      document_id = encounter.get('encounter_id', f"{claim_id}_doc_{i}")

      self.logger.info("")
      self.logger.info("=" * 60)

      if not document_text:
        self.logger.warning(f"Empty document text for {document_id}")
        continue

      self.logger.info(f"[{i}/{len(encounters)}] Processing document: {document_type}...")

      # Process document
      features = self.stage1_process_one_document(
        document_text=document_text,
        document_type=document_type,
        document_id=document_id
      )

      if features:
        stage1_results.append(features)
        self.logger.success(f"✓ Extracted features from {document_type}")
      else:
        self.logger.error(f"✗ Failed to process {document_type}")

    return stage1_results


class ClassValidateStage2:
  """
  Validates Stage 2 outputs against variable definitions
  Generates warnings and quality flags without modifying data
  """

  def __init__ (self, definition_loader: ClassVariableDefinitions, logger: ClassLogger, config: ClassConfig):
    self.definitions = definition_loader
    self.logger = logger
    self.config = config
    self.validation_settings = config.get_validation_settings()

    # Load schema mapping for deduplication
    self._init_schema_mapping()

  def _init_schema_mapping (self):
    """Initialize mapping of where each variable should be"""
    self.correct_placement = {
      # Reserving variables
      'claim_severity': 'reserving_variables',
      'injury_severity': 'reserving_variables',
      'medical_complexity': 'reserving_variables',
      'treatment_type': 'reserving_variables',
      'expected_development_pattern': 'reserving_variables',
      'ultimate_cost_category': 'reserving_variables',
      'total_incurred_cost': 'reserving_variables',
      'estimated_outstanding_cost': 'reserving_variables',
      'ultimate_cost_prediction': 'reserving_variables',
      'permanent_disability_rating': 'reserving_variables',
      'recovery_timeline_days': 'reserving_variables',
      'maximum_medical_improvement_reached': 'reserving_variables',
      'total_medical_costs': 'reserving_variables',
      'total_indemnity_paid': 'reserving_variables',
      'settlement_amount': 'reserving_variables',
      'reserve_adequacy': 'reserving_variables',
      'medical_provider_quality': 'reserving_variables',

      # Ratemaking variables
      'risk_level': 'ratemaking_variables',
      'causation_type': 'ratemaking_variables',
      'industry_risk_category': 'ratemaking_variables',
      'industry_risk_level': 'ratemaking_variables',
      'safety_compliance': 'ratemaking_variables',
      'experience_modifier_impact': 'ratemaking_variables',
      'employer_size_category': 'ratemaking_variables',
      'claim_frequency_indicator': 'ratemaking_variables',

      # Claim management variables
      'litigation_risk': 'claim_management_variables',
      'settlement_likelihood': 'claim_management_variables',
      'management_complexity': 'claim_management_variables',
      'fraud_risk': 'claim_management_variables',
      'time_to_closure_days': 'claim_management_variables',
      'recommended_reserve': 'claim_management_variables',
      'work_relatedness_status': 'claim_management_variables',
      'return_to_work_status': 'claim_management_variables',
      'claim_closure_status': 'claim_management_variables',
      'subrogation_potential': 'claim_management_variables',
      'claimant_cooperation_level': 'claim_management_variables'
    }

  def deduplicate_and_fix_placement (
    self,
    actuarial_variables: Dict,
    claim_id: str
  ) -> Tuple[Dict, Dict]:
    """
    Remove duplicate and misplaced variables

    Args:
        actuarial_variables: The actuarial_variables dict from Stage 2
        claim_id: Claim identifier for logging

    Returns:
        (fixed_variables, report)
    """
    report = {
      'duplicates_fixed': [],
      'misplaced_fixed': [],
      'variables_removed': []
    }

    # Track variables seen
    seen_variables = {}

    # Scan for duplicates and misplacements
    for category in ['reserving_variables', 'ratemaking_variables', 'claim_management_variables']:
      if category not in actuarial_variables:
        continue

      category_data = actuarial_variables[category]
      if not isinstance(category_data, dict):
        continue

      vars_to_remove = []

      for var_name in list(category_data.keys()):
        # Check if we've seen this variable before
        if var_name in seen_variables:
          # Duplicate - decide which to keep
          correct_category = self.correct_placement.get(var_name)

          if correct_category == category:
            # This is correct location, remove from wrong location
            prev_category = seen_variables[var_name]
            if prev_category in actuarial_variables:
              if var_name in actuarial_variables[prev_category]:
                del actuarial_variables[prev_category][var_name]
                report['duplicates_fixed'].append(
                  f"{var_name}: removed from {prev_category}, kept in {category}"
                )
          else:
            # This is wrong location, mark for removal
            vars_to_remove.append(var_name)
            report['duplicates_fixed'].append(
              f"{var_name}: removed from {category}, keeping in {seen_variables[var_name]}"
            )

        # Check if variable is in correct category
        elif var_name in self.correct_placement:
          correct_category = self.correct_placement[var_name]
          if correct_category != category:
            vars_to_remove.append(var_name)
            report['misplaced_fixed'].append(
              f"{var_name}: moved from {category} to {correct_category}"
            )

            # Move to correct category
            if correct_category not in actuarial_variables:
              actuarial_variables[correct_category] = {}
            actuarial_variables[correct_category][var_name] = category_data[var_name]

        # Track this variable
        if var_name not in vars_to_remove:
          seen_variables[var_name] = category

      # Remove misplaced variables
      for var in vars_to_remove:
        if var in category_data:
          del category_data[var]
          report['variables_removed'].append(f"{var} from {category}")

    # Log summary
    total_fixes = (
      len(report['duplicates_fixed']) +
      len(report['misplaced_fixed'])
    )

    if total_fixes > 0:
      self.logger.warning(
        f"Fixed {total_fixes} variable placement issues for {claim_id}"
      )
      for fix in report['duplicates_fixed'][:3]:  # Show first 3
        self.logger.debug_stage2(f"  • {fix}")
      for fix in report['misplaced_fixed'][:3]:  # Show first 3
        self.logger.debug_stage2(f"  • {fix}")

    return actuarial_variables, report

  def validate_stage2_output (
    self,
    actuarial_variables: Dict,
    claim_id: str
  ) -> Tuple[Dict, List[str]]:
    """
    Validate Stage 2 output and generate quality flags

    Args:
        actuarial_variables: The actuarial_variables dict from Stage 2
        claim_id: Claim identifier for logging

    Returns:
        (validated_variables, quality_flags)
    """
    quality_flags = []
    warnings = []

    # 1: Deduplicate and fix placement FIRST
    actuarial_variables, dedup_report = self.deduplicate_and_fix_placement(
      actuarial_variables,
      claim_id
    )

    # Add quality flags for fixed issues
    if dedup_report['duplicates_fixed']:
      quality_flags.append(f"DUPLICATES_FIXED_{len(dedup_report['duplicates_fixed'])}")
    if dedup_report['misplaced_fixed']:
      quality_flags.append(f"MISPLACED_FIXED_{len(dedup_report['misplaced_fixed'])}")

    # 2. Validate individual variables (if enabled)
    if self.validation_settings.get('validate_stage2_schema', True):
      for category_name, category_vars in actuarial_variables.items():
        if not isinstance(category_vars, dict):
          continue

        for var_name, var_value in category_vars.items():
          is_valid, var_warnings = self.definitions.validate_extraction(
            var_name, var_value, stage=2
          )

          if not is_valid:
            warnings.extend(var_warnings)
            quality_flags.append(f"VALIDATION_WARNING: {var_name}")

      # 3. Validate cross-variable consistency

      consistency_valid, consistency_warnings = self.definitions.validate_stage2_consistency(
        actuarial_variables
      )

      if not consistency_valid:
        warnings.extend(consistency_warnings)
        quality_flags.append("CONSISTENCY_ISSUES_DETECTED")

      # 4. Specific validation for critical variables

      reserving = actuarial_variables.get('reserving_variables', {})

      # Check ultimate_cost_prediction vs ultimate_cost_category
      cost_issues = self._validate_cost_category_alignment(reserving)
      if cost_issues:
        warnings.extend(cost_issues)
        quality_flags.append("COST_CATEGORY_MISMATCH")

      # Check settlement consistency
      settlement_issues = self._validate_settlement_consistency(reserving)
      if settlement_issues:
        warnings.extend(settlement_issues)
        quality_flags.append("SETTLEMENT_ULTIMATE_MISMATCH")

      # Check total_incurred vs ultimate_cost
      progression_issues = self._validate_cost_progression(reserving)
      if progression_issues:
        warnings.extend(progression_issues)
        quality_flags.append("COST_PROGRESSION_ISSUE")

    # 4.5. Validate rationale presence (if enabled)
    if self.validation_settings.get('validate_rationale_presence', False):
      rationale_warnings = self._validate_rationale_presence_stage2(actuarial_variables, claim_id)
      if rationale_warnings:
        warnings.extend(rationale_warnings)
        quality_flags.append("LOW_RATIONALE_COVERAGE")

    # 4.6. Validate source citations (if enabled)
    if self.validation_settings.get('require_source_citations', False):
      source_warnings = self._validate_source_citations_stage2(actuarial_variables, claim_id)
      if source_warnings:
        warnings.extend(source_warnings)
        quality_flags.append("MISSING_SOURCE_CITATIONS")

    # 5. Log all warnings

    if warnings:
      self.logger.warning(f"⚠️  Validation issues for claim {claim_id}:")
      for warning in warnings:
        self.logger.warning(f"   - {warning}")
    else:
      self.logger.info(f"✅ No validation issues for claim {claim_id}")

    return actuarial_variables, quality_flags


  def _validate_cost_category_alignment (self, reserving: Dict) -> List[str]:
    """
    CRITICAL: Validate ultimate_cost_category matches ultimate_cost_prediction
    This is the PRIMARY use case for the variable definition system
    """
    issues = []

    # Extract values (handle rationale wrapper)
    cost_pred = reserving.get('ultimate_cost_prediction', {})
    cost_cat = reserving.get('ultimate_cost_category', {})

    # Handle rationale wrapper
    if isinstance(cost_pred, dict):
      pred_value = cost_pred.get('value', 0)
    else:
      pred_value = cost_pred

    if isinstance(cost_cat, dict):
      cat_value = cost_cat.get('value', '')
    else:
      cat_value = cost_cat

    if not pred_value or not cat_value:
      return issues

    # Use definition loader's validation method
    is_valid, message = self.definitions.validate_ultimate_cost_category(
      pred_value,
      cat_value
    )

    if not is_valid:
      expected_cat = self.definitions.get_expected_category_for_amount(pred_value)

      issues.append(
        f"🚨 CRITICAL: {message}\n"
        f"   Prediction: ${pred_value:,.0f}\n"
        f"   Current Category: {cat_value}\n"
        f"   Expected Category: {expected_cat}\n"
        f"   This is a MATHEMATICAL inconsistency that MUST be flagged."
      )

      self.logger.error(
        f"🚨 COST CATEGORY MISMATCH for ultimate_cost_prediction=${pred_value:,}\n"
        f"   LLM classified as: {cat_value}\n"
        f"   Should be: {expected_cat}"
      )

    return issues

  def _validate_cost_progression (self, reserving: Dict) -> List[str]:
    """Check if ultimate_cost >= total_incurred_cost"""
    issues = []

    ultimate = reserving.get('ultimate_cost_prediction', {})
    incurred = reserving.get('total_incurred_cost', {})

    if isinstance(ultimate, dict):
      ultimate_value = ultimate.get('value', 0)
    else:
      ultimate_value = ultimate

    if isinstance(incurred, dict):
      incurred_value = incurred.get('value', 0)
    else:
      incurred_value = incurred

    if ultimate_value and incurred_value:
      if ultimate_value < incurred_value:
        issues.append(
          f"COST PROGRESSION ISSUE: ultimate_cost_prediction (${ultimate_value:,}) "
          f"is less than total_incurred_cost (${incurred_value:,}). "
          f"Ultimate cost cannot be less than already incurred costs."
        )

    return issues

  def _validate_settlement_consistency (self, reserving: Dict) -> List[str]:
    """Validate that settling claims have ultimate == settlement"""
    issues = []

    ultimate_pred = self._extract_value(reserving.get('ultimate_cost_prediction'))
    settlement_amt = self._extract_value(reserving.get('settlement_amount'))
    claim_status = self._extract_value(reserving.get('claim_closure_status'))

    # For settling claims, ultimate should equal settlement
    if claim_status in ['closed_settled', 'pending_settlement']:
      if all(v is not None for v in [settlement_amt, ultimate_pred]):
        if abs(settlement_amt - ultimate_pred) > 100:  # Allow $100 tolerance
          issues.append(
            f"⚠️  SETTLEMENT MISMATCH: For settling claim, "
            f"ultimate_cost_prediction (${ultimate_pred:,.0f}) "
            f"should equal settlement_amount (${settlement_amt:,.0f}). "
            f"Settlement IS the ultimate cost - do not add speculation."
          )

    return issues

  def _extract_value (self, field: Any) -> Any:
    """Extract value from field (handles rationale wrapper)"""
    if field is None:
      return None
    if isinstance(field, dict) and 'value' in field:
      return field['value']
    return field

  def _validate_rationale_presence_stage2 (self, actuarial_variables: Dict, claim_id: str) -> List[str]:
    """Validate that rationale fields are present in Stage 2 output"""
    warnings = []

    # Check if rationale system is enabled
    rationale_settings = self.config.get_rationale_settings()
    if not rationale_settings.get('enabled', False):
      return []  # Skip validation if rationale system is disabled

    # Count variables with rationale across all categories
    total_variables = 0
    variables_with_rationale = 0

    for category_name, category_vars in actuarial_variables.items():
      if not isinstance(category_vars, dict):
        continue

      for var_name, var_value in category_vars.items():
        total_variables += 1
        if isinstance(var_value, dict) and ('rationale' in var_value or 'reasoning' in var_value):
          variables_with_rationale += 1

    # Require at least 50% of variables to have rationale
    if total_variables > 0:
      rationale_percentage = variables_with_rationale / total_variables
      if rationale_percentage < 0.5:
        warnings.append(
          f"Low rationale coverage in claim {claim_id}: "
          f"{variables_with_rationale}/{total_variables} variables ({rationale_percentage:.0%})"
        )

    return warnings

  def _validate_source_citations_stage2 (self, actuarial_variables: Dict, claim_id: str) -> List[str]:
    """Validate that source citations are present in Stage 2 output"""
    warnings = []

    # Check if any variables have source_documents field
    has_any_sources = False

    for category_name, category_vars in actuarial_variables.items():
      if not isinstance(category_vars, dict):
        continue

      for var_name, var_value in category_vars.items():
        if isinstance(var_value, dict):
          source_docs = var_value.get('source_documents', [])
          if source_docs and len(source_docs) > 0:
            has_any_sources = True
            break

      if has_any_sources:
        break

    if not has_any_sources:
      warnings.append(f"No source citations found in claim {claim_id}")

    return warnings


class ClassProcessStage2:
  """
  Stage 2: Cross-document aggregation into final actuarial variables

  Aggregates Stage 1 features across all documents for a claim:
  - Uses Stage 2 aggregation function schema
  - LLM-based conflict detection and resolution
  - Produces final actuarial variables with rationales
  """

  def __init__ (self, config: ClassConfig, logger: ClassLogger,
                api_client: ClassAPIClient, metrics: ClassTrackMetrics):
    self.config = config
    self.logger = logger
    self.api_client = api_client
    self.metrics = metrics

    # Initialize supporting components
    self.schema_loader = ClassLoadSchemas(config, logger)
    self.prompt_builder = ClassBuildPrompt(config, logger)

    # Enhanced prompt for correct variable placement
    self.enhanced_instructions = """
    CRITICAL VARIABLE PLACEMENT RULES:

You must place each variable in EXACTLY ONE category. DO NOT create duplicates.

RESERVING VARIABLES ONLY:
- claim_severity
- injury_severity
- medical_complexity
- treatment_type
- expected_development_pattern
- ultimate_cost_category ← ONLY HERE, NOT in ratemaking!
- total_incurred_cost
- estimated_outstanding_cost
- ultimate_cost_prediction
- permanent_disability_rating
- recovery_timeline_days
- maximum_medical_improvement_reached
- total_medical_costs
- total_indemnity_paid
- settlement_amount
- reserve_adequacy
- medical_provider_quality

RATEMAKING VARIABLES ONLY:
- risk_level
- causation_type
- industry_risk_category
- industry_risk_level
- safety_compliance
- experience_modifier_impact
- employer_size_category
- claim_frequency_indicator

CLAIM MANAGEMENT VARIABLES ONLY:
- litigation_risk ← ONLY HERE, NOT in ratemaking!
- settlement_likelihood ← ONLY HERE, NOT in ratemaking!
- management_complexity ← ONLY HERE, NOT in ratemaking!
- fraud_risk
- time_to_closure_days
- recommended_reserve
- work_relatedness_status ← ONLY HERE, NOT in ratemaking!
- return_to_work_status
- claim_closure_status
- subrogation_potential
- claimant_cooperation_level

VALIDATION CHECKS:
1. Each variable appears in exactly ONE category
2. No variable appears in multiple categories
3. Only variables listed above are included
4. All required fields are present
    """

    # Initialize validator
    self.validator = ClassValidateStage2(
      self.prompt_builder.definition_loader,
      logger,
      config
    )

    # Settings
    self.stage2_settings = config.get_stage2_settings()
    self.api_settings = config.get_api_settings()

    # Compound scorer
    self.compound_scorer = ClassCalculateScore(config, self.prompt_builder.definition_loader, logger)

    self.logger.info("✅ Stage 2 Processor initialized with validation")

  def stage2_process_all_features (self, claim_id: str, stage1_features: List[ClassOutputStage1]) -> \
    Optional[ClassOutputStage2]:
    """
    Aggregate Stage 1 features into final actuarial analysis

    Args:
        claim_id: Claim identifier
        stage1_features: List of Stage1DocumentFeatures objects

    Returns:
        Stage2FinalAnalysis object with final actuarial variables
    """
    start_time = perf_counter()

    self.logger.debug_stage2(f"Aggregating {len(stage1_features)} documents for claim {claim_id}")

    try:
      # Load Stage 2 function schema
      function_schema = self.schema_loader.load_stage2_schema()
      if not function_schema:
        self.logger.error("Failed to load Stage 2 function schema")
        return None

      # Convert Stage 1 features to dict format
      # (Already includes document_date, document_age_days, document_weight, recency_factor)
      stage1_dicts = [features.to_dict() for features in stage1_features]

      # Calculate compound scores for all features
      stage1_dicts = self.compound_scorer.calculate_compound_scores_for_claim(
        stage1_dicts,
        claim_id
      )

      # Build prompt with or without score guidance
      if self.config.get_compound_scoring().get('include_scores_in_prompt', True):
        self.logger.debug("Building Stage 2 prompt with compound score rankings")
        prompt = self.prompt_builder.build_stage2_prompt_with_scores(
          stage1_features=stage1_dicts,
          claim_id=claim_id
        )
      else:
        self.logger.debug("Building standard Stage 2 prompt (scores disabled)")
        prompt = self.prompt_builder.build_stage2_prompt(
          stage1_features=stage1_dicts,
          claim_id=claim_id
        )

      prompt += "\n\n" + self.enhanced_instructions

      call_type = "Stage2"

      # Make API call
      self.logger.debug_stage2(f"Making Stage 2 API call for claim {claim_id}")
      response = self.api_client.call_llm_with_function(
        messages=[{"role": "user", "content": prompt}],
        function_schema=function_schema,
        function_name=function_schema['name'],
        model=None,
        max_tokens=None,
        temperature=None,
        call_type=call_type
      )

      # Record metrics
      success = response.get('success', False)
      self.metrics.record_api_call(
        api_response=response,
        stage='stage2',
        method='function_calling',
        success=success
      )
      self.metrics.record_stage2_success(success)

      # Record token usage
      if success:
        usage = response.get('usage', {})
        self.metrics.record_token_usage(
          usage=usage,
          context='stage2',
          doc_type=None
        )

      if not success:
        self.logger.error(f"Stage 2 API call failed: {response.get('error')}")
        return None

      # Extract result
      result = response.get('result', {})

      self.logger.debug_api_response(
        json.dumps(result, indent=2),
        "Parsed Stage2 Aggregation"
      )

      # Get the complete actuarial_variables with rationale fields intact
      actuarial_variables = result.get('actuarial_variables', {})

      # Validate against definitions (single call)
      validated_variables, quality_flags = self.validator.validate_stage2_output(
        actuarial_variables,
        claim_id
      )

      # Log quality flags summary if any issues found
      if quality_flags:
        self.logger.warning(
          f"⚠️  Claim {claim_id} completed with {len(quality_flags)} quality flags")
        for flag in quality_flags:
          self.logger.warning(f"   - {flag}")

      # Log if rationale is present (for debugging)
      if self.config.get_rationale_settings().get('enabled', False):
        rationale_found = False
        for var_name, var_value in actuarial_variables.items():
          if isinstance(var_value, dict):
            for sub_var_name, sub_var_value in var_value.items():
              if isinstance(sub_var_value, dict) and 'rationale' in sub_var_value:
                rationale_found = True
                break
          if rationale_found:
            break

        if rationale_found:
          self.logger.debug_stage2("✅ Rationale fields detected in Stage 2 response")
        else:
          self.logger.warning(
            "⚠️ Rationale fields NOT found in Stage 2 response (rationale enabled)")

      # Build Stage2FinalAnalysis object with COMPLETE actuarial_variables
      analysis = ClassOutputStage2(
        claim_id=claim_id,
        processing_timestamp=datetime.now().isoformat(),
        actuarial_variables=actuarial_variables,  # ✅ PRESERVE COMPLETE STRUCTURE
        aggregated_narrative=result.get('aggregated_narrative', ''),
        confidence_scores=result.get('confidence_scores', {}),
        cost_predictions=self._extract_cost_predictions(result),
        risk_assessment=self._extract_risk_assessment(result),
        encounters_processed=len(stage1_features),
        stage2_method='function_calling_aggregation',
        input_source='stage1_features',
        quality_flags=self._generate_quality_flags(result, stage1_features)
      )

      # Record processing time
      duration = perf_counter() - start_time
      self.metrics.record_processing_time('stage2', duration)

      # Log validation summary
      if quality_flags:
        self.logger.warning(
          f"⚠️  Claim {claim_id} completed with {len(quality_flags)} quality flags"
        )
      else:
        self.logger.info(f"✅ Claim {claim_id} validated successfully")

      return analysis

    except Exception as e:
      self.logger.error(f"Error aggregating claim {claim_id}: {e}")
      self.metrics.record_stage2_success(False)
      return None

  def _extract_cost_predictions (self, result: Dict) -> Dict:
    """Extract cost-related predictions from aggregated result"""
    actuarial_vars = result.get('actuarial_variables', {})

    cost_predictions = {}

    # Look for cost-related fields in all variable categories
    for category_name, category_value in actuarial_vars.items():
      if isinstance(category_value, dict):
        for key, value in category_value.items():
          if 'cost' in key.lower() or 'reserve' in key.lower():
            # Handle rationale-wrapped values
            if isinstance(value, dict) and 'value' in value:
              cost_predictions[key] = value['value']
            else:
              cost_predictions[key] = value

    return cost_predictions

  def _extract_risk_assessment (self, result: Dict) -> Dict:
    """Extract risk-related assessments from aggregated result"""
    actuarial_vars = result.get('actuarial_variables', {})

    risk_assessment = {}

    # Look for risk-related fields in all variable categories
    for category_name, category_value in actuarial_vars.items():
      if isinstance(category_value, dict):
        for key, value in category_value.items():
          if 'risk' in key.lower() or 'litigation' in key.lower() or 'fraud' in key.lower():
            # Handle rationale-wrapped values
            if isinstance(value, dict) and 'value' in value:
              risk_assessment[key] = value['value']
            else:
              risk_assessment[key] = value

    return risk_assessment

  def _generate_quality_flags (self, result: Dict, stage1_features: List[ClassOutputStage1]) -> \
    List[str]:
    """
    Generate quality flags based on analysis results.

    Checks:
    - Category-level confidence (overall, reserving, ratemaking, claim_management)
    - Variable-level confidence (individual actuarial variables)
    - Conflicts, document coverage, missing key documents

    Uses configurable thresholds from quality_control section in config.yaml
    """
    flags = []

    # Get quality control settings
    quality_settings = self.config.get_quality_control_settings()

    # Check if confidence flagging is enabled
    if not quality_settings.get('flag_low_confidence', True):
      self.logger.debug("Confidence flagging disabled, skipping confidence checks")
      # Still check non-confidence flags
      flags.extend(self._check_non_confidence_flags(result, stage1_features))
      return flags

    # Get thresholds with defaults
    category_low = quality_settings.get('category_confidence_low', 0.6)
    category_medium = quality_settings.get('category_confidence_medium', 0.7)
    variable_low = quality_settings.get('variable_confidence_low', 0.5)
    variable_medium = quality_settings.get('variable_confidence_medium', 0.7)

    # 1. CHECK CATEGORY-LEVEL CONFIDENCE
    confidence_scores = result.get('confidence_scores', {})

    # Categories to check (exclude data_completeness)
    categories_to_check = ['overall', 'reserving', 'ratemaking', 'claim_management']

    for category in categories_to_check:
      if category not in confidence_scores:
        continue

      score = confidence_scores[category]
      category_name = category.upper().replace('_', '_')  # Keep underscores as-is

      if score <= category_low:
        flags.append(f"{category_name}-category-CONFIDENCE_LOW-{score:.2f}")
      elif score <= category_medium:
        flags.append(f"{category_name}-category-CONFIDENCE_MEDIUM-{score:.2f}")

    # 2. CHECK VARIABLE-LEVEL CONFIDENCE
    actuarial_vars = result.get('actuarial_variables', {})

    # Map category keys to uppercase for flag names
    category_map = {
      'reserving_variables': 'RESERVING',
      'ratemaking_variables': 'RATEMAKING',
      'claim_management_variables': 'CLAIM_MANAGEMENT'
    }

    for category_key, category_name in category_map.items():
      if category_key not in actuarial_vars:
        continue

      variables = actuarial_vars[category_key]
      if not isinstance(variables, dict):
        continue

      for var_name, var_data in variables.items():
        if not isinstance(var_data, dict):
          continue

        # Get variable confidence
        var_confidence = var_data.get('confidence')

        if var_confidence is None:
          continue

        # Check thresholds
        if var_confidence <= variable_low:
          flags.append(f"{category_name}-{var_name}-CONFIDENCE_LOW-{var_confidence:.2f}")
        elif var_confidence <= variable_medium:
          flags.append(f"{category_name}-{var_name}-CONFIDENCE_MEDIUM-{var_confidence:.2f}")

    # 3. ADD NON-CONFIDENCE FLAGS
    flags.extend(self._check_non_confidence_flags(result, stage1_features))

    return flags

  def _check_non_confidence_flags (self, result: Dict, stage1_features: List[ClassOutputStage1]) -> \
    List[str]:
    """
    Check for non-confidence quality flags (conflicts, document coverage, etc.)

    Returns:
        List of quality flag strings
    """
    flags = []

    # Get quality control settings
    quality_settings = self.config.get_quality_control_settings()

    # Check for conflicts (if enabled)
    if quality_settings.get('flag_conflicts', True):
      actuarial_vars = result.get('actuarial_variables', {})
      for category_key, category_value in actuarial_vars.items():
        if isinstance(category_value, dict):
          for var_name, var_data in category_value.items():
            if isinstance(var_data, dict):
              rationale_type = var_data.get('rationale_type', '')
              if rationale_type == 'conflict_resolved':
                flags.append("CONFLICTS_DETECTED")
                break
        if "CONFLICTS_DETECTED" in flags:
          break

    # Check document coverage (if missing documents flagging enabled)
    if quality_settings.get('flag_missing_documents', True):
      # Check for limited documents
      if len(stage1_features) < 3:
        flags.append("LIMITED_DOCUMENTS")

      # Check for missing key documents
      doc_types = {f.document_type for f in stage1_features}
      required_docs = quality_settings.get('required_documents', [])

      for required_doc in required_docs:
        if required_doc not in doc_types:
          flags.append(f"MISSING_{required_doc.upper()}")

    return flags

  def get_temporal_weighting (self) -> Dict:
    """
    Get temporal weighting configuration for recency calculation.
    Returns config with defaults if not present.
    """
    return self.config.get('temporal_weighting', {
      'enabled': True,
      'decay_function': 'stepped',
      'missing_date_factor': 0.7,
      'stepped_decay': {
        'thresholds': [
          {'days': 30, 'factor': 1.0},
          {'days': 90, 'factor': 0.9},
          {'days': 180, 'factor': 0.8},
          {'days': 365, 'factor': 0.7},
          {'days': 999999, 'factor': 0.6}
        ]
      },
      'document_overrides': {}
    })

  def get_compound_scoring (self) -> Dict:
    """
    Get compound scoring configuration.
    Returns config with defaults if not present.
    """
    return self.config.get('compound_scoring', {
      'enabled': True,
      'use_document_weight': True,
      'use_confidence_score': True,
      'use_recency_factor': True,
      'use_feature_importance': True,
      'missing_confidence_default': 0.5,
      'missing_recency_default': 0.7,
      'missing_importance_default': 0.5,
      'minimum_compound_score': 0.2,
      'low_score_threshold': 0.4,
      'include_scores_in_prompt': True,
      'score_presentation': 'detailed'
    })


class ClassInputOutput:
  """Handle input validation and output saving"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger
    self.processing_settings = config.get_processing_settings()
    self.output_structure = config.get_output_structure()
    self.filename_templates = config.get_filename_templates()

  def load_claim_file (self, file_path: Path) -> Optional[Dict]:
    """Load and validate claim JSON file"""
    try:
      with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

      # Basic validation
      if 'claim_id' not in data:
        self.logger.error(f"Missing claim_id in {file_path.name}")
        return None

      if 'encounters' not in data or not data['encounters']:
        self.logger.error(f"No encounters found in {file_path.name}")
        return None

      return data

    except json.JSONDecodeError as e:
      self.logger.error(f"Invalid JSON in {file_path.name}: {e}")
      return None
    except Exception as e:
      self.logger.error(f"Error loading {file_path.name}: {e}")
      return None

  def save_stage1_output (self, claim_id: str, patient_initials: str,
                          stage1_features: List[ClassOutputStage1],
                          output_dir: Path) -> bool:
    """Save Stage 1 features to JSON"""
    try:
      # Create output directory
      stage1_dir = output_dir / self.output_structure.get('feature_extraction', 'stage1_features')
      stage1_dir.mkdir(parents=True, exist_ok=True)

      # Build filename
      template = self.filename_templates.get('feature_extraction',
                                             'stage1_{patient_initials}_{claim_id}_features.json')
      filename = template.format(claim_id=claim_id, patient_initials=patient_initials)
      output_file = stage1_dir / filename

      # Convert to dict
      output_data = {
        'claim_id': claim_id,
        'stage1_features': [f.to_dict() for f in stage1_features],
        'processing_metadata': {
          'timestamp': datetime.now().isoformat(),
          'documents_processed': len(stage1_features),
          'stage': 'stage1_feature_extraction'
        }
      }

      # Save
      with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

      self.logger.debug(f"💾 Saved Stage 1 output: {output_file}")
      return True

    except Exception as e:
      self.logger.error(f"Error saving Stage 1 output: {e}")
      return False

  def save_stage2_output (self, analysis: ClassOutputStage2, patient_initials: str,
                          output_dir: Path) -> bool:
    """Save Stage 2 final analysis to JSON"""
    try:
      # Create output directory
      stage2_dir = output_dir / self.output_structure.get('final_analysis', 'stage2_final_analysis')
      stage2_dir.mkdir(parents=True, exist_ok=True)

      # Build filename
      template = self.filename_templates.get('final_analysis',
                                             'stage2_{patient_initials}_{claim_id}_final_analysis.json')
      filename = template.format(claim_id=analysis.claim_id, patient_initials=patient_initials)
      output_file = stage2_dir / filename

      # Convert to dict
      output_data = analysis.to_dict()

      # Save
      with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

      self.logger.debug(f"Saved Stage 2 output: {output_file}")
      return True

    except Exception as e:
      self.logger.error(f"Error saving Stage 2 output: {e}")
      return False


class ClassOrchestrator:
  """
  Main orchestration class for LLM claims analysis

  Integrates all components:
  - Stage 1 Processor (document-specific extraction)
  - Stage 2 Processor (cross-document aggregation)
  - Cloud storage (optional)
  - Metrics tracking
  - Input/output handling
  """

  def __init__ (self, config_path: Optional[str] = None):
    # Initialize infrastructure
    self.config = ClassConfig(config_path)
    self.logger = ClassLogger(self.config)

    self.metrics = ClassTrackMetrics(self.logger)
    self.api_client = ClassAPIClient(self.config, self.logger)
    self.cloud_client = ClassCloudStorage(self.config, self.logger)

    # Initialize processors
    self.stage1_processor = ClassProcessStage1(
      self.config, self.logger, self.api_client, self.metrics
    )
    self.stage2_processor = ClassProcessStage2(
      self.config, self.logger, self.api_client, self.metrics
    )

    # Initialize I/O handler
    self.io_handler = ClassInputOutput(self.config, self.logger)

    # Settings
    self.processing_settings = self.config.get_processing_settings()
    self.stage1_settings = self.config.get_stage1_settings()
    self.stage2_settings = self.config.get_stage2_settings()
    self.cloud_settings = self.config.get_cloud_storage_settings()

    self.logger.success("Claims Analyzer initialized successfully")

  def process_claim_pipeline (self, claim_file: Path, output_dir: Path,
                              skip_cloud: bool = False) -> Dict:
    """
    Process a single claim through the complete pipeline

    Pipeline: Load → Stage 1 → (Save/Upload) → Stage 2 → (Save/Upload)

    Returns:
        Dict with processing results and metadata
    """
    start_time = perf_counter()
    claim_id = claim_file.stem.split('_')[1] if '_' in claim_file.stem else claim_file.stem

    cost_before = self.metrics.stats['total_cost']

    self.logger.info(f"🔄 PROCESSING CLAIM ID: {claim_id}")

    result = {
      'claim_id': claim_id,
      'file': str(claim_file),
      'success': False,
      'stage1_success': False,
      'stage2_success': False,
      'stage1_documents': 0,
      'stage1_output': None,
      'stage2_output': None,
      'errors': [],
      'processing_time': 0.0,
      'cost': 0.0
    }

    try:
      # Load claim data
      self.logger.info("📂 Loading claim data...")
      claim_data = self.io_handler.load_claim_file(claim_file)

      if not claim_data:
        error_msg = f"Failed to load claim file: {claim_file.name}"
        self.logger.error(error_msg)
        result['errors'].append(error_msg)
        result['processing_time'] = perf_counter() - start_time
        return result

      claim_id = claim_data.get('claim_id', claim_id)
      result['claim_id'] = claim_id

      # Check if Stage 1 is enabled
      if not self.stage1_settings.get('enabled', True):
        self.logger.warning("Stage 1 disabled in configuration")
        result['errors'].append("Stage 1 disabled")
        return result

      # STAGE 1: Document-specific feature extraction
      self.logger.info("📊 STAGE 1: Document-Specific Feature Extraction")

      stage1_start = perf_counter()
      stage1_features = self.stage1_processor.stage1_process_all_documents(claim_data)
      stage1_duration = perf_counter() - stage1_start

      if not stage1_features:
        error_msg = "Stage 1 processing failed - no features extracted"
        self.logger.error(error_msg)
        result['errors'].append(error_msg)
        result['processing_time'] = perf_counter() - start_time
        # CALCULATE COST: Even if failed, capture what was spent
        result['cost'] = self.metrics.stats['total_cost'] - cost_before
        return result

      result['stage1_success'] = True
      result['stage1_documents'] = len(stage1_features)
      self.logger.success("-" * 60)
      self.logger.success(
        f" Stage 1 complete: {len(stage1_features)} documents processed in {stage1_duration:.2f}s")

      # Save Stage 1 output
      patient_initials = claim_data.get('patient_initials', 'XX')
      stage1_saved = self.io_handler.save_stage1_output(
        claim_id=claim_id,
        patient_initials=patient_initials,
        stage1_features=stage1_features,
        output_dir=output_dir
      )

      if stage1_saved:
        self.logger.success(" Stage 1 output saved locally")

      # Upload Stage 1 to cloud if enabled
      if self.cloud_client.client and not skip_cloud:
        self.logger.info("☁️  Uploading Stage 1 features to cloud...")
        cloud_path = f"{self.cloud_settings.get('stage1_output_path', 'stage1/')}{claim_id}_stage1.json"
        stage1_data = {
          'claim_id': claim_id,
          'stage1_features': [f.to_dict() for f in stage1_features]
        }
        if self.cloud_client.upload_json(stage1_data, cloud_path):
          self.logger.success("Stage 1 features uploaded to cloud")

      # Check if Stage 2 is enabled
      if not self.stage2_settings.get('enabled', True):
        self.logger.warning("Stage 2 disabled in configuration")
        result['success'] = True  # Stage 1 completed
        result['processing_time'] = perf_counter() - start_time
        result['cost'] = self.metrics.stats['total_cost'] - cost_before
        return result

      # STAGE 2: Cross-document aggregation
      self.logger.info("=" * 60)
      self.logger.info("🔬 STAGE 2: Cross-Document Aggregation")

      stage2_start = perf_counter()
      final_analysis = self.stage2_processor.stage2_process_all_features(
        claim_id=claim_id,
        stage1_features=stage1_features
      )
      stage2_duration = perf_counter() - stage2_start

      if not final_analysis:
        error_msg = "Stage 2 aggregation failed"
        self.logger.error(error_msg)
        result['errors'].append(error_msg)
        result['success'] = True  # Stage 1 completed
        result['processing_time'] = perf_counter() - start_time
        result['cost'] = self.metrics.stats['total_cost'] - cost_before
        return result

      result['stage2_success'] = True
      result['stage2_output'] = final_analysis.claim_id
      self.logger.success(f"Stage 2 complete: Final analysis generated in {stage2_duration:.2f}s")

      # Save Stage 2 output
      self.logger.info("💾 Saving Stage 2 final analysis...")
      patient_initials = claim_data.get('patient_initials', 'XX')
      stage2_saved = self.io_handler.save_stage2_output(
        analysis=final_analysis,
        patient_initials=patient_initials,
        output_dir=output_dir
      )

      if stage2_saved:
        self.logger.success("Stage 2 output saved locally")

      # Upload Stage 2 to cloud if enabled
      if self.cloud_client.client and not skip_cloud:
        self.logger.info("☁️  Uploading Stage 2 analysis to cloud...")
        cloud_path = f"{self.cloud_settings.get('stage2_output_path', 'stage2/')}{claim_id}_stage2.json"
        if self.cloud_client.upload_json(final_analysis.to_dict(), cloud_path):
          self.logger.success("Stage 2 analysis uploaded to cloud")

      # Mark as successful
      result['success'] = True
      result['processing_time'] = perf_counter() - start_time

      # Calculate total cost for this claim
      result['cost'] = self.metrics.stats['total_cost'] - cost_before

      self.logger.info("-" * 60)
      self.logger.success(f"✅ CLAIM PROCESSING COMPLETE: {claim_id}")
      self.logger.info(f"⏱️ Total time: {result['processing_time']:.2f}s")
      self.logger.info(f"💰 Total cost: ${result['cost']:.4f}")

      # Update metrics
      self.metrics.stats['files_processed'] += 1
      self.metrics.stats['files_successful'] += 1
      self.metrics.stats['claims_processed'] += 1

      return result

    except Exception as e:
      error_msg = f"Pipeline error: {e}"
      self.logger.error(error_msg)
      self.logger.error(traceback.format_exc())
      result['errors'].append(error_msg)
      result['processing_time'] = perf_counter() - start_time
      result['cost'] = self.metrics.stats['total_cost'] - cost_before

      self.metrics.stats['files_processed'] += 1
      self.metrics.stats['files_failed'] += 1

      return result

  def process_batch (self, input_dir: Path, output_dir: Path,
                     limit: Optional[int] = None, skip_cloud: bool = False) -> Dict:
    """
    Process a batch of claim files

    Args:
        input_dir: Directory containing claim JSON files
        output_dir: Output directory for results
        limit: Optional limit on number of files to process
        skip_cloud: Skip cloud upload even if enabled

    Returns:
        Dict with batch processing results
    """
    self.logger.info("=" * 60)
    self.logger.info("📦 BATCH PROCESSING STARTED")
    self.logger.info(f"📂 Input directory: {input_dir}")
    self.logger.info(f"📁 Output directory: {output_dir}")
    if limit:
      self.logger.info(f"🔢 Limit: {limit} files")

    # Find all JSON files
    json_files = sorted(input_dir.glob("*.json"))

    if not json_files:
      self.logger.error(f"No JSON files found in {input_dir}")
      return {
        'success': False,
        'error': 'No input files found',
        'files_processed': 0
      }

    # Apply limit if specified
    if limit:
      json_files = json_files[:limit]

    self.logger.info(f"📊 Found {len(json_files)} files to process")

    # Process each file
    batch_results = []
    batch_start = perf_counter()

    for i, claim_file in enumerate(json_files, 1):
      self.logger.info(f"")
      self.logger.info(f"{'=' * 60}")
      self.logger.info(f"FILE {i}/{len(json_files)}: {claim_file.name}")

      result = self.process_claim_pipeline(
        claim_file=claim_file,
        output_dir=output_dir,
        skip_cloud=skip_cloud
      )

      batch_results.append(result)

    batch_duration = perf_counter() - batch_start

    # Generate batch summary
    summary = self._generate_batch_summary(batch_results, batch_duration)

    # Save batch report
    self._save_batch_report(summary, output_dir)

    # Print comprehensive summary
    self._print_consolidated_summary(summary, batch_start)

    return summary

  def _generate_batch_summary (self, batch_results: List[Dict], duration: float) -> Dict:
    """Generate comprehensive batch processing summary"""

    successful = sum(1 for r in batch_results if r['success'])
    stage1_success = sum(1 for r in batch_results if r['stage1_success'])
    stage2_success = sum(1 for r in batch_results if r['stage2_success'])

    total_documents = sum(r['stage1_documents'] for r in batch_results)
    total_cost = sum(r.get('cost', 0.0) for r in batch_results)

    return {
      'batch_summary': {
        'total_files': len(batch_results),
        'successful': successful,
        'failed': len(batch_results) - successful,
        'stage1_success': stage1_success,
        'stage2_success': stage2_success,
        'total_documents_processed': total_documents,
        'total_processing_time': duration,
        'total_cost': self.metrics.stats['total_cost'],
        'timestamp': datetime.now().isoformat()
      },
      'detailed_statistics': {
        'stage1_stats': {
          'documents_processed': self.metrics.stats['stage1_documents_processed'],
          'successful': self.metrics.stats['stage1_documents_successful'],
          'failed': self.metrics.stats['stage1_documents_failed'],
          'cost': self.metrics.stats['cost_by_stage']['stage1']
        },
        'stage2_stats': {
          'aggregations_processed': self.metrics.stats['stage2_aggregations_processed'],
          'successful': self.metrics.stats['stage2_aggregations_successful'],
          'failed': self.metrics.stats['stage2_aggregations_failed'],
          'cost': self.metrics.stats['cost_by_stage']['stage2']
        },
        'cost_breakdown': self.metrics.stats['cost_by_document_type'],
        'token_breakdown': self.metrics.stats['token_usage'],
        'success_rates': self.metrics.stats['generation_success_rates'],
        'method_performance': self.metrics.stats['method_usage']
      },
      'claim_details': [
        {
          'claim_id': r['claim_id'],
          'file': r['file'],
          'success': r['success'],
          'stage1_documents': r['stage1_documents'],
          'processing_time': r['processing_time'],
          'cost': r.get('cost', 0.0),
          'errors': r.get('errors', [])
        }
        for r in batch_results
      ],
      'processing_metadata': {
        'config_file': str(self.config.config_path),
        'total_api_calls': (
          self.metrics.stats['stage1_documents_processed'] +
          self.metrics.stats['stage2_aggregations_processed']
        ),
        'cloud_enabled': self.cloud_client.client is not None
      }
    }

  def _save_batch_report (self, summary: Dict, output_dir: Path):
    """Save batch processing report to JSON"""
    try:
      # Create reports directory
      reports_dir = output_dir / self.config.get_output_structure().get('reports', 'reports')
      reports_dir.mkdir(parents=True, exist_ok=True)

      # Generate filename with timestamp
      timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
      report_file = reports_dir / f"4_analysis-analyze_claims-report_{timestamp}.json"

      # Save report
      with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

      self.logger.success(f"Batch report saved: {report_file}")

    except Exception as e:
      self.logger.error(f"Failed to save batch report: {e}")

  def _print_consolidated_summary (self, summary: Dict, start_time: float) -> None:
    """
    Print single consolidated summary replacing all separate summaries.
    Includes: batch stats, stage breakdown, document breakdown, performance metrics.

    Enhanced to show:
    - Token format: total (input → output)
    - Average cost and time per claim
    - Processing stage breakdown with tokens and metrics
    """
    elapsed_time = summary['batch_summary']['total_processing_time']

    stats = summary['detailed_statistics']
    batch = summary['batch_summary']

    # Get token data from metrics tracker (the actual source)
    token_usage = self.metrics.stats.get('token_usage', {})

    # Calculate rates
    claims_per_min = (batch['successful'] / elapsed_time * 60) if elapsed_time > 0 else 0
    cost_per_claim = batch['total_cost'] / batch['successful'] if batch['successful'] > 0 else 0
    time_per_claim = elapsed_time / batch['successful'] if batch['successful'] > 0 else 0

    total_tokens = token_usage.get('total_usage', 0)
    tokens_per_dollar = total_tokens / batch['total_cost'] if batch['total_cost'] > 0 else 0

    self.logger.info("=" * 60)
    self.logger.info("📊 PROCESSING COMPLETE")

    # Success summary
    success_rate = (batch['successful'] / batch['total_files'] * 100) if batch[
                                                                           'total_files'] > 0 else 0
    self.logger.info(
      f"✅ Success: {batch['successful']}/{batch['total_files']} claims ({success_rate:.0f}%)")
    self.logger.info(f"📄 Documents: {batch['total_documents_processed']} processed")
    self.logger.info(f"⏱️  Time: {elapsed_time:.1f}s")
    self.logger.info(f"💰 Cost: ${batch['total_cost']:.4f}")

    # Overall token summary with new format: total (input → output)
    total_tokens_input = token_usage.get('total_input', 0)
    total_tokens_output = token_usage.get('total_output', 0)
    total_tokens = token_usage.get('total_usage', 0)

    self.logger.info(
      f"🎯 Tokens: {total_tokens:,} ({total_tokens_input:,} → {total_tokens_output:,})")

    # By Document Type section
    self.logger.info("─" * 60)
    self.logger.info("📈 By Document Type:")

    # Get document type data
    # cost_by_document_type is {doc_type: float_cost}
    cost_breakdown = self.metrics.stats.get('cost_by_document_type', {})
    token_by_doc = token_usage.get('by_document_type', {})
    success_rates = self.metrics.stats.get('generation_success_rates', {}).get('stage1', {})

    doc_types = []

    for doc_type in cost_breakdown.keys():
      cost = cost_breakdown.get(doc_type, 0.0)

      # Get tokens for this document type
      tokens_data = token_by_doc.get(doc_type, {})
      tokens_in = tokens_data.get('input', 0)
      tokens_out = tokens_data.get('output', 0)
      tokens_total = tokens_in + tokens_out

      # Get success rate from generation_success_rates
      rates = success_rates.get(doc_type, {})
      processed = rates.get('attempted', 0)
      successful = rates.get('successful', 0)
      success_rate = (successful / processed * 100) if processed > 0 else 0

      # Get document type display name
      doc_type_names = {
        'settlement_adjuster_notes': 'Settlement Adjuster Notes',
        'adjuster_notes_initial': 'Adjuster Notes Initial',
        'medical_provider_letter': 'Medical Provider Letter',
        'phone_transcript': 'Phone Transcript',
        'claimant_statement': 'Claimant Statement',
        'clinical_note': 'Clinical Note'
      }
      display_name = doc_type_names.get(doc_type, doc_type.replace('_', ' ').title())

      doc_types.append({
        'name': display_name,
        'cost': cost,
        'tokens_total': tokens_total,
        'tokens_in': tokens_in,
        'tokens_out': tokens_out,
        'successful': successful,
        'processed': processed,
        'success_rate': success_rate
      })

    # Sort by cost descending
    doc_types.sort(key=lambda x: x['cost'], reverse=True)

    # Print each document type with new format
    for doc in doc_types:
      # Format: Name  $cost | tokens (input → output) | success/total (%)
      self.logger.info(
        f"  {doc['name']:<26} ${doc['cost']:.4f} | "
        f"{doc['tokens_total']:,} ({doc['tokens_in']:,} → {doc['tokens_out']:,}) | "
        f"{doc['successful']}/{doc['processed']} ({doc['success_rate']:.0f}%)"
      )

    # Processing Stages section with new breakdown
    self.logger.info("─" * 60)
    self.logger.info("📊 Processing Stages:")

    # Stage 1 breakdown
    stage1_by_stage = token_usage.get('by_stage', {}).get('stage1', {})
    stage1_tokens_in = stage1_by_stage.get('input', 0)
    stage1_tokens_out = stage1_by_stage.get('output', 0)
    stage1_tokens_total = stage1_by_stage.get('total', stage1_tokens_in + stage1_tokens_out)
    stage1_cost = stats['stage1_stats']['cost']

    # Get stage 1 time from processing times
    stage1_times = self.metrics.stats.get('stage_processing_times', {}).get('stage1', [])
    stage1_time = sum(stage1_times) if stage1_times else 0.0

    self.logger.info(
      f"Stage 1: {stage1_tokens_total:,} ({stage1_tokens_in:,} → {stage1_tokens_out:,}) | Cost: ${stage1_cost:.4f}, Time: {stage1_time:.1f}s")

    # Stage 2 breakdown
    stage2_by_stage = token_usage.get('by_stage', {}).get('stage2', {})
    stage2_tokens_in = stage2_by_stage.get('input', 0)
    stage2_tokens_out = stage2_by_stage.get('output', 0)
    stage2_tokens_total = stage2_by_stage.get('total', stage2_tokens_in + stage2_tokens_out)
    stage2_cost = stats['stage2_stats']['cost']

    # Get stage 2 time from processing times
    stage2_times = self.metrics.stats.get('stage_processing_times', {}).get('stage2', [])
    stage2_time = sum(stage2_times) if stage2_times else 0.0

    self.logger.info(
      f"Stage 2: {stage2_tokens_total:,} ({stage2_tokens_in:,} → {stage2_tokens_out:,}) | Cost: ${stage2_cost:.4f}, Time: {stage2_time:.1f}s")

    # Performance metrics section (enhanced)
    self.logger.info("─" * 60)

    # Check provider for display
    api_settings = self.config.get_api_settings()
    provider_name = api_settings.get('provider', 'openai')

    self.logger.info(f"🎯 Performance: {claims_per_min:.1f} claims/min")
    if provider_name == 'ollama' or batch['total_cost'] == 0:
      self.logger.info(f"   PREE (Local Ollama)")
    else:
      self.logger.info(f"   Tokens/dollar: {tokens_per_dollar / 1e6: .1f}")
      self.logger.info(f"   Avg cost/claim: ${cost_per_claim:.4f}")
    self.logger.info(f"   Avg time/claim: {time_per_claim:.1f}s")


class ClassProcessRunMode:
  """Handle different processing modes (stage1, stage2, pipeline)"""

  def __init__ (self, analyzer: ClassOrchestrator):
    self.analyzer = analyzer
    self.logger = analyzer.logger

  def process_stage1_only (self, input_dir: Path, output_dir: Path,
                           limit: Optional[int] = None) -> bool:
    """Process only Stage 1 (feature extraction) for all claims"""
    self.logger.info("🔍 MODE: Stage 1 Only (Feature Extraction)")

    # Find input files
    json_files = sorted(input_dir.glob("*.json"))
    if limit:
      json_files = json_files[:limit]

    if not json_files:
      self.logger.error(f"No JSON files found in {input_dir}")
      return False

    self.logger.info(f"Processing {len(json_files)} files (Stage 1 only)")

    success_count = 0

    for i, claim_file in enumerate(json_files, 1):
      self.logger.info(f"\n[{i}/{len(json_files)}] Processing {claim_file.name}")

      # Load claim
      claim_data = self.analyzer.io_handler.load_claim_file(claim_file)
      if not claim_data:
        continue

      claim_id = claim_data.get('claim_id', claim_file.stem)

      # Process Stage 1
      stage1_features = self.analyzer.stage1_processor.stage1_process_all_documents(claim_data)

      if stage1_features:
        # Save output
        self.analyzer.io_handler.save_stage1_output(claim_id, stage1_features, output_dir)
        success_count += 1
        self.logger.success(f"Stage 1 complete for {claim_id}")

    self.logger.info(f"\nStage 1 processing complete: {success_count}/{len(json_files)} successful")
    return success_count > 0

  def process_stage2_only (self, input_dir: Path, output_dir: Path,
                           limit: Optional[int] = None) -> bool:
    """Process only Stage 2 (aggregation) using existing Stage 1 outputs"""
    self.logger.info("🔬 MODE: Stage 2 Only (Aggregation)")

    # Find Stage 1 output files
    stage1_dir = input_dir / self.analyzer.config.get_output_structure().get('feature_extraction',
                                                                             'stage1_features')

    if not stage1_dir.exists():
      self.logger.error(f"Stage 1 output directory not found: {stage1_dir}")
      self.logger.info("Run Stage 1 first or use pipeline mode")
      return False

    stage1_files = sorted(stage1_dir.glob("*stage1*.json"))
    if limit:
      stage1_files = stage1_files[:limit]

    if not stage1_files:
      self.logger.error(f"No Stage 1 output files found in {stage1_dir}")
      return False

    self.logger.info(f"Processing {len(stage1_files)} Stage 1 outputs (Stage 2 aggregation)")

    success_count = 0

    for i, stage1_file in enumerate(stage1_files, 1):
      self.logger.info(f"\n[{i}/{len(stage1_files)}] Aggregating {stage1_file.name}")

      # Load Stage 1 features
      try:
        with open(stage1_file, 'r', encoding='utf-8') as f:
          stage1_data = json.load(f)

        claim_id = stage1_data.get('claim_id')
        features_dicts = stage1_data.get('stage1_features', [])

        # Convert to Stage1DocumentFeatures objects
        stage1_features = [
          ClassOutputStage1(**feat) for feat in features_dicts
        ]

        # Process Stage 2
        final_analysis = self.analyzer.stage2_processor.stage2_process_all_features(claim_id, stage1_features)

        if final_analysis:
          # Save output
          self.analyzer.io_handler.save_stage2_output(final_analysis, output_dir)
          success_count += 1
          self.logger.success(f"Stage 2 complete for {claim_id}")

      except Exception as e:
        self.logger.error(f"Error processing {stage1_file.name}: {e}")
        continue

    self.logger.info(
      f"\nStage 2 processing complete: {success_count}/{len(stage1_files)} successful")
    return success_count > 0


def setup_argument_parser () -> argparse.ArgumentParser:
  """Setup comprehensive command line argument parser"""

  parser = argparse.ArgumentParser(
    description="LLM Claims Analysis with Two-Stage Processing",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Processing Modes:
  pipeline    - Full pipeline: Stage 1 → Stage 2 (default)
  stage1      - Stage 1 only: Document-specific feature extraction
  stage2      - Stage 2 only: Aggregate existing Stage 1 outputs

Examples:
  # Full pipeline processing with defaults from config
  python 4_analysis-analyze_claims.py --mode pipeline

  # Process specific input directory
  python 4_analysis-analyze_claims.py --mode pipeline --input-dir ./data/claims

  # Process with custom output and limit
  python 4_analysis-analyze_claims.py --mode pipeline --output-dir ./results --limit 10

  # Stage 1 only (feature extraction)
  python 4_analysis-analyze_claims.py --mode stage1 --input-dir ./data

  # Stage 2 only (requires existing Stage 1 outputs)
  python 4_analysis-analyze_claims.py --mode stage2 --input-dir ./output

  # Dry run to validate configuration
  python 4_analysis-analyze_claims.py --dry-run

  # Verbose debug logging
  python 4_analysis-analyze_claims.py --mode pipeline --verbose

  # Skip cloud upload even if configured
  python 4_analysis-analyze_claims.py --mode pipeline --skip-cloud

Configuration:
  Default paths are loaded from config/4_analysis-analyze_claims.yaml
  CLI arguments override config file settings
  Use --config to specify a custom configuration file
        """
  )

  # Processing mode
  parser.add_argument(
    "--mode",
    type=str,
    choices=['pipeline', 'stage1', 'stage2'],
    default='pipeline',
    help="Processing mode (default: pipeline)"
  )

  # Input/Output directories
  parser.add_argument(
    "--input-dir",
    type=str,
    help="Input directory containing claim JSON files (overrides config)"
  )

  parser.add_argument(
    "--output-dir",
    type=str,
    help="Output directory for results (overrides config)"
  )

  # Configuration
  parser.add_argument(
    "--config",
    type=str,
    help="Path to configuration YAML file (default: config/4_analysis-analyze_claims.yaml)"
  )

  # Processing options
  parser.add_argument(
    "--limit",
    type=int,
    help="Limit number of files to process"
  )

  parser.add_argument(
    "--skip-cloud",
    action="store_true",
    help="Skip cloud upload even if cloud storage is configured"
  )

  # Logging options
  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Enable verbose debug logging"
  )

  # Testing options
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Validate configuration and inputs without processing"
  )

  parser.add_argument(
    "--json-output",
    action="store_true",
    help="Output structured JSON events for progress tracking"
  )

  return parser


def validate_arguments (args, config: ClassConfig) -> Tuple[bool, str]:
  """
  Validate command line arguments

  Returns:
      (is_valid, error_message)
  """

  # Get directories from args or config
  processing_settings = config.get_processing_settings()

  input_dir = args.input_dir if args.input_dir else processing_settings.get('default_input_dir')
  output_dir = args.output_dir if args.output_dir else processing_settings.get('default_output_dir')

  if not input_dir:
    return False, "Input directory not specified (use --input-dir or set in config)"

  if not output_dir:
    return False, "Output directory not specified (use --output-dir or set in config)"

  # Convert to Path objects
  script_dir = Path(__file__).parent.resolve()

  input_path = Path(input_dir)
  if not input_path.is_absolute():
    input_path = script_dir / input_dir

  # Validate input directory exists (except for dry-run)
  if not args.dry_run and not input_path.exists():
    return False, f"Input directory does not exist: {input_path}"

  if not args.dry_run and not input_path.is_dir():
    return False, f"Input path is not a directory: {input_path}"

  # Validate limit
  if args.limit and args.limit < 1:
    return False, "--limit must be a positive integer"

  # Mode-specific validation
  if args.mode == 'stage2':
    # Check for Stage 1 output directory
    output_structure = config.get_output_structure()
    stage1_dir = input_path / output_structure.get('feature_extraction', 'stage1_features')

    if not args.dry_run and not stage1_dir.exists():
      return False, f"Stage 2 mode requires existing Stage 1 outputs at: {stage1_dir}"

  return True, "Validation passed"


def get_directories (args, config: ClassConfig) -> Tuple[Path, Path]:
  """
  Get input and output directories from args or config

  Returns:
      (input_path, output_path)
  """
  script_dir = Path(__file__).parent.resolve()
  processing_settings = config.get_processing_settings()

  # Get input directory
  if args.input_dir:
    input_dir = args.input_dir
  else:
    input_dir = processing_settings.get('default_input_dir', 'output/2_data-add_documents')

  input_path = Path(input_dir)
  if not input_path.is_absolute():
    input_path = script_dir / input_dir

  # Get output directory
  if args.output_dir:
    output_dir = args.output_dir
  else:
    output_dir = processing_settings.get('default_output_dir', 'output/4_analysis-analyze_claims')

  output_path = Path(output_dir)
  if not output_path.is_absolute():
    output_path = script_dir / output_dir

  # Create output directory
  output_path.mkdir(parents=True, exist_ok=True)

  return input_path, output_path


def print_startup_banner ():
  """Print startup banner with version info"""
  print("\n" + "=" * 60, file=sys.stderr)
  print("🚀 LLM Claims Analysis - Script 4", file=sys.stderr)
  print("📊 Two-Stage Processing Pipeline with Modern Infrastructure", file=sys.stderr)
  print("📝 Stage 1: Document-Specific Feature Extraction", file=sys.stderr)
  print("🔬 Stage 2: Cross-Document Aggregation", file=sys.stderr)
  print("💰 Includes cost tracking, retry logic, and rationale system", file=sys.stderr)
  print("☁️  Optional cloud storage integration", file=sys.stderr)
  print("🔗 Compatible with Scripts 1, 2, and 3 outputs", file=sys.stderr)


def print_completion_banner (success: bool, start_time: float):
  """Print completion banner with timing"""
  elapsed_time = time.time() - start_time
  print("\n" + "=" * 60, file=sys.stderr)

  if success:
    print("✅ PROCESSING COMPLETED SUCCESSFULLY", file=sys.stderr)
  else:
    print("⚠️  PROCESSING COMPLETED WITH ERRORS", file=sys.stderr)

  print("=" * 60, file=sys.stderr)
  print(f"⏱️  Total elapsed time: {elapsed_time:.2f} seconds", file=sys.stderr)
  print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)


def print_dry_run_summary (config: ClassConfig, input_path: Path, output_path: Path):
  """Print dry run validation summary"""
  print("\n" + "=" * 60, file=sys.stderr)
  print("🧪 DRY RUN MODE - Configuration Validation", file=sys.stderr)

  # Configuration
  print(f"\n📋 Configuration:", file=sys.stderr)
  print(f"  Config file: {config.config_path}", file=sys.stderr)

  api_settings = config.get_api_settings()
  print(f"  Stage 1 model: {api_settings.get('stage1_model', 'N/A')}", file=sys.stderr)
  print(f"  Stage 2 model: {api_settings.get('stage2_model', 'N/A')}", file=sys.stderr)

  # Rationale system
  rationale = config.get_rationale_settings()
  print(f"\n🔍 Rationale System:", file=sys.stderr)
  print(f"  Enabled: {rationale.get('enabled', False)}", file=sys.stderr)
  print(f"  Mode: {rationale.get('mode', 'N/A')}", file=sys.stderr)

  if rationale.get('mode') == 'selective':
    fields = rationale.get('selective_fields', [])
    print(f"  Selective fields: {', '.join(fields) if fields else 'None'}", file=sys.stderr)

  # Directories
  print(f"\n📁 Directories:", file=sys.stderr)
  print(f"  Input: {input_path}", file=sys.stderr)
  print(f"  Output: {output_path}", file=sys.stderr)
  print(f"  Input exists: {'✅ Yes' if input_path.exists() else '❌ No'}", file=sys.stderr)

  # Cloud storage
  cloud = config.get_cloud_storage_settings()
  print(f"\n☁️  Cloud Storage:", file=sys.stderr)

  print(f"  Enabled: {cloud.get('enabled', False)}", file=sys.stderr)

  if cloud.get('enabled'):
    print(f"  Project: {cloud.get('project_id', 'N/A')}", file=sys.stderr)

    print(f"  Bucket: {cloud.get('bucket_name', 'N/A')}", file=sys.stderr)

  # Document types
  doc_types = config.get_document_types()
  print(f"\n📄 Document Types Configured: {len(doc_types)}", file=sys.stderr)

  for dtype in doc_types.keys():
    print(f"  - {dtype}", file=sys.stderr)
  print("\n" + "=" * 60, file=sys.stderr)
  print("✅ Configuration validation complete", file=sys.stderr)
  print("ðŸ’¡ Remove --dry-run to start processing", file=sys.stderr)


def main ():
  """Main application entry point"""

  start_time = time.time()

  try:
    # Print startup banner
    print_startup_banner()

    # Parse arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Load configuration
    try:
      config = ClassConfig(args.config)
    except SystemExit:
      return EXIT_CONFIG_ERROR
    except Exception as e:
      print(f"❌ Configuration error: {e}", file=sys.stderr)
      return EXIT_CONFIG_ERROR

    # Validate arguments
    print("🔍 Validating arguments...", file=sys.stderr)

    is_valid, error_msg = validate_arguments(args, config)
    if not is_valid:
      print(f"❌ Validation error: {error_msg}", file=sys.stderr)
      parser.print_help()
      return EXIT_VALIDATION_ERROR
    print("✅ Arguments validated successfully", file=sys.stderr)

    # Get directories
    input_path, output_path = get_directories(args, config)
    print(f"📂 Input directory: {input_path}", file=sys.stderr)
    print(f"📁 Output directory: {output_path}", file=sys.stderr)

    # Dry run mode
    if args.dry_run:
      print_dry_run_summary(config, input_path, output_path)
      return EXIT_SUCCESS

    # Initialize Claims Analyzer
    print("\n🔨 Initializing Claims Analyzer...", file=sys.stderr)

    try:
      analyzer = ClassOrchestrator(config_path=args.config)

      # Enable JSON output mode if requested
      if args.json_output:
        analyzer.set_json_mode(True)
        print("📊 JSON output mode enabled", file=sys.stderr)

      # Override logging if verbose
      if args.verbose:
        analyzer.logger.logger.setLevel(logging.DEBUG)
        analyzer.logger.info("🔊 Verbose logging enabled")

      print("✅ Claims Analyzer initialized", file=sys.stderr)

    except Exception as e:
      print(f"❌ Initialization error: {e}", file=sys.stderr)

      traceback.print_exc()
      return EXIT_PROCESSING_ERROR

    # Process based on mode
    print(f"\n🎯 Processing mode: {args.mode.upper()}", file=sys.stderr)

    try:
      if args.mode == 'pipeline':
        # Full pipeline processing
        analyzer.logger.info("Starting full pipeline processing...")
        summary = analyzer.process_batch(
          input_dir=input_path,
          output_dir=output_path,
          limit=args.limit,
          skip_cloud=args.skip_cloud
        )
        success = summary['batch_summary']['successful'] > 0

      elif args.mode == 'stage1':
        # Stage 1 only processing
        mode_processor = ClassProcessRunMode(analyzer)
        success = mode_processor.process_stage1_only(
          input_dir=input_path,
          output_dir=output_path,
          limit=args.limit
        )

        # Print metrics
        analyzer.metrics.print_comprehensive_summary()

      elif args.mode == 'stage2':
        # Stage 2 only processing
        mode_processor = ClassProcessRunMode(analyzer)
        success = mode_processor.process_stage2_only(
          input_dir=input_path,
          output_dir=output_path,
          limit=args.limit
        )

        # Print metrics
        analyzer.metrics.print_comprehensive_summary()

      else:
        print(f"❌ Unknown mode: {args.mode}", file=sys.stderr)

        return EXIT_VALIDATION_ERROR

      # Print completion banner
      print_completion_banner(success, start_time)

      return EXIT_SUCCESS if success else EXIT_PROCESSING_ERROR

    except KeyboardInterrupt:
      print("\n⚠️  Processing interrupted by user", file=sys.stderr)

      analyzer.logger.warning("Processing interrupted by user")
      return EXIT_SUCCESS

    except Exception as e:
      print(f"\n❌ Processing error: {e}", file=sys.stderr)

      traceback.print_exc()
      return EXIT_PROCESSING_ERROR

  except KeyboardInterrupt:
    print("\n⚠️  Startup interrupted by user", file=sys.stderr)

    return EXIT_SUCCESS

  except Exception as e:
    print(f"\n❌ Fatal error: {e}", file=sys.stderr)

    traceback.print_exc()
    return EXIT_PROCESSING_ERROR


def verify_stage2_rationale_in_output (self, stage2_output: Dict) -> bool:
  """
  Debug method to verify rationale fields are present in Stage 2 output

  Args:
      stage2_output: The Stage2FinalAnalysis.to_dict() output

  Returns:
      True if rationale fields found, False otherwise
  """
  rationale_config = self.config.get_rationale_settings()

  if not rationale_config.get('enabled', False):
    self.logger.debug("Rationale system is disabled")
    return True  # Not an error if disabled

  actuarial_vars = stage2_output.get('actuarial_variables', {})
  rationale_found = False

  # Check for rationale in actuarial variables
  for category_name, category_value in actuarial_vars.items():
    if isinstance(category_value, dict):
      for var_name, var_value in category_value.items():
        if isinstance(var_value, dict) and 'rationale' in var_value:
          rationale_found = True
          self.logger.debug(f"Found rationale in {category_name}.{var_name}")
          break
    if rationale_found:
      break

  if not rationale_found:
    self.logger.error(
      "❌ RATIONALE MISSING: Rationale is enabled but no rationale fields found in output!")
    self.logger.error("This means either:")
    self.logger.error("  1. Function schema injection failed")
    self.logger.error("  2. LLM didn't follow the schema")
    self.logger.error("  3. Rationale fields were stripped during processing")

  return rationale_found


if __name__ == "__main__":
  exit_code = main()
  sys.exit(exit_code)
