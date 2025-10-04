"""
Jira Data Collection Tools
Functions for collecting and storing Jira data for AI analysis
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_team_name
from ..client import JiraClient
from ..config import JiraConfig
import os
import json
import yaml
from datetime import datetime
from typing import Dict, Any, List

def dump_jira_team_data_tool(client, config):
    """Create dump_jira_team_data tool function"""
    
    def dump_jira_team_data(team: str, tickets_filter: str = "All In Progress") -> str:
        """Dump Jira issues data for a specific team."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Initialize Jira client
            jira_config = JiraConfig.load("config/jira.yaml")
            jira_client = JiraClient(jira_config)
            
            # Build JQL query based on team and filter
            jql_query = _build_jql_query(validated_team, tickets_filter)
            
            # Get issues from Jira
            issues = jira_client.search_issues(jql_query)
            
            if not issues:
                return create_success_response({
                    "team": validated_team,
                    "filter": tickets_filter,
                    "issues_found": 0,
                    "message": f"No issues found for team '{validated_team}' with filter '{tickets_filter}'"
                })
            
            # Create dump directory
            dump_dir = config.get("data_collection", {}).get("dump_directory", "jira_dumps")
            if not os.path.exists(dump_dir):
                os.makedirs(dump_dir, exist_ok=True)
            
            # Generate filename
            filename = f"{validated_team}_{tickets_filter.lower().replace(' ', '_')}_jira_dump.txt"
            filepath = os.path.join(dump_dir, filename)
            
            # Write issues to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Jira Team Data Dump\n")
                f.write(f"# Team: {validated_team}\n")
                f.write(f"# Filter: {tickets_filter}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Total Issues: {len(issues)}\n")
                f.write(f"# JQL Query: {jql_query}\n\n")
                
                for issue in issues:
                    _write_issue_details(f, issue)
            
            # Also create JSON format for structured data access
            json_filename = f"{validated_team}_{tickets_filter.lower().replace(' ', '_')}_jira_dump.json"
            json_filepath = os.path.join(dump_dir, json_filename)
            
            issues_data = []
            for issue in issues:
                issue_data = _extract_issue_data(issue)
                issues_data.append(issue_data)
            
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "team": validated_team,
                    "filter": tickets_filter,
                    "generated": datetime.now().isoformat(),
                    "total_issues": len(issues),
                    "jql_query": jql_query,
                    "issues": issues_data
                }, f, indent=2, ensure_ascii=False)
            
            return create_success_response({
                "team": validated_team,
                "filter": tickets_filter,
                "issues_found": len( issues),
                "file_path": filepath,
                "filename": filename,
                "json_file_path": json_filepath,
                "json_filename": json_filename,
                "jql_query": jql_query
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to dump Jira team data", str(e))
    
    return dump_jira_team_data


def _build_jql_query(team: str, tickets_filter: str) -> str:
    """Build JQL query based on team and filter"""
    # Base query for automotive project
    base_jql = 'project = "Automotive Feature Teams"'
    
    # Add status filter
    if "in progress" in tickets_filter.lower():
        status_filter = 'statusCategory = "In Progress"'
    elif "completed" in tickets_filter.lower():
        status_filter = 'statusCategory = "Done"'
    elif "blocked" in tickets_filter.lower():
        status_filter = 'status = "Blocked"'
    else:
        # Default to all status
        status_filter = 'statusCategory IN ("To Do", "In Progress", "Done")'
    
    # Map team names to their actual AssignedTeam field values
    team_mapping = {
        "toolchain": "rhivos-pdr-auto-toolchain",
        "foa": "rhivos-pdr-auto-foa", 
        "assessment": "rhivos-pdr-auto-assessment",
        "boa": "rhivos-pdr-auto-boa"
    }
    
    # Get the actual team identifier
    assigned_team = team_mapping.get(team, f"{team}-team")
    team_filter = f'AND "AssignedTeam" = "{assigned_team}"'
    
    return f"{base_jql} AND {status_filter} {team_filter} ORDER BY updatedDate DESC"


def _write_issue_details(file, issue):
    """Write detailed issue information to file"""
    try:
        # Extract key fields
        key = getattr(issue, 'key', 'UNKNOWN')
        summary = getattr(issue.fields, 'summary', 'No summary')
        status = getattr(issue.fields.status, 'name', 'Unknown')
        assignee = getattr(issue.fields.assignee, 'displayName', 'Unassigned') if issue.fields.assignee else 'Unassigned'
        reporter = getattr(issue.fields.reporter, 'displayName', 'Unknown') if issue.fields.reporter else 'Unknown'
        created = getattr(issue.fields, 'created', 'Unknown')
        updated = getattr(issue.fields, 'updated', 'Unknown')
        priority = getattr(issue.fields.priority, 'name', 'Unknown')
        issue_type = getattr(issue.fields.issuetype, 'name', 'Unknown')
        
        # Description
        description = getattr(issue.fields, 'description', 'No description')
        if description:
            # Clean up description text
            description = description.replace('\n', ' ').strip()
            if len(description) > 500:
                description = description[:500] + "..."
        else:
            description = 'No description'
        
        file.write(f"================================================================================\n")
        file.write(f"Issue: {key}\n")
        file.write(f"Title: {summary}\n")
        file.write(f"Type: {issue_type}\n")
        file.write(f"Status: {status}\n")
        file.write(f"Priority: {priority}\n")
        file.write(f"Assignee: {assignee}\n")
        file.write(f"Reporter: {reporter}\n")
        file.write(f"Created: {created}\n")
        file.write(f"Updated: {updated}\n")
        file.write(f"Description: {description}\n")
        file.write(f"\n")
        
    except Exception as e:
        file.write(f"Error processing issue: {str(e)}\n")
        file.write(f"================================================================================\n\n")


def _extract_issue_data(issue) -> Dict[str, Any]:
    """Extract structured issue data for JSON storage"""
    try:
        # Handle both dictionary and object formats
        if isinstance(issue, dict):
            key = issue.get('key', 'UNKNOWN')
            fields = issue.get('fields', {})
            summary = fields.get('summary', 'No summary')
            status_obj = fields.get('status', {})
            status = status_obj.get('name', 'Unknown') if isinstance(status_obj, dict) else getattr(status_obj, 'name', 'Unknown')
            priority_obj = fields.get('priority', {})
            priority = priority_obj.get('name', 'Unknown') if isinstance(priority_obj, dict) else getattr(priority_obj, 'name', 'Unknown')
            issue_type_obj = fields.get('issuetype', {})
            issue_type = issue_type_obj.get('name', 'Unknown') if isinstance(issue_type_obj, dict) else getattr(issue_type_obj, 'name', 'Unknown')
            
            # Handle assignees and reporters
            assignee_obj = fields.get('assignee', None)
            assignee = None
            if assignee_obj:
                if isinstance(assignee_obj, dict):
                    assignee = {
                        "name": assignee_obj.get('displayName', 'Unknown'),
                        "email": assignee_obj.get('emailAddress', 'Unknown')
                    }
                else:
                    assignee = {
                        "name": getattr(assignee_obj, 'displayName', 'Unknown'),
                        "email": getattr(assignee_obj, 'emailAddress', 'Unknown')
                    }
            
            reporter_obj = fields.get('reporter', None)
            reporter = None
            if reporter_obj:
                if isinstance(reporter_obj, dict):
                    reporter = {
                        "name": reporter_obj.get('displayName', 'Unknown'),
                        "email": reporter_obj.get('emailAddress', 'Unknown')
                    }
                else:
                    reporter = {
                        "name": getattr(reporter_obj, 'displayName', 'Unknown'),
                        "email": getattr(reporter_obj, 'emailAddress', 'Unknown')
                    }
            
            # Description
            description = fields.get('description', '')
            if description:
                description = description.replace('\n', ' ').strip()
            
            # Timestamps
            created = fields.get('created', '')
            updated = fields.get('updated', '')
        
        else:
            # Handle old object format
            key = getattr(issue, 'key', 'UNKNOWN')
            fields_obj = getattr(issue, 'fields', None)
            summary = getattr(fields_obj, 'summary', 'No summary') if fields_obj else 'No summary'
            status_obj = getattr(fields_obj, 'status', None) if fields_obj else None
            status = getattr(status_obj, 'name', 'Unknown') if status_obj else 'Unknown'
            priority_obj = getattr(fields_obj, 'priority', None) if fields_obj else None
            priority = getattr(priority_obj, 'name', 'Unknown') if priority_obj else 'Unknown'
            issue_type_obj = getattr(fields_obj, 'issuetype', None) if fields_obj else None
            issue_type = getattr(issue_type_obj, 'name', 'Unknown') if issue_type_obj else 'Unknown'
            
            assignee = None
            if fields_obj and fields_obj.assignee:
                assignee = {
                    "name": getattr(fields_obj.assignee, 'displayName', 'Unknown'),
                    "email": getattr(fields_obj.assignee, 'emailAddress', 'Unknown')
                }
            
            reporter = None
            if fields_obj and fields_obj.reporter:
                reporter = {
                    "name": getattr(fields_obj.reporter, 'displayName', 'Unknown'),
                    "email": getattr(fields_obj.reporter, 'emailAddress', 'Unknown')
                }
            
            # Description
            description = getattr(fields_obj, 'description', '') if fields_obj else ''
            if description:
                description = description.replace('\n', ' ').strip()
            
            # Timestamps
            created = getattr(fields_obj, 'created', '') if fields_obj else ''
            updated = getattr(fields_obj, 'updated', '') if fields_obj else ''
        
        return {
            "key": key,
            "summary": summary,
            "type": issue_type,
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "reporter": reporter,
            "created": created,
            "updated": updated,
            "description": description
        }
        
    except Exception as e:
        return {
            "key": getattr(issue, 'key', 'ERROR'),
            "error": str(e),
            "summary": "Error extracting issue data"
        }


def read_jira_team_data_tool(client, config):
    """Create read_jira_team_data tool function"""
    
    def read_jira_team_data(team: str, tickets_filter: str = "All In Progress", format: str = "json") -> str:
        """Read Jira team data dump."""
        try:
            validated_team = validate_team_name(team)
            
            # Determine file paths
            dump_dir = config.get("data_collection", {}).get("dump_directory", "jira_dumps")
            filename = f"{validated_team}_{tickets_filter.lower().replace(' ', '_')}_jira_dump.{format}"
            filepath = os.path.join(dump_dir, filename)
            
            if not os.path.exists(filepath):
                return create_error_response(f"Jira data dump not found: {filepath}")
            
            if format.lower() == "json":
                # Read JSON data
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return create_success_response({
                    "team": validated_team,
                    "filter": tickets_filter,
                    "format": format,
                    "file_path": filepath,
                    "data": data
                })
            
            else:
                # Read text data
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return create_success_response({
                    "team": validated_team,
                    "filter": tickets_filter,
                    "format": format,
                    "file_path": filepath,
                    "content": content
                })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to read Jira team data", str(e))
    
    return read_jira_team_data
