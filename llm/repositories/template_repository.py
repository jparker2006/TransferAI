"""
TransferAI Template Repository

This module provides a repository for managing prompt templates used throughout
the TransferAI system. It handles loading, caching, and retrieving templates
for various query types and response formats.
"""

from typing import Dict, Any, List, Optional, Set
import os
import json
from pathlib import Path
import functools
import time
from datetime import datetime

# Cache decorator for method results
def cached_result(ttl_seconds: int = 3600):
    """
    Method decorator that caches results with a time-to-live (TTL).
    
    Args:
        ttl_seconds: Cache expiration time in seconds (default: 1 hour)
    """
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Create a cache key from the function arguments
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check if result is in cache and not expired
            if key in cache:
                result, timestamp = cache[key]
                if timestamp + ttl_seconds > time.time():
                    return result
            
            # Call the original function and cache the result
            result = func(self, *args, **kwargs)
            cache[key] = (result, time.time())
            return result
            
        # Add a method to clear the cache
        def clear_cache(self=None):
            cache.clear()
            
        wrapper.clear_cache = clear_cache
        wrapper._is_cached_method = True
            
        return wrapper
    return decorator


class TemplateRepository:
    """
    Repository for managing prompt templates.
    
    This class provides methods for loading and retrieving prompt templates
    used throughout the TransferAI system. It supports different template types
    for various query scenarios and response formats.
    
    Attributes:
        _templates: Dictionary mapping template names to their content
        _last_loaded: Timestamp of when templates were last loaded
    """
    
    def __init__(self):
        """Initialize the template repository."""
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._last_loaded: Optional[float] = None
        
    def load_templates(self, path: Optional[str] = None) -> int:
        """
        Load templates from the data source.
        
        Args:
            path: Optional path to the templates directory
            
        Returns:
            Number of templates loaded
        """
        if path is None:
            # Try to find the templates directory relative to current module
            current_dir = os.path.dirname(__file__)
            possible_paths = [
                os.path.join(current_dir, "..", "templates"),
                os.path.join(current_dir, "..", "..", "templates"),
                os.path.join(current_dir, "..", "llm", "templates")
            ]
            
            for p in possible_paths:
                if os.path.exists(p):
                    path = p
                    break
            
            if path is None:
                raise FileNotFoundError("Could not find templates directory in any expected location")
                
        # Load all template files from the directory
        template_files = [
            f for f in os.listdir(path)
            if f.endswith('.py') and not f.startswith('_')
        ]
        
        self._templates = {}
        
        for filename in template_files:
            template_path = os.path.join(path, filename)
            template_name = filename[:-3]  # Remove .py extension
            
            try:
                # Import the template module
                import importlib.util
                spec = importlib.util.spec_from_file_location(template_name, template_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Extract templates from the module
                templates = {
                    name: value for name, value in vars(module).items()
                    if isinstance(value, str) and not name.startswith('_')
                }
                
                self._templates[template_name] = templates
                
            except Exception as e:
                print(f"Error loading template {filename}: {e}")
                
        self._last_loaded = time.time()
        return sum(len(templates) for templates in self._templates.values())
        
    @cached_result(ttl_seconds=3600)
    def get_template(self, template_name: str, template_type: str = "default") -> Optional[str]:
        """
        Get a specific template by name and type.
        
        Args:
            template_name: Name of the template to retrieve
            template_type: Type of template (e.g., "course", "group", "default")
            
        Returns:
            The template string if found, None otherwise
        """
        if template_type in self._templates:
            return self._templates[template_type].get(template_name)
        return None
        
    def get_template_types(self) -> List[str]:
        """
        Get a list of available template types.
        
        Returns:
            List of template type names
        """
        return sorted(self._templates.keys())
        
    def get_templates_by_type(self, template_type: str) -> Dict[str, str]:
        """
        Get all templates of a specific type.
        
        Args:
            template_type: Type of templates to retrieve
            
        Returns:
            Dictionary mapping template names to their content
        """
        return self._templates.get(template_type, {}).copy()
        
    def get_reload_status(self) -> Dict[str, Any]:
        """
        Get information about the template loading status.
        
        Returns:
            Dictionary with template count and last load time
        """
        total_templates = sum(len(templates) for templates in self._templates.values())
        return {
            "template_count": total_templates,
            "template_types": len(self._templates),
            "last_loaded": datetime.fromtimestamp(self._last_loaded).isoformat() if self._last_loaded else None
        }
        
    def clear_cache(self) -> None:
        """Clear all cached results."""
        # Clear method-specific caches
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_is_cached_method') and attr._is_cached_method:
                attr.clear_cache(self)
