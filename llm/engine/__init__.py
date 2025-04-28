"""
TransferAI Engine Package

This package contains the core engine and related components for TransferAI.
"""

__version__ = "1.5.0"

# Export main components
from .transfer_engine import TransferAIEngine
from .config import Config, get_config, configure, Environment

__all__ = [
    "TransferAIEngine",
    "Config",
    "get_config",
    "configure",
    "Environment",
]
