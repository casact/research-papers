# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# This software was developed and implemented by MDSight, LLC
# with project management by Lieberthal & Associates, LLC
# and funding from the Casualty Actuarial Society.

# =========================================================================
# category/orchestrator.py
# =========================================================================

# Import all the template functions
from .specialized.template_phone_transcript import create_phone_transcript_specialized_prompt
from .specialized.template_adjuster_notes import create_adjuster_notes_specialized_prompt
from .specialized.template_medical_provider import create_medical_provider_specialized_prompt
from .specialized.template_settlement_notes import create_settlement_notes_specialized_prompt
from .specialized.template_claimant_statement import create_claimant_statement_specialized_prompt
from .specialized.template_clinical_notes import create_clinical_notes_specialized_prompt

from .category.template_medical import create_medical_category_prompt
from .category.template_legal import create_legal_category_prompt
from .category.template_investigation import create_investigation_category_prompt
from .category.template_workplace import create_workplace_category_prompt
from .category.template_financial import create_financial_category_prompt
from .category.template_external import create_external_category_prompt

from .universal.template_universal import create_universal_fallback_prompt

class CategoryTemplateOrchestrator:
    """
    Orchestrates the selection and application of category-based extraction templates
    for different document types in actuarial claims analysis.
    """

    def __init__(self):
        # Document type to category mappings
        self.category_mappings = {
            # Medical Category
            "hospital_discharge_summary": "medical",
            "ime_report": "medical",
            "physical_therapy_notes": "medical",
            "psychiatric_evaluation": "medical",
            "pharmacy_records": "medical",
            "diagnostic_test_results": "medical",
            "specialist_consultation_notes": "medical",
            "rehabilitation_reports": "medical",
            "nursing_notes": "medical",
            "emergency_room_records": "medical",

            # Legal Category
            "attorney_correspondence": "legal",
            "court_filings": "legal",
            "depositions": "legal",
            "expert_witness_reports": "legal",
            "settlement_agreements": "legal",
            "subrogation_files": "legal",
            "legal_pleadings": "legal",
            "arbitration_records": "legal",
            "mediation_reports": "legal",
            "litigation_correspondence": "legal",

            # Investigation Category
            "investigation_reports": "investigation",
            "surveillance_reports": "investigation",
            "witness_statements": "investigation",
            "scene_investigation": "investigation",
            "background_checks": "investigation",
            "fraud_investigation_reports": "investigation",
            "special_investigation_unit_reports": "investigation",
            "accident_reconstruction_reports": "investigation",
            "claim_investigation_summary": "investigation",
            "interviewer_notes": "investigation",

            # Workplace Category
            "employer_incident_reports": "workplace",
            "safety_training_records": "workplace",
            "job_descriptions": "workplace",
            "return_to_work_documentation": "workplace",
            "osha_reports": "workplace",
            "workplace_safety_inspections": "workplace",
            "employee_handbook_excerpts": "workplace",
            "disciplinary_records": "workplace",
            "safety_committee_minutes": "workplace",
            "ergonomic_assessments": "workplace",

            # Financial Category
            "wage_statements": "financial",
            "financial_records": "financial",
            "business_interruption_documentation": "financial",
            "loss_calculations": "financial",
            "audit_reports": "financial",
            "tax_returns": "financial",
            "employment_verification": "financial",
            "benefit_statements": "financial",
            "payroll_records": "financial",
            "economic_loss_reports": "financial",

            # External Category
            "police_reports": "external",
            "weather_reports": "external",
            "news_articles": "external",
            "government_records": "external",
            "regulatory_correspondence": "external",
            "environmental_assessments": "external",
            "traffic_reports": "external",
            "public_records": "external",
            "municipal_reports": "external",
            "third_party_documentation": "external"
        }

        # Category template functions
        self.category_templates = {
            "medical": create_medical_category_prompt,
            "legal": create_legal_category_prompt,
            "investigation": create_investigation_category_prompt,
            "workplace": create_workplace_category_prompt,
            "financial": create_financial_category_prompt,
            "external": create_external_category_prompt
        }

        # Specialized template functions
        self.specialized_templates = {
            "phone_transcript": create_phone_transcript_specialized_prompt,
            "adjuster_notes_initial": create_adjuster_notes_specialized_prompt,
            "medical_provider_letter": create_medical_provider_specialized_prompt,
            "settlement_notes": create_settlement_notes_specialized_prompt,
            "claimant_statement": create_claimant_statement_specialized_prompt,
            "clinical_notes": create_clinical_notes_specialized_prompt
        }

        # Specialized document types
        self.specialized_types = set(self.specialized_templates.keys())

    # Add this method to CategoryTemplateOrchestrator class in templates/orchestrator.py

    def _match_document_type_intelligently (self, document_type):
        """
        Intelligently match document types using keyword matching with priority.
        Returns the appropriate specialized template key or None if no match.
        """
        document_type_lower = document_type.lower()

        # Priority-based matching rules (order matters - higher priority first)
        matching_rules = [
            # Settlement has highest priority for adjuster notes
            {
                "keywords": ["settlement"],
                "required": ["adjuster"],
                "template": "settlement_notes",
                "priority": 1
            },
            # Phone/transcript matching
            {
                "keywords": ["phone", "transcript"],
                "required": [],
                "template": "phone_transcript",
                "priority": 2
            },
            # Medical provider matching
            {
                "keywords": ["medical", "provider", "doctor", "physician"],
                "required": ["letter", "report", "note", "summary"],
                "template": "medical_provider_letter",
                "priority": 2
            },
            # Claimant statement matching
            {
                "keywords": ["claimant"],
                "required": [],
                "template": "claimant_statement",
                "priority": 2
            },
            # Clinical notes matching
            {
                "keywords": ["clinical"],
                "required": [],
                "template": "clinical_notes",
                "priority": 2
            },
            # General adjuster notes (lower priority - after settlement)
            {
                "keywords": ["adjuster"],
                "required": ["notes", "investigation"],
                "template": "adjuster_notes_initial",
                "priority": 3
            },
            # Fallback adjuster (even lower priority)
            {
                "keywords": ["adjuster"],
                "required": [],
                "template": "adjuster_notes_initial",
                "priority": 4
            }
        ]

        # Sort by priority (lower number = higher priority)
        matching_rules.sort(key=lambda x: x["priority"])

        # Try each rule in priority order
        for rule in matching_rules:
            # Check if all keywords are present
            keywords_match = any(keyword in document_type_lower for keyword in rule["keywords"])

            # Check if all required terms are present
            required_match = all(req in document_type_lower for req in rule["required"])

            # If both conditions met, return this template
            if keywords_match and required_match:
                return rule["template"]

        return None  # No intelligent match found

    def get_extraction_strategy (self, document_type):
        """
        Determine which extraction strategy to use for a given document type.
        Now with intelligent matching fallback.
        """
        # First, try exact match with specialized templates
        if document_type in self.specialized_types:
            return ("specialized", self.specialized_templates[document_type])

        # Second, try intelligent matching
        intelligent_match = self._match_document_type_intelligently(document_type)
        if intelligent_match and intelligent_match in self.specialized_templates:
            return ("specialized", self.specialized_templates[intelligent_match])

        # Third, try category mappings
        elif document_type in self.category_mappings:
            category = self.category_mappings[document_type]
            template_func = self.category_templates[category]
            return ("category", template_func)

        # Finally, use universal fallback
        else:
            return ("universal", create_universal_fallback_prompt)

    def get_extraction_prompt(self, document_text, document_type, specialized_prompt_func=None):
        """
        Get the appropriate extraction prompt for a document.

        Args:
            document_text: The text content of the document
            document_type: The type/category of the document
            specialized_prompt_func: Function to get specialized prompts (your existing function)

        Returns:
            str: The extraction prompt for the LLM
        """
        strategy, template_func = self.get_extraction_strategy(document_type)

        if strategy == "specialized":
            # Use the imported specialized template function directly
            return template_func(document_text)
        elif strategy == "category":
            # Use category-based template
            return template_func(document_text, document_type)
        elif strategy == "universal":
            # Use universal fallback template
            return create_universal_fallback_prompt(document_text, document_type)
        else:
            raise ValueError(f"Unknown extraction strategy: {strategy}")


    def add_document_type_mapping(self, document_type, category):
        """
        Add a new document type to category mapping.

        Args:
            document_type: The new document type
            category: The category it should map to
        """
        if category not in self.category_templates:
            raise ValueError(f"Unknown category: {category}. Available: {list(self.category_templates.keys())}")

        self.category_mappings[document_type] = category

    def get_document_categories(self):
        """Get all available document categories."""
        return list(self.category_templates.keys())

    def get_documents_in_category(self, category):
        """Get all document types mapped to a specific category."""
        return [doc_type for doc_type, cat in self.category_mappings.items() if cat == category]

    def get_coverage_statistics(self):
        """Get statistics about document type coverage."""
        total_mapped = len(self.category_mappings)
        by_category = {}

        for category in self.category_templates.keys():
            by_category[category] = len(self.get_documents_in_category(category))

        return {
            "total_specialized_types": len(self.specialized_types),
            "total_category_mapped_types": total_mapped,
            "by_category": by_category,
            "specialized_types": list(self.specialized_types)
        }