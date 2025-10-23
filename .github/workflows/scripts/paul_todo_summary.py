#!/usr/bin/env python3
"""
GitHub Actions Script: Paul TODO Summary - Consolidated Email Only
Focuses on generating a single consolidated TODO email for Paul Caramuto
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any

# Suppress warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['GRPC_POLL_STRATEGY'] = 'poll'
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '0'

import logging
logging.getLogger('absl').setLevel(logging.ERROR)

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

print(f'🔍 Project root: {project_root}')

# Import from main script (reuse helper functions)
from github_daily_report import (
    _load_time_ranges_config,
    _load_gemini_prompts,
    _load_paul_todo_config,
    _run_async_helper,
    generate_paul_todo_items,
    collect_team_data
)


def extract_email_todos(gemini_client, time_ranges: Dict) -> tuple:
    """Extract email TODOs"""
    try:
        print('\n📧 Extracting Email TODOs...')
        from connectors.email.config import EmailConfig
        from connectors.email.tools.inbox_tools import extract_email_todos_tool
        
        email_config = EmailConfig()
        slack_config = time_ranges.get('slack', {})
        search_days = slack_config.get('paul_todo_search_days', 30)
        
        gemini_config_dict = gemini_client.config if hasattr(gemini_client, 'config') else {}
        email_tool = extract_email_todos_tool(email_config, gemini_config_dict)
        
        print(f'  📧 Analyzing inbox (last {search_days} days)...')
        result = email_tool(days_back=search_days)
        data = json.loads(result)
        
        todos = data.get('todos', [])
        emails_analyzed = data.get('emails_analyzed', 0)
        
        print(f'  ✅ Email extraction complete: {len(todos)} TODOs from {emails_analyzed} emails')
        
        # Format TODOs for HTML
        if todos:
            email_todos_html = '<div style="margin: 10px 0;">'
            
            urgency_groups = {'critical': [], 'high': [], 'medium': [], 'low': []}
            for todo in todos:
                urgency = todo.get('urgency', 'low')
                if urgency in urgency_groups:
                    urgency_groups[urgency].append(todo)
            
            urgency_colors = {
                'critical': '#dc3545',
                'high': '#fd7e14',
                'medium': '#ffc107',
                'low': '#28a745'
            }
            
            urgency_icons = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }
            
            for urgency in ['critical', 'high', 'medium', 'low']:
                urgency_todos = urgency_groups[urgency]
                if urgency_todos:
                    email_todos_html += f'<h4 style="color: {urgency_colors[urgency]}; margin-top: 15px;">{urgency_icons[urgency]} {urgency.upper()} Priority ({len(urgency_todos)} items)</h4>'
                    
                    for todo in urgency_todos[:10]:
                        desc = todo.get('description', 'No description')
                        deadline = todo.get('deadline') or 'No deadline'
                        confidence = float(todo.get('confidence', 0))
                        metadata = todo.get('metadata', {})
                        from_email = metadata.get('from', 'Unknown')
                        subject = metadata.get('subject', 'No subject')
                        
                        email_todos_html += f'''
                        <div style="margin: 10px 0; padding: 10px; border-left: 3px solid {urgency_colors[urgency]}; background: #f8f9fa;">
                            <p style="margin: 5px 0;"><strong>{desc}</strong></p>
                            <p style="margin: 5px 0; font-size: 12px; color: #666;">
                                📅 Deadline: {deadline} | 📈 Confidence: {confidence:.2f}<br>
                                📧 From: {from_email[:50]}<br>
                                📝 Subject: {subject[:60]}
                            </p>
                        </div>
                        '''
            
            email_todos_html += '</div>'
        else:
            email_todos_html = '<p style="color: #666; font-style: italic;">No actionable email TODOs found in the specified time period.</p>'
        
        return len(todos), email_todos_html
        
    except Exception as e:
        print(f'  ❌ Email TODO extraction failed: {e}')
        import traceback
        traceback.print_exc()
        return 0, '<p style="color: #dc3545; font-style: italic;">Email TODO extraction failed. Check logs for details.</p>'


def send_consolidated_email(all_team_todos: Dict, gemini_client, time_ranges: Dict) -> bool:
    """Send consolidated Paul TODO email"""
    try:
        print(f'\n📋 Sending Paul Caramuto consolidated TODO email...')
        from connectors.email.client import EmailClient
        from connectors.email.config import EmailConfig
        
        email_config = EmailConfig()
        config = email_config.get_config()
        
        if not email_config.validate_config():
            print(f'  ❌ Email config validation failed')
            return False
            
        email_client = EmailClient(config)
        
        # Filter team data
        team_todos_only = {k: v for k, v in all_team_todos.items() if not k.startswith('_')}
        
        # Calculate statistics
        total_todos = len(team_todos_only)
        total_slack_mentions = sum(data['slack_mentions_count'] for data in team_todos_only.values())
        total_jira_mentions = sum(data['jira_mentions_count'] for data in team_todos_only.values())
        
        # Generate AI consolidated summary
        print(f'  🤖 Generating consolidated AI summary...')
        prompts = _load_gemini_prompts()
        prompt_template = prompts.get('paul_consolidated_todo')
        
        if not prompt_template:
            print(f'  ⚠️  paul_consolidated_todo prompt not found in gemini.yaml')
            consolidated_todos_text = "Consolidated TODO analysis unavailable - prompt configuration missing"
        else:
            consolidated_prompt = prompt_template.format(
                team_count=total_todos,
                team_todos=chr(10).join([f"Team {team.upper()}: {chr(10)}{data['ai_todos']}" for team, data in team_todos_only.items()])
            )
            
            consolidated_todos_text = gemini_client.generate_content(consolidated_prompt)
            if not consolidated_todos_text:
                consolidated_todos_text = "Consolidated TODO analysis not available"
        
        consolidated_todos_html = f"<pre style='white-space: pre-wrap; font-family: monospace; line-height: 1.6;'>{consolidated_todos_text}</pre>"
        
        # Format TODOs by team
        todos_by_team_html = ""
        for team, data in team_todos_only.items():
            todos_by_team_html += f"""
            <div style="margin: 20px 0; padding: 20px; border: 1px solid #dee2e6; border-radius: 5px; background: #ffffff;">
                <h4 style="margin-top: 0; color: #007acc;">🔧 {team.upper()} Team</h4>
                <p><strong>Slack Mentions:</strong> {data['slack_mentions_count']} | <strong>Jira Mentions:</strong> {data['jira_mentions_count']}</p>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 10px;">
                    <pre style="white-space: pre-wrap; font-family: monospace; margin: 0; line-height: 1.6;">{data['ai_todos']}</pre>
                </div>
            </div>
            """
        
        slack_config = time_ranges.get('slack', {})
        search_days = slack_config.get('paul_todo_search_days', 30)
        
        # Get email data
        email_todos_count = all_team_todos.get('_email_todos_count', 0)
        email_action_items = all_team_todos.get('_email_action_items', '<p style="color: #666; font-style: italic;">Email TODO extraction not enabled.</p>')
        
        # Prepare template data
        template_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            'search_days': search_days,
            'total_todos': total_todos,
            'teams_count': len(team_todos_only),
            'slack_mentions_count': total_slack_mentions,
            'jira_mentions_count': total_jira_mentions,
            'email_todos_count': email_todos_count,
            'email_action_items': email_action_items,
            'consolidated_todos': consolidated_todos_html,
            'todos_by_team': todos_by_team_html
        }
        
        # Send email
        result = email_client.send_email(
            template_name='paul_todo_summary',
            recipients=config['recipients']['default'],
            content_data=template_data
        )
        
        if result.get('success'):
            print(f'  ✅ Paul consolidated TODO email sent successfully!')
            return True
        else:
            print(f'  ❌ Email failed: {result.get("error")}')
            return False
            
    except Exception as e:
        print(f'  ❌ Email sending failed: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function for Paul TODO Summary"""
    print('🚀 Starting Paul TODO Summary Email Generation...')
    
    # Initialize clients
    from connectors.slack.client import SlackClient
    from connectors.slack.config import SlackConfig
    from connectors.jira.client import JiraClient
    from connectors.jira.config import JiraConfig
    from connectors.gemini.client import GeminiClient
    from connectors.gemini.config import GeminiConfig
    
    slack_config = SlackConfig.load("config/slack.yaml")
    slack_client = SlackClient(slack_config)
    
    jira_config = JiraConfig.load("config/jira.yaml")
    jira_client = JiraClient(jira_config)
    
    gemini_config = GeminiConfig("config/gemini.yaml")
    gemini_client = GeminiClient(gemini_config.get_config())
    
    teams = ['toolchain', 'foa', 'assessment', 'boa']
    
    # Load time ranges
    time_ranges = _load_time_ranges_config()
    
    # Extract Email TODOs first
    email_todos_count, email_action_items_html = extract_email_todos(gemini_client, time_ranges)
    
    # Collect TODO data from all teams (Slack/Jira mentions only)
    all_team_todos = {}
    
    for team in teams:
        print(f'\n📊 Collecting TODO data for team: {team.upper()}')
        
        # Collect minimal team data (we don't need full channel details for consolidated email)
        team_data = collect_team_data(team, slack_client, jira_client)
        
        # Generate Paul TODO items for this team
        paul_todo_items = generate_paul_todo_items(team_data, slack_client, jira_client, gemini_client)
        
        # Count mentions
        slack_mentions_count = len([
            msg for channel_data in team_data.get('channels', {}).values()
            for msg in channel_data.get('messages', [])
            if any(mention in msg.get('text', '').lower() for mention in ['paul', 'pacaramu'])
        ])
        
        jira_mentions_count = sum(
            1 for tickets in team_data.get('jira_tickets', {}).values()
            for ticket in tickets
            if any(mention in str(ticket).lower() for mention in ['paul', 'pacaramu'])
        )
        
        all_team_todos[team] = {
            'ai_todos': paul_todo_items,
            'slack_mentions_count': slack_mentions_count,
            'jira_mentions_count': jira_mentions_count
        }
        
        print(f'  ✅ {team.upper()}: {slack_mentions_count} Slack mentions, {jira_mentions_count} Jira mentions')
    
    # Add email data
    all_team_todos['_email_todos_count'] = email_todos_count
    all_team_todos['_email_action_items'] = email_action_items_html
    
    # Send consolidated email
    print('\n📋 Generating and sending consolidated Paul TODO email...')
    success = send_consolidated_email(all_team_todos, gemini_client, time_ranges)
    
    if success:
        print('\n🎉 Paul TODO Summary email sent successfully!')
        print(f'📧 Consolidated email includes:')
        print(f'   - {email_todos_count} Email action items')
        print(f'   - Slack/Jira mentions from {len(teams)} teams')
        print(f'   - AI-powered consolidated summary')
    else:
        print('\n❌ Failed to send Paul TODO Summary email')
        sys.exit(1)


if __name__ == '__main__':
    main()

