"""
Slack tools registration - Core Tools Only
"""

# Core Slack tools (5 tools)
from .unified_slack_tools import (
    dump_slack_data_tool,
    read_slack_data_tool,
    search_slack_data_tool,
    list_slack_channels_tool,
    list_slack_dumps_tool
)

# TODO extraction tool
from .extract_slack_todos import extract_slack_todos_tool
