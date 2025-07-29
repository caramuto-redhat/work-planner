#!/usr/bin/env python

import os
import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv
from jira import JIRA
from fastmcp import FastMCP

# ─── 1. Environment Setup ─────────────────────────────────────────────
load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not all([JIRA_URL, JIRA_API_TOKEN]):
    raise RuntimeError("Missing JIRA_URL or JIRA_API_TOKEN environment variables")

# ─── 2. Jira Client ─────────────────────────────────────────────────
jira_client = JIRA(server=JIRA_URL, token_auth=JIRA_API_TOKEN)

# ─── 3. Simple Configuration ────────────────────────────────────────
def load_config() -> Dict[str, Any]:
    """Load simplified configuration."""
    try:
        with open("jira-config.yaml", 'r') as file:
            return yaml.safe_load(file)
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
    if "user_display_names" in config:
        # Create reverse mapping: display_name -> username
        reverse_mapping = {v: k for k, v in config["user_display_names"].items()}
        if display_name in reverse_mapping:
            return reverse_mapping[display_name]
    
    # If not found in reverse mapping, assume it's already a username
    return display_name

def get_display_name(username: str, jira_display_name: str) -> str:
    """Get custom display name from config or fall back to Jira's display name."""
    if "user_display_names" in config and username in config["user_display_names"]:
        return config["user_display_names"][username]
    return jira_display_name

def get_issues(jql: str, max_results: int = 20) -> List[Dict]:
    """Get issues with consistent formatting."""
    issues = jira_client.search_issues(jql, maxResults=max_results)
    
    result = []
    for issue in issues:
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
    
    return result

# ─── 5. MCP Server ─────────────────────────────────────────────────
mcp = FastMCP()

@mcp.tool()
def search_issues(jql: str, max_results: int = 20) -> str:
    """Search Jira issues using JQL query."""
    try:
        issues = get_issues(jql, max_results)
        return json.dumps({"issues": issues, "count": len(issues)}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
def get_team_issues(team: str, status: str = "In Progress", organization: str = None) -> str:
    """Get issues for a specific team with optional organization filtering."""
    try:
        if team not in config["teams"]:
            return json.dumps({"error": f"Team '{team}' not found"}, indent=2)
        
        team_config = config["teams"][team]
        project = team_config["project"]
        assigned_team = team_config.get("assigned_team")
        
        # Determine assignees based on organization
        assignees = None
        if organization:
            if organization in config["organizations"]:
                assignees = config["organizations"][organization]
            else:
                return json.dumps({"error": f"Organization '{organization}' not found"}, indent=2)
        
        # Build JQL
        jql = build_jql(project, status, assignees, assigned_team)
        
        # Get issues
        issues = get_issues(jql)
        
        return json.dumps({
            "team": team,
            "status": status,
            "organization": organization,
            "jql": jql,
            "issues": issues,
            "count": len(issues)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
def get_project_info(project_key: str) -> str:
    """Get basic project information."""
    try:
        project = jira_client.project(project_key)
        return json.dumps({
            "key": project.key,
            "name": project.name,
            "description": project.description,
            "lead": project.lead.displayName if project.lead else None
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
def get_user_info(username: str) -> str:
    """Get user information."""
    try:
        user = jira_client.user(username)
        
        # Use custom display name if available, otherwise use Jira's
        display_name = get_display_name(user.name, user.displayName)
        
        return json.dumps({
            "username": user.name,
            "display_name": display_name,
            "jira_display_name": user.displayName,
            "email": user.emailAddress,
            "active": user.active
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
def list_teams() -> str:
    """List all configured teams."""
    teams = []
    for key, team in config["teams"].items():
        teams.append({
            "id": key,
            "name": team["name"],
            "project": team["project"],
            "member_count": len(team["members"])
        })
    
    return json.dumps({"teams": teams}, indent=2)

@mcp.tool()
def list_organizations() -> str:
    """List all configured organizations."""
    orgs = []
    for key, members in config["organizations"].items():
        orgs.append({
            "name": key,
            "member_count": len(members)
        })
    
    return json.dumps({"organizations": orgs}, indent=2)

if __name__ == "__main__":
    mcp.run() 