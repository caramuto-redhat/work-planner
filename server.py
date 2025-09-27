#!/usr/bin/env python3
"""
Features Teams MCP Server
Simple server that imports and registers tools from connectors
"""

from fastmcp import FastMCP
from utils.responses import create_success_response

# Create MCP server
mcp = FastMCP()

# Initialize Jira connector
try:
    from connectors.jira.client import JiraClient
    from connectors.jira.config import JiraConfig
    from connectors.jira.tools import (
        search_issues_tool,
        get_team_issues_tool,
        get_project_info_tool,
        get_user_info_tool,
        list_teams_tool,
        list_organizations_tool
    )
    
    # Create Jira client and config
    jira_config = JiraConfig.load("config/jira.yaml")
    jira_client = JiraClient(jira_config)
    
    # Register Jira tools
    mcp.tool()(search_issues_tool(jira_client, jira_config))
    mcp.tool()(get_team_issues_tool(jira_client, jira_config))
    mcp.tool()(get_project_info_tool(jira_client, jira_config))
    mcp.tool()(get_user_info_tool(jira_client, jira_config))
    mcp.tool()(list_teams_tool(jira_client, jira_config))
    mcp.tool()(list_organizations_tool(jira_client, jira_config))
    
    print("✅ Registered Jira connector with 6 tools")
except Exception as e:
    print(f"❌ Failed to register Jira connector: {e}")

# Initialize Slack connector
try:
    from connectors.slack.client import SlackClient
    from connectors.slack.config import SlackConfig
    from connectors.slack.tools import (
        dump_slack_channel_tool,
        dump_team_slack_data_tool,
        list_team_slack_channels_tool,
        read_slack_channel_tool,
        read_team_slack_data_tool,
        list_slack_dumps_tool,
        get_slack_dump_summary_tool,
        force_fresh_slack_dump_tool,
        search_slack_mentions_tool,
        search_team_slack_mentions_tool
    )
    
    # Create Slack client and config
    slack_config = SlackConfig.load("config/slack.yaml")
    slack_client = SlackClient(slack_config)
    
    # Register Slack tools
    mcp.tool()(dump_slack_channel_tool(slack_client, slack_config))
    mcp.tool()(dump_team_slack_data_tool(slack_client, slack_config))
    mcp.tool()(list_team_slack_channels_tool(slack_client, slack_config))
    mcp.tool()(read_slack_channel_tool(slack_client, slack_config))
    mcp.tool()(read_team_slack_data_tool(slack_client, slack_config))
    mcp.tool()(list_slack_dumps_tool(slack_client, slack_config))
    mcp.tool()(get_slack_dump_summary_tool(slack_client, slack_config))
    mcp.tool()(force_fresh_slack_dump_tool(slack_client, slack_config))
    mcp.tool()(search_slack_mentions_tool(slack_client, slack_config))
    mcp.tool()(search_team_slack_mentions_tool(slack_client, slack_config))
    
    print("✅ Registered Slack connector with 10 tools")
except Exception as e:
    print(f"❌ Failed to register Slack connector: {e}")

# Built-in tool listing
@mcp.tool()
def list_available_tools() -> str:
    """List all available MCP tools"""
    return create_success_response({
        "message": "Features Teams MCP Server is running",
        "tools": [
            "search_issues", "get_team_issues", "get_project_info", 
            "get_user_info", "list_teams", "list_organizations",
            "dump_slack_channel", "dump_team_slack_data", "list_team_slack_channels",
            "read_slack_channel", "read_team_slack_data", "list_slack_dumps",
            "get_slack_dump_summary", "force_fresh_slack_dump",
            "search_slack_mentions", "search_team_slack_mentions",
            "list_available_tools"
        ],
        "total_tools": 17
    })

if __name__ == "__main__":
    mcp.run()