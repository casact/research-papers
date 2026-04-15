# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# python 3_data-process_text_files.py --input-dir ./input --output-dir ./output
# python 3_data-process_text_files.py --limit 10 --verbose
# python 3_data-process_text_files.py --json-output  # JSON mode
"""
Text File Processor for Claims Analysis - Script 3
Converts text files to unified JSON format for claims processing pipeline
Enhanced with modern infrastructure: UnifiedConfig, SimpleLogger, MetricsTracker
No LLM API calls - pure text processing and conversion

CONVERTED WITH STRUCTURED LOGGING:
- JSON output mode with --json-output flag
- All human messages on stderr
- Pure JSON events on stdout in JSON mode
- Backward compatible CLI mode

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
import re
import argparse
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from time import perf_counter
import traceback

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
  "claimant_statement": "Claimant Statement",
  "clinical_note": "Clinical Note"
}


class ClassConfig:
  """Centralized configuration management for text file processing"""

  def __init__ (self, config_path: Optional[str] = None):
    self.config = self._load_config(config_path)

  def _load_config (self, config_path: Optional[str]) -> Dict:
    """Load configuration from YAML file"""
    if config_path is None:
      script_dir = Path(__file__).parent.resolve()
      config_path = script_dir / "config" / "3_process-combine_text_to_json.yaml"

    self.config_path = str(config_path)

    try:
      with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
      return config
    except FileNotFoundError:
      print(f"⚠️ Config file not found: {config_path}", file=sys.stderr)
      print("📁 Using default configuration", file=sys.stderr)
      return self._get_default_config()
    except Exception as e:
      print(f"❌ Error loading config from {config_path}: {e}", file=sys.stderr)
      sys.exit(EXIT_CONFIG_ERROR)

  def _get_default_config (self) -> Dict:
    """Return default configuration"""
    return {
      'processing': {
        'input_folder': 'input/text_files',
        'default_output_dir': './output/3_process-combine_text_to_json.yaml',
        'encoding': 'utf-8',
        'min_content_length': 50
      },
      'logging': {
        'level': 'INFO',
        'console_format': '%(asctime)s - %(levelname)s - %(message)s',
        'debug_options': {
          'show_file_processing': True,
          'show_json_creation': True,
          'show_encounter_details': True,
          'max_content_preview': 200
        }
      },
      'text_file_processing': {
        'filename_pattern': 'patient_initials_claim_id_document_type.txt',
        'encoding': 'utf-8',
        'min_content_length': 50
      },
      'document_type_mapping': {
        'phone': 'phone_transcript',
        'transcript': 'phone_transcript',
        'phone_transcript': 'phone_transcript',
        'adjuster': 'adjuster_notes_initial',
        'adjuster_initial': 'adjuster_notes_initial',
        'adjuster_notes_initial': 'adjuster_notes_initial',
        'medical': 'medical_provider_letter',
        'provider': 'medical_provider_letter',
        'medical_provider_letter': 'medical_provider_letter',
        'settlement': 'settlement_adjuster_notes',
        'settlement_adjuster_notes': 'settlement_adjuster_notes',
        'claimant': 'claimant_statement',
        'statement': 'claimant_statement',
        'claimant_statement': 'claimant_statement',
        'clinical': 'clinical_note',
        'note': 'clinical_note',
        'clinical_note': 'clinical_note'
      },
      'filename_templates': {
        'json_conversion': '{patient_initials}_{claim_id}.json'
      },
      'quality_control': {
        'validate_filename_format': True,
        'require_minimum_content': True,
        'merge_duplicate_document_types': True,
        'log_skipped_files': True
      },
      'error_handling': {
        'continue_on_file_error': True,
        'save_partial_results': True,
        'max_filename_parse_retries': 1
      }
    }

  def get_logging_settings (self) -> Dict:
    """Get logging configuration"""
    return self.config.get('logging', {})

  def get_processing_settings (self) -> Dict:
    """Get text processing configuration"""
    return self.config.get('processing', {})

  def get_text_processing_settings (self) -> Dict:
    """Get text file processing specific settings"""
    return self.config.get('text_file_processing', {})

  def get_document_type_mapping (self) -> Dict:
    """Get document type mapping"""
    return self.config.get('document_type_mapping', {})

  def get_quality_control_settings (self) -> Dict:
    """Get quality control settings"""
    return self.config.get('quality_control', {})

  def get_error_handling_settings (self) -> Dict:
    """Get error handling settings"""
    return self.config.get('error_handling', {})


class ClassLogger:
  """Streamlined logging with configurable debug options and JSON output mode"""

  def __init__ (self, config: ClassConfig, json_mode: bool = False):
    self.config = config
    self.json_mode = json_mode
    self.logger = self._setup_logger()

    # Debug settings
    self.debug_settings = config.get_logging_settings().get('debug_options', {})
    self.show_file_processing = self.debug_settings.get('show_file_processing', True)
    self.show_json_creation = self.debug_settings.get('show_json_creation', True)
    self.show_encounter_details = self.debug_settings.get('show_encounter_details', True)
    self.max_content_preview = self.debug_settings.get('max_content_preview', 200)

  def _setup_logger (self):
    """Setup logger with configuration"""
    logger = logging.getLogger('text_processor')

    # Set level
    log_config = self.config.get_logging_settings()
    level = getattr(logging, log_config.get('level', 'INFO').upper())
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler - ALWAYS STDERR
    console_handler = logging.StreamHandler(sys.stderr)
    console_format = log_config.get('console_format', '%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(logging.Formatter(console_format))
    logger.addHandler(console_handler)

    return logger

  def _emit_json (self, event_type: str, data: Dict):
    """Emit JSON event to stdout (only in JSON mode)"""
    if self.json_mode:
      event = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'data': data
      }
      print(json.dumps(event), flush=True)

  def progress (self, message: str, current: int = None, total: int = None, **kwargs):
    """Log progress with optional JSON output"""
    if self.json_mode:
      data = {'message': message, **kwargs}
      if current is not None:
        data['current'] = current
      if total is not None:
        data['total'] = total
      self._emit_json('progress', data)

    # Always log to stderr as well for visibility
    if current is not None and total is not None:
      self.logger.info(f"🔄 {message} ({current}/{total})")
    else:
      self.logger.info(f"🔄 {message}")

  def milestone (self, message: str, status: str = 'info', **kwargs):
    """Log milestone with optional JSON output"""
    if self.json_mode:
      data = {'message': message, 'status': status, **kwargs}
      self._emit_json('milestone', data)

    # Always log to stderr
    emoji = {'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '❌'}.get(status, 'ℹ️')
    self.logger.info(f"{emoji}  MILESTONE: {message}")

  def stats (self, stats_data: Dict):
    """Log statistics with optional JSON output"""
    if self.json_mode:
      self._emit_json('stats', stats_data)

    # Always log to stderr
    # self.logger.info(f"📊 STATS: {stats_data}")

  def debug_file_processing (self, message: str):
    """Debug logging for file processing (only shown when debug enabled)"""
    if self.logger.level <= logging.DEBUG and self.show_file_processing:
      self.logger.debug(f"📄 FILE: {message}")

  def debug_json_creation (self, message: str):
    """Debug logging for JSON creation (only shown when debug enabled)"""
    if self.logger.level <= logging.DEBUG and self.show_json_creation:
      self.logger.debug(f"📋 JSON: {message}")

  def debug_encounter_details (self, encounter_data: Dict, claim_id: str = ""):
    """Debug logging for encounter details (only shown when debug enabled)"""
    if self.logger.level <= logging.DEBUG and self.show_encounter_details:
      encounter_id = encounter_data.get('encounter_id', 'unknown')
      doc_type = encounter_data.get('document_type', 'unknown')
      content = encounter_data.get('document_text', '')

      # Truncate content for preview
      if self.max_content_preview > 0 and len(content) > self.max_content_preview:
        content_preview = content[:self.max_content_preview] + "..."
      else:
        content_preview = content

      self.logger.debug(f"🏥 ENCOUNTER [{claim_id}]: {encounter_id}")
      self.logger.debug(f"    📋 Type: {doc_type}")
      self.logger.debug(f"    📄 Content: {content_preview}")

  def info (self, message: str):
    """Standard info logging"""
    self.logger.info(message)

  def debug (self, message: str):
    """Standard debug logging"""
    self.logger.debug(message)

  def warning (self, message: str):
    """Standard warning logging"""
    self.logger.warning(message)

  def error (self, message: str):
    """Standard error logging"""
    self.logger.error(message)

  def success (self, message: str):
    """Success logging with emoji"""
    self.logger.info(f"✅ {message}")


class ClassTrackMetrics:
  """Track processing metrics for text file processing (no API calls)"""

  def __init__ (self, logger: 'ClassLogger'):
    self.logger = logger
    self.start_time = perf_counter()
    self.processing_times = []
    self.file_stats = {
      'files_processed': 0,
      'files_successful': 0,
      'files_failed': 0,
      'files_skipped': 0,
      'claims_created': 0,
      'encounters_created': 0,
      'total_content_characters': 0
    }

  def record_file_processing (self, processing_time: float, success: bool,
                              characters_processed: int = 0, encounters_created: int = 0):
    """Record file processing metrics"""
    self.processing_times.append(processing_time)
    self.file_stats['files_processed'] += 1
    self.file_stats['total_content_characters'] += characters_processed
    self.file_stats['encounters_created'] += encounters_created

    if success:
      self.file_stats['files_successful'] += 1
    else:
      self.file_stats['files_failed'] += 1

  def record_claim_created (self):
    """Record that a claim JSON was created"""
    self.file_stats['claims_created'] += 1

  def record_file_skipped (self):
    """Record that a file was skipped"""
    self.file_stats['files_skipped'] += 1

  def get_processing_rate (self) -> float:
    """Get files processed per minute"""
    elapsed_time = perf_counter() - self.start_time
    if elapsed_time == 0:
      return 0.0
    return (self.file_stats['files_processed'] / elapsed_time) * 60

  def get_average_processing_time (self) -> float:
    """Get average processing time per file"""
    if not self.processing_times:
      return 0.0
    return sum(self.processing_times) / len(self.processing_times)

  def get_efficiency_metrics (self) -> Dict:
    """Get efficiency metrics"""
    total_time = perf_counter() - self.start_time
    avg_chars_per_file = (self.file_stats['total_content_characters'] /
                          max(self.file_stats['files_processed'], 1))

    return {
      'total_processing_time': total_time,
      'average_processing_time_per_file': self.get_average_processing_time(),
      'files_per_minute': self.get_processing_rate(),
      'average_characters_per_file': avg_chars_per_file,
      'encounters_per_file': (self.file_stats['encounters_created'] /
                              max(self.file_stats['files_processed'], 1))
    }

  def output_stats (self):
    """Output current statistics via logger.stats()"""
    self.logger.stats({
      'files_processed': self.file_stats['files_processed'],
      'files_successful': self.file_stats['files_successful'],
      'files_failed': self.file_stats['files_failed'],
      'files_skipped': self.file_stats['files_skipped'],
      'claims_created': self.file_stats['claims_created'],
      'encounters_created': self.file_stats['encounters_created']
    })

  def print_summary (self):
    """Print processing summary"""
    efficiency = self.get_efficiency_metrics()
    success_rate = ((self.file_stats['files_successful'] /
                     max(self.file_stats['files_processed'], 1)) * 100)

    self.logger.info("=" * 60)
    self.logger.info("📊 PROCESSING METRICS SUMMARY")
    self.logger.info("-" * 60)
    self.logger.info(f"📁 Files processed: {self.file_stats['files_processed']}")
    self.logger.info(f"✅ Files successful: {self.file_stats['files_successful']}")
    self.logger.info(f"❌ Files failed: {self.file_stats['files_failed']}")
    self.logger.info(f"⏭️ Files skipped: {self.file_stats['files_skipped']}")
    self.logger.info(f"📋 Claims created: {self.file_stats['claims_created']}")
    self.logger.info(f"🏥 Encounters created: {self.file_stats['encounters_created']}")
    self.logger.info(f"📈 Success rate: {success_rate:.1f}%")
    self.logger.info(f"⚡ Processing rate: {efficiency['files_per_minute']:.1f} files/min")
    self.logger.info(f"⏱️ Avg time per file: {efficiency['average_processing_time_per_file']:.2f}s")
    self.logger.info(f"📄 Avg characters per file: {efficiency['average_characters_per_file']:.0f}")
    # self.logger.info("-" * 60)


# PART 2: TEXT FILE PROCESSING ENGINE

class ClassProcessTextDocuments:
  """Main text file processor with enhanced infrastructure"""

  def __init__ (self, config: ClassConfig, logger: 'ClassLogger'):
    self.config = config
    self.logger = logger
    self.metrics = ClassTrackMetrics(logger)

    # Processing settings
    self.processing_settings = config.get_processing_settings()
    self.text_settings = config.get_text_processing_settings()
    self.doc_type_mapping = config.get_document_type_mapping()
    self.quality_settings = config.get_quality_control_settings()
    self.error_settings = config.get_error_handling_settings()

    # Processing statistics
    self.processing_report = {
      "total_files_found": 0,
      "files_processed": 0,
      "files_skipped": 0,
      "claims_created": 0,
      "skipped_files": [],
      "processing_timestamp": datetime.now().isoformat()
    }

  def find_text_files (self, input_dir: str) -> List[Path]:
    """Find all text files in input directory"""
    input_path = Path(input_dir)

    if not input_path.exists():
      self.logger.error(f"Input directory does not exist: {input_dir}")
      return []

    if not input_path.is_dir():
      self.logger.error(f"Input path is not a directory: {input_dir}")
      return []

    # Find all .txt files
    text_files = list(input_path.glob("*.txt"))

    self.logger.info(f"📂 Found {len(text_files)} text files in {input_path}")
    self.logger.debug_file_processing(f"Text files found: {[f.name for f in text_files]}")

    return text_files

  def parse_filename (self, filename: str) -> Optional[Tuple[str, str, str]]:
    """Parse filename to extract patient_initials, claim_id, document_type"""
    try:
      # Remove extension
      basename = Path(filename).stem

      self.logger.debug_file_processing(f"Parsing filename: {basename}")

      # Split by underscores
      parts = basename.split('_')

      if len(parts) < 2:
        self.logger.warning(f"Filename format invalid (need at least 2 parts): {basename}")
        return None

      # Assume pattern: patient_initials_claim_id_document_type
      patient_initials = parts[0]
      claim_id = parts[1]
      document_type_raw = '_'.join(parts[2:])  # Join remaining parts

      # Map document type
      document_type = self.doc_type_mapping.get(document_type_raw.lower(), document_type_raw)

      self.logger.debug_file_processing(
        f"Parsed: claim_id='{claim_id}', "
        f"doc_type='{document_type}' (from '{document_type_raw}')"
      )

      return patient_initials, claim_id, document_type

    except Exception as e:
      self.logger.error(f"Error parsing filename {filename}: {e}")
      return None

  def load_patient_metadata (self, patient_folder: Path) -> Optional[Dict]:
    """Load patient metadata from {patient_initials}_metadata.txt"""
    try:
      # Look for any file ending with _metadata.txt
      metadata_files = list(patient_folder.glob("*_metadata.txt"))

      if not metadata_files:
        self.logger.error(f"No metadata file found in {patient_folder}")
        self.logger.error(
          f"Expected format: {{patient_initials}}_metadata.txt (e.g., mr_metadata.txt)")
        return None

      if len(metadata_files) > 1:
        self.logger.warning(
          f"Multiple metadata files found in {patient_folder}, using first one: {metadata_files[0].name}")

      metadata_file = metadata_files[0]
      self.logger.info(f"📋 Found metadata file: {metadata_file.name}")

      # Read and parse YAML content
      with open(metadata_file, 'r', encoding='utf-8') as f:
        content = f.read()

      import yaml
      metadata = yaml.safe_load(content)

      # Validate required fields
      required_fields = ['patient_initials', 'age', 'gender', 'name']
      for field in required_fields:
        if field not in metadata:
          self.logger.error(f"Missing required field '{field}' in metadata file: {metadata_file}")
          return None

      self.logger.info(f"✅  Loaded metadata for patient: {metadata.get('patient_initials')}")
      return metadata

    except Exception as e:
      self.logger.error(f"Error loading metadata from {patient_folder}: {e}")
      return None

  def process_patient_folder (self, patient_folder: Path, output_dir: str) -> Dict:
    """Process all text files in a single patient folder"""

    self.logger.progress(
      f"Patient folder: {patient_folder.name}",
      operation='process_folder',
      folder=patient_folder.name
    )

    folder_result = {
      "folder_name": patient_folder.name,
      "files_found": 0,
      "files_processed": 0,
      "files_skipped": 0,
      "claims_created": 0,
      "skipped_files": [],
      "created_files": [],
      "patient_initials": None
    }

    # Load patient metadata
    patient_metadata = self.load_patient_metadata(patient_folder)
    if not patient_metadata:
      self.logger.error(f"❌ Cannot process folder without metadata: {patient_folder.name}")
      return folder_result

    # patient_initials = patient_metadata.get('patient_initials')
    # folder_result["patient_initials"] = patient_initials

    # Find all text files (excluding metadata)
    text_files = [f for f in patient_folder.glob("*.txt") if not f.name.endswith("_metadata.txt")]
    folder_result["files_found"] = len(text_files)

    if not text_files:
      self.logger.warning(f"⚠️ No text files found in {patient_folder.name}")
      return folder_result

    self.logger.info(f"📄 Found {len(text_files)} text files")

    # Group files by claim_id
    claims_data = {}

    for idx, text_file in enumerate(text_files):
      try:
        # Progress update
        self.logger.progress(
          f"Processing file {idx + 1}/{len(text_files)}",
          current=idx + 1,
          total=len(text_files),
          file=text_file.name
        )

        # Parse filename (2-part format)
        parsed = self.parse_filename(text_file.name)
        if not parsed:
          self.logger.warning(f"⚠️ Invalid filename format: {text_file.name}")
          folder_result["skipped_files"].append(text_file.name)
          folder_result["files_skipped"] += 1
          continue

        patient_initials, claim_id, document_type = parsed

        # Read file content
        with open(text_file, 'r', encoding='utf-8') as f:
          content = f.read().strip()

        # Check minimum content length
        min_length = self.text_settings.get('min_content_length', 50)
        if len(content) < min_length:
          self.logger.warning(f"⚠️ Content too short ({len(content)} chars): {text_file.name}")
          folder_result["skipped_files"].append(text_file.name)
          folder_result["files_skipped"] += 1
          continue

        # Extract encounter date
        encounter_date = self.extract_date_from_content(content)

        # Get file timestamp
        file_timestamp = datetime.fromtimestamp(text_file.stat().st_mtime).isoformat()

        # Group by claim_id
        if claim_id not in claims_data:
          claims_data[claim_id] = {
            'claim_id': claim_id,
            'patient_initials': patient_initials,
            'documents': {}
          }

        # Group documents by type (for handling duplicates)
        if document_type not in claims_data[claim_id]['documents']:
          claims_data[claim_id]['documents'][document_type] = []

        claims_data[claim_id]['documents'][document_type].append({
          'content': content,
          'document_type': document_type,
          'encounter_date': encounter_date,
          'file_timestamp': file_timestamp,
          'source_file': text_file.name
        })

        folder_result["files_processed"] += 1

      except Exception as e:
        self.logger.error(f"❌ Error processing {text_file.name}: {e}")
        folder_result["skipped_files"].append(text_file.name)
        folder_result["files_skipped"] += 1

    # Create JSON files for each claim
    script_dir = Path(__file__).parent.resolve()
    if Path(output_dir).is_absolute():
      output_path = Path(output_dir)
    else:
      output_path = script_dir / output_dir

    output_path.mkdir(parents=True, exist_ok=True)

    encounter_counter = 0

    for claim_id, claim_data in claims_data.items():
      try:
        # Create encounters list
        encounters = []

        for doc_type, documents in claim_data['documents'].items():
          # Merge duplicate document types if needed
          if len(documents) > 1:
            merged_doc = self.merge_duplicate_documents(documents)
          else:
            merged_doc = documents[0]

          # Create encounter entry
          encounter_counter += 1
          encounter_id = f"encounter_{encounter_counter:03d}"

          encounter_entry = {
            "encounter_id": encounter_id,
            "document_type": merged_doc['document_type'],
            "document_text": merged_doc['content'],
            "encounter_date": merged_doc['encounter_date'],
            "processing_metadata": {
              "source_files": merged_doc.get('source_files', [merged_doc.get('source_file', '')]),
              "processing_timestamp": datetime.now().isoformat(),
              "processor": "text_file_processor"
            }
          }

          encounters.append(encounter_entry)

        # Create unified JSON output
        unified_output = {
          "claim_id": claim_id,
          "patient_initials": patient_initials,
          "patient_metadata": patient_metadata,
          "encounters": encounters,
          "processing_metadata": {
            "source_type": "text_file_processor",
            "processing_timestamp": datetime.now().isoformat(),
            "patient_folder": patient_folder.name,
            "encounters_processed": len(encounters),
            "text_files_combined": folder_result["files_processed"]
          }
        }

        # Create output filename: {patient_initials}_{claim_id}.json
        output_filename = f"{patient_initials.lower()}_{claim_id}.json"
        output_file = output_path / output_filename

        # Save JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
          json.dump(unified_output, f, indent=2, ensure_ascii=False)

        folder_result["created_files"].append(str(output_file))
        folder_result["claims_created"] += 1

        self.logger.info(f"✅  Created: {output_filename}")
        self.logger.milestone(
          f"Created claim JSON: {output_filename}",
          status='success',
          claim_id=claim_id,
          encounters=len(encounters)
        )

      except Exception as e:
        self.logger.error(f"❌ Failed to create JSON for claim {claim_id}: {e}")

    return folder_result

  def extract_date_from_content (self, text: str) -> str:
    """Extract date from document content"""
    # Common date patterns
    date_patterns = [
      r'Date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
      r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
      r'(\w+ \d{1,2},?\s*\d{4})',
      r'(\d{4}-\d{2}-\d{2})'
    ]

    for pattern in date_patterns:
      match = re.search(pattern, text, re.IGNORECASE)
      if match:
        found_date = match.group(1)
        self.logger.debug_file_processing(f"Extracted date: {found_date}")
        return found_date

    self.logger.debug_file_processing("No date found in content, using 'unknown'")
    return "unknown"

  def load_and_validate_file (self, file_path: Path) -> Optional[Dict]:
    """Load file content and validate"""
    try:
      file_start_time = perf_counter()

      # Get encoding from config
      encoding = self.text_settings.get('encoding', 'utf-8')

      # Read file content
      with open(file_path, 'r', encoding=encoding) as f:
        content = f.read().strip()

      # Validate content length
      min_length = self.text_settings.get('min_content_length', 50)
      if len(content) < min_length:
        self.logger.warning(
          f"File content too short ({len(content)} chars < {min_length}): {file_path.name}")
        self.metrics.record_file_skipped()
        return None

      # Get file timestamp
      file_timestamp = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()

      # Parse filename
      parse_result = self.parse_filename(file_path.name)
      if not parse_result:
        self.logger.warning(f"Could not parse filename: {file_path.name}")
        self.metrics.record_file_skipped()
        return None

      patient_initials, claim_id, document_type = parse_result

      # Extract date from content
      encounter_date = self.extract_date_from_content(content)

      file_data = {
        'content': content,
        'document_type': document_type,
        'claim_id': claim_id,
        'patient_initials': patient_initials,
        'encounter_date': encounter_date,
        'file_timestamp': file_timestamp,
        'source_file': file_path.name,
        'processing_time': perf_counter() - file_start_time,
        'character_count': len(content)
      }

      self.logger.debug_file_processing(
        f"Loaded file: {file_path.name} ({len(content)} chars, "
        f"type: {document_type}, claim: {claim_id})"
      )

      return file_data

    except Exception as e:
      self.logger.error(f"Error loading file {file_path}: {e}")
      self.metrics.record_file_skipped()
      return None

  def merge_duplicate_documents (self, documents: List[Dict]) -> Dict:
    """Merge documents of same type with timestamp sections"""
    if len(documents) == 1:
      return documents[0]

    self.logger.debug_file_processing(f"Merging {len(documents)} duplicate documents")

    # Sort by file modification time or content order
    documents.sort(key=lambda x: x.get('file_timestamp', ''))

    merged_content = ""
    source_files = []

    for i, doc in enumerate(documents):
      timestamp = doc.get('file_timestamp', f'Document_{i + 1}')
      merged_content += f"[Document {i + 1} - {timestamp}]\n"
      merged_content += doc['content']
      source_files.append(doc['source_file'])

      if i < len(documents) - 1:
        merged_content += "\n\n--- ADDITIONAL DOCUMENT ---\n\n"

    # Return merged document with latest timestamp
    merged_doc = {
      'content': merged_content,
      'document_type': documents[0]['document_type'],
      'encounter_date': documents[-1].get('encounter_date', 'unknown'),
      'file_timestamp': documents[-1].get('file_timestamp', ''),
      'source_files': source_files,
      'character_count': len(merged_content)
    }

    self.logger.debug_file_processing(
      f"Merged into {len(merged_content)} chars from {len(source_files)} files")

    return merged_doc

  def create_encounter_from_document (self, document: Dict, encounter_counter: int) -> Dict:
    """Create encounter entry from document data"""
    # Generate encounter ID
    doc_type = document['document_type']
    encounter_id = f"encounter_{doc_type}_{encounter_counter:03d}"

    # Create encounter entry compatible with pipeline
    encounter_entry = {
      "encounter_id": encounter_id,
      "document_type": doc_type,
      "document_text": document['content'],
      "encounter_date": document['encounter_date'],
      "source_file": document.get('source_files', [document.get('source_file', '')])
    }

    # Add metadata if multiple source files
    if isinstance(encounter_entry['source_file'], list) and len(encounter_entry['source_file']) > 1:
      encounter_entry['encounter_metadata'] = {
        "merged_from_files": encounter_entry['source_file'],
        "merge_timestamp": datetime.now().isoformat()
      }

    self.logger.debug_encounter_details(encounter_entry, document.get('claim_id', ''))

    return encounter_entry

  def group_files_by_claim (self, file_data_list: List[Dict]) -> Dict:
    """Group processed file data by claim"""
    claims_data = {}

    self.logger.debug_json_creation(f"Grouping {len(file_data_list)} files by claim")

    for file_data in file_data_list:
      claim_id = file_data['claim_id']
      patient_initials = file_data['patient_initials']
      document_type = file_data['document_type']

      # Create claim key
      claim_key = f"{patient_initials}_{claim_id}"

      # Initialize claim data if needed
      if claim_key not in claims_data:
        claims_data[claim_key] = {
          'claim_id': claim_id,
          'patient_initials': patient_initials,
          'documents': {}
        }
        self.logger.debug_json_creation(f"Created claim group: {claim_key}")

      # Initialize document type if needed
      if document_type not in claims_data[claim_key]['documents']:
        claims_data[claim_key]['documents'][document_type] = []

      # Add document to claim
      claims_data[claim_key]['documents'][document_type].append(file_data)

      self.logger.debug_json_creation(
        f"Added {document_type} to claim {claim_key} "
        f"({len(claims_data[claim_key]['documents'][document_type])} docs of this type)"
      )

    self.logger.debug_json_creation(f"Created {len(claims_data)} claim groups")
    return claims_data

  def create_unified_json_output (self, claim_data: Dict, encounter_counter: int) -> Tuple[
    Dict, int]:
    """Create unified JSON output for a claim"""
    claim_id = claim_data['claim_id']
    patient_initials = claim_data['patient_initials']

    self.logger.debug_json_creation(f"Creating unified JSON for claim: {claim_id}")

    encounters = []

    # Process each document type
    for doc_type, documents in claim_data['documents'].items():
      self.logger.debug_json_creation(f"Processing {len(documents)} documents of type: {doc_type}")

      # Merge duplicates if necessary and enabled
      if len(documents) > 1 and self.quality_settings.get('merge_duplicate_document_types', True):
        merged_doc = self.merge_duplicate_documents(documents)
        self.logger.debug_json_creation(f"Merged {len(documents)} documents into 1")
      else:
        merged_doc = documents[0]  # Take first document if no merging

      # Create encounter entry
      encounter_counter += 1
      encounter_entry = self.create_encounter_from_document(merged_doc, encounter_counter)
      encounters.append(encounter_entry)

      self.logger.debug_json_creation(f"Created encounter: {encounter_entry['encounter_id']}")

    # Create unified JSON output compatible with pipeline
    unified_output = {
      "claim_id": claim_id,
      "patient_initials": patient_initials,
      "encounters": encounters,
      "processing_metadata": {
        "source_type": "text_file_processor",
        "processing_timestamp": datetime.now().isoformat(),
        "total_encounters": len(encounters),
        "processor_version": "enhanced_v3.0"
      }
    }

    self.logger.debug_json_creation(
      f"Created unified JSON with {len(encounters)} encounters for claim {claim_id}"
    )

    return unified_output, encounter_counter

  def save_json_file (self, unified_output: Dict, output_dir: str) -> Optional[str]:
    """Save unified JSON file"""
    try:
      # Create output directory
      script_dir = Path(__file__).parent.resolve()

      if Path(output_dir).is_absolute():
        output_path = Path(output_dir)
      else:
        output_path = script_dir / output_dir

      output_path.mkdir(parents=True, exist_ok=True)

      # Create output filename using template
      filename_template = self.config.config.get('filename_templates', {}).get(
        'json_conversion', '{patient_initials}_{claim_id}.json'
      )

      output_filename = filename_template.format(
        claim_id=unified_output['claim_id'],
        patient_initials=unified_output['patient_initials']
      )

      output_file = output_path / output_filename

      # Save JSON file
      with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_output, f, indent=2, ensure_ascii=False)

      self.logger.debug_json_creation(f"Saved JSON file: {output_file}")
      self.logger.success(f"Created: {output_filename}")

      return str(output_file)

    except Exception as e:
      self.logger.error(f"Error saving JSON file: {e}")
      return None

  def generate_processing_report (self, results: Dict, output_dir: str):
    """Generate detailed processing report"""
    try:
      # Create report data
      report_data = {
        "processing_summary": {
          "timestamp": datetime.now().isoformat(),
          "input_directory": results['input_dir'],
          "output_directory": output_dir,
          "processing_duration": results.get('processing_duration', 0),
          "files_found": self.processing_report['total_files_found'],
          "files_processed": self.processing_report['files_processed'],
          "files_skipped": self.processing_report['files_skipped'],
          "claims_created": self.processing_report['claims_created'],
          "success_rate": (self.processing_report['files_processed'] /
                           max(self.processing_report['total_files_found'], 1)) * 100
        },
        "metrics": self.metrics.get_efficiency_metrics(),
        "file_statistics": self.metrics.file_stats,
        "skipped_files": self.processing_report['skipped_files'],
        "created_files": results.get('created_files', [])
      }

      # Create reports subdirectory
      script_dir = Path(__file__).parent.resolve()
      if Path(output_dir).is_absolute():
        output_path = Path(output_dir)
      else:
        output_path = script_dir / output_dir

      reports_dir = output_path / "reports"
      reports_dir.mkdir(parents=True, exist_ok=True)

      # Generate filename with timestamp
      timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
      report_filename = f"3_process-combine_text_to_json-report_{timestamp}.json"
      report_file = reports_dir / report_filename

      with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

      self.logger.debug_json_creation(f"Generated processing report: {report_file}")

    except Exception as e:
      self.logger.warning(f"Could not generate processing report: {e}")

  def process_text_files (self, input_dir: str, output_dir: str = None, limit: int = None) -> Dict:
    """Main processing method - convert text files to unified JSON format"""
    processing_start_time = perf_counter()

    self.logger.info("== STARTING TEXT FILE PROCESSING ============================")
    self.logger.milestone("Text file processing started", status='info')

    if limit:
      self.logger.info(f"🔢 Processing limit: {limit} files")

    script_dir = Path(__file__).parent.resolve()
    # Resolve input directory relative to script if not absolute
    if Path(input_dir).is_absolute():
      input_path = Path(input_dir)
    else:
      input_path = script_dir / input_dir

    self.logger.info(f"📂 Input directory: {input_path}")

    # Set default output directory if needed
    if output_dir is None:
      output_dir = self.processing_settings.get('default_output_dir',
                                                './output/3_process-combine_text_to_json')

    # Resolve output directory relative to script if not absolute
    if Path(output_dir).is_absolute():
      output_path = Path(output_dir)
    else:
      output_path = script_dir / output_dir

    self.logger.info(f"📂 Output directory: {output_path}")

    try:
      # Check if input directory exists
      if not input_path.exists():
        self.logger.error(f"Input directory does not exist: {input_path}")
        return self._create_empty_results(str(input_path), str(output_path))

      # Find all subdirectories (patient folders)
      patient_folders = [d for d in input_path.iterdir() if d.is_dir()]

      if not patient_folders:
        self.logger.warning(f"No patient folders found in {input_path}")
        return self._create_empty_results(str(input_path), str(output_path))

      self.logger.info(f"📂 Found {len(patient_folders)} patient folders")

      # Apply limit if specified
      if limit and limit > 0:
        patient_folders = patient_folders[:limit]
        self.logger.info(f"🔢 Limited to first {limit} patient folders")

      # Process each patient folder
      all_results = []
      total_claims = 0
      total_files = 0

      for folder_idx, patient_folder in enumerate(patient_folders):
        self.logger.info(f"{'-' * 60}")
        self.logger.progress(
          f"Processing patient folder {folder_idx + 1}/{len(patient_folders)}",
          current=folder_idx + 1,
          total=len(patient_folders),
          folder=patient_folder.name
        )

        folder_result = self.process_patient_folder(patient_folder, str(output_path))
        all_results.append(folder_result)

        total_claims += folder_result["claims_created"]
        total_files += folder_result["files_processed"]

        # Update metrics
        self.metrics.record_file_processing(
          processing_time=1.0,  # Placeholder
          success=folder_result["claims_created"] > 0,
          characters_processed=0,  # Could be calculated if needed
          encounters_created=folder_result["claims_created"]
        )

        # Output stats every 5 folders
        if (folder_idx + 1) % 5 == 0:
          self.metrics.output_stats()

      # Calculate processing duration
      processing_duration = perf_counter() - processing_start_time

      # Aggregate statistics for metrics tracking
      total_successful = sum(1 for r in all_results if r["claims_created"] > 0)
      total_failed = sum(1 for r in all_results if r["claims_created"] == 0)
      total_skipped = sum(r["files_skipped"] for r in all_results)

      # Update processing report
      self.processing_report.update({
        "total_files_found": total_files,
        "files_processed": total_files,
        "files_skipped": total_skipped,
        "claims_created": total_claims,
        "skipped_files": [{"file": f, "reason": "See folder results"} for r in all_results for f
                          in r.get("skipped_files", [])]
      })

      # Update metrics
      self.metrics.file_stats.update({
        "files_processed": len(all_results),
        "files_successful": total_successful,
        "files_failed": total_failed,
        "files_skipped": total_skipped,
        "claims_created": total_claims,
        "encounters_created": total_claims,
        "total_content_characters": 0
      })

      # Create results summary
      results = {
        "success": total_claims > 0,
        "input_dir": str(input_path),
        "output_dir": str(output_path),
        "processing_duration": processing_duration,
        "patient_folders_found": len(patient_folders),
        "patient_folders_processed": len(all_results),
        "total_files_processed": total_files,
        "total_claims_created": total_claims,
        "folder_results": all_results,
        "created_files": [f for r in all_results for f in r.get("created_files", [])],
        "processing_summary": self.processing_report
      }

      # Print summary
      # self.logger.info(f"\n{'=' * 60}")
      # self.logger.info("=== PROCESSING COMPLETE ===")
      # self.logger.info(f"📂 Patient folders processed: {len(all_results)}")
      # self.logger.info(f"📄 Total files processed: {total_files}")
      # self.logger.info(f"📋 Total claims created: {total_claims}")
      # self.logger.info(f"⏱️ Total processing time: {processing_duration:.2f} seconds")
      # self.logger.info(f"{'=' * 60}")

      # Milestone for completion
      self.logger.milestone(
        "Text file processing complete",
        status='success',
        folders_processed=len(all_results),
        files_processed=total_files,
        claims_created=total_claims,
        duration_seconds=round(processing_duration, 2)
      )

      # Generate processing report
      self.generate_processing_report(results, output_dir)

      # Print metrics summary
      self.metrics.print_summary()

      # Final stats output
      self.metrics.output_stats()

      # Print final summary
      # self.logger.info(f"{'=' * 60}")
      self.logger.info("== TEXT FILE PROCESSING COMPLETE ==========================")
      self.logger.info(f"📂 Patient folders processed: {len(all_results)}")
      self.logger.info(f"📄 Total files processed: {total_files}")
      self.logger.info(f"📋 Total claims created: {total_claims}")
      self.logger.info(f"⏱️ Total processing time: {processing_duration:.2f} seconds")
      # self.logger.info(f"{'=' * 60}")

      return results

    except Exception as e:
      self.logger.error(f"Processing failed: {e}")
      import traceback
      traceback.print_exc()

      if self.error_settings.get('save_partial_results', True):
        # Try to save what we have so far
        processing_duration = perf_counter() - processing_start_time
        return {
          "success": False,
          "error": str(e),
          "input_dir": input_dir,
          "output_dir": output_dir,
          "processing_duration": processing_duration,
          "partial_results": True
        }
      else:
        raise

  def _create_empty_results (self, input_dir: str, output_dir: str) -> Dict:
    """Create empty results structure"""
    return {
      "success": False,
      "input_dir": input_dir,
      "output_dir": output_dir,
      "processing_duration": 0,
      "files_found": 0,
      "files_processed": 0,
      "files_skipped": 0,
      "claims_created": 0,
      "created_files": [],
      "skipped_files": [],
      "error": "No files to process"
    }


# PART 3: CLI INTERFACE AND MAIN APPLICATION

def setup_argument_parser () -> argparse.ArgumentParser:
  """Setup command line argument parser"""

  parser = argparse.ArgumentParser(
    description="Enhanced Text File Processor - Convert text files to unified JSON for claims analysis",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  # Process all patient folders in input directory (uses config file paths)
  python 3_process-combine_text_to_json.py --limit 1

  # Process with custom input/output directories
  python 3_process-combine_text_to_json.py --input-dir "input/text_data" --output-dir "./output/" --limit 5

  # Process with verbose logging
  python 3_process-combine_text_to_json.py --verbose

  # Process with custom config file
  python 3_process-combine_text_to_json.py --config "custom_config.yaml"

  # Process with JSON output mode 
  python 3_process-combine_text_to_json.py --json-output

  # JSON mode with silent stderr
  python 3_process-combine_text_to_json.py --json-output 2>/dev/null

Input Format:
  Directory Structure:
    input/text_data/
    ├── Patient_MR/
    │   ├── mr_metadata.txt (required - contains patient_initials, age, gender, name)
    │   ├── 2024-MC-087432_phone_transcript.txt
    │   ├── 2024-MC-087432_medical_provider_letter.txt
    │   └── 2024-MC-087433_adjuster_notes_initial.txt
    └── Patient_JS/
        ├── js_metadata.txt
        └── 2024-MC-100001_claimant_statement.txt

  File Naming Pattern: {patient_initials}_{claim_id}_{document_type}.txt
  Metadata File Pattern: {patient_initials}_metadata.txt

  Examples:
    - 2024-MC-087432_phone_transcript.txt
    - 2024-MC-087432_medical_provider_letter.txt
    - CLM001_adjuster_notes_initial.txt
    - mr_metadata.txt (contains patient_initials: mr)

Output Structure:
  Filename: {patient_initials}_{claim_id}.json
  Example: mr_2024-MC-087432.json

  JSON Content:
    - claim_id: Unique identifier for the claim
    - patient_initials: Patient initials from metadata file
    - patient_metadata: Full metadata (age, gender, name, patient_initials)
    - encounters: List of documents grouped by claim
    - processing_metadata: Processing details with source_type="text_file_processor"

Processing Logic:
  - Each subfolder in input directory = 1 patient
  - Files in each folder are grouped by claim_id
  - One JSON file created per claim
  - Multiple claims per patient are supported

Configuration:
  Place config file at: ./config/3_process-combine_text_to_json.yaml
  Includes:
    - Default input/output directories
    - Document type mappings
    - Quality control settings
    - Error handling options
        """
  )

  # Input/Output arguments
  parser.add_argument(
    "--input-dir",
    required=False,
    help="Directory containing text files to process"
  )
  parser.add_argument(
    "--output-dir",
    help="Output directory for JSON files (default: ./output/3_process-combine_text_to_json/)"
  )
  parser.add_argument(
    "--config",
    help="Path to configuration file (default: config/3_process-combine_text_to_json.yaml)"
  )

  # Processing options
  parser.add_argument(
    "--limit",
    type=int,
    help="Limit number of files to process (for testing)"
  )
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

  # Testing options
  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Validate inputs and configuration without processing"
  )

  # JSON output mode
  parser.add_argument(
    "--json-output",
    action="store_true",
    help="Enable JSON output mode (structured events on stdout, messages on stderr)"
  )

  return parser


def validate_arguments (args) -> bool:
  """Validate command line arguments"""

  # If input_dir not provided, we'll get it from config later
  if args.input_dir is None:
    print("📁 Input directory will be loaded from config file", file=sys.stderr)
    return True

  # Validate input directory
  input_path = Path(args.input_dir)
  if not input_path.exists():
    print(f"❌ Error: Input directory does not exist: {args.input_dir}", file=sys.stderr)
    return False

  if not input_path.is_dir():
    print(f"❌ Error: Input path is not a directory: {args.input_dir}", file=sys.stderr)
    return False

  # Check for text files
  text_files = list(input_path.glob("*.txt"))
  if not text_files:
    print(f"❌ Error: No text files found in: {args.input_dir}", file=sys.stderr)
    return False

  print(f"📁 Input directory validated: {len(text_files)} text files found", file=sys.stderr)

  # Validate output directory (create if needed)
  if args.output_dir:
    try:
      output_path = Path(args.output_dir)
      output_path.mkdir(parents=True, exist_ok=True)
      print(f"📂 Output directory: {output_path}", file=sys.stderr)
    except Exception as e:
      print(f"❌ Error: Cannot create output directory {args.output_dir}: {e}", file=sys.stderr)
      return False

  # Validate limit
  if args.limit and args.limit < 1:
    print("❌ Error: --limit must be positive", file=sys.stderr)
    return False

  return True


def print_startup_banner ():
  """Print startup banner with version info"""
  print("🚀 Enhanced Text File Processor v3.0", file=sys.stderr)
  print("=" * 60, file=sys.stderr)
  print("📄 Converts text files to unified JSON for claims analysis", file=sys.stderr)
  print("🔧 Enhanced with modern infrastructure and metrics tracking", file=sys.stderr)
  print("📊 No LLM API calls - pure text processing and conversion", file=sys.stderr)
  print("🔗 Compatible with Claims Analysis Pipeline (Scripts 1, 2, 4)", file=sys.stderr)
  print("-" * 60, file=sys.stderr)


def print_completion_banner (success: bool, start_time: float, logger):
  """Print completion banner with timing"""
  elapsed_time = time.time() - start_time

  logger.info("=" * 60)
  if success:
    logger.info("✅  PROCESSING COMPLETED SUCCESSFULLY")
  else:
    logger.info("❌ PROCESSING COMPLETED WITH ERRORS")
  # logger.info("=" * 60)
  logger.info(f"⏱️ Total elapsed time: {elapsed_time:.1f} seconds")
  logger.info(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  logger.info("=" * 60)

def main ():
  """Main execution function with comprehensive error handling"""
  start_time = time.time()

  try:
    # Print startup banner
    print_startup_banner()

    # Parse arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Validate arguments
    if not args.skip_validation:
      print("🔍 Validating input arguments...", file=sys.stderr)
      if not validate_arguments(args):
        return EXIT_VALIDATION_ERROR
      print("✅ Arguments validated successfully", file=sys.stderr)

    # Load configuration
    print("🔧 Loading configuration...", file=sys.stderr)
    config = ClassConfig(args.config)
    print(f"✅ Configuration loaded from: {config.config_path}", file=sys.stderr)

    # Setup logging with JSON mode if requested
    logger = ClassLogger(config, json_mode=args.json_output)
    if args.verbose:
      logger.logger.setLevel(logging.DEBUG)
      logger.debug("Debug logging enabled")

    # Log JSON mode status
    if args.json_output:
      print("📊 JSON output mode enabled (events on stdout, messages on stderr)", file=sys.stderr)

    # Initialize processor
    print("🚀 Initializing text file processor...", file=sys.stderr)
    processor = ClassProcessTextDocuments(config, logger)

    # Print processing info
    logger.info("🚀 Enhanced Text File Processor started")
    logger.info(f"📁 Working directory: {Path.cwd()}")
    logger.info(f"🔧 Config file: {config.config_path}")

    # Dry run mode
    if args.dry_run:
      logger.info("🔍 DRY RUN MODE - Validating configuration only")
      logger.info("✅ Configuration validation complete")
      logger.info("💡 Remove --dry-run to process files")
      return EXIT_SUCCESS

    # Process files
    # logger.info("📄 Starting text file processing...")

    # Get input/output directories
    input_dir = args.input_dir if args.input_dir else processor.processing_settings.get(
      'input_folder', 'input/text_data')
    output_dir = args.output_dir if args.output_dir else processor.processing_settings.get(
      'default_output_dir', './output/3_process-combine_text_to_json')

    # Call process_text_files directly
    results = processor.process_text_files(
      input_dir=input_dir,
      output_dir=output_dir,
      limit=args.limit
    )

    # Check success
    success = results.get('success', False) and results.get('total_claims_created', 0) > 0

    # Print completion banner
    print_completion_banner(success, start_time, logger)

    return EXIT_SUCCESS if success else EXIT_PROCESSING_ERROR

  except KeyboardInterrupt:
    print("\n⚠️ Processing interrupted by user", file=sys.stderr)
    return EXIT_SUCCESS
  except Exception as e:
    print(f"❌ Fatal error: {e}", file=sys.stderr)
    traceback.print_exc()
    return EXIT_PROCESSING_ERROR


if __name__ == "__main__":
  exit_code = main()
  sys.exit(exit_code)