import re


def normalize_course_code(code: str) -> str:
    """Standardize course codes like 'CSE 8A:' → 'CSE 8A'"""
    return re.sub(r"[^A-Z0-9 ]", "", code.upper()).strip()


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
    """
    Extract all UC and CCC course codes found in the query.
    Returns dict:
        {"uc_course": ["CSE 11"], "ccc_courses": ["CIS 36A", "CIS 36B"]}
    """
    query_upper = query.upper()
    filters = {}

    def find_matches(prefixes):
        if not prefixes:
            return []
        pattern = r"\b(?:%s)\s\d+[A-Z]?\b" % "|".join(prefixes)
        return [normalize_course_code(m) for m in re.findall(pattern, query_upper)]

    uc_matches = find_matches(uc_prefixes)
    ccc_matches = find_matches(ccc_prefixes)

    if uc_matches:
        filters["uc_course"] = list(set(uc_matches))
    if ccc_matches:
        filters["ccc_courses"] = list(set(ccc_matches))

    return filters


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
