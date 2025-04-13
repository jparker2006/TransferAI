from main import TransferAIEngine

test_prompts = [
    # CSE 30 logic (AND + OR)
    "Do I need to take CIS 21JA, CIS 21JB, and CIS 26B to get credit for CSE 30?",

    # CSE 8B mapping (direct)
    "What does CIS 36B transfer to at UCSD?",

    # CSE 11 accelerated path (AND requirement)
    "Is CIS 36B enough by itself for CSE 11?",

    # Cross-group logic check
    "Can I satisfy Group 1 with CIS 22A and CIS 36B?",

    # PHYS 2A mapping
    "Does PHYS 4A transfer to anything at UCSD?",

    # CSE 8A (OR logic options)
    "What courses at De Anza satisfy CSE 8A?",

    # CSE 15L (no articulation)
    "Does De Anza have an equivalent for CSE 15L?",

    # CSE 12 (OR with honors)
    "What courses at De Anza satisfy CSE 12?",

    # CSE 20 (math OR with honors)
    "What satisfies CSE 20 at De Anza?",

    # CSE 21 (no articulation)
    "Is there a De Anza equivalent for CSE 21?",

    # MATH 20C (AND + OR + honors)
    "What courses satisfy MATH 20C at UCSD from De Anza?",

    # BILD 1 (complex OR of ANDs)
    "What do I need to take at De Anza to get credit for BILD 1?",

    # Catch-all logic test
    "What De Anza courses do I need for every CSE core class required for transfer?",
]

def run_test_suite():
    engine = TransferAIEngine()
    engine.configure()
    engine.load()

    print("🧪 Running TransferAI test suite...\n")
    for i, prompt in enumerate(test_prompts, 1):
        print(f"===== Test {i}: {prompt} =====")
        engine.handle_query(prompt)
        print("=" * 60 + "\n")

if __name__ == "__main__":
    run_test_suite()
