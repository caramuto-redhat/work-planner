#!/usr/bin/env python

import os
import yaml
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional, Any
from jinja2 import Template

from dotenv import load_dotenv
from jira import JIRA
from fastmcp import FastMCP
from fastapi import HTTPException

# AI Provider imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ─── 1. Load environment variables ─────────────────────────────────────────────
load_dotenv()

JIRA_URL       = os.getenv("JIRA_URL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

# Optional AI and Email environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")

if not all([JIRA_URL, JIRA_API_TOKEN]):
    raise RuntimeError("Missing JIRA_URL or JIRA_API_TOKEN environment variables")

# Initialize AI providers
ai_clients = {}
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_clients['gemini'] = genai.GenerativeModel('gemini-1.5-flash')

if OPENAI_AVAILABLE and OPENAI_API_KEY:
    ai_clients['openai'] = OpenAI(api_key=OPENAI_API_KEY)

# ─── 2. Create a Jira client ───────────────────────────────────────────────────
#    Uses token_auth (API token) for authentication.
jira_client = JIRA(server=JIRA_URL, token_auth=JIRA_API_TOKEN)

# ─── 3. Load team configuration ────────────────────────────────────────────────
def load_team_config(config_path: str = "jira-config.yaml") -> Dict[str, Any]:
    """Load team configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        return {
            "team_configs": {},
            "jira_users": {},
            "settings": {
                "project_name": "Default Project",
                "update_grace_days": 10,
                "current_period": "weekly",
                "ai_provider": "gemini",
                "enable_ai_summary": True
            }
        }

# Global config (loaded once)
team_config = load_team_config()

# ─── 4. Team reporting utility functions ──────────────────────────────────────
def generate_jql_query(team_id: str, query_type: str = "in_progress") -> str:
    """Generate JQL query for a specific team and query type."""
    config = team_config
    if team_id not in config["team_configs"]:
        raise ValueError(f"Team {team_id} not found in configuration")
    
    team = config["team_configs"][team_id]
    settings = config["settings"]
    period_config = config.get("period_configs", {}).get(settings["current_period"], {"days": 7})
    
    # Format assignees for JQL
    assignees = ", ".join([f'"{assignee}"' for assignee in team["assignees"]])
    
    # Get JQL template
    jql_templates = config.get("jql_templates", {})
    
    if query_type == "in_progress":
        template = jql_templates.get("in_progress", 'project = "{project_name}" AND assignee in ({team_assignees}) AND statusCategory = "In Progress"')
    elif query_type == "todo":
        template = jql_templates.get("todo", 'project = "{project_name}" AND assignee in ({team_assignees}) AND statusCategory = "To Do"')
    elif query_type == "recently_closed":
        template = jql_templates.get("recently_closed", 'project = "{project_name}" AND assignee in ({team_assignees}) AND statusCategory = "Done" AND resolutiondate >= -{period_days}d')
    else:
        template = jql_templates.get("base_query", 'project = "{project_name}" AND assignee in ({team_assignees})')
    
    # Format the template
    return template.format(
        project_name=settings["project_name"],
        team_assignees=assignees,
        period_days=period_config["days"]
    )

def get_ai_summary(prompt: str, data: str, ai_provider: str = "gemini") -> str:
    """Generate AI summary using specified provider."""
    if ai_provider not in ai_clients:
        return f"AI provider '{ai_provider}' not available. Raw data:\n{data}"
    
    try:
        full_prompt = f"{prompt}\n\nData:\n{data}"
        
        if ai_provider == "gemini":
            response = ai_clients["gemini"].generate_content(full_prompt)
            return response.text
        elif ai_provider == "openai":
            response = ai_clients["openai"].chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates detailed Jira project reports."},
                    {"role": "user", "content": full_prompt}
                ]
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"AI summarization failed: {e}\n\nRaw data:\n{data}"

def filter_comments(issue: Any, exclude_authors: List[str]) -> List[Dict[str, Any]]:
    """Filter out comments from bot/automation accounts."""
    if not hasattr(issue.fields, 'comment') or not issue.fields.comment:
        return []
    
    filtered_comments = []
    for comment in issue.fields.comment.comments:
        author_name = comment.author.displayName.lower() if hasattr(comment.author, 'displayName') else ""
        if not any(excluded in author_name for excluded in exclude_authors):
            filtered_comments.append({
                "author": comment.author.displayName if hasattr(comment.author, 'displayName') else "Unknown",
                "created": comment.created,
                "body": comment.body
            })
    
    return filtered_comments

def send_email(to_emails: List[str], subject: str, html_content: str, text_content: str = "") -> bool:
    """Send email via SMTP."""
    if not all([EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM]):
        print("Email credentials not configured")
        return False
    
    try:
        msg = MimeMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = ', '.join(to_emails)
        
        if text_content:
            text_part = MimeText(text_content, 'plain')
            msg.attach(text_part)
        
        html_part = MimeText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        smtp_settings = team_config.get("email_settings", {})
        server = smtplib.SMTP(
            smtp_settings.get("smtp_server", "smtp.gmail.com"),
            smtp_settings.get("smtp_port", 587)
        )
        
        if smtp_settings.get("use_tls", True):
            server.starttls()
        
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# ─── 5. Instantiate the MCP server ─────────────────────────────────────────────
mcp = FastMCP("Jira Context Server")

# ─── 4. Register the get_jira tool ─────────────────────────────────────────────
@mcp.tool()
def get_jira(issue_key: str) -> str:
    """
    Fetch the Jira issue identified by 'issue_key' using jira_client,
    then return a Markdown string: "# ISSUE-KEY: summary\n\ndescription"
    """
    try:
        issue = jira_client.issue(issue_key)
    except Exception as e:
        # If the JIRA client raises an error (e.g. issue not found),
        # wrap it in an HTTPException so MCP/Client sees a 4xx/5xx.
        raise HTTPException(status_code=404, detail=f"Failed to fetch Jira issue {issue_key}: {e}")

    # Extract summary & description fields
    summary     = issue.fields.summary or ""
    description = issue.fields.description or ""

    return f"# {issue_key}: {summary}\n\n{description}"

def to_markdown(obj):
    if isinstance(obj, dict):
        return '```json\n' + json.dumps(obj, indent=2) + '\n```'
    elif hasattr(obj, 'raw'):
        return '```json\n' + json.dumps(obj.raw, indent=2) + '\n```'
    elif isinstance(obj, list):
        return '\n'.join([to_markdown(o) for o in obj])
    else:
        return str(obj)

@mcp.tool()
def search_issues(jql: str, max_results: int = 10) -> str:
    """Search issues using JQL."""
    try:
        issues = jira_client.search_issues(jql, maxResults=max_results)
        return to_markdown([i.raw for i in issues])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JQL search failed: {e}")

@mcp.tool()
def search_users(query: str, max_results: int = 10) -> str:
    """Search users by query."""
    try:
        users = jira_client.search_users(query, maxResults=max_results)
        return to_markdown([u.raw for u in users])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to search users: {e}")

@mcp.tool()
def list_projects() -> str:
    """List all projects."""
    try:
        projects = jira_client.projects()
        return to_markdown([p.raw for p in projects])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {e}")

@mcp.tool()
def get_project(project_key: str) -> str:
    """Get a project by key."""
    try:
        project = jira_client.project(project_key)
        return to_markdown(project)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch project: {e}")

@mcp.tool()
def get_project_components(project_key: str) -> str:
    """Get components for a project."""
    try:
        components = jira_client.project_components(project_key)
        return to_markdown([c.raw for c in components])
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch components: {e}")

@mcp.tool()
def get_project_versions(project_key: str) -> str:
    """Get versions for a project."""
    try:
        versions = jira_client.project_versions(project_key)
        return to_markdown([v.raw for v in versions])
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch versions: {e}")

@mcp.tool()
def get_project_roles(project_key: str) -> str:
    """Get roles for a project."""
    try:
        roles = jira_client.project_roles(project_key)
        return to_markdown(roles)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch roles: {e}")

@mcp.tool()
def get_project_permission_scheme(project_key: str) -> str:
    """Get permission scheme for a project."""
    try:
        scheme = jira_client.project_permissionscheme(project_key)
        return to_markdown(scheme.raw)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch permission scheme: {e}")

@mcp.tool()
def get_project_issue_types(project_key: str) -> str:
    """Get issue types for a project."""
    try:
        types = jira_client.project_issue_types(project_key)
        return to_markdown([t.raw for t in types])
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch issue types: {e}")

@mcp.tool()
def get_current_user() -> str:
    """Get current user info."""
    try:
        user = jira_client.myself()
        return to_markdown(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch current user: {e}")

@mcp.tool()
def get_user(account_id: str) -> str:
    """Get user by account ID."""
    try:
        user = jira_client.user(account_id)
        return to_markdown(user.raw)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch user: {e}")

@mcp.tool()
def get_assignable_users_for_project(project_key: str, query: str = "", max_results: int = 10) -> str:
    """Get assignable users for a project."""
    try:
        users = jira_client.search_assignable_users_for_projects(query, project_key, maxResults=max_results)
        return to_markdown([u.raw for u in users])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get assignable users: {e}")

@mcp.tool()
def get_assignable_users_for_issue(issue_key: str, query: str = "", max_results: int = 10) -> str:
    """Get assignable users for an issue."""
    try:
        users = jira_client.search_assignable_users_for_issues(query, issueKey=issue_key, maxResults=max_results)
        return to_markdown([u.raw for u in users])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get assignable users: {e}")

@mcp.tool()
def list_boards(max_results: int = 10) -> str:
    """List boards."""
    try:
        boards = jira_client.boards(maxResults=max_results)
        return to_markdown([b.raw for b in boards])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch boards: {e}")

@mcp.tool()
def get_board(board_id: int) -> str:
    """Get board by ID."""
    try:
        board = jira_client.board(board_id)
        return to_markdown(board.raw)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch board: {e}")

@mcp.tool()
def list_sprints(board_id: int, max_results: int = 10) -> str:
    """List sprints for a board."""
    try:
        sprints = jira_client.sprints(board_id, maxResults=max_results)
        return to_markdown([s.raw for s in sprints])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sprints: {e}")

@mcp.tool()
def get_sprint(sprint_id: int) -> str:
    """Get sprint by ID."""
    try:
        sprint = jira_client.sprint(sprint_id)
        return to_markdown(sprint.raw)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Failed to fetch sprint: {e}")

@mcp.tool()
def get_issues_for_board(board_id: int, max_results: int = 10) -> str:
    """Get issues for a board."""
    try:
        issues = jira_client.get_issues_for_board(board_id, maxResults=max_results)
        return to_markdown([i.raw for i in issues])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch issues for board: {e}")

@mcp.tool()
def get_issues_for_sprint(board_id: int, sprint_id: int, max_results: int = 10) -> str:
    """Get issues for a sprint in a board."""
    try:
        issues = jira_client.get_all_issues_for_sprint_in_board(board_id, sprint_id, maxResults=max_results)
        return to_markdown([i.raw for i in issues])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch issues for sprint: {e}")

# ─── 6. Team Reporting MCP Tools ──────────────────────────────────────────────
@mcp.tool()
def get_team_config() -> str:
    """Get the current team configuration."""
    try:
        return to_markdown(team_config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team config: {e}")

@mcp.tool()
def list_teams() -> str:
    """List all configured teams."""
    try:
        teams = {}
        for team_id, team_data in team_config.get("team_configs", {}).items():
            teams[team_id] = {
                "name": team_data.get("name", "Unknown"),
                "focus": team_data.get("focus", ""),
                "assignees": team_data.get("assignees", [])
            }
        return to_markdown(teams)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list teams: {e}")

@mcp.tool()
def generate_team_jql(team_id: str, query_type: str = "in_progress") -> str:
    """Generate JQL query for a specific team and query type."""
    try:
        jql = generate_jql_query(team_id, query_type)
        return f"Generated JQL for team {team_id} ({query_type}):\n\n```jql\n{jql}\n```"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate JQL: {e}")

@mcp.tool()
def get_team_issues(team_id: str, query_type: str = "in_progress", include_comments: bool = True) -> str:
    """Get issues for a specific team with optional AI summarization."""
    try:
        if team_id not in team_config["team_configs"]:
            raise ValueError(f"Team {team_id} not found")
        
        # Generate and execute JQL query
        jql = generate_jql_query(team_id, query_type)
        max_results = team_config.get("settings", {}).get("max_results_per_query", 100)
        issues = jira_client.search_issues(jql, maxResults=max_results, expand="comments")
        
        # Process issues with enhanced data
        enhanced_issues = []
        exclude_authors = team_config.get("settings", {}).get("exclude_comment_authors", [])
        
        for issue in issues:
            issue_data = {
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "created": issue.fields.created,
                "updated": issue.fields.updated,
                "description": issue.fields.description or "",
                "issue_type": issue.fields.issuetype.name,
                "priority": issue.fields.priority.name if issue.fields.priority else "None"
            }
            
            if include_comments:
                issue_data["comments"] = filter_comments(issue, exclude_authors)
            
            enhanced_issues.append(issue_data)
        
        return to_markdown({
            "team_id": team_id,
            "team_name": team_config["team_configs"][team_id].get("name", "Unknown"),
            "query_type": query_type,
            "jql_used": jql,
            "issue_count": len(enhanced_issues),
            "issues": enhanced_issues
        })
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get team issues: {e}")

@mcp.tool()
def generate_team_report(team_id: str, include_ai_summary: bool = True, send_email: bool = False) -> str:
    """Generate a comprehensive team report with optional AI analysis and email delivery."""
    try:
        if team_id not in team_config["team_configs"]:
            raise ValueError(f"Team {team_id} not found")
        
        team = team_config["team_configs"][team_id]
        settings = team_config["settings"]
        
        # Get all issue types for the team
        in_progress_issues = jira_client.search_issues(
            generate_jql_query(team_id, "in_progress"), 
            maxResults=settings.get("max_results_per_query", 100),
            expand="comments"
        )
        
        todo_issues = jira_client.search_issues(
            generate_jql_query(team_id, "todo"),
            maxResults=settings.get("max_results_per_query", 100),
            expand="comments"
        )
        
        closed_issues = jira_client.search_issues(
            generate_jql_query(team_id, "recently_closed"),
            maxResults=settings.get("max_results_per_query", 100),
            expand="comments"
        )
        
        # Prepare report data
        current_date = datetime.now().strftime("%Y-%m-%d")
        period_config = team_config.get("period_configs", {}).get(settings["current_period"], {"title": "Weekly", "description": "Weekly status update"})
        
        report_data = {
            "team_name": team["name"],
            "team_id": team_id,
            "report_date": current_date,
            "period": period_config["title"],
            "focus": team.get("focus", ""),
            "assignees": team["assignees"],
            "summary": {
                "in_progress_count": len(in_progress_issues),
                "todo_count": len(todo_issues),
                "closed_count": len(closed_issues)
            },
            "in_progress_issues": [
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                    "status": issue.fields.status.name,
                    "updated": issue.fields.updated,
                    "comments": filter_comments(issue, settings.get("exclude_comment_authors", []))
                } for issue in in_progress_issues
            ],
            "todo_issues": [
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                    "priority": issue.fields.priority.name if issue.fields.priority else "None"
                } for issue in todo_issues
            ],
            "closed_issues": [
                {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                    "resolution_date": issue.fields.resolutiondate
                } for issue in closed_issues
            ]
        }
        
        # Generate AI summary if enabled and available
        ai_summary = ""
        if include_ai_summary and settings.get("enable_ai_summary", False):
            ai_provider = settings.get("ai_provider", "gemini")
            ai_prompts = team_config.get("ai_prompts", {})
            team_report_prompt = ai_prompts.get("team_report", "Generate a team status report summary.")
            
            ai_summary = get_ai_summary(
                team_report_prompt.format(
                    team_name=team["name"],
                    period=period_config["title"],
                    grace_days=settings.get("update_grace_days", 10)
                ),
                json.dumps(report_data, indent=2, default=str),
                ai_provider
            )
            report_data["ai_summary"] = ai_summary
        
        # Generate HTML report
        html_template = Template("""
        <html>
        <head><title>{{ team_name }} {{ period }} Status Report</title></head>
        <body>
            <h1>{{ team_name }} {{ period }} Status Report - {{ report_date }}</h1>
            
            <h2>Team Focus</h2>
            <p>{{ focus }}</p>
            
            <h2>Summary</h2>
            <ul>
                <li>In Progress: {{ summary.in_progress_count }} issues</li>
                <li>To Do: {{ summary.todo_count }} issues</li>
                <li>Recently Closed: {{ summary.closed_count }} issues</li>
            </ul>
            
            {% if ai_summary %}
            <h2>AI Analysis</h2>
            <div>{{ ai_summary | safe }}</div>
            {% endif %}
            
            <h2>Current Work (In Progress)</h2>
            {% for issue in in_progress_issues %}
            <h3><a href="{{ jira_url }}/browse/{{ issue.key }}">{{ issue.key }}: {{ issue.summary }}</a></h3>
            <p><strong>Assignee:</strong> {{ issue.assignee }} | <strong>Status:</strong> {{ issue.status }}</p>
            {% endfor %}
            
            <h2>Upcoming Work (To Do)</h2>
            {% for issue in todo_issues %}
            <h3><a href="{{ jira_url }}/browse/{{ issue.key }}">{{ issue.key }}: {{ issue.summary }}</a></h3>
            <p><strong>Assignee:</strong> {{ issue.assignee }} | <strong>Priority:</strong> {{ issue.priority }}</p>
            {% endfor %}
            
            <h2>Recently Completed</h2>
            {% for issue in closed_issues %}
            <h3><a href="{{ jira_url }}/browse/{{ issue.key }}">{{ issue.key }}: {{ issue.summary }}</a></h3>
            <p><strong>Assignee:</strong> {{ issue.assignee }} | <strong>Completed:</strong> {{ issue.resolution_date }}</p>
            {% endfor %}
        </body>
        </html>
        """)
        
        html_report = html_template.render(
            jira_url=JIRA_URL,
            **report_data
        )
        
        report_data["html_report"] = html_report
        
        # Send email if requested
        if send_email and team.get("email", {}).get("recipients"):
            email_config = team["email"]
            subject = email_config["subject"].format(
                period_title=period_config["title"],
                date=current_date
            )
            
            email_sent = send_email(
                email_config["recipients"],
                subject,
                html_report
            )
            report_data["email_sent"] = email_sent
        
        return to_markdown(report_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate team report: {e}")

@mcp.tool()
def send_team_report_email(team_id: str, report_data: str) -> str:
    """Send a team report via email using the team's email configuration."""
    try:
        if team_id not in team_config["team_configs"]:
            raise ValueError(f"Team {team_id} not found")
        
        team = team_config["team_configs"][team_id]
        email_config = team.get("email", {})
        
        if not email_config.get("recipients"):
            return "No email recipients configured for this team"
        
        # Parse report data if it's JSON string
        if isinstance(report_data, str):
            try:
                parsed_data = json.loads(report_data)
                html_content = parsed_data.get("html_report", report_data)
            except:
                html_content = report_data
        else:
            html_content = str(report_data)
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        period_config = team_config.get("period_configs", {}).get(
            team_config["settings"]["current_period"], 
            {"title": "Weekly"}
        )
        
        subject = email_config["subject"].format(
            period_title=period_config["title"],
            date=current_date
        )
        
        success = send_email(email_config["recipients"], subject, html_content)
        
        return f"Email {'sent successfully' if success else 'failed to send'} to {', '.join(email_config['recipients'])}"
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")

# ─── 7. Run the HTTP-based MCP server on port 8000 ───────────────────────────────
if __name__ == "__main__":
    mcp.run()
