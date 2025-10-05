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

async def _test_conversations_members(slack_client, channel_id: str) -> dict:
    """Test conversations.members API to see what user info we can get"""
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {slack_client.xoxc_token}",
            "Content-Type": "application/json",
        }
        cookies = {"d": slack_client.xoxd_token}
        
        url = f"{slack_client.base_url}/conversations.members"
        payload = {"channel": channel_id}
        
        print(f'  🔍 Testing conversations.members API for channel {channel_id}')
        print(f'  🔍 API request: {url}')
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, cookies=cookies, json=payload, timeout=10.0)
            print(f'  🔍 Response status: {response.status_code}')
            
            response.raise_for_status()
            data = response.json()
            print(f'  🔍 Response data: {data}')
            
            if data.get("ok"):
                members = data.get("members", [])
                print(f'  ✅ Found {len(members)} channel members')
                return {"success": True, "members": members, "response": data}
            else:
                print(f'  ❌ API error: {data.get("error", "Unknown error")}')
                return {"success": False, "error": data.get("error"), "response": data}
                    
    except Exception as e:
        print(f'  ❌ API exception: {e}')
        return {"success": False, "error": str(e)}

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
        
        print(f'  🔍 API request: {url} with user={user_id}')
        print(f'  🔍 Token prefix: {slack_client.xoxc_token[:10]}...')
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, cookies=cookies, json=payload, timeout=10.0)
            print(f'  🔍 Response status: {response.status_code}')
            print(f'  🔍 Response headers: {dict(response.headers)}')
            
            response.raise_for_status()
            data = response.json()
            print(f'  🔍 Response data: {data}')
            
            if data.get("ok"):
                user_info = data.get("user", {})
                print(f'  🔍 User info: {user_info}')
                
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
        return f"Unknown User"  # More user-friendly fallback

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
                    user_info_cache[user_id] = f"Unknown User"
            
            cached_name = user_info_cache[user_id]
            if cached_name != f"Unknown User":
                return f"@{cached_name}"
        
        # Final fallback
        return f"@Unknown User"
    
    # Replace <@USER_ID> patterns with display names
    clean_text = re.sub(r'<@([A-Z0-9]+)>', replace_mention, text)
    
    # Also clean up other Slack formatting
    clean_text = clean_text.replace('<', '&lt;').replace('>', '&gt;')
    
    return clean_text

def collect_team_data(team: str) -> Dict[str, Any]:
    """Collect Slack and Jira data for a team with per-channel summaries and organized tickets"""
    print(f'📊 Collecting data for team: {team.upper()}')
    
    # Initialize data structure
    team_data = {
        'team': team,
        'channels': {},  # Per-channel data
        'jira_tickets': {
            'toolchain': [],  # Toolchain team tickets
            'sp_organization': []  # SP organization tickets
        },
        'total_messages': 0,
        'total_tickets': 0
    }
    
    # Collect Slack data per channel
    try:
        print(f'  📱 Collecting Slack data...')
        from connectors.slack.client import SlackClient
        from connectors.slack.config import SlackConfig
        
        slack_config = SlackConfig.load('config/slack.yaml')
        slack_client = SlackClient(slack_config)
        
        # Find team channels
        slack_channels = slack_config.get('slack_channels', {})
        team_channels = {ch_id: ch_name for ch_id, ch_name in slack_channels.items() if ch_name == team}
        
        print(f'  📱 Found {len(team_channels)} channels for {team}')
        
        # Get user mappings
        user_mapping = slack_config.get('user_display_names', {})
        bot_mapping = slack_config.get('bot_display_names', {})
        unknown_users = slack_config.get('unknown_users', {})
        user_mapping.update(unknown_users)
        
        if team_channels:
            import asyncio
            
            for channel_id, channel_name in team_channels.items():
                try:
                    print(f'  📱 Processing channel: {channel_name} ({channel_id})')
                    
                    # Get messages from last 7 days
                    messages = asyncio.run(slack_client.get_channel_history(channel_id))
                    print(f'  📱 Retrieved {len(messages)} messages from {channel_name}')
                    
                    if messages:
                        # Filter messages from last 7 days
                        from datetime import datetime, timedelta
                        seven_days_ago = datetime.now() - timedelta(days=7)
                        
                        recent_messages = []
                        for msg in messages:
                            try:
                                timestamp = float(msg.get('ts', '0'))
                                msg_date = datetime.fromtimestamp(timestamp)
                                if msg_date >= seven_days_ago:
                                    recent_messages.append(msg)
                            except:
                                continue
                        
                        print(f'  📱 Found {len(recent_messages)} messages from last 7 days')
                        
                        # Store channel data
                        team_data['channels'][channel_name] = {
                            'channel_id': channel_id,
                            'total_messages': len(messages),
                            'recent_messages': len(recent_messages),
                            'messages': recent_messages[-20:] if recent_messages else [],  # Last 20 for AI analysis
                            'user_mapping': user_mapping,
                            'bot_mapping': bot_mapping
                        }
                        
                        team_data['total_messages'] += len(recent_messages)
                        
                except Exception as e:
                    print(f'  ⚠️  Error processing channel {channel_id}: {e}')
                    continue
                    
    except Exception as e:
        print(f'  ❌ Slack collection failed: {e}')
    
    # Collect Jira data organized by team vs SP organization
    try:
        print(f'  🎫 Collecting Jira data...')
        from connectors.jira.client import JiraClient
        from connectors.jira.config import JiraConfig
        
        jira_config = JiraConfig.load('config/jira.yaml')
        jira_client = JiraClient(jira_config)
        
        # Toolchain team tickets
        teams_config = jira_config.get('teams', {})
        team_config = teams_config.get(team, {})
        
        if team_config:
            assigned_team = team_config.get('assigned_team', '')
            
            # Toolchain team tickets
            toolchain_jql = f'project = "Automotive Feature Teams" AND "AssignedTeam" = "{assigned_team}" AND status IN ("In Progress", "To Do", "In Review")'
            print(f'  🎫 Toolchain JQL: {toolchain_jql}')
            
            toolchain_issues = jira_client.search_issues(toolchain_jql)
            print(f'  🎫 Found {len(toolchain_issues)} toolchain tickets')
            
            team_data['jira_tickets']['toolchain'] = toolchain_issues[:15]  # Limit to 15
            team_data['total_tickets'] += len(toolchain_issues)
            
            # SP organization tickets (different project/filter)
            sp_jql = f'project = "SP-RHIVOS" AND status IN ("In Progress", "To Do", "In Review")'
            print(f'  🎫 SP Organization JQL: {sp_jql}')
            
            sp_issues = jira_client.search_issues(sp_jql)
            print(f'  🎫 Found {len(sp_issues)} SP organization tickets')
            
            team_data['jira_tickets']['sp_organization'] = sp_issues[:15]  # Limit to 15
            team_data['total_tickets'] += len(sp_issues)
        else:
            print(f'  ⚠️  No team config found for {team}')
            
    except Exception as e:
        print(f'  ❌ Jira collection failed: {e}')
    
    return team_data


def generate_ai_analysis(team_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate AI analysis for each channel and overall team summary"""
    try:
        print(f'  🤖 Generating AI analysis for {team_data["team"]}...')
        from connectors.gemini.client import GeminiClient
        from connectors.gemini.config import GeminiConfig
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        
        channel_summaries = {}
        
        # Generate per-channel summaries
        for channel_name, channel_data in team_data.get('channels', {}).items():
            try:
                print(f'  🤖 Analyzing channel: {channel_name}')
                
                messages = channel_data.get('messages', [])
                if not messages:
                    channel_summaries[channel_name] = f"No recent activity in {channel_name}"
                    continue
                
                # Prepare messages for AI analysis
                message_texts = []
                for msg in messages:
                    user_id = msg.get('user', 'Unknown')
                    text = msg.get('text', 'No text')
                    timestamp = msg.get('ts', '')
                    
                    # Get user display name
                    user_mapping = channel_data.get('user_mapping', {})
                    bot_mapping = channel_data.get('bot_mapping', {})
                    user_display_name = user_mapping.get(user_id, bot_mapping.get(user_id, f"User {user_id}"))
                    
                    # Format timestamp
                    if timestamp:
                        try:
                            from datetime import datetime
                            dt = datetime.fromtimestamp(float(timestamp))
                            time_str = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            time_str = 'Unknown'
                    else:
                        time_str = 'Unknown'
                    
                    # Clean text
                    clean_text = _map_user_mentions_in_text(text, user_mapping, bot_mapping)
                    message_texts.append(f"[{time_str}] {user_display_name}: {clean_text}")
                
                # Create AI prompt for channel
                prompt = f"""
                Analyze the last 7 days of activity in the Slack channel "{channel_name}" for the {team_data["team"]} team.
                
                Recent Messages ({len(messages)} messages):
                {chr(10).join(message_texts[-10:])}
                
                Please provide a concise summary (2-3 sentences) covering:
                1. Main topics and discussions
                2. Key decisions or updates
                3. Any blockers or issues
                4. Team collaboration patterns
                
                Focus on actionable insights and important developments.
                """
                
                # Generate AI summary
                summary = gemini_client.generate_content(prompt)
                channel_summaries[channel_name] = summary if summary else f"AI analysis completed for {channel_name}"
                
            except Exception as e:
                print(f'  ⚠️  AI analysis failed for {channel_name}: {e}')
                channel_summaries[channel_name] = f"AI analysis not available for {channel_name}"
        
        # Generate overall team summary
        try:
            print(f'  🤖 Generating overall team summary...')
            
            # Prepare overall prompt
            total_messages = team_data.get('total_messages', 0)
            total_tickets = team_data.get('total_tickets', 0)
            channel_count = len(team_data.get('channels', {}))
            
            overall_prompt = f"""
            Provide an executive summary for the {team_data["team"]} team based on the last 7 days of activity:
            
            Team Activity Overview:
            - {total_messages} messages across {channel_count} channels
            - {total_tickets} active Jira tickets
            
            Channel Summaries:
            {chr(10).join([f"- {ch}: {summary}" for ch, summary in channel_summaries.items()])}
            
            Please provide a high-level summary (2-3 sentences) covering:
            1. Overall team productivity and focus areas
            2. Key accomplishments or milestones
            3. Any concerns or areas needing attention
            
            Keep it concise and executive-friendly.
            """
            
            overall_summary = gemini_client.generate_content(overall_prompt)
            channel_summaries['overall'] = overall_summary if overall_summary else "Overall team analysis completed"
            
        except Exception as e:
            print(f'  ⚠️  Overall AI analysis failed: {e}')
            channel_summaries['overall'] = "Overall team analysis not available"
        
        return channel_summaries
        
    except Exception as e:
        print(f'  ❌ AI analysis failed: {e}')
        return {'overall': 'AI analysis not available'}


def create_email_content(team_data: Dict[str, Any], ai_summaries: Dict[str, str]) -> str:
    """Create HTML email content with per-channel summaries and organized Jira tickets"""
    team = team_data['team']
    channels = team_data.get('channels', {})
    jira_tickets = team_data.get('jira_tickets', {})
    
    # Create channel summaries section
    channel_summaries_html = ""
    for channel_name, channel_data in channels.items():
        channel_summary = ai_summaries.get(channel_name, "No analysis available")
        recent_count = channel_data.get('recent_messages', 0)
        total_count = channel_data.get('total_messages', 0)
        
        channel_summaries_html += f"""
        <div style="margin: 15px 0; padding: 15px; border-left: 4px solid #007acc; background: #f8f9fa;">
            <h4 style="margin: 0 0 10px 0; color: #007acc;">📱 #{channel_name}</h4>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">
                <strong>Activity:</strong> {recent_count} messages in last 7 days ({total_count} total)
            </p>
            <p style="margin: 10px 0; line-height: 1.4;">{channel_summary}</p>
        </div>
        """
    
    # Create Jira tickets sections
    def format_jira_tickets(tickets, section_title, section_color):
        if not tickets:
            return f"""
            <div style="margin: 15px 0; padding: 15px; border-left: 4px solid {section_color}; background: #f8f9fa;">
                <h4 style="margin: 0 0 10px 0; color: {section_color};">{section_title}</h4>
                <p style="margin: 0; color: #666;">No active tickets found</p>
            </div>
            """
        
        tickets_html = f"""
        <div style="margin: 15px 0; padding: 15px; border-left: 4px solid {section_color}; background: #f8f9fa;">
            <h4 style="margin: 0 0 10px 0; color: {section_color};">{section_title} ({len(tickets)} tickets)</h4>
        """
        
        for issue in tickets[:10]:  # Limit to 10 tickets
            if isinstance(issue, dict):
                key = issue.get('key', 'N/A')
                assignee = issue.get('assignee', {}).get('displayName', 'Unassigned') if isinstance(issue.get('assignee'), dict) else str(issue.get('assignee', 'Unassigned'))
                summary = issue.get('summary', 'No summary')
                status = issue.get('status', {}).get('name', 'Unknown') if isinstance(issue.get('status'), dict) else str(issue.get('status', 'Unknown'))
                priority = issue.get('priority', {}).get('name', 'Medium') if isinstance(issue.get('priority'), dict) else str(issue.get('priority', 'Medium'))
                updated = issue.get('updated', 'Unknown')
                
                # Format updated date
                if updated != 'Unknown':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        updated_str = dt.strftime('%Y-%m-%d')
                    except:
                        updated_str = updated
                else:
                    updated_str = 'Unknown'
                
                tickets_html += f"""
                <div style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px;">
                    <strong>{key}</strong> - {summary}<br>
                    <small style="color: #666;">👤 {assignee} | 📊 {status} | ⚡ {priority} | 📅 {updated_str}</small>
                </div>
                """
            else:
                tickets_html += f"""
                <div style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px;">
                    <strong>{str(issue)}</strong>
                </div>
                """
        
        tickets_html += "</div>"
        return tickets_html
    
    # Toolchain tickets section
    toolchain_tickets_html = format_jira_tickets(
        jira_tickets.get('toolchain', []), 
        "🎫 Toolchain Team Tickets", 
        "#007acc"
    )
    
    # SP organization tickets section
    sp_tickets_html = format_jira_tickets(
        jira_tickets.get('sp_organization', []), 
        "🏢 SP Organization Tickets", 
        "#28a745"
    )
    
    # Overall AI summary
    overall_summary = ai_summaries.get('overall', 'Overall analysis not available')
    
    # Create the complete HTML content
    html_content = f"""
    <h2>📊 {team.upper()} Team Daily Report</h2>
    
    <div style="margin: 15px 0; padding: 15px; background: #e8f4fd; border-left: 4px solid #007acc;">
        <h3 style="margin: 0 0 10px 0;">🤖 Executive Summary</h3>
        <p style="margin: 0; line-height: 1.4;">{overall_summary}</p>
    </div>
    
    <h3>📱 Slack Channel Activity (Last 7 Days)</h3>
    {channel_summaries_html if channel_summaries_html else '<p>No channel activity found</p>'}
    
    <h3>🎫 Active Sprint Tickets</h3>
    {toolchain_tickets_html}
    {sp_tickets_html}
    
    <hr style="margin: 30px 0;">
    <p style="font-size: 12px; color: #666; text-align: center;">
        Generated by Work Planner MCP Server | {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
    </p>
    """
    
    return html_content


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


def send_team_email(team: str, team_data: Dict[str, Any], ai_summaries: Dict[str, str]) -> bool:
    """Send email for team using enhanced format with per-channel summaries"""
    try:
        print(f'  📧 Sending enhanced email for {team.upper()} team...')
        from connectors.email.client import EmailClient
        from connectors.email.config import EmailConfig
        
        email_config = EmailConfig()
        config = email_config.get_config()
        
        # Validate config before creating client
        if not email_config.validate_config():
            print(f'  ❌ Email config validation failed')
            return False
            
        email_client = EmailClient(config)
        
        # Create enhanced email content
        email_content = create_email_content(team_data, ai_summaries)
        
        # Prepare summary data for daily_summary template
        summary_data = {
            'content': email_content
        }
        
        # Send email using send_daily_summary method
        result = email_client.send_daily_summary(team, summary_data)
        
        if result.get('success'):
            print(f'  ✅ Enhanced email sent successfully for {team.upper()} team!')
            return True
        else:
            print(f'  ❌ Email failed: {result.get("error")}')
            return False
            
    except Exception as e:
        print(f'  ❌ Email sending failed: {e}')
        return False


def main():
    """Main function for GitHub Actions with enhanced reporting"""
    print('🚀 Starting Enhanced Daily Team Report Generation...')
    
    teams = ['toolchain', 'foa', 'assessment', 'boa']
    
    for team in teams:
        print(f'\n📊 Processing team: {team.upper()}')
        
        # Collect team data with per-channel structure
        team_data = collect_team_data(team)
        
        # Generate AI analysis for each channel and overall
        ai_summaries = generate_ai_analysis(team_data)
        
        # Send enhanced email with per-channel summaries
        send_team_email(team, team_data, ai_summaries)
    
    print('\n🎉 Enhanced Daily Team Report generation completed!')
    print('📧 Check your email for detailed team reports with per-channel summaries!')


if __name__ == '__main__':
    main()
