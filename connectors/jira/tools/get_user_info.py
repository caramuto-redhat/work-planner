"""
Get user information
"""

from utils.responses import create_error_response, create_success_response


def get_user_info_tool(client, config):
    """Create get_user_info tool function"""
    
    def get_user_info(username: str) -> str:
        """Get user information."""
        try:
            if not username:
                return create_error_response("Username cannot be empty")
                
            user = client.client.user(username)
            
            # Use custom display name if available, otherwise use Jira's
            display_name = client._get_display_name(user.name)
            
            return create_success_response({
                "username": user.name,
                "display_name": display_name,
                "jira_display_name": user.displayName,
                "email": user.emailAddress,
                "active": user.active
            })
        except Exception as e:
            return create_error_response("Failed to get user info", str(e))
    
    return get_user_info
