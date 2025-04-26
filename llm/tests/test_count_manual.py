from unittest.mock import MagicMock, patch
from logic_formatter import count_uc_matches

# Create mock Document objects for testing
mock_docs = []

# Create a doc for CSE 8A where CIS 36A is a direct match
doc1 = MagicMock()
doc1.metadata = {
    "uc_course": "CSE 8A",
    "logic_block": {
        "type": "OR",
        "courses": [
            {
                "type": "AND",
                "courses": [
                    {"course_letters": "CIS 36A", "honors": False}
                ]
            }
        ]
    }
}

# Create a doc for CSE 11 where CIS 36A contributes
doc2 = MagicMock()
doc2.metadata = {
    "uc_course": "CSE 11",
    "logic_block": {
        "type": "OR",
        "courses": [
            {
                "type": "AND",
                "courses": [
                    {"course_letters": "CIS 36A", "honors": False},
                    {"course_letters": "CIS 36B", "honors": False}
                ]
            }
        ]
    }
}

mock_docs = [doc1, doc2]

# Patch the helper functions to return expected results
with patch('logic_formatter.get_uc_courses_satisfied_by_ccc', return_value=["CSE 8A"]):
    with patch('logic_formatter.get_uc_courses_requiring_ccc_combo', return_value=["CSE 11"]):
        count, direct, combo = count_uc_matches("CIS 36A", mock_docs)
        print(f"Direct matches ({count}): {direct}")
        print(f"Contributes to: {combo}")

# Expected output:
# Direct matches (1): ['CSE 8A']
# Contributes to: ['CSE 11'] 