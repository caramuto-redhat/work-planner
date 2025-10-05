#!/usr/bin/env python3
"""
GitHub Actions Daily Team Report Script
Clean separation from MCP tools - reuses existing functionality
"""

import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any

# Add project root to Python path so we can import connectors
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

print(f'🔍 Project root: {project_root}')
print(f'🔍 Python path: {sys.path[:3]}...')

def collect_team_data(team: str) -> Dict[str, Any]:
    """Collect Slack and Jira data for a team using existing MCP tools"""
    print(f'📊 Collecting data for team: {team.upper()}')
    
    # Initialize Slack data
    slack_data = {
        'summary': 'No Slack data available',
        'details': [],
        'messages_count': 0
    }
    
    # Initialize Jira data  
    jira_data = {
        'summary': 'No Jira data available',
        'details': [],
        'issues_count': 0
    }
    
    # Collect Slack data using existing MCP tools
    try:
        print(f'  📱 Attempting to import Slack tools...')
        from connectors.slack.tools.unified_slack_tools import dump_slack_data_tool, read_slack_data_tool
        from connectors.slack.client import SlackClient
        from connectors.slack.config import SlackConfig
        
        print(f'  📱 Successfully imported Slack tools')
        
        slack_config = SlackConfig.load('config/slack.yaml')
        slack_client = SlackClient(slack_config)
        
        # Find team channels
        slack_channels = slack_config.get('slack_channels', {})
        team_channels = [ch_id for ch_id, team_name in slack_channels.items() if team_name == team]
        
        print(f'  📱 Found {len(team_channels)} channels for {team}')
        
        if team_channels:
            # Use existing MCP tools
            dump_tool = dump_slack_data_tool(slack_client, slack_config)
            read_tool = read_slack_data_tool(slack_client, slack_config)
            
            for channel_id in team_channels:
                try:
                    print(f'  📱 Processing channel: {channel_id}')
                    
                    # Dump data using MCP tool
                    dump_result = dump_tool(channel_id)
                    print(f'  📱 Dump result type: {type(dump_result)}')
                    
                    # Parse JSON result
                    if dump_result is None:
                        print(f'  ⚠️  Dump returned None for channel {channel_id}')
                        continue
                    elif isinstance(dump_result, str):
                        try:
                            dump_data = json.loads(dump_result)
                        except json.JSONDecodeError:
                            print(f'  ⚠️  Dump returned non-JSON: {dump_result[:100]}...')
                            continue
                    else:
                        dump_data = dump_result
                    
                    if not dump_data.get('success'):
                        print(f'  ⚠️  Dump failed: {dump_data.get("error")}')
                        continue
                    
                    # Read data using MCP tool
                    read_result = read_tool(channel_id)
                    print(f'  📱 Read result type: {type(read_result)}')
                    
                    # Parse JSON result
                    if isinstance(read_result, str):
                        try:
                            read_data = json.loads(read_result)
                        except json.JSONDecodeError:
                            print(f'  ⚠️  Read returned non-JSON: {read_result[:100]}...')
                            continue
                    else:
                        read_data = read_result
                    
                    if read_data.get('success'):
                        data = read_data.get('data', {})
                        messages = data.get('messages', [])
                        
                        slack_data['messages_count'] = len(messages)
                        slack_data['summary'] = f'Slack data collected from {len(team_channels)} channels ({len(messages)} messages)'
                        
                        # Get recent messages for summary
                        recent_messages = messages[-5:] if messages else []
                        for msg in recent_messages:
                            user = msg.get('user', 'Unknown')
                            text = msg.get('text', 'No text')
                            slack_data['details'].append(f'  - {user}: {text[:100]}...')
                        break
                        
                except Exception as e:
                    print(f'  ⚠️  Slack channel {channel_id}: {e}')
                    continue
                    
    except Exception as e:
        print(f'  ❌ Slack collection failed: {e}')
    
    # Collect Jira data using existing MCP tools
    try:
        print(f'  🎫 Attempting to import Jira tools...')
        from connectors.jira.tools.jira_data_collection import dump_jira_team_data_tool
        from connectors.jira.client import JiraClient
        from connectors.jira.config import JiraConfig
        
        print(f'  🎫 Successfully imported Jira tools')
        
        jira_config = JiraConfig.load('config/jira.yaml')
        jira_client = JiraClient(jira_config)
        
        print(f'  🎫 Collecting Jira data for {team}...')
        
        # Use existing MCP tool
        dump_tool = dump_jira_team_data_tool(jira_client, jira_config)
        dump_result = dump_tool(team, 'All In Progress')
        print(f'  🎫 Dump result type: {type(dump_result)}')
        
        # Parse JSON result
        if dump_result is None:
            print(f'  ⚠️  Jira dump returned None')
            dump_data = {'success': False, 'error': 'Dump returned None'}
        elif isinstance(dump_result, str):
            try:
                dump_data = json.loads(dump_result)
            except json.JSONDecodeError:
                print(f'  ⚠️  Jira dump returned non-JSON: {dump_result[:100]}...')
                dump_data = {'success': False, 'error': 'Invalid JSON response'}
        else:
            dump_data = dump_result
        
        if dump_data.get('success'):
            # Read the JSON dump created by the MCP tool
            dump_dir = 'jira_dumps'
            json_file = f'{team}_all_in_progress_jira_dump.json'
            json_path = f'{dump_dir}/{json_file}'
            
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                issues = data.get('issues', [])
                jira_data['issues_count'] = len(issues)
                jira_data['summary'] = f'{len(issues)} tickets in progress'
                
                print(f'  🎫 Found {len(issues)} issues for {team}')
                
                # Format ticket details (inspired by jira-report-mpc)
                for issue in issues[:10]:  # Limit to 10 most recent
                    ticket_info = f"""
==========
Issue: {issue.get('key', 'N/A')}
({jira_config.get('jira_url', '')}/browse/{issue.get('key', '')})
Owner: {issue.get('assignee', {}).get('displayName', 'Unassigned')}
Summary: {issue.get('summary', 'No summary')}
Status: {issue.get('status', {}).get('name', 'Unknown')}
Updated: {issue.get('updated', 'Unknown')}
"""
                    jira_data['details'].append(ticket_info.strip())
            else:
                print(f'  ⚠️  Jira dump file not found: {json_path}')
        else:
            print(f'  ⚠️  Jira dump failed: {dump_data.get("error")}')
            
    except Exception as e:
        print(f'  ❌ Jira collection failed: {e}')
    
    return {
        'team': team,
        'slack': slack_data,
        'jira': jira_data
    }


def generate_ai_analysis(team_data: Dict[str, Any]) -> str:
    """Generate AI analysis using existing Gemini tools"""
    try:
        print(f'  🤖 Attempting to import Gemini tools...')
        from connectors.gemini.tools.ai_summary_tool import ai_summary_tool
        from connectors.gemini.client import GeminiClient
        from connectors.gemini.config import GeminiConfig
        
        print(f'  🤖 Successfully imported Gemini tools')
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        ai_tool_func = ai_summary_tool(gemini_client, gemini_config.get_config())
        
        print(f'  🤖 Generating AI summary for {team_data["team"]}...')
        
        # Use existing MCP tool
        result = ai_tool_func(team=team_data['team'], send_email=False)
        print(f'  🤖 AI result type: {type(result)}')
        
        # Parse JSON result
        if result is None:
            print(f'  ⚠️  AI analysis returned None')
            return 'AI analysis returned None'
        elif isinstance(result, str):
            try:
                result_data = json.loads(result)
            except json.JSONDecodeError:
                print(f'  ⚠️  AI analysis returned non-JSON: {result[:100]}...')
                return 'AI analysis returned invalid response'
        else:
            result_data = result
        
        if result_data.get('success'):
            return result_data.get('summary', 'AI analysis completed')
        else:
            return f'AI analysis failed: {result_data.get("error", "Unknown error")}'
            
    except Exception as e:
        print(f'  ⚠️  AI analysis failed: {e}')
        return 'AI analysis not available'


def create_email_content(team_data: Dict[str, Any], ai_summary: str) -> str:
    """Create HTML email content"""
    team = team_data['team']
    slack = team_data['slack']
    jira = team_data['jira']
    
    return f"""
<h2>📊 {team.upper()} Team Daily Report</h2>

<p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><strong>Team:</strong> {team.upper()}</p>

<h3>📱 Slack Activity</h3>
<p>{slack['summary']}</p>
{''.join(f'<p>{detail}</p>' for detail in slack['details']) if slack['details'] else ''}

<h3>🎫 Jira Tickets - In Progress</h3>
<p><strong>{jira['summary']}</strong></p>

{''.join(f'<pre>{detail}</pre>' for detail in jira['details']) if jira['details'] else '<p>No tickets found</p>'}

<h3>🤖 AI Analysis</h3>
<p>{ai_summary}</p>

<hr>
<p><em>Generated by Work Planner MCP Server</em></p>
"""


def send_email(team: str, email_body: str) -> bool:
    """Send email using existing email configuration"""
    try:
        print(f'  📧 Attempting to import Email tools...')
        from connectors.email.client import EmailClient
        from connectors.email.config import EmailConfig
        
        print(f'  📧 Successfully imported Email tools')
        
        email_config = EmailConfig()
        config = email_config.get_config()
        print(f'  📧 Email config loaded: {bool(config)}')
        print(f'  📧 Config keys: {list(config.keys()) if config else "None"}')
        
        # Validate config before creating client
        if not email_config.validate_config():
            print(f'  ❌ Email config validation failed')
            return False
            
        email_client = EmailClient(config)
        
        # Prepare summary data for daily_summary template
        summary_data = {
            'content': f"""
<h3>📱 Slack Activity</h3>
<p>{team_data.get('slack_summary', 'No Slack data available')}</p>

<h3>🎫 Jira Tickets - In Progress</h3>
<p><strong>{team_data.get('jira_summary', 'No Jira data available')}</strong></p>
{chr(10).join(team_data.get('jira_details', []))}

<h3>🤖 AI Analysis</h3>
<p>{team_data.get('ai_summary', 'AI analysis not available')}</p>
"""
        }
        
        # Send email using send_daily_summary method (which uses daily_summary template)
        result = email_client.send_daily_summary(team, summary_data)
        
        if result.get('success'):
            print(f'  ✅ Email sent successfully for {team.upper()} team!')
            return True
        else:
            print(f'  ❌ Email failed: {result.get("error")}')
            return False
            
    except Exception as e:
        print(f'  ❌ Email sending failed: {e}')
        return False


def main():
    """Main function for GitHub Actions"""
    print('🚀 Starting Daily Team Report Generation...')
    
    teams = ['toolchain', 'foa', 'assessment', 'boa']
    
    for team in teams:
        print(f'\n📊 Processing team: {team.upper()}')
        
        # Collect team data using existing MCP tools
        team_data = collect_team_data(team)
        
        # Generate AI analysis using existing MCP tools
        ai_summary = generate_ai_analysis(team_data)
        
        # Create email content
        email_body = create_email_content(team_data, ai_summary)
        
        # Send email using existing MCP email client
        send_email(team, email_body)
    
    print('\n🎉 Daily Team Report generation completed!')
    print('📧 Check your email for team reports!')


if __name__ == '__main__':
    main()
