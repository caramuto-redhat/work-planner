"""
Slack TODO Extraction Tool
MCP tool for extracting actionable TODO items from Slack messages and threads using Gemini AI
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from utils.responses import create_error_response, create_success_response
from connectors.gemini.client import GeminiClient
from .slack_helpers import check_and_dump_if_needed, get_channel_name_from_config


def extract_slack_todos_tool(slack_client, slack_config: Dict[str, Any], gemini_config_dict: Dict[str, Any]):
    """Create extract_slack_todos tool function"""
    
    def extract_slack_todos(
        team: Optional[str] = None,
        include_dms: bool = True,
        include_mentions: bool = True,
        days_back: int = 30,
        max_age_hours: int = 24
    ) -> str:
        """
        Extract actionable TODO items from Slack messages and threads using Gemini AI natural language understanding.
        
        Analyzes Slack messages, DMs, and thread replies to identify tasks requiring action,
        including @mentions, direct questions, commitments, and follow-up requests.
        
        Args:
            team: Team name to filter channels (optional, analyzes all teams if not specified)
            include_dms: Analyze direct messages (default: True)
            include_mentions: Focus on messages with @mentions (default: True)
            days_back: Number of days to look back for messages (default: 30)
            max_age_hours: Maximum age of cached Slack data before refreshing (default: 24)
            
        Returns:
            JSON response with extracted TODO items, urgency, deadlines, and context
            
        Example:
            extract_slack_todos(team="toolchain", days_back=30)
        """
        try:
            print(f"\n💬 Starting Slack TODO extraction...")
            if team:
                print(f"   Team: {team}")
            print(f"   Days back: {days_back}")
            
            # Get TODO extraction configuration
            todo_config = gemini_config_dict.get('todo_extraction', {})
            if not todo_config.get('enabled', False):
                return create_error_response(
                    "TODO extraction disabled",
                    "todo_extraction.enabled is false in gemini.yaml"
                )
            
            slack_source_config = todo_config.get('sources', {}).get('slack', {})
            if not slack_source_config.get('enabled', True):
                return create_error_response(
                    "Slack TODO extraction disabled",
                    "todo_extraction.sources.slack.enabled is false in gemini.yaml"
                )
            
            # Get channels to analyze
            slack_channels = slack_config.get('slack_channels', {})
            
            if team:
                # Filter channels by team
                validated_team = team.lower().strip()
                channel_ids = [
                    channel_id for channel_id, channel_team in slack_channels.items()
                    if channel_team.lower() == validated_team
                ]
                
                if not channel_ids:
                    return create_error_response(
                        "Team not found",
                        f"Team '{team}' not found in Slack configuration or has no channels"
                    )
            else:
                # All channels
                channel_ids = list(slack_channels.keys())
            
            if not channel_ids:
                return create_success_response({
                    'messages_analyzed': 0,
                    'todos_found': 0,
                    'todos': [],
                    'message': 'No Slack channels configured for the specified team'
                })
            
            print(f"📥 Analyzing {len(channel_ids)} Slack channels...")
            
            # Read Slack data from dumps
            all_messages = []
            for channel_id in channel_ids:
                try:
                    # Ensure data is fresh
                    check_and_dump_if_needed(slack_client, slack_config, channel_id, max_age_hours)
                    
                    # Read parsed dump
                    dump_path = os.path.join(
                        'connectors', 'slack', 'slack_dump', 'slack_dumps_parsed',
                        f'{channel_id}_slack_dump_parsed.txt'
                    )
                    
                    if os.path.exists(dump_path):
                        with open(dump_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Parse messages from parsed dump format
                            # Format: 
                            # Message X - YYYY-MM-DD HH:MM
                            # From: Username
                            # ----------------------------------------
                            # Message text
                            
                            lines = content.strip().split('\n')
                            i = 0
                            while i < len(lines):
                                line = lines[i].strip()
                                
                                # Look for message header: "Message X - YYYY-MM-DD HH:MM"
                                if line.startswith('Message ') and ' - ' in line:
                                    try:
                                        # Extract date and time from header
                                        date_time_part = line.split(' - ', 1)[1]
                                        date_parts = date_time_part.split()
                                        if len(date_parts) >= 2:
                                            date = date_parts[0]
                                            time = date_parts[1] if len(date_parts) > 1 else ''
                                            
                                            # Next line should be "From: Username"
                                            i += 1
                                            if i < len(lines) and lines[i].startswith('From: '):
                                                user = lines[i].replace('From: ', '').strip()
                                                
                                                # Skip separator line
                                                i += 1
                                                if i < len(lines) and '---' in lines[i]:
                                                    i += 1
                                                
                                                # Collect message text until next message or separator
                                                message_lines = []
                                                while i < len(lines):
                                                    if lines[i].startswith('Message ') or lines[i].startswith('==='):
                                                        break
                                                    message_lines.append(lines[i])
                                                    i += 1
                                                
                                                message = '\n'.join(message_lines).strip()
                                                
                                                if message:  # Only add non-empty messages
                                                    all_messages.append({
                                                        'channel_id': channel_id,
                                                        'channel_name': get_channel_name_from_config(slack_config, channel_id),
                                                        'date': date,
                                                        'time': time,
                                                        'user': user,
                                                        'message': message[:500],  # Limit message length
                                                        'thread_context': ''
                                                    })
                                                continue
                                    except Exception as e:
                                        pass
                                
                                i += 1
                    
                except Exception as e:
                    print(f"  ⚠️  Failed to read channel {channel_id}: {e}")
                    continue
            
            if not all_messages:
                return create_success_response({
                    'messages_analyzed': 0,
                    'todos_found': 0,
                    'todos': [],
                    'message': 'No Slack messages found in dumps'
                })
            
            print(f"✅ Loaded {len(all_messages)} messages from Slack dumps")
            
            # Filter messages if needed
            if include_mentions:
                # Look for messages that might contain mentions (simplified filtering)
                filtered_messages = [
                    msg for msg in all_messages
                    if '@' in msg.get('message', '') or msg.get('thread_context', '')
                ]
                if filtered_messages:
                    all_messages = filtered_messages
                    print(f"   Filtered to {len(all_messages)} messages with potential mentions")
            
            # Initialize Gemini client for TODO extraction
            todo_model_config = {
                'model': todo_config.get('model', 'models/gemini-2.0-flash'),
                'generation_config': {
                    'temperature': todo_config.get('temperature', 0.3),
                    'top_p': 0.9,
                    'top_k': 40,
                    'max_output_tokens': todo_config.get('max_output_tokens', 2000)
                }
            }
            gemini_client = GeminiClient(todo_model_config)
            
            # Get prompts
            prompts = todo_config.get('prompts', {})
            system_prompt = prompts.get('system_prompt', '')
            slack_prompt_template = prompts.get('slack_prompt', '')
            
            # Extract TODOs from messages (analyze in batches for efficiency)
            print(f"🤖 Analyzing Slack messages for TODOs using Gemini AI...")
            all_todos = []
            confidence_threshold = todo_config.get('detection', {}).get('confidence_threshold', 0.6)
            max_todos_per_message = todo_config.get('detection', {}).get('max_todos_per_item', 3)
            priority_weight = slack_source_config.get('priority_weight', 0.9)
            
            # Analyze messages in batches (group by channel for context)
            analyzed_count = 0
            for msg in all_messages[:100]:  # Limit to 100 messages for performance
                try:
                    # Build Slack prompt
                    slack_prompt = slack_prompt_template.format(
                        channel=msg.get('channel_name', 'Unknown'),
                        sender=msg.get('user', 'Unknown'),
                        date=f"{msg.get('date', 'Unknown')} {msg.get('time', '')}",
                        message=msg.get('message', '')[:500],  # Limit message length
                        thread_context=msg.get('thread_context', 'No thread')
                    )
                    
                    # Combine system prompt and slack prompt
                    full_prompt = f"{system_prompt}\n\n{slack_prompt}"
                    
                    # Get Gemini analysis
                    response = gemini_client.generate_content(full_prompt)
                    
                    # Parse JSON response
                    try:
                        # Clean response (remove markdown code blocks if present)
                        response_cleaned = response.strip()
                        if response_cleaned.startswith('```json'):
                            response_cleaned = response_cleaned[7:]
                        if response_cleaned.startswith('```'):
                            response_cleaned = response_cleaned[3:]
                        if response_cleaned.endswith('```'):
                            response_cleaned = response_cleaned[:-3]
                        response_cleaned = response_cleaned.strip()
                        
                        todos = json.loads(response_cleaned)
                        
                        if not isinstance(todos, list):
                            continue
                        
                        # Filter by confidence and limit
                        filtered_todos = [
                            todo for todo in todos 
                            if float(todo.get('confidence', 0)) >= confidence_threshold
                        ][:max_todos_per_message]
                        
                        # Add metadata and apply priority weight
                        for todo in filtered_todos:
                            todo['source'] = 'slack'
                            todo['metadata'] = {
                                'channel': msg.get('channel_name', 'Unknown'),
                                'channel_id': msg.get('channel_id', 'Unknown'),
                                'sender': msg.get('user', 'Unknown'),
                                'date': msg.get('date', 'Unknown'),
                                'message_link': f"https://redhat.slack.com/archives/{msg.get('channel_id', '')}"
                            }
                            # Apply priority weight if urgency is specified
                            if 'urgency' in todo:
                                todo['original_urgency'] = todo['urgency']
                                todo['priority_weight'] = priority_weight
                        
                        all_todos.extend(filtered_todos)
                        analyzed_count += 1
                        
                        if filtered_todos:
                            print(f"  ✅ Message {analyzed_count}: Found {len(filtered_todos)} TODO(s)")
                    
                    except json.JSONDecodeError:
                        continue
                
                except Exception as e:
                    print(f"  ❌ Message analysis failed: {e}")
                    continue
            
            # Sort by urgency and confidence
            urgency_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            all_todos.sort(
                key=lambda x: (
                    urgency_order.get(x.get('urgency', 'low'), 4),
                    -float(x.get('confidence', 0))
                )
            )
            
            print(f"\n✅ Slack TODO extraction complete!")
            print(f"   📊 Messages analyzed: {analyzed_count}")
            print(f"   📋 TODOs found: {len(all_todos)}")
            
            return create_success_response({
                'messages_analyzed': analyzed_count,
                'todos_found': len(all_todos),
                'todos': all_todos,
                'analysis_period': f'Last {days_back} days',
                'team': team or 'All teams',
                'channels_analyzed': len(channel_ids),
                'confidence_threshold': confidence_threshold,
                'priority_weight': priority_weight
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Slack TODO extraction failed: {e}")
            return create_error_response(
                "Slack TODO extraction failed",
                f"{str(e)}\n\n{error_details}"
            )
    
    return extract_slack_todos

