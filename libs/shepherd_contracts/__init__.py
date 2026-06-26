"""Shared contracts for Shepherd services."""
from .auth import CallerContext, Role

__all__ = [
    "Role",
    "CallerContext",
]
