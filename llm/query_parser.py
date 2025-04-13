import re


def extract_prefixes_from_docs(docs, key):
    prefixes = set()
    for doc in docs:
        values = doc.metadata.get(key, [])
        if isinstance(values, str):
            values = [values]
        for val in values:
            match = re.match(r"([A-Z]{2,6})\s\d+", val.upper())
            if match:
                prefixes.add(match.group(1))
    return sorted(prefixes)


def extract_filters(query, uc_prefixes, ccc_prefixes):
    """
    Extracts all UC and CCC course codes found in the query.
    Returns dict like:
        {"uc_course": ["CSE 11"], "ccc_courses": ["CIS 36A", "CIS 36B"]}
    """
    query_upper = query.upper()
    filters = {}

    def find_matches(prefixes):
        pattern = r"\b(?:%s)\s\d+[A-Z]?\b" % "|".join(prefixes)
        return re.findall(pattern, query_upper)

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
        if any(cc in query_upper for cc in ccc_list):
            matches.append(doc)
    return matches


def extract_group_matches(query, docs):
    """
    Detect if a group number is mentioned in the query (e.g., 'Group 3') and return matching docs.
    """
    group_match = re.search(r"\bgroup\s*(\d+)\b", query.lower())
    if not group_match:
        return []

    group_num = group_match.group(1)
    return [doc for doc in docs if doc.metadata.get("group") == group_num]
