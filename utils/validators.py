"""
Input validation utilities for MCP tools
"""


def validate_jql(jql: str) -> str:
    """Validate JQL query input"""
    if not jql or not jql.strip():
        raise ValueError("JQL query cannot be empty")
    return jql.strip()


def validate_max_results(max_results: int) -> int:
    """Validate max_results parameter"""
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results must be between 1 and 100")
    return max_results


def validate_team_name(team: str) -> str:
    """Validate team name input"""
    if not team or not team.strip():
        raise ValueError("Team name cannot be empty")
    return team.strip()


def validate_channel_id(channel_id: str) -> str:
    """Validate Slack channel ID input"""
    if not channel_id or not channel_id.strip():
        raise ValueError("Channel ID cannot be empty")
    return channel_id.strip()
