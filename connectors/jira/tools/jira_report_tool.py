"""
Jira Report Tool for Work Planner MCP Server
Inspired by jira-report-mpc project for clean, effective reporting
"""

from fastmcp import FastMCP
from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime
from connectors.jira.client import JiraClient
from connectors.jira.config import JiraConfig
from connectors.gemini.client import GeminiClient
from connectors.gemini.config import GeminiConfig
from utils.responses import create_success_response, create_error_response


def register_jira_report_tool(mcp: FastMCP):
    """Register Jira report generation tool"""
    
    @mcp.tool()
    def generate_jira_team_report(team: str, status_filter: str = "All In Progress") -> str:
        """
        Generate a comprehensive Jira team report in the style of jira-report-mpc.
        
        Args:
            team: Team name (e.g., 'toolchain', 'foa', 'assessment', 'boa')
            status_filter: Jira status filter (default: 'All In Progress')
            
        Returns:
            JSON string with formatted report data
        """
        try:
            # Initialize Jira client
            jira_config = JiraConfig.load('config/jira.yaml')
            jira_client = JiraClient(jira_config)
            
            # Get team issues
            from connectors.jira.tools.get_team_issues import get_team_issues_tool
            team_issues_tool = get_team_issues_tool(jira_client, jira_config)
            
            result = team_issues_tool(team=team, status=status_filter)
            
            if not result.get('success'):
                return create_error_response("Failed to fetch team issues", result.get('error', 'Unknown error'))
            
            issues = result.get('data', {}).get('issues', [])
            
            # Format issues in jira-report-mpc style
            formatted_issues = []
            for issue in issues:
                formatted_issue = {
                    'key': issue.get('key', 'N/A'),
                    'url': f"{jira_config.get('jira_url', '')}/browse/{issue.get('key', '')}",
                    'summary': issue.get('summary', 'No summary'),
                    'assignee': issue.get('assignee', {}).get('displayName', 'Unassigned'),
                    'status': issue.get('status', {}).get('name', 'Unknown'),
                    'updated': issue.get('updated', 'Unknown'),
                    'priority': issue.get('priority', {}).get('name', 'Unknown'),
                    'issuetype': issue.get('issuetype', {}).get('name', 'Unknown'),
                    'epic_link': issue.get('customfield_10014', 'No Epic Link'),  # Epic Link field
                    'description': issue.get('description', 'No description'),
                    'comments': issue.get('comments', [])
                }
                formatted_issues.append(formatted_issue)
            
            # Generate AI summary if available
            ai_summary = "AI analysis not available"
            try:
                gemini_config = GeminiConfig()
                gemini_client = GeminiClient(gemini_config.get_config())
                
                # Create AI prompt for team analysis
                issues_text = "\n".join([
                    f"Issue: {issue['key']} - {issue['summary']} (Status: {issue['status']}, Assignee: {issue['assignee']})"
                    for issue in formatted_issues
                ])
                
                prompt = f"""
                Analyze the following Jira issues for the {team} team and provide insights:
                
                {issues_text}
                
                Please provide:
                1. Key themes and patterns
                2. Potential blockers or risks
                3. Productivity suggestions
                4. Team workload distribution
                
                Keep the response concise and actionable.
                """
                
                ai_response = gemini_client.generate_content(prompt)
                if ai_response:
                    ai_summary = ai_response
                    
            except Exception as e:
                print(f"AI analysis failed: {e}")
            
            # Create report data
            report_data = {
                'team': team,
                'status_filter': status_filter,
                'total_issues': len(formatted_issues),
                'issues': formatted_issues,
                'ai_summary': ai_summary,
                'generated_at': datetime.now().isoformat(),
                'jira_url': jira_config.get('jira_url', '')
            }
            
            return create_success_response(report_data)
            
        except Exception as e:
            return create_error_response("Failed to generate Jira team report", str(e))
    
    @mcp.tool()
    def generate_detailed_jira_report(team: str, status_filter: str = "All In Progress") -> str:
        """
        Generate a detailed Jira report with individual ticket details.
        
        Args:
            team: Team name
            status_filter: Jira status filter
            
        Returns:
            JSON string with detailed report
        """
        try:
            # Get basic report first
            basic_report = generate_jira_team_report(team, status_filter)
            basic_data = json.loads(basic_report)
            
            if not basic_data.get('success'):
                return basic_report
            
            issues = basic_data.get('data', {}).get('issues', [])
            
            # Format detailed ticket information
            detailed_tickets = []
            for issue in issues:
                # Extract recent comments for AI analysis
                comments_text = ""
                if issue.get('comments'):
                    recent_comments = issue['comments'][-3:]  # Last 3 comments
                    comments_text = "\n".join([
                        f"- {comment.get('author', {}).get('displayName', 'Unknown')}: {comment.get('body', 'No content')}"
                        for comment in recent_comments
                    ])
                
                detailed_ticket = {
                    'key': issue['key'],
                    'url': issue['url'],
                    'summary': issue['summary'],
                    'assignee': issue['assignee'],
                    'status': issue['status'],
                    'updated': issue['updated'],
                    'priority': issue['priority'],
                    'issuetype': issue['issuetype'],
                    'epic_link': issue['epic_link'],
                    'description': issue['description'][:500] + "..." if len(issue['description']) > 500 else issue['description'],
                    'recent_comments': comments_text,
                    'has_epic': issue['epic_link'] != 'No Epic Link',
                    'is_stale': _is_stale_issue(issue['updated'])
                }
                detailed_tickets.append(detailed_ticket)
            
            # Generate detailed AI analysis
            detailed_analysis = _generate_detailed_analysis(detailed_tickets, team)
            
            report_data = {
                'team': team,
                'status_filter': status_filter,
                'total_issues': len(detailed_tickets),
                'tickets': detailed_tickets,
                'detailed_analysis': detailed_analysis,
                'generated_at': datetime.now().isoformat()
            }
            
            return create_success_response(report_data)
            
        except Exception as e:
            return create_error_response("Failed to generate detailed Jira report", str(e))
    
    @mcp.tool()
    def generate_executive_summary(team: str) -> str:
        """
        Generate an executive summary report for team leadership.
        
        Args:
            team: Team name
            
        Returns:
            JSON string with executive summary
        """
        try:
            # Get team issues
            team_report = generate_jira_team_report(team, "All In Progress")
            team_data = json.loads(team_report)
            
            if not team_data.get('success'):
                return team_report
            
            issues = team_data.get('data', {}).get('issues', [])
            
            # Group issues by assignee
            assignee_groups = {}
            for issue in issues:
                assignee = issue.get('assignee', 'Unassigned')
                if assignee not in assignee_groups:
                    assignee_groups[assignee] = []
                assignee_groups[assignee].append(issue)
            
            # Generate executive summary
            executive_data = {
                'team': team,
                'total_issues': len(issues),
                'assignee_count': len(assignee_groups),
                'assignee_workload': {
                    assignee: {
                        'issue_count': len(issues_list),
                        'issues': [issue['key'] for issue in issues_list],
                        'statuses': list(set(issue['status'] for issue in issues_list))
                    }
                    for assignee, issues_list in assignee_groups.items()
                },
                'team_insights': _generate_team_insights(assignee_groups, team),
                'generated_at': datetime.now().isoformat()
            }
            
            return create_success_response(executive_data)
            
        except Exception as e:
            return create_error_response("Failed to generate executive summary", str(e))


def _is_stale_issue(updated_date: str) -> bool:
    """Check if an issue is stale (not updated in 7+ days)"""
    try:
        from datetime import datetime, timedelta
        updated = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
        return datetime.now(updated.tzinfo) - updated > timedelta(days=7)
    except:
        return False


def _generate_detailed_analysis(tickets: List[Dict], team: str) -> str:
    """Generate detailed AI analysis of tickets"""
    try:
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        
        tickets_summary = "\n".join([
            f"- {ticket['key']}: {ticket['summary']} (Status: {ticket['status']}, Assignee: {ticket['assignee']})"
            for ticket in tickets
        ])
        
        prompt = f"""
        Provide a detailed analysis of the {team} team's Jira tickets:
        
        {tickets_summary}
        
        Please analyze:
        1. Work distribution and workload balance
        2. Potential blockers and dependencies
        3. Risk assessment
        4. Recommendations for team productivity
        5. Priority attention items
        
        Format as a structured report with clear sections.
        """
        
        return gemini_client.generate_content(prompt) or "Detailed analysis not available"
        
    except Exception as e:
        return f"Analysis failed: {str(e)}"


def _generate_team_insights(assignee_groups: Dict, team: str) -> str:
    """Generate team-level insights"""
    try:
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        
        workload_summary = "\n".join([
            f"- {assignee}: {len(issues)} issues"
            for assignee, issues in assignee_groups.items()
        ])
        
        prompt = f"""
        Analyze the {team} team's workload distribution and provide executive insights:
        
        {workload_summary}
        
        Provide insights on:
        1. Team capacity and workload balance
        2. Resource allocation recommendations
        3. Potential bottlenecks
        4. Strategic recommendations
        
        Keep it concise and executive-focused.
        """
        
        return gemini_client.generate_content(prompt) or "Team insights not available"
        
    except Exception as e:
        return f"Insights generation failed: {str(e)}"
