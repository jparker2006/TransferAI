"""
Configuration Management for TransferAI

This module provides configuration management for the TransferAI system.
It supports different environments (development, testing, production) and
allows for runtime configuration overrides.
"""

import os
import json
from enum import Enum
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Config:
    """
    Configuration management for TransferAI.
    
    Loads configuration from environment variables and configuration files,
    with support for runtime overrides.
    """
    
    def __init__(self, env: Optional[Environment] = None):
        """
        Initialize configuration with default values for the specified environment.
        
        Args:
            env: The environment to use for configuration. If None, will be determined
                 from the TRANSFERAI_ENV environment variable, defaulting to DEVELOPMENT.
        """
        # Determine environment
        self.env = env or self._determine_environment()
        logger.info(f"Initializing configuration for environment: {self.env.value}")
        
        # Initialize with default values
        self._config = self._default_config()
        
        # Load environment-specific configuration
        self._load_environment_config()
        
        # Load configuration from environment variables
        self._load_from_env_vars()
    
    @staticmethod
    def _determine_environment() -> Environment:
        """
        Determine the environment from environment variables.
        
        Returns:
            The detected environment, defaulting to DEVELOPMENT.
        """
        env_name = os.environ.get("TRANSFERAI_ENV", "development").lower()
        try:
            return Environment(env_name)
        except ValueError:
            logger.warning(f"Unknown environment: {env_name}. Using DEVELOPMENT.")
            return Environment.DEVELOPMENT
    
    def _default_config(self) -> Dict[str, Any]:
        """
        Get default configuration values.
        
        Returns:
            Dictionary of default configuration values.
        """
        return {
            # General settings
            "verbosity": "STANDARD",  # MINIMAL, STANDARD, DETAILED
            "debug_mode": self.env != Environment.PRODUCTION,
            
            # LLM settings
            "temperature": 0.2,
            "max_tokens": 1000,
            "timeout": 30,
            
            # Document settings
            "cache_documents": True,
            "cache_directory": ".transferai_cache",
            "cache_ttl": 86400,  # 24 hours in seconds
            
            # Query settings
            "default_query_type": "UNKNOWN",
            
            # Logging
            "log_level": "INFO",
            "log_file": None,  # None for console logging only
        }
    
    def _load_environment_config(self):
        """Load environment-specific configuration overrides."""
        if self.env == Environment.DEVELOPMENT:
            self._config.update({
                "debug_mode": True,
                "log_level": "DEBUG",
                "cache_ttl": 300,  # 5 minutes in development
            })
        elif self.env == Environment.TESTING:
            self._config.update({
                "debug_mode": True,
                "cache_documents": False,  # Don't cache in tests for predictability
                "log_level": "DEBUG",
            })
        elif self.env == Environment.PRODUCTION:
            self._config.update({
                "debug_mode": False,
                "log_level": "INFO",
                "cache_ttl": 86400 * 7,  # 7 days in production
            })
    
    def _load_from_env_vars(self):
        """Load configuration from environment variables."""
        prefix = "TRANSFERAI_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                if config_key in self._config:
                    # Convert value to appropriate type based on default
                    default_value = self._config[config_key]
                    if isinstance(default_value, bool):
                        self._config[config_key] = value.lower() in ("1", "true", "yes", "on")
                    elif isinstance(default_value, int):
                        try:
                            self._config[config_key] = int(value)
                        except ValueError:
                            logger.warning(f"Invalid integer value for {key}: {value}")
                    elif isinstance(default_value, float):
                        try:
                            self._config[config_key] = float(value)
                        except ValueError:
                            logger.warning(f"Invalid float value for {key}: {value}")
                    else:
                        self._config[config_key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key to retrieve.
            default: Default value to return if key is not found.
            
        Returns:
            The configuration value, or the default if not found.
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key to set.
            value: The value to set.
        """
        self._config[key] = value
    
    def update(self, **kwargs) -> None:
        """
        Update multiple configuration values.
        
        Args:
            **kwargs: Key-value pairs to update.
        """
        self._config.update(kwargs)
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the entire configuration as a dictionary.
        
        Returns:
            Dictionary of all configuration values.
        """
        return dict(self._config)


# Default configuration instance
default_config = Config()


def get_config() -> Config:
    """
    Get the default configuration instance.
    
    Returns:
        The default Config instance.
    """
    return default_config


def configure(**kwargs) -> None:
    """
    Update the default configuration with the provided values.
    
    Args:
        **kwargs: Key-value pairs to update.
    """
    default_config.update(**kwargs)


def load_config(config_path: Path) -> Config:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        A new Config instance with values from the file
        
    Raises:
        FileNotFoundError: If the config file does not exist
        json.JSONDecodeError: If the config file is not valid JSON
    """
    logger.info(f"Loading configuration from {config_path}")
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    # Create a new configuration instance
    config = Config()
    
    # Update with values from file
    config.update(**config_data)
    
    logger.info(f"Loaded configuration with {len(config_data)} values")
    return config
