"""
TransferAI Configuration Models

This module defines the configuration models and settings for the TransferAI system.
It provides centralized configuration with type validation and default values.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, Union, List


class VerbosityLevel(Enum):
    """Verbosity levels for responses."""
    CONCISE = "CONCISE"
    STANDARD = "STANDARD"
    DETAILED = "DETAILED"


@dataclass
class LLMConfig:
    """Configuration for language model interactions."""
    model_name: str = "deepseek-r1:1.5b"
    temperature: float = 0.2
    max_tokens: int = 1000
    timeout: float = 30.0
    request_timeout: float = 30.0


@dataclass
class RepositoryConfig:
    """Configuration for document repositories."""
    data_path: Optional[str] = None
    cache_enabled: bool = True
    max_cache_size: int = 1000
    refresh_interval: Optional[int] = None  # In seconds, None means no auto-refresh


@dataclass
class AppConfig:
    """Application-wide configuration settings."""
    verbosity: VerbosityLevel = VerbosityLevel.STANDARD
    debug_mode: bool = False
    log_level: str = "INFO"
    llm: LLMConfig = field(default_factory=LLMConfig)
    repository: RepositoryConfig = field(default_factory=RepositoryConfig)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AppConfig':
        """
        Create an AppConfig from a dictionary.
        
        Args:
            config_dict: Dictionary containing configuration options
            
        Returns:
            Configured AppConfig instance
        """
        # Extract nested configs first
        llm_dict = config_dict.pop('llm', {})
        repository_dict = config_dict.pop('repository', {})
        
        # Handle verbosity conversion
        if 'verbosity' in config_dict and isinstance(config_dict['verbosity'], str):
            try:
                config_dict['verbosity'] = VerbosityLevel[config_dict['verbosity'].upper()]
            except KeyError:
                config_dict['verbosity'] = VerbosityLevel.STANDARD
                
        # Create the config instance
        config = cls(**config_dict)
        
        # Apply nested configs
        if llm_dict:
            config.llm = LLMConfig(**llm_dict)
        if repository_dict:
            config.repository = RepositoryConfig(**repository_dict)
            
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert config to a dictionary.
        
        Returns:
            Dictionary representation of the configuration
        """
        result = {
            "verbosity": self.verbosity.value,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
            "llm": {
                "model_name": self.llm.model_name,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
                "request_timeout": self.llm.request_timeout
            },
            "repository": {
                "data_path": self.repository.data_path,
                "cache_enabled": self.repository.cache_enabled,
                "max_cache_size": self.repository.max_cache_size,
                "refresh_interval": self.repository.refresh_interval
            }
        }
        return result
    
    def update(self, **kwargs) -> 'AppConfig':
        """
        Update configuration with new values.
        
        Args:
            **kwargs: Configuration options to update
            
        Returns:
            Updated AppConfig instance (self)
        """
        # Handle nested updates
        llm_updates = kwargs.pop('llm', {})
        repo_updates = kwargs.pop('repository', {})
        
        # Update top-level attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                # Special handling for verbosity
                if key == 'verbosity' and isinstance(value, str):
                    try:
                        setattr(self, key, VerbosityLevel[value.upper()])
                    except KeyError:
                        pass
                else:
                    setattr(self, key, value)
        
        # Update LLM config
        for key, value in llm_updates.items():
            if hasattr(self.llm, key):
                setattr(self.llm, key, value)
                
        # Update repository config
        for key, value in repo_updates.items():
            if hasattr(self.repository, key):
                setattr(self.repository, key, value)
                
        return self
