#!/usr/bin/env python3
"""
Work Planner MCP Server
Simple server that imports and registers tools from connectors
"""

import signal
import sys
from fastmcp import FastMCP
from utils.responses import create_success_response

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
        dump_slack_data_tool,
        read_slack_data_tool,
        search_slack_data_tool,
        list_slack_channels_tool,
        list_slack_dumps_tool
    )
    
    # Create Slack client and config
    slack_config = SlackConfig.load("config/slack.yaml")
    slack_client = SlackClient(slack_config)
    
    # Register Slack tools
    mcp.tool()(dump_slack_data_tool(slack_client, slack_config))
    mcp.tool()(read_slack_data_tool(slack_client, slack_config))
    mcp.tool()(search_slack_data_tool(slack_client, slack_config))
    mcp.tool()(list_slack_channels_tool(slack_client, slack_config))
    mcp.tool()(list_slack_dumps_tool(slack_client, slack_config))
    
    print("✅ Registered Slack connector with 5 unified tools")
except Exception as e:
    print(f"❌ Failed to register Slack connector: {e}")

# Initialize Gemini connector
try:
    from connectors.gemini.tools import (
        analyze_slack_data_tool,
        analyze_jira_data_tool,
        generate_email_summary_tool,
        custom_ai_analysis_tool
    )
    
    # Create Gemini client and config
    from connectors.gemini.client import GeminiClient
    from connectors.gemini.config import GeminiConfig
    
    gemini_config = GeminiConfig()
    gemini_client = GeminiClient(gemini_config.get_config())
    
    # Register Gemini tools
    mcp.tool()(analyze_slack_data_tool(gemini_client, gemini_config.get_config()))
    mcp.tool()(analyze_jira_data_tool(gemini_client, gemini_config.get_config()))
    mcp.tool()(generate_email_summary_tool(gemini_client, gemini_config.get_config()))
    mcp.tool()(custom_ai_analysis_tool(gemini_client, gemini_config.get_config()))
    
    print("✅ Registered Gemini connector with 4 tools")
except Exception as e:
    print(f"❌ Failed to register Gemini connector: {e}")

# Initialize Schedule connector
try:
    from connectors.schedule.tools import (
        get_schedule_status_tool,
        run_scheduled_collection_tool,
        update_schedule_config_tool,
        add_team_to_schedule_tool,
        remove_team_from_schedule_tool,
        toggle_slack_attachments_tool
    )
    
    # Create Schedule client and config
    from connectors.schedule.config import ScheduleConfig
    
    schedule_config = ScheduleConfig()
    
    # Register Schedule tools
    mcp.tool()(get_schedule_status_tool(None, schedule_config))
    mcp.tool()(run_scheduled_collection_tool(None, schedule_config))
    mcp.tool()(update_schedule_config_tool(None, schedule_config))
    mcp.tool()(add_team_to_schedule_tool(None, schedule_config))
    mcp.tool()(remove_team_from_schedule_tool(None, schedule_config))
    mcp.tool()(toggle_slack_attachments_tool(None, schedule_config))
    
    print("✅ Registered Schedule connector with 6 tools")
except Exception as e:
    print(f"❌ Failed to register Schedule connector: {e}")

# Built-in tool listing
@mcp.tool()
def list_available_tools() -> str:
    """List all available MCP tools"""
    return create_success_response({
        "message": "Work Planner MCP Server is running",
        "tools": [
            "search_issues", "get_team_issues", "get_project_info", 
            "get_user_info", "list_teams", "list_organizations",
            "dump_slack_data", "read_slack_data", "search_slack_data",
            "list_slack_channels", "list_slack_dumps",
            "analyze_slack_data", "analyze_jira_data", "generate_email_summary",
            "custom_ai_analysis", "get_schedule_status", "run_scheduled_collection",
            "update_schedule_config", "add_team_to_schedule", "remove_team_from_schedule",
            "list_available_tools"
        ],
        "total_tools": 21
    })

if __name__ == "__main__":
    mcp.run()