"""
Daily Report Tool - Wraps GitHub Actions workflow for local testing
Allows triggering the full daily team report from Cursor without GitHub Actions
"""

import sys
import os
from typing import Optional
from utils.responses import create_error_response, create_success_response


def send_team_daily_report_tool():
    """Create send_team_daily_report tool function"""
    
    def send_team_daily_report(
        team: str = "toolchain",
        include_paul_todos: bool = True
    ) -> str:
        """
        Generate and send complete daily team report with AI analysis.
        This is the LOCAL equivalent of the GitHub Actions workflow.
        
        Args:
            team: Team name (toolchain, foa, assessment, boa)
            include_paul_todos: Whether to include Paul's TODO items in the report
            
        Returns:
            Report generation and email send status
            
        Example:
            send_team_daily_report(team="toolchain")
        """
        try:
            print(f"\n🚀 Starting daily report generation for {team} team...")
            print(f"📍 Running from: {os.getcwd()}")
            
            # Import the GitHub Actions workflow script
            sys.path.insert(0, os.path.join(os.getcwd(), '.github', 'workflows', 'scripts'))
            
            try:
                from github_daily_report import (
                    collect_team_data,
                    generate_ai_analysis,
                    generate_paul_todo_items,
                    send_team_email
                )
            except ImportError as e:
                return create_error_response(
                    "Failed to import GitHub Actions workflow",
                    f"Could not import github_daily_report.py: {e}"
                )
            
            # Initialize clients (same as GitHub Actions)
            print(f"📡 Initializing Slack client...")
            from connectors.slack.client import SlackClient
            from connectors.slack.config import SlackConfig
            slack_config = SlackConfig.load('config/slack.yaml')
            slack_client = SlackClient(slack_config)
            
            print(f"📡 Initializing Jira client...")
            from connectors.jira.client import JiraClient
            from connectors.jira.config import JiraConfig
            jira_config = JiraConfig()
            jira_client = JiraClient(jira_config.get_config())
            
            print(f"📡 Initializing Gemini AI client...")
            from connectors.gemini.client import GeminiClient
            from connectors.gemini.config import GeminiConfig
            gemini_config = GeminiConfig()
            gemini_client = GeminiClient(gemini_config.get_config())
            
            # Step 1: Collect team data
            print(f"\n📊 Collecting data for {team} team...")
            team_data = collect_team_data(team)
            
            channels_count = len(team_data.get('channels', {}))
            messages_count = team_data.get('total_messages', 0)
            tickets_count = team_data.get('total_tickets', 0)
            
            print(f"  ✅ Collected: {channels_count} channels, {messages_count} messages, {tickets_count} tickets")
            
            # Step 2: Generate AI analysis
            print(f"\n🤖 Running AI analysis...")
            ai_summaries = generate_ai_analysis(team_data)
            
            # Step 3: Generate Paul TODO items (if requested)
            paul_todo_items = ""
            if include_paul_todos:
                print(f"\n📝 Generating Paul's action items...")
                paul_todo_items = generate_paul_todo_items(
                    team_data, 
                    slack_client, 
                    jira_client, 
                    gemini_client
                )
            
            # Step 4: Send email
            print(f"\n📧 Sending email report...")
            email_success = send_team_email(
                team,
                team_data,
                ai_summaries,
                paul_todo_items,
                slack_client,
                jira_client,
                gemini_client
            )
            
            if email_success:
                return create_success_response({
                    "message": f"Daily report for {team} team generated and sent successfully",
                    "team": team,
                    "channels_processed": channels_count,
                    "messages_collected": messages_count,
                    "tickets_collected": tickets_count,
                    "paul_todos_included": include_paul_todos,
                    "email_sent": True,
                    "note": "This uses the same logic as GitHub Actions workflow"
                })
            else:
                return create_error_response(
                    f"Report generated but email failed for {team} team",
                    "Check email configuration and logs"
                )
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"\n❌ Error: {error_details}")
            return create_error_response(
                f"Failed to generate daily report for {team} team",
                str(e)
            )
    
    return send_team_daily_report

