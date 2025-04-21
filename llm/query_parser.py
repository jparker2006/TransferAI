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

def extract_filters(query, uc_course_catalog, ccc_course_catalog):
    query_upper = query.upper()
    filters = {"uc_course": set(), "ccc_courses": set()}

    # Step 1: Extract full course-like tokens (e.g., "CSE 8A", "CIS 36A", "PHYS-2A")
    raw_matches = re.findall(r"[A-Z]{2,5}[- ]?\d+[A-Z]{0,2}", query_upper)
    normalized_matches = []
    last_uc_prefix = None

    for match in raw_matches:
        norm = normalize_course_code(match)
        if not re.match(r"^[A-Z]{2,5} \d+[A-Z]{0,2}$", norm):
            continue

        in_uc = norm in uc_course_catalog
        in_ccc = norm in ccc_course_catalog

        if in_uc and not in_ccc:
            filters["uc_course"].add(norm)
            last_uc_prefix = norm.split(" ")[0]
        elif in_ccc and not in_uc:
            filters["ccc_courses"].add(norm)
        elif in_uc and in_ccc:
            # Ambiguous — default to CCC for group/articulation queries
            filters["ccc_courses"].add(norm)

        normalized_matches.append(norm)

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



# NEW IN 1.2
def split_multi_uc_query(query, uc_courses):
    return [f"{query.strip()} (focus on {uc})" for uc in uc_courses]

def enrich_uc_courses_with_prefixes(matches, uc_prefixes):
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


def find_uc_courses_satisfied_by(ccc_code: str, docs: list):
    matched_docs = []
    for doc in docs:
        logic_block = doc.metadata.get("logic_block", {})
        if not logic_block or logic_block.get("no_articulation"):
            continue

        if logic_block_contains_ccc_course(logic_block, ccc_code):
            matched_docs.append(doc)

    return matched_docs

def logic_block_contains_ccc_course(logic_block: dict, target_ccc: str) -> bool:
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
