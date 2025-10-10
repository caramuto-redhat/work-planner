"""
Get issues for a specific team with optional organization filtering
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_team_name
from utils.sprint_helpers import filter_issues_by_latest_sprint


def get_team_issues_tool(client, config):
    """Create get_team_issues tool function"""
    
    # Get MCP query filters configuration
    mcp_filters = config.get("mcp_query_filters", {})
    default_status = mcp_filters.get("default_status")  # No hardcoded default
    all_statuses = mcp_filters.get("all_statuses", [])  # List of statuses to include
    order_by = mcp_filters.get("order_by", "updated DESC")
    max_results = mcp_filters.get("max_results", 20)  # Default to 20 if not configured
    additional_jql = mcp_filters.get("additional_jql", "")
    filter_to_latest_sprint = mcp_filters.get("filter_to_latest_sprint", False)
    
    def get_team_issues(team: str, status: str = None, organization: str = None) -> str:
        """Get issues for a specific team with optional organization filtering."""
        try:
            # Determine status filter to use
            status_filter = None
            if status is not None:
                # Explicit status provided by caller
                status_filter = status
            elif default_status is not None:
                # Use default_status from config
                status_filter = default_status
            elif all_statuses:
                # Use all_statuses from config (multiple statuses)
                status_filter = all_statuses  # Will be a list
            
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
                
                # Build JQL with assignee filter and status
                # Note: build_jql expects a single status or None, so we pass None if using list
                if isinstance(status_filter, list):
                    # Build JQL without status, then add multi-status filter
                    jql = client.build_jql(project, None, assignees)
                    jql = jql.replace(' ORDER BY updatedDate DESC', '')
                    status_list = '", "'.join(status_filter)
                    jql += f' AND status IN ("{status_list}")'
                else:
                    # Single status or None
                    jql = client.build_jql(project, status_filter, assignees)
                    jql = jql.replace(' ORDER BY updatedDate DESC', '')
                
                # Apply additional filters from mcp_query_filters
                if additional_jql:
                    jql += f' {additional_jql}'
                jql += f' ORDER BY {order_by}'
            else:
                # Default to AssignedTeam filtering for all teams
                if team_label:
                    # Build JQL with optional status filtering
                    jql = f'project = "{project}"'
                    
                    # Add status filter (single or multiple)
                    if isinstance(status_filter, list):
                        # Multiple statuses - use status field for custom status names
                        status_list = '", "'.join(status_filter)
                        jql += f' AND status IN ("{status_list}")'
                    elif status_filter:
                        # Single status - use statusCategory for categories like "In Progress"
                        jql += f' AND statusCategory = "{status_filter}"'
                    
                    jql += f' AND "AssignedTeam" = "{team_label}"'
                    # Add additional JQL filter if configured
                    if additional_jql:
                        jql += f' {additional_jql}'
                    jql += f' ORDER BY {order_by}'
                else:
                    # Fallback to assignee filtering if no assigned_team is configured
                    team_members = team_config.get("members", [])
                    resolved_members = []
                    for member in team_members:
                        username = client.resolve_display_name_to_username(member)
                        if username:
                            resolved_members.append(username)
                    
                    # Build JQL with assignee filter and status
                    if isinstance(status_filter, list):
                        # Build JQL without status, then add multi-status filter
                        jql = client.build_jql(project, None, resolved_members)
                        jql = jql.replace(' ORDER BY updatedDate DESC', '')
                        status_list = '", "'.join(status_filter)
                        jql += f' AND status IN ("{status_list}")'
                    else:
                        # Single status or None
                        jql = client.build_jql(project, status_filter, resolved_members)
                        jql = jql.replace(' ORDER BY updatedDate DESC', '')
                    
                    # Apply additional filters from mcp_query_filters
                    if additional_jql:
                        jql += f' {additional_jql}'
                    jql += f' ORDER BY {order_by}'
            
            # Get issues
            issues = client.search_issues(jql, max_results=max_results)
            
            # Apply latest sprint filter if enabled
            latest_sprint_num = None
            original_count = len(issues)
            if filter_to_latest_sprint and issues:
                issues, latest_sprint_num = filter_issues_by_latest_sprint(issues)
            
            return create_success_response({
                "team": resolved_team,
                "original_team": team,
                "status": status,
                "status_filter_applied": status_filter,
                "organization": resolved_organization if organization else None,
                "original_organization": organization,
                "jql": jql,
                "issues": issues,
                "count": len(issues),
                "original_count": original_count,
                "filtered_to_sprint": latest_sprint_num,
                "sprint_filter_applied": filter_to_latest_sprint
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to get team issues", str(e))
    
    return get_team_issues
