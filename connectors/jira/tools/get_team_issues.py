"""
Get issues for a specific team with optional organization filtering
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_team_name


def get_team_issues_tool(client, config):
    """Create get_team_issues tool function"""
    
    def get_team_issues(team: str, status: str = "In Progress", organization: str = None) -> str:
        """Get issues for a specific team with optional organization filtering."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Resolve team alias to actual team ID
            resolved_team = client.resolve_team_alias(validated_team)
            
            if resolved_team not in config["teams"]:
                return create_error_response(f"Team '{team}' not found (resolved to '{resolved_team}')")
            
            team_config = config["teams"][resolved_team]
            project = team_config["project"]
            
            # Determine how to filter tickets
            assignees = None
            team_label = team_config.get("assigned_team")
            
            if organization:
                # Resolve organization alias to actual organization ID
                resolved_organization = client.resolve_organization_alias(organization)
                
                # If organization is specified, filter by organization members within the team
                if resolved_organization not in config["organizations"]:
                    return create_error_response(f"Organization '{organization}' not found (resolved to '{resolved_organization}')")
                
                # Get organization members (these are display names that need to be resolved to usernames)
                org_members = config["organizations"][resolved_organization]
                # Get team members (these are display names that need to be resolved to usernames)
                team_members = team_config.get("members", [])
                
                # Resolve both organization and team members to usernames
                resolved_org_members = []
                for member in org_members:
                    username = client.resolve_display_name_to_username(member)
                    if username:
                        resolved_org_members.append(username)
                
                resolved_team_members = []
                for member in team_members:
                    username = client.resolve_display_name_to_username(member)
                    if username:
                        resolved_team_members.append(username)
                
                # Filter resolved team members to only include those in the resolved organization
                assignees = [member for member in resolved_team_members if member in resolved_org_members]
                # Build JQL with assignee filter
                jql = client.build_jql(project, status, assignees)
            else:
                # Default to AssignedTeam filtering for all teams
                if team_label:
                    jql = f'project = "{project}" AND statusCategory = "{status}" AND "AssignedTeam" = "{team_label}" ORDER BY updatedDate DESC'
                else:
                    # Fallback to assignee filtering if no assigned_team is configured
                    team_members = team_config.get("members", [])
                    resolved_members = []
                    for member in team_members:
                        username = client.resolve_display_name_to_username(member)
                        if username:
                            resolved_members.append(username)
                    jql = client.build_jql(project, status, resolved_members)
            
            # Get issues
            issues = client.search_issues(jql)
            
            return create_success_response({
                "team": resolved_team,
                "original_team": team,
                "status": status,
                "organization": resolved_organization if organization else None,
                "original_organization": organization,
                "jql": jql,
                "issues": issues,
                "count": len(issues)
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to get team issues", str(e))
    
    return get_team_issues
