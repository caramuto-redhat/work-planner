"""
List all configured teams
"""

from utils.responses import create_error_response, create_success_response


def list_teams_tool(client, config):
    """Create list_teams tool function"""
    
    def list_teams() -> str:
        """List all configured teams."""
        try:
            teams = []
            for key, team in config["teams"].items():
                # Resolve display names to usernames for better understanding
                resolved_members = []
                for member in team.get("members", []):
                    username = client.resolve_display_name_to_username(member)
                    resolved_members.append({
                        "display_name": member,
                        "username": username
                    })
                
                teams.append({
                    "id": key,
                    "name": team["name"],
                    "project": team["project"],
                    "member_count": len(team["members"]),
                    "members": resolved_members
                })
            
            return create_success_response({"teams": teams})
        except Exception as e:
            return create_error_response("Failed to list teams", str(e))
    
    return list_teams
