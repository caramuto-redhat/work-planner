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

# Suppress gRPC/absl warnings from Gemini client
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['GRPC_POLL_STRATEGY'] = 'poll'
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '0'

# Suppress absl logging warnings
import logging
logging.getLogger('absl').setLevel(logging.ERROR)

# Add project root to Python path so we can import connectors
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

print(f'🔍 Project root: {project_root}')
print(f'🔍 Python path: {sys.path[:3]}...')

async def _get_user_display_name(slack_client, user_id: str, user_mapping: dict, bot_mapping: dict) -> str:
    """Get user display name from Slack API or fallback to mapping"""
    try:
        # Try to get user info from Slack API
        import httpx
        
        headers = {
            "Authorization": f"Bearer {slack_client.xoxc_token}",
            "Content-Type": "application/json",
        }
        cookies = {"d": slack_client.xoxd_token}
        
        url = f"{slack_client.base_url}/users.info"
        payload = {"user": user_id}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, cookies=cookies, json=payload, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                user_info = data.get("user", {})
                # Try different name fields in order of preference
                display_name = (user_info.get("profile", {}).get("display_name") or 
                              user_info.get("profile", {}).get("real_name") or 
                              user_info.get("name") or 
                              user_info.get("real_name"))
                
                if display_name:
                    print(f'  ✅ API success for {user_id}: {display_name}')
                    return display_name
                else:
                    print(f'  ⚠️  API returned no display name for {user_id}')
            else:
                print(f'  ⚠️  API error for {user_id}: {data.get("error", "Unknown error")}')
                    
    except Exception as e:
        print(f'  ❌ API exception for {user_id}: {e}')
    
    # Fallback to manual mapping
    if user_id in user_mapping:
        print(f'  📋 Using manual mapping for {user_id}: {user_mapping[user_id]}')
        return user_mapping[user_id]
    elif user_id in bot_mapping:
        print(f'  🤖 Using bot mapping for {user_id}: {bot_mapping[user_id]}')
        return bot_mapping[user_id]
    else:
        print(f'  ❌ No mapping found for {user_id}, using fallback')
        return f"User {user_id}"  # Final fallback

def _map_user_mentions_in_text(text: str, user_mapping: dict, bot_mapping: dict, slack_client=None, user_info_cache=None) -> str:
    """Map user mentions in message text from <@USER_ID> to display names"""
    import re
    
    def replace_mention(match):
        user_id = match.group(1)
        
        # Try manual mapping first (fastest)
        if user_id in user_mapping:
            return f"@{user_mapping[user_id]}"
        elif user_id in bot_mapping:
            return f"@{bot_mapping[user_id]}"
        
        # Try Slack API if available (for unmapped users)
        if slack_client and user_info_cache is not None:
            if user_id not in user_info_cache:
                try:
                    import asyncio
                    print(f'  🔍 API lookup for mention {user_id}...')
                    display_name = asyncio.run(_get_user_display_name(slack_client, user_id, user_mapping, bot_mapping))
                    user_info_cache[user_id] = display_name
                except Exception as e:
                    print(f'  ❌ API lookup failed for mention {user_id}: {e}')
                    user_info_cache[user_id] = f"User {user_id}"
            
            cached_name = user_info_cache[user_id]
            if cached_name != f"User {user_id}":
                return f"@{cached_name}"
        
        # Final fallback
        return f"@User {user_id}"
    
    # Replace <@USER_ID> patterns with display names
    clean_text = re.sub(r'<@([A-Z0-9]+)>', replace_mention, text)
    
    # Also clean up other Slack formatting
    clean_text = clean_text.replace('<', '&lt;').replace('>', '&gt;')
    
    return clean_text

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
            # Call Slack API directly to avoid MCP tool async issues
            import asyncio
            
            for channel_id in team_channels:
                try:
                    print(f'  📱 Processing channel: {channel_id}')
                    
                    # Call Slack API directly using async
                    try:
                        messages = asyncio.run(slack_client.get_channel_history(channel_id))
                        print(f'  📱 Retrieved {len(messages)} messages from {channel_id}')
                        
                        if messages:
                            slack_data['messages_count'] = len(messages)
                            slack_data['summary'] = f'📱 {len(messages)} messages from {len(team_channels)} channels'
                            
                            # Get recent messages for summary (inspired by jira-report-mpc)
                            recent_messages = messages[-10:] if messages else []
                            
                            # Get user and bot mapping from config (fallback)
                            user_mapping = slack_config.get('user_display_names', {})
                            bot_mapping = slack_config.get('bot_display_names', {})
                            
                            # Cache for user info to avoid repeated API calls
                            user_info_cache = {}
                            
                            print(f'  📱 Using user mapping with {len(user_mapping)} users and {len(bot_mapping)} bots')
                            
                            for msg in recent_messages:
                                user_id = msg.get('user', 'Unknown')
                                text = msg.get('text', 'No text')
                                timestamp = msg.get('ts', '')
                                
                                # Get user display name (try API first, then fallback to mapping)
                                if user_id not in user_info_cache:
                                    print(f'  🔍 API lookup for sender {user_id}...')
                                    user_display_name = asyncio.run(_get_user_display_name(slack_client, user_id, user_mapping, bot_mapping))
                                    user_info_cache[user_id] = user_display_name
                                else:
                                    user_display_name = user_info_cache[user_id]
                                
                                # Format timestamp
                                if timestamp:
                                    try:
                                        from datetime import datetime
                                        dt = datetime.fromtimestamp(float(timestamp))
                                        time_str = dt.strftime('%H:%M')
                                    except:
                                        time_str = 'Unknown'
                                else:
                                    time_str = 'Unknown'
                                
                                # Clean up text and map user mentions
                                clean_text = _map_user_mentions_in_text(text, user_mapping, bot_mapping, slack_client, user_info_cache)
                                slack_data['details'].append(f'[{time_str}] {user_display_name}: {clean_text[:150]}...')
                            break
                        else:
                            print(f'  ⚠️  No messages found in channel {channel_id}')
                            
                    except Exception as async_error:
                        print(f'  ⚠️  Async error for channel {channel_id}: {async_error}')
                        continue
                        
                except Exception as e:
                    print(f'  ⚠️  Slack channel {channel_id}: {e}')
                    continue
                    
    except Exception as e:
        print(f'  ❌ Slack collection failed: {e}')
    
    # Collect Jira data directly (bypassing MCP tools)
    try:
        print(f'  🎫 Attempting to import Jira client...')
        from connectors.jira.client import JiraClient
        from connectors.jira.config import JiraConfig
        
        print(f'  🎫 Successfully imported Jira client')
        
        jira_config = JiraConfig.load('config/jira.yaml')
        jira_client = JiraClient(jira_config)
        
        print(f'  🎫 Collecting Jira data for {team}...')
        
        # Build JQL query for team
        teams_config = jira_config.get('teams', {})
        team_config = teams_config.get(team, {})
        if not team_config:
            print(f'  ⚠️  No team config found for {team}')
            return jira_data
            
        assigned_team = team_config.get('assigned_team', '')
        jql_query = f'project = "Automotive Feature Teams" AND "AssignedTeam" = "{assigned_team}" AND status IN ("In Progress", "To Do", "In Review")'
        
        print(f'  🎫 Using JQL: {jql_query}')
        
        # Call Jira API directly
        issues = jira_client.search_issues(jql_query)
        print(f'  🎫 Found {len(issues)} issues for {team}')
        
        if issues:
            jira_data['issues_count'] = len(issues)
            jira_data['summary'] = f'🎫 {len(issues)} tickets in progress'
            
            # Format ticket details (inspired by jira-report-mpc)
            for issue in issues[:10]:  # Limit to 10 most recent
                # Handle both dict and string issue formats
                if isinstance(issue, dict):
                    key = issue.get('key', 'N/A')
                    assignee = issue.get('assignee', {}).get('displayName', 'Unassigned') if isinstance(issue.get('assignee'), dict) else str(issue.get('assignee', 'Unassigned'))
                    summary = issue.get('summary', 'No summary')
                    status = issue.get('status', {}).get('name', 'Unknown') if isinstance(issue.get('status'), dict) else str(issue.get('status', 'Unknown'))
                    updated = issue.get('updated', 'Unknown')
                    priority = issue.get('priority', {}).get('name', 'Medium') if isinstance(issue.get('priority'), dict) else str(issue.get('priority', 'Medium'))
                else:
                    # If issue is a string, use it as-is
                    key = str(issue)
                    assignee = 'Unknown'
                    summary = str(issue)
                    status = 'Unknown'
                    updated = 'Unknown'
                    priority = 'Medium'
                
                # Format updated date
                if updated != 'Unknown':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        updated_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        updated_str = updated
                else:
                    updated_str = 'Unknown'
                
                ticket_info = f"""
==========
Issue: {key}
({jira_config.get('jira_url', '')}/browse/{key})
Owner: {assignee}
Summary: {summary}
Status: {status} | Priority: {priority}
Updated: {updated_str}
"""
                jira_data['details'].append(ticket_info.strip())
        else:
            print(f'  ⚠️  No issues found for {team}')
            
    except Exception as e:
        print(f'  ❌ Jira collection failed: {e}')
    
    return {
        'team': team,
        'slack_summary': slack_data.get('summary', 'No Slack data available'),
        'slack_details': slack_data.get('details', []),
        'jira_summary': jira_data.get('summary', 'No Jira data available'),
        'jira_details': jira_data.get('details', [])
    }


def generate_ai_analysis(team_data: Dict[str, Any]) -> str:
    """Generate AI analysis using existing Gemini tools"""
    try:
        print(f'  🤖 Attempting to import Gemini client...')
        from connectors.gemini.client import GeminiClient
        from connectors.gemini.config import GeminiConfig
        
        print(f'  🤖 Successfully imported Gemini client')
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        
        print(f'  🤖 Generating AI summary for {team_data["team"]}...')
        
        # Prepare data for AI analysis
        slack_summary = team_data.get('slack_summary', 'No Slack data available')
        jira_summary = team_data.get('jira_summary', 'No Jira data available')
        slack_details = team_data.get('slack_details', [])
        jira_details = team_data.get('jira_details', [])
        
        # Create detailed prompt with actual data
        prompt = f"""
        Analyze the following team data for {team_data["team"]} team:
        
        SLACK ACTIVITY:
        {slack_summary}
        
        Recent Messages:
        {chr(10).join(slack_details[:5]) if slack_details else 'No recent messages'}
        
        JIRA TICKETS:
        {jira_summary}
        
        Ticket Details:
        {chr(10).join(jira_details[:5]) if jira_details else 'No tickets found'}
        
        Please provide:
        1. A brief summary of team activity
        2. Any blockers or issues identified
        3. Suggestions for improvement
        4. Key accomplishments
        
        Keep it concise and actionable (2-3 sentences max).
        """
        
        # Call Gemini API directly
        result = gemini_client.generate_content(prompt)
        print(f'  🤖 AI analysis completed')
        
        return result if result else 'AI analysis completed'
            
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
        
        # Prepare summary data for daily_summary template (inspired by jira-report-mpc)
        slack_details_html = ''.join(f'<p style="margin: 5px 0; font-family: monospace; font-size: 12px;">{detail}</p>' for detail in team_data.get('slack_details', []))
        jira_details_html = ''.join(f'<pre style="background: #f5f5f5; padding: 10px; margin: 5px 0; border-left: 3px solid #007acc;">{detail}</pre>' for detail in team_data.get('jira_details', []))
        
        summary_data = {
            'content': f"""
<h3>📱 Slack Activity</h3>
<p><strong>{team_data.get('slack_summary', 'No Slack data available')}</strong></p>
{slack_details_html if slack_details_html else '<p>No recent messages</p>'}

<h3>🎫 Jira Tickets - In Progress</h3>
<p><strong>{team_data.get('jira_summary', 'No Jira data available')}</strong></p>
{jira_details_html if jira_details_html else '<p>No tickets found</p>'}

<h3>🤖 AI Analysis</h3>
<p style="background: #e8f4fd; padding: 15px; border-left: 4px solid #007acc; margin: 10px 0;">{team_data.get('ai_summary', 'AI analysis not available')}</p>
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


def send_team_email(team: str, team_data: Dict[str, Any]) -> bool:
    """Send email for team using existing MCP email client"""
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
        
        # Prepare summary data for daily_summary template (inspired by jira-report-mpc)
        slack_details_html = ''.join(f'<p style="margin: 5px 0; font-family: monospace; font-size: 12px;">{detail}</p>' for detail in team_data.get('slack_details', []))
        jira_details_html = ''.join(f'<pre style="background: #f5f5f5; padding: 10px; margin: 5px 0; border-left: 3px solid #007acc;">{detail}</pre>' for detail in team_data.get('jira_details', []))
        
        summary_data = {
            'content': f"""
<h3>📱 Slack Activity</h3>
<p><strong>{team_data.get('slack_summary', 'No Slack data available')}</strong></p>
{slack_details_html if slack_details_html else '<p>No recent messages</p>'}

<h3>🎫 Jira Tickets - In Progress</h3>
<p><strong>{team_data.get('jira_summary', 'No Jira data available')}</strong></p>
{jira_details_html if jira_details_html else '<p>No tickets found</p>'}

<h3>🤖 AI Analysis</h3>
<p style="background: #e8f4fd; padding: 15px; border-left: 4px solid #007acc; margin: 10px 0;">{team_data.get('ai_summary', 'AI analysis not available')}</p>
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
        team_data['ai_summary'] = ai_summary
        
        # Send email using existing MCP email client
        send_team_email(team, team_data)
    
    print('\n🎉 Daily Team Report generation completed!')
    print('📧 Check your email for team reports!')


if __name__ == '__main__':
    main()
