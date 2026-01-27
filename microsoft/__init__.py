"""
Microsoft Excel Online Integration Module
Provides authentication and Excel sync capabilities for OneDrive.
"""

from .auth import get_access_token, is_configured, refresh_access_token
from .excel_handler import add_break_event, init_excel_handler

__all__ = [
    'get_access_token',
    'is_configured',
    'refresh_access_token',
    'add_break_event',
    'init_excel_handler',
]
