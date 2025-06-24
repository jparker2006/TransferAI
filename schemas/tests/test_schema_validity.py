"""Test suite for validating all JSON Schema files in the TransferAI project.

This module discovers and validates every *.schema.json file under the schemas/
directory, ensuring they conform to JSON Schema Draft 2020-12 and meet project
style requirements.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
import jsonschema
from jsonschema.validators import Draft202012Validator


# Discover all schema files in the project
SCHEMAS_ROOT = Path(__file__).parent.parent  # schemas/
ALL_SCHEMA_PATHS = list(SCHEMAS_ROOT.rglob("*.schema.json"))


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_PATHS, ids=lambda p: str(p.relative_to(SCHEMAS_ROOT)))
def test_schema_is_valid(schema_path: Path) -> None:
    """Test that each schema file is syntactically valid Draft 2020-12."""
    
    # Load the JSON content
    with schema_path.open("r", encoding="utf-8") as f:
        schema_data = json.load(f)
    
    # Validate that it's a syntactically correct JSON Schema
    Draft202012Validator.check_schema(schema_data)
    
    # Additional constraint: tool schemas must have additionalProperties: false
    if "tools" in schema_path.parts:
        assert schema_data.get("additionalProperties") is False, (
            f"Tool schema {schema_path.name} must have 'additionalProperties': false"
        )
    
    # Special constraint for dag_node.schema.json
    if schema_path.name == "dag_node.schema.json":
        required_fields = schema_data.get("required", [])
        expected_fields = {"id", "tool", "args", "depends_on"}
        actual_fields = set(required_fields)
        
        assert actual_fields == expected_fields, (
            f"dag_node.schema.json must require exactly {sorted(expected_fields)}, "
            f"but found {sorted(actual_fields)}"
        )


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_PATHS, ids=lambda p: str(p.relative_to(SCHEMAS_ROOT)))
def test_schema_has_draft_2020_12(schema_path: Path) -> None:
    """Test that each schema declares Draft 2020-12."""
    
    with schema_path.open("r", encoding="utf-8") as f:
        schema_data = json.load(f)
    
    schema_uri = schema_data.get("$schema", "")
    expected_uri = "https://json-schema.org/draft/2020-12/schema"
    
    assert schema_uri == expected_uri, (
        f"Schema {schema_path.name} must declare '$schema': '{expected_uri}', "
        f"but found: '{schema_uri}'"
    )


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_PATHS, ids=lambda p: str(p.relative_to(SCHEMAS_ROOT)))
def test_schema_has_required_metadata(schema_path: Path) -> None:
    """Test that each schema has title and description."""
    
    with schema_path.open("r", encoding="utf-8") as f:
        schema_data = json.load(f)
    
    # Check for required metadata fields
    assert "title" in schema_data, f"Schema {schema_path.name} must have a 'title' field"
    assert "description" in schema_data, f"Schema {schema_path.name} must have a 'description' field"
    
    # Ensure they're non-empty strings
    assert isinstance(schema_data["title"], str) and schema_data["title"].strip(), (
        f"Schema {schema_path.name} 'title' must be a non-empty string"
    )
    assert isinstance(schema_data["description"], str) and schema_data["description"].strip(), (
        f"Schema {schema_path.name} 'description' must be a non-empty string"
    )


def test_all_tool_schemas_exist() -> None:
    """Test that we have schemas for all expected tools."""
    
    tools_dir = SCHEMAS_ROOT / "tools"
    if not tools_dir.exists():
        pytest.skip("tools directory not found")
    
    # Expected tool schema files based on the project structure
    expected_tools = {
        "articulation_match_tool.schema.json",
        "breadth_coverage_tool.schema.json", 
        "course_detail_tool.schema.json",
        "course_search_tool.schema.json",
        "deadline_lookup_tool.schema.json",
        "faq_search_tool.schema.json",
        "glossary_tool.schema.json",
        "gpa_projection_tool.schema.json",
        "major_requirement_tool.schema.json",
        "prereq_graph_tool.schema.json",
        "professor_rating_tool.schema.json",
        "schedule_conflict_tool.schema.json",
        "section_lookup_tool.schema.json",
        "unit_calculator_tool.schema.json",
    }
    
    actual_tools = {f.name for f in tools_dir.glob("*.schema.json")}
    
    missing_tools = expected_tools - actual_tools
    extra_tools = actual_tools - expected_tools
    
    assert not missing_tools, f"Missing tool schemas: {sorted(missing_tools)}"
    # Note: extra tools are allowed (project might add new tools)


def test_dag_node_schema_exists() -> None:
    """Test that the dag_node schema exists and is properly structured."""
    
    dag_schema_path = SCHEMAS_ROOT / "dag_node.schema.json"
    assert dag_schema_path.exists(), "dag_node.schema.json must exist"
    
    with dag_schema_path.open("r", encoding="utf-8") as f:
        schema_data = json.load(f)
    
    # Verify it's an object schema
    assert schema_data.get("type") == "object", "dag_node schema must be type 'object'"
    
    # Verify it has properties for the required fields
    properties = schema_data.get("properties", {})
    required_props = {"id", "tool", "args", "depends_on"}
    
    for prop in required_props:
        assert prop in properties, f"dag_node schema must define property '{prop}'"


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_PATHS, ids=lambda p: str(p.relative_to(SCHEMAS_ROOT)))
def test_schema_json_format(schema_path: Path) -> None:
    """Test that each schema file is valid JSON."""
    
    try:
        with schema_path.open("r", encoding="utf-8") as f:
            json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"Schema {schema_path.name} contains invalid JSON: {e}")


def test_schemas_directory_structure() -> None:
    """Test that the schemas directory has the expected structure."""
    
    assert SCHEMAS_ROOT.exists(), "schemas/ directory must exist"
    
    # Check for expected subdirectories and files
    expected_structure = [
        "dag_node.schema.json",
        "tools/",
    ]
    
    for item in expected_structure:
        path = SCHEMAS_ROOT / item
        assert path.exists(), f"Expected {item} to exist in schemas/"


if __name__ == "__main__":
    # Allow running this file directly for quick validation
    pytest.main([__file__, "-v"]) 