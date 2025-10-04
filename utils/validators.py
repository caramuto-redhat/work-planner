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
    """Validate and resolve team name input with fuzzy matching"""
    if not team or not team.strip():
        raise ValueError("Team name cannot be empty")
    
    team = team.strip().lower()
    
    # Known valid team names
    valid_teams = ["toolchain", "foa", "assessment", "boa", "sp-rhivos"]
    
    # Direct match
    if team in valid_teams:
        return team
    
    # Fuzzy matching for common variations
    fuzzy_matches = {
        "automotive": "toolchain",
        "toolchain automotive": "toolchain", 
        "toolchain-infra": "toolchain",
        "toolchain team": "toolchain",
        "follow-on-activities": "foa",
        "follow on activities": "foa",
        "boa team": "boa",
        "assessment team": "assessment",
        "sp rhivos": "sp-rhivos",
        "software platform rhivos": "sp-rhivos"
    }
    
    if team in fuzzy_matches:
        return fuzzy_matches[team]
    
    # If no exact match, raise error with suggestions
    suggestions = ", ".join(valid_teams)
    raise ValueError(f"Team '{team}' not found. Valid teams: {suggestions}")


def validate_channel_id(channel_id: str) -> str:
    """Validate Slack channel ID input"""
    if not channel_id or not channel_id.strip():
        raise ValueError("Channel ID cannot be empty")
    return channel_id.strip()
