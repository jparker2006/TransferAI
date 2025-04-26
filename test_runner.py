from llm.main import TransferAIEngine

# 🔍 High-coverage prompt-based articulation test suite (De Anza → UCSD)
# Includes edge cases, multi-course logic, honors variants, and validation-style prompts

OG_test_prompts = [
    "Which De Anza courses satisfy CSE 8A at UCSD?",
    "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?",
    "What De Anza courses are required to satisfy Group 2 for Computer Science at UCSD?",
    "How many science courses do I need to transfer for UCSD Computer Science under Group 3?",
    "Does De Anza have an equivalent for CSE 21 at UCSD?",
    "What De Anza courses count for CSE 30 at UC San Diego?",
    "What De Anza classes satisfy BILD 1 for UCSD transfer?",
]


test_prompts = [
    "Which De Anza courses satisfy CSE 8A at UCSD?",
    "Which courses satisfy CSE 8B?",
    "Which courses satisfy CSE 11?",
    "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?",
    "Can I take CIS 22A and CIS 36B to satisfy anything in Group 1?",
    "Can I mix CIS 22A and CIS 35A for Group 1 at UCSD?",  # invalid cross-section
    "If I complete CSE 8A and 8B, is that one full path?",
    "What are all valid De Anza combinations to satisfy Group 1 at UCSD?",
    "What De Anza courses are required to satisfy Group 2 for Computer Science at UCSD?",
    "Which courses count for CSE 12 at UCSD?",
    "What satisfies MATH 18 for UCSD transfer?",
    "Does MATH 2BH satisfy MATH 18?",
    "Can I take MATH 2B instead of MATH 2BH for MATH 18?",
    "Is CSE 21 articulated from De Anza?",  # no articulation
    "Can I complete just CIS 21JA and 21JB to satisfy CSE 30?",
    "Does CSE 15L have any articulation?",
    "How can I satisfy CSE 30 using De Anza classes?",
    "Does MATH 1CH and 1DH count for MATH 20C?",
    "What De Anza classes satisfy MATH 20C at UCSD?",
    "Is there a difference between MATH 1A and MATH 1AH for transfer credit?",
    "Which courses satisfy MATH 20A and 20B?",
    "List all options for CSE 30 at UCSD from De Anza.",
    "What are my options for fulfilling Group 3 science requirements for CS at UCSD?",
    "What courses count for BILD 1?",
    "Can I take BIOL 6A and 6B only to satisfy BILD 1?",
    "How many science courses do I need to transfer for UCSD Computer Science under Group 3?",
    "Can I satisfy Group 3 with CHEM 1A and PHYS 4A?",
    "Does PHYS 4A articulate to UCSD?",
    "Does BILD 2 require the same BIOL series as BILD 1?",
    "What De Anza courses are required for CHEM 6A and 6B?",
    "If I took CIS 36A, can it satisfy more than one UCSD course?",
    "Are any honors courses required for the CS transfer path from De Anza to UCSD?",
    # New test cases for v1.4 features
    "Does CSE 12 require honors courses at De Anza?",
    "Can I take both MATH 1A and MATH 1AH for MATH 20A?",
    "Which UC courses can I satisfy with CIS 36A?",
    "Does CIS 22C satisfy CSE 12?",
]



regression_tests = [
    "Which De Anza courses satisfy CSE 8A at UCSD?",              # CIS 36A alone is valid
    "Which courses satisfy CSE 11?",                              # Needs CIS 36A + CIS 36B (make sure prompt still builds!)
    "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?",  # LLM required
    "If I complete CSE 8A and 8B, is that one full path?",        # Should NOT trigger R31 logic
    "Can I take CIS 22A and CIS 36B to satisfy anything in Group 1?",  # Group logic, unrelated
    "If I took CIS 36A, can it satisfy more than one UCSD course?",  # ✅ We just fixed this!
    # New v1.4 regression tests
    "Does CSE 12 require honors courses at De Anza?", # Should say no, honors not required for CSE 12
    "Can I take both MATH 1A and MATH 1AH for MATH 20A?", # Should detect redundant courses
]




def run_test_suite():
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    offset = 7
    print("🧪 Running TransferAI test suite...\n")
    for i, prompt in enumerate(test_prompts, 1 + offset):
        print(f"===== Test {i}: {prompt} =====")
        response = engine.handle_query(prompt)
        if response:
            print(response.strip())
        print("=" * 60 + "\n")


if __name__ == "__main__":
    run_test_suite()
