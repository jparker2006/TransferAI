import re


def normalize_course_code(code: str) -> str:
    """
    Normalize codes like 'cis-21ja:' → 'CIS 21JA'
    Handles patterns like 'CIS21JA', 'MATH 2BH', 'PHYS-4A', etc.
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

def extract_prefixes_from_docs(docs, key):
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

def extract_filters(query, uc_prefixes, ccc_prefixes):
    query_upper = query.upper()
    filters = {"uc_course": set(), "ccc_courses": set()}
    
    all_matches = re.findall(r"[A-Z]{2,5}\s?\d+[A-Z]{0,2}", query_upper)
    for match in all_matches:
        normalized = normalize_course_code(match)
        prefix = normalized.split(" ")[0]
        if prefix in uc_prefixes:
            filters["uc_course"].add(normalized)
        elif prefix in ccc_prefixes:
            filters["ccc_courses"].add(normalized)

    return {
        "uc_course": sorted(filters["uc_course"]),
        "ccc_courses": sorted(filters["ccc_courses"])
    }

def extract_reverse_matches(query, docs):
    """
    Reverse lookup: find docs where any CCC course appears in the user query.
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


def extract_group_matches(query, docs):
    """
    Detect if a group number is mentioned in the query (e.g., 'Group 3') and return matching docs.
    """
    group_match = re.search(r"\bgroup\s*(\d+)\b", query.lower())
    if not group_match:
        return []

    group_num = group_match.group(1).strip()
    return [doc for doc in docs if str(doc.metadata.get("group", "")).strip() == group_num]


def extract_section_matches(query, docs):
    """
    Detect mentions like 'section A of group 2' and return matching documents.
    """
    match = re.search(r"group\s*(\d+)[\s,;]*section\s*([A-Z])", query.lower())
    if not match:
        return []

    group_num, section_label = match.groups()
    return [
        doc for doc in docs
        if str(doc.metadata.get("group", "")).strip() == group_num and str(doc.metadata.get("section", "")).strip().upper() == section_label.upper()
    ]