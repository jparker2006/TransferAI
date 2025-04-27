"""
Test file to verify local embeddings work properly
"""

import sys
import os

# Add the project root to sys.path to allow imports from all modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import after setting up path
from llm.main import TransferAIEngine

def test_engine_loads_with_local_embeddings():
    """Test that the TransferAIEngine loads correctly with local embeddings"""
    print("Initializing TransferAIEngine...")
    engine = TransferAIEngine()
    
    print("Configuring engine...")
    engine.configure()
    
    print("Loading documents with local embeddings...")
    engine.load()
    
    print("Success! Engine loaded with local embeddings")
    
    # Run a simple test query to make sure everything works
    print("\nTesting a simple query...")
    response = engine.handle_query("Which De Anza courses satisfy CSE 8A at UCSD?")
    print(f"\nResponse received: {'Successfully' if response else 'Failed'}")
    print("\nTest completed.")
    
    return response is not None

if __name__ == "__main__":
    success = test_engine_loads_with_local_embeddings()
    print(f"\nTest {'passed' if success else 'failed'}!")
    sys.exit(0 if success else 1) 