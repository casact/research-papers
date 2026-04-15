# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

"""
LLM Provider Abstraction Layer
Supports multiple LLM providers (OpenAI, Ollama) with a unified interface
"""

import os
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from openai import OpenAI


class ClassLLM(ABC):
  """Abstract base class for LLM providers"""

  def __init__(self, config: Dict, logger, dry_run: bool = False):
    self.config = config
    self.logger = logger
    self.dry_run = dry_run
    self.total_cost = 0.0
    self.total_calls = 0
    self.total_tokens = 0
    self.total_input_tokens = 0
    self.total_output_tokens = 0
    self.total_time = 0.0

  @abstractmethod
  def call_llm(self, messages: List[Dict], model: str = None,
               max_tokens: int = None, temperature: float = 0.0,
               call_type: str = "general") -> Dict:
    """
    Make a chat completion call

    Returns:
      {
        'content': str,
        'usage': {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int},
        'cost': float,
        'response_time': float,
        'model': str
      }
    """
    pass

  @abstractmethod
  def call_llm_with_function(self, messages: List[Dict], schema: Dict,
                             function_name: str, model: str = None,
                             max_tokens: int = None, temperature: float = 0.7,
                             call_type: str = "structured") -> Dict:
    """
    Make a structured output call (function calling or equivalent)

    Returns:
      {
        'success': bool,
        'function_args': dict,  # parsed structured output
        'usage': {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int},
        'cost': float,
        'response_time': float,
        'model': str,
        'error': str  # only if success=False
      }
    """
    pass

  @abstractmethod
  def get_cost_summary(self) -> Dict:
    """
    Get cost and usage statistics

    returns:
      {
      'total_cost': self.total_cost,
      'total_calls': self.total_calls,
      'average_cost_per_call': self.total_cost / max(self.total_calls, 1),
      'total_tokens': self.total_tokens,
      'total_time': self.total_time
    }
    """
    pass


class ClassLLMOpenAI(ClassLLM):
  """OpenAI API provider implementation"""

  def __init__(self, config: Dict, logger, provider_config: Dict, dry_run: bool = False):
    super().__init__(config, logger, dry_run)
    self.provider_config = provider_config

    # Initialize OpenAI client (skip if dry run)
    if not dry_run:
      api_key_env = provider_config.get('api_key_env', 'OPENAI_API_KEY')
      api_key = os.getenv(api_key_env)
      if not api_key:
        raise ValueError(f"{api_key_env} environment variable not set")

      self.client = OpenAI(api_key=api_key)
    else:
      self.client = None  # No client needed for dry run

    self.total_cost = 0.0
    self.total_calls = 0
    self.total_input_tokens = 0
    self.total_output_tokens = 0
    self.total_tokens = 0

    # Get pricing configuration
    self.pricing = provider_config.get('pricing', {})

    # Retry settings
    self.max_retries = config.get('retry_count', 3)
    self.base_delay = config.get('retry_delay_base', 2)

    # self.logger.info(f"LLM Provider - OpenAI - Initialized")

  def call_llm(self, messages: List[Dict], model: str = None,
               max_tokens: int = None, temperature: float = 0.0,
               call_type: str = "general") -> Dict:
    """Make OpenAI chat completion call"""

    # Use defaults from config if not provided
    if model is None:
      models_config = self.provider_config.get('models', {})
      model = models_config.get('default', 'gpt-4o-mini-2024-07-18')
    if max_tokens is None:
      max_tokens = self.config.get('default_max_tokens', 1000)

    # Log the request
    self.logger.debug(f"OpenAI completion call - {call_type}")
    self.logger.debug_api_prompt(self._format_messages_for_log(messages), call_type.upper())

    # DRY RUN: Return mock response without making API call
    if self.dry_run:
      self.logger.info(f"🧪 DRY RUN - Returning mock response for {call_type}")

      # Generate mock content based on call type
      if "classification" in call_type.lower():
        mock_content = json.dumps({
          "is_relevant": True,
          "confidence": 0.8,
          "reason": "DRY RUN - Mock classification response",
          "category": "moderate_cost",
          "cost_indicators": ["mock_indicator"]
        })
      else:
        mock_content = "DRY RUN - Mock clinical note for encounter. This is a simulated response for testing purposes without making actual LLM API calls."

      # Update tracking (zero cost/tokens for dry run)
      self.total_calls += 1

      return {
        'content': mock_content,
        'usage': {
          'prompt_tokens': 0,
          'completion_tokens': 0,
          'total_tokens': 0
        },
        'cost': 0.0,
        'response_time': 0.001,
        'model': f"{model} (dry-run)"
      }

    for attempt in range(self.max_retries):
      try:
        start_time = time.time()

        response = self.client.chat.completions.create(
          model=model,
          messages=messages,
          max_tokens=max_tokens,
          temperature=temperature
        )

        response_time = time.time() - start_time

        # Extract content and usage
        content = response.choices[0].message.content
        usage = response.usage

        # Log the response
        self.logger.debug_api_response(content, call_type.upper())

        # Calculate costs
        input_cost = self._calculate_input_cost(usage.prompt_tokens, model)
        output_cost = self._calculate_output_cost(usage.completion_tokens, model)
        total_cost = input_cost + output_cost

        # Update tracking
        self.total_cost += total_cost
        self.total_calls += 1
        self.total_tokens += usage.total_tokens
        self.total_input_tokens += usage.prompt_tokens
        self.total_output_tokens += usage.completion_tokens
        self.total_time += response_time

        # Log details
        self.logger.debug(f"OpenAI call successful - {call_type}")
        self.logger.debug(f"  Model: {model}")
        self.logger.debug(f"  Tokens: {usage.prompt_tokens} → {usage.completion_tokens}")
        self.logger.debug(f"  Cost: ${total_cost:.6f}")
        self.logger.debug(f"  Time: {response_time:.2f}s")

        return {
          'content': content,
          'usage': {
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens
          },
          'cost': total_cost,
          'response_time': response_time,
          'model': model
        }

      except Exception as e:
        self.logger.warning(f"OpenAI call attempt {attempt + 1}/{self.max_retries} failed: {e}")

        if attempt < self.max_retries - 1:
          delay = self.base_delay ** (attempt + 1)
          self.logger.info(f"Retrying in {delay} seconds...")
          time.sleep(delay)
        else:
          self.logger.error(f"OpenAI call failed after {self.max_retries} attempts")
          raise

  def call_llm_with_function(self, messages: List[Dict], schema: Dict,
                             function_name: str, model: str = None,
                             max_tokens: int = None, temperature: float = 0.7,
                             call_type: str = "structured") -> Dict:
    """Make OpenAI function call"""

    # Use defaults from config if not provided
    if model is None:
      models_config = self.provider_config.get('models', {})
      model = models_config.get('default', 'gpt-4o-mini-2024-07-18')
    if max_tokens is None:
      max_tokens = self.config.get('default_max_tokens', 1500)

    # Log the request
    self.logger.debug(f"LLMProvider - OpenAI Make Structured Call - {call_type}")
    self.logger.debug_api_prompt(self._format_messages_for_log(messages), call_type.upper())

    # DRY RUN: Return mock structured response without making API call
    if self.dry_run:
      self.logger.info(f"🧪 DRY RUN - Returning mock structured response for {call_type}")

      # Generate mock structured output
      mock_function_args = {
        "status": "mock",
        "message": "DRY RUN - Mock structured output for testing",
        "data": {}
      }

      # Update tracking (zero cost/tokens for dry run)
      self.total_calls += 1

      return {
        'success': True,
        'function_args': mock_function_args,
        'usage': {
          'prompt_tokens': 0,
          'completion_tokens': 0,
          'total_tokens': 0
        },
        'cost': 0.0,
        'response_time': 0.001,
        'model': f"{model} (dry-run)"
      }

    for attempt in range(self.max_retries):
      try:
        start_time = time.time()

        response = self.client.chat.completions.create(
          model=model,
          messages=messages,
          functions=[schema],
          function_call={"name": function_name},
          max_tokens=max_tokens,
          temperature=temperature
        )

        response_time = time.time() - start_time
        usage = response.usage

        # Get function call response
        choice = response.choices[0]
        content = choice.message.function_call.arguments if choice.message.function_call else None

        # Log the response
        self.logger.debug_api_response(content, call_type.upper())

        if not content:
          raise ValueError("No function call in response")

        # Parse function arguments
        function_args = json.loads(content)

        # Calculate costs
        input_cost = self._calculate_input_cost(usage.prompt_tokens, model)
        output_cost = self._calculate_output_cost(usage.completion_tokens, model)
        total_cost = input_cost + output_cost

        # Update tracking
        self.total_cost += total_cost
        self.total_calls += 1
        self.total_tokens += usage.total_tokens
        self.total_input_tokens += usage.prompt_tokens
        self.total_output_tokens += usage.completion_tokens
        self.total_time += response_time

        return {
          'success': True,
          'function_args': function_args,
          'usage': {
            'prompt_tokens': usage.prompt_tokens,
            'completion_tokens': usage.completion_tokens,
            'total_tokens': usage.total_tokens
          },
          'cost': total_cost,
          'response_time': response_time,
          'model': model
        }

      except Exception as e:
        self.logger.warning(f"OpenAI function call attempt {attempt + 1}/{self.max_retries} failed: {e}")

        if attempt < self.max_retries - 1:
          delay = self.base_delay ** (attempt + 1)
          self.logger.info(f"Retrying in {delay} seconds...")
          time.sleep(delay)
        else:
          self.logger.error(f"OpenAI function call failed after {self.max_retries} attempts")
          return {
            'success': False,
            'error': f"All {self.max_retries} attempts failed. Last error: {e}",
            'attempts': attempt + 1
          }

  def _calculate_input_cost(self, tokens: int, model: str) -> float:
    """Calculate input token cost"""
    if 'gpt-4o-mini' in model:
      rate = self.pricing.get('gpt_4o_mini_input_cost_per_1k', 0.00015)
    elif 'gpt-5-nano' in model:
      rate = self.pricing.get('gpt_5_nano_input_cost_per_1k', 0.00005)
    else:
      rate = 0.00015  # Default fallback
    return (tokens / 1000) * rate

  def _calculate_output_cost(self, tokens: int, model: str) -> float:
    """Calculate output token cost"""
    if 'gpt-4o-mini' in model:
      rate = self.pricing.get('gpt_4o_mini_output_cost_per_1k', 0.0006)
    elif 'gpt-5-nano' in model:
      rate = self.pricing.get('gpt_5_nano_output_cost_per_1k', 0.0004)
    else:
      rate = 0.0006  # Default fallback
    return (tokens / 1000) * rate

  def _format_messages_for_log(self, messages: List[Dict]) -> str:
    """Format messages for logging"""
    if isinstance(messages, str):
      return messages
    elif isinstance(messages, list):
      return "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])
    else:
      return str(messages)

  def get_cost_summary(self) -> Dict:
    """Get cost and usage statistics"""
    return {
      'total_cost': self.total_cost,
      'total_calls': self.total_calls,
      'average_cost_per_call': self.total_cost / max(self.total_calls, 1),
      'total_tokens': self.total_tokens,
      'total_input_tokens': self.total_input_tokens,
      'total_output_tokens': self.total_output_tokens,
      'total_time': self.total_time,
      'average_time_per_call': self.total_time / max(self.total_calls, 1)
    }


class ClassLLMOllama(ClassLLM):
  """Ollama API provider implementation (OpenAI-compatible)"""

  def __init__(self, config: Dict, logger, provider_config: Dict, dry_run: bool = False):
    super().__init__(config, logger, dry_run)
    self.provider_config = provider_config

    # Get base URL for logging purposes
    base_url = provider_config.get('base_url', 'http://localhost:11434/v1')

    # Initialize OpenAI client with Ollama base URL (skip if dry run)
    if not dry_run:
      # Ollama doesn't require an API key, but OpenAI SDK needs something
      self.client = OpenAI(
        base_url=base_url,
        api_key="ollama"  # Dummy key for Ollama
      )
      self.logger.info(f"Ollama provider initialized (base_url: {base_url})")
    else:
      self.client = None
      self.logger.info(f"Ollama provider initialized in DRY RUN mode (would use: {base_url})")

    # Retry settings
    self.max_retries = config.get('retry_count', 3)
    self.base_delay = config.get('retry_delay_base', 2)

  def call_llm(self, messages: List[Dict], model: str = None,
               max_tokens: int = None, temperature: float = 0.0,
               call_type: str = "general") -> Dict:
    """Make Ollama chat completion call"""

    # Use defaults from config if not provided
    if model is None:
      models_config = self.provider_config.get('models', {})
      model = models_config.get('default', 'mistral')
    if max_tokens is None:
      max_tokens = self.config.get('default_max_tokens', 1000)

    # Log the request
    self.logger.debug(f"Ollama completion call - {call_type}")
    self.logger.debug_api_prompt(self._format_messages_for_log(messages), call_type.upper())

    # DRY RUN: Return mock response without making API call
    if self.dry_run:
      self.logger.info(f"🧪 DRY RUN - Returning mock response for {call_type}")

      # Generate mock content based on call type
      if "classification" in call_type.lower():
        mock_content = json.dumps({
          "is_relevant": True,
          "confidence": 0.8,
          "reason": "DRY RUN - Mock classification response",
          "category": "moderate_cost",
          "cost_indicators": ["mock_indicator"]
        })
      else:
        mock_content = "DRY RUN - Mock clinical note for encounter. This is a simulated response for testing purposes without making actual LLM API calls."

      # Update tracking (zero cost/tokens for dry run)
      self.total_calls += 1

      return {
        'content': mock_content,
        'usage': {
          'prompt_tokens': 0,
          'completion_tokens': 0,
          'total_tokens': 0
        },
        'cost': 0.0,
        'response_time': 0.001,
        'model': f"{model} (dry-run)"
      }

    for attempt in range(self.max_retries):
      try:
        start_time = time.time()

        response = self.client.chat.completions.create(
          model=model,
          messages=messages,
          max_tokens=max_tokens,
          temperature=temperature
        )

        response_time = time.time() - start_time

        # Extract content
        content = response.choices[0].message.content

        # Ollama may or may not return usage stats
        usage = response.usage if hasattr(response, 'usage') and response.usage else None

        # Log the response
        self.logger.debug_api_response(content, call_type.upper())

        # Update tracking
        self.total_calls += 1
        self.total_time += response_time

        # Extract token counts (may be None for Ollama)
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        if usage:
          self.total_tokens += total_tokens
          self.total_input_tokens += prompt_tokens
          self.total_output_tokens += completion_tokens

        # Log details
        self.logger.debug(f"Ollama call successful - {call_type}")
        self.logger.debug(f"  Model: {model}")
        if usage:
          self.logger.debug(f"  Tokens: {prompt_tokens} → {completion_tokens}")
        self.logger.debug(f"  Time: {response_time:.2f}s")

        return {
          'content': content,
          'usage': {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens
          },
          'cost': 0.0,  # Ollama is free (local)
          'response_time': response_time,
          'model': model
        }

      except Exception as e:
        self.logger.warning(f"Ollama call attempt {attempt + 1}/{self.max_retries} failed: {e}")

        if attempt < self.max_retries - 1:
          delay = self.base_delay ** (attempt + 1)
          self.logger.info(f"Retrying in {delay} seconds...")
          time.sleep(delay)
        else:
          self.logger.error(f"Ollama call failed after {self.max_retries} attempts")
          raise

  def call_llm_with_function(self, messages: List[Dict], schema: Dict,
                             function_name: str, model: str = None,
                             max_tokens: int = None, temperature: float = 0.7,
                             call_type: str = "structured") -> Dict:
    """
    Make Ollama structured call by simulating function calling
    Uses JSON mode with schema in prompt
    """

    # Use defaults from config if not provided
    if model is None:
      models_config = self.provider_config.get('models', {})
      model = models_config.get('default', 'mistral')
    if max_tokens is None:
      max_tokens = self.config.get('default_max_tokens', 1500)

    # Convert function schema to JSON schema for prompt
    schema_description = self._schema_to_prompt(schema)

    # Add schema instruction to messages
    enhanced_messages = messages.copy()

    # Determine context: document generation (Script 2) vs analysis (Script 4)
    # Check for generation patterns: ends with "_generation" or starts with "document_generation"
    call_type_lower = call_type.lower()
    is_generation = (
        call_type_lower.endswith("_generation") or
        call_type_lower.startswith("document_generation") or
        "master_profile" in call_type_lower
    )

    # Build context-appropriate system message for Ollama
    if is_generation:
      # Generation prompt for Script 2 - creating synthetic training data
      schema_instruction = f"""You are generating REALISTIC TRAINING DATA for insurance claim analysis.

CRITICAL REQUIREMENTS:
1. Output ONLY valid JSON matching the schema below
2. NO markdown formatting, NO code blocks, NO explanations
3. Include REALISTIC IMPERFECTIONS as specified in descriptions:
   - 1-3 minor typos ("teh", "recieve", "occured")
   - Industry abbreviations (w/, w/o, approx, est.)
   - Informal elements appropriate to document type
   - Natural human imperfections (this is training data, not perfect documents)

{schema_description}

REMEMBER: These imperfections make the training data authentic. They are REQUIRED, not mistakes."""
    else:
      # Analysis prompt for Script 4 and others - extracting from real documents
      schema_instruction = f"""You are analyzing documents to extract structured information.

CRITICAL REQUIREMENTS:
1. Output ONLY valid JSON matching the schema below
2. NO markdown formatting, NO code blocks, NO explanations
3. Extract information ACCURATELY from the provided document
4. Follow the extraction rules and variable definitions provided in the prompt
5. Provide rationale and confidence scores as specified in the schema

{schema_description}

REMEMBER: Extract information faithfully from the source document. Be precise and accurate."""

    # Insert schema instruction at the beginning or append to system message
    if enhanced_messages and enhanced_messages[0].get('role') == 'system':
      # Enhance existing system message
      original_content = enhanced_messages[0]['content']
      enhanced_messages[0]['content'] = f"{original_content}\n\n{schema_instruction}"
    else:
      enhanced_messages.insert(0, {'role': 'system', 'content': schema_instruction})

    # Log the request
    self.logger.debug(f"Ollama structured call - {call_type}")
    self.logger.debug_api_prompt(self._format_messages_for_log(enhanced_messages), call_type.upper())

    # DRY RUN: Return mock structured response without making API call
    if self.dry_run:
      self.logger.info(f"🧪 DRY RUN - Returning mock structured response for {call_type}")

      # Generate mock structured output
      mock_function_args = {
        "status": "mock",
        "message": "DRY RUN - Mock structured output for testing",
        "data": {}
      }

      # Update tracking (zero cost/tokens for dry run)
      self.total_calls += 1

      return {
        'success': True,
        'function_args': mock_function_args,
        'usage': {
          'prompt_tokens': 0,
          'completion_tokens': 0,
          'total_tokens': 0
        },
        'cost': 0.0,
        'response_time': 0.001,
        'model': f"{model} (dry-run)"
      }

    for attempt in range(self.max_retries):
      try:
        start_time = time.time()

        # Try to use JSON mode if supported
        try:
          response = self.client.chat.completions.create(
            model=model,
            messages=enhanced_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={'type': 'json_object'}  # OpenAI-compatible JSON mode
          )
        except Exception as json_mode_error:
          # Fallback to regular mode if JSON mode not supported
          self.logger.debug(f"JSON mode not supported, using regular mode: {json_mode_error}")
          response = self.client.chat.completions.create(
            model=model,
            messages=enhanced_messages,
            max_tokens=max_tokens,
            temperature=temperature
          )

        response_time = time.time() - start_time

        # Extract content
        content = response.choices[0].message.content

        # Ollama may or may not return usage stats
        usage = response.usage if hasattr(response, 'usage') and response.usage else None

        # Log the response
        self.logger.debug_api_response(content, call_type.upper())

        # Update tracking
        self.total_calls += 1
        self.total_time += response_time

        # Extract token counts (may be None for Ollama)
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        if usage:
          self.total_tokens += total_tokens
          self.total_input_tokens += prompt_tokens
          self.total_output_tokens += completion_tokens

        # Parse JSON response with enhanced extraction
        try:
          function_args = self._extract_json_from_response(content)

          return {
            'success': True,
            'function_args': function_args,
            'usage': {
              'prompt_tokens': prompt_tokens,
              'completion_tokens': completion_tokens,
              'total_tokens': total_tokens
            },
            'cost': 0.0,  # Ollama is free
            'response_time': response_time,
            'model': model
          }

        except json.JSONDecodeError as e:
          self.logger.error(f"Failed to parse Ollama JSON response: {e}")
          self.logger.debug(f"Raw response (first 500 chars): {content[:500]}")
          return {
            'success': False,
            'error': f"JSON decode error: {e}",
            'raw_response': content[:500]
          }

      except Exception as e:
        self.logger.warning(f"Ollama structured call attempt {attempt + 1}/{self.max_retries} failed: {e}")

        if attempt < self.max_retries - 1:
          delay = self.base_delay * (2 ** attempt)
          self.logger.debug(f"Retrying in {delay} seconds...")
          time.sleep(delay)
        else:
          return {
            'success': False,
            'error': f"All {self.max_retries} attempts failed. Last error: {e}",
            'attempts': attempt + 1
          }

  def _build_example_value(self, prop_name: str, prop_info: Dict, is_required: bool) -> any:
    """Recursively build example values for schema properties"""
    prop_type = prop_info.get('type', 'string')

    if prop_type == 'string':
      return f"<{prop_name}_text>" if is_required else ""
    elif prop_type == 'number' or prop_type == 'integer':
      return 0
    elif prop_type == 'boolean':
      return True
    elif prop_type == 'array':
      items_info = prop_info.get('items', {})
      items_type = items_info.get('type', 'string')
      if items_type == 'string':
        return ["item1", "item2"]
      elif items_type == 'object':
        # Build example object for array items
        nested_props = items_info.get('properties', {})
        nested_required = items_info.get('required', [])
        if nested_props:
          return [self._build_nested_example(nested_props, nested_required)]
        return [{}]
      else:
        return []
    elif prop_type == 'object':
      # Recursively build complete nested structure
      nested_props = prop_info.get('properties', {})
      nested_required = prop_info.get('required', [])
      return self._build_nested_example(nested_props, nested_required)
    else:
      return "<value>"

  def _build_nested_example(self, properties: Dict, required: List) -> Dict:
    """Build complete nested object example with all fields"""
    example = {}
    for key, value_info in properties.items():
      is_required = key in required
      example[key] = self._build_example_value(key, value_info, is_required)
    return example

  def _schema_to_prompt(self, schema: Dict) -> str:
    """Convert OpenAI function schema to detailed prompt with complete nested examples"""
    function_name = schema.get('name', 'function')
    description = schema.get('description', '')
    parameters = schema.get('parameters', {})

    prompt_parts = [
      f"Function: {function_name}",
      f"Description: {description}",
      "",
      "CRITICAL: Output ONLY valid JSON. No markdown, no code blocks, no explanations.",
      "",
      "Required JSON Structure:"
    ]

    # Format parameters with explicit type information
    properties = parameters.get('properties', {})
    required = parameters.get('required', [])

    # Build complete example JSON structure with nested objects fully expanded
    example_json = {}

    for prop_name, prop_info in properties.items():
      is_required = prop_name in required
      prop_type = prop_info.get('type', 'string')
      prop_desc = prop_info.get('description', '')

      req_marker = "[REQUIRED]" if is_required else "[OPTIONAL]"
      prompt_parts.append(f"  - {prop_name} ({prop_type}) {req_marker}: {prop_desc}")

      # Build example value using recursive helper
      example_json[prop_name] = self._build_example_value(prop_name, prop_info, is_required)

    # Add JSON example
    prompt_parts.extend([
      "",
      "Example JSON Format (with COMPLETE nested structures):",
      "```",
      json.dumps(example_json, indent=2),
      "```",
      "",
      "IMPORTANT:",
      "- Replace <placeholders> with actual content",
      "- ALL nested objects must include ALL their required fields",
      "- Output ONLY the JSON object, nothing else",
      "- Ensure all required fields are present at every nesting level",
      "- Use double quotes for strings",
      "- No trailing commas"
    ])

    return "\n".join(prompt_parts)

  def _extract_json_from_response(self, content: str) -> Dict:
    """
    Extract and parse JSON from model response with robust error handling

    Handles common issues:
    - Markdown code blocks (```json...```)
    - Leading/trailing whitespace
    - BOM characters
    - Explanatory text before/after JSON
    - Trailing commas (attempts to fix)
    """
    import re

    # Remove BOM if present
    content = content.lstrip('\ufeff')

    # Try to extract from markdown code blocks first
    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    code_match = re.search(code_block_pattern, content, re.DOTALL)
    if code_match:
      json_str = code_match.group(1)
      return json.loads(json_str)

    # Try to find JSON object boundaries
    json_pattern = r'\{.*\}'
    json_match = re.search(json_pattern, content, re.DOTALL)
    if json_match:
      json_str = json_match.group()

      # Try parsing as-is first
      try:
        return json.loads(json_str)
      except json.JSONDecodeError:
        # Attempt to fix common issues

        # Fix trailing commas before } or ]
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

        # Try again
        try:
          return json.loads(json_str)
        except json.JSONDecodeError:
          # Last resort: try to parse the original content directly
          pass

    # Final attempt: parse content directly (might have no wrapper text)
    return json.loads(content.strip())

  def _format_messages_for_log(self, messages: List[Dict]) -> str:
    """Format messages for logging"""
    if isinstance(messages, str):
      return messages
    elif isinstance(messages, list):
      return "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])
    else:
      return str(messages)

  def get_cost_summary(self) -> Dict:
    """Get usage statistics (no cost for Ollama)"""
    return {
      'total_cost': 0.0,
      'total_calls': self.total_calls,
      'average_cost_per_call': 0.0,
      'total_tokens': self.total_tokens,
      'total_input_tokens': self.total_input_tokens,
      'total_output_tokens': self.total_output_tokens,
      'total_time': self.total_time,
      'average_time_per_call': self.total_time / max(self.total_calls, 1)
    }


class ClassCreateLLM:
  """Factory for creating LLM providers based on configuration"""

  @staticmethod
  def create_provider(config: Dict, logger, dry_run: bool = False) -> ClassLLM:
    """
    Create and return appropriate provider based on config

    Args:
      config: Full api_settings dict from YAML
      logger: Logger instance
      dry_run: If True, provider returns mock data without API calls

    Returns:
      LLMProvider instance (OpenAIProvider or OllamaProvider)
    """

    logger.info("=" * 60)
    provider_name = config.get('provider', 'openai').lower()

    if provider_name == 'openai':
      provider_config = config.get('openai', {})
      logger.info("Creating LLM Provider: OpenAI")
      return ClassLLMOpenAI(config, logger, provider_config, dry_run)

    elif provider_name == 'ollama':
      provider_config = config.get('ollama', {})
      logger.info("Creating LLM Provider: Ollama")
      return ClassLLMOllama(config, logger, provider_config, dry_run)

    else:
      raise ValueError(f"Unknown provider: {provider_name}. Supported: 'openai', 'ollama'")