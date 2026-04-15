# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# python 2_data-add_documents.py --limit 1
# python 2_data-add_documents.py --input-dir ./input --output-dir ./output --json-output
"""
Synthetic Document Generator for Claims Analysis - Script 2
Generates comprehensive claim documents from FHIR processor outputs
with modern infrastructure: UnifiedConfig, APIClient, SimpleLogger, MetricsTracker
Validates input comes from Script 1 (FHIR processor)

✨ STRUCTURED LOGGING:
- JSON output mode (--json-output flag)
- progress() events for tracking loops
- milestone() events for key completions
- stats() events for metrics and costs

Exit Codes:
0 - Success
1 - Configuration error
2 - Input/Output error
3 - Processing error
4 - Validation error
"""

import json
import yaml
import sys
import logging
import argparse
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from time import perf_counter
import traceback
from llm_providers import ClassCreateLLM

# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_IO_ERROR = 2
EXIT_PROCESSING_ERROR = 3
EXIT_VALIDATION_ERROR = 4

# Document types mapping
DOCUMENT_TYPES = {
  "phone_transcript": "Initial Phone Call Transcript",
  "adjuster_notes_initial": "Initial Adjuster Notes",
  "medical_provider_letter": "Medical Provider Letter",
  "settlement_adjuster_notes": "Settlement Adjuster Notes",
  "claimant_statement": "Claimant Statement"
}

class ClassConfig:
  """Centralized configuration management for Document Generator"""

  def __init__ (self, config_path: Optional[str] = None):
    self.script_dir = Path(__file__).parent.resolve()
    self.config = self._load_config(config_path)

  def _load_config (self, config_path: Optional[str]) -> Dict:
    """Load document generator specific configuration file"""
    if config_path is None:
      config_file = self.script_dir / "config" / "2_data-add_documents.yaml"
    else:
      config_path_obj = Path(config_path)
      config_file = config_path_obj if config_path_obj.is_absolute() else self.script_dir / config_path

    if not config_file.exists():
      print(f"❌ Config file not found at: {config_file}", file=sys.stderr)
      print("📝 Please create the 2_data-add_documents.yaml file", file=sys.stderr)
      sys.exit(EXIT_CONFIG_ERROR)

    try:
      with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

      # Validate required sections
      required_sections = ['api_settings', 'processing', 'document_generation', 'logging']
      for section in required_sections:
        if section not in config:
          print(f"❌ Missing required config section: {section}", file=sys.stderr)
          sys.exit(EXIT_CONFIG_ERROR)

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

  def get_document_generation_settings (self) -> Dict:
    return self.config['document_generation']

  def get_validation_settings (self) -> Dict:
    return self.config['validation']

  def get_max_tokens_for_call_type (self, call_type: str) -> int:
      """
      Get max_tokens for a specific call type.
      Priority: document_generation -> api_settings fallback

      Args:
          call_type: One of:
              - 'master_profile' or 'master_profile_generation'
              - 'phone_transcript'
              - 'adjuster_notes_initial'
              - 'medical_provider_letter'
              - 'settlement_adjuster_notes'
              - 'claimant_statement'

      Returns:
          Max tokens for that call type
      """
      doc_gen = self.config.get('document_generation', {})
      api_settings = self.config.get('api_settings', {})

      # Normalize call_type
      if call_type == 'master_profile_generation':
        call_type = 'master_profile'

      # Try document_generation first (PRIMARY)
      if call_type == 'master_profile':
        master_settings = doc_gen.get('master_profile', {})
        if 'max_tokens' in master_settings:
          return master_settings['max_tokens']
      else:
        # Check in documents section
        documents = doc_gen.get('documents', {})
        if call_type in documents and 'max_tokens' in documents[call_type]:
          return documents[call_type]['max_tokens']

      # Fallback to api_settings (SECONDARY)
      if call_type == 'master_profile':
        if 'master_profile_max_tokens' in api_settings:
          return api_settings['master_profile_max_tokens']
      else:
        if 'document_max_tokens' in api_settings:
          return api_settings['document_max_tokens']

      # Final fallback to default
      return api_settings.get('default_max_tokens', 1500)

  def get_temperature_for_call_type (self, call_type: str) -> float:
    """
    Get temperature for a specific call type.
    Priority: document_generation -> default (0.7)

    Args:
        call_type: Same as get_max_tokens_for_call_type

    Returns:
        Temperature for that call type
    """
    doc_gen = self.config.get('document_generation', {})

    # Normalize call_type
    if call_type == 'master_profile_generation':
      call_type = 'master_profile'

    # Try document_generation
    if call_type == 'master_profile':
      master_settings = doc_gen.get('master_profile', {})
      if 'temperature' in master_settings:
        return master_settings['temperature']
    else:
      documents = doc_gen.get('documents', {})
      if call_type in documents and 'temperature' in documents[call_type]:
        return documents[call_type]['temperature']

    # Default temperature
    return 0.7


class ClassAPIClient:
  """Centralized OpenAI API client with retry logic and cost tracking"""

  def __init__ (self, config: ClassConfig, logger: 'ClassLogger'):
    self.config = config
    self.logger = logger
    self.api_settings = config.get_api_settings()

    # Create provider using factory (OpenAI or Ollama)
    try:
      self.provider = ClassCreateLLM.create_provider(self.api_settings, logger)
      provider_name = self.api_settings.get('provider', 'openai')
      self.logger.info(f"API Client initialized with {provider_name} provider")
    except Exception as e:
      self.logger.error(f"Failed to initialize provider: {e}")
      raise

    # Pricing configuration
    provider_config = self.api_settings.get(provider_name, {})
    self.pricing = provider_config.get('pricing', {})

    # Cost tracking
    self.total_cost = 0.0
    self.total_calls = 0
    self.total_tokens = 0
    self.total_input_tokens = 0
    self.total_output_tokens = 0

    # Retry settings from config
    self.max_retries = self.api_settings.get('retry_count', 3)
    self.base_delay = self.api_settings.get('retry_delay_base', 2)

    self.logger.info(f"API Client initialized with {self.max_retries} max retries")



  def call_llm_with_function (
    self,
    messages: List[Dict],
    function_schema: Dict,
    function_name: str,
    model: str = None,
    call_type: str = "function_call",
    max_tokens: int = None,
    temperature: float = 0.7
  ) -> Dict:
    """Make API call with function calling and retry logic"""

    # Determine model based on call_type
    if model is None:
      provider_name = self.api_settings.get('provider', 'openai')
      provider_config = self.api_settings.get(provider_name, {})
      models = provider_config.get('models', {})

      # Map call_type to model
      if "master_profile" in call_type.lower():
        model = models.get('master_profile')
      elif "document" in call_type.lower():
        model = models.get('document')

      # Fallback to default model
      if not model:
        model = models.get('default', 'gpt-4o-mini-2024-07-18')

    if max_tokens is None:
      max_tokens = self.config.get_max_tokens_for_call_type(call_type)

    for attempt in range(self.max_retries):
      try:
        if attempt > 0:
          self.logger.warning(
            f"Retrying API call (attempt {attempt + 1}/{self.max_retries})"
          )

        start_time = perf_counter()

        # Use provider's structured call
        response = self.provider.call_llm_with_function(
          messages=messages,
          schema=function_schema,
          function_name=function_name,
          model=model,
          max_tokens=max_tokens,
          temperature=temperature,
          call_type=call_type
        )

        response_time = perf_counter() - start_time

        # Check success
        if not response.get('success', False):
          raise Exception(response.get('error', 'Function call failed'))

        # Extract usage and calculate cost
        function_args = response['function_args']
        usage = response['usage']
        provider_cost  = response['cost']

        # Calculate costs
        input_cost = self._calculate_input_cost(usage['prompt_tokens'], model)
        output_cost = self._calculate_output_cost(usage['completion_tokens'], model)
        total_cost = input_cost + output_cost

        self.total_cost += total_cost
        self.total_calls += 1
        self.total_tokens += usage['total_tokens']
        self.total_input_tokens += usage['prompt_tokens']
        self.total_output_tokens += usage['completion_tokens']

        # Log if there's a cost discrepancy
        if abs(total_cost - provider_cost) / max(total_cost, 0.0001) > 0.01:
          self.logger.warning(
            f"Cost discrepancy: APIClient=${total_cost:.6f} vs "
            f"Provider=${provider_cost:.6f}"
          )

        # Log API call details
        self.logger.debug("=" * 80)
        self.logger.debug(f"API call successful - {call_type}")
        self.logger.debug(f"  Model: {model}")
        self.logger.debug(f"  Tokens: {usage['prompt_tokens']} → {usage['completion_tokens']}")
        self.logger.debug(f"  Cost: ${total_cost:.6f}")
        self.logger.debug(f"  Time: {response_time:.2f}s")

        return {
          'success': True,
          'function_args': function_args,
          'usage': {
            'prompt_tokens': usage['prompt_tokens'],
            'completion_tokens': usage['completion_tokens'],
            'total_tokens': usage['total_tokens']
          },
          'cost': total_cost,  # Use our calculated cost
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
          return {
            'success': False,
            'error': str(e),
            'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
            'cost': 0.0
          }

      # Should never reach here, but just in case
    return {
      'success': False,
      'error': 'Max retries exceeded',
      'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
      'cost': 0.0
    }

  def _calculate_input_cost (self, tokens: int, model: str) -> float:
    """Calculate input token cost"""
    if 'gpt-4o-mini' in model:
      rate = self.pricing.get('gpt_4o_mini_input_cost_per_1k', 0.00015)
    elif 'gpt-5-nano' in model:
      rate = self.pricing.get('gpt_5_nano_input_cost_per_1k', 0.00005)
    else:
      rate = 0.00015
    return (tokens / 1000) * rate

  def _calculate_output_cost (self, tokens: int, model: str) -> float:
    """Calculate output token cost"""
    if 'gpt-4o-mini' in model:
      rate = self.pricing.get('gpt_4o_mini_output_cost_per_1k', 0.0006)
    elif 'gpt-5-nano' in model:
      rate = self.pricing.get('gpt_5_nano_output_cost_per_1k', 0.0004)
    else:
      rate = 0.0006
    return (tokens / 1000) * rate

  def get_cost_summary (self) -> Dict:
    """Get total cost and call statistics"""
    return self.provider.get_cost_summary()


class ClassLogger:
  """✨ Streamlined logging with structured JSON output mode"""

  def __init__ (self, config: ClassConfig, json_mode: bool = False):
    self.config = config
    self.log_settings = config.get_logging_settings()
    self.json_mode = json_mode  # ✨ JSON output mode

    # Initialize standard logger
    self.logger = self._setup_logger()

    # Debug configuration
    self.debug_options = self.log_settings.get('debug_options', {})
    self.show_api_prompts = self.debug_options.get('show_api_prompts', False)
    self.show_api_responses = self.debug_options.get('show_api_responses', False)
    self.max_prompt_chars = self.debug_options.get('max_prompt_chars', 2000)
    self.max_response_chars = self.debug_options.get('max_response_chars', 1000)

  def _setup_logger (self) -> logging.Logger:
    """Setup logging with both console and file handlers"""
    # Create logs directory
    logs_dir = self.config.script_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Create log filename with current date
    log_filename = f"{datetime.now().strftime('%Y%m%d')}_document_generator.log"
    log_file = logs_dir / log_filename

    # Setup logger
    logger = logging.getLogger("document_generator")
    logger.setLevel(getattr(logging, self.log_settings.get('level', 'INFO')))
    logger.handlers.clear()

    # File handler
    if self.log_settings.get('file_logging', True):
      file_handler = logging.FileHandler(log_file, encoding='utf-8')
      file_formatter = logging.Formatter(
        self.log_settings.get('file_format',
                              '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
      )
      file_handler.setFormatter(file_formatter)
      logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
      self.log_settings.get('console_format',
                            '%(asctime)s - %(levelname)s - %(message)s')
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

  def _json_output (self, event_type: str, data: Dict):
    """✨ Output structured JSON event"""
    event = {
      "timestamp": datetime.now().isoformat(),
      "event_type": event_type,
      **data
    }
    print(json.dumps(event), flush=True)

  def progress (self, stage: str, current: int, total: int, extra_data: Dict = None):
    """✨ Log progress through a stage"""
    if self.json_mode:
      data = {
        "stage": stage,
        "current": current,
        "total": total,
        "percentage": (current / total * 100) if total > 0 else 0
      }
      if extra_data:
        data.update(extra_data)
      self._json_output("progress", data)
    else:
      percentage = (current / total * 100) if total > 0 else 0
      self.logger.info(f"📊 Progress [{stage}]: {current}/{total} ({percentage:.1f}%)")

  def milestone (self, description: str, status: str = "info", data: Dict = None):
    """✨ Log major milestone completion"""
    if self.json_mode:
      milestone_data = {
        "description": description,
        "status": status
      }
      if data:
        milestone_data.update(data)
      self._json_output("milestone", milestone_data)
    else:
      status_emoji = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "🎯"}.get(status, "📌")
      self.logger.info(f"{status_emoji} MILESTONE: {description}")

  def stats (self, data: Dict):
    """✨ Log statistics/metrics"""
    if self.json_mode:
      self._json_output("stats", data)
    else:
      self.logger.info("📈 STATS:")
      for key, value in data.items():
        self.logger.info(f"  {key}: {value}")

  def debug_api_prompt (self, prompt: str, call_type: str = "API"):
    """Log API prompt if debug options allow"""
    if not self.debug_options.get('show_api_prompts', False):
      return

    max_chars = self.debug_options.get('max_prompt_chars', 0)
    display_prompt = prompt

    if max_chars > 0 and len(prompt) > max_chars:
      display_prompt = prompt[:max_chars] + f"\n... [truncated, {len(prompt)} total chars]"

    self.debug("=" * 80)
    self.debug(f"📤 DEBUG_API_PROMPT: PROMPT - {call_type}:")
    self.debug("")
    self.debug(display_prompt)

  def debug_api_response (self, response: str, call_type: str = "API"):
    """Log API response if debug options allow"""
    if not self.debug_options.get('show_api_responses', False):
      return

    max_chars = self.debug_options.get('max_response_chars', 0)
    display_response = response

    if max_chars > 0 and len(response) > max_chars:
      display_response = response[:max_chars] + f"\n... [truncated, {len(response)} total chars]"

    self.debug("=" * 80)
    self.debug(f"🤖 DEBUG_API_RESPONSE: RESPONSE - {call_type}:")
    self.debug("")
    self.debug(display_response)

  def info (self, message: str):
    if not self.json_mode:
      self.logger.info(message)

  def debug (self, message: str):
    if not self.json_mode:
      self.logger.debug(message)

  def warning (self, message: str):
    if self.json_mode:
      self._json_output("warning", {"message": message})
    else:
      self.logger.warning(message)

  def error (self, message: str):
    if self.json_mode:
      self._json_output("error", {"message": message})
    else:
      self.logger.error(message)

  def success (self, message: str):
    """Log success messages with special formatting"""
    if not self.json_mode:
      self.logger.info(f"✅ {message}")


class ClassTrackMetrics:
  """Track processing metrics: time, calls per minute, tokens per dollar"""

  def __init__ (self, logger: ClassLogger):
    self.logger = logger
    self.start_time = time.time()
    self.api_calls = 0
    self.total_cost = 0.0
    self.total_input_tokens = 0
    self.total_output_tokens = 0
    self.processing_times = {}
    self.cost_by_document_type = {}
    self.calls_by_document_type = {}

  def record_api_call (self, api_response: Dict, call_type: str = "general"):
    """Record API call metrics"""
    self.api_calls += 1

    # Extract token usage and cost
    usage = api_response.get('usage', {})
    self.total_input_tokens += usage.get('prompt_tokens', 0)
    self.total_output_tokens += usage.get('completion_tokens', 0)

    cost = api_response.get('cost', 0)
    self.total_cost += cost

    # Track by document type
    if call_type not in self.cost_by_document_type:
      self.cost_by_document_type[call_type] = 0
      self.calls_by_document_type[call_type] = 0

    self.cost_by_document_type[call_type] += cost
    self.calls_by_document_type[call_type] += 1

  def record_processing_time (self, task_name: str, duration: float):
    """Record processing time for a task"""
    self.processing_times[task_name] = duration

  def get_processing_rate (self) -> float:
    """Get tasks processed per minute"""
    elapsed_minutes = (time.time() - self.start_time) / 60
    return len(self.processing_times) / max(elapsed_minutes, 0.01)

  def get_api_rate (self) -> float:
    """Get API calls per minute"""
    elapsed_minutes = (time.time() - self.start_time) / 60
    return self.api_calls / max(elapsed_minutes, 0.01)

  def get_efficiency (self) -> float:
    """Get tokens per dollar efficiency"""
    total_tokens = self.total_input_tokens + self.total_output_tokens
    return total_tokens / max(self.total_cost, 0.001)


class ClassValidateInput:
  """Validates input files and data structures from Script 1"""

  def __init__ (self, logger: ClassLogger):
    self.logger = logger

  def validate_input_source (self, json_data: Dict) -> bool:
    """Validate that input comes from Script 1 (FHIR processor)"""
    # Update required keys to match actual Script 1 output
    required_keys = ['patient_metadata', 'encounters', 'processing_metadata']

    if not all(key in json_data for key in required_keys):
      return False

    # Check for FHIR processor metadata
    metadata = json_data.get('processing_metadata', {})
    if metadata.get('source_type') != 'fhir_processor':
      return False

    return True

  def validate_json_structure (self, json_data: Dict) -> bool:
    """Validate JSON structure is compatible with document generator"""
    try:
      if not isinstance(json_data, dict):
        self.logger.error("JSON data is not a dictionary")
        return False

      # Required fields - matching actual Script 1 output
      required_fields = ['claim_id', 'patient_initials', 'patient_metadata', 'encounters',
                         'processing_metadata']

      missing_fields = []
      for field in required_fields:
        if field not in json_data:
          missing_fields.append(field)

      if missing_fields:
        self.logger.error(f"Missing required fields: {missing_fields}")
        self.logger.info(f"Available fields: {list(json_data.keys())}")
        return False

      # Validate encounters structure
      encounters = json_data.get('encounters', [])
      if not isinstance(encounters, list):
        self.logger.error("'encounters' field is not a list")
        return False

      if not encounters:
        self.logger.error("No encounters found in JSON")
        return False

      # Check that encounters have the basic required structure
      for i, encounter in enumerate(encounters):
        if not isinstance(encounter, dict):
          self.logger.error(f"Encounter {i} is not a dictionary")
          return False

        required_encounter_fields = ['encounter_id', 'document_type', 'document_text']
        missing_encounter_fields = [field for field in required_encounter_fields if
                                    field not in encounter]

        if missing_encounter_fields:
          self.logger.error(f"Encounter {i} missing fields: {missing_encounter_fields}")
          return False

      self.logger.info(f"JSON structure validation passed - {len(encounters)} encounters found")
      return True

    except Exception as e:
      self.logger.error(f"JSON structure validation error: {e}")
      import traceback
      self.logger.error(f"Traceback: {traceback.format_exc()}")
      return False


class ClassExtractFeatures:
  """Extracts features from JSON data for document generation"""

  def __init__ (self, logger: ClassLogger):
    self.logger = logger

  def extract_features_from_json (self, json_data: Dict) -> Dict:
    """Extract comprehensive features for document generation"""
    try:
      features = {
        'patient_demographics': self._extract_patient_demographics(json_data),
        'medical_conditions': self._extract_medical_conditions(json_data),
        'treatment_summary': self._extract_treatments(json_data),
        'severity_indicators': self._extract_severity_indicators(json_data),
        'cost_implications': self._extract_cost_implications(json_data),
        'encounter_dates': self._extract_encounter_dates(json_data)
      }

      self.logger.debug(f"Extracted features: {len(features)} categories")
      return features

    except Exception as e:
      self.logger.error(f"Feature extraction failed: {e}")
      return {}

  def _extract_patient_demographics (self, json_data: Dict) -> Dict:
    """Extract patient demographic information"""
    patient_info = json_data.get('patient_metadata', {})
    return {
      'age': patient_info.get('age', 'Unknown'),
      'gender': patient_info.get('gender', 'Unknown'),
      'initials': json_data.get('patient_initials', 'XX')
    }

  def _extract_medical_conditions (self, json_data: Dict) -> List[str]:
    """Extract medical conditions from encounters"""
    conditions = set()
    encounters = json_data.get('encounters', [])

    for encounter in encounters:
      clinical_note = encounter.get('clinical_note', '')
      # Simple extraction - could be enhanced with NLP
      if 'fracture' in clinical_note.lower():
        conditions.add('fracture')
      if 'sprain' in clinical_note.lower():
        conditions.add('sprain')
      if 'strain' in clinical_note.lower():
        conditions.add('strain')
      if 'injury' in clinical_note.lower():
        conditions.add('injury')

    return list(conditions)[:5]

  def _extract_treatments (self, json_data: Dict) -> List[str]:
    """Extract treatment information"""
    treatments = set()
    encounters = json_data.get('encounters', [])

    for encounter in encounters:
      clinical_note = encounter.get('clinical_note', '')
      # Simple extraction
      if 'therapy' in clinical_note.lower():
        treatments.add('therapy')
      if 'medication' in clinical_note.lower():
        treatments.add('medication')
      if 'surgery' in clinical_note.lower():
        treatments.add('surgery')

    return list(treatments)[:3]

  def _extract_severity_indicators (self, json_data: Dict) -> List[str]:
    """Extract severity indicators"""
    indicators = []
    encounters = json_data.get('encounters', [])

    if len(encounters) > 5:
      indicators.append('multiple encounters')
    if len(encounters) > 10:
      indicators.append('complex case')

    return indicators[:2]

  def _extract_cost_implications (self, json_data: Dict) -> List[str]:
    """Extract cost-related information"""
    implications = []
    encounters = json_data.get('encounters', [])

    if len(encounters) > 3:
      implications.append('multiple treatments')

    return implications[:2]

  def _extract_encounter_dates (self, json_data: Dict) -> List[str]:
    """Extract encounter dates"""
    dates = []
    encounters = json_data.get('encounters', [])

    for encounter in encounters:
      date = encounter.get('encounter_date')
      if date:
        dates.append(date)

    return sorted(dates)[:3]


class ClassDocumentSchemas:
  """OpenAI function schemas for structured document generation"""

  def __init__ (self):
    """Initialize with realism instructions for all document types"""

    # Define base realism instructions that apply to all documents
    self.base_realism = """
- 1-3 minor typos: "teh", "recieve", "occured", "seperate"
- Industry acronyms: WC, BI, PD, ROM, EMG, MRI, PT, LOI (don't always define)
- Abbreviations: Dr., approx., pt., eval., Tx, Dx
- Date format variations: "January 15th" vs "01/15/2024" vs "1/15/24"
- Terminology inconsistencies: mix "patient"/"claimant" interchangeably
- Informal language where appropriate"""

    # Document-specific realism instructions
    self.doc_specific_realism = {
      "phone_transcript": """
- Speech disfluencies: "um", "uh", "you know", "like" (3-5 times total)
- Background artifacts: "[background noise]", "[muffled]", "(inaudible)"
- Interruptions: "[overlap]" or "[speaking over each other]"
- Incomplete thoughts trailing off with "..."
- Name misspellings corrected: "Jhonson... oh sorry, Johnson"
- Common mishearings of medical terminology initially clarified""",

      "adjuster_notes_initial": """
- Shorthand: "w/", "w/o", "approx", "est.", "re:"
- Time stamps: "10:30am spoke w/ clmt", "2:15pm reviewed file"
- Sentence fragments and bullet points mixed in narrative
- Quick documentation typos from rapid note-taking
- Acronyms: LOI, ROI, IME, QME, SIU (often undefined)
- References like "per phone call 1/15" or "email received"
- Inconsistent date/time formats throughout notes""",

      "medical_provider_letter": """
- Medical abbreviations: ROM, DTRs, WNL, NKA, NKDA
- Mix spelled-out and abbreviated terms inconsistently
- Occasional dictation transcription errors
- Latin terms: "per os", "prn", "bid", "qd"
- Some acronyms defined on first use, others assumed known
- Professional but with minor formatting inconsistencies""",

      "settlement_adjuster_notes": """
- Mix of narrative paragraphs and bullet points
- Financial abbreviations: "est.", "approx.", "~$"
- Calculation notes: "($500 x 12 visits = $6,000)"
- References to "prior notes" or "per file review"
- Shorthand: "w/", "w/o", "re:", "per"
- Industry terms: LOI, IME, QME, MMI without definition
- Inconsistent number formatting: "$1,500" vs "$1500" vs "1,500.00"
- Date references: "per 2/15 phone call" or "see 1/20 note" """,

      "claimant_statement": """
- Grammar errors proportional to education level in profile
- Run-on sentences when describing emotional moments
- Spelling mistakes on complex/medical terms
- Repetition for emphasis: "really, really hurt", "so so painful"
- Colloquial expressions and regional language
- Informal punctuation: excessive "!!!" or "..."
- Emotional language: "couldn't believe it", "was in so much pain"
- Varying detail levels (sometimes too much, sometimes too little)
- Stream of consciousness style in parts"""
    }

  def _get_realism_description (self, doc_type: str) -> str:
    """Build complete realism description for a specific document type"""
    specific = self.doc_specific_realism.get(doc_type, "")

    return f"""

REALISM REQUIREMENTS - Make this document feel authentic by including:

General realistic elements:
{self.base_realism}

Document-specific realistic elements:
{specific}

These imperfections should feel natural and authentic, not forced.""".strip()

  def get_master_profile_function (self):
    """Master profile function schema with structured validation"""
    return {
      "name": "generate_master_case_profile",
      "description": "Generate comprehensive master case profile with structured validation and narrative content",
      "parameters": {
        "type": "object",
        "properties": {
          "structured_elements": {
            "type": "object",
            "properties": {
              "basic_information": {
                "type": "object",
                "properties": {
                  "claimant_name": {"type": "string"},
                  "age": {"type": "number"},
                  "occupation": {"type": "string"},
                  "claim_number": {"type": "string"},
                  "policy_number": {"type": "string"},
                  "incident_date": {"type": "string"},
                  "reported_date": {"type": "string"}
                },
                "required": ["claimant_name", "age", "occupation"]
              },
              "incident_details": {
                "type": "object",
                "properties": {
                  "location": {"type": "string"},
                  "mechanism_of_injury": {"type": "string"},
                  "witnesses_present": {"type": "array", "items": {"type": "string"}},
                  "equipment_involved": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["location", "mechanism_of_injury"]
              },
              "medical_information": {
                "type": "object",
                "properties": {
                  "primary_injury": {"type": "string"},
                  "secondary_injuries": {"type": "array", "items": {"type": "string"}},
                  "treating_physicians": {"type": "array", "items": {"type": "string"}},
                  "initial_treatment": {"type": "string"}
                },
                "required": ["primary_injury"]
              },
              "timeline": {
                "type": "object",
                "properties": {
                  "incident_date": {"type": "string"},
                  "first_medical_treatment": {"type": "string"},
                  "key_milestones": {"type": "array", "items": {"type": "string"}},
                  "return_to_work_status": {"type": "string"},
                  "maximum_medical_improvement": {"type": "string"}
                },
                "required": ["incident_date", "first_medical_treatment"]
              }
            },
            "required": ["basic_information", "incident_details", "medical_information", "timeline"]
          },
          "validation_checks": {
            "type": "object",
            "properties": {
              "has_basic_information_section": {"type": "boolean"},
              "has_incident_details_section": {"type": "boolean"},
              "has_medical_information_section": {"type": "boolean"},
              "has_timeline_section": {"type": "boolean"},
              "content_length_adequate": {"type": "boolean"},
              "sections_internally_consistent": {"type": "boolean"}
            },
            "required": ["has_basic_information_section", "has_incident_details_section",
                         "has_medical_information_section", "has_timeline_section"]
          },
          "profile_content": {
            "type": "string",
            "description": "Complete master case profile text with all sections (minimum 800 characters)"
          }
        },
        "required": ["structured_elements", "validation_checks", "profile_content"]
      }
    }

  def get_document_function (self, doc_type: str):
    """Get function schema for specific document type"""
    schemas = {
      "phone_transcript": self._get_phone_transcript_function(),
      "adjuster_notes_initial": self._get_adjuster_notes_function(),
      "medical_provider_letter": self._get_medical_provider_function(),
      "settlement_adjuster_notes": self._get_settlement_notes_function(),
      "claimant_statement": self._get_claimant_statement_function()
    }
    return schemas.get(doc_type)

  def _get_phone_transcript_function (self):
    """Function schema for phone transcript generation"""
    realism_desc = self._get_realism_description("phone_transcript")

    return {
      "name": "generate_phone_transcript",
      "description": f"Generate a realistic phone transcript between insurance representative and claimant. {realism_desc}",
      "parameters": {
        "type": "object",
        "properties": {
          "document_content": {
            "type": "string",
            "description": "Full phone transcript with realistic conversation flow and imperfections (minimum 600 characters)"
          },
          "validation": {
            "type": "object",
            "properties": {
              "has_representative_dialogue": {"type": "boolean"},
              "has_claimant_dialogue": {"type": "boolean"},
              "includes_incident_description": {"type": "boolean"},
              "includes_injury_details": {"type": "boolean"},
              "content_length_adequate": {"type": "boolean"}
            }
          }
        },
        "required": ["document_content", "validation"]
      }
    }

  def _get_adjuster_notes_function (self):
    """Function schema for adjuster notes generation"""
    realism_desc = self._get_realism_description("adjuster_notes_initial")

    return {
      "name": "generate_adjuster_notes",
      "description": f"Generate realistic initial adjuster notes. {realism_desc}",
      "parameters": {
        "type": "object",
        "properties": {
          "document_content": {
            "type": "string",
            "description": "Complete adjuster notes with realistic shorthand and formatting (minimum 500 characters)"
          },
          "validation": {
            "type": "object",
            "properties": {
              "includes_claim_information": {"type": "boolean"},
              "includes_injury_assessment": {"type": "boolean"},
              "includes_initial_actions": {"type": "boolean"},
              "content_length_adequate": {"type": "boolean"}
            }
          }
        },
        "required": ["document_content", "validation"]
      }
    }

  def _get_medical_provider_function (self):
    """Function schema for medical provider letter generation"""
    realism_desc = self._get_realism_description("medical_provider_letter")

    return {
      "name": "generate_medical_provider_letter",
      "description": f"Generate a professional medical provider letter. {realism_desc}",
      "parameters": {
        "type": "object",
        "properties": {
          "document_content": {
            "type": "string",
            "description": "Complete medical letter with professional medical terminology (minimum 700 characters)"
          },
          "validation": {
            "type": "object",
            "properties": {
              "has_patient_information": {"type": "boolean"},
              "has_examination_findings": {"type": "boolean"},
              "has_treatment_plan": {"type": "boolean"},
              "has_prognosis": {"type": "boolean"},
              "content_length_adequate": {"type": "boolean"}
            }
          }
        },
        "required": ["document_content", "validation"]
      }
    }

  def _get_settlement_notes_function (self):
    """Function schema for settlement adjuster notes generation"""
    realism_desc = self._get_realism_description("settlement_adjuster_notes")

    return {
      "name": "generate_settlement_notes",
      "description": f"Generate settlement evaluation adjuster notes. {realism_desc}",
      "parameters": {
        "type": "object",
        "properties": {
          "document_content": {
            "type": "string",
            "description": "Complete settlement notes with financial calculations (minimum 600 characters)"
          },
          "validation": {
            "type": "object",
            "properties": {
              "includes_medical_summary": {"type": "boolean"},
              "includes_cost_breakdown": {"type": "boolean"},
              "includes_settlement_recommendation": {"type": "boolean"},
              "content_length_adequate": {"type": "boolean"}
            }
          }
        },
        "required": ["document_content", "validation"]
      }
    }

  def _get_claimant_statement_function (self):
    """Function schema for claimant statement generation"""
    realism_desc = self._get_realism_description("claimant_statement")

    return {
      "name": "generate_claimant_statement",
      "description": f"Generate a first-person claimant statement. {realism_desc}",
      "parameters": {
        "type": "object",
        "properties": {
          "document_content": {
            "type": "string",
            "description": "Complete first-person statement with emotional and factual elements (minimum 600 characters)"
          },
          "validation": {
            "type": "object",
            "properties": {
              "is_first_person": {"type": "boolean"},
              "includes_incident_narrative": {"type": "boolean"},
              "includes_personal_impact": {"type": "boolean"},
              "content_length_adequate": {"type": "boolean"}
            }
          }
        },
        "required": ["document_content", "validation"]
      }
    }


class ClassGenerateProfile:
  """Generates master case profile using function calling"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger, api_client: ClassAPIClient):
      self.config = config
      self.logger = logger

      # Use shared APIClient if provided, otherwise create one
      if api_client:
        self.api_client = api_client

      self.generation_settings = config.get_document_generation_settings().get('master_profile', {})
      self.validation_settings = config.get_validation_settings()

      self.schemas = ClassDocumentSchemas()

  def generate_master_profile (self, features: Dict) -> Tuple[str, float]:
    """Generate master case profile using function calling"""
    self.logger.info("Generating master case profile...")

    # Build prompt
    prompt = self._build_master_profile_prompt(features)


    # Get function schema
    function_schema = self.schemas.get_master_profile_function()

    # Get settings from config (NOT hard-coded)
    max_tokens = self.config.get_max_tokens_for_call_type('master_profile')
    temperature = self.config.get_temperature_for_call_type('master_profile')

    # Make API call with function calling
    response = self.api_client.call_llm_with_function(
      messages=[
        {"role": "system",
         "content": "Generate comprehensive master case profiles for insurance claims."},
        {"role": "user",
         "content": prompt}
      ],
      function_schema=function_schema,
      function_name="generate_master_case_profile",
      max_tokens=max_tokens,
      temperature=temperature,
      call_type="master_profile_generation"
    )

    if not response.get('success'):
      error_msg = response.get('error', 'Unknown error')
      self.logger.error(f"Master profile generation failed: {error_msg}")
      raise ValueError(f"Master profile generation failed: {error_msg}")

    # Extract function arguments
    function_args = response['function_args']
    cost = response['cost']

    # Extract model info for metadata
    model_info = {
      'model': response.get('model', 'unknown'),
      'response_time': response.get('response_time', 0),
      'provider': self.config.get_api_settings().get('provider', 'unknown'),
      'tokens': response.get('usage', {})
    }

    # Extract and validate profile content
    profile_content = function_args.get('profile_content', '')

    # Debug log response
    self.logger.debug_api_response(profile_content, "Parsed Master Profile")

    # Validate profile
    if not self._validate_master_profile(function_args, profile_content):
      raise ValueError("Master profile validation failed")

    self.logger.success(f"Master profile generated (Cost: ${cost:.4f})")

    return (profile_content, cost, model_info)

  def _build_master_profile_prompt (self, features: Dict) -> str:
    """Build prompt for master profile generation"""
    patient_demographics = features.get('patient_demographics', {})
    medical_conditions = features.get('medical_conditions', [])
    treatments = features.get('treatment_summary', [])

    return f"""Create a comprehensive master case profile for this claim:

Patient Demographics:
- Age: {patient_demographics.get('age', 'Unknown')}
- Gender: {patient_demographics.get('gender', 'Unknown')}
- Initials: {patient_demographics.get('initials', 'XX')}

Medical Conditions: {', '.join(medical_conditions) if medical_conditions else 'General injury'}
Treatments: {', '.join(treatments) if treatments else 'Standard medical care'}
Severity Level: {', '.join(features.get('severity_indicators', [])[:2])}
Cost Information: {', '.join(features.get('cost_implications', [])[:2])}
Encounter Dates: {', '.join(features.get('encounter_dates', [])[:2])}

Generate a detailed, comprehensive profile (minimum 800 characters) including:
1. Basic Information (full name, age, occupation, marital status, claim number)
2. Incident Details (specific location, date/time, detailed mechanism of injury, witnesses, equipment/environment)
3. Medical Information (specific injuries with medical terminology, treating physicians, initial treatment details, ongoing care)
4. Timeline (incident date, first treatment date, key treatment milestones, return to work date/restrictions, MMI date)

Make the profile realistic, detailed, and internally consistent. Include specific dates, names, and medical details."""

  def _validate_master_profile (self, function_args: Dict, profile_content: str) -> bool:
    """
    Validate generated master profile based on content quality
    Uses generation settings from config
    """
    # Get minimum length from generation config (where it's actually defined)
    min_length = self.generation_settings.get('min_content_length', 800)

    # Check minimum length
    if len(profile_content) < min_length:
      self.logger.warning(f"Master profile too short: {len(profile_content)} chars (minimum: {min_length})")
      return False

    # Check for reasonable word count (minimum ~100 words = ~500 chars / 5)
    min_words = min_length // 5
    if len(profile_content.split()) < min_words:
      self.logger.warning(f"Profile content seems too brief (less than {min_words} words)")
      return False

    # Check for required content markers (flexible validation)
    required_content_markers = [
      'age', 'occupation',  # Basic info
      'incident', 'injury',  # Incident details
      'treatment', 'medical',  # Medical info
      'date'  # Timeline
    ]

    content_lower = profile_content.lower()
    missing_markers = [marker for marker in required_content_markers if marker not in content_lower]
    found_markers = len(required_content_markers) - len(missing_markers)

    if found_markers < 6:  # Need at least 6 out of 7
      missing_str = ", ".join(missing_markers)
      self.logger.warning(
        f"Profile content missing key information "
        f"(only {found_markers}/7 markers found). "
        f"Missing markers: {missing_str}"
      )
      return False

    # Check for obvious placeholders
    placeholder_indicators = ["[placeholder]", "xxx", "tbd", "to be determined", "insert"]
    if any(placeholder in content_lower for placeholder in placeholder_indicators):
      self.logger.warning("Profile content contains placeholder text")
      return False

    return True


class ClassGenerateDocuments:
  """Generates individual documents using function calling"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger, api_client: ClassAPIClient):
    self.config = config
    self.logger = logger
    self.api_client = api_client
    self.schemas = ClassDocumentSchemas()

    # Document generation settings
    self.document_settings = config.get_document_generation_settings()
    self.validation_settings = config.get_validation_settings()

    # Document-specific prompts
    self.document_prompts = {
      "phone_transcript": """Generate a phone transcript of the initial call between the insurance representative and the claimant. Include conversational dialogue, incident description, injury details, and next steps discussion. Use natural conversation flow with realistic speech patterns.""",
      "adjuster_notes_initial": """Generate initial adjuster notes documenting the first review of this claim. Include claim information, injury assessment, liability evaluation, initial actions taken, and next steps. Use professional adjuster terminology and shorthand.""",
      "medical_provider_letter": """Generate a letter from the treating physician to the insurance adjuster. Include professional medical correspondence format, clinical summary, examination findings, treatment plan, prognosis, and work restrictions. Use appropriate medical terminology.""",
      "settlement_adjuster_notes": """Generate adjuster notes for settlement evaluation. Include medical treatment summary, total expenses calculation, wage loss analysis, settlement analysis, negotiation strategy, and settlement authority recommendation.""",
      "claimant_statement": """Generate a first-person written statement from the claimant describing the incident. Include first-person narrative, detailed incident description, personal impact on daily life and work, and emotional/factual tone appropriate for a claimant statement."""
    }

  def generate_document (self, master_profile: str, doc_type: str, features: Dict = None) -> \
  Optional[Dict]:
    """Generate document using function calling with validation"""
    self.logger.info(f"Generating {DOCUMENT_TYPES.get(doc_type, doc_type)}")

    try:
      # Get function schema
      function_schema = self.schemas.get_document_function(doc_type)
      if not function_schema:
        self.logger.error(f"No function schema available for {doc_type}")
        return None

      # Build prompt
      prompt = self._build_document_prompt(master_profile, doc_type)

      # Get document-specific settings
      max_tokens = self.config.get_max_tokens_for_call_type(doc_type)
      temperature = self.config.get_temperature_for_call_type(doc_type)

      # Make function call using the shared API client method
      response = self.api_client.call_llm_with_function(
        messages=[
          {"role": "system",
           "content": f"Generate realistic {DOCUMENT_TYPES.get(doc_type, doc_type)} documents for insurance claims."},
          {"role": "user", "content": prompt}
        ],
        function_schema=function_schema,
        function_name=function_schema["name"],
        max_tokens=max_tokens,
        temperature=temperature,  # From config
        call_type=f"document_{doc_type}_generation"
      )

      # Check if call succeeded
      if not response['success']:
        raise ValueError(f"API call failed: {response.get('error', 'Unknown error')}")

      # Extract function arguments and usage
      function_args = response['function_args']
      cost = response['cost']

      # Extract model info for metadata
      model_info = {
        'model': response.get('model', 'unknown'),
        'response_time': response.get('response_time', 0),
        'provider': self.config.get_api_settings().get('provider', 'unknown'),
        'tokens': response.get('usage', {})
      }

      # Calculate cost
      usage = response['usage']
      model = self.api_client.api_settings.get('default_model', 'gpt-4o-mini-2024-07-18')
      input_cost = self.api_client._calculate_input_cost(usage['prompt_tokens'], model)
      output_cost = self.api_client._calculate_output_cost(usage['completion_tokens'], model)
      cost = input_cost + output_cost
      self.api_client.total_cost += cost
      self.api_client.total_calls += 1

      # Debug log response
      self.logger.debug_api_response(json.dumps(function_args, indent=2), "Parsed " + doc_type)

      # Extract document content
      document_content = function_args.get("document_content", "")

      if self._validate_document_content(document_content, doc_type):
        self.logger.success(f"{doc_type} generated (Cost: ${cost:.4f})")
        return {
          'content': document_content,
          'cost': cost,
          'method': 'function_calling',
          'doc_type': doc_type,
          'model_info': model_info  # Include model info
        }
      else:
        raise ValueError(f"Document validation failed for {doc_type}")

    except Exception as e:
      self.logger.error(f"Document generation failed for {doc_type}: {e}")
      return None

  def _build_document_prompt (self, master_profile: str, doc_type: str) -> str:
    """Build prompt for document generation"""
    base_prompt = self.document_prompts.get(doc_type, "Generate a document.")

    return f"""{base_prompt}

Using this established case profile:

{master_profile}

Generate the complete document content ensuring all details match the case profile exactly."""

  def _validate_document_content(self, content: str, doc_type: str) -> bool:
    """Validate generated document content using validation config"""
    # Get minimum length from validation config
    doc_min_lengths = self.validation_settings.get('document_min_lengths', {})
    min_length = doc_min_lengths.get(doc_type, 200)

    if not content or len(content) < min_length:
      self.logger.warning(f"Document content too short for {doc_type}: {len(content)} chars (minimum: {min_length})")
      return False

    # Check for required elements from config
    required_elements_config = self.validation_settings.get('required_elements', {})
    required_elements = required_elements_config.get(doc_type, [])

    if required_elements:
      content_lower = content.lower()
      missing_elements = [element for element in required_elements if element.lower() not in content_lower]
      found_elements = len(required_elements) - len(missing_elements)
      required_count = max(len(required_elements) - 1, 1)  # Allow missing 1 element

      if found_elements < required_count:
        missing_str = ", ".join(missing_elements)
        self.logger.warning(
          f"{doc_type} missing required elements "
          f"(found {found_elements}/{len(required_elements)}, need {required_count}). "
          f"Missing elements: {missing_str}"
        )
        return False

    return True


class ClassProcessDocuments:
  """✨ Main processor with progress tracking and milestones"""

  def __init__ (self, config: ClassConfig, logger: ClassLogger):
    self.config = config
    self.logger = logger

    # Initialize infrastructure
    self.api_client = ClassAPIClient(config, logger)
    self.metrics = ClassTrackMetrics(logger)

    # Initialize processing components
    self.input_validator = ClassValidateInput(logger)
    self.feature_extractor = ClassExtractFeatures(logger)

    self.master_profile_generator = ClassGenerateProfile(config, logger,
                                                         self.api_client)
    self.document_generator = ClassGenerateDocuments(config, logger, self.api_client)

    # Processing settings
    self.processing_settings = config.get_processing_settings()

    # Statistics tracking
    self.stats = {
      "files_processed": 0,
      "files_successful": 0,
      "files_failed": 0,
      "documents_generated": 0,
      "documents_skipped": 0,
      "total_cost": 0.0,
      "total_api_calls": 0,
      "token_usage": {
        "total_input": 0,
        "total_output": 0,
        "total_usage": 0,
        "by_document_type": {}
      },
      "cost_by_document_type": {**{doc_type: 0.0 for doc_type in DOCUMENT_TYPES.keys()},
                                "master_profile": 0.0},
      "processing_times": {},
      "generation_success_rates": {doc_type: {"successful": 0, "attempted": 0} for doc_type in
                                   DOCUMENT_TYPES.keys()}
    }

  """
  Complete record_token_usage() method for Script 2
  Add this to the SyntheticDocumentProcessor class in 2_data-add_documents.py
  """

  def record_token_usage (self, usage: Dict, doc_type: str):
    """
    Record token usage for tracking and reporting with business context

    Args:
        usage: Dictionary with token usage information
               Expected keys: 'prompt_tokens', 'completion_tokens', 'total_tokens'
        doc_type: Document type identifier (e.g., 'master_profile', 'phone_transcript')
    """
    # Extract token counts from usage dict
    input_tokens = usage.get('prompt_tokens', 0)
    output_tokens = usage.get('completion_tokens', 0)
    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)

    # Update global totals
    self.stats["token_usage"]["total_input"] += input_tokens
    self.stats["token_usage"]["total_output"] += output_tokens
    self.stats["token_usage"]["total_usage"] += total_tokens

    # Initialize document type tracking if first time
    if doc_type not in self.stats["token_usage"]["by_document_type"]:
      self.stats["token_usage"]["by_document_type"][doc_type] = {
        "input": 0,
        "output": 0,
        "total": 0
      }

    # Update document type specific totals
    self.stats["token_usage"]["by_document_type"][doc_type]["input"] += input_tokens
    self.stats["token_usage"]["by_document_type"][doc_type]["output"] += output_tokens
    self.stats["token_usage"]["by_document_type"][doc_type]["total"] += total_tokens

    # Track API call count
    self.stats["total_api_calls"] += 1

    # Optional: Log token usage for debugging (only in debug mode)
    if self.logger.logger.level == 10:  # DEBUG level
      self.logger.debug(
        f"Token usage recorded for {doc_type}: "
        f"{input_tokens} → {output_tokens} (total: {total_tokens})"
      )

  def find_json_files (self, input_dir: str) -> List[str]:
    """Find FHIR processor JSON files in input directory"""
    script_dir = Path(__file__).parent.resolve()

    if Path(input_dir).is_absolute():
      input_path = Path(input_dir)
    else:
      input_path = script_dir / input_dir

    if not input_path.exists():
      self.logger.error(f"Input directory does not exist: {input_path}")
      return []

    # Find JSON files
    json_files = list(input_path.glob("*.json"))

    # Filter for FHIR processor output files
    valid_files = []
    for json_file in json_files:
      try:
        with open(json_file, 'r', encoding='utf-8') as f:
          data = json.load(f)
        if self.input_validator.validate_input_source(data):
          valid_files.append(str(json_file))
      except Exception as e:
        self.logger.warning(f"Skipping invalid JSON file {json_file}: {e}")

    self.logger.info(f"Found {len(valid_files)} valid FHIR processor files")
    return valid_files

  def check_existing_documents (self, json_data: Dict) -> List[str]:
    """Check which document types already exist in the JSON"""
    existing_types = set()

    encounters = json_data.get("encounters", [])
    for encounter in encounters:
      doc_type = encounter.get("document_type", "")
      if doc_type in DOCUMENT_TYPES:
        existing_types.add(doc_type)

    return list(existing_types)

  def determine_documents_to_generate (self, json_data: Dict) -> List[str]:
    """Determine which document types need to be generated"""
    # Get existing document types from encounters
    existing_types = set()
    for encounter in json_data.get("encounters", []):
      if "document_type" in encounter:
        existing_types.add(encounter["document_type"])

    # Generate missing document types
    all_types = set(DOCUMENT_TYPES.keys())
    missing_types = all_types - existing_types

    return list(missing_types)

  def create_encounter_entry (self, doc_type: str, document_content: str,
                              model_info: Dict = None) -> Dict:
    """Create encounter entry with generation metadata"""

    entry = {
      "date": datetime.now().isoformat(),
      "type": "other_text_data",
      "document_type": doc_type,
      "document_text": document_content
    }

    # Add generation metadata if model_info provided
    if model_info:
      entry["generation_metadata"] = {
        "generated_timestamp": datetime.now().isoformat(),
        "generator": "synthetic_document_generator",
        "document_display_name": DOCUMENT_TYPES[doc_type],
        "generation_method": "function_calling",
        "model_name": model_info.get("model", "unknown"),
        "provider": model_info.get("provider", "unknown"),
        "response_time": model_info.get("response_time", 0),
        "tokens": model_info.get("tokens", {})
      }

    return entry

  def process_json_file (self, file_path: Path, output_dir: str) -> Dict:
    """✨ ENHANCED: Process a single JSON file with progress tracking"""
    start_time = perf_counter()

    self.logger.info(f"Processing file: {file_path.name}")

    # Initialize file result structure
    file_result = {
      "file": str(file_path),
      "success": False,
      "errors": [],
      "documents_generated": {},
      "documents_skipped": [],
      "processing_time": 0.0,
      "cost": 0.0,
      "generation_methods": {}
    }

    try:
      # Load and validate JSON file
      with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

      # Validate input structure
      if not self.input_validator.validate_json_structure(json_data):
        raise ValueError("Invalid JSON structure")

      # Extract features for master profile
      features = self.feature_extractor.extract_features_from_json(json_data)
      if not features:
        raise ValueError("No features could be extracted")

      # ✨ Generate master profile with milestone
      master_profile_start = perf_counter()
      master_profile, profile_cost, master_profile_model_info = self.master_profile_generator.generate_master_profile(features)
      profile_time = perf_counter() - master_profile_start

      self.stats["cost_by_document_type"]["master_profile"] += profile_cost
      self.stats["processing_times"]["master_profile"] = profile_time
      file_result["cost"] += profile_cost

      # Record token usage for master profile
      profile_usage = self.api_client.provider.get_cost_summary()
      if 'total_input_tokens' in profile_usage:
        usage_dict = {
          'prompt_tokens': profile_usage['total_input_tokens'],
          'completion_tokens': profile_usage['total_output_tokens'],
          'total_tokens': profile_usage['total_tokens']
        }
        self.record_token_usage(usage_dict, "master_profile")

      # ✨ Master profile completion milestone
      self.logger.milestone(
        "Master profile generated",
        status="success",
        data={"time": f"{profile_time:.2f}s", "cost": f"${profile_cost:.4f}"}
      )

      # Check existing documents
      existing_docs = self.check_existing_documents(json_data)

      # Determine documents to generate
      documents_to_generate = self.determine_documents_to_generate(json_data)

      # Track skipped documents
      for doc_type in DOCUMENT_TYPES.keys():
        if doc_type in existing_docs:
          file_result["documents_skipped"].append(doc_type)
          self.stats["documents_skipped"] += 1
          self.logger.info(f"Skipping {DOCUMENT_TYPES[doc_type]} - already exists")

      if not documents_to_generate:
        self.logger.warning("No documents to generate - all documents already exist!")
        file_result["success"] = True
        processing_time = perf_counter() - start_time
        file_result["processing_time"] = processing_time
        self.stats["files_processed"] += 1
        self.stats["files_successful"] += 1
        return file_result

      # ✨ Start document generation with progress tracking
      generated_encounters = []
      total_docs = len(documents_to_generate)

      self.logger.milestone(
        f"Starting document generation - {total_docs} documents",
        status="info",
        data={"document_types": documents_to_generate}
      )

      for i, doc_type in enumerate(documents_to_generate):
        doc_start_time = perf_counter()

        # ✨ Progress update
        self.logger.progress(
          "document_generation",
          current=i + 1,
          total=total_docs,
          extra_data={"document_type": doc_type}
        )

        try:
          # Track attempt
          if "generation_success_rates" in self.stats and doc_type in self.stats[
            "generation_success_rates"]:
            self.stats["generation_success_rates"][doc_type]["attempted"] += 1

            # Generate document
            document_result = self.document_generator.generate_document(
              master_profile, doc_type, features
            )
            doc_time = perf_counter() - doc_start_time

            if document_result:
              # Extract results
              document_content = document_result['content']
              doc_cost = document_result['cost']
              generation_method = document_result.get('method', 'function_calling')

              # Extract model info if available
              model_info = document_result.get('model_info', {
                'model': document_result.get('model', 'unknown'),
                'response_time': document_result.get('response_time', 0),
                'provider': self.config.get_api_settings().get('provider', 'unknown'),
                'tokens': document_result.get('usage', {})
              })

              # Record token usage for this document
              if 'model_info' in document_result and 'tokens' in document_result['model_info']:
                self.record_token_usage(document_result['model_info']['tokens'], doc_type)

              # Update tracking
              self.stats["cost_by_document_type"][doc_type] += doc_cost
              self.stats["processing_times"][doc_type] = doc_time
              if "generation_success_rates" in self.stats and doc_type in self.stats[
                "generation_success_rates"]:
                self.stats["generation_success_rates"][doc_type]["successful"] += 1
              self.stats["documents_generated"] += 1

              file_result["cost"] += doc_cost
              file_result["documents_generated"][doc_type] = "Success"
              file_result["generation_methods"][doc_type] = generation_method

              # Create encounter entry WITH MODEL INFO
              encounter_entry = self.create_encounter_entry(
                doc_type, document_content, model_info
              )
              generated_encounters.append(encounter_entry)

              # Logging
              self.logger.milestone(
                f"{DOCUMENT_TYPES[doc_type]} generated",
                status="success",
                data={
                  "time": f"{doc_time:.2f}s",
                  "cost": f"${doc_cost:.4f}",
                  "length": len(document_content),
                  "model": model_info.get('model', 'unknown')
                }
              )

            else:
              file_result["documents_generated"][doc_type] = "Failed"
              error_msg = f"Document generation returned None for {doc_type}"
              file_result["errors"].append(error_msg)
              self.logger.error(error_msg)

        except Exception as e:
              error_msg = f"Failed to generate {doc_type}: {e}"
              self.logger.error(error_msg)
              file_result["errors"].append(error_msg)
              file_result["documents_generated"][doc_type] = "Failed"

      # Add generated documents to JSON
      if generated_encounters:
        json_data["encounters"].extend(generated_encounters)

        # Update metadata
        if "processing_metadata" not in json_data:
          json_data["processing_metadata"] = {}

        json_data["processing_metadata"]["synthetic_documents_added"] = {
          "timestamp": datetime.now().isoformat(),
          "generator": "synthetic_document_generator",
          "documents_added": len(generated_encounters),
          "total_encounters": len(json_data["encounters"])
        }

      # Create output directory relative to script location
      script_dir = Path(__file__).parent.resolve()

      if Path(output_dir).is_absolute():
        output_path = Path(output_dir)
      else:
        output_path = script_dir / output_dir

      output_path.mkdir(parents=True, exist_ok=True)

      # Create output filename
      original_name = file_path.stem
      if "_with_other_text_data" in original_name:
        output_filename = f"{original_name}.json"
      else:
        output_filename = f"{original_name}_with_other_text_data.json"
      output_file = output_path / output_filename

      with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

      file_result["output_file"] = str(output_file)
      file_result["success"] = True

      # Calculate file-specific cost
      file_cost = sum([
        self.stats["cost_by_document_type"]["master_profile"],
        sum(self.stats["cost_by_document_type"][doc_type] for doc_type in documents_to_generate)
      ])
      file_result["cost"] = file_cost

      processing_time = perf_counter() - start_time
      file_result["processing_time"] = processing_time

      # ✨ File completion milestone
      self.logger.milestone(
        f"File processing complete: {file_path.name}",
        status="success",
        data={
          "documents_generated": len(generated_encounters),
          "documents_skipped": len(file_result['documents_skipped']),
          "time": f"{processing_time:.2f}s",
          "cost": f"${file_cost:.4f}"
        }
      )

      return file_result

    except Exception as e:
      error_msg = f"File processing failed: {e}"
      self.logger.error(error_msg)
      file_result["errors"].append(error_msg)
      file_result["success"] = False

      # ✨ Error milestone
      self.logger.milestone(
        f"File processing failed: {file_path.name}",
        status="error",
        data={"error": str(e)}
      )

      return file_result

  def process_batch (self, input_dir: str, output_dir: str, limit: Optional[int] = None) -> Dict:
    """✨ ENHANCED: Process batch of files with progress tracking"""
    start_time = perf_counter()

    # ✨ Batch start milestone
    self.logger.milestone("Starting batch processing", status="info", data={"input_dir": input_dir})

    # Find files
    json_files = self.find_json_files(input_dir)

    if not json_files:
      self.logger.error("No valid JSON files found")
      return {
        "summary": {
          "total_files": 0,
          "successful": 0,
          "failed": 0
        },
        "processed_files": []
      }

    # Apply limit if specified
    if limit and limit > 0:
      json_files = json_files[:limit]
      self.logger.info(f"Limiting processing to {limit} files")

    total_files = len(json_files)
    processed_files = []

    # ✨ Process files with progress tracking
    for i, json_file in enumerate(json_files):
      self.logger.progress(
        "batch_processing",
        current=i + 1,
        total=total_files,
        extra_data={"file": Path(json_file).name}
      )

      file_result = self.process_json_file(Path(json_file), output_dir)
      processed_files.append(file_result)

      if file_result["success"]:
        self.stats["files_successful"] += 1
      else:
        self.stats["files_failed"] += 1

      self.stats["files_processed"] += 1
      self.stats["total_cost"] += file_result.get("cost", 0)

    # Calculate summary
    total_processing_time = perf_counter() - start_time

    batch_results = {
      "summary": {
        "total_files": total_files,
        "successful": self.stats["files_successful"],
        "failed": self.stats["files_failed"],
        "documents_generated": self.stats["documents_generated"],
        "documents_skipped": self.stats["documents_skipped"],
        "total_cost": self.stats["total_cost"],
        "token_usage": self.stats["token_usage"],  # ← ADD: Include token usage
        "cost_by_document_type": self.stats["cost_by_document_type"],
        "processing_times": self.stats["processing_times"],
        "generation_success_rates": self.stats["generation_success_rates"],
        "total_processing_time": total_processing_time
      },
      "processed_files": processed_files
    }

    # Save processing report
    self._save_processing_report(batch_results, output_dir)

    # ✨ Batch completion milestone
    self.logger.milestone(
      "Batch processing complete",
      status="success",
      data={
        "total_files": total_files,
        "successful": self.stats["files_successful"],
        "failed": self.stats["files_failed"],
        "documents_generated": self.stats["documents_generated"],
        "total_cost": f"${self.stats['total_cost']:.4f}",
        "total_time": f"{total_processing_time:.2f}s"
      }
    )

    return batch_results

  def print_batch_summary (self, batch_results: Dict):
    """Print batch processing summary with token usage"""
    summary = batch_results.get("summary", {})

    self.logger.info("=" * 60)
    self.logger.info("BATCH PROCESSING SUMMARY")
    self.logger.info(f"📁 Total files: {summary.get('total_files', 0)}")
    self.logger.info(f"✅ Successful: {summary.get('successful', 0)}")
    self.logger.info(f"❌ Failed: {summary.get('failed', 0)}")
    self.logger.info(f"📄 Documents generated: {summary.get('documents_generated', 0)}")
    self.logger.info(f"⏭️  Documents skipped: {summary.get('documents_skipped', 0)}")
    self.logger.info(f"💰 Total cost: ${summary.get('total_cost', 0):.4f}")
    self.logger.info(f"⏱️  Total time: {summary.get('total_processing_time', 0):.2f}s")

    # Token usage summary section
    token_usage = summary.get('token_usage', {})
    if token_usage and token_usage.get('total_usage', 0) > 0:
      self.logger.info("─" * 60)
      self.logger.info("🎯 Token Usage:")

      total_input = token_usage.get('total_input', 0)
      total_output = token_usage.get('total_output', 0)
      total_usage = token_usage.get('total_usage', 0)
      total_calls = self.stats.get('total_api_calls', 1)
      total_cost = summary.get('total_cost', 0.0001)

      self.logger.info(f"  Total tokens: {total_usage:,} ({total_input:,} → {total_output:,})")
      self.logger.info(f"  Input tokens: {total_input:,}")
      self.logger.info(f"  Output tokens: {total_output:,}")
      self.logger.info(f"  Avg tokens/call: {total_usage // max(total_calls, 1):,}")
      self.logger.info(f"  Tokens per dollar: {int(total_usage / total_cost):,}")

    # Cost breakdown
    cost_by_type = summary.get('cost_by_document_type', {})
    if cost_by_type:
      self.logger.info("─" * 60)
      self.logger.info("💵 Cost by Document Type:")
      for doc_type, cost in cost_by_type.items():
        if cost > 0:
          doc_name = DOCUMENT_TYPES.get(doc_type, doc_type.replace('_', ' ').title())
          self.logger.info(f"  {doc_name}: ${cost:.4f}")

    # Token usage by document type section
    if token_usage and 'by_document_type' in token_usage:
      by_doc_type = token_usage['by_document_type']
      if by_doc_type:
        self.logger.info("─" * 60)
        self.logger.info("🎯 Token Usage by Document Type:")

        for doc_type, tokens in by_doc_type.items():
          if tokens.get('total', 0) > 0:
            doc_name = DOCUMENT_TYPES.get(doc_type, doc_type.replace('_', ' ').title())
            input_tok = tokens.get('input', 0)
            output_tok = tokens.get('output', 0)
            total_tok = tokens.get('total', 0)
            self.logger.info(f"  {doc_name}: {total_tok:,} ({input_tok:,} → {output_tok:,})")

    # Success rates
    success_rates = summary.get("generation_success_rates", {})
    if success_rates:
      self.logger.info("─" * 60)
      self.logger.info("📈 Document Generation Success Rates:")
      for doc_type, rates in success_rates.items():
        if rates["attempted"] > 0:
          rate = (rates["successful"] / rates["attempted"]) * 100
          doc_name = DOCUMENT_TYPES.get(doc_type, doc_type.replace('_', ' ').title())
          self.logger.info(
            f"  {doc_name}: {rates['successful']}/{rates['attempted']} ({rate:.1f}%)")

    self.logger.info("=" * 60)

  def _save_processing_report (self, batch_results: Dict, output_dir: str):
    """Save detailed processing report to JSON file"""

    try:
      # Make output_dir relative to script location
      script_dir = Path(__file__).parent.resolve()
      if Path(output_dir).is_absolute():
        output_path = Path(output_dir)
      else:
        output_path = script_dir / output_dir

      # Create reports subdirectory
      reports_dir = output_path / "reports"
      reports_dir.mkdir(parents=True, exist_ok=True)

      # Generate report filename with timestamp
      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
      report_file = reports_dir / f"2_data-add_documents-report_{timestamp}.json"

      # Build comprehensive report
      summary = batch_results["summary"]
      processed_files = batch_results.get("processed_files", [])

      report = {
        "report_type": "synthetic_document_generation",
        "timestamp": timestamp,
        "processing_summary": {
          "total_files": summary.get("total_files", 0),
          "successful_files": summary.get("successful", 0),
          "failed_files": summary.get("failed", 0),
          "success_rate": (summary.get("successful", 0) / max(summary.get("total_files", 1),
                                                              1)) * 100,
          "total_processing_time": summary.get("total_processing_time", 0),
          "documents_generated": summary.get("documents_generated", 0)
        },
        "cost_analysis": {
          "total_cost": summary.get("total_cost", 0),
          "cost_by_document_type": summary.get("cost_by_document_type", {}),
          "average_cost_per_file": summary.get("total_cost", 0) / max(summary.get("total_files", 1),
                                                                      1)
        },
        "performance_metrics": {
          "processing_times": summary.get("processing_times", {}),
          "generation_success_rates": summary.get("generation_success_rates", {}),
          "files_per_minute": (summary.get("total_files", 0) / max(
            summary.get("total_processing_time", 1), 1)) * 60,
          "documents_per_minute": (summary.get("documents_generated", 0) / max(
            summary.get("total_processing_time", 1), 1)) * 60
        },
        "file_details": [
          {
            "file": f.get("file", "unknown"),
            "success": f.get("success", False),
            "documents_generated": f.get("documents_generated", {}),
            "documents_skipped": f.get("documents_skipped", []),
            "processing_time": f.get("processing_time", 0),
            "cost": f.get("cost", 0),
            "errors": f.get("errors", [])
          }
          for f in processed_files
        ],
        "statistics": {
          "total_documents_attempted": sum(
            len(f.get("documents_generated", {})) + len(f.get("documents_skipped", []))
            for f in processed_files
          ),
          "total_documents_generated": sum(
            len([doc for doc in f.get("documents_generated", {}).values() if doc == "Success"])
            for f in processed_files
          ),
          "total_documents_failed": sum(
            len([doc for doc in f.get("documents_generated", {}).values() if doc == "Failed"])
            for f in processed_files
          )
        }
      }

      # Save report
      with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

      self.logger.info(f"Processing report saved: {report_file}")
      return str(report_file)

    except Exception as e:
      self.logger.error(f"Failed to save processing report: {e}")
      return None


# MAIN EXECUTION AND CLI SETUP

def setup_argument_parser () -> argparse.ArgumentParser:
  """Setup command line argument parser"""
  parser = argparse.ArgumentParser(
    description="Enhanced Synthetic Document Generator for Claims Analysis",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  # CLI Mode (original behavior)
  python 2_data-add_documents.py --input-dir ./input --output-dir ./output

  # JSON Mode (structured logging)
  python 2_data-add_documents.py --input-dir ./input --output-dir ./output --json-output

  # With limit
  python 2_data-add_documents.py --input-dir ./input --limit 5

  # Custom config
  python 2_data-add_documents.py --config ./config/custom_config.yaml
        """
  )

  # Input/Output arguments
  parser.add_argument("--input-dir", type=str,
                      help="Input directory containing JSON files from Script 1")
  parser.add_argument("--output-dir", type=str,
                      help="Output directory for enhanced JSON files")
  parser.add_argument("--config", type=str,
                      help="Path to configuration file")
  parser.add_argument("--limit", type=int,
                      help="Limit number of files to process")

  # Execution options
  parser.add_argument("--verbose", action="store_true",
                      help="Enable verbose logging")
  parser.add_argument("--skip-validation", action="store_true",
                      help="Skip input argument validation")

  # ✨ JSON output mode
  parser.add_argument("--json-output", action="store_true",
                      help="Output structured JSON events for progress tracking")

  return parser


def validate_arguments (args) -> bool:
  """Validate command line arguments"""
  # Note: input_dir is optional - will use config default if not provided

  if args.limit and args.limit < 1:
    print("❌ Error: --limit must be positive", file=sys.stderr)
    return False

  return True


def print_startup_banner ():
  """Print startup banner with version info"""
  print("🚀 Enhanced Synthetic Document Generator v2.0", file=sys.stderr)
  print("=" * 60, file=sys.stderr)
  print("📄 Generates comprehensive claim documents from FHIR data", file=sys.stderr)
  print("🔧 Enhanced with modern infrastructure and function calling", file=sys.stderr)
  print("💰 Includes cost tracking and retry logic", file=sys.stderr)
  print("✨ NOW WITH: Structured JSON logging mode", file=sys.stderr)
  print("🔗 Compatible with Script 1 (FHIR Processor)", file=sys.stderr)
  print("", file=sys.stderr)


def print_completion_banner (success: bool, start_time: float):
  """Print completion banner with timing"""
  elapsed_time = time.time() - start_time

  print("\n" + "=" * 60, file=sys.stderr)
  if success:
    print("✅ PROCESSING COMPLETED SUCCESSFULLY", file=sys.stderr)
  else:
    print("❌ PROCESSING COMPLETED WITH ERRORS", file=sys.stderr)
  print("=" * 60, file=sys.stderr)
  print(f"⏱️  Total elapsed time: {elapsed_time:.1f} seconds", file=sys.stderr)
  print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
  print("")


def main ():
  """✨ Main execution with structured logging support"""
  start_time = time.time()

  try:
    # Parse arguments first to check for JSON mode
    parser = setup_argument_parser()
    args = parser.parse_args()

    # ✨ Determine if we're in JSON mode
    json_mode = args.json_output

    # Print startup banner (skip in JSON mode)
    if not json_mode:
      print_startup_banner()

    # Validate arguments
    if not args.skip_validation:
      if not json_mode:
        print("🔍 Validating input arguments...", file=sys.stderr)
      if not validate_arguments(args):
        parser.print_help()
        return EXIT_CONFIG_ERROR
      if not json_mode:
        print("✅ Input validation passed", file=sys.stderr)

    # Load configuration
    try:
      if not json_mode:
        print("🔧 Loading configuration...", file=sys.stderr)
      config = ClassConfig(args.config)
      if not json_mode:
        print("✅ Configuration loaded successfully", file=sys.stderr)
    except Exception as e:
      print(f"❌ Configuration error: {e}", file=sys.stderr)
      return EXIT_CONFIG_ERROR

    # ✨ Setup logging with JSON mode
    try:
      if not json_mode:
        print("📊 Setting up logging...", file=sys.stderr)
      logger = ClassLogger(config, json_mode=json_mode)

      # Override log level if verbose
      if args.verbose:
        logger.logger.setLevel(logging.DEBUG)
        logger.debug("🔍 Verbose logging enabled")

      if not json_mode:
        print("✅ Logging setup complete", file=sys.stderr)
    except Exception as e:
      print(f"❌ Logging setup error: {e}", file=sys.stderr)
      return EXIT_CONFIG_ERROR

    # ✨ Startup milestone
    logger.milestone(
      "Document generator initialized",
      status="info",
      data={"version": "2.0", "json_mode": json_mode}
    )

    # Initialize processor
    try:
      if not json_mode:
        print("🔧 Initializing document processor...", file=sys.stderr)
      processor = ClassProcessDocuments(config, logger)
      if not json_mode:
        print("✅ Processor initialized", file=sys.stderr)
    except Exception as e:
      print(f"❌ Processor initialization failed: {e}", file=sys.stderr)
      logger.milestone("Initialization failed", status="error", data={"error": str(e)})
      return EXIT_PROCESSING_ERROR

    # Log startup
    logger.info("Enhanced Synthetic Document Generator started")

    # Process files
    try:
      # Use config defaults if not provided
      processing_settings = config.get_processing_settings()

      # Get script directory for relative paths
      script_dir = Path(__file__).parent.resolve()

      # Handle input directory
      if args.input_dir:
        input_dir = args.input_dir if Path(args.input_dir).is_absolute() else str(
          script_dir / args.input_dir)
      else:
        default_input = processing_settings.get('default_input_dir', './input')
        input_dir = str(script_dir / default_input) if not Path(
          default_input).is_absolute() else default_input

      # Handle output directory
      if args.output_dir:
        output_dir = args.output_dir if Path(args.output_dir).is_absolute() else str(
          script_dir / args.output_dir)
      else:
        default_output = processing_settings.get('default_output_dir', './output')
        output_dir = str(script_dir / default_output) if not Path(
          default_output).is_absolute() else default_output

      logger.info(f"📂 Input directory: {input_dir}")
      logger.info(f"📁 Output directory: {output_dir}")

      # ✨ Processing start milestone
      logger.milestone(
        "Starting file processing",
        status="info",
        data={"input_dir": input_dir, "output_dir": output_dir, "limit": args.limit}
      )

      # Process batch
      batch_results = processor.process_batch(input_dir, output_dir, args.limit)

      # Print results (skip in JSON mode)
      if not json_mode:
        processor.print_batch_summary(batch_results)

      # ✨ Final stats
      summary = batch_results["summary"]
      stats_dict = {
          "total_files": summary["total_files"],
          "successful_files": summary["successful"],
          "failed_files": summary["failed"],
          "documents_generated": summary["documents_generated"],
          "documents_skipped": summary["documents_skipped"],
          "total_cost": summary["total_cost"],
          "total_time": summary["total_processing_time"]
      }

      # Add token statistics if available
      token_usage = summary.get('token_usage', {})
      if token_usage and token_usage.get('total_usage', 0) > 0:
          stats_dict["total_tokens"] = token_usage.get('total_usage', 0)
          stats_dict["total_input_tokens"] = token_usage.get('total_input', 0)
          stats_dict["total_output_tokens"] = token_usage.get('total_output', 0)

      logger.stats(stats_dict)

      # Determine success
      success = batch_results["summary"]["successful"] > 0

      # Print completion banner (skip in JSON mode)
      if not json_mode:
        print_completion_banner(success, start_time)
      else:
        # ✨ Final milestone in JSON mode
        logger.milestone(
          "Processing complete" if success else "Processing completed with errors",
          status="success" if success else "warning",
          data=batch_results["summary"]
        )

      return EXIT_SUCCESS if success else EXIT_PROCESSING_ERROR

    except Exception as e:
      logger.error(f"Processing error: {e}")
      logger.milestone("Processing failed", status="error", data={"error": str(e)})
      if not json_mode:
        print(f"❌ Processing error: {e}", file=sys.stderr)
      return EXIT_PROCESSING_ERROR

  except KeyboardInterrupt:
    if not json_mode:
      print("\n⚠️  Processing interrupted by user", file=sys.stderr)
    return EXIT_SUCCESS
  except Exception as e:
    print(f"❌ Fatal error: {e}", file=sys.stderr)
    traceback.print_exc()
    return EXIT_PROCESSING_ERROR


if __name__ == "__main__":
  sys.exit(main())