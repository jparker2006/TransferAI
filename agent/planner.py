"""TransferAI Planner Service.

Converts user questions into validated DAG execution plans using OpenAI and 
the planner_prompt.xml system prompt. Outputs JSON plans that can be executed
by agent.executor.

Usage:
    python -m agent.planner "Find CS courses and analyze them"
    python -m agent.planner  # Interactive mode
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import jsonschema
from jsonschema import ValidationError

# Import OpenAI with fallback for different versions
try:
    import openai
    from openai import OpenAI
    _HAS_OPENAI_V1 = hasattr(openai, "OpenAI")
except ImportError as exc:
    raise ImportError(
        "OpenAI package required for planner. Install with: pip install openai"
    ) from exc

# Load environment for API key
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

import os

# Paths relative to project root
PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_XML_PATH = PROJECT_ROOT / "agent" / "planner_prompt.xml"
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "dag_node.schema.json"


def _get_openai_client():
    """Get OpenAI client, handling both v1.x and legacy versions."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Set it in .env or environment variables."
        )
    
    if _HAS_OPENAI_V1:
        # New v1.x client
        return OpenAI(api_key=api_key)
    else:
        # Legacy v0.x - set global key
        openai.api_key = api_key
        return None  # Use global openai module


def get_plan(question: str, *, model: str = "gpt-4o", temperature: float = 0.1) -> List[Dict[str, Any]]:
    """Generate a DAG plan from a user question using OpenAI.
    
    Args:
        question: User's question about course planning/transfer
        model: OpenAI model to use (default: gpt-4o)
        temperature: Sampling temperature (default: 0.1 for consistency)
        
    Returns:
        List of DAG nodes representing the execution plan
        
    Raises:
        RuntimeError: If OpenAI call fails or returns invalid JSON
        FileNotFoundError: If planner_prompt.xml is missing
    """
    # Load system prompt from XML
    if not PROMPT_XML_PATH.exists():
        raise FileNotFoundError(f"Planner prompt not found: {PROMPT_XML_PATH}")
    
    system_prompt = PROMPT_XML_PATH.read_text(encoding="utf-8")
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    
    # Call OpenAI with appropriate API version
    client = _get_openai_client()
    
    try:
        if _HAS_OPENAI_V1:
            # New v1.x API
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            content = response.choices[0].message.content
        else:
            # Legacy v0.x API
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            content = response.choices[0].message.content
            
    except Exception as exc:
        raise RuntimeError(f"OpenAI API call failed: {exc}") from exc
    
    # Parse JSON response
    try:
        plan_data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenAI returned invalid JSON: {exc}\nContent: {content}") from exc
    
    # Handle different response formats (array vs object with array)
    if isinstance(plan_data, list):
        return plan_data
    elif isinstance(plan_data, dict) and "plan" in plan_data:
        return plan_data["plan"]
    elif isinstance(plan_data, dict) and "nodes" in plan_data:
        return plan_data["nodes"]
    elif isinstance(plan_data, dict) and ("value" in plan_data or "data" in plan_data):
        # Handle OpenAI's structured output format: {'type': 'json_object', 'value': {...}} or {'type': 'json_object', 'data': {...}}
        nested_data = plan_data.get("value") or plan_data.get("data")
        if isinstance(nested_data, list):
            return nested_data
        elif isinstance(nested_data, dict) and "plan" in nested_data:
            return nested_data["plan"]
        elif isinstance(nested_data, dict) and "nodes" in nested_data:
            return nested_data["nodes"]
        else:
            raise RuntimeError(f"Unexpected nested format in structured response: {type(nested_data)}\nContent: {nested_data}")
    else:
        raise RuntimeError(f"Unexpected response format: {type(plan_data)}\nContent: {plan_data}")


def validate_plan(plan: List[Dict[str, Any]]) -> None:
    """Validate each node in the plan against the DAG node schema.
    
    Args:
        plan: List of DAG nodes to validate
        
    Raises:
        ValidationError: If any node fails schema validation
        FileNotFoundError: If schema file is missing
    """
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found: {SCHEMA_PATH}")
    
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    
    for i, node in enumerate(plan):
        try:
            jsonschema.validate(node, schema)
        except ValidationError as exc:
            # Add context about which node failed
            exc.message = f"Node {i} (id: {node.get('id', 'unknown')}) failed validation: {exc.message}"
            raise exc


def main() -> None:
    """CLI entry point for the planner service."""
    # Get user question from command line or interactive input
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        try:
            question = input("User query> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            sys.exit(0)
    
    if not question:
        print("Error: No question provided", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Generate plan
        print(f"🤔 Planning for: {question}", file=sys.stderr)
        plan = get_plan(question)
        
        # Validate plan
        print(f"✅ Validating {len(plan)} nodes...", file=sys.stderr)
        validate_plan(plan)
        
        # Save to file
        output_path = Path("last_plan.json")
        plan_json = json.dumps(plan, indent=2, ensure_ascii=False)
        output_path.write_text(plan_json, encoding="utf-8")
        
        print(f"💾 Saved plan to {output_path}", file=sys.stderr)
        
        # Print to stdout for piping/capture
        print(plan_json)
        
    except ValidationError as exc:
        print(f"❌ Plan failed schema validation:\n{exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"❌ Planner failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main() 