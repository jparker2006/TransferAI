"""
Query Parser Module for TransferAI

This module is responsible for analyzing and extracting structured information from natural
language queries about course articulation. It provides functions to:

1. Normalize course codes for consistent matching
2. Extract UC and CCC course codes from user queries
3. Identify group and section references
4. Match queries to specific articulation documents

The module uses spaCy for NLP processing and regex patterns to identify course codes, 
groups, and sections in user questions. It handles various formats and edge cases in 
course code notation.
"""

import re
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import spacy

nlp = spacy.load("en_core_web_sm")

def normalize_course_code(code: str) -> str:
    """
    Normalize course codes to a standard format (e.g., 'cis-21ja:' → 'CIS 21JA').
    
    This function standardizes various course code formats to ensure consistent matching
    regardless of input format variations. It handles patterns like 'CIS21JA', 'MATH 2BH',
    'PHYS-4A', etc.
    
    Args:
        code: The course code string to normalize.
        
    Returns:
        A normalized course code in the format "DEPT NUM" (e.g., "CIS 22A").
        
    Examples:
        >>> normalize_course_code("cis-21ja:")
        'CIS 21JA'
        >>> normalize_course_code("MATH2BH")
        'MATH 2BH'
    """
    code = code.upper()
    code = re.sub(r"[^A-Z0-9]", "", code)  # Remove all non-alphanumerics

    # Match subject + number + up to 2 trailing letters (e.g. '21JA', '2BH')
    match = re.match(r"([A-Z]{2,5})(\d+[A-Z]{0,2})", code)
    if match:
        subject = match.group(1)
        number = match.group(2)
        return f"{subject} {number}"

    return code  # Fallback

def extract_prefixes_from_docs(docs: List[Any], key: str) -> List[str]:
    """
    Extract course code prefixes (department codes) from document metadata.
    
    Analyzes document metadata to extract unique department prefixes (e.g., "CSE", "MATH")
    from course codes to help with course code identification in queries.
    
    Args:
        docs: List of documents containing metadata.
        key: The metadata key that contains course codes ("uc_course" or "ccc_courses").
        
    Returns:
        A sorted list of unique department prefixes found in the documents.
        
    Example:
        >>> extract_prefixes_from_docs(docs, "uc_course")
        ['BILD', 'CSE', 'MATH', 'PHYS']
    """
    prefixes = set()
    for doc in docs:
        values = doc.metadata.get(key, [])
        if isinstance(values, str):
            values = [values]
        for val in values:
            normalized = normalize_course_code(val)
            match = re.match(r"([A-Z]{2,6})\s\d+", normalized)
            if match:
                prefixes.add(match.group(1))
    return sorted(prefixes)


def extract_filters(query: str, uc_course_catalog: Set[str], ccc_course_catalog: Set[str]) -> Dict[str, List[str]]:
    """
    Extract UC and CCC course codes from a natural language query.
    
    Uses NLP and pattern matching to identify course codes in user queries, distinguishing
    between UC and CCC courses based on the provided course catalogs.
    
    Args:
        query: The user's natural language query.
        uc_course_catalog: Set of known UC course codes (e.g., "CSE 8A").
        ccc_course_catalog: Set of known CCC course codes (e.g., "CIS 22A").
        
    Returns:
        A dictionary with keys "uc_course" and "ccc_courses", each containing a sorted
        list of course codes extracted from the query.
        
    Example:
        >>> extract_filters("Does CIS 22A satisfy CSE 8A?", {"CSE 8A"}, {"CIS 22A"})
        {'uc_course': ['CSE 8A'], 'ccc_courses': ['CIS 22A']}
        
    Note:
        This function handles sequences like "CSE 8A and 8B" by tracking the last department
        prefix seen to correctly identify "8B" as "CSE 8B".
    """
    filters = {"uc_course": set(), "ccc_courses": set()}
    doc = nlp(query.upper())
    last_prefix = None

    # print("🔍 [spaCy] Tokenized words:", [token.text for token in doc])

    for i, token in enumerate(doc):
        text = token.text.strip(",.?!")
        next_token = doc[i + 1].text.strip(",.?!") if i + 1 < len(doc) else None

        # print(f"🔎 [Token {i}] '{text}' (next: '{next_token}')")

        # Skip coordination words — preserve last prefix
        if text in {"AND", "OR", "WITH", "TO", "FOR"}:
            # print(f"⏭️ Skipping connector: {text}")
            continue

        course = None

        # Full course (e.g., CSE 8A)
        if re.fullmatch(r"[A-Z]{2,5}", text) and next_token and re.fullmatch(r"\d+[A-Z]{0,2}", next_token):
            course = f"{text} {next_token}"
            last_prefix = text
            # print(f"🧩 Full course match → {course}")

        # Suffix only (e.g., '8B' after 'CSE')
        elif re.fullmatch(r"\d+[A-Z]{0,2}", text) and last_prefix:
            course = f"{last_prefix} {text}"
            # print(f"🧩 Suffix course match → {course}")

        else:
            # print(f"⛔ Skipping token: {text}")
            continue

        in_uc = course in uc_course_catalog
        in_ccc = course in ccc_course_catalog
        # print(f"📘 {course} → in_uc: {in_uc}, in_ccc: {in_ccc}")

        if in_uc and not in_ccc:
            filters["uc_course"].add(course)
        elif in_ccc and not in_uc:
            filters["ccc_courses"].add(course)
        elif in_uc and in_ccc:
            filters["ccc_courses"].add(course)

    # print("🎯 [DEBUG] Extracted filters:", filters)
    return {
        "uc_course": sorted(filters["uc_course"]),
        "ccc_courses": sorted(filters["ccc_courses"])
    }

def extract_reverse_matches(query: str, docs: List[Any]) -> List[Any]:
    """
    Find documents where any CCC course in the metadata appears in the user query.
    
    Performs a reverse lookup to find articulation documents where the CCC course
    codes mentioned in the document match courses mentioned in the query.
    
    Args:
        query: The user's query text.
        docs: List of articulation documents to search through.
        
    Returns:
        A list of matching documents where at least one CCC course appears in the query.
        
    Example:
        >>> extract_reverse_matches("Can I take CIS 22A?", docs)
        [Document(metadata={'uc_course': 'CSE 8A', 'ccc_courses': ['CIS 22A', ...]}), ...]
    """
    query_upper = query.upper()
    matches = []
    for doc in docs:
        ccc_list = doc.metadata.get("ccc_courses") or []
        for cc in ccc_list:
            if normalize_course_code(cc) in query_upper:
                matches.append(doc)
                break
    return matches


def extract_group_matches(query: str, docs: List[Any]) -> List[Any]:
    """
    Find documents matching a group mentioned in the query (e.g., 'Group 3').
    
    Uses regex to detect group number references in queries and returns all documents
    belonging to that group.
    
    Args:
        query: The user's query text.
        docs: List of articulation documents to search through.
        
    Returns:
        A list of documents belonging to the group mentioned in the query.
        
    Example:
        >>> extract_group_matches("What courses satisfy Group 2?", docs)
        [Document(metadata={'group': '2', ...}), ...]
    """
    group_match = re.search(r"\bgroup\s*(\d+)\b", query.lower())
    if not group_match:
        return []

    group_num = group_match.group(1).strip()
    return [doc for doc in docs if str(doc.metadata.get("group", "")).strip() == group_num]


def extract_section_matches(query: str, docs: List[Any]) -> List[Any]:
    """
    Find documents matching a specific section within a group.
    
    Detects mentions like 'section A of group 2' and returns matching documents.
    
    Args:
        query: The user's query text.
        docs: List of articulation documents to search through.
        
    Returns:
        A list of documents belonging to the specific section of the group.
        
    Example:
        >>> extract_section_matches("What's in Group 2 Section A?", docs)
        [Document(metadata={'group': '2', 'section': 'A', ...}), ...]
    """
    match = re.search(r"group\s*(\d+)[\s,;]*section\s*([A-Z])", query.lower())
    if not match:
        return []

    group_num, section_label = match.groups()
    return [
        doc for doc in docs
        if str(doc.metadata.get("group", "")).strip() == group_num and str(doc.metadata.get("section", "")).strip().upper() == section_label.upper()
    ]


def split_multi_uc_query(query: str, uc_courses: List[str]) -> List[str]:
    """
    Split a multi-course query into individual queries for each UC course.
    
    Used for handling queries about multiple UC courses by creating focused sub-queries.
    
    Args:
        query: The original user query.
        uc_courses: List of UC courses detected in the query.
        
    Returns:
        List of modified queries, each focusing on a specific UC course.
        
    Example:
        >>> split_multi_uc_query("What satisfies CSE 8A and CSE 8B?", ["CSE 8A", "CSE 8B"])
        ["What satisfies CSE 8A and CSE 8B? (focus on CSE 8A)", "What satisfies CSE 8A and CSE 8B? (focus on CSE 8B)"]
    """
    return [f"{query.strip()} (focus on {uc})" for uc in uc_courses]

def enrich_uc_courses_with_prefixes(matches: List[str], uc_prefixes: List[str]) -> List[str]:
    """
    Enrich course code matches with department prefixes where needed.
    
    Handles cases where only the course number is mentioned by applying the appropriate
    department prefix based on context. For example, "CSE 8A and 8B" becomes
    ["CSE 8A", "CSE 8B"].
    
    Args:
        matches: List of raw course code matches from the query.
        uc_prefixes: List of known UC department prefixes.
        
    Returns:
        List of enriched course codes with proper department prefixes.
        
    Example:
        >>> enrich_uc_courses_with_prefixes(["CSE 8A", "8B"], ["CSE", "MATH"])
        ["CSE 8A", "CSE 8B"]
    """
    enriched = []
    last_prefix = None

    for raw in matches:
        normalized = normalize_course_code(raw)
        parts = normalized.split()

        # Skip junk like 'AND', 'OR', etc.
        if len(parts) == 1 and not re.match(r"\d+[A-Z]{0,2}$", parts[0]):
            continue

        if len(parts) == 2:
            prefix, number = parts
            if prefix in uc_prefixes:
                last_prefix = prefix
                enriched.append(normalized)
            else:
                # '15L' with no known prefix → try last seen prefix
                if last_prefix and re.match(r"\d+[A-Z]{0,2}$", number):
                    enriched.append(f"{last_prefix} {prefix}")
        elif len(parts) == 1:
            # Pure number like '15L' → use last seen subject prefix
            if last_prefix:
                enriched.append(f"{last_prefix} {parts[0]}")
        else:
            # Unexpected format — skip
            continue

    return enriched


def find_uc_courses_satisfied_by(ccc_code: str, docs: List[Any]) -> List[Any]:
    """
    Find UC courses that can be satisfied by a specific CCC course.
    
    Searches through documents to find UC courses where the given CCC course
    appears in the articulation logic.
    
    Args:
        ccc_code: The CCC course code to search for.
        docs: List of articulation documents to search through.
        
    Returns:
        List of documents for UC courses satisfied by the given CCC course.
        
    Example:
        >>> find_uc_courses_satisfied_by("CIS 22A", docs)
        [Document(metadata={'uc_course': 'CSE 8A', ...}), ...]
    """
    matched_docs = []
    for doc in docs:
        logic_block = doc.metadata.get("logic_block", {})
        if not logic_block or logic_block.get("no_articulation"):
            continue

        if logic_block_contains_ccc_course(logic_block, ccc_code):
            matched_docs.append(doc)

    return matched_docs

def logic_block_contains_ccc_course(logic_block: Dict[str, Any], target_ccc: str) -> bool:
    """
    Check if a specific CCC course appears in the articulation logic block.
    
    Searches through the logic block for the target CCC course code, handling
    both single courses and course groups.
    
    Args:
        logic_block: The articulation logic block to search.
        target_ccc: The CCC course code to look for.
        
    Returns:
        True if the course appears in the logic block, False otherwise.
        
    Note:
        This is a helper function for find_uc_courses_satisfied_by.
    """
    norm = lambda s: normalize_course_code(s)

    for option in logic_block.get("options", []):
        for course in option.get("courses", []):
            if isinstance(course, list):  # AND group
                if any(norm(c) == norm(target_ccc) for c in course):
                    return True
            elif isinstance(course, str):  # single course
                if norm(course) == norm(target_ccc):
                    return True
    return False
