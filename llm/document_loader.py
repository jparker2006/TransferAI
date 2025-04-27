"""
Document Loader Module for TransferAI

This module handles the loading and transformation of articulation data from JSON format
into LlamaIndex Document objects suitable for RAG. It's responsible for:

1. Loading JSON data from the articulation source file
2. Transforming nested articulation data into flat, searchable documents
3. Extracting and organizing metadata for retrieval and presentation
4. Creating LlamaIndex Document objects with appropriate text and metadata

The module provides functions to extract course information, flatten complex logic structures,
and prepare documents for vector indexing.
"""

import json
import os
from typing import Dict, List, Set, Union, Optional, Any
from llama_index.core import Document


def extract_ccc_courses_from_logic(logic_block: Dict[str, Any]) -> List[str]:
    """
    Extract all CCC course codes from a logic block recursively.
    
    This function traverses the nested structure of a logic block to find all course codes
    mentioned in any part of the articulation logic, handling both AND and OR blocks.
    
    Args:
        logic_block: A dictionary containing the articulation logic structure with 
                    nested AND/OR blocks and course information.
    
    Returns:
        A sorted list of unique CCC course codes found in the logic block.
        
    Example:
        >>> logic = {"type": "OR", "courses": [{"type": "AND", "courses": [{"course_letters": "CIS 22A"}]}]}
        >>> extract_ccc_courses_from_logic(logic)
        ['CIS 22A']
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


def flatten_courses_from_json(json_data: Dict[str, Any]) -> List[Dict[str, Union[str, Dict]]]:
    """
    Convert nested articulation JSON into flat document objects for LLM ingestion.
    
    This function transforms the hierarchical ASSIST.org data structure into flat documents,
    each representing a single UC course with its articulation options. It extracts metadata
    and creates a text representation suitable for vector indexing.
    
    Args:
        json_data: The parsed JSON data containing articulation information, including
                  groups, sections, and UC courses with their logic blocks.
    
    Returns:
        A list of dictionaries, each containing 'text' and 'metadata' keys, ready to be
        converted to LlamaIndex Document objects.
        
    Note:
        The resulting documents preserve the hierarchical relationship through metadata
        while flattening the structure for easier retrieval.
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
        """Check if any option requires multiple courses (AND logic)."""
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
                ccc_courses = extract_ccc_courses_from_logic(logic_block)

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


def load_documents(path: Optional[str] = None) -> List[Document]:
    """
    Load articulation data from JSON and convert to LlamaIndex Document objects.
    
    This is the main entry point for loading articulation data. It reads the JSON file,
    creates an overview document, and converts all articulation data into searchable
    Document objects with appropriate metadata.
    
    Args:
        path: Optional path to the JSON data file. If None, defaults to "data/rag_data.json"
              relative to the current module.
    
    Returns:
        A list of LlamaIndex Document objects, including an overview document and
        individual documents for each UC course articulation.
        
    Example:
        >>> docs = load_documents()
        >>> len(docs)  # Number of documents created
        95  # (varies based on data size)
    """
    if path is None:
        current_dir = os.path.dirname(__file__)
        path = os.path.join(current_dir, "data/rag_data.json")

    with open(path, "r") as f:
        parsed_json = json.load(f)

    # Overview doc
    overview = {
        "text": f"Overview:\n{parsed_json.get('general_advice', '')}",
        "metadata": {
            "doc_type": "overview",
            "title": f"{parsed_json.get('major', '')} Transfer Overview",
            "source": parsed_json.get("from", "")
        }
    }

    flat_docs = flatten_courses_from_json(parsed_json)
    all_docs = [overview] + flat_docs

    return [Document(text=d["text"], metadata=d["metadata"]) for d in all_docs]