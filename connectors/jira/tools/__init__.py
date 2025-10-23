"""
Jira tools registration
"""

from .search_issues import search_issues_tool
from .get_team_issues import get_team_issues_tool
from .get_project_info import get_project_info_tool
from .get_user_info import get_user_info_tool
from .list_teams import list_teams_tool
from .list_organizations import list_organizations_tool
from .jira_data_collection import dump_jira_team_data_tool, read_jira_team_data_tool
from .jira_report_tool import register_jira_report_tool
from .extract_jira_todos import extract_jira_todos_tool


def get_jira_tools(client, config, gemini_config=None):
    """Return all Jira tools"""
    tools = [
        search_issues_tool(client, config),
        get_team_issues_tool(client, config),
        get_project_info_tool(client, config),
        get_user_info_tool(client, config),
        list_teams_tool(client, config),
        list_organizations_tool(client, config),
        dump_jira_team_data_tool(client, config),
        read_jira_team_data_tool(client, config),
    ]
    
    # Add TODO extraction tool if gemini_config is provided
    if gemini_config:
        tools.append(extract_jira_todos_tool(client, config, gemini_config))
    
    return tools


def register_jira_report_tools(mcp):
    """Register Jira report tools"""
    register_jira_report_tool(mcp)
