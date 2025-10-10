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
        list_organizations_tool,
        dump_jira_team_data_tool,
        read_jira_team_data_tool,
        register_jira_report_tools
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
    mcp.tool()(dump_jira_team_data_tool(jira_client, jira_config))
    mcp.tool()(read_jira_team_data_tool(jira_client, jira_config))
    
    # Register Jira report tools
    register_jira_report_tools(mcp)
    
    print("✅ Registered Jira connector with 8 tools + 3 report tools")
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
            analyze_jira_data_tool,
            generate_email_summary_tool,
            custom_ai_analysis_tool,
            ai_summary_tool
        )
        
        # Create Gemini client and config
        from connectors.gemini.client import GeminiClient
        from connectors.gemini.config import GeminiConfig
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
    
        # Register Gemini tools
        mcp.tool()(analyze_jira_data_tool(gemini_client, gemini_config.get_config()))
        mcp.tool()(generate_email_summary_tool(gemini_client, gemini_config.get_config()))
        mcp.tool()(custom_ai_analysis_tool(gemini_client, gemini_config.get_config()))
        mcp.tool()(ai_summary_tool(gemini_client, gemini_config.get_config()))
        
        print("✅ Registered Gemini connector with 4 tools")
except Exception as e:
    print(f"❌ Failed to register Gemini connector: {e}")


# Initialize Email connector
try:
    from connectors.email.client import EmailClient
    from connectors.email.config import EmailConfig
    from connectors.email.tools import (
        send_email_tool,
        test_email_connection_tool,
        get_email_config_tool
    )
    
    # Create Email client and config
    email_config = EmailConfig()
    email_client = EmailClient(email_config.get_config())
    
    # Register Email tools (only working ones)
    mcp.tool()(send_email_tool(email_client, email_config.get_config()))
    mcp.tool()(test_email_connection_tool(email_client, email_config.get_config()))
    mcp.tool()(get_email_config_tool(email_client, email_config.get_config()))
    
    print("✅ Registered Email connector with 3 tools (send_email, test_email_connection, get_email_config)")
except Exception as e:
    print(f"❌ Failed to register Email connector: {e}")

# Built-in tool listing
@mcp.tool()
def list_available_tools() -> str:
    """List all available MCP tools"""
    return create_success_response({
        "message": "Work Planner MCP Server is running",
        "tools": [
            "search_issues", "get_team_issues", "get_project_info", 
            "get_user_info", "list_teams", "list_organizations",
            "dump_jira_team_data", "read_jira_team_data",
            "dump_slack_data", "read_slack_data", "search_slack_data",
            "list_slack_channels", "list_slack_dumps",
            "analyze_jira_data", "generate_email_summary", "custom_ai_analysis", "ai_summary",
            "send_email", "test_email_connection", "get_email_config",
            "list_available_tools"
        ],
        "total_tools": 20  # Removed 3 broken email tools
    })

if __name__ == "__main__":
    mcp.run()