"""
Jira client wrapper
"""

import os
from jira import JIRA
from typing import List, Dict, Any


class JiraClient:
    """Jira client wrapper"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = self._create_client()
    
    def _create_client(self):
        """Create Jira client instance"""
        jira_url = os.getenv('JIRA_URL')
        jira_token = os.getenv('JIRA_API_TOKEN')
        
        if not all([jira_url, jira_token]):
            raise RuntimeError("Missing JIRA_URL or JIRA_API_TOKEN environment variables")
        
        return JIRA(server=jira_url, token_auth=jira_token)
    
    def search_issues(self, jql: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search issues using JQL"""
        # Search with all fields to get complete issue data
        issues = self.client.search_issues(jql, maxResults=max_results, expand='changelog')
        
        result = []
        for issue in issues:
            # Get all fields from the issue
            issue_data = {
                'key': issue.key,
                'summary': issue.fields.summary,
                'status': issue.fields.status.name,
                'assignee': self._get_display_name(issue.fields.assignee.displayName) if issue.fields.assignee else 'Unassigned',
                'updated': issue.fields.updated,
                'priority': issue.fields.priority.name if issue.fields.priority else 'None',
                'issue_type': issue.fields.issuetype.name,
                'url': f"{self.client.server_url}/browse/{issue.key}"
            }
            
            # Add all custom fields and other fields
            for field_name, field_value in issue.raw['fields'].items():
                if field_name not in ['summary', 'status', 'assignee', 'updated', 'priority', 'issuetype']:
                    issue_data[field_name] = field_value
            
            result.append(issue_data)
        
        return result
    
    def _get_display_name(self, username: str) -> str:
        """Get display name from username"""
        user_mappings = self.config.get("user_display_names", {})
        for eng_name, jira_username in user_mappings.items():
            if jira_username == username:
                return eng_name
        return username
    
    def resolve_display_name_to_username(self, display_name: str) -> str:
        """Resolve engineer display name to Jira username using the configuration"""
        user_display_names = self.config.get("user_display_names", {})
        # Check for exact match first (case-sensitive)
        if display_name in user_display_names:
            return user_display_names[display_name]
        
        # Check for case-insensitive match
        for eng_name, jira_username in user_display_names.items():
            if eng_name.lower() == display_name.lower():
                return jira_username
        
        # If no mapping found, return the input as-is (assume it's already a Jira username)
        return display_name
    
    def resolve_team_alias(self, team_input: str) -> str:
        """Resolve team alias to actual team ID using the configuration"""
        team_aliases = self.config.get("team_aliases", {})
        # Check for exact match first (case-sensitive)
        if team_input in team_aliases:
            return team_aliases[team_input]
        
        # Check for case-insensitive match
        for alias, team_id in team_aliases.items():
            if alias.lower() == team_input.lower():
                return team_id
        
        # If no alias found, return the input as-is
        return team_input
    
    def resolve_organization_alias(self, org_input: str) -> str:
        """Resolve organization alias to actual organization ID using the configuration"""
        org_aliases = self.config.get("organization_aliases", {})
        # Check for exact match first (case-sensitive)
        if org_input in org_aliases:
            return org_aliases[org_input]
        
        # Check for case-insensitive match
        for alias, org_id in org_aliases.items():
            if alias.lower() == org_input.lower():
                return org_id
        
        # If no alias found, return the input as-is
        return org_input
    
    def build_jql(self, project: str, status: str, assignees: list = None) -> str:
        """Build JQL query for project, status, and optional assignees"""
        jql = f'project = "{project}"'
        
        # Only add status filter if status is provided
        if status:
            jql += f' AND statusCategory = "{status}"'
        
        if assignees and len(assignees) > 0:
            assignee_list = ' OR '.join([f'assignee = "{assignee}"' for assignee in assignees])
            jql += f' AND ({assignee_list})'
        
        jql += ' ORDER BY updatedDate DESC'
        return jql
