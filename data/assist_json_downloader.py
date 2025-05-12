from __future__ import annotations
from pathlib import Path
import json
import requests
import re # Added for slugify

def slugify(name: str) -> str:
    """Convert a string to a URL-friendly slug."""
    name = name.lower().replace('&', 'and')
    name = name.replace('.', '')  # Remove periods like in "B.S."
    name = re.sub(r'[^a-z0-9]+', '_', name)
    return re.sub(r'_+', '_', name).strip('_')

def download_agreement_json(
    year_id: str,
    sending_id: str,
    receiving_id: str,
    major_key: str,
    out_dir: Path,
) -> Path:
    """
    Download a single ASSIST agreement JSON using the direct URL pattern.

    Args:
        year_id: Academic year ID (e.g., "75" for 2024-2025)
        sending_id: Sending institution ID (e.g., "113" for De Anza)
        receiving_id: Receiving institution ID (e.g., "7" for UCSD)
        major_key: Major key/ID (e.g., "0a3e674e-b9e8-4340-6726-08dca807bc66" for CS)
        out_dir: Directory to save the JSON file

    Returns:
        Path to the saved JSON file
    """
    # Create the URL using the pattern we discovered
    url = f"https://assist.org/api/articulation/Agreements?Key={year_id}/{sending_id}/to/{receiving_id}/Major/{major_key}"
    
    print(f"Downloading from: {url}")
    
    # Make the request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Parse the JSON data
    data = response.json()
    
    # Create the output directory if it doesn't exist
    # out_dir.mkdir(parents=True, exist_ok=True) # Will be handled by specific path creation
    
    # Extract information for the filename
    sending_name_raw = data["result"]["sendingInstitution"]
    receiving_name_raw = data["result"]["receivingInstitution"]
    major_name_raw = data["result"]["name"]
    
    # Clean up the names for the filename
    sending_name_full = sending_name_raw.split('"name":"')[1].split('"')[0] if '"name":"' in sending_name_raw else "Unknown_Sending_Institution"
    receiving_name_full = receiving_name_raw.split('"name":"')[1].split('"')[0] if '"name":"' in receiving_name_raw else "Unknown_Receiving_Institution"
    # major_name_clean = major_name_raw.replace(" ", "_").replace(",", "").replace(".", "") # Old way

    # Slugify names for path components
    sending_slug = slugify(sending_name_full)
    receiving_slug = slugify(receiving_name_full)
    major_slug = slugify(major_name_raw)

    # Create the nested output path
    # The 'out_dir' parameter now serves as the base (e.g., "json")
    specific_out_dir = out_dir / sending_slug / receiving_slug
    specific_out_dir.mkdir(parents=True, exist_ok=True)
    
    # Create the output filename
    # filename = out_dir / f"{sending_name_clean}_to_{receiving_name_clean}_{major_name_clean}.json" # Old way
    filename = specific_out_dir / f"{major_slug}.json"
    
    # Save the JSON data
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved JSON to {filename}")
    return filename 