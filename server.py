#!/usr/bin/env python3
"""
Work Planner MCP Server
Simple server that imports and registers tools from connectors
"""

import os
import signal
import sys
from fastmcp import FastMCP
from utils.responses import create_success_response

# Load environment variables from ENV_FILE if specified (for local development)
# In container, variables are already set via --env-file flag
env_file = os.getenv('ENV_FILE')
if env_file and os.path.exists(env_file):
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    # Check if essential variables are already set (container mode)
    slack_token = os.getenv('SLACK_XOXC_TOKEN')
    jira_token = os.getenv('JIRA_API_TOKEN')
    if slack_token and jira_token:
        print(f"✅ Environment variables already available (container mode)")
    else:
        print(f"⚠️  No ENV_FILE specified and essential variables not found")

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
        register_jira_report_tools,
        extract_jira_todos_tool
    )
    from connectors.gemini.config import GeminiConfig
    
    # Create Jira client and config
    jira_config = JiraConfig.load("config/jira.yaml")
    jira_client = JiraClient(jira_config)
    
    # Load Gemini config for TODO extraction
    gemini_config_dict = GeminiConfig.load("config/gemini.yaml")
    
    # Register Jira tools
    mcp.tool()(search_issues_tool(jira_client, jira_config))
    mcp.tool()(get_team_issues_tool(jira_client, jira_config))
    mcp.tool()(get_project_info_tool(jira_client, jira_config))
    mcp.tool()(get_user_info_tool(jira_client, jira_config))
    mcp.tool()(list_teams_tool(jira_client, jira_config))
    mcp.tool()(list_organizations_tool(jira_client, jira_config))
    mcp.tool()(dump_jira_team_data_tool(jira_client, jira_config))
    mcp.tool()(read_jira_team_data_tool(jira_client, jira_config))
    mcp.tool()(extract_jira_todos_tool(jira_client, jira_config, gemini_config_dict))  # NEW: TODO extraction
    
    # Register Jira report tools
    register_jira_report_tools(mcp)
    
    print("✅ Registered Jira connector with 9 tools + 3 report tools")
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
        list_slack_dumps_tool,
        extract_slack_todos_tool
    )
    
    # Create Slack client and config
    slack_config = SlackConfig.load("config/slack.yaml")
    slack_client = SlackClient(slack_config)
    
    # Gemini config already loaded above for Jira TODO extraction
    
    # Register Slack tools
    mcp.tool()(dump_slack_data_tool(slack_client, slack_config))
    mcp.tool()(read_slack_data_tool(slack_client, slack_config))
    mcp.tool()(search_slack_data_tool(slack_client, slack_config))
    mcp.tool()(list_slack_channels_tool(slack_client, slack_config))
    mcp.tool()(list_slack_dumps_tool(slack_client, slack_config))
    mcp.tool()(extract_slack_todos_tool(slack_client, slack_config, gemini_config_dict))  # NEW: TODO extraction
    
    print("✅ Registered Slack connector with 6 tools")
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
        from connectors.gemini.tools.extract_all_todos_tool import extract_all_todos_tool
        
        # Create Gemini client and config
        from connectors.gemini.client import GeminiClient
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
    
        # Register Gemini tools
        mcp.tool()(analyze_jira_data_tool(gemini_client, gemini_config.get_config()))
        mcp.tool()(generate_email_summary_tool(gemini_client, gemini_config.get_config()))
        mcp.tool()(custom_ai_analysis_tool(gemini_client, gemini_config.get_config()))
        mcp.tool()(ai_summary_tool(gemini_client, gemini_config.get_config()))
        
        # NEW: Unified TODO extraction (requires individual tools to be registered first)
        # Will be registered after all connectors are initialized
        
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
        get_email_config_tool,
        send_team_daily_report_tool,
        extract_email_todos_tool
    )
    
    # Create Email client and config
    email_config = EmailConfig()
    email_client = EmailClient(email_config.get_config())
    
    # Register Email tools
    mcp.tool()(send_email_tool(email_client, email_config.get_config()))
    mcp.tool()(test_email_connection_tool(email_client, email_config.get_config()))
    mcp.tool()(get_email_config_tool(email_client, email_config.get_config()))
    mcp.tool()(send_team_daily_report_tool())  # GitHub Actions workflow wrapper
    mcp.tool()(extract_email_todos_tool(email_config, gemini_config_dict))  # NEW: TODO extraction
    
    print("✅ Registered Email connector with 5 tools")
except Exception as e:
    print(f"❌ Failed to register Email connector: {e}")

# Register unified TODO extraction tool (after all individual tools are registered)
try:
    # Get references to individual TODO extraction functions
    email_todos_func = extract_email_todos_tool(email_config, gemini_config_dict)
    jira_todos_func = extract_jira_todos_tool(jira_client, jira_config, gemini_config_dict)
    slack_todos_func = extract_slack_todos_tool(slack_client, slack_config, gemini_config_dict)
    
    # Register unified tool
    mcp.tool()(extract_all_todos_tool(email_todos_func, jira_todos_func, slack_todos_func))
    
    print("✅ Registered unified TODO extraction tool")
except Exception as e:
    print(f"⚠️  Failed to register unified TODO extraction tool: {e}")

# Built-in tool listing
@mcp.tool()
def list_available_tools() -> str:
    """List all available MCP tools"""
    return create_success_response({
        "message": "Work Planner MCP Server is running",
        "tools": [
            # Jira tools (9)
            "search_issues", "get_team_issues", "get_project_info", 
            "get_user_info", "list_teams", "list_organizations",
            "dump_jira_team_data", "read_jira_team_data", "extract_jira_todos",
            # Slack tools (6)
            "dump_slack_data", "read_slack_data", "search_slack_data",
            "list_slack_channels", "list_slack_dumps", "extract_slack_todos",
            # Gemini tools (4)
            "analyze_jira_data", "generate_email_summary", "custom_ai_analysis", "ai_summary",
            # Email tools (5)
            "send_email", "test_email_connection", "get_email_config", 
            "send_team_daily_report", "extract_email_todos",
            # Unified TODO tool (1)
            "extract_all_todos",
            # System tools (1)
            "list_available_tools"
        ],
        "total_tools": 26  # 9 Jira + 6 Slack + 4 Gemini + 5 Email + 1 Unified TODO + 1 System
    })

if __name__ == "__main__":
    mcp.run()