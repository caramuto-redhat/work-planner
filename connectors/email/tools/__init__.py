"""
Email Tools for Work Planner MCP Server
MCP tools for sending emails using configured templates and recipients
"""

from .email_tools import (
    send_email_tool,
    send_daily_summary_tool,
    send_alert_tool,
    send_data_collection_report_tool,
    test_email_connection_tool,
    get_email_config_tool
)

__all__ = [
    'send_email_tool',
    'send_daily_summary_tool', 
    'send_alert_tool',
    'send_data_collection_report_tool',
    'test_email_connection_tool',
    'get_email_config_tool'
]

