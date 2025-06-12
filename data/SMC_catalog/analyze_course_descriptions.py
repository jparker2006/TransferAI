import os
import json
import re
from collections import defaultdict

def analyze_course_descriptions(directory_path):
    """
    Analyze course descriptions in all JSON files in the specified directory.
    
    This function looks for:
    1. Empty descriptions
    2. Descriptions not starting with capital letters
    3. Unusually short descriptions
    4. Descriptions with unusual starting patterns
    
    Args:
        directory_path (str): Path to the directory containing JSON files
        
    Returns:
        dict: A dictionary containing analysis results
    """
    # Initialize results dictionary
    results = {
        "empty_descriptions": [],
        "lowercase_start": [],
        "short_descriptions": [],
        "unusual_patterns": [],
        "stats": {
            "total_courses": 0,
            "total_files": 0,
            "files_with_issues": 0
        }
    }
    
    # Counter for common description starters
    starter_words = defaultdict(int)
    
    # Process each JSON file in the directory
    for filename in os.listdir(directory_path):
        if not filename.endswith('.json'):
            continue
            
        file_path = os.path.join(directory_path, filename)
        file_has_issues = False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            program_name = data.get("program_name", "Unknown Program")
            courses = data.get("courses", [])
            
            results["stats"]["total_files"] += 1
            results["stats"]["total_courses"] += len(courses)
            
            for course in courses:
                course_code = course.get("course_code", "Unknown Code")
                course_title = course.get("course_title", "Unknown Title")
                description = course.get("description", "")
                
                # Check for empty descriptions
                if not description or description.strip() == "":
                    results["empty_descriptions"].append({
                        "program": program_name,
                        "file": filename,
                        "course_code": course_code,
                        "course_title": course_title
                    })
                    file_has_issues = True
                    continue
                
                # Check for descriptions not starting with capital letter
                if description and not description[0].isupper():
                    results["lowercase_start"].append({
                        "program": program_name,
                        "file": filename,
                        "course_code": course_code,
                        "course_title": course_title,
                        "description": description[:100] + "..." if len(description) > 100 else description
                    })
                    file_has_issues = True
                
                # Check for unusually short descriptions (less than 20 characters)
                if description and len(description) < 20:
                    results["short_descriptions"].append({
                        "program": program_name,
                        "file": filename,
                        "course_code": course_code,
                        "course_title": course_title,
                        "description": description
                    })
                    file_has_issues = True
                
                # Track common starting words/patterns
                if description:
                    first_word = description.split()[0] if description.split() else ""
                    starter_words[first_word] += 1
                    
                    # Check for unusual starting patterns (not common sentence starters)
                    common_starters = ["This", "The", "A", "An", "Students", "In", "These", "Topics", 
                                      "Course", "Emphasis", "Introduction", "Study"]
                    
                    if first_word and first_word not in common_starters and len(first_word) > 1:
                        # Don't flag every uncommon starter, just very unusual ones
                        unusual_pattern = False
                        
                        # Check if starts with lowercase or special characters
                        if not first_word[0].isalpha() or first_word[0].islower():
                            unusual_pattern = True
                            
                        # Check if starts with numbers
                        if first_word[0].isdigit():
                            unusual_pattern = True
                        
                        if unusual_pattern:
                            results["unusual_patterns"].append({
                                "program": program_name,
                                "file": filename,
                                "course_code": course_code,
                                "course_title": course_title,
                                "description": description[:100] + "..." if len(description) > 100 else description,
                                "first_word": first_word
                            })
                            file_has_issues = True
            
            if file_has_issues:
                results["stats"]["files_with_issues"] += 1
                
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
    # Add common starters to results
    results["common_starters"] = dict(sorted(starter_words.items(), key=lambda item: item[1], reverse=True)[:20])
    
    return results

def print_report(results):
    """Print a formatted report of the analysis results."""
    
    print("\n===== COURSE DESCRIPTION ANALYSIS REPORT =====\n")
    
    # Print statistics
    print(f"Total files analyzed: {results['stats']['total_files']}")
    print(f"Total courses analyzed: {results['stats']['total_courses']}")
    print(f"Files with issues: {results['stats']['files_with_issues']}")
    print("\n")
    
    # Print empty descriptions
    print(f"EMPTY DESCRIPTIONS: {len(results['empty_descriptions'])}")
    for item in results['empty_descriptions']:
        print(f"  • {item['program']} - {item['course_code']}: {item['course_title']} (File: {item['file']})")
    print("\n")
    
    # Print lowercase starters
    print(f"DESCRIPTIONS NOT STARTING WITH CAPITAL LETTER: {len(results['lowercase_start'])}")
    for item in results['lowercase_start']:
        print(f"  • {item['program']} - {item['course_code']}: {item['course_title']}")
        print(f"    Description: {item['description']}")
    print("\n")
    
    # Print short descriptions
    print(f"UNUSUALLY SHORT DESCRIPTIONS: {len(results['short_descriptions'])}")
    for item in results['short_descriptions']:
        print(f"  • {item['program']} - {item['course_code']}: {item['course_title']}")
        print(f"    Description: {item['description']}")
    print("\n")
    
    # Print unusual patterns
    print(f"UNUSUAL STARTING PATTERNS: {len(results['unusual_patterns'])}")
    for item in results['unusual_patterns']:
        print(f"  • {item['program']} - {item['course_code']}: {item['course_title']}")
        print(f"    First word: '{item['first_word']}'")
        print(f"    Description: {item['description']}")
    print("\n")
    
    # Print common starters
    print("MOST COMMON DESCRIPTION STARTERS:")
    for word, count in results['common_starters'].items():
        print(f"  • '{word}': {count} occurrences")

if __name__ == "__main__":
    # Directory containing the JSON files
    directory_path = "/Users/ryancheng/p/TransferAI/data/SMC_catalog/parsed_programs"
    
    # Analyze course descriptions
    results = analyze_course_descriptions(directory_path)
    
    # Print the report
    print_report(results) 