"""
Utility Functions for TransferAI Engine

This module provides utility functions for the TransferAI engine, including:
- Logging helpers
- Version information
- Handler registration helpers
"""

import importlib
import inspect
import logging
import os
import sys
from typing import List, Type, Dict, Any, TypeVar, Optional, Set, Tuple

# Type variable for handler classes
T = TypeVar('T')

# Set up logging
logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file, or None for console logging only
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        logger.warning(f"Invalid log level: {log_level}, using INFO")
        numeric_level = logging.INFO
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            logger.error(f"Failed to set up file logging to {log_file}: {e}")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    
    # Add our handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    logger.debug("Logging configured")


def get_version() -> str:
    """
    Get the TransferAI version.
    
    Returns:
        The current version string.
    """
    try:
        from llm import __version__
        return __version__
    except (ImportError, AttributeError):
        return "1.5.0"  # Default version
    

def load_handler_classes(
    package_path: str, 
    base_class: Type[T],
    exclude: Optional[Set[str]] = None
) -> List[Type[T]]:
    """
    Load all handler classes from a package.
    
    Args:
        package_path: The package path to scan (e.g., 'llm.handlers')
        base_class: The base class that discovered classes should extend
        exclude: Optional set of class names to exclude
        
    Returns:
        List of handler classes found in the package
    """
    if exclude is None:
        exclude = set()
        
    logger.debug(f"Loading handler classes from {package_path}")
    
    try:
        # Split package path into parts
        parts = package_path.split('.')
        
        # Import the package
        package = importlib.import_module(package_path)
        
        # Get package directory 
        package_dir = os.path.dirname(package.__file__)
        
        # Find Python files in package directory
        handler_classes = []
        
        for file in os.listdir(package_dir):
            # Skip non-Python files, __init__.py, and files with leading underscore
            if not file.endswith('.py') or file == '__init__.py' or file.startswith('_'):
                continue
                
            module_name = f"{package_path}.{file[:-3]}"
            try:
                # Import the module
                module = importlib.import_module(module_name)
                
                # Find all classes in the module that extend the base class
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, base_class) and 
                        obj.__module__ == module_name and 
                        name not in exclude):
                        logger.debug(f"Found handler class: {name}")
                        handler_classes.append(obj)
            except Exception as e:
                logger.warning(f"Error loading module {module_name}: {e}")
        
        return handler_classes
    except Exception as e:
        logger.error(f"Error loading handler classes from {package_path}: {e}")
        return []


def format_error(error: Exception, include_traceback: bool = False) -> str:
    """
    Format an exception for display.
    
    Args:
        error: The exception to format
        include_traceback: Whether to include the traceback
        
    Returns:
        Formatted error string
    """
    if include_traceback:
        import traceback
        return f"{type(error).__name__}: {str(error)}\n\n{traceback.format_exc()}"
    else:
        return f"{type(error).__name__}: {str(error)}"
