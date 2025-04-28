"""
TransferAI Document Service

This module provides a service layer for document operations, acting as a bridge
between the TransferAIEngine and the DocumentRepository. It handles document loading,
transformation, and maintenance of course information caches.
"""

from typing import List, Dict, Any, Optional, Set, Union, Tuple
import json
import os
import re
import time
from pathlib import Path

# Import our Document model wrapper
from llm.models.document import Document 
from llama_index.core import Document as LlamaDocument
from llm.repositories.document_repository import DocumentRepository


# Cache for course data to avoid repeated file reads
_course_cache: Dict[str, Dict[str, Any]] = {}
_json_data: Optional[Dict[str, Any]] = None


class DocumentService:
    """
    Service for document operations in the TransferAI system.
    
    This service acts as a facade over the DocumentRepository, providing
    document loading, transformation, and higher-level operations while
    maintaining a cache of frequently accessed data.
    
    Attributes:
        repository: The underlying DocumentRepository
    """
    
    def __init__(self, repository: Optional[DocumentRepository] = None):
        """
        Initialize the document service.
        
        Args:
            repository: Optional DocumentRepository instance. If None, a new one is created.
        """
        self.repository = repository or DocumentRepository()
        
    def load_documents(self, path: Optional[str] = None) -> int:
        """
        Load articulation documents from the data source.
        
        Args:
            path: Optional path to the document data file
            
        Returns:
            Number of documents loaded
        """
        documents = self._load_documents(path)
        
        # Convert to our Document wrapper if needed
        wrapped_documents = []
        for doc in documents:
            if not isinstance(doc, Document):
                wrapped_documents.append(Document.from_llama_document(doc))
            else:
                wrapped_documents.append(doc)
                
        # Store documents in repository
        self.repository.documents = wrapped_documents
        self.repository._build_course_catalogs()
        self.repository._last_loaded = time.time()
        self.repository.clear_cache()
        
        return len(wrapped_documents)
        
    def _load_json_data(self, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and cache the articulation JSON data.
        
        Args:
            path: Optional path to the JSON data file. If None, defaults to "data/rag_data.json"
                  relative to the project root.
                  
        Returns:
            The parsed JSON data containing articulation information.
        """
        global _json_data
        
        if _json_data is not None:
            return _json_data
            
        if path is None:
            # Try to find the data file relative to current module
            current_dir = os.path.dirname(__file__)
            possible_paths = [
                os.path.join(current_dir, "..", "data", "rag_data.json"),
                os.path.join(current_dir, "..", "..", "data", "rag_data.json"),
                os.path.join(current_dir, "..", "llm", "data", "rag_data.json")
            ]
            
            for p in possible_paths:
                if os.path.exists(p):
                    path = p
                    break
            
            if path is None:
                raise FileNotFoundError("Could not find rag_data.json in any expected location")

        with open(path, "r") as f:
            _json_data = json.load(f)
            
        return _json_data
        
    def _build_course_cache(self) -> None:
        """
        Build a cache of course data from the articulation data.
        
        This function extracts all course information from the articulation database and
        organizes it for quick lookup by course code.
        """
        global _course_cache
        
        if _course_cache:
            return  # Cache already built
            
        data = self._load_json_data()
        
        try:
            # Extract all course information from the groups data
            for group in data.get('groups', []):
                for section in group.get('sections', []):
                    for uc_course in section.get('uc_courses', []):
                        # Process UC course
                        uc_code = uc_course.get('uc_course_id', '')
                        if uc_code:
                            # Store with uppercase course code for consistent lookups
                            _course_cache[uc_code.upper()] = {
                                'title': uc_course.get('uc_course_title', ''),
                                'units': uc_course.get('units', 0.0),
                                'type': 'UC',
                                'original_code': uc_code  # Keep original code for display
                            }
                        
                        # Process associated CCC courses
                        logic_block = uc_course.get('logic_block', {})
                        for option in logic_block.get('courses', []):
                            if option.get('type') == 'AND':
                                for course in option.get('courses', []):
                                    course_code = course.get('course_letters', '')
                                    if course_code and course_code != 'N/A':
                                        # Store with uppercase course code for consistent lookups
                                        _course_cache[course_code.upper()] = {
                                            'title': course.get('title', ''),
                                            'honors': course.get('honors', False),
                                            'name': course.get('name', ''),
                                            'type': 'CCC',
                                            'original_code': course_code  # Keep original code for display
                                        }
        except Exception as e:
            print(f"Error building course cache: {e}")
            # Initialize with empty data rather than failing
            _course_cache = {}

    def get_course_title(self, course_code: str) -> str:
        """
        Get the official title for a course code.
        
        Args:
            course_code: The course code to look up (e.g., "CIS 21JB")
            
        Returns:
            The official course title or an empty string if not found
        """
        if not _course_cache:
            self._build_course_cache()
        
        # Normalize the course code by removing extra spaces and converting to uppercase
        normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
        
        # Try direct lookup first
        course_data = _course_cache.get(normalized_code, {})
        if course_data:
            return course_data.get('title', '')
        
        # If not found, try case-insensitive lookup
        for cached_code, cached_data in _course_cache.items():
            if cached_code.upper() == normalized_code:
                return cached_data.get('title', '')
        
        return ""

    def get_course_description(self, course_code: str) -> str:
        """
        Get a formatted description with course code and title.
        
        Args:
            course_code: The course code to look up (e.g., "CIS 21JB")
            
        Returns:
            A formatted string with the course code and title, or just the code if not found
        """
        if not _course_cache:
            self._build_course_cache()
        
        # Normalize the course code by removing extra spaces and converting to uppercase
        normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
        fallback_code = course_code.strip()  # Use as fallback if not found
        
        # Try direct lookup first
        course_data = _course_cache.get(normalized_code, {})
        if not course_data:
            # If not found, try case-insensitive lookup
            for cached_code, cached_data in _course_cache.items():
                if cached_code.upper() == normalized_code:
                    course_data = cached_data
                    break
        
        title = course_data.get('title', '')
        
        if title:
            is_honors = course_data.get('honors', False)
            honors_suffix = " (Honors)" if is_honors else ""
            # Use original code from cache if available, otherwise use the provided code
            display_code = course_data.get('original_code', fallback_code)
            return f"{display_code}{honors_suffix}: {title}"
        
        return fallback_code

    def extract_ccc_courses_from_logic(self, logic_block: Dict[str, Any]) -> List[str]:
        """
        Extract all CCC course codes from a logic block recursively.
        
        Args:
            logic_block: A dictionary containing the articulation logic structure
        
        Returns:
            A sorted list of unique CCC course codes found in the logic block
        """
        course_codes = set()

        def recurse(node):
            if isinstance(node, list):
                for item in node:
                    recurse(item)
            elif isinstance(node, dict):
                if "type" in node and "courses" in node:
                    # This is an AND/OR logic wrapper
                    recurse(node["courses"])
                else:
                    # This is a course dict
                    code = node.get("course_letters", "").strip()
                    if code and code.upper() != "N/A":
                        course_codes.add(code)

        recurse(logic_block.get("courses", []))
        return sorted(course_codes)

    def flatten_courses_from_json(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert nested articulation JSON into flat document objects for ingestion.
        
        Args:
            json_data: The parsed JSON data containing articulation information
        
        Returns:
            A list of dictionaries, each containing 'text' and 'metadata' keys
        """
        flattened_docs = []

        def summarize_options(logic_block: Dict[str, Any]) -> str:
            """Create a human-readable summary of the options in a logic block."""
            summaries = []
            options = logic_block.get("courses", [])
            for i, option in enumerate(options):
                label = f"Option {chr(65 + i)}"
                if isinstance(option, dict) and option.get("type") == "AND":
                    course_codes = [c.get("course_letters", "UNKNOWN") for c in option.get("courses", [])]
                    summaries.append(f"{label}: " + " + ".join(course_codes))
                else:
                    summaries.append(f"{label}: UNKNOWN FORMAT")
            return "; ".join(summaries)

        def get_course_count(logic_block: Dict[str, Any]) -> int:
            """Get the maximum number of courses required in any single option."""
            options = logic_block.get("courses", [])
            return max(
                len(opt.get("courses", [])) if isinstance(opt, dict) and opt.get("type") == "AND" else 1
                for opt in options
            ) if options else 0

        def has_multi_course_option(logic_block: Dict[str, Any]) -> bool:
            """Check if any option requires multiple courses."""
            for opt in logic_block.get("courses", []):
                if isinstance(opt, dict) and opt.get("type") == "AND" and len(opt.get("courses", [])) > 1:
                    return True
            return False

        for group in json_data.get("groups", []):
            group_id = group.get("group_id")
            group_title = group.get("group_title")
            group_logic_type = group.get("group_logic_type")
            n_courses = group.get("n_courses")

            for section in group.get("sections", []):
                section_id = section.get("section_id")
                section_title = section.get("section_title")

                for course in section.get("uc_courses", []):
                    logic_block = course.get("logic_block", {})
                    no_articulation = logic_block.get("no_articulation", False)
                    uc_id = course.get("uc_course_id", "").replace(":", "").strip()
                    ccc_courses = self.extract_ccc_courses_from_logic(logic_block)

                    enriched_metadata = {
                        "doc_type": "articulation",
                        "uc_course": uc_id,
                        "uc_title": course.get("uc_course_title"),
                        "units": course.get("units"),
                        "group": group_id,
                        "group_title": group_title,
                        "group_logic_type": group_logic_type,
                        "n_courses": n_courses,
                        "section": section_id,
                        "section_title": section_title,
                        "logic_block": logic_block,
                        "no_articulation": no_articulation,
                        "ccc_courses": ccc_courses,
                        "must_complete_at_uc": no_articulation,
                    }

                    # Enrich logic metadata if articulation exists
                    if not no_articulation and isinstance(logic_block, dict):
                        enriched_metadata["logic_type"] = logic_block.get("type", "OR")
                        enriched_metadata["course_count"] = get_course_count(logic_block)
                        enriched_metadata["multi_course_option"] = has_multi_course_option(logic_block)
                        enriched_metadata["options_summary"] = summarize_options(logic_block)
                    else:
                        enriched_metadata["logic_type"] = "OR"
                        enriched_metadata["course_count"] = 0
                        enriched_metadata["multi_course_option"] = False
                        enriched_metadata["options_summary"] = "No articulated course."

                    flattened_docs.append({
                        "text": f"{uc_id} - {course.get('uc_course_title')}\n"
                                f"Group: {group_id} | Section: {section_id}\n"
                                f"Logic Type: {group_logic_type} | N Required: {n_courses or 'N/A'}\n"
                                f"Articulation Logic: {json.dumps(logic_block, indent=2)}",
                        "metadata": enriched_metadata
                    })

        return flattened_docs

    def _load_documents(self, path: Optional[str] = None) -> List[LlamaDocument]:
        """
        Load articulation data and convert to Document objects.
        
        Args:
            path: Optional path to the JSON data file
        
        Returns:
            A list of Document objects
        """
        json_data = self._load_json_data(path)

        # Build the course cache
        self._build_course_cache()

        # Overview doc
        overview = {
            "text": f"Overview:\n{json_data.get('general_advice', '')}",
            "metadata": {
                "doc_type": "overview",
                "title": f"{json_data.get('major', '')} Transfer Overview",
                "source": json_data.get("from", "")
            }
        }

        flat_docs = self.flatten_courses_from_json(json_data)
        all_docs = [overview] + flat_docs

        # Create LlamaDocuments first
        return [LlamaDocument(text=d["text"], metadata=d["metadata"]) for d in all_docs]
        
    def get_uc_course_prefixes(self) -> List[str]:
        """
        Get a list of UC course prefixes.
        
        Returns:
            List of UC department prefixes (e.g., ["CSE", "MATH"])
        """
        uc_catalog, _ = self.repository.get_course_catalogs()
        prefixes = set()
        
        for course in uc_catalog:
            parts = course.split()
            if len(parts) >= 1:
                prefixes.add(parts[0])
                
        return sorted(list(prefixes))
        
    def get_ccc_course_prefixes(self) -> List[str]:
        """
        Get a list of CCC course prefixes.
        
        Returns:
            List of CCC department prefixes (e.g., ["CIS", "MATH"])
        """
        _, ccc_catalog = self.repository.get_course_catalogs()
        prefixes = set()
        
        for course in ccc_catalog:
            parts = course.split()
            if len(parts) >= 1:
                prefixes.add(parts[0])
                
        return sorted(list(prefixes))
        
    def get_course_catalogs(self) -> Tuple[Set[str], Set[str]]:
        """
        Get the UC and CCC course catalogs.
        
        Returns:
            Tuple containing (uc_course_catalog, ccc_course_catalog)
        """
        return self.repository.get_course_catalogs()
        
    def find_documents_by_uc_course(self, uc_course: str) -> List[Document]:
        """
        Find documents for a specific UC course.
        
        Args:
            uc_course: The UC course code to search for
            
        Returns:
            List of documents matching the UC course
        """
        return self.repository.find_by_uc_course(uc_course)
        
    def find_documents_by_ccc_courses(self, 
                                     ccc_courses: List[str], 
                                     require_all: bool = True) -> List[Document]:
        """
        Find documents containing specific CCC courses.
        
        Args:
            ccc_courses: List of CCC course codes to search for
            require_all: If True, all specified courses must be present;
                        if False, matches documents containing any of the courses
            
        Returns:
            List of documents matching the criteria
        """
        return self.repository.find_by_ccc_courses(ccc_courses, require_all)
        
    def find_documents_by_group(self, group_id: str) -> List[Document]:
        """
        Find documents for a specific group.
        
        Args:
            group_id: The group identifier to search for
            
        Returns:
            List of documents matching the group
        """
        return self.repository.find_by_group(group_id)
        
    def find_documents_by_section(self, section_id: str) -> List[Document]:
        """
        Find documents for a specific section.
        
        Args:
            section_id: The section identifier to search for
            
        Returns:
            List of documents matching the section
        """
        return self.repository.find_by_section(section_id)
        
    def find_reverse_matches(self, ccc_course: str) -> List[Document]:
        """
        Find UC courses that can be satisfied by a specific CCC course.
        
        Args:
            ccc_course: The CCC course code to search for
            
        Returns:
            List of UC course documents that can be satisfied by the CCC course
        """
        return self.repository.find_reverse_matches(ccc_course)
        
    def find_documents_by_filter(self, 
                                filters: Dict[str, Any], 
                                limit: Optional[int] = None) -> List[Document]:
        """
        Find documents matching a combination of filters.
        
        Args:
            filters: Dictionary of filter criteria
            limit: Optional maximum number of documents to return
            
        Returns:
            List of documents matching all specified filters
        """
        results = self.repository.get_all_documents()
        
        # Apply UC course filter
        if "uc_course" in filters and filters["uc_course"]:
            if isinstance(filters["uc_course"], list):
                uc_docs = []
                for uc in filters["uc_course"]:
                    uc_docs.extend(self.repository.find_by_uc_course(uc))
                results = uc_docs
            else:
                results = self.repository.find_by_uc_course(filters["uc_course"])
                
        # Apply CCC course filter
        if "ccc_courses" in filters and filters["ccc_courses"]:
            ccc_docs = self.repository.find_by_ccc_courses(
                filters["ccc_courses"],
                True
            )
            # Intersect with current results
            if "uc_course" in filters and filters["uc_course"]:
                # Find docs that match both UC and CCC filters
                results = [doc for doc in results if doc in ccc_docs]
            else:
                results = ccc_docs
                
        # Apply group filter
        if "group" in filters and filters["group"]:
            group_docs = self.repository.find_by_group(filters["group"])
            # Intersect with current results
            if "uc_course" in filters or "ccc_courses" in filters:
                results = [doc for doc in results if doc in group_docs]
            else:
                results = group_docs
                
        # Apply section filter
        if "section" in filters and filters["section"]:
            section_docs = self.repository.find_by_section(filters["section"])
            # Intersect with current results
            results = [doc for doc in results if doc in section_docs]
            
        # Apply no_articulation filter
        if "no_articulation" in filters:
            no_articulation_value = filters["no_articulation"]
            results = [
                doc for doc in results
                if (isinstance(doc.metadata.get("logic_block", {}), dict) and
                    doc.metadata.get("logic_block", {}).get("no_articulation", False)) == no_articulation_value
            ]
            
        # Apply limit
        if limit is not None and limit > 0:
            results = results[:limit]
            
        return results
        
    def validate_documents_same_section(self, docs: List[Document]) -> List[Document]:
        """
        Filter documents to keep only those in the same section as the first document.
        
        Args:
            docs: List of articulation documents to filter
            
        Returns:
            A filtered list of documents all belonging to the same section
        """
        if not docs:
            return []
            
        section = docs[0].metadata.get("section")
        return [d for d in docs if d.metadata.get("section") == section]
        
    def get_reload_status(self) -> Dict[str, Any]:
        """
        Get information about the document loading status.
        
        Returns:
            Dictionary with document count and last load time
        """
        return self.repository.get_reload_status()
        
    def clear_cache(self) -> None:
        """Clear all cached results in the service and repository."""
        global _course_cache, _json_data
        _course_cache = {}
        _json_data = None
        self.repository.clear_cache() 