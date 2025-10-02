"""
Slack tools registration - Unified Tools
"""

# Unified tools (recommended)
from .unified_slack_tools import (
    dump_slack_data_tool,
    read_slack_data_tool,
    search_slack_data_tool,
    list_slack_channels_tool,
    list_slack_dumps_tool
)

# Legacy individual tools (for backward compatibility)
from .slack_dumper import (
    dump_slack_channel_tool,
    dump_team_slack_data_tool,
    list_team_slack_channels_tool
)
from .slack_reader import (
    read_slack_channel_tool,
    read_team_slack_data_tool,
    list_slack_dumps_tool as legacy_list_slack_dumps_tool,
    get_slack_dump_summary_tool,
    force_fresh_slack_dump_tool
)
from .search_slack_mentions import (
    search_slack_mentions_tool,
    search_team_slack_mentions_tool
)


def get_slack_tools(client, config):
    """Return all Slack tools (unified + legacy)"""
    return [
        # Unified tools (recommended)
        dump_slack_data_tool(client, config),
        read_slack_data_tool(client, config),
        search_slack_data_tool(client, config),
        list_slack_channels_tool(client, config),
        list_slack_dumps_tool(client, config),
        
        # Legacy tools (for backward compatibility)
        dump_slack_channel_tool(client, config),
        dump_team_slack_data_tool(client, config),
        list_team_slack_channels_tool(client, config),
        read_slack_channel_tool(client, config),
        read_team_slack_data_tool(client, config),
        legacy_list_slack_dumps_tool(client, config),
        get_slack_dump_summary_tool(client, config),
        force_fresh_slack_dump_tool(client, config),
        search_slack_mentions_tool(client, config),
        search_team_slack_mentions_tool(client, config),
    ]


def get_unified_slack_tools(client, config):
    """Return only the unified Slack tools"""
    return [
        dump_slack_data_tool(client, config),
        read_slack_data_tool(client, config),
        search_slack_data_tool(client, config),
        list_slack_channels_tool(client, config),
        list_slack_dumps_tool(client, config),
    ]
