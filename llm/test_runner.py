from main import TransferAIEngine

# Core prompt-based tests for reasoning and validation
test_prompts = [
    "Which De Anza courses satisfy CSE 8A at UCSD?",
    "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?",
    "What De Anza courses are required to satisfy Group 2 for Computer Science at UCSD?",
    "How many science courses do I need to transfer for UCSD Computer Science under Group 3?",
    "Does De Anza have an equivalent for CSE 21 at UCSD?",
    "What De Anza courses count for CSE 30 at UC San Diego?",
    "What De Anza classes satisfy BILD 1 for UCSD transfer?",
]

# Group-based debug validator (verifies metadata and phrasing)
group_validation_queries = [
    ("Group 1", "What counts toward Group 1 requirements?"),
    ("Group 2", "Which De Anza courses satisfy Group 2 at UCSD?"),
    ("Group 3", "What science courses can I use to fulfill Group 3 for UCSD Computer Science?"),
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


def run_group_logic_debug():
    engine = TransferAIEngine()
    engine.configure()
    engine.load()

    print("🔍 Running group logic metadata checks...\n")
    for group_name, prompt in group_validation_queries:
        print(f"📁 Validating {group_name} — {prompt}")
        engine.handle_query(prompt)
        print("=" * 60 + "\n")


if __name__ == "__main__":
    run_test_suite()
    # run_group_logic_debug()
