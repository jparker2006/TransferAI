#!/usr/bin/env python3

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix prompt_builder import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm"))

# Import the necessary components
from llm.prompt_builder import build_course_prompt, VerbosityLevel

print("=== TransferAI Verbosity Comparison ===\n")

rendered_logic = '* Option A: MATH 1A OR MATH 1AH (Honors)\n* Option B: MATH 1B OR MATH 1BH (Honors)'
user_question = 'Can I take MATH 1A and MATH 1B to satisfy MATH 10A and 10B at UCSD?'

minimal = build_course_prompt(
    rendered_logic=rendered_logic,
    user_question=user_question,
    uc_course='MATH 10A, MATH 10B',
    uc_course_title='Calculus I and Calculus II',
    verbosity=VerbosityLevel.MINIMAL
)

standard = build_course_prompt(
    rendered_logic=rendered_logic,
    user_question=user_question,
    uc_course='MATH 10A, MATH 10B',
    uc_course_title='Calculus I and Calculus II',
    verbosity=VerbosityLevel.STANDARD
)

detailed = build_course_prompt(
    rendered_logic=rendered_logic,
    user_question=user_question,
    uc_course='MATH 10A, MATH 10B',
    uc_course_title='Calculus I and Calculus II',
    verbosity=VerbosityLevel.DETAILED
)

print('--- MINIMAL PROMPT ---')
print(minimal)
print(f'\nLength: {len(minimal)} chars')

print('\n--- STANDARD PROMPT ---')
print(standard)
print(f'\nLength: {len(standard)} chars')

print('\n--- DETAILED PROMPT ---')
print(detailed)
print(f'\nLength: {len(detailed)} chars')

print(f'\nSize reduction (DETAILED → MINIMAL): {100 - (len(minimal) / len(detailed) * 100):.1f}%') 