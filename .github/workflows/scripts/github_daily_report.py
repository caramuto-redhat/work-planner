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
        
        # Find team channels - map channel IDs to descriptive names
        slack_channels = slack_config.get('slack_channels', {})
        team_channel_ids = [ch_id for ch_id, team_name in slack_channels.items() if team_name == team]
        
        # Map channel IDs to descriptive names based on comments in slack.yaml
        channel_name_mapping = {
            "C04JDFLHJN6": "team-toolchain-automotive",
            "C05BYR06B0V": "toolchain-infra", 
            "C04U16VAWL9": "toolchain-release-readiness",
            "C095CUUBNM9": "toolchain-sla",
            "C0910QFKTSN": "toolchain-AI",
            "C064MPL86N6": "toolchain-errata",
            "C0659G4HAF9": "team-auto-follow-on-activities",
            "C065HHG49QB": "team-auto-assessment", 
            "C04QNKX7RU4": "boa-team",
            "C06B9BCD456": "SP-RHIVOS"
        }
        
        team_channels = {ch_id: channel_name_mapping.get(ch_id, f"channel-{ch_id}") for ch_id in team_channel_ids}
        
        print(f'  📱 Found {len(team_channels)} channels for {team}: {list(team_channels.values())}')
        
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
                        # Filter messages from last 7 days from the most recent message
                        from datetime import datetime, timedelta
                        
                        # Find the timestamp of the most recent message
                        latest_timestamp = 0
                        for msg in messages:
                            try:
                                timestamp = float(msg.get('ts', '0'))
                                if timestamp > latest_timestamp:
                                    latest_timestamp = timestamp
                            except:
                                continue
                        
                        if latest_timestamp > 0:
                            # Calculate 7 days back from the most recent message
                            latest_message_date = datetime.fromtimestamp(latest_timestamp)
                            seven_days_ago = latest_message_date - timedelta(days=7)
                            
                            print(f'  📱 Latest message in {channel_name}: {latest_message_date.strftime("%Y-%m-%d %H:%M")}')
                            print(f'  📱 Looking for messages from: {seven_days_ago.strftime("%Y-%m-%d %H:%M")} onwards')
                            
                            recent_messages = []
                            for msg in messages:
                                try:
                                    timestamp = float(msg.get('ts', '0'))
                                    msg_date = datetime.fromtimestamp(timestamp)
                                    if msg_date >= seven_days_ago:
                                        recent_messages.append(msg)
                                except:
                                    continue
                            
                            print(f'  📱 Found {len(recent_messages)} messages from last 7 days in {channel_name}')
                        else:
                            print(f'  📱 No valid timestamps found in {channel_name}')
                            recent_messages = []
                        
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
                        print(f'  ✅ Successfully processed {channel_name} - stored in team_data')
                    else:
                        print(f'  ⚠️  No messages found in {channel_name}')
                        
                except Exception as e:
                    print(f'  ⚠️  Error processing channel {channel_id} ({channel_name}): {e}')
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
            
            # Get SP organization members for filtering
            organizations_config = jira_config.get('organizations', {})
            sp_members = organizations_config.get('SP', [])
            sp_members_str = '", "'.join(sp_members) if sp_members else ""
            
            # Team tickets with sprint information
            toolchain_jql = f'project = "Automotive Feature Teams" AND "AssignedTeam" = "{assigned_team}" AND status IN ("In Progress", "To Do", "In Review") ORDER BY updated DESC'
            print(f'  🎫 Team JQL: {toolchain_jql}')
            
            toolchain_issues = jira_client.search_issues(toolchain_jql)
            print(f'  🎫 Found {len(toolchain_issues)} team tickets')
            
            team_data['jira_tickets']['toolchain'] = toolchain_issues[:15]  # Limit to 15
            team_data['total_tickets'] += len(toolchain_issues)
            
            # SP organization tickets - filter by SP members AND team's AssignedTeam
            if sp_members_str:
                sp_jql = f'project = "Automotive Feature Teams" AND "AssignedTeam" = "{assigned_team}" AND assignee in ("{sp_members_str}") AND status IN ("In Progress", "To Do", "In Review") ORDER BY updated DESC'
                print(f'  🎫 SP Organization JQL: {sp_jql}')
                
                sp_issues = jira_client.search_issues(sp_jql)
                print(f'  🎫 Found {len(sp_issues)} SP organization tickets')
                
                team_data['jira_tickets']['sp_organization'] = sp_issues[:15]  # Limit to 15
                team_data['total_tickets'] += len(sp_issues)
            else:
                print(f'  ⚠️  No SP organization members found in config')
                team_data['jira_tickets']['sp_organization'] = []
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


def generate_paul_todo_items(team_data: Dict[str, Any], slack_client, jira_client, gemini_client) -> str:
    """Generate AI-powered TODO items for Paul Caramuto based on Slack and Jira mentions"""
    try:
        print(f'  📝 Generating Paul Caramuto TODO items...')
        
        # Collect Slack messages mentioning Paul (30 days back from latest message)
        paul_slack_content = []
        channels = team_data.get('channels', {})
        
        for channel_name, channel_data in channels.items():
            channel_id = channel_data.get('channel_id')
            messages = channel_data.get('recent_messages', [])
            
            if not channel_id or not messages:
                continue
                
            try:
                print(f'    📱 Checking {channel_name} for Paul mentions (30 days back)...')
                
                # Get messages from last 30 days from the most recent message
                from datetime import datetime, timedelta
                
                # Find the timestamp of the most recent message
                latest_timestamp = 0
                for msg in messages:
                    try:
                        timestamp = float(msg.get('ts', '0'))
                        if timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                    except:
                        continue
                
                if latest_timestamp > 0:
                    # Calculate 30 days back from the most recent message
                    latest_message_date = datetime.fromtimestamp(latest_timestamp)
                    thirty_days_ago = latest_message_date - timedelta(days=30)
                    
                    # Get all messages from the channel (not just recent ones)
                    all_messages = asyncio.run(slack_client.get_channel_history(channel_id))
                    
                    paul_messages = []
                    for msg in all_messages:
                        try:
                            timestamp = float(msg.get('ts', '0'))
                            msg_date = datetime.fromtimestamp(timestamp)
                            if msg_date >= thirty_days_ago:
                                # Check if message mentions Paul
                                text = msg.get('text', '')
                                if any(mention in text.lower() for mention in ['paul', 'pacaramu', '@paul', '@pacaramu']):
                                    paul_messages.append({
                                        'text': text,
                                        'user': msg.get('user', 'Unknown'),
                                        'timestamp': msg_date.isoformat(),
                                        'channel': channel_name
                                    })
                        except:
                            continue
                    
                    if paul_messages:
                        print(f'    📱 Found {len(paul_messages)} Paul mentions in {channel_name}')
                        paul_slack_content.extend(paul_messages)
                
            except Exception as e:
                print(f'    ⚠️  Error checking {channel_name} for Paul mentions: {e}')
                continue
        
        # Collect Jira tickets mentioning Paul
        paul_jira_content = []
        all_tickets = []
        
        # Get all team tickets
        team_tickets = team_data.get('jira_tickets', {}).get(team, [])
        all_tickets.extend(team_tickets)
        
        # Get SP organization tickets
        sp_tickets = team_data.get('jira_tickets', {}).get('SP', [])
        all_tickets.extend(sp_tickets)
        
        for ticket in all_tickets:
            if isinstance(ticket, dict):
                # Check various fields for Paul mentions
                fields_to_check = [
                    'summary', 'description', 'comment', 'assignee', 'reporter'
                ]
                
                paul_mentioned = False
                for field in fields_to_check:
                    field_value = ticket.get(field, '')
                    if isinstance(field_value, dict):
                        field_value = str(field_value)
                    elif field_value is None:
                        field_value = ''
                    else:
                        field_value = str(field_value)
                    
                    if any(mention in field_value.lower() for mention in ['paul', 'pacaramu']):
                        paul_mentioned = True
                        break
                
                if paul_mentioned:
                    paul_jira_content.append({
                        'key': ticket.get('key', 'N/A'),
                        'summary': ticket.get('summary', 'No summary'),
                        'status': ticket.get('status', {}).get('name', 'Unknown') if isinstance(ticket.get('status'), dict) else str(ticket.get('status', 'Unknown')),
                        'assignee': ticket.get('assignee', {}).get('displayName', 'Unassigned') if isinstance(ticket.get('assignee'), dict) else str(ticket.get('assignee', 'Unassigned')),
                        'url': ticket.get('url', '#')
                    })
        
        print(f'  📝 Found {len(paul_slack_content)} Slack mentions and {len(paul_jira_content)} Jira mentions')
        
        # Generate AI TODO items if we have content
        if paul_slack_content or paul_jira_content:
            # Prepare content for AI analysis
            slack_summary = ""
            if paul_slack_content:
                slack_summary = f"""
                Slack Messages Mentioning Paul (Last 30 Days):
                {chr(10).join([f"- [{msg['channel']}] {msg['user']}: {msg['text'][:200]}..." for msg in paul_slack_content[:10]])}
                """
            
            jira_summary = ""
            if paul_jira_content:
                jira_summary = f"""
                Jira Tickets Mentioning Paul:
                {chr(10).join([f"- {ticket['key']}: {ticket['summary']} (Status: {ticket['status']}, Assignee: {ticket['assignee']})" for ticket in paul_jira_content[:10]])}
                """
            
            # Generate TODO items using AI
            todo_prompt = f"""
            Based on the following Slack conversations and Jira tickets that mention Paul Caramuto, generate a concise TODO list of items that require Paul's attention.
            
            {slack_summary}
            {jira_summary}
            
            Please provide 3-5 specific, actionable TODO items in this format:
            1. [Priority] Action item description
            2. [Priority] Action item description
            3. [Priority] Action item description
            
            Use priorities: HIGH, MEDIUM, LOW
            Focus on items that require Paul's direct action or response.
            Keep each item concise but specific.
            """
            
            todo_items = gemini_client.generate_content(todo_prompt)
            return todo_items if todo_items else "No specific TODO items identified at this time."
        
        return "No mentions of Paul Caramuto found in the last 30 days."
        
    except Exception as e:
        print(f'  ❌ Paul TODO generation failed: {e}')
        return f"TODO generation failed: {str(e)}"


def create_email_content(team_data: Dict[str, Any], ai_summaries: Dict[str, str], paul_todo_items: str = "") -> str:
    """Create HTML email content with per-channel summaries and organized Jira tickets"""
    team = team_data['team']
    channels = team_data.get('channels', {})
    jira_tickets = team_data.get('jira_tickets', {})
    
    # Extract sprint information from tickets - check multiple possible field names
    def get_most_common_sprint(tickets):
        sprint_counts = {}
        for issue in tickets:
            if isinstance(issue, dict):
                sprint_name = None
                
                # Check for customfield_12310940 first (the actual sprint field from Jira)
                if 'customfield_12310940' in issue:
                    sprint_data = issue.get('customfield_12310940', [])
                    if sprint_data and len(sprint_data) > 0:
                        # Look for the ACTIVE sprint, not just the first one
                        import re
                        for sprint_string in sprint_data:
                            sprint_str = str(sprint_string)
                            # Check if this sprint is ACTIVE
                            state_match = re.search(r'state=([^,]+)', sprint_str)
                            if state_match and state_match.group(1) == 'ACTIVE':
                                # Extract sprint name from the active sprint
                                name_match = re.search(r'name=([^,]+)', sprint_str)
                                if name_match:
                                    sprint_name = name_match.group(1)
                                    break
                        
                        # If no active sprint found, fall back to first sprint
                        if not sprint_name:
                            sprint_string = str(sprint_data[0])
                            name_match = re.search(r'name=([^,]+)', sprint_string)
                            if name_match:
                                sprint_name = name_match.group(1)
                
                # Fallback to other sprint field names
                if not sprint_name:
                    sprint_fields_to_check = [
                        'Active Sprint',     # Exact field name from Jira UI
                        'customfield_10020', # Common Sprint field
                        'customfield_10021', # Alternative Sprint field
                        'sprint',           # Direct sprint field
                        'active_sprint',    # Snake case version
                        'activeSprint'      # Camel case version
                    ]
                    
                    for field_name in sprint_fields_to_check:
                        if field_name in issue:
                            sprint_data = issue.get(field_name, [])
                            if sprint_data and len(sprint_data) > 0:
                                if isinstance(sprint_data[0], dict):
                                    sprint_name = sprint_data[0].get('name', sprint_data[0].get('value', 'Unknown Sprint'))
                                else:
                                    sprint_name = str(sprint_data[0])
                                break
                
                if sprint_name and sprint_name != 'Unknown Sprint':
                    sprint_counts[sprint_name] = sprint_counts.get(sprint_name, 0) + 1
        
        if sprint_counts:
            return max(sprint_counts, key=sprint_counts.get)
        return None
    
    # Get sprint name from team tickets
    team_tickets = jira_tickets.get('toolchain', [])
    
    # Debug: Print available fields from first ticket
    if team_tickets and isinstance(team_tickets[0], dict):
        print(f'  🔍 Debug: Available fields in first ticket: {list(team_tickets[0].keys())}')
        sprint_fields_found = [field for field in team_tickets[0].keys() if 'sprint' in field.lower() or 'active' in field.lower()]
        print(f'  🔍 Debug: Sprint-related fields found: {sprint_fields_found}')
        
        # Debug: Check all possible sprint field names
        possible_sprint_fields = ['customfield_12310940', 'Active Sprint', 'customfield_10020', 'customfield_10021', 'sprint', 'Sprint']
        for field_name in possible_sprint_fields:
            if field_name in team_tickets[0]:
                field_value = team_tickets[0][field_name]
                print(f'  🔍 Debug: Found {field_name}: {field_value} (type: {type(field_value)})')
            else:
                print(f'  🔍 Debug: {field_name} NOT found')
        
        # Debug: Show ALL fields that might contain sprint info
        print(f'  🔍 Debug: All fields containing sprint/active:')
        for field_name, field_value in team_tickets[0].items():
            if 'sprint' in field_name.lower() or 'active' in field_name.lower():
                print(f'    {field_name}: {field_value}')
    
    active_sprint = get_most_common_sprint(team_tickets)
    print(f'  🔍 Debug: Detected active sprint: {active_sprint}')
    sprint_title_debug = f'🎫 Active Sprint "{active_sprint}" Tickets' if active_sprint else '🎫 Active Sprint Tickets'
    print(f'  🔍 Debug: Sprint title will be: {sprint_title_debug}')
    
    # Create sprint-aware section title
    sprint_title = f'🎫 Active Sprint "{active_sprint}" Tickets' if active_sprint else '🎫 Active Sprint Tickets'
    
    # Create channel summaries section with detailed activity
    channel_summaries_html = ""
    for channel_name, channel_data in channels.items():
        channel_summary = ai_summaries.get(channel_name, "No analysis available")
        recent_count = channel_data.get('recent_messages', 0)
        total_count = channel_data.get('total_messages', 0)
        messages = channel_data.get('messages', [])
        
        # Create recent messages preview
        recent_messages_html = ""
        if messages:
            recent_messages_html = "<div style='margin: 10px 0; max-height: 200px; overflow-y: auto;'>"
            for msg in messages[-5:]:  # Show last 5 messages
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
                        time_str = dt.strftime('%m-%d %H:%M')
                    except:
                        time_str = 'Unknown'
                else:
                    time_str = 'Unknown'
                
                # Clean text and truncate
                clean_text = _map_user_mentions_in_text(text, user_mapping, bot_mapping)
                clean_text = clean_text[:100] + "..." if len(clean_text) > 100 else clean_text
                
                recent_messages_html += f"""
                <div style='margin: 3px 0; padding: 5px; background: white; border-radius: 3px; font-size: 12px;'>
                    <strong>{time_str}</strong> <strong>{user_display_name}:</strong> {clean_text}
                </div>
                """
            recent_messages_html += "</div>"
        
        channel_summaries_html += f"""
        <div style="margin: 20px 0; padding: 20px; border-left: 4px solid #007acc; background: #f8f9fa; border-radius: 5px;">
            <h4 style="margin: 0 0 15px 0; color: #007acc; font-size: 16px;">📱 #{channel_name}</h4>
            
            <div style="margin: 10px 0;">
                <span style="background: #e3f2fd; padding: 4px 8px; border-radius: 12px; font-size: 11px; color: #1976d2;">
                    📊 {recent_count} messages (last 7 days) • {total_count} total
                </span>
            </div>
            
            <div style="margin: 15px 0;">
                <h5 style="margin: 0 0 8px 0; color: #333; font-size: 14px;">🤖 AI Summary:</h5>
                <p style="margin: 0; line-height: 1.4; font-style: italic; color: #555;">{channel_summary}</p>
            </div>
            
            {recent_messages_html if recent_messages_html else '<p style="color: #666; font-size: 12px;">No recent messages</p>'}
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
        
        # Sort tickets by priority: In Progress + Active Sprint first, then In Progress + No/Other Sprint
        def get_ticket_sort_key(issue):
            if not isinstance(issue, dict):
                return (2, '')  # Lowest priority for invalid tickets
            
            # Get status
            status = issue.get('status', {}).get('name', 'Unknown') if isinstance(issue.get('status'), dict) else str(issue.get('status', 'Unknown'))
            
            # Only process In Progress tickets (all tickets should be In Progress)
            if status != 'In Progress':
                return (2, issue.get('key', ''))  # Lowest priority for non-In Progress
            
            # Check for active sprint
            has_active_sprint = False
            if 'customfield_12310940' in issue:
                sprint_data = issue.get('customfield_12310940', [])
                if sprint_data and len(sprint_data) > 0:
                    import re
                    for sprint_string in sprint_data:
                        sprint_str = str(sprint_string)
                        state_match = re.search(r'state=([^,]+)', sprint_str)
                        if state_match and state_match.group(1) == 'ACTIVE':
                            has_active_sprint = True
                            break
            
            # Determine priority for In Progress tickets
            if has_active_sprint:
                return (0, issue.get('key', ''))  # Highest priority: In Progress + Active Sprint
            else:
                return (1, issue.get('key', ''))  # Lower priority: In Progress + No/Other Sprint
        
        # Sort tickets
        sorted_tickets = sorted(tickets, key=get_ticket_sort_key)
        
        tickets_html = f"""
        <div style="margin: 15px 0; padding: 15px; border-left: 4px solid {section_color}; background: #f8f9fa;">
            <h4 style="margin: 0 0 10px 0; color: {section_color};">{section_title} ({len(sorted_tickets)} tickets)</h4>
        """
        
        for issue in sorted_tickets[:10]:  # Limit to 10 tickets
            if isinstance(issue, dict):
                key = issue.get('key', 'N/A')
                assignee = issue.get('assignee', {}).get('displayName', 'Unassigned') if isinstance(issue.get('assignee'), dict) else str(issue.get('assignee', 'Unassigned'))
                summary = issue.get('summary', 'No summary')
                status = issue.get('status', {}).get('name', 'Unknown') if isinstance(issue.get('status'), dict) else str(issue.get('status', 'Unknown'))
                priority = issue.get('priority', {}).get('name', 'Medium') if isinstance(issue.get('priority'), dict) else str(issue.get('priority', 'Medium'))
                updated = issue.get('updated', 'Unknown')
                
                # Get sprint information - prioritize customfield_12310940 (actual sprint field)
                sprint_info = "No Sprint"
                
                # Check for customfield_12310940 first (the actual sprint field from Jira)
                if 'customfield_12310940' in issue:
                    sprint_data = issue.get('customfield_12310940', [])
                    if sprint_data and len(sprint_data) > 0:
                        # Look for the ACTIVE sprint, not just the first one
                        import re
                        for sprint_string in sprint_data:
                            sprint_str = str(sprint_string)
                            # Check if this sprint is ACTIVE
                            state_match = re.search(r'state=([^,]+)', sprint_str)
                            if state_match and state_match.group(1) == 'ACTIVE':
                                # Extract sprint name from the active sprint
                                name_match = re.search(r'name=([^,]+)', sprint_str)
                                if name_match:
                                    sprint_name = name_match.group(1)
                                    sprint_info = f"🏃 {sprint_name}"
                                    break
                        
                        # If no active sprint found, fall back to first sprint
                        if sprint_info == "No Sprint":
                            sprint_string = str(sprint_data[0])
                            name_match = re.search(r'name=([^,]+)', sprint_string)
                            if name_match:
                                sprint_name = name_match.group(1)
                                sprint_info = f"🏃 {sprint_name}"
                
                # Fallback to other sprint field names
                if sprint_info == "No Sprint":
                    sprint_fields_to_check = [
                        'Active Sprint',     # Exact field name from Jira UI
                        'customfield_10020', # Common Sprint field
                        'customfield_10021', # Alternative Sprint field
                        'sprint',           # Direct sprint field
                        'active_sprint',    # Snake case version
                        'activeSprint'      # Camel case version
                    ]
                    
                    for field_name in sprint_fields_to_check:
                        if field_name in issue:
                            sprint_data = issue.get(field_name, [])
                            if sprint_data and len(sprint_data) > 0:
                                if isinstance(sprint_data[0], dict):
                                    sprint_name = sprint_data[0].get('name', sprint_data[0].get('value', 'Unknown Sprint'))
                                else:
                                    sprint_name = str(sprint_data[0])
                                sprint_info = f"🏃 {sprint_name}"
                                break
                
                # Get project information
                project_key = issue.get('project', {}).get('key', 'Unknown') if isinstance(issue.get('project'), dict) else 'Unknown'
                
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
                <div style="margin: 8px 0; padding: 12px; background: white; border-radius: 4px; border-left: 3px solid {section_color};">
                    <div style="margin-bottom: 8px;">
                        <strong style="color: {section_color}; font-size: 14px;">{key}</strong>
                        <span style="background: #f0f0f0; padding: 2px 6px; border-radius: 10px; font-size: 10px; margin-left: 8px;">{project_key}</span>
                    </div>
                    <div style="margin-bottom: 6px; font-weight: 500;">{summary}</div>
                    <div style="font-size: 12px; color: #666;">
                        👤 {assignee} | 📊 {status} | ⚡ {priority} | 📅 {updated_str}
                    </div>
                    <div style="font-size: 11px; color: #888; margin-top: 4px;">
                        {sprint_info}
                    </div>
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
    
    # Team tickets section
    team_name = team_data['team'].upper()
    toolchain_tickets_html = format_jira_tickets(
        jira_tickets.get('toolchain', []), 
        f"🎫 {team_name} Team Tickets (In Progress)", 
        "#007acc"
    )
    
    # SP organization tickets section
    sp_tickets_html = format_jira_tickets(
        jira_tickets.get('sp_organization', []), 
        "🏢 SP Organization Tickets (In Progress)", 
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
    
    <div style="margin: 15px 0; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107;">
        <h3 style="margin: 0 0 10px 0;">📝 Paul Caramuto: TODO</h3>
        <div style="margin: 0; line-height: 1.4; white-space: pre-line;">{paul_todo_items}</div>
    </div>
    
    <h3>📱 Individual Slack Channel Activity (Last 7 Days)</h3>
    <p style="color: #666; font-size: 14px; margin-bottom: 20px;">
        Each channel shows AI analysis and recent message previews
    </p>
    {channel_summaries_html if channel_summaries_html else '<p>No channel activity found</p>'}
    
    <h3>{sprint_title}</h3>
    <p style="color: #666; font-size: 14px; margin-bottom: 20px;">
        Tickets organized by team and SP organization members
    </p>
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


def send_team_email(team: str, team_data: Dict[str, Any], ai_summaries: Dict[str, str], slack_client, jira_client, gemini_client) -> bool:
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
        
        # Generate Paul TODO items
        paul_todo_items = generate_paul_todo_items(team_data, slack_client, jira_client, gemini_client)
        
        # Create enhanced email content
        email_content = create_email_content(team_data, ai_summaries, paul_todo_items)
        
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
    gemini_client = GeminiClient(gemini_config)
    
    teams = ['toolchain', 'foa', 'assessment', 'boa']
    
    for team in teams:
        print(f'\n📊 Processing team: {team.upper()}')
        
        # Collect team data with per-channel structure
        team_data = collect_team_data(team)
        
        # Generate AI analysis for each channel and overall
        ai_summaries = generate_ai_analysis(team_data)
        
        # Send enhanced email with per-channel summaries and Paul TODO
        send_team_email(team, team_data, ai_summaries, slack_client, jira_client, gemini_client)
    
    print('\n🎉 Enhanced Daily Team Report generation completed!')
    print('📧 Check your email for detailed team reports with per-channel summaries and Paul TODO items!')


if __name__ == '__main__':
    main()
