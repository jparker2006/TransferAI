#!/usr/bin/env python3
"""
Analyze department count differences.
"""

import json
import os

def analyze_departments():
    # Load JSON data
    with open('smc_department_headers.json', 'r') as f:
        json_data = json.load(f)
    
    print(f"Total departments in JSON: {len(json_data)}")
    print()
    
    # Count by course letters
    course_letters_count = {}
    empty_course_letters = []
    departments_by_cl = {}
    
    for dept in json_data:
        cl = dept.get('course_letters', '')
        major = dept.get('major', '')
        
        if cl:
            if cl in course_letters_count:
                course_letters_count[cl] += 1
                departments_by_cl[cl].append(major)
            else:
                course_letters_count[cl] = 1
                departments_by_cl[cl] = [major]
        else:
            empty_course_letters.append(major)
    
    print(f"Departments with empty course_letters: {len(empty_course_letters)}")
    for dept in empty_course_letters:
        print(f"  - {dept}")
    print()
    
    print(f"Unique course letters: {len(course_letters_count)}")
    print()
    
    print("Course letters shared by multiple departments:")
    shared_count = 0
    for cl, count in sorted(course_letters_count.items(), key=lambda x: x[1], reverse=True):
        if count > 1:
            shared_count += count
            print(f"  {cl}: {count} departments")
            for dept in departments_by_cl[cl]:
                print(f"    - {dept}")
            print()
    
    print(f"Total departments sharing course letters: {shared_count}")
    print(f"Expected output files if properly grouped: {len(course_letters_count) + len(empty_course_letters) - len([cl for cl, count in course_letters_count.items() if count > 1]) + len([cl for cl, count in course_letters_count.items() if count > 1])}")
    
    # Count actual output files
    if os.path.exists('course_data'):
        actual_files = len([f for f in os.listdir('course_data') if f.endswith('_courses.json')])
        print(f"Actual output files: {actual_files}")

if __name__ == "__main__":
    analyze_departments() 