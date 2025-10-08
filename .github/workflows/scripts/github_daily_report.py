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

def _load_time_ranges_config():
    """Load time ranges configuration from mail_template.yaml"""
    try:
        import yaml
        with open('config/mail_template.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config.get('time_ranges', {})
    except Exception as e:
        print(f'  ⚠️  Warning: Could not load time ranges config: {e}')
        # Fallback to default values
        return {
            'slack': {
                'channel_activity_days': 7,
                'history_collection_days': 30,
                'paul_todo_search_days': 30,
                'max_messages_for_analysis': 10
            },
            'jira': {
                'ticket_limit_per_team': 15,
                'ticket_limit_per_org': 10,
                'max_tickets_for_analysis': 20
            }
        }


def collect_team_data(team: str) -> Dict[str, Any]:
    """Collect Slack and Jira data for a team with per-channel summaries and organized tickets"""
    print(f'📊 Collecting data for team: {team.upper()}')
    
    # Load time ranges configuration
    time_ranges = _load_time_ranges_config()
    slack_config = time_ranges.get('slack', {})
    jira_config = time_ranges.get('jira', {})
    
    # Initialize data structure
    team_data = {
        'team': team,
        'channels': {},  # Per-channel data
        'jira_tickets': {
            'toolchain': [],  # Toolchain team tickets
            'sp_organization': []  # SP organization tickets
        },
        'total_messages': 0,
        'total_tickets': 0,
        'time_ranges': time_ranges  # Include config for template use
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
                        # Filter messages using configurable time range
                        from datetime import datetime, timedelta
                        
                        # Get configurable time range
                        activity_days = slack_config.get('channel_activity_days', 7)
                        
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
                            # Calculate configurable days back from the most recent message
                            latest_message_date = datetime.fromtimestamp(latest_timestamp)
                            activity_cutoff = latest_message_date - timedelta(days=activity_days)
                            
                            print(f'  📱 Latest message in {channel_name}: {latest_message_date.strftime("%Y-%m-%d %H:%M")}')
                            print(f'  📱 Looking for messages from: {activity_cutoff.strftime("%Y-%m-%d %H:%M")} onwards (last {activity_days} days)')
                            
                            recent_messages = []
                            for msg in messages:
                                try:
                                    timestamp = float(msg.get('ts', '0'))
                                    msg_date = datetime.fromtimestamp(timestamp)
                                    if msg_date >= activity_cutoff:
                                        recent_messages.append(msg)
                                except:
                                    continue
                            
                            print(f'  📱 Found {len(recent_messages)} messages from last {activity_days} days in {channel_name}')
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
            
            # Use configurable ticket limit
            ticket_limit = jira_config.get('ticket_limit_per_team', 15)
            team_data['jira_tickets']['toolchain'] = toolchain_issues[:ticket_limit]
            team_data['total_tickets'] += len(toolchain_issues)
            
            # SP organization tickets - filter by SP members AND team's AssignedTeam
            if sp_members_str:
                sp_jql = f'project = "Automotive Feature Teams" AND "AssignedTeam" = "{assigned_team}" AND assignee in ("{sp_members_str}") AND status IN ("In Progress", "To Do", "In Review") ORDER BY updated DESC'
                print(f'  🎫 SP Organization JQL: {sp_jql}')
                
                sp_issues = jira_client.search_issues(sp_jql)
                print(f'  🎫 Found {len(sp_issues)} SP organization tickets')
                
                # Use configurable ticket limit for SP organization
                sp_ticket_limit = jira_config.get('ticket_limit_per_org', 10)
                team_data['jira_tickets']['sp_organization'] = sp_issues[:sp_ticket_limit]
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
        
        # Get configurable message limits
        time_ranges = team_data.get('time_ranges', {})
        slack_config = time_ranges.get('slack', {})
        max_messages = slack_config.get('max_messages_for_analysis', 10)
        
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
                Analyze the last {slack_config.get('channel_activity_days', 7)} days of activity in the Slack channel "{channel_name}" for the {team_data["team"]} team.
                
                Recent Messages ({len(messages)} messages):
                {chr(10).join(message_texts[-max_messages:])}
                
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
            
            # Get configurable ticket limit for AI analysis
            jira_config = time_ranges.get('jira', {})
            max_tickets_for_ai = jira_config.get('max_tickets_for_analysis', 20)
            
            # Limit tickets for AI analysis
            all_tickets = []
            toolchain_tickets = team_data.get('jira_tickets', {}).get('toolchain', [])
            sp_tickets = team_data.get('jira_tickets', {}).get('sp_organization', [])
            all_tickets.extend(toolchain_tickets)
            all_tickets.extend(sp_tickets)
            
            # Take only the most recent tickets for AI analysis
            tickets_for_ai = all_tickets[:max_tickets_for_ai]
            
            overall_prompt = f"""
            Provide an executive summary for the {team_data["team"]} team based on the last {slack_config.get('channel_activity_days', 7)} days of activity:
            
            Team Activity Overview:
            - {total_messages} messages across {channel_count} channels
            - {len(tickets_for_ai)} active Jira tickets (analyzing most recent {max_tickets_for_ai})
            
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
        
        # Load time ranges configuration
        time_ranges = team_data.get('time_ranges', {})
        slack_config = time_ranges.get('slack', {})
        paul_search_days = slack_config.get('paul_todo_search_days', 30)
        
        # Collect Slack messages mentioning Paul (configurable days back from latest message)
        paul_slack_content = []
        channels = team_data.get('channels', {})
        
        for channel_name, channel_data in channels.items():
            channel_id = channel_data.get('channel_id')
            messages = channel_data.get('recent_messages', [])
            
            if not channel_id or not messages:
                continue
                
            try:
                print(f'    📱 Checking {channel_name} for Paul mentions ({paul_search_days} days back)...')
                
                # Get messages from configurable days back from the most recent message
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
                    # Calculate configurable days back from the most recent message
                    latest_message_date = datetime.fromtimestamp(latest_timestamp)
                    search_cutoff = latest_message_date - timedelta(days=paul_search_days)
                    
                    # Get all messages from the channel (not just recent ones)
                    all_messages = asyncio.run(slack_client.get_channel_history(channel_id))
                    
                    paul_messages = []
                    for msg in all_messages:
                        try:
                            timestamp = float(msg.get('ts', '0'))
                            msg_date = datetime.fromtimestamp(timestamp)
                            if msg_date >= search_cutoff:
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
        
        # Get team name from team_data
        team_name = team_data.get('team', 'unknown')
        
        # Get all team tickets
        team_tickets = team_data.get('jira_tickets', {}).get(team_name, [])
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
                Slack Messages Mentioning Paul (Last {paul_search_days} Days):
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
        
        return f"No mentions of Paul Caramuto found in the last {paul_search_days} days."
        
    except Exception as e:
        print(f'  ❌ Paul TODO generation failed: {e}')
        return f"TODO generation failed: {str(e)}"


# Note: create_email_content function has been removed as email formatting 
# is now handled by templates in mail_template.yaml


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


def _get_sprint_title(team_data: Dict[str, Any]) -> str:
    """Extract sprint title from team data"""
    jira_tickets = team_data.get('jira_tickets', {})
    team_tickets = jira_tickets.get('toolchain', [])
    
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
                
                if sprint_name and sprint_name != 'Unknown Sprint':
                    sprint_counts[sprint_name] = sprint_counts.get(sprint_name, 0) + 1
        
        if sprint_counts:
            return max(sprint_counts, key=sprint_counts.get)
        return None
    
    active_sprint = get_most_common_sprint(team_tickets)
    return f'🎫 Active Sprint "{active_sprint}" Tickets' if active_sprint else '🎫 Active Sprint Tickets'


def _format_slack_channel_details(team_data: Dict[str, Any], ai_summaries: Dict[str, str]) -> str:
    """Format Slack channel details for template with AI summaries"""
    channels = team_data.get('channels', {})
    channel_summaries_html = ""
    
    # Get configurable time range for display
    time_ranges = team_data.get('time_ranges', {})
    slack_config = time_ranges.get('slack', {})
    activity_days = slack_config.get('channel_activity_days', 7)
    
    for channel_name, channel_data in channels.items():
        recent_count = channel_data.get('recent_messages', 0)
        total_count = channel_data.get('total_messages', 0)
        messages = channel_data.get('messages', [])
        
        # Get AI summary for this channel
        ai_summary = ai_summaries.get(channel_name, 'AI analysis not available for this channel')
        
        # Create recent messages preview
        recent_messages_html = ""
        if messages:
            for msg in messages:  # Show all messages from channel_activity_days period
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
                
                recent_messages_html += f"<p><strong>{time_str}</strong> <strong>{user_display_name}:</strong> {clean_text}</p>"
        
        channel_summaries_html += f"""
        <h4>📱 #{channel_name}</h4>
        <p><strong>📊 {recent_count} messages (last {activity_days} days) • {total_count} total</strong></p>
        
        <h5>🤖 AI Analysis</h5>
        <p>{ai_summary}</p>
        
        <h5>Recent Messages</h5>
        {recent_messages_html if recent_messages_html else '<p><em>No recent messages</em></p>'}
        
        <hr>
        """
    
    return channel_summaries_html if channel_summaries_html else '<p>No channel activity found</p>'


def _generate_ai_jira_summary(team_data: Dict[str, Any], ai_summaries: Dict[str, str]) -> str:
    """Generate AI summary specifically for Jira tickets"""
    try:
        from connectors.gemini.client import GeminiClient
        from connectors.gemini.config import GeminiConfig
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        
        # Get Jira tickets data
        jira_tickets = team_data.get('jira_tickets', {})
        toolchain_tickets = jira_tickets.get('toolchain', [])
        sp_tickets = jira_tickets.get('sp_organization', [])
        
        # Get configurable ticket limit for AI analysis
        time_ranges = team_data.get('time_ranges', {})
        jira_config = time_ranges.get('jira', {})
        max_tickets_for_ai = jira_config.get('max_tickets_for_analysis', 20)
        
        # Combine and limit tickets for AI analysis
        all_tickets = toolchain_tickets + sp_tickets
        tickets_for_ai = all_tickets[:max_tickets_for_ai]
        
        if not tickets_for_ai:
            return '<p style="color: #666; font-size: 14px;">No Jira tickets available for AI analysis</p>'
        
        # Prepare ticket summaries for AI
        ticket_summaries = []
        for ticket in tickets_for_ai:
            if isinstance(ticket, dict):
                key = ticket.get('key', 'N/A')
                summary = ticket.get('summary', 'No summary')
                status = ticket.get('status', {}).get('name', 'Unknown') if isinstance(ticket.get('status'), dict) else str(ticket.get('status', 'Unknown'))
                assignee = ticket.get('assignee', {}).get('displayName', 'Unassigned') if isinstance(ticket.get('assignee'), dict) else str(ticket.get('assignee', 'Unassigned'))
                
                ticket_summaries.append(f"- {key}: {summary} (Status: {status}, Assignee: {assignee})")
        
        # Generate AI analysis for Jira tickets
        jira_prompt = f"""
        Analyze the following Jira tickets for the {team_data["team"]} team and provide insights:
        
        Jira Tickets ({len(tickets_for_ai)} tickets analyzed):
        {chr(10).join(ticket_summaries)}
        
        Please provide a concise analysis (2-3 sentences) covering:
        1. Overall ticket status and progress patterns
        2. Key blockers or issues that need attention
        3. Team workload distribution and priorities
        
        Focus on actionable insights for project management.
        """
        
        jira_summary = gemini_client.generate_content(jira_prompt)
        
        if jira_summary:
            return f'<p>{jira_summary}</p>'
        else:
            return '<p><em>AI Jira analysis not available</em></p>'
            
    except Exception as e:
        print(f'  ⚠️  AI Jira analysis failed: {e}')
        return '<p><em>AI Jira analysis failed</em></p>'


def _format_ai_channel_summaries(ai_summaries: Dict[str, str]) -> str:
    """Format AI channel summaries for template"""
    summaries_html = ""
    
    # Filter out the 'overall' summary as it's used elsewhere
    channel_summaries = {k: v for k, v in ai_summaries.items() if k != 'overall'}
    
    if not channel_summaries:
        return '<p style="color: #666; font-size: 14px;">No AI channel analysis available</p>'
    
    for channel_name, summary in channel_summaries.items():
        summaries_html += f"""
        <div style="margin: 15px 0; padding: 15px; border-left: 4px solid #28a745; background: #f8f9fa; border-radius: 5px;">
            <h4 style="margin: 0 0 10px 0; color: #28a745; font-size: 16px;">📱 #{channel_name}</h4>
            <p style="margin: 0; line-height: 1.5; color: #333; font-size: 14px;">{summary}</p>
        </div>
        """
    
    return summaries_html if summaries_html else '<p style="color: #666; font-size: 14px;">No AI channel analysis available</p>'


def _format_jira_ticket_details(team_data: Dict[str, Any]) -> str:
    """Format Jira ticket details for template"""
    jira_tickets = team_data.get('jira_tickets', {})
    
    def format_jira_tickets(tickets, section_title, ticket_limit=10):
        if not tickets:
            return f"<h4>{section_title}</h4><p><em>No active tickets found</em></p>"
        
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
        
        tickets_html = f"<h4>{section_title} ({len(sorted_tickets)} tickets)</h4>"
        
        for issue in sorted_tickets[:ticket_limit]:  # Use configurable ticket limit
            if isinstance(issue, dict):
                key = issue.get('key', 'N/A')
                summary = issue.get('summary', 'No summary')
                status = issue.get('status', {}).get('name', 'Unknown') if isinstance(issue.get('status'), dict) else str(issue.get('status', 'Unknown'))
                assignee = issue.get('assignee', {}).get('displayName', 'Unassigned') if isinstance(issue.get('assignee'), dict) else str(issue.get('assignee', 'Unassigned'))
                
                # Get sprint information
                sprint_info = "No Sprint"
                if 'customfield_12310940' in issue:
                    sprint_data = issue.get('customfield_12310940', [])
                    if sprint_data and len(sprint_data) > 0:
                        import re
                        for sprint_string in sprint_data:
                            sprint_str = str(sprint_string)
                            state_match = re.search(r'state=([^,]+)', sprint_str)
                            name_match = re.search(r'name=([^,]+)', sprint_str)
                            if name_match:
                                sprint_name = name_match.group(1)
                                if state_match and state_match.group(1) == 'ACTIVE':
                                    sprint_info = f"🏃 {sprint_name} (Active)"
                                else:
                                    sprint_info = f"🏃 {sprint_name}"
                                break
                
                tickets_html += f"<p><strong>{key}:</strong> {summary}<br><em>Status: {status} | Assignee: {assignee} | Sprint: {sprint_info}</em></p>"
        
        return tickets_html
    
    # Format toolchain and SP tickets with configurable limits
    toolchain_tickets = jira_tickets.get('toolchain', [])
    sp_tickets = jira_tickets.get('sp_organization', [])
    
    # Get configurable ticket limits
    time_ranges = team_data.get('time_ranges', {})
    jira_config = time_ranges.get('jira', {})
    team_ticket_limit = jira_config.get('ticket_limit_per_team', 15)
    org_ticket_limit = jira_config.get('ticket_limit_per_org', 10)
    
    toolchain_tickets_html = format_jira_tickets(toolchain_tickets, "🔧 Toolchain Team Tickets", team_ticket_limit)
    sp_tickets_html = format_jira_tickets(sp_tickets, "👥 SP Organization Tickets", org_ticket_limit)
    
    return toolchain_tickets_html + sp_tickets_html


def send_team_email(team: str, team_data: Dict[str, Any], ai_summaries: Dict[str, str], slack_client, jira_client, gemini_client) -> bool:
    """Send email for team using template-based formatting"""
    try:
        print(f'  📧 Sending template-based email for {team.upper()} team...')
        from connectors.email.client import EmailClient
        from connectors.email.config import EmailConfig
        from datetime import datetime
        
        email_config = EmailConfig()
        config = email_config.get_config()
        
        # Validate config before creating client
        if not email_config.validate_config():
            print(f'  ❌ Email config validation failed')
            return False
            
        email_client = EmailClient(config)
        
        # Generate Paul TODO items
        paul_todo_items = generate_paul_todo_items(team_data, slack_client, jira_client, gemini_client)
        
        # Prepare template data for team_daily_report_with_todo template
        template_data = {
            'team': team.upper(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            'executive_summary': ai_summaries.get('overall', 'AI analysis not available'),
            'paul_todo_items': paul_todo_items,
            'slack_channel_details': _format_slack_channel_details(team_data, ai_summaries),
            'ai_jira_summary': _generate_ai_jira_summary(team_data, ai_summaries),
            'sprint_title': _get_sprint_title(team_data),
            'jira_ticket_details': _format_jira_ticket_details(team_data),
            # Add configurable time ranges for template display
            'slack_activity_days': team_data.get('time_ranges', {}).get('slack', {}).get('channel_activity_days', 7),
            'jira_ticket_limit': team_data.get('time_ranges', {}).get('jira', {}).get('ticket_limit_per_team', 15)
        }
        
        # Send email using the new template
        result = email_client.send_email(
            template_name='team_daily_report_with_todo',
            recipients=config['recipients']['default'],
            content_data=template_data
        )
        
        if result.get('success'):
            print(f'  ✅ Template-based email sent successfully for {team.upper()} team!')
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
    gemini_client = GeminiClient(gemini_config.get_config())
    
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
