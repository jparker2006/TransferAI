import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# List of default majors to process if --scrape-all is not specified
DEFAULT_TARGET_MAJORS: List[str] = [
    "CSE: Computer Science B.S.",
    "Biology: General Biology B.S.",
    "Physics B.S.",
    "Mathematics B.S.",
    "Structural Engineering B.S.",
    "Economics B.S.",
    "History B.A.",
    "Art: Studio B.A. (Visual Arts)",
    "Chemistry and Biochemistry: Chemistry B.S."
]

def slugify(label: str) -> str:
    """
    Convert a label string into a filesystem-friendly slug.
    - Convert to lowercase.
    - Replace '&' with 'and'.
    - Remove periods.
    - Replace non-alphanumeric (excluding underscores) with underscore.
    - Consolidate multiple underscores.
    - Strip leading/trailing underscores.
    """
    if not label:
        return ""
    label = label.lower()
    label = label.replace('&', 'and')
    label = label.replace('.', '')
    # Replace non-alphanumeric (keeps underscore)
    label = re.sub(r'[^\w_]+', '_', label)
    label = re.sub(r'_+', '_', label)      # Consolidate multiple underscores
    label = label.strip('_')
    return label

def generate_batch_config(
    majors_json_path: Path,
    year_id: str,
    sending_institution_id: str,
    receiving_institution_id: str,
    sending_institution_slug: str,
    receiving_institution_slug: str,
    scrape_all_majors: bool, # Changed from target_majors
    output_config_path: Path
) -> None:
    """
    Generates the batch_config.json file.
    """
    try:
        with open(majors_json_path, 'r', encoding='utf-8') as f:
            majors_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Majors JSON file not found at {majors_json_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in majors file at {majors_json_path}", file=sys.stderr)
        sys.exit(1)

    if 'reports' not in majors_data or not isinstance(majors_data['reports'], list):
        print("Error: Majors JSON file must contain a 'reports' list.", file=sys.stderr)
        sys.exit(1)

    all_majors_in_file: List[Dict[str, Any]] = majors_data['reports']
    majors_to_process: List[Dict[str, Any]] = []

    if scrape_all_majors:
        majors_to_process = all_majors_in_file
    else:
        # Filter based on the hardcoded DEFAULT_TARGET_MAJORS list
        default_target_majors_set = set(DEFAULT_TARGET_MAJORS)
        for major in all_majors_in_file:
            if major.get('label') in default_target_majors_set:
                majors_to_process.append(major)
        
        # Optional: Warn if some default majors were not found in the JSON file
        found_labels_in_json = {m.get('label') for m in majors_to_process}
        for default_major_label in default_target_majors_set:
            if default_major_label not in found_labels_in_json:
                print(f"Warning: Default target major '{default_major_label}' not found in {majors_json_path}.", file=sys.stderr)

    operations: List[Dict[str, Any]] = []
    processed_count = 0

    for major in majors_to_process: # Use majors_to_process instead of processed_majors
        major_label = major.get('label')
        full_major_key_from_file = major.get('key')

        if not major_label or not full_major_key_from_file:
            print(f"Warning: Skipping major with missing label or key: {major}", file=sys.stderr)
            continue

        # Extract only the hash part (UUID) from the full major key
        # Assumes the key is like "prefix/prefix/Major/HASH_PART"
        try:
            major_key_hash = full_major_key_from_file.split('/')[-1]
            if not major_key_hash: # handle cases like trailing slash if any
                raise ValueError("Extracted major key hash is empty")
        except (IndexError, ValueError) as e:
            print(f"Warning: Could not extract hash from major_key '{full_major_key_from_file}' for label '{major_label}'. Error: {e}. Skipping.", file=sys.stderr)
            continue

        major_slug = slugify(major_label)
        if not major_slug:
            print(f"Warning: Could not generate a valid slug for major label '{major_label}'. Skipping.", file=sys.stderr)
            continue

        # Construct paths
        input_json_filename = f"{major_slug}.json"
        download_output_base_dir = "json"  # As per spec

        convert_input_file_path = f"{download_output_base_dir}/{sending_institution_slug}/{receiving_institution_slug}/{input_json_filename}"
        convert_output_file_path = f"rag_output/{sending_institution_slug}/{receiving_institution_slug}/{input_json_filename}"

        # Create download operation
        download_op = {
            "type": "download",
            "year_id": year_id,
            "sending_id": sending_institution_id,
            "receiving_id": receiving_institution_id,
            "major_key": major_key_hash, # Use the extracted hash
            "output_dir": download_output_base_dir
        }
        operations.append(download_op)

        # Create convert operation
        convert_op = {
            "type": "convert",
            "input_file": convert_input_file_path,
            "output_file": convert_output_file_path,
            "major_key": major_key_hash # Use the extracted hash
        }
        operations.append(convert_op)
        processed_count += 1

    output_data = {"operations": operations}

    try:
        output_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_config_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"Successfully generated batch configuration for {processed_count} major(s).")
        print(f"Output written to: {output_config_path.resolve()}")
    except IOError as e:
        print(f"Error writing output config file to {output_config_path}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Generates a batch_config.json file for processing ASSIST articulation agreements."
    )
    parser.add_argument(
        "--majors-json-path",
        required=True,
        type=Path,
        help="Path to the input JSON file containing the list of majors."
    )
    parser.add_argument(
        "--year-id",
        required=True,
        help="Academic year ID for ASSIST (e.g., 75)."
    )
    parser.add_argument(
        "--sending-institution-id",
        required=True,
        help="ID of the sending institution (e.g., 137 for Santa Monica College)."
    )
    parser.add_argument(
        "--receiving-institution-id",
        required=True,
        help="ID of the receiving institution (e.g., 7 for UC San Diego)."
    )
    parser.add_argument(
        "--sending-institution-slug",
        required=True,
        help="Filesystem-friendly slug for the sending institution (e.g., santa_monica_college)."
    )
    parser.add_argument(
        "--receiving-institution-slug",
        required=True,
        help="Filesystem-friendly slug for the receiving institution (e.g., university_of_california_san_diego)."
    )
    parser.add_argument(
        "--scrape-all",
        action="store_true", # Makes this a boolean flag
        help="If specified, process all majors from the majors JSON file. Otherwise, process a predefined list."
    )
    parser.add_argument(
        "--output-config-path",
        type=Path,
        default=Path("batch_config.json"),
        help="Path where the generated JSON configuration will be saved (default: batch_config.json, relative to script location in data/ folder)."
    )

    args = parser.parse_args()

    # No longer need to parse target_majors_list from args
    # scrape_all_majors flag is directly available in args.scrape_all

    generate_batch_config(
        args.majors_json_path,
        args.year_id,
        args.sending_institution_id,
        args.receiving_institution_id,
        args.sending_institution_slug,
        args.receiving_institution_slug,
        args.scrape_all, # Pass the boolean flag directly
        args.output_config_path
    )

if __name__ == "__main__":
    main() 