"""Tests for the planner service.

Tests the planner's ability to generate and validate DAG plans from user questions
using mocked OpenAI responses to avoid network dependencies.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import agent.planner as pln  # noqa: E402
from agent.planner import get_plan, validate_plan  # noqa: E402


def test_planner_generates_valid_plan(monkeypatch):
    """Test that planner generates a valid plan from user question."""
    # Mock OpenAI response with a valid plan
    fake_plan = [
        {
            "id": "search_courses",
            "tool": "course_search",
            "args": {"query": "computer science"},
            "depends_on": []
        },
        {
            "id": "analyze_results",
            "tool": "llm_step",
            "args": {"instructions": "Analyze the search results"},
            "depends_on": ["search_courses"]
        }
    ]
    
    fake_response_content = json.dumps(fake_plan)
    
    # Mock both v1.x and legacy OpenAI APIs
    def mock_openai_v1_create(**kwargs):
        """Mock for new OpenAI v1.x API."""
        return type("Response", (), {
            "choices": [
                type("Choice", (), {
                    "message": type("Message", (), {
                        "content": fake_response_content
                    })()
                })()
            ]
        })()
    
    def mock_openai_legacy_create(**kwargs):
        """Mock for legacy OpenAI v0.x API."""
        return type("Response", (), {
            "choices": [
                type("Choice", (), {
                    "message": type("Message", (), {
                        "content": fake_response_content
                    })()
                })()
            ]
        })()
    
    # Mock both API versions
    monkeypatch.setattr("openai.chat.completions.create", mock_openai_v1_create)
    monkeypatch.setattr("openai.ChatCompletion.create", mock_openai_legacy_create)
    
    # Mock the client creation to avoid API key requirement
    monkeypatch.setattr("agent.planner._get_openai_client", lambda: None)
    
    # Mock the API version detection
    monkeypatch.setattr("agent.planner._HAS_OPENAI_V1", False)  # Use legacy API for test
    
    # Test the planner
    plan = get_plan("Find computer science courses")
    
    assert len(plan) == 2
    assert plan[0]["tool"] == "course_search"
    assert plan[1]["tool"] == "llm_step"
    assert plan[1]["depends_on"] == ["search_courses"]


def test_planner_handles_wrapped_response(monkeypatch):
    """Test that planner handles responses wrapped in objects."""
    # Mock response with plan wrapped in an object
    fake_wrapped_response = {
        "plan": [
            {
                "id": "simple_task",
                "tool": "llm_step", 
                "args": {"instructions": "Hello world"},
                "depends_on": []
            }
        ]
    }
    
    fake_content = json.dumps(fake_wrapped_response)
    
    def mock_create(**kwargs):
        return type("Response", (), {
            "choices": [
                type("Choice", (), {
                    "message": type("Message", (), {"content": fake_content})()
                })()
            ]
        })()
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_create)
    monkeypatch.setattr("agent.planner._get_openai_client", lambda: None)
    monkeypatch.setattr("agent.planner._HAS_OPENAI_V1", False)
    
    plan = get_plan("Say hello")
    
    assert len(plan) == 1
    assert plan[0]["tool"] == "llm_step"


def test_planner_handles_structured_output_format(monkeypatch):
    """Test that planner handles OpenAI's structured output format."""
    # Mock response with OpenAI's structured output format: {'type': 'json_object', 'value': {...}}
    fake_structured_response = {
        "type": "json_object",
        "value": {
            "nodes": [
                {
                    "id": "search_task",
                    "tool": "course_search",
                    "args": {"query": "computer science"},
                    "depends_on": []
                },
                {
                    "id": "analyze_task",
                    "tool": "llm_step",
                    "args": {"instructions": "Analyze the results"},
                    "depends_on": ["search_task"]
                }
            ]
        }
    }
    
    fake_content = json.dumps(fake_structured_response)
    
    def mock_create(**kwargs):
        return type("Response", (), {
            "choices": [
                type("Choice", (), {
                    "message": type("Message", (), {"content": fake_content})()
                })()
            ]
        })()
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_create)
    monkeypatch.setattr("agent.planner._get_openai_client", lambda: None)
    monkeypatch.setattr("agent.planner._HAS_OPENAI_V1", False)
    
    plan = get_plan("Find CS courses")
    
    assert len(plan) == 2
    assert plan[0]["tool"] == "course_search"
    assert plan[1]["tool"] == "llm_step"
    assert plan[1]["depends_on"] == ["search_task"]


def test_planner_handles_data_format(monkeypatch):
    """Test that planner handles OpenAI's 'data' format variation."""
    # Mock response with 'data' instead of 'value'
    fake_data_response = {
        "type": "json_object",
        "data": {
            "nodes": [
                {
                    "id": "lookup_task",
                    "tool": "major_requirement",
                    "args": {"major_name": "Computer Science"},
                    "depends_on": []
                }
            ]
        }
    }
    
    fake_content = json.dumps(fake_data_response)
    
    def mock_create(**kwargs):
        return type("Response", (), {
            "choices": [
                type("Choice", (), {
                    "message": type("Message", (), {"content": fake_content})()
                })()
            ]
        })()
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_create)
    monkeypatch.setattr("agent.planner._get_openai_client", lambda: None)
    monkeypatch.setattr("agent.planner._HAS_OPENAI_V1", False)
    
    plan = get_plan("Find major requirements")
    
    assert len(plan) == 1
    assert plan[0]["tool"] == "major_requirement"
    assert plan[0]["depends_on"] == []


def test_validate_plan_success():
    """Test that valid plans pass validation."""
    valid_plan = [
        {
            "id": "test_node",
            "tool": "course_search",
            "args": {"query": "test"},
            "depends_on": []
        }
    ]
    
    # Should not raise any exception
    validate_plan(valid_plan)


def test_validate_plan_failure():
    """Test that invalid plans fail validation."""
    invalid_plan = [
        {
            # Missing required 'id' field
            "tool": "course_search",
            "args": {"query": "test"},
            "depends_on": []
        }
    ]
    
    with pytest.raises(Exception):  # ValidationError or similar
        validate_plan(invalid_plan)


def test_planner_handles_api_errors(monkeypatch):
    """Test that planner handles OpenAI API errors gracefully."""
    def mock_failing_create(**kwargs):
        raise Exception("API Error: Rate limit exceeded")
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_failing_create)
    monkeypatch.setattr("agent.planner._get_openai_client", lambda: None)
    monkeypatch.setattr("agent.planner._HAS_OPENAI_V1", False)
    
    with pytest.raises(RuntimeError, match="OpenAI API call failed"):
        get_plan("Test question")


def test_planner_handles_invalid_json(monkeypatch):
    """Test that planner handles invalid JSON responses."""
    def mock_invalid_json_create(**kwargs):
        return type("Response", (), {
            "choices": [
                type("Choice", (), {
                    "message": type("Message", (), {
                        "content": "This is not valid JSON!"
                    })()
                })()
            ]
        })()
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_invalid_json_create)
    monkeypatch.setattr("agent.planner._get_openai_client", lambda: None)
    monkeypatch.setattr("agent.planner._HAS_OPENAI_V1", False)
    
    with pytest.raises(RuntimeError, match="OpenAI returned invalid JSON"):
        get_plan("Test question")


def test_planner_missing_prompt_file(monkeypatch, tmp_path):
    """Test that planner handles missing prompt file gracefully."""
    # Change the prompt path to a non-existent file
    monkeypatch.setattr("agent.planner.PROMPT_XML_PATH", tmp_path / "nonexistent.xml")
    
    with pytest.raises(FileNotFoundError, match="Planner prompt not found"):
        get_plan("Test question")


def test_planner_missing_schema_file(monkeypatch, tmp_path):
    """Test that planner handles missing schema file gracefully."""
    # Mock a valid plan response
    fake_plan = [{"id": "test", "tool": "llm_step", "args": {}, "depends_on": []}]
    
    # Change the schema path to a non-existent file
    monkeypatch.setattr("agent.planner.SCHEMA_PATH", tmp_path / "nonexistent.json")
    
    with pytest.raises(FileNotFoundError, match="Schema not found"):
        validate_plan(fake_plan) 