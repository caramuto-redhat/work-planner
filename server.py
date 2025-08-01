#!/usr/bin/env python

import os
import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from dotenv import load_dotenv
from jira import JIRA
from fastmcp import FastMCP

# ─── 1. Environment Setup ─────────────────────────────────────────────
# Load environment variables from multiple sources
load_dotenv()  # Load from .env file
load_dotenv(Path.home() / ".rh-jira-mcp-features-master-web.env")  # Load from home directory

JIRA_URL = os.getenv("JIRA_URL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not all([JIRA_URL, JIRA_API_TOKEN]):
    raise RuntimeError("Missing JIRA_URL or JIRA_API_TOKEN environment variables. Please check your .env file or ~/.rh-jira-mcp-features-master-web.env")

# ─── 2. Jira Client ─────────────────────────────────────────────────
try:
    jira_client = JIRA(server=JIRA_URL, token_auth=JIRA_API_TOKEN)
    # Test connection
    jira_client.projects()
except Exception as e:
    raise RuntimeError(f"Failed to connect to Jira: {str(e)}")

# Cache for user display names to reduce API calls
_user_display_cache = {}

# ─── 3. Configuration Loading ────────────────────────────────────────
def load_config() -> Dict[str, Any]:
    """Load simplified configuration with error handling."""
    try:
        with open("jira-config.yaml", 'r') as file:
            config = yaml.safe_load(file)
            
        # Validate required sections
        required_sections = ['teams', 'organizations']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required section: {section}")
                
        return config
    except FileNotFoundError:
        return {
            "teams": {
                "toolchain": {
                    "name": "ToolChain Team",
                    "project": "Automotive Feature Teams",
                    "assigned_team": "rhivos-ft-auto-toolchain",
                    "members": ["rhn-support-skalgudi", "rhn-support-ounsal", "mabanas@redhat.com"]
                }
            },
            "organizations": {
                "SP": ["rhn-support-skalgudi", "rhn-support-ounsal", "mabanas@redhat.com"]
            }
        }
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {str(e)}")

config = load_config()

# ─── 4. Core Query Functions ────────────────────────────────────────
def build_jql(project: str, status: str = "In Progress", assignees: List[str] = None, assigned_team: str = None) -> str:
    """Build JQL query with flexible filtering."""
    conditions = [f'project = "{project}"', f'statusCategory = "{status}"']
    
    if assignees:
        # Resolve display names to usernames for JQL
        resolved_assignees = []
        for assignee in assignees:
            username = resolve_display_name_to_username(assignee)
            resolved_assignees.append(username)
        
        assignee_list = ', '.join([f'"{a}"' for a in resolved_assignees])
        conditions.append(f'assignee in ({assignee_list})')
    
    if assigned_team:
        conditions.append(f'"AssignedTeam" = "{assigned_team}"')
    
    return ' AND '.join(conditions) + ' ORDER BY updatedDate DESC'

def resolve_display_name_to_username(display_name: str) -> str:
    """Resolve display name to username using reverse mapping."""
    if not display_name:
        return ""
        
    if "user_display_names" in config:
        # Create reverse mapping: display_name -> username
        reverse_mapping = {v: k for k, v in config["user_display_names"].items()}
        if display_name in reverse_mapping:
            return reverse_mapping[display_name]
    
    # If not found in reverse mapping, assume it's already a username
    return display_name

def get_display_name(username: str, jira_display_name: str) -> str:
    """Get custom display name from config or fall back to Jira's display name."""
    if not username:
        return "Unassigned"
    
    # Check cache first
    if username in _user_display_cache:
        return _user_display_cache[username]
        
    if "user_display_names" in config and username in config["user_display_names"]:
        display_name = config["user_display_names"][username]
    else:
        display_name = jira_display_name
    
    # Cache the result
    _user_display_cache[username] = display_name
    return display_name

def get_issues(jql: str, max_results: int = 20) -> List[Dict]:
    """Get issues with consistent formatting and error handling."""
    try:
        issues = jira_client.search_issues(jql, maxResults=max_results)
        
        result = []
        for issue in issues:
            try:
                # Get the original Jira display name
                jira_display_name = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                
                # Use custom display name if available, otherwise use Jira's
                if issue.fields.assignee:
                    display_name = get_display_name(issue.fields.assignee.name, jira_display_name)
                else:
                    display_name = "Unassigned"
                
                result.append({
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": display_name,
                    "assignee_username": issue.fields.assignee.name if issue.fields.assignee else None,
                    "created": issue.fields.created,
                    "updated": issue.fields.updated,
                    "issue_type": issue.fields.issuetype.name,
                    "priority": issue.fields.priority.name if issue.fields.priority else "Undefined"
                })
            except Exception as e:
                # Log individual issue processing errors but continue
                print(f"Warning: Failed to process issue {issue.key}: {str(e)}")
                continue
        
        return result
    except Exception as e:
        raise RuntimeError(f"Failed to fetch issues: {str(e)}")

# ─── 5. MCP Server ─────────────────────────────────────────────────
mcp = FastMCP()

def create_error_response(error_msg: str, details: str = None) -> str:
    """Create consistent error responses."""
    response = {"error": error_msg}
    if details:
        response["details"] = details
    return json.dumps(response, indent=2)

def create_success_response(data: Dict, message: str = None) -> str:
    """Create consistent success responses."""
    response = data.copy()
    if message:
        response["message"] = message
    return json.dumps(response, indent=2)

@mcp.tool()
def search_issues(jql: str, max_results: int = 20) -> str:
    """Search Jira issues using JQL query."""
    try:
        # Input validation
        if not jql or not jql.strip():
            return create_error_response("JQL query cannot be empty")
        
        if max_results < 1 or max_results > 100:
            return create_error_response("max_results must be between 1 and 100")
        
        issues = get_issues(jql, max_results)
        return create_success_response({
            "issues": issues,
            "count": len(issues),
            "jql": jql
        })
    except Exception as e:
        return create_error_response("Failed to search issues", str(e))

@mcp.tool()
def get_team_issues(team: str, status: str = "In Progress", organization: str = None) -> str:
    """Get issues for a specific team with optional organization filtering."""
    try:
        # Input validation
        if not team:
            return create_error_response("Team name cannot be empty")
        
        if team not in config["teams"]:
            return create_error_response(f"Team '{team}' not found")
        
        team_config = config["teams"][team]
        project = team_config["project"]
        assigned_team = team_config.get("assigned_team")
        
        # Determine assignees based on organization
        assignees = None
        if organization:
            if organization not in config["organizations"]:
                return create_error_response(f"Organization '{organization}' not found")
            assignees = config["organizations"][organization]
        
        # Build JQL
        jql = build_jql(project, status, assignees, assigned_team)
        
        # Get issues
        issues = get_issues(jql)
        
        return create_success_response({
            "team": team,
            "status": status,
            "organization": organization,
            "jql": jql,
            "issues": issues,
            "count": len(issues)
        })
        
    except Exception as e:
        return create_error_response("Failed to get team issues", str(e))

@mcp.tool()
def get_project_info(project_key: str) -> str:
    """Get basic project information."""
    try:
        if not project_key:
            return create_error_response("Project key cannot be empty")
            
        project = jira_client.project(project_key)
        return create_success_response({
            "key": project.key,
            "name": project.name,
            "description": project.description,
            "lead": project.lead.displayName if project.lead else None
        })
    except Exception as e:
        return create_error_response("Failed to get project info", str(e))

@mcp.tool()
def get_user_info(username: str) -> str:
    """Get user information."""
    try:
        if not username:
            return create_error_response("Username cannot be empty")
            
        user = jira_client.user(username)
        
        # Use custom display name if available, otherwise use Jira's
        display_name = get_display_name(user.name, user.displayName)
        
        return create_success_response({
            "username": user.name,
            "display_name": display_name,
            "jira_display_name": user.displayName,
            "email": user.emailAddress,
            "active": user.active
        })
    except Exception as e:
        return create_error_response("Failed to get user info", str(e))

@mcp.tool()
def list_teams() -> str:
    """List all configured teams."""
    try:
        teams = []
        for key, team in config["teams"].items():
            teams.append({
                "id": key,
                "name": team["name"],
                "project": team["project"],
                "member_count": len(team["members"])
            })
        
        return create_success_response({"teams": teams})
    except Exception as e:
        return create_error_response("Failed to list teams", str(e))

@mcp.tool()
def list_organizations() -> str:
    """List all configured organizations."""
    try:
        orgs = []
        for key, members in config["organizations"].items():
            orgs.append({
                "name": key,
                "member_count": len(members)
            })
        
        return create_success_response({"organizations": orgs})
    except Exception as e:
        return create_error_response("Failed to list organizations", str(e))

if __name__ == "__main__":
    mcp.run() 