"""
List all configured organizations
"""

from utils.responses import create_error_response, create_success_response


def list_organizations_tool(client, config):
    """Create list_organizations tool function"""
    
    def list_organizations() -> str:
        """List all configured organizations."""
        try:
            orgs = []
            for key, members in config["organizations"].items():
                # Show both usernames and their display names for better understanding
                resolved_members = []
                for member in members:
                    # Find the display name for this username
                    display_name = None
                    if "user_display_names" in config:
                        display_name = config["user_display_names"].get(member, member)
                    
                    resolved_members.append({
                        "username": member,
                        "display_name": display_name
                    })
                
                orgs.append({
                    "name": key,
                    "member_count": len(members),
                    "members": resolved_members
                })
            
            return create_success_response({"organizations": orgs})
        except Exception as e:
            return create_error_response("Failed to list organizations", str(e))
    
    return list_organizations
