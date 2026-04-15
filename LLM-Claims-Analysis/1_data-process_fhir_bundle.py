# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

"""
FHIR Processor - Production Ready Script 1
Converts FHIR bundles to unified JSON format for LLM claims analysis
"""

import time
import logging
import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
from llm_providers import ClassCreateLLM
import sys
import json
import uuid
import yaml


class ClassConfig:
  """Centralized configuration management for FHIR Processor"""

  def __init__ (self, config_path: Optional[str] = None):
    self.script_dir = Path(__file__).parent.resolve()
    self.config = self._load_config(config_path)

  def _load_config (self, config_path: Optional[str]) -> Dict:
    """Load FHIR processor specific configuration file"""

    if config_path is None:
      config_file = self.script_dir / "config" / "1_data-process_fhir_bundle.yaml"
    else:
      config_path_obj = Path(config_path)
      config_file = config_path_obj if config_path_obj.is_absolute() else self.script_dir / config_path

    print(f"🔧 Loading config from: {config_file}")

    if not config_file.exists():
      print(f"❌ Config file not found at: {config_file}")
      print("📝 Please create the 1_data-process_fhir_bundle.yaml file")
      print("   Use the provided configuration template")
      sys.exit(1)

    try:
      with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

      # Validate required sections
      required_sections = ['api_settings', 'processing', 'medical_classification']
      for section in required_sections:
        if section not in config:
          print(f"❌ Missing required config section: {section}")
          sys.exit(1)

      print(f"✅ Config loaded successfully")
      return config

    except Exception as e:
      print(f"❌ Error loading config: {e}")
      sys.exit(1)

  def get_api_settings (self) -> Dict:
    return self.config['api_settings']

  def get_logging_settings (self) -> Dict:
    return self.config.get('logging', {})

  def get_processing_settings (self) -> Dict:
    return self.config['processing']

  def get_medical_classification (self) -> Dict:
    return self.config['medical_classification']

  def get_encounter_filtering (self) -> Dict:
    return self.config.get('encounter_filtering', {})

  def get_relevance_classification (self) -> Dict:
    return self.config.get('relevance_classification', {})


class ClassAPIClient:
  """Centralized LLM API client with provider abstraction, retry logic, cost tracking, and structured logging"""

  def __init__(self, config: ClassConfig, logger: 'ClassLogger', dry_run: bool = False):
    self.config = config
    self.logger = logger
    self.dry_run = dry_run
    self.api_settings = config.get_api_settings()

    # Create provider using factory (OpenAI or Ollama)
    try:
      self.provider = ClassCreateLLM.create_provider(self.api_settings, logger, dry_run)
      provider_name = self.api_settings.get('provider', 'openai')
      dry_run_msg = " (DRY RUN mode)" if dry_run else ""
      self.logger.info(f"API Client initialized with {provider_name} provider{dry_run_msg}")
    except Exception as e:
      self.logger.error(f"Failed to initialize provider: {e}")
      raise

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

    self.logger.info(f"API Client initialized with {self.max_retries} max retries")

  def call_llm (self, prompt: str, model: str = None, max_tokens: int = None,
                temperature: float = 0.0, call_type: str = "general") -> Dict:
    """
    Make API call with retry logic, cost tracking, and structured logging

    This method maintains backward compatibility while using the provider abstraction
    """
    # Determine which model to use based on call_type
    if model is None:
      # Map call_type to specific model from config
      provider_name = self.api_settings.get('provider', 'openai')
      provider_config = self.api_settings.get(provider_name, {})
      models = provider_config.get('models', {})

      # Try to get model based on call type
      if call_type == "encounter_classification":
        model = models.get('classification')
      elif call_type == "clinical_note_generation":
        model = models.get('clinical_notes')

      # Fallback to default model
      if not model:
        model = models.get('default', 'gpt-4o-mini-2024-07-18')

    if max_tokens is None:
      max_tokens = self.api_settings.get('default_max_tokens', 1500)

    # Log API call start
    self.logger.debug(f"Starting API call: {call_type}")

    # Log the prompt if debug logging is enabled
    self.logger.debug_api_prompt(prompt, call_type.upper())

    for attempt in range(self.max_retries):
      try:
        # Show retry attempts
        if attempt > 0:
          self.logger.warning(
            f"Retrying API call (attempt {attempt + 1}/{self.max_retries})"
          )

        start_time = time.time()

        # Convert prompt to messages format
        messages = [{"role": "user", "content": prompt}]

        # Call provider's make_completion method
        result = self.provider.call_llm(
          messages=messages,
          model=model,
          max_tokens=max_tokens,
          temperature=temperature,
          call_type=call_type
        )

        end_time = time.time()
        response_time = end_time - start_time

        # Extract content and usage
        content = result['content']
        usage = result['usage']

        # Log the response if debug logging is enabled
        self.logger.debug_api_response(content, call_type.upper())

        # Calculate costs
        input_cost = self._calculate_input_cost(usage['prompt_tokens'], model)
        output_cost = self._calculate_output_cost(usage['completion_tokens'], model)
        total_cost = input_cost + output_cost

        self.total_cost += total_cost
        self.total_calls += 1
        self.total_tokens += usage['total_tokens']
        self.total_input_tokens += usage['prompt_tokens']
        self.total_output_tokens += usage['completion_tokens']

        # Log API call details
        self.logger.debug(f"API call successful - {call_type}")
        self.logger.debug(f"  Model: {model}")
        self.logger.debug(f"  Tokens: {usage['prompt_tokens']} → {usage['completion_tokens']}")
        self.logger.debug(f"  Cost: ${total_cost:.6f}")
        self.logger.debug(f"  Time: {response_time:.2f}s")

        # Periodic stats output (every 5 calls)
        if self.total_calls % 5 == 0:
          self.logger.stats({
            'total_cost': round(self.total_cost, 4),
            'total_tokens': self.total_tokens,
            'api_calls': self.total_calls
          })

        return {
          'content': content,
          'usage': {
            'prompt_tokens': usage['prompt_tokens'],
            'completion_tokens': usage['completion_tokens'],
            'total_tokens': usage['total_tokens']
          },
          'cost': total_cost,
          'response_time': response_time,
          'model': model
        }

      except Exception as e:
        self.logger.error(f"API call attempt {attempt + 1}/{self.max_retries} failed: {e}")

        if attempt < self.max_retries - 1:
          delay = self.base_delay ** (attempt + 1)
          self.logger.warning(f"Waiting {delay} seconds before retry...")
          time.sleep(delay)
        else:
          # Milestone for final failure
          self.logger.milestone(
            f"API call failed after {self.max_retries} attempts",
            status='error',
            data={'call_type': call_type, 'error': str(e)}
          )
          raise

  def _calculate_input_cost (self, tokens: int, model: str) -> float:
    """Calculate input token cost"""
    if 'gpt-4o-mini' in model:
      rate = self.pricing.get('gpt_4o_mini_input_cost_per_1k', 0.00015)
    elif 'gpt-5-nano' in model:
      rate = self.pricing.get('gpt_5_nano_input_cost_per_1k', 0.00005)
    else:
      rate = 0.00015  # Default fallback
    return (tokens / 1000) * rate

  def _calculate_output_cost (self, tokens: int, model: str) -> float:
    """Calculate output token cost"""
    if 'gpt-4o-mini' in model:
      rate = self.pricing.get('gpt_4o_mini_output_cost_per_1k', 0.0006)
    elif 'gpt-5-nano' in model:
      rate = self.pricing.get('gpt_5_nano_output_cost_per_1k', 0.0004)
    else:
      rate = 0.0006  # Default fallback
    return (tokens / 1000) * rate

  def get_cost_summary (self) -> Dict:
    """Get total cost and call statistics"""
    return self.provider.get_cost_summary()


class ClassLogger:
  """Logging with JSON output mode and structured events for UI integration

  Maintains full backward compatibility - existing functionality unchanged.
  When json_mode=False (default): Normal human-readable console output
  When json_mode=True: Structured JSON output for UI parsing
  """

  def __init__ (self, config, json_mode: bool = False):
    """Initialize logger with optional JSON output mode

    Args:
      config: UnifiedConfig object with logging settings
      json_mode: If True, output JSON to console for UI parsing
    """
    self.config = config
    self.json_mode = json_mode  # JSON output mode for UI
    self.log_settings = config.get_logging_settings()
    self.debug_options = self.log_settings.get('debug_options', {})

    # Setup logger (file + console)
    self.logger = logging.getLogger('fhir_processor')
    self.logger.setLevel(getattr(logging, self.log_settings.get('level', 'INFO')))

    # Clear existing handlers
    self.logger.handlers.clear()

    # Console handler - ALWAYS (but JSON mode overrides in _output_json)
    console_handler = logging.StreamHandler()
    console_format = logging.Formatter(
      self.log_settings.get('console_format', '%(asctime)s - %(levelname)s - %(message)s')
    )
    console_handler.setFormatter(console_format)
    self.logger.addHandler(console_handler)

    # File handler (optional) - ALWAYS uses text format
    if self.log_settings.get('file_logging', False):
      self._setup_file_logging()

    # Tracking
    self.start_time = time.time()

  def _setup_file_logging (self):
    """Setup file logging if enabled - UNCHANGED"""
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / f"{datetime.now().strftime('%Y%m%d')}_fhir_processor.log"

    file_handler = logging.FileHandler(log_file)
    file_format = logging.Formatter(
      self.log_settings.get('file_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    file_handler.setFormatter(file_format)
    self.logger.addHandler(file_handler)

  def _output_json (self, level: str, message: str, event_type: str = None, data: Dict = None):
    """Output JSON formatted event for UI consumption

    Outputs single-line JSON (JSON Lines format) for easy parsing.
    This is only called when json_mode=True.
    """
    event = {
      'timestamp': datetime.now().isoformat(),
      'level': level,
      'message': message
    }
    if event_type:
      event['type'] = event_type
    if data:
      event['data'] = data

    # Print as single-line JSON (one event per line)
    print(json.dumps(event), flush=True)

  def info (self, message: str):
    self.logger.info(message)
    if self.json_mode:
      self._output_json('info', message)

  def debug (self, message: str):
    self.logger.debug(message)
    if self.json_mode and self.logger.level <= logging.DEBUG:
      self._output_json('debug', message)

  def warning (self, message: str):
    self.logger.warning(message)
    if self.json_mode:
      self._output_json('warning', message)

  def error (self, message: str):
    self.logger.error(message)
    if self.json_mode:
      self._output_json('error', message)

  def success (self, message: str):
    self.logger.info(f"✅ {message}")
    if self.json_mode:
      self._output_json('info', message, event_type='success')

  def debug_api_prompt (self, prompt: str, call_type: str = "API"):
    """Log API prompt if debug options allow - UNCHANGED"""
    if not self.debug_options.get('show_api_prompts', False):
      return

    max_chars = self.debug_options.get('max_prompt_chars', 0)
    display_prompt = prompt

    if max_chars > 0 and len(prompt) > max_chars:
      display_prompt = prompt[:max_chars] + f"\n... [truncated, {len(prompt)} total chars]"

    self.debug("=" * 80)
    self.debug(f"📤 {call_type} PROMPT:")
    self.debug("=" * 80)
    self.debug(display_prompt)
    self.debug("=" * 80)

  def debug_api_response (self, response: str, call_type: str = "API"):
    """Log API response if debug options allow - UNCHANGED"""
    if not self.debug_options.get('show_api_responses', False):
      return

    max_chars = self.debug_options.get('max_response_chars', 0)
    display_response = response

    if max_chars > 0 and len(response) > max_chars:
      display_response = response[:max_chars] + f"\n... [truncated, {len(response)} total chars]"

    self.debug("=" * 80)
    self.debug(f"🤖 {call_type} RESPONSE:")
    self.debug("=" * 80)
    self.debug(display_response)
    self.debug("=" * 80)

  def progress (self, message: str, current: int = None, total: int = None, data: Dict = None):
    """Progress event - processing updates

    Args:
      message: Progress description
      current: Current item number (optional)
      total: Total items (optional)
      data: Additional metadata (optional)

    Example:
      logger.progress("Processing encounter", current=2, total=5)
    """
    # Always log to file
    self.logger.info(message)

    # Console output depends on mode
    if self.json_mode:
      event_data = {}
      if current is not None:
        event_data['current'] = current
      if total is not None:
        event_data['total'] = total
      if data:
        event_data.update(data)
      self._output_json('info', message, event_type='progress', data=event_data)
    else:
      # Human-readable format for CLI
      if current and total:
        print(f"📄 {message} ({current}/{total})")
      else:
        print(f"📄 {message}")

  def milestone (self, message: str, status: str = 'success', data: Dict = None):
    """Milestone event - major completions

    Args:
      message: Milestone description
      status: 'success', 'error', or 'warning'
      data: Additional metadata (optional)

    Example:
      logger.milestone("Classification complete", status='success', data={'count': 10})
    """
    # Always log to file
    if status == 'error':
      self.logger.error(message)
    elif status == 'warning':
      self.logger.warning(message)
    else:
      self.logger.info(message)

    # Console output depends on mode
    if self.json_mode:
      event_data = {'status': status}
      if data:
        event_data.update(data)
      level = 'error' if status == 'error' else 'warning' if status == 'warning' else 'info'
      self._output_json(level, message, event_type='milestone', data=event_data)
    else:
      # Human-readable format for CLI
      icon = '✅' if status == 'success' else '❌' if status == 'error' else '⚠️'
      print(f"{icon} {message}")

  def stats (self, stats_dict: Dict):
    """Statistics event - metrics and cost updates

    Args:
      stats_dict: Dictionary of statistics to report

    Example:
      logger.stats({
        'total_cost': 0.05,
        'total_tokens': 1234,
        'encounters_processed': 3
      })
    """
    # Always log to file (formatted)
    self.logger.info("Statistics update:")
    for key, value in stats_dict.items():
      self.logger.info(f"  {key}: {value}")

    # Console output depends on mode
    if self.json_mode:
      self._output_json('info', 'Statistics update', event_type='stats', data=stats_dict)
    else:
      # Human-readable format for CLI
      print("\n=== STATISTICS ===")
      for key, value in stats_dict.items():
        if isinstance(value, float):
          print(f"  {key}: {value:.4f}")
        else:
          print(f"  {key}: {value}")
      print("==================\n")


class ClassTrackMetrics:
  """Track processing metrics: time, calls per minute, tokens per dollar """

  def __init__ (self, logger: 'ClassLogger'):
    self.logger = logger
    self.start_time = time.time()
    self.encounter_count = 0
    self.file_count = 0
    self.api_calls = 0
    self.total_tokens = 0
    self.total_cost = 0.0

  def start_file_processing (self):
    """Mark start of file processing"""
    self.file_start_time = time.time()

  def end_file_processing (self, encounters_processed: int):
    """Mark end of file processing"""
    self.file_count += 1
    self.encounter_count += encounters_processed

    if hasattr(self, 'file_start_time'):
      processing_time = time.time() - self.file_start_time
      self.logger.debug(
        f"File processed in {processing_time:.2f}s ({encounters_processed} encounters)")

  def record_api_call (self, api_response: Dict):
    """Record API call metrics"""
    self.api_calls += 1
    self.total_tokens += api_response['usage']['total_tokens']
    self.total_cost += api_response['cost']

  def get_processing_rate (self) -> float:
    """Calculate encounters per minute"""
    elapsed_minutes = (time.time() - self.start_time) / 60
    return self.encounter_count / max(elapsed_minutes, 0.001)

  def get_api_rate (self) -> float:
    """Calculate API calls per minute"""
    elapsed_minutes = (time.time() - self.start_time) / 60
    return self.api_calls / max(elapsed_minutes, 0.001)

  def get_efficiency (self) -> float:
    """Calculate tokens per dollar efficiency"""
    return self.total_tokens / max(self.total_cost, 0.000001)

  def get_summary (self) -> Dict:
    """Get comprehensive metrics summary"""
    elapsed_time = time.time() - self.start_time
    return {
      'total_files': self.file_count,
      'total_encounters': self.encounter_count,
      'total_api_calls': self.api_calls,
      'total_tokens': self.total_tokens,
      'total_cost': self.total_cost,
      'elapsed_time': elapsed_time,
      'encounters_per_minute': self.get_processing_rate(),
      'api_calls_per_minute': self.get_api_rate(),
      'tokens_per_dollar': self.get_efficiency(),
      'average_cost_per_file': self.total_cost / max(self.file_count, 1),
      'average_tokens_per_encounter': self.total_tokens / max(self.encounter_count, 1)
    }


class ClassSummarizeClinicalData:
  """Configurable medical classification system with HIGH-COST prioritization for actuarial analysis
  - Uses logger.debug() instead of no logging
  - Adds logger.info() for important classification results
  """

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger
    self.medical_config = config.get_medical_classification()
    self.procedure_groups = self.medical_config.get('procedure_groups', {})
    self.medication_groups = self.medical_config.get('medication_groups', {})
    self.settings = self.medical_config.get('classification_settings', {})

    # Log initialization
    self.logger.debug(
      f"MedicalClassifier initialized with {len(self.procedure_groups)} procedure groups "
      f"and {len(self.medication_groups)} medication groups"
    )

  def classify_procedures (self, procedures: List[str]) -> Dict[str, Dict]:
    """Classify procedures using configurable keywords and return with metadata
    """
    if not procedures:
      self.logger.debug("No procedures to classify")
      return {}

    # Log start of classification
    self.logger.debug(f"Classifying {len(procedures)} procedures")

    procedure_counts = {}
    max_items = self.settings.get('max_procedure_groups', 6)
    case_sensitive = self.settings.get('case_sensitive', False)

    # Sort procedure groups by priority (HIGH-COST items first)
    sorted_groups = sorted(
      self.procedure_groups.items(),
      key=lambda x: x[1].get('priority', 999)
    )

    matched_count = 0
    unmatched_count = 0

    for proc in procedures:
      proc_text = proc if case_sensitive else proc.lower()
      matched = False

      # Try to match against configured groups
      for group_name, group_config in sorted_groups:
        keywords = group_config.get('keywords', [])

        if any(keyword in proc_text for keyword in keywords):
          if group_name not in procedure_counts:
            procedure_counts[group_name] = {
              'count': 0,
              'priority': group_config.get('priority', 999),
              'cost_impact': group_config.get('cost_impact', 'unknown'),
              'examples': []
            }

          procedure_counts[group_name]['count'] += 1
          procedure_counts[group_name]['examples'].append(proc[:50])
          matched = True
          matched_count += 1

          # Log high-cost procedure matches
          if group_config.get('cost_impact') in ['very_high', 'high']:
            self.logger.debug(f"HIGH-COST procedure matched: {group_name}")

          break

      # If no match found, add as individual procedure (up to max_items)
      if not matched and len(procedure_counts) < max_items:
        short_name = proc.split(' (')[0]
        if len(short_name) > 30:
          short_name = short_name[:30] + "..."

        procedure_counts[short_name] = {
          'count': 1,
          'priority': 999,
          'cost_impact': 'unknown',
          'examples': [proc[:50]]
        }
        unmatched_count += 1

    # Log classification summary
    self.logger.debug(
      f"Procedure classification complete: {matched_count} matched to groups, "
      f"{unmatched_count} individual procedures, {len(procedure_counts)} total groups"
    )

    return procedure_counts

  def classify_medications (self, medications: List[str]) -> Dict[str, Dict]:
    """Classify medications using configurable keywords and return with metadata
    """
    if not medications:
      self.logger.debug("No medications to classify")
      return {}

    # Log start of classification
    self.logger.debug(f"Classifying {len(medications)} medications")

    med_counts = {}
    max_items = self.settings.get('max_medication_groups', 5)
    case_sensitive = self.settings.get('case_sensitive', False)

    # Sort medication groups by priority (HIGH-COST items first)
    sorted_groups = sorted(
      self.medication_groups.items(),
      key=lambda x: x[1].get('priority', 999)
    )

    matched_count = 0
    unmatched_count = 0

    for med in medications:
      med_text = med if case_sensitive else med.lower()
      matched = False

      # Try to match against configured groups
      for group_name, group_config in sorted_groups:
        keywords = group_config.get('keywords', [])

        if any(keyword in med_text for keyword in keywords):
          if group_name not in med_counts:
            med_counts[group_name] = {
              'count': 0,
              'priority': group_config.get('priority', 999),
              'cost_impact': group_config.get('cost_impact', 'unknown'),
              'category': group_config.get('category', 'general'),
              'examples': []
            }

          med_counts[group_name]['count'] += 1
          med_counts[group_name]['examples'].append(med[:50])
          matched = True
          matched_count += 1

          # Log high-cost medication matches
          if group_config.get('cost_impact') in ['very_high', 'high']:
            self.logger.debug(f"HIGH-COST medication matched: {group_name}")

          break

      # If no match found, add as individual medication (up to max_items)
      if not matched and len(med_counts) < max_items:
        short_name = med.split(' (')[0]
        if len(short_name) > 30:
          short_name = short_name[:30] + "..."

        med_counts[short_name] = {
          'count': 1,
          'priority': 999,
          'cost_impact': 'unknown',
          'category': 'general',
          'examples': [med[:50]]
        }
        unmatched_count += 1

    # Log classification summary
    self.logger.debug(
      f"Medication classification complete: {matched_count} matched to groups, "
      f"{unmatched_count} individual medications, {len(med_counts)} total groups"
    )

    return med_counts

  def summarize_procedures (self, procedures: List[str], max_items: Optional[int] = None) -> str:
    """Summarize procedures with HIGH-COST prioritization for actuarial analysis
    """
    if not procedures:
      self.logger.debug("No procedures to summarize")
      return "No procedures documented"

    if max_items is None:
      max_items = self.settings.get('max_procedure_groups', 6)

    # Log summarization start
    self.logger.debug(f"Summarizing {len(procedures)} procedures (max_items={max_items})")

    procedure_data = self.classify_procedures(procedures)

    # Sort by cost impact and count, prioritizing HIGH-COST procedures
    def sort_key (item):
      name, data = item
      cost_priority = {'very_high': 0, 'high': 1, 'moderate': 2, 'low': 3, 'unknown': 4}
      return (cost_priority.get(data['cost_impact'], 4), -data['count'], data['priority'])

    sorted_groups = sorted(procedure_data.items(), key=sort_key)[:max_items]

    summary_parts = []
    high_cost_count = 0

    for proc_type, data in sorted_groups:
      count = data['count']
      cost_impact = data['cost_impact']

      # Add cost indicator for high-impact procedures
      cost_indicator = ""
      if cost_impact in ['very_high', 'high']:
        cost_indicator = " [HIGH-COST]"
        high_cost_count += 1

      if count > 1:
        summary_parts.append(f"{proc_type} ({count}x){cost_indicator}")
      else:
        summary_parts.append(f"{proc_type}{cost_indicator}")

    summary = '; '.join(summary_parts)

    # Log summary with high-cost indicator
    if high_cost_count > 0:
      self.logger.info(f"Procedure summary includes {high_cost_count} HIGH-COST items")
    self.logger.debug(f"Procedure summary generated: {len(summary_parts)} items")

    return summary

  def summarize_medications (self, medications: List[str], max_items: Optional[int] = None) -> str:
    """Summarize medications with HIGH-COST prioritization for actuarial analysis
    """
    if not medications:
      self.logger.debug("No medications to summarize")
      return "No medications documented"

    if max_items is None:
      max_items = self.settings.get('max_medication_groups', 5)

    # Log summarization start
    self.logger.debug(f"Summarizing {len(medications)} medications (max_items={max_items})")

    med_data = self.classify_medications(medications)

    # Sort by cost impact and count, prioritizing HIGH-COST medications
    def sort_key (item):
      name, data = item
      cost_priority = {'very_high': 0, 'high': 1, 'moderate': 2, 'low': 3, 'unknown': 4}
      return (cost_priority.get(data['cost_impact'], 4), -data['count'], data['priority'])

    sorted_groups = sorted(med_data.items(), key=sort_key)[:max_items]

    summary_parts = []
    high_cost_count = 0

    for med_type, data in sorted_groups:
      count = data['count']
      cost_impact = data['cost_impact']

      # Add cost indicator for high-impact medications
      cost_indicator = ""
      if cost_impact in ['very_high', 'high']:
        cost_indicator = " [HIGH-COST]"
        high_cost_count += 1

      if count > 1:
        summary_parts.append(f"{med_type} ({count}x){cost_indicator}")
      else:
        summary_parts.append(f"{med_type}{cost_indicator}")

    summary = '; '.join(summary_parts)

    # Log summary with high-cost indicator
    if high_cost_count > 0:
      self.logger.info(f"Medication summary includes {high_cost_count} HIGH-COST items")
    self.logger.debug(f"Medication summary generated: {len(summary_parts)} items")

    return summary


class ClassProcessEncounter:
  """Filter and prioritize encounters based on relevance and recency"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger
    self.filter_settings = config.get_encounter_filtering()

  def filter_encounters (self, encounters: List[Dict]) -> List[Dict]:
    """Filter encounters based on configuration rules"""
    if not self.filter_settings.get('enabled', False):
      self.logger.debug("Encounter filtering disabled")
      return encounters

    original_count = len(encounters)
    filtered_encounters = encounters

    # Filter by recency if configured
    recent_months = self.filter_settings.get('recent_only_months')
    if recent_months and recent_months > 0:
      cutoff_date = datetime.now() - timedelta(days=recent_months * 30)
      self.logger.debug(
        f"Filtering encounters to last {recent_months} months (after {cutoff_date.strftime('%Y-%m-%d')})")
      filtered_encounters = self._filter_by_recency(filtered_encounters, cutoff_date)
    else:
      self.logger.debug("No recency filtering applied (recent_only_months = 0 or not set)")

    # Limit encounters per patient if configured
    max_encounters = self.filter_settings.get('max_encounters_per_patient')
    if max_encounters and max_encounters > 0 and len(filtered_encounters) > max_encounters:
      filtered_encounters = self._prioritize_encounters(filtered_encounters, max_encounters)

    filtered_count = len(filtered_encounters)
    if filtered_count != original_count:
      self.logger.info(f"Filtered encounters: {original_count} → {filtered_count}")
    else:
      self.logger.debug(f"No encounters filtered out ({original_count} encounters)")

    return filtered_encounters

  def _filter_by_recency (self, encounters: List[Dict], cutoff_date: datetime) -> List[Dict]:
    """Filter encounters by recency"""
    recent_encounters = []
    no_date_encounters = []

    for encounter in encounters:
      encounter_date = self._parse_encounter_date(encounter)
      if encounter_date:
        if encounter_date >= cutoff_date:
          recent_encounters.append(encounter)
          self.logger.debug(
            f"Encounter {encounter.get('id', 'unknown')} included (date: {encounter_date.strftime('%Y-%m-%d')})")
        else:
          self.logger.debug(
            f"Encounter {encounter.get('id', 'unknown')} filtered out (date: {encounter_date.strftime('%Y-%m-%d')} before cutoff)")
      else:
        # Include encounters without dates (rather than excluding them)
        no_date_encounters.append(encounter)
        self.logger.debug(f"Encounter {encounter.get('id', 'unknown')} included (no date found)")

    # Combine recent encounters with encounters that have no date
    all_included = recent_encounters + no_date_encounters

    self.logger.debug(
      f"Date filtering: {len(recent_encounters)} with recent dates, {len(no_date_encounters)} without dates, {len(all_included)} total included")

    return all_included

  def _prioritize_encounters (self, encounters: List[Dict], max_count: int) -> List[Dict]:
    """Prioritize encounters by recency and clinical relevance"""
    # Sort by date (most recent first) and take top N
    encounters_with_dates = []
    for encounter in encounters:
      encounter_date = self._parse_encounter_date(encounter)
      encounters_with_dates.append((encounter_date or datetime.min, encounter))

    encounters_with_dates.sort(key=lambda x: x[0], reverse=True)
    return [encounter for _, encounter in encounters_with_dates[:max_count]]

  def _parse_encounter_date (self, encounter: Dict) -> Optional[datetime]:
    """Parse encounter date from various possible formats"""
    # Try different date fields that might exist in FHIR resources
    date_fields = [
      'period', 'start', 'date', 'effectiveDateTime', 'authoredOn',
      'performedDateTime', 'onsetDateTime', 'recordedDate', 'occurrenceDateTime'
    ]

    for field in date_fields:
      if field in encounter:
        date_value = encounter[field]

        # Handle period objects
        if isinstance(date_value, dict) and 'start' in date_value:
          date_value = date_value['start']

        if isinstance(date_value, str) and date_value:
          try:
            # Clean the date string
            clean_date = date_value.split('.')[0].replace('Z', '').replace('+00:00', '')

            # Try various date formats
            date_formats = [
              '%Y-%m-%d',
              '%Y-%m-%dT%H:%M:%S',
              '%Y-%m-%dT%H:%M',
              '%Y-%m-%d %H:%M:%S',
              '%Y/%m/%d',
              '%m/%d/%Y'
            ]

            for fmt in date_formats:
              try:
                parsed_date = datetime.strptime(clean_date, fmt)
                self.logger.debug(f"Successfully parsed date {date_value} using format {fmt}")
                return parsed_date
              except ValueError:
                continue

          except Exception as e:
            self.logger.debug(f"Error parsing date {date_value}: {e}")
            continue

    # If no date found, default to None (will be filtered out)
    self.logger.debug(f"No valid date found for encounter {encounter.get('id', 'unknown')}")
    return None


class ClassProcessFhir:
  """Main FHIR processing class for Synthea native format with infrastructure integration"""

  def __init__ (self, config: ClassConfig, logger: 'ClassLogger', dry_run: bool = False):
    self.config = config
    self.logger = logger
    self.dry_run = dry_run

    # Initialize components
    self.api_client = ClassAPIClient(config, logger, dry_run)
    self.metrics = ClassTrackMetrics(logger)
    self.medical_classifier = ClassSummarizeClinicalData(config, logger)
    self.encounter_filter = ClassProcessEncounter(config, logger)

    # Processing settings
    self.processing_settings = config.get_processing_settings()
    self.relevance_settings = config.get_relevance_classification()

    # Processing statistics
    self.processing_stats = {
      "total_evaluated": 0,
      "relevant_encounters": 0,
      "classification_errors": 0,
      "note_generation_errors": 0,
      "api_calls": 0,
      "total_cost": 0.0,
      "skipped_irrelevant": 0
    }

    # Track models used for each task type
    self.models_used = {
      "classification": set(),
      "clinical_notes": set()
    }

    self.logger.info("FHIR Processor initialized for Synthea native format")

  def _detect_bundle_type (self, data: Dict) -> str:
    """
    Detect whether this is a Synthea native format or standard R4 FHIR bundle

    Returns:
        'synthea' - Synthea native format {seed, record: {encounters: [...]}}
        'fhir_r4' - Standard FHIR R4 bundle {resourceType: "Bundle", entry: [...]}
        'unknown' - Unable to determine format
    """
    # Check for Synthea native format
    if 'record' in data and 'encounters' in data.get('record', {}):
      self.logger.info("📦 Detected: Synthea native format")
      return 'synthea'

    # Check for standard FHIR R4 bundle
    if data.get('resourceType') == 'Bundle' and 'entry' in data:
      bundle_type = data.get('type', 'unknown')
      self.logger.info(f"📦 Detected: Standard FHIR R4 bundle (type: {bundle_type})")
      return 'fhir_r4'

    self.logger.warning("⚠️ Unknown bundle format")
    self.logger.debug(f"Root keys found: {list(data.keys())}")
    return 'unknown'

  def _normalize_encounter_for_filter (self, encounter: Dict, bundle_type: str) -> Dict:
    """
    Normalize R4 encounter to Synthea-like format for filter compatibility
    Your encounter_filter expects Synthea format, so we convert R4 to match
    """
    if bundle_type == 'synthea':
      encounter['_original_format'] = 'synthea'
      # Already in correct format
      return encounter
    elif bundle_type == 'fhir_r4':
      # Convert R4 simple strings to Synthea-like objects
      # Convert medications (strings → objects with codes)
      medications_normalized = []
      for med in encounter.get('medications', []):
        if isinstance(med, str):
          medications_normalized.append({
            'codes': [{'display': med}],
            'description': med
          })
        else:
          medications_normalized.append(med)

      # Convert procedures (strings → objects with codes)
      procedures_normalized = []
      for proc in encounter.get('procedures', []):
        if isinstance(proc, str):
          procedures_normalized.append({
            'codes': [{'display': proc}],
            'description': proc
          })
        else:
          procedures_normalized.append(proc)
      # Convert diagnoses (strings → objects with codes)
      diagnoses_normalized = []
      for diag in encounter.get('diagnoses', []):
        if isinstance(diag, str):
          diagnoses_normalized.append({
            'codes': [{'display': diag}],
            'description': diag
          })
        else:
          diagnoses_normalized.append(diag)

      # Convert observations (strings → objects with codes)
      observations_normalized = []
      for obs in encounter.get('observations', []):
        if isinstance(obs, str):
          observations_normalized.append({
            'codes': [{'display': obs}],
            'value': obs
          })
        else:
          observations_normalized.append(obs)
      # Create normalized encounter in Synthea-like format
      normalized = {
        'uuid': encounter.get('encounter_id', ''),
        'start': self._iso_to_timestamp(encounter.get('date', '')),
        'encounterType': encounter.get('type', ''),
        'synthea_type': encounter.get('type', ''),
        'synthea_name': encounter.get('type', ''),
        'class': encounter.get('class', ''),
        'diagnoses': diagnoses_normalized,
        'procedures': procedures_normalized,
        'medications': medications_normalized,
        'conditions': diagnoses_normalized,  # Conditions = diagnoses
        'reasonDescription': encounter.get('reason', ''),
        'observations': observations_normalized,
        '_original_format': 'fhir_r4'
      }

      return normalized

    return encounter

  def _iso_to_timestamp (self, iso_date: str) -> int:
    """
    Convert ISO date string to millisecond timestamp (for Synthea compatibility)
    """
    if not iso_date:
      return 0

    try:
      from datetime import datetime
      dt = datetime.strptime(iso_date, '%Y-%m-%d')
      return int(dt.timestamp() * 1000)  # Convert to milliseconds
    except ValueError:
      return 0

  def _timestamp_to_iso (self, timestamp: Optional[int]) -> str:
    """Convert Synthea timestamp (milliseconds since epoch) to ISO format"""
    if timestamp is None:
      return datetime.now().isoformat()

    try:
      # Synthea uses milliseconds since epoch
      dt = datetime.fromtimestamp(timestamp / 1000)
      return dt.strftime('%Y-%m-%d')
    except Exception:
      return datetime.now().strftime('%Y-%m-%d')

  def process_bundle (self, bundle_path: str, output_dir: str = None, limit: int = None) -> \
    Optional[Dict]:
    """Process a single Synthea native format file"""
    self.logger.info(f"📄 Processing Synthea file: {Path(bundle_path).name}")

    # Milestone for start
    self.logger.milestone(
      "Starting bundle processing",
      status='success',
      data={'bundle_file': Path(bundle_path).name}
    )

    self.metrics.start_file_processing()

    # Reset processing stats for this file
    self.processing_stats = {key: 0 if isinstance(value, int) else 0.0 for key, value in
                             self.processing_stats.items()}

    # Reset models tracking for this file
    self.models_used = {
      "classification": set(),
      "clinical_notes": set()
    }

    try:
      # Load and validate Synthea data
      synthea_data = self._load_bundle(bundle_path)
      if not synthea_data:
        return None

      # Extract patient demographics based on bundle type
      bundle_type = synthea_data.get('_detected_bundle_type', 'synthea')

      if bundle_type == 'synthea':
        demographics = self._extract_patient_demographics_from_synthea(synthea_data)
      elif bundle_type == 'fhir_r4':
        demographics = self._extract_patient_demographics_from_fhir_r4(synthea_data)
      else:
        self.logger.error("❌ Unknown bundle type for patient extraction")
        return None

      self.logger.info(
        f"👤 Patient: {demographics['name']} ({demographics['age']}, {demographics['gender']})")

      # Extract encounters based on bundle type
      bundle_type = synthea_data.get('_detected_bundle_type', 'synthea')

      if bundle_type == 'synthea':
        raw_encounters = self._extract_encounters_from_synthea(synthea_data)
      elif bundle_type == 'fhir_r4':
        raw_encounters = self._extract_encounters_from_fhir_r4(synthea_data)
      else:
        self.logger.error("❌ Unknown bundle type for encounter extraction")
        return None

      self.logger.info(f"📋 Found {len(raw_encounters)} encounters")

      if not raw_encounters:
        self.logger.warning("No encounters found in Synthea data")
        return None

      # Normalize encounters for filter compatibility
      # (R4 encounters need to match Synthea format for existing filter logic)
      normalized_encounters = [
        self._normalize_encounter_for_filter(enc, bundle_type)
        for enc in raw_encounters
      ]

      filtered_encounters = self.encounter_filter.filter_encounters(normalized_encounters)

      # Apply limit if specified
      if limit:
        filtered_encounters = filtered_encounters[:limit]
        self.logger.info(f"🔢 Limited to {len(filtered_encounters)} encounters")

      # Process encounters
      processed_encounters = []
      for i, encounter in enumerate(filtered_encounters):
        # Progress tracking
        self.logger.progress(
          f"Evaluating encounter relevance",
          current=i + 1,
          total=len(filtered_encounters),
          data={'encounter_type': encounter.get('synthea_type', 'unknown')}
        )

        try:
          processed_encounter = self._process_encounter(encounter, i + 1)
          if processed_encounter:
            processed_encounters.append(processed_encounter)
            self.processing_stats["relevant_encounters"] += 1

        except Exception as e:
          self.logger.error(f"Error processing encounter {i + 1}: {e}")
          self.processing_stats["classification_errors"] += 1
          continue

        self.processing_stats["total_evaluated"] += 1

      # Check if we have any relevant encounters
      if not processed_encounters:
        self.logger.warning("No actuarially relevant encounters found - skipping file creation")
        return None

      # Milestone for completion
      self.logger.milestone(
        f"Encounter processing complete",
        status='success',
        data={
          'total_evaluated': len(filtered_encounters),
          'relevant': len(processed_encounters),
          'skipped': len(filtered_encounters) - len(processed_encounters)
        }
      )

      # Create claim ID
      claim_id = self._generate_claim_id(bundle_path, demographics)

      # Create unified JSON output (compatible with Script 2)
      unified_output = self._create_unified_output(
        claim_id, demographics, processed_encounters, bundle_path
      )

      self._save_output(unified_output, output_dir, claim_id, demographics['initials'])

      # Record metrics
      self.metrics.end_file_processing(len(processed_encounters))

      # Update total processing stats
      self.processing_stats["api_calls"] = self.api_client.total_calls
      self.processing_stats["total_cost"] = self.api_client.total_cost

      # Log summary
      self._log_processing_summary()

      return unified_output

    except Exception as e:
      self.logger.error(f"Error processing Synthea data: {e}")
      import traceback
      self.logger.debug(f"Traceback: {traceback.format_exc()}")
      return None

  def _load_bundle (self, bundle_path: str) -> Optional[Dict]:
    """
    Load and validate FHIR bundle - supports both Synthea native and standard R4 formats
    """
    try:
      with open(bundle_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

      # Validate it's a dict
      if not isinstance(data, dict):
        self.logger.error("❌ File is not a valid JSON object")
        return None

      # Detect bundle type
      bundle_type = self._detect_bundle_type(data)

      if bundle_type == 'unknown':
        self.logger.error("❌ Unrecognized bundle format")
        self.logger.error(f"Expected either:")
        self.logger.error("  1. Synthea format: {record: {encounters: [...]}}")
        self.logger.error("  2. FHIR R4 format: {resourceType: 'Bundle', entry: [...]}")
        return None

      # Store bundle type for later use
      data['_detected_bundle_type'] = bundle_type

      # Validate content based on type
      if bundle_type == 'synthea':
        encounters = data['record']['encounters']
        self.logger.info(f"✅ Synthea native format loaded with {len(encounters)} encounters")

        if len(encounters) == 0:
          self.logger.warning("⚠️ No encounters found in Synthea data")
          return None

      elif bundle_type == 'fhir_r4':
        entries = data.get('entry', [])
        self.logger.info(f"✅ FHIR R4 bundle loaded with {len(entries)} entries")

        if len(entries) == 0:
          self.logger.warning("⚠️ No entries found in FHIR bundle")
          return None

      return data

    except json.JSONDecodeError as e:
      self.logger.error(f"❌ Invalid JSON in file: {e}")
      return None
    except Exception as e:
      self.logger.error(f"❌ Error loading bundle: {e}")
      import traceback
      self.logger.debug(f"Traceback: {traceback.format_exc()}")
      return None

  def _extract_patient_demographics_from_synthea (self, synthea_data: Dict) -> Dict:
    """Extract patient demographics from Synthea native format"""
    demographics = {
      'name': 'Synthea Patient',
      'initials': 'SP',
      'age': 'Unknown',
      'gender': 'Unknown'
    }

    try:
      # Patient info is in the 'attributes' section
      attributes = synthea_data.get('attributes', {})

      # Extract name components
      first_name = attributes.get('first_name', '')
      middle_name = attributes.get('middle_name', '')
      last_name = attributes.get('last_name', '')

      # Build full name
      name_parts = [first_name, middle_name, last_name]
      full_name = ' '.join([p for p in name_parts if p]).strip()

      if full_name:
        demographics['name'] = full_name
      else:
        # Fallback to 'name' field if individual parts not available
        demographics['name'] = attributes.get('name', 'Synthea Generated Patient')

      # Generate initials from first and last name
      if first_name and last_name:
        # Remove numbers from names (Synthea adds numbers like "Angelic427")
        clean_first = ''.join([c for c in first_name if c.isalpha()])
        clean_last = ''.join([c for c in last_name if c.isalpha()])

        if clean_first and clean_last:
          demographics['initials'] = f"{clean_first[0]}{clean_last[0]}".upper()
        else:
          demographics['initials'] = 'SG'  # Fallback
      else:
        demographics['initials'] = 'SG'  # Fallback

      # Extract age
      age = attributes.get('AGE')
      if age is not None:
        demographics['age'] = str(age)
      else:
        # Calculate age from birthdate if available
        birthdate_timestamp = attributes.get('birthdate')
        if birthdate_timestamp:
          try:
            # Synthea uses milliseconds since epoch
            birth_date = datetime.fromtimestamp(birthdate_timestamp / 1000).date()
            today = date.today()
            age_calc = (today - birth_date).days // 365
            demographics['age'] = str(age_calc)
          except:
            demographics['age'] = 'Unknown'

      # Extract gender
      gender = attributes.get('gender', 'Unknown')
      # Normalize gender (Synthea uses 'M'/'F')
      if gender == 'M':
        demographics['gender'] = 'Male'
      elif gender == 'F':
        demographics['gender'] = 'Female'
      else:
        demographics['gender'] = gender if gender else 'Unknown'

      self.logger.debug(f"Extracted patient demographics: {demographics}")

    except Exception as e:
      self.logger.debug(f"Could not extract patient demographics: {e}")
      # Return defaults
      pass

    return demographics

  def _extract_encounters_from_synthea (self, synthea_data: Dict) -> List[Dict]:
    """Extract encounter data from Synthea native format"""
    encounters = []

    try:
      synthea_encounters = synthea_data.get('record', {}).get('encounters', [])

      for idx, enc in enumerate(synthea_encounters):
        encounter_data = {
          'id': enc.get('uuid', f"encounter-{idx}"),
          'resourceType': 'Encounter',
          'synthea_type': enc.get('type', 'unknown'),
          'synthea_name': enc.get('name', 'Unknown Encounter'),
          'start': self._timestamp_to_iso(enc.get('start')),
          'stop': self._timestamp_to_iso(enc.get('stop')),
          'ended': enc.get('ended', False),

          # Store raw Synthea data
          'conditions': enc.get('conditions', []),
          'procedures': enc.get('procedures', []),
          'medications': enc.get('medications', []),
          'observations': enc.get('observations', []),
          'immunizations': enc.get('immunizations', []),
          'careplans': enc.get('careplans', []),
          'allergies': enc.get('allergies', []),
          'reports': enc.get('reports', []),
          'codes': enc.get('codes', []),
          'cost': enc.get('cost', {})
        }

        encounters.append(encounter_data)

      self.logger.debug(f"Extracted {len(encounters)} encounters from Synthea data")

    except Exception as e:
      self.logger.error(f"Error extracting Synthea encounters: {e}")
      import traceback
      self.logger.debug(f"Traceback: {traceback.format_exc()}")

    return encounters

  def _extract_patient_demographics_from_fhir_r4 (self, fhir_bundle: Dict) -> Dict:
    """
    Extract patient demographics from standard FHIR R4 bundle
    Handles the example format with entry array containing resources
    """
    demographics = {
      'name': 'Unknown Patient',
      'initials': 'UP',
      'age': 'Unknown',
      'gender': 'Unknown',
      'date_of_birth': None
    }

    try:
      # Find Patient resource in bundle entries
      patient_resource = None
      for entry in fhir_bundle.get('entry', []):
        resource = entry.get('resource', {})
        if resource.get('resourceType') == 'Patient':
          patient_resource = resource
          break

      if not patient_resource:
        self.logger.warning("⚠️ No Patient resource found in FHIR bundle")
        return demographics

      # Extract name
      names = patient_resource.get('name', [])
      if names:
        name_obj = names[0]

        # Get name components
        given_names = name_obj.get('given', [])
        family_name = name_obj.get('family', '')

        # Use 'text' field if available (full formatted name)
        if 'text' in name_obj:
          demographics['name'] = name_obj['text']
        elif given_names and family_name:
          full_name = ' '.join(given_names) + ' ' + family_name
          demographics['name'] = full_name.strip()

        # Generate initials
        if given_names and family_name:
          first_initial = given_names[0][0] if given_names[0] else 'U'
          last_initial = family_name[0] if family_name else 'P'
          demographics['initials'] = f"{first_initial}{last_initial}".upper()

      # Extract gender
      gender = patient_resource.get('gender', '')
      if gender:
        demographics['gender'] = gender.capitalize()

      # Extract birthdate and calculate age
      birth_date_str = patient_resource.get('birthDate')
      if birth_date_str:
        demographics['date_of_birth'] = birth_date_str
        try:
          birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
          today = date.today()
          age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
          )
          demographics['age'] = str(age)
        except ValueError:
          self.logger.warning(f"⚠️ Could not parse birthdate: {birth_date_str}")

      self.logger.info(f"👤 Extracted patient: {demographics['name']} ({demographics['initials']}), "
                       f"Age: {demographics['age']}, Gender: {demographics['gender']}")

    except Exception as e:
      self.logger.error(f"❌ Error extracting patient demographics: {e}")
      import traceback
      self.logger.debug(f"Traceback: {traceback.format_exc()}")

    return demographics

  def _extract_encounters_from_fhir_r4 (self, fhir_bundle: Dict) -> List[Dict]:
    """
    Extract encounters from standard FHIR R4 bundle
    Returns encounters in a normalized format similar to Synthea
    """
    encounters = []

    try:
      # Get all resources by type for easy lookup
      resources_by_type = {}
      for entry in fhir_bundle.get('entry', []):
        resource = entry.get('resource', {})
        resource_type = resource.get('resourceType')
        if resource_type:
          if resource_type not in resources_by_type:
            resources_by_type[resource_type] = []
          resources_by_type[resource_type].append(resource)

      # Process each Encounter resource
      encounter_resources = resources_by_type.get('Encounter', [])

      for encounter_resource in encounter_resources:
        encounter_data = {
          'encounter_id': encounter_resource.get('id', str(uuid.uuid4())),
          'date': None,
          'type': '',
          'class': '',
          'diagnoses': [],
          'procedures': [],
          'medications': [],
          'observations': [],
          'reason': ''
        }

        # Extract date from period
        period = encounter_resource.get('period', {})
        if 'start' in period:
          encounter_data['date'] = period['start'].split('T')[0]  # Get date part

        # Extract encounter type
        types = encounter_resource.get('type', [])
        if types:
          type_text = types[0].get('text', '')
          if not type_text:
            # Try to get from coding
            codings = types[0].get('coding', [])
            if codings:
              type_text = codings[0].get('display', '')
          encounter_data['type'] = type_text

        # Extract encounter class
        encounter_class = encounter_resource.get('class', {})
        if encounter_class:
          encounter_data['class'] = encounter_class.get('display',
                                                        encounter_class.get('code', ''))

        encounters.append(encounter_data)

      # Now find and attach related resources to encounters
      self._attach_related_resources_r4(encounters, resources_by_type, fhir_bundle)

      self.logger.info(f"📋 Extracted {len(encounters)} encounters from FHIR R4 bundle")

    except Exception as e:
      self.logger.error(f"❌ Error extracting encounters: {e}")
      import traceback
      self.logger.debug(f"Traceback: {traceback.format_exc()}")

    return encounters

  def _attach_related_resources_r4 (self, encounters: List[Dict], resources_by_type: Dict,
                                    fhir_bundle: Dict):
    """
    Attach diagnoses, medications, observations to encounters
    """
    try:
      # Process Observations
      for obs in resources_by_type.get('Observation', []):
        encounter_ref = obs.get('encounter', {}).get('reference', '')
        obs_value = obs.get('valueString', '')
        obs_code = obs.get('code', {}).get('text', 'Observation')

        for encounter in encounters:
          if encounter['encounter_id'] in encounter_ref:
            if obs_value:
              encounter['observations'].append(f"{obs_code}: {obs_value}")
            if not encounter['reason'] and obs_value:
              encounter['reason'] = obs_value

      # Process MedicationRequest
      for med_req in resources_by_type.get('MedicationRequest', []):
        med_concept = med_req.get('medicationCodeableConcept', {})
        med_text = med_concept.get('text', '')

        if not med_text:
          codings = med_concept.get('coding', [])
          if codings:
            med_text = codings[0].get('display', 'Medication')

        # Try to match to encounter (if no encounter ref, add to all)
        if med_text:
          for encounter in encounters:
            encounter['medications'].append(med_text)

      # Process MedicationStatement
      for med_stmt in resources_by_type.get('MedicationStatement', []):
        med_concept = med_stmt.get('medicationCodeableConcept', {})
        med_text = med_concept.get('text', '')

        if med_text:
          for encounter in encounters:
            encounter['medications'].append(med_text)

      # Process AllergyIntolerance (add as observation)
      for allergy in resources_by_type.get('AllergyIntolerance', []):
        allergy_code = allergy.get('code', {}).get('text', '')
        reactions = allergy.get('reaction', [])
        reaction_text = ''
        if reactions:
          manifestations = reactions[0].get('manifestation', [])
          if manifestations:
            reaction_text = manifestations[0].get('text', '')

        if allergy_code:
          allergy_info = f"Allergy: {allergy_code}"
          if reaction_text:
            allergy_info += f" (reaction: {reaction_text})"

          for encounter in encounters:
            encounter['observations'].append(allergy_info)

    except Exception as e:
      self.logger.error(f"⚠️ Error attaching related resources: {e}")

  def _process_encounter (self, encounter: Dict, encounter_num: int) -> Optional[Dict]:
    """Process individual encounter with classification and note generation"""

    try:
      # Step 1: Classify encounter relevance
      classification_result, classification_model = self._classify_encounter_relevance(encounter)

      self.logger.debug(f"Encounter {encounter_num} classification:")
      self.logger.debug(f"  - Relevant: {classification_result['is_relevant']}")
      self.logger.debug(f"  - Confidence: {classification_result['confidence']:.2f}")
      self.logger.debug(f"  - Category: {classification_result['category']}")
      self.logger.debug(f"  - Reason: {classification_result['reason']}")
      self.logger.debug(f"  - Model: {classification_model}")

      if not classification_result['is_relevant']:
        self.logger.info(
          f"❌ Encounter {encounter_num} not relevant: {classification_result['reason']}")
        self.processing_stats["skipped_irrelevant"] += 1
        return None

      self.logger.info(
        f"✅ Encounter {encounter_num} is relevant ({classification_result['category']}, confidence: {classification_result['confidence']:.2f})")

      # Step 2: Generate clinical note
      document_text, clinical_note_model = self._generate_clinical_note(encounter,
                                                                        classification_result)
      if not document_text:
        self.logger.warning(f"Failed to generate clinical note for encounter {encounter_num}")
        return None

      # Track models used
      self.models_used["classification"].add(classification_model)
      self.models_used["clinical_notes"].add(clinical_note_model)

      # Step 3: Create encounter output structure (compatible with Script 2)
      encounter_output = {
        "encounter_id": encounter.get('id', f"encounter_{encounter_num}"),
        "document_type": "document_text",  # Required by Script 2
        "document_text": document_text,
        "encounter_date": self._extract_encounter_date(encounter),
        "source_file": encounter.get('_original_format', 'synthea'),
        "encounter_metadata": {
          "resource_type": encounter.get('resourceType', 'unknown'),
          "synthea_type": encounter.get('synthea_type', 'unknown'),
          "synthea_name": encounter.get('synthea_name', 'Unknown'),
          "classification": classification_result,
          "processing_timestamp": datetime.now().isoformat(),
          "models_used": {
            "classification_model": classification_model,
            "clinical_note_model": clinical_note_model
          }
        }
      }

      return encounter_output

    except Exception as e:
      self.logger.error(f"Error processing encounter {encounter_num}: {e}")
      import traceback
      self.logger.error(f"Traceback: {traceback.format_exc()}")
      return None

  def _classify_encounter_relevance (self, encounter: Dict) -> tuple:
    """Classify encounter relevance using LLM with structured output

    Returns:
      tuple: (classification_dict, model_used)
    """

    # Create classification prompt
    prompt = self._create_classification_prompt(encounter)

    try:
      # Make API call for classification
      api_response = self.api_client.call_llm(
        prompt=prompt,
        model=self.config.get_api_settings().get('classification_model', 'gpt-4o-mini-2024-07-18'),
        max_tokens=self.config.get_api_settings().get('classification_max_tokens', 1000),
        call_type="encounter_classification"
      )

      # Record metrics
      self.metrics.record_api_call(api_response)

      # Parse response
      classification = self._parse_classification_response(api_response['content'])
      model_used = api_response.get('model_used', 'unknown')

      return classification, model_used

    except Exception as e:
      self.logger.error(f"Classification API call failed: {e}")
      return {
        'is_relevant': False,
        'confidence': 0.0,
        'reason': f"Classification error: {str(e)}",
        'category': 'error'
      }, 'error'

  def _create_classification_prompt (self, encounter: Dict) -> str:
    """Create classification prompt for encounter relevance"""

    # Extract key information from encounter
    resource_type = encounter.get('resourceType', 'unknown')
    encounter_summary = self._summarize_encounter_for_classification(encounter)

    prompt = f"""Analyze this medical encounter for actuarial relevance and potential cost impact.

ENCOUNTER DATA:
Resource Type: {resource_type}
{encounter_summary}

CLASSIFICATION CRITERIA:
- HIGH RELEVANCE: Chronic conditions, surgeries, high-cost treatments, emergency care, ongoing medical needs
- MODERATE RELEVANCE: Acute illnesses, mental health, diagnostic procedures, medication management, specialist visits
- LOW RELEVANCE: Routine preventive care, wellness checks, minor issues
- ONLY exclude if clearly administrative or non-medical

IMPORTANT: Be inclusive - when in doubt, classify as relevant for actuarial analysis.

Respond with JSON only:
{{
  "is_relevant": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation",
  "category": "high_cost|moderate_cost|low_cost|preventive|administrative", 
  "cost_indicators": ["list", "of", "potential", "cost", "factors"]
}}"""

    return prompt

  def _summarize_encounter_for_classification (self, encounter: Dict) -> str:
    """Create a concise summary of Synthea encounter for classification"""

    summary_parts = []

    # Add Synthea encounter type and name
    enc_type = encounter.get('synthea_type', 'unknown')
    enc_name = encounter.get('synthea_name', 'Unknown')
    summary_parts.append(f"Encounter Type: {enc_type}")
    summary_parts.append(f"Encounter Name: {enc_name}")

    # Add date
    start = encounter.get('start', 'unknown')
    summary_parts.append(f"Date: {start}")

    # Summarize conditions
    conditions = encounter.get('conditions', [])
    if conditions:
      condition_names = []
      for cond in conditions[:3]:  # Limit to first 3
        codes = cond.get('codes', [])
        if codes:
          condition_names.append(codes[0].get('display', 'Unknown'))
      if condition_names:
        summary_parts.append(f"Conditions: {', '.join(condition_names)}")

    # Summarize procedures
    procedures = encounter.get('procedures', [])
    if procedures:
      procedure_names = []
      for proc in procedures[:3]:  # Limit to first 3
        codes = proc.get('codes', [])
        if codes:
          procedure_names.append(codes[0].get('display', 'Unknown'))
      if procedure_names:
        summary_parts.append(f"Procedures: {', '.join(procedure_names)}")

    # Summarize medications
    medications = encounter.get('medications', [])
    if medications:
      med_names = []
      for med in medications[:3]:  # Limit to first 3
        codes = med.get('codes', [])
        if codes:
          med_names.append(codes[0].get('display', 'Unknown'))
      if med_names:
        summary_parts.append(f"Medications: {', '.join(med_names)}")

    # Summarize observations
    observations = encounter.get('observations', [])
    if observations:
      obs_names = []
      for obs in observations[:3]:  # Limit to first 3
        codes = obs.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          value = obs.get('value', '')
          unit = obs.get('unit', '')
          if value:
            obs_names.append(f"{display}: {value} {unit}".strip())
          else:
            obs_names.append(display)
      if obs_names:
        summary_parts.append(f"Observations: {', '.join(obs_names)}")

    # Add immunizations
    immunizations = encounter.get('immunizations', [])
    if immunizations:
      imm_names = []
      for imm in immunizations[:2]:  # Limit to first 2
        codes = imm.get('codes', [])
        if codes:
          imm_names.append(codes[0].get('display', 'Unknown'))
      if imm_names:
        summary_parts.append(f"Immunizations: {', '.join(imm_names)}")

    return '\n'.join(summary_parts) if summary_parts else "No detailed information available"

  def _parse_classification_response (self, response_content: str) -> Dict:
    """Parse classification response with fallback handling"""

    try:
      # Try to extract JSON from response
      json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
      if json_match:
        classification = json.loads(json_match.group())

        # Validate required fields
        required_fields = ['is_relevant', 'confidence', 'reason', 'category']
        for field in required_fields:
          if field not in classification:
            classification[field] = self._get_default_classification_value(field)

        # Ensure confidence is a float between 0 and 1
        try:
          classification['confidence'] = max(0.0, min(1.0, float(classification['confidence'])))
        except (ValueError, TypeError):
          classification['confidence'] = 0.5

        return classification

    except (json.JSONDecodeError, AttributeError) as e:
      self.logger.warning(f"Failed to parse classification JSON: {e}")

    # Fallback classification
    return {
      'is_relevant': True,  # Default to relevant to be safe
      'confidence': 0.5,
      'reason': 'Failed to parse classification response',
      'category': 'unknown',
      'cost_indicators': []
    }

  def _get_default_classification_value (self, field: str):
    """Get default value for missing classification field"""
    defaults = {
      'is_relevant': True,
      'confidence': 0.5,
      'reason': 'Default classification',
      'category': 'unknown',
      'cost_indicators': []
    }
    return defaults.get(field, None)

  def _generate_clinical_note (self, encounter: Dict, classification: Dict) -> tuple:
    """Generate clinical note for encounter

    Returns:
      tuple: (document_text, model_used) or (None, 'error') on failure
    """

    # Create clinical note prompt
    prompt = self._create_clinical_note_prompt(encounter, classification)

    try:
      # Make API call for note generation
      api_response = self.api_client.call_llm(
        prompt=prompt,
        model=self.config.get_api_settings().get('clinical_notes_model', 'gpt-4o-mini-2024-07-18'),
        max_tokens=self.config.get_api_settings().get('clinical_note_max_tokens', 2000),
        call_type="clinical_note_generation"
      )

      # Record metrics
      self.metrics.record_api_call(api_response)

      # Extract clinical note from response
      document_text = api_response['content'].strip()
      model_used = api_response.get('model_used', 'unknown')

      # Basic validation
      if len(document_text) < 50:
        self.logger.warning("Generated clinical note is too short")
        return None, model_used

      return document_text, model_used

    except Exception as e:
      self.logger.error(f"Clinical note generation failed: {e}")
      self.processing_stats["note_generation_errors"] += 1
      return None, 'error'

  def _create_clinical_note_prompt (self, encounter: Dict, classification: Dict) -> str:
    """Create prompt for clinical note generation"""

    # Get detailed encounter information
    encounter_details = self._get_detailed_encounter_info(encounter)

    # Extract classification info safely
    category = classification.get('category', 'unknown')
    confidence = classification.get('confidence', 0.0)
    reason = classification.get('reason', 'N/A')
    cost_indicators = classification.get('cost_indicators', [])

    # Format cost indicators
    cost_indicators_str = ', '.join(cost_indicators) if cost_indicators else 'None specified'

    prompt = f"""Generate a comprehensive clinical note for this medical encounter.

  ENCOUNTER INFORMATION:
  {encounter_details}

  RELEVANCE CLASSIFICATION:
  - Category: {category}
  - Confidence: {confidence:.1%}
  - Reason: {reason}
  - Cost Indicators: {cost_indicators_str}

  REQUIREMENTS:
  - Write as a professional clinical note
  - Include relevant medical terminology
  - Focus on billable and significant clinical elements
  - Structure: Chief Complaint, Assessment, Plan
  - Length: 200-500 words
  - Be specific about procedures, medications, and diagnoses

  Generate the clinical note:"""

    return prompt

  def _get_detailed_encounter_info (self, encounter: Dict) -> str:
    """Get detailed encounter information from Synthea format for note generation"""

    info_parts = []

    # Basic encounter info
    info_parts.append(f"Encounter Type: {encounter.get('synthea_type', 'unknown')}")
    info_parts.append(f"Encounter Name: {encounter.get('synthea_name', 'Unknown')}")
    info_parts.append(f"Date: {encounter.get('start', 'unknown')}")

    # Conditions
    conditions = encounter.get('conditions', [])
    if conditions:
      info_parts.append(f"\nConditions ({len(conditions)}):")
      for cond in conditions:
        codes = cond.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          info_parts.append(f"  - {display}")

    # Procedures
    procedures = encounter.get('procedures', [])
    if procedures:
      info_parts.append(f"\nProcedures ({len(procedures)}):")
      for proc in procedures:
        codes = proc.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          info_parts.append(f"  - {display}")

    # Medications
    medications = encounter.get('medications', [])
    if medications:
      info_parts.append(f"\nMedications ({len(medications)}):")
      for med in medications:
        codes = med.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          info_parts.append(f"  - {display}")

    # Observations
    observations = encounter.get('observations', [])
    if observations:
      info_parts.append(f"\nObservations ({len(observations)}):")
      for obs in observations[:10]:  # Limit to first 10
        codes = obs.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          value = obs.get('value', '')
          unit = obs.get('unit', '')
          if value:
            info_parts.append(f"  - {display}: {value} {unit}".strip())
          else:
            info_parts.append(f"  - {display}")

    # Immunizations
    immunizations = encounter.get('immunizations', [])
    if immunizations:
      info_parts.append(f"\nImmunizations ({len(immunizations)}):")
      for imm in immunizations:
        codes = imm.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          info_parts.append(f"  - {display}")

    # Allergies
    allergies = encounter.get('allergies', [])
    if allergies:
      info_parts.append(f"\nAllergies ({len(allergies)}):")
      for allergy in allergies:
        codes = allergy.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          info_parts.append(f"  - {display}")

    # CarePlans
    careplans = encounter.get('careplans', [])
    if careplans:
      info_parts.append(f"\nCare Plans ({len(careplans)}):")
      for plan in careplans[:3]:  # Limit to first 3
        codes = plan.get('codes', [])
        if codes:
          display = codes[0].get('display', 'Unknown')
          info_parts.append(f"  - {display}")

    # Cost information - FIXED TO HANDLE BOTH FLOAT AND DICT
    cost = encounter.get('cost')
    if cost is not None:
      try:
        if isinstance(cost, dict):
          # Cost is a dictionary like {'total': 150.0}
          total = cost.get('total', 0)
          info_parts.append(f"\nEncounter Cost: ${total:.2f}")
        elif isinstance(cost, (int, float)):
          # Cost is a simple number like 150.0
          info_parts.append(f"\nEncounter Cost: ${cost:.2f}")
      except (TypeError, ValueError) as e:
        # If there's any issue, just skip the cost
        self.logger.debug(f"Could not format cost: {e}")

    return '\n'.join(info_parts)

  def _extract_encounter_date (self, encounter: Dict) -> str:
    """Extract encounter date from Synthea format"""
    return encounter.get('start', datetime.now().strftime('%Y-%m-%d'))

  def _generate_claim_id (self, bundle_path: str, demographics: Dict) -> str:
    """Generate unique claim ID"""
    unique_id = uuid.uuid4()
    unique_int = unique_id.int
    short_id = unique_int % 10_000_000_000
    return short_id

  def _create_unified_output (self, claim_id: str, demographics: Dict,
                              encounters: List[Dict], bundle_path: str,
                              bundle_type: str = 'synthea') -> Dict:
    """Create unified JSON output compatible with Script 2"""

    # Get provider and models info
    provider_name = self.config.get_api_settings().get('provider', 'openai')

    return {
      "claim_id": claim_id,
      "patient_initials": demographics['initials'],
      "patient_metadata": {
        "age": demographics['age'],
        "gender": demographics['gender'],
        "name": demographics['name']
      },
      "encounters": encounters,
      "processing_metadata": {
        "source_type": "fhir_processor",
        "bundle_format": bundle_type,
        "bundle_file": str(Path(bundle_path).name),
        "processing_timestamp": datetime.now().isoformat(),
        "total_encounters_evaluated": self.processing_stats["total_evaluated"],
        "relevant_encounters": self.processing_stats["relevant_encounters"],
        "processing_stats": self.processing_stats.copy(),
        "cost_summary": self.api_client.get_cost_summary(),
        "processor_version": "1.0",
        "llm_provider": provider_name,
        "models_used": {
          "classification": list(self.models_used["classification"]),
          "clinical_notes": list(self.models_used["clinical_notes"])
        }
      }
    }

  def _save_output (self, unified_output: Dict, output_dir: str,
                    claim_id: str, patient_initials: str) -> str:
    """Save unified output to JSON file"""

    # Determine output directory
    if output_dir is None:
      output_dir = self.processing_settings.get('default_output_dir',
                                                './output/1_data-process_fhir_bundle')

    # Convert to Path and ensure it's relative to script directory
    script_dir = Path(__file__).parent
    output_path = script_dir / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    # Create filename
    output_filename = f"{patient_initials}_{claim_id}.json"
    output_file = output_path / output_filename

    try:
      with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_output, f, indent=2, ensure_ascii=False)

      self.logger.success(f"Output saved: {output_file}")
      return str(output_file)

    except Exception as e:
      self.logger.error(f"Error saving output: {e}")
      raise

  def _log_processing_summary (self):
    """Log processing summary for this file"""
    stats = self.processing_stats

    self.logger.info("─" * 50)
    self.logger.info("📊 FILE PROCESSING SUMMARY")
    self.logger.info(f"  Encounters evaluated: {stats['total_evaluated']}")
    self.logger.info(f"  Relevant encounters: {stats['relevant_encounters']}")
    self.logger.info(f"  API calls made: {stats['api_calls']}")
    self.logger.info(f"  Processing cost: ${stats['total_cost']:.4f}")

    if stats['classification_errors'] > 0:
      self.logger.warning(f"  Classification errors: {stats['classification_errors']}")
    if stats['note_generation_errors'] > 0:
      self.logger.warning(f"  Note generation errors: {stats['note_generation_errors']}")

    self.logger.info("─" * 50)

    # Structured stats for UI
    self.logger.stats({
      'encounters_evaluated': stats['total_evaluated'],
      'relevant_encounters': stats['relevant_encounters'],
      'skipped_encounters': stats['skipped_irrelevant'],
      'api_calls': stats['api_calls'],
      'total_cost': stats['total_cost'],
      'classification_errors': stats['classification_errors'],
      'note_generation_errors': stats['note_generation_errors']
    })


def process_single_file (processor: ClassProcessFhir, bundle_path: str,
                         output_dir: str = None, limit: int = None) -> bool:
  """Process a single FHIR bundle file"""

  try:
    # Validate input file
    bundle_file = Path(bundle_path)
    if not bundle_file.exists():
      processor.logger.error(f"Bundle file not found: {bundle_path}")
      return False

    if not bundle_file.suffix.lower() == '.json':
      processor.logger.error(f"Bundle file must be JSON: {bundle_path}")
      return False

    processor.logger.info(f"🎯 Single file mode: {bundle_file.name}")

    # Process the file
    result = processor.process_bundle(str(bundle_file), output_dir, limit)

    if result:
      processor.logger.success(f"Successfully processed: {bundle_file.name}")
      return True
    else:
      processor.logger.error(f"Failed to process: {bundle_file.name}")
      return False

  except Exception as e:
    processor.logger.error(f"Error in single file processing: {e}")
    return False


def process_batch_files (processor: ClassProcessFhir, input_dir: str,
                         output_dir: str = None, limit: int = None) -> bool:
  """Process all FHIR bundle files in a directory"""

  try:
    # Validate input directory
    input_path = Path(input_dir)
    if not input_path.exists():
      processor.logger.error(f"Input directory not found: {input_dir}")
      return False

    if not input_path.is_dir():
      processor.logger.error(f"Input path is not a directory: {input_dir}")
      return False

    # Find JSON files
    json_files = list(input_path.glob("*.json"))
    if not json_files:
      processor.logger.error(f"No JSON files found in: {input_dir}")
      return False

    processor.logger.info(f"📂 Batch mode: {len(json_files)} files in {input_path}")
    processor.logger.milestone(
      f"Starting batch processing",
      status='success',
      data={'total_files': len(json_files)}
    )

    # Process files
    successful_files = 0
    failed_files = 0

    for i, json_file in enumerate(json_files, 1):
      processor.logger.info(f"\n{'=' * 60}")

      # CHANGED: Use progress() instead of plain info()
      processor.logger.progress(
        f"Processing file: {json_file.name}",
        current=i,
        total=len(json_files),
        data={'filename': json_file.name}
      )

      processor.logger.info(f"{'=' * 60}")

      try:
        result = processor.process_bundle(str(json_file), output_dir, limit)

        if result:
          successful_files += 1
          processor.logger.success(f"✅ File {i} completed successfully")
        else:
          failed_files += 1
          processor.logger.error(f"❌ File {i} failed to process")

      except Exception as e:
        failed_files += 1
        processor.logger.error(f"Error processing {json_file.name}: {e}")

    # Final batch summary
    processor.logger.info(f"\n{'=' * 60}")
    processor.logger.milestone(
      "Batch processing complete",
      status='success' if failed_files == 0 else 'warning',
      data={
        'successful_files': successful_files,
        'failed_files': failed_files,
        'total_files': len(json_files)
      }
    )

    return failed_files == 0

  except Exception as e:
    processor.logger.error(f"Error in batch processing: {e}")
    return False


def validate_arguments (args, json_mode: bool = False) -> bool:
  """Validate command line arguments

  Args:
    args: Parsed arguments
    json_mode: If True, output errors as JSON

  Returns:
    True if valid, False otherwise
  """

  def print_error (message: str):
    """Print error message based on mode"""
    if json_mode:
      error_event = {
        'timestamp': datetime.now().isoformat(),
        'level': 'error',
        'message': message,
        'type': 'milestone',
        'data': {'status': 'error'}
      }
      print(json.dumps(error_event))
    else:
      print(f"❌ Error: {message}")

  # Validate single file mode
  if args.bundle:
    bundle_path = Path(args.bundle)

    if not bundle_path.exists():
      print_error(f"Bundle file not found: {args.bundle}")
      return False

    if not bundle_path.suffix.lower() == '.json':
      print_error(f"Bundle file must be JSON: {args.bundle}")
      return False
    if not json_mode:
      print(f"📄 Bundle file: {bundle_path}")


  # Validate batch mode
  elif args.input_dir:
    input_path = Path(args.input_dir)
    if not input_path.exists():
      print_error(f"Input directory not found: {args.input_dir}")
      return False
    if not input_path.is_dir():
      print_error(f"Input path is not a directory: {args.input_dir}")
      return False
    if not json_mode:
      print(f"📁 Input directory: {input_path}")

  # Validate/create output directory
  if args.output_dir:
    try:
      output_path = Path(args.output_dir)
      output_path.mkdir(parents=True, exist_ok=True)
      if not json_mode:
        print(f"📂 Output directory: {output_path}")
    except Exception as e:
      print_error(f"Cannot create output directory {args.output_dir}: {e}")
      return False

  return True


def setup_argument_parser () -> argparse.ArgumentParser:
  """Setup command line argument parser with --json-output flag"""

  parser = argparse.ArgumentParser(
    description="FHIR Processor - Convert FHIR bundles to unified JSON for claims analysis",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  # Process single file (human-readable output)
  python 1_data-process_fhir_bundle.py -b "path/to/bundle.json" --limit 5

  # Process with JSON output for UI
  python 1_data-process_fhir_bundle.py -b "bundle.json" --json-output

  # Process directory of files  
  python 1_data-process_fhir_bundle.py --input-dir "input/fhir_bundles" --output-dir "./output/"

  # Process with custom config
  python 1_data-process_fhir_bundle.py -b "bundle.json" --config "custom_config.yaml"

  # Verbose logging
  python 1_data-process_fhir_bundle.py -b "bundle.json" --verbose

Output Structure (Compatible with Script 2):
  - claim_id: Unique identifier for the claim
  - patient_initials: Patient initials
  - patient_metadata: Age, gender, name
  - encounters: List of processed encounters with clinical notes
  - processing_metadata: Processing details with source_type="fhir_processor"

Configuration:
  Place config file at: ./config/1_data-process_fhir_bundle.yaml
  Includes medical classification, API settings, and processing options
        """
  )

  # Input options (mutually exclusive)
  input_group = parser.add_mutually_exclusive_group(required=False)
  input_group.add_argument(
    "-b", "--bundle",
    help="Path to single FHIR bundle JSON file"
  )
  input_group.add_argument(
    "--input-dir",
    help="Directory containing FHIR bundle files for batch processing"
  )

  # Output and processing options
  parser.add_argument(
    "--output-dir",
    help="Output directory (default: ./output/1_data-process_fhir_bundle/)"
  )
  parser.add_argument(
    "--limit",
    type=int,
    help="Limit number of encounters per file (for testing)"
  )
  parser.add_argument(
    "--config",
    help="Path to configuration file (default: config/1_data-process_fhir_bundle.yaml)"
  )

  # Processing options
  parser.add_argument(
    "--skip-validation",
    action="store_true",
    help="Skip input validation (not recommended)"
  )
  parser.add_argument(
    "--verbose",
    action="store_true",
    help="Enable verbose debug logging"
  )
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Run without making LLM API calls (returns mock data for testing)"
  )

  parser.add_argument(
    "--json-output",
    action="store_true",
    help="Output structured JSON events for UI consumption (instead of human-readable text)"
  )

  return parser


def print_startup_banner ():
  """Print startup banner with version info"""
  print("🚀 FHIR Processor")
  print("=" * 60)
  print("🔄 Converts FHIR bundles to unified JSON format")
  print("💰 Includes HIGH-COST medical classification")
  print("🔗 Compatible with Script 2 (Document Generator)")
  print("📊 Enhanced with metrics tracking and cost analysis")
  print("=" * 60)


def print_completion_banner (success: bool, start_time: float):
  """Print completion banner with timing"""
  elapsed_time = time.time() - start_time

  print("\n" + "=" * 60)
  if success:
    print("✅ PROCESSING COMPLETED SUCCESSFULLY")
  else:
    print("❌ PROCESSING COMPLETED WITH ERRORS")
  print("=" * 60)
  print(f"⏱️  Total elapsed time: {elapsed_time:.1f} seconds")
  print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  print("=" * 60)


def main ():
  """Main entry point - updated to support JSON output mode and optional input arguments"""

  start_time = time.time()

  try:
    # Parse arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Only print startup messages if NOT in JSON mode
    if not args.json_output:
      print("\n" + "=" * 60)
      print("FHIR PROCESSOR - SCRIPT 1")
      print("Convert FHIR bundles to unified JSON")
      print("=" * 60 + "\n")

    # Validate arguments (skip prints in JSON mode)
    if not validate_arguments(args, json_mode=args.json_output):
      return 1

    # Load configuration
    try:
      config = ClassConfig(args.config)

      # Override log level if verbose flag set
      if args.verbose:
        config.config['logging']['level'] = 'DEBUG'
        if not args.json_output:
          print("🔍 Verbose mode enabled - setting log level to DEBUG")

    except Exception as e:
      if args.json_output:
        # Output error as JSON
        error_event = {
          'timestamp': datetime.now().isoformat(),
          'level': 'error',
          'message': f"Configuration error: {e}",
          'type': 'milestone',
          'data': {'status': 'error'}
        }
        print(json.dumps(error_event))
      else:
        print(f"❌ Configuration error: {e}")
      return 1

    # Initialize logger with JSON mode
    try:
      logger = ClassLogger(config, json_mode=args.json_output)

      if not args.json_output:
        print("✅ Logger initialized")

    except Exception as e:
      if args.json_output:
        error_event = {
          'timestamp': datetime.now().isoformat(),
          'level': 'error',
          'message': f"Logger initialization failed: {e}",
          'type': 'milestone',
          'data': {'status': 'error'}
        }
        print(json.dumps(error_event))
      else:
        print(f"❌ Logger initialization failed: {e}")
      return 1

    # Initialize processor (with dry_run flag if present)
    try:
      processor = ClassProcessFhir(config, logger, dry_run=args.dry_run)
      if not args.json_output:
        print("✅ Processor initialized" + (" (DRY RUN mode)" if args.dry_run else ""))
    except Exception as e:
      logger.error(f"Processor initialization failed: {e}")
      logger.milestone("Processor initialization failed", status='error')
      return 1

    # Log startup milestone
    logger.milestone("FHIR Processor started", status='success', data={
      'working_directory': str(Path.cwd()),
      'config_file': str(config.config),
      'json_mode': args.json_output,
      'dry_run': args.dry_run
    })

    # Determine input source (explicit or config default)

    # Determine which processing mode to use
    if args.bundle:
      # Single file mode (explicitly specified)
      input_source = args.bundle
      processing_mode = 'single_file'

    elif args.input_dir:
      # Batch mode with explicit directory
      input_source = args.input_dir
      processing_mode = 'batch'

    else:
      # Use default input directory from config
      default_input = config.get_processing_settings().get('input_folder')

      if not default_input:
        error_msg = "No input specified and no input_folder in config"
        logger.error(error_msg)
        logger.milestone("Configuration error", status='error', data={
          'error': error_msg,
          'solution': 'Either specify -b/--bundle or --input-dir, or set input_folder in config'
        })
        if not args.json_output:
          print(f"❌ Error: {error_msg}")
          print("   Either:")
          print("   1. Specify -b or --input-dir on command line")
          print("   2. Set input_folder in config/1_data-process_fhir_bundle.yaml")
        return 1

      # Resolve default path
      script_dir = Path(__file__).parent.resolve()
      default_path = Path(default_input)
      if not default_path.is_absolute():
        default_path = script_dir / default_input

      # Validate default path exists
      if not default_path.exists():
        error_msg = f"Default input directory does not exist: {default_path}"
        logger.error(error_msg)
        logger.milestone("Input validation failed", status='error', data={
          'error': error_msg,
          'input_folder': str(default_path),
          'solution': 'Configure input_folder in config file'
        })
        if not args.json_output:
          print(f"❌ Error: {error_msg}")
          print(f"   Configure input_folder in: config/1_data-process_fhir_bundle.yaml")
        return 1

      # Use default directory for batch processing
      input_source = str(default_path)
      processing_mode = 'batch'

      # Log that we're using default directory
      logger.info(f"Using default input directory from config: {default_path}")
      if not args.json_output:
        print(f"📂 Using default input directory from config: {default_path}")

    # Process files based on determined mode

    try:
      if processing_mode == 'single_file':
        logger.info("Starting single file processing...")
        success = process_single_file(processor, input_source, args.output_dir, args.limit)
        files_to_process = 1

      else:  # batch mode
        logger.info("Starting batch file processing...")
        success = process_batch_files(processor, input_source, args.output_dir, args.limit)

        # Count files for stats
        input_path = Path(input_source)
        files_to_process = len(list(input_path.glob("*.json")))

      # Final stats output
      duration = time.time() - start_time

      # Get final metrics from processor
      final_stats = {
        'processing_duration': round(duration, 2),
        'total_cost': processor.api_client.total_cost,
        'tokens': {
          'total': processor.api_client.total_tokens,
          'input': processor.api_client.total_input_tokens,
          'output': processor.api_client.total_output_tokens,
          'ratio': round(processor.api_client.total_output_tokens /
                         max(processor.api_client.total_input_tokens, 1), 2)
        },
        'api_calls': processor.api_client.total_calls,
        'files_processed': files_to_process,
        'processing_mode': processing_mode,
        'input_source': input_source,
        'success': success
      }

      # Output final stats
      logger.stats(final_stats)

      # Print completion banner (only in non-JSON mode)
      if not args.json_output:
        print_completion_banner(success, start_time)
      else:
        # Output final milestone in JSON mode
        logger.milestone(
          "Processing complete" if success else "Processing failed",
          status='success' if success else 'error',
          data=final_stats
        )

      return 0 if success else 1

    except KeyboardInterrupt:
      logger.warning("Processing interrupted by user")
      logger.milestone("Processing interrupted", status='warning')
      return 1
    except Exception as e:
      logger.error(f"Unexpected processing error: {e}")
      logger.milestone("Processing failed", status='error', data={'error': str(e)})
      return 1

  except KeyboardInterrupt:
    # Handle early interruption
    if 'logger' in locals():
      logger.milestone("Startup interrupted", status='warning')
    return 1
  except Exception as e:
    if 'logger' in locals():
      logger.milestone("Fatal startup error", status='error', data={'error': str(e)})
    return 1


if __name__ == "__main__":
  sys.exit(main())
