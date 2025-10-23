"""
Email Tools for Work Planner MCP Server
MCP tools for sending emails using configured templates and recipients
"""

from .email_tools import (
    send_email_tool,
    test_email_connection_tool,
    get_email_config_tool
)
from .daily_report_tool import send_team_daily_report_tool
from .inbox_tools import extract_email_todos_tool

__all__ = [
    'send_email_tool',
    'test_email_connection_tool',
    'get_email_config_tool',
    'send_team_daily_report_tool',
    'extract_email_todos_tool'
]

