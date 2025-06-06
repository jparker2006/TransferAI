#!/usr/bin/env python3
"""
TransferAI ASSIST Scraper v2 - Command-line interface for downloading and processing ASSIST data.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import time

# Import our modules
from assist_json_downloader import download_agreement_json
from assist_to_rag import process_assist_json_file, save_rag_json


def download_command(args: argparse.Namespace) -> None:
    """
    Download articulation agreement(s) from ASSIST API.
    
    Args:
        args: Command-line arguments containing year, sending, receiving, major and output
    """
    # Create output directory if it doesn't exist
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download the agreement
    try:
        json_file = download_agreement_json(
            args.year,
            args.sending,
            args.receiving,
            args.major,
            output_dir
        )
        print(f"✅ Successfully downloaded agreement to {json_file}")
    except Exception as e:
        print(f"❌ Error downloading agreement: {e}")
        sys.exit(1)


def convert_command(args: argparse.Namespace) -> None:
    """
    Convert ASSIST JSON file(s) to RAG format.
    
    Args:
        args: Command-line arguments containing input and output
    """
    input_path = Path(args.input)
    output_path = Path(args.output)
    major_key = args.major_key
    manual_source_url = args.source_url
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Process the file
        rag_data = process_assist_json_file(
            input_path, manual_source_url=manual_source_url, major_key=major_key
        )
        
        # Save the results
        save_rag_json(rag_data, output_path)
        print(f"✅ Successfully converted {input_path} to {output_path}")
    except Exception as e:
        print(f"❌ Error converting file: {e}")
        sys.exit(1)


def batch_command(args: argparse.Namespace) -> None:
    """
    Process a batch of download and convert operations defined in a config file.
    
    Args:
        args: Command-line arguments containing config file path
    """
    config_path = Path(args.config)
    
    try:
        # Load the config file
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Process each operation
        total_ops = len(config.get("operations", []))
        print(f"🔄 Processing {total_ops} operations from config file")
        
        for i, op in enumerate(config.get("operations", []), 1):
            op_type = op.get("type")
            
            print(f"\n[{i}/{total_ops}] {op_type.upper()} operation:")
            
            if op_type == "download":
                # Extract parameters
                year_id = op.get("year_id")
                sending_id = op.get("sending_id")
                receiving_id = op.get("receiving_id")
                major_key = op.get("major_key")
                output_dir = Path(op.get("output_dir", "./json"))
                
                # Validate parameters
                if not all([year_id, sending_id, receiving_id, major_key]):
                    print("❌ Missing required parameters for download operation")
                    continue
                
                # Download the agreement
                try:
                    print(f"📥 Downloading agreement: {sending_id} → {receiving_id}, major {major_key}")
                    json_file = download_agreement_json(
                        year_id,
                        sending_id,
                        receiving_id,
                        major_key,
                        output_dir
                    )
                    print(f"✅ Downloaded to {json_file}")
                    
                    # Add a small delay to avoid hammering the API
                    time.sleep(1)
                except Exception as e:
                    print(f"❌ Error downloading agreement: {e}")
            
            elif op_type == "convert":
                # Extract parameters
                input_file = op.get("input_file")
                output_file = op.get("output_file")
                major_key = op.get("major_key")  # Extract major_key from the operation
                source_url = op.get("source_url")
                
                # Validate parameters
                if not all([input_file, output_file]):
                    print("❌ Missing required parameters for convert operation")
                    continue
                
                # Convert the file
                try:
                    print(f"🔄 Converting {input_file} to RAG format")
                    rag_data = process_assist_json_file(
                        input_file, manual_source_url=source_url, major_key=major_key
                    )
                    save_rag_json(rag_data, output_file)
                    print(f"✅ Converted to {output_file}")
                except Exception as e:
                    print(f"❌ Error converting file: {e}")
            
            else:
                print(f"❓ Unknown operation type: {op_type}")
        
        print(f"\n✅ Batch processing complete")
    
    except Exception as e:
        print(f"❌ Error processing batch config: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the command-line interface."""
    # Create the main parser
    parser = argparse.ArgumentParser(
        description="TransferAI ASSIST Scraper v2 - Download and process articulation agreements from ASSIST.org"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download agreements from ASSIST API")
    download_parser.add_argument("--year", required=True, help="Academic year ID (e.g., 75 for 2024-2025)")
    download_parser.add_argument("--sending", required=True, help="Sending institution ID (e.g., 113 for De Anza)")
    download_parser.add_argument("--receiving", required=True, help="Receiving institution ID (e.g., 7 for UCSD)")
    download_parser.add_argument("--major", required=True, help="Major key ID")
    download_parser.add_argument("--output", default="./json", help="Output directory for JSON files")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert ASSIST JSON to RAG format")
    convert_parser.add_argument("--input", required=True, help="Input ASSIST JSON file")
    convert_parser.add_argument("--output", required=True, help="Output RAG JSON file")
    convert_parser.add_argument("--major-key", help="Major key ID for accurate source URL generation")
    convert_parser.add_argument("--source-url", help="Manual source URL override")
    
    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Process a batch of operations from a config file")
    batch_parser.add_argument("--config", required=True, help="Path to JSON config file")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "download":
        download_command(args)
    elif args.command == "convert":
        convert_command(args)
    elif args.command == "batch":
        batch_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 