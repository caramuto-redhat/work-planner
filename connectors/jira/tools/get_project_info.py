"""
Get basic project information
"""

from utils.responses import create_error_response, create_success_response


def get_project_info_tool(client, config):
    """Create get_project_info tool function"""
    
    def get_project_info(project_key: str) -> str:
        """Get basic project information."""
        try:
            if not project_key:
                return create_error_response("Project key cannot be empty")
                
            project = client.client.project(project_key)
            return create_success_response({
                "key": project.key,
                "name": project.name,
                "description": project.description,
                "lead": project.lead.displayName if project.lead else None
            })
        except Exception as e:
            return create_error_response("Failed to get project info", str(e))
    
    return get_project_info
