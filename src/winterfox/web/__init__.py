"""
Web dashboard for winterfox research system.

Provides:
- REST API for graph visualization and management
- WebSocket streaming for real-time cycle updates
- Static file serving for React frontend
"""

from .server import create_app

__all__ = ["create_app"]
