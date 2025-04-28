"""
TransferAI Entry Point

This module serves as the entry point for the TransferAI system.
It provides a simple CLI interface to interact with the system.
"""

import argparse
import logging
import sys
from pathlib import Path

from llm.engine.transfer_engine import TransferAIEngine
from llm.engine.config import Config, load_config
from llm.services.prompt_service import VerbosityLevel

def main():
    """Main entry point for the CLI interface."""
    parser = argparse.ArgumentParser(description="TransferAI CLI")
    parser.add_argument("query", help="Query to process")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--verbosity", default="STANDARD", choices=["MINIMAL", "STANDARD", "DETAILED"], 
                       help="Verbosity level")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = None
        if args.config:
            config = load_config(Path(args.config))
        else:
            config = Config()
            
        # Override config with CLI arguments
        config.update(
            verbosity=args.verbosity,
            debug_mode=args.debug,
            log_level=args.log_level
        )
        
        # Initialize engine
        engine = TransferAIEngine(config=config)
        
        # Process query
        response = engine.handle_query(args.query)
        
        # Print response
        if response:
            print(response)
        else:
            print("No response generated.")
            
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()