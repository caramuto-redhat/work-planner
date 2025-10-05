"""
Unified Slack Tools
Combines individual channel and team operations into unified tools
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_channel_id, validate_team_name
import os
import json
import asyncio
import threading
from datetime import datetime, timedelta
import re


def dump_slack_data_tool(client, config):
    """Create unified dump_slack_data tool function"""
    
    def dump_slack_data(target: str, latest_date: str = None) -> str:
        """
        Dump Slack data for a specific channel or all channels for a team.
        
        Args:
            target: Either a channel ID (starts with 'C') or team name
            latest_date: Optional date to limit messages (ISO format)
        """
        try:
            # Determine if target is a channel ID or team name
            if target.startswith('C') and len(target) >= 8:
                # It's a channel ID - dump single channel
                return _dump_single_channel(client, config, target, latest_date)
            else:
                # It's a team name - dump all team channels
                return _dump_team_channels(client, config, target, latest_date)
                
        except Exception as e:
            return create_error_response("Failed to dump Slack data", str(e))
    
    return dump_slack_data


def read_slack_data_tool(client, config):
    """Create unified read_slack_data tool function"""
    
    def read_slack_data(target: str, max_age_hours: int = 24) -> str:
        """
        Read Slack data for a specific channel or all channels for a team.
        Automatically dumps fresh data if needed.
        
        Args:
            target: Either a channel ID (starts with 'C') or team name
            max_age_hours: Maximum age of cached data before refreshing
        """
        try:
            # Determine if target is a channel ID or team name
            if target.startswith('C') and len(target) >= 8:
                # It's a channel ID - read single channel
                return _read_single_channel(client, config, target, max_age_hours)
            else:
                # It's a team name - read all team channels
                return _read_team_channels(client, config, target, max_age_hours)
                
        except Exception as e:
            return create_error_response("Failed to read Slack data", str(e))
    
    return read_slack_data


def search_slack_data_tool(client, config):
    """Create unified search_slack_data tool function"""
    
    def search_slack_data(target: str, search_term: str, max_age_hours: int = 24) -> str:
        """
        Search for specific mentions or names in a Slack channel or across all team channels.
        
        Args:
            target: Either a channel ID (starts with 'C') or team name
            search_term: Term to search for
            max_age_hours: Maximum age of cached data before refreshing
        """
        try:
            # Determine if target is a channel ID or team name
            if target.startswith('C') and len(target) >= 8:
                # It's a channel ID - search single channel
                return _search_single_channel(client, config, target, search_term, max_age_hours)
            else:
                # It's a team name - search all team channels
                return _search_team_channels(client, config, target, search_term, max_age_hours)
                
        except Exception as e:
            return create_error_response("Failed to search Slack data", str(e))
    
    return search_slack_data


def list_slack_channels_tool(client, config):
    """Create unified list_slack_channels tool function"""
    
    def list_slack_channels(team: str = None) -> str:
        """
        List all Slack channels, optionally filtered by team.
        
        Args:
            team: Optional team name to filter channels
        """
        try:
            slack_channels = config.get("slack_channels", {})
            
            if team:
                # Filter by team
                validated_team = validate_team_name(team)
                team_channels = [channel_id for channel_id, team_id in slack_channels.items() 
                               if team_id == validated_team]
                
                return create_success_response({
                    "team": validated_team,
                    "channels": team_channels,
                    "count": len(team_channels)
                })
            else:
                # Return all channels grouped by team
                teams = {}
                for channel_id, team_id in slack_channels.items():
                    if team_id not in teams:
                        teams[team_id] = []
                    teams[team_id].append(channel_id)
                
                return create_success_response({
                    "all_channels": slack_channels,
                    "channels_by_team": teams,
                    "total_channels": len(slack_channels),
                    "total_teams": len(teams)
                })
                
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to list Slack channels", str(e))
    
    return list_slack_channels


def list_slack_dumps_tool(client, config):
    """Create unified list_slack_dumps tool function"""
    
    def list_slack_dumps(team: str = None) -> str:
        """
        List all available Slack dumps, optionally filtered by team.
        
        Args:
            team: Optional team name to filter dumps
        """
        try:
            dump_dir = config.get("data_collection", {}).get("dump_directory", "slack_dumps")
            
            # Check if dump directory exists
            if not os.path.exists(dump_dir):
                return create_success_response({
                    "dumps": [],
                    "count": 0,
                    "note": "No dump directory found. Run dump_slack_data first."
                })
            
            # Get all dump files
            all_dumps = []
            for filename in os.listdir(dump_dir):
                if filename.endswith("_slack_dump.txt"):
                    filepath = os.path.join(dump_dir, filename)
                    stat = os.stat(filepath)
                    
                    # Extract channel ID from filename
                    channel_id = filename.replace("_slack_dump.txt", "")
                    
                    # Determine team from channel ID
                    slack_channels = config.get("slack_channels", {})
                    team_id = slack_channels.get(channel_id, "unknown")
                    
                    dump_info = {
                        "filename": filename,
                        "file_path": filepath,
                        "channel_id": channel_id,
                        "team": team_id,
                        "size_bytes": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                    
                    # Filter by team if specified
                    if team is None or team_id == team:
                        all_dumps.append(dump_info)
            
            # Sort by creation time (newest first)
            all_dumps.sort(key=lambda x: x["created"], reverse=True)
            
            return create_success_response({
                "dumps": all_dumps,
                "count": len(all_dumps),
                "filtered_by_team": team
            })
            
        except Exception as e:
            return create_error_response("Failed to list Slack dumps", str(e))
    
    return list_slack_dumps


# Helper functions for the unified tools

def _dump_single_channel(client, config, channel_id: str, latest_date: str = None, include_attachments: bool = None) -> str:
    """Dump a single Slack channel"""
    try:
        validated_channel_id = validate_channel_id(channel_id)
        
        # Default to False for attachments if not specified
        if include_attachments is None:
            include_attachments = False
        
        # Get channel history using async function
        def run_async():
            return asyncio.run(client.get_channel_history(validated_channel_id, latest_date))
        
        # Run in a separate thread to avoid event loop conflicts
        result = None
        def target():
            nonlocal result
            result = run_async()
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        
        if result is None:
            raise Exception("Failed to get channel history")
        
        messages = result
        
        # Create dump directory
        dump_dir = config.get("data_collection", {}).get("dump_directory", "slack_dumps")
        os.makedirs(dump_dir, exist_ok=True)
        
        # Create attachments directory if including attachments
        attachments_dir = None
        if include_attachments:
            attachments_dir = config.get("data_collection", {}).get("attachments_directory", "slack_attachments")
            attachment_channel_dir = os.path.join(attachments_dir, validated_channel_id)
            os.makedirs(attachment_channel_dir, exist_ok=True)
            print(f"📎 Attachment download enabled for channel {validated_channel_id}")
        else:
            print(f"📎 Attachment download disabled for channel {validated_channel_id}")
        
        # Create filename
        filename = f"{validated_channel_id}_slack_dump.txt"
        filepath = os.path.join(dump_dir, filename)
        
        # Write messages to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Slack Channel Dump\n")
            f.write(f"# Channel ID: {validated_channel_id}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n")
            if latest_date:
                f.write(f"# Messages up to: {latest_date}\n")
            f.write(f"# Total Messages: {len(messages)}\n\n")
            
            attachment_count = 0
            for message in messages:
                # Extract full message content using enhanced extraction
                extracted = _extract_full_message_content(message, config)
                timestamp = datetime.fromtimestamp(float(extracted['timestamp']))
                display_name = extracted['display_name']
                full_content = extracted['full_content']
                
                f.write(f"[{timestamp.isoformat()}] {display_name}: {full_content}\n")
                
                # Handle attachments if enabled
                if include_attachments and ('files' in message or 'blocks' in message):
                    attachments = client.get_message_attachments(message)
                    for attachment in attachments:
                        download_url = attachment.get('url_private_download') or attachment.get('url_private')
                        if download_url:
                            try:
                                # Download attachment
                                attachment_result = [None]
                                def run_async():
                                    try:
                                        attachment_result[0] = asyncio.run(client.download_attachment(download_url, attachment['name']))
                                    except Exception as e:
                                        attachment_result[0] = (None, None)
                                
                                thread = threading.Thread(target=run_async)
                                thread.start()
                                thread.join()
                                
                                attachment_filename, attachment_content = attachment_result[0] or (None, None)
                                
                                if attachment_filename and attachment_content:
                                    # Save attachment
                                    attachment_path = os.path.join(attachment_channel_dir, attachment_filename)
                                    with open(attachment_path, 'wb') as af:
                                        af.write(attachment_content)
                                    
                                    f.write(f"    [ATTACHMENT: {attachment_filename} ({attachment.get('size', 0)} bytes)]\n")
                                    attachment_count += 1
                                else:
                                    f.write(f"    [ATTACHMENT: {attachment['name']} (download failed)]\n")
                            except Exception as e:
                                f.write(f"    [ATTACHMENT: {attachment['name']} (error: {str(e)})]\n")
        
        # Also create parsed version
        parsed_dir = config.get("data_collection", {}).get("parsed_directory", "slack_dumps_parsed")
        os.makedirs(parsed_dir, exist_ok=True)
        
        parsed_filename = f"{validated_channel_id}_slack_dump_parsed.txt"
        parsed_filepath = os.path.join(parsed_dir, parsed_filename)
        
        # Get channel name from config
        channel_name = _get_channel_name_from_config(config, validated_channel_id)
        
        # Write parsed messages to file with Google Docs-friendly formatting
        with open(parsed_filepath, 'w', encoding='utf-8') as f:
            f.write(f"Slack Channel Dump\n")
            f.write(f"Channel: {channel_name}\n")
            f.write(f"Channel ID: {validated_channel_id}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if latest_date:
                f.write(f"Messages up to: {latest_date}\n")
            f.write(f"Total Messages: {len(messages)}\n")
            f.write(f"{'='*80}\n\n")
            
            for i, message in enumerate(messages):
                # Extract full message content using enhanced extraction
                extracted = _extract_full_message_content(message, config)
                timestamp = datetime.fromtimestamp(float(extracted['timestamp']))
                user = extracted['display_name']
                full_content = extracted['full_content']
                
                # Enhanced parsing: clean up Slack formatting
                parsed_text = full_content  # Use enhanced full content
                
                # Get mappings for user mentions
                user_mappings = config.get('user_display_names', {})
                bot_mappings = config.get('bot_display_names', {})
                
                # Replace user mentions in message content with display names
                def replace_user_mention(match):
                    mentioned_user_id = match.group(1)
                    # Check both user and bot mappings
                    display_name = user_mappings.get(mentioned_user_id) or bot_mappings.get(mentioned_user_id, mentioned_user_id)
                    return f"@{display_name}"
                parsed_text = re.sub(r'<@([A-Z0-9]+)>', replace_user_mention, parsed_text)
                # Remove Slack channel links and replace with readable format
                parsed_text = re.sub(r'<#([A-Z0-9]+)\|([^>]+)>', r'#\2', parsed_text)
                # Remove general links but keep the URL
                parsed_text = re.sub(r'<([^|>]+)\|([^>]+)>', r'\2 (\1)', parsed_text)
                parsed_text = re.sub(r'<([^>]+)>', r'\1', parsed_text)
                
                # Format for Google Docs readability
                formatted_date = timestamp.strftime('%Y-%m-%d %H:%M')
                
                # Write message with clear formatting
                f.write(f"Message {i+1} - {formatted_date}\n")
                f.write(f"From: {user}\n")
                f.write(f"{'-'*40}\n")
                
                # Split long messages into paragraphs for better readability
                if parsed_text.strip():
                    # Split by double newlines or long lines
                    paragraphs = parsed_text.split('\n\n')
                    for paragraph in paragraphs:
                        if paragraph.strip():
                            # Clean up the paragraph
                            clean_paragraph = paragraph.strip().replace('\n', ' ')
                            # Break very long lines
                            if len(clean_paragraph) > 100:
                                words = clean_paragraph.split()
                                current_line = ""
                                for word in words:
                                    if len(current_line + word) > 100:
                                        f.write(f"{current_line.strip()}\n")
                                        current_line = word + " "
                                    else:
                                        current_line += word + " "
                                if current_line.strip():
                                    f.write(f"{current_line.strip()}\n")
                            else:
                                f.write(f"{clean_paragraph}\n")
                else:
                    f.write("[No text content]\n")
                
                f.write(f"\n")
        
        result_data = {
            "target": validated_channel_id,
            "target_type": "channel",
            "messages_count": len(messages),
            "file_path": filepath,
            "filename": filename,
            "parsed_file_path": parsed_filepath,
            "parsed_filename": parsed_filename,
            "channel_name": channel_name,
            "latest_date": latest_date
        }
        
        if include_attachments:
            result_data["attachments_count"] = attachment_count
            result_data["attachments_dir"] = attachment_channel_dir
            result_data["include_attachments"] = True
        
        return create_success_response(result_data)
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response("Failed to dump single channel", str(e))


def _dump_team_channels(client, config, team: str, latest_date: str = None) -> str:
    """Dump all channels for a team"""
    try:
        validated_team = validate_team_name(team)
        
        # Get team's channels from config
        slack_channels = config.get("slack_channels", {})
        team_channels = [channel_id for channel_id, team_id in slack_channels.items() if team_id == validated_team]
        
        if not team_channels:
            return create_error_response(f"No Slack channels found for team '{team}'")
        
        results = []
        errors = []
        
        for channel_id in team_channels:
            result = _dump_single_channel(client, config, channel_id, latest_date)
            result_data = json.loads(result)
            if "error" not in result_data:
                results.append(result_data)
            else:
                errors.append(f"Channel {channel_id}: {result_data['error']}")
        
        return create_success_response({
            "target": validated_team,
            "target_type": "team",
            "channels_processed": len(results),
            "results": results,
            "errors": errors,
            "latest_date": latest_date
        })
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response("Failed to dump team channels", str(e))


def _read_single_channel(client, config, channel_id: str, max_age_hours: int = 24, use_parsed: bool = False) -> str:
    """Read a single Slack channel"""
    try:
        validated_channel_id = validate_channel_id(channel_id)
        
        # First, ensure we have fresh data
        dump_result = _check_and_dump_if_needed(client, config, validated_channel_id, max_age_hours)
        dump_data = json.loads(dump_result)
        if "error" in dump_data:
            return dump_result  # Return the original error response
        
        # Choose between raw dump (with user IDs) or parsed dump (with display names)
        if use_parsed:
            dump_dir = config.get("data_collection", {}).get("parsed_directory", "slack_dumps_parsed")
            filename = f"{validated_channel_id}_slack_dump_parsed.txt"
        else:
            dump_dir = config.get("data_collection", {}).get("dump_directory", "slack_dumps")
            filename = f"{validated_channel_id}_slack_dump.txt"
            
        filepath = os.path.join(dump_dir, filename)
        
        if not os.path.exists(filepath):
            return create_error_response(f"No Slack dump found for channel '{validated_channel_id}' after attempting to create one.")
        
        # Read content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get file stats
        stat = os.stat(filepath)
        
        # Get channel name from config comments for better context
        channel_name = _get_channel_name_from_config(config, validated_channel_id)
        
        return create_success_response({
            "target": validated_channel_id,
            "target_type": "channel",
            "channel_name": channel_name,
            "data": content,
            "source_file": filename,
            "file_path": filepath,
            "file_size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "data_action": dump_data.get("action", "unknown"),
            "data_format": "parsed" if use_parsed else "raw",
            "note": "Parsed Slack data with display names" if use_parsed else "Raw Slack data with user IDs"
        })
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response("Failed to read single channel", str(e))


def _read_team_channels(client, config, team: str, max_age_hours: int = 24) -> str:
    """Read all channels for a team"""
    try:
        validated_team = validate_team_name(team)
        
        # Get team's channels from config
        slack_channels = config.get("slack_channels", {})
        team_channels = [channel_id for channel_id, team_id in slack_channels.items() if team_id == validated_team]
        
        if not team_channels:
            return create_error_response(f"No Slack channels found for team '{team}'")
        
        all_data = {}
        errors = []
        actions_taken = []
        
        for channel_id in team_channels:
            result = _read_single_channel(client, config, channel_id, max_age_hours)
            result_data = json.loads(result)
            if "error" not in result_data:
                all_data[channel_id] = {
                    "data": result_data["data"],
                    "source_file": result_data["source_file"],
                    "file_size_bytes": result_data["file_size_bytes"],
                    "created": result_data["created"],
                    "data_action": result_data.get("data_action", "unknown")
                }
                actions_taken.append(f"Channel {channel_id}: {result_data.get('data_action', 'unknown')}")
            else:
                errors.append(f"Channel {channel_id}: {result_data['error']}")
        
        return create_success_response({
            "target": validated_team,
            "target_type": "team",
            "channels": list(all_data.keys()),
            "data": all_data,
            "errors": errors,
            "actions_taken": actions_taken,
            "note": "Raw Slack data for all team channels - automatically refreshed if needed - let LLM analyze"
        })
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response("Failed to read team channels", str(e))


def _search_single_channel(client, config, channel_id: str, search_term: str, max_age_hours: int = 24) -> str:
    """Search a single Slack channel using parsed data with display names"""
    try:
        validated_channel_id = validate_channel_id(channel_id)
        
        # Read parsed data (with display names) instead of raw data (with user IDs)
        channel_result = _read_single_channel(client, config, validated_channel_id, max_age_hours, use_parsed=True)
        channel_data = json.loads(channel_result)
        if "error" in channel_data:
            return channel_result  # Return the original error response
        
        # Extract the Slack data
        slack_data = channel_data.get("data", "")
        if not slack_data:
            return create_error_response("No Slack data available for search")
        
        # Search for mentions in parsed text (case-insensitive)
        search_patterns = _get_search_patterns(client, config, search_term)
        matches = []
        
        # Simple text search in parsed content
        lines = slack_data.split('\n')
        current_message = None
        message_context = []
        
        for line in lines:
            if line.startswith('Message '):
                # Save previous message if it matched
                if current_message and any(pattern.lower() in current_message['text'].lower() for pattern in search_patterns):
                    matches.append({
                        'timestamp': current_message.get('timestamp', ''),
                        'user': current_message.get('user', ''),
                        'text': current_message.get('text', ''),
                        'context': '\n'.join(current_message.get('context', [])[:2])  # Include 2 lines of context
                    })
                
                # Start new message
                current_message = {'timestamp': '', 'user': '', 'text': '', 'context': []}
                message_context = []
            
            elif line.startswith('From: '):
                if current_message:
                    current_message['user'] = line.replace('From: ', '')
            
            elif line.startswith('From: '):
                if current_message:
                    current_message['user'] = line.replace('From: ', '')
                    
            else:
                if current_message and line.strip():
                    current_message['context'].append(line)
                    if not line.startswith('=') and not line.startswith('-'):
                        current_message['text'] += line + ' '
        
        # Check last message
        if current_message and any(pattern.lower() in current_message['text'].lower() for pattern in search_patterns):
            matches.append({
                'timestamp': current_message.get('timestamp', ''),
                'user': current_message.get('user', ''),
                'text': current_message.get('text', ''),
                'context': '\n'.join(current_message.get('context', [])[:2])
            })
        
        # Prepare response
        response_data = {
            "target": validated_channel_id,
            "target_type": "channel",
            "channel_name": channel_data.get("channel_name", ""),
            "search_term": search_term,
            "matches_found": len(matches),
            "matches": matches[:10],  # Limit to 10 matches for readability
            "source_file": channel_data.get("source_file", "unknown"),
            "data_action": channel_data.get("data_action", "unknown"),
            "data_format": channel_data.get("data_format", "parsed"),
            "search_patterns_used": search_patterns
        }
        
        return create_success_response(response_data)
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response("Failed to search single channel", str(e))


def _search_team_channels(client, config, team: str, search_term: str, max_age_hours: int = 24) -> str:
    """Search all channels for a team"""
    try:
        validated_team = validate_team_name(team)
        
        # Get team channels
        slack_channels = config.get('slack_channels', {})
        team_channels = [channel_id for channel_id, team_id in slack_channels.items() 
                       if team_id.lower() == validated_team.lower()]
        
        if not team_channels:
            return create_error_response(f"No channels found for team: {team}")
        
        all_matches = {}
        total_matches = 0
        
        # Search each channel
        for channel_id in team_channels:
            channel_result = _search_single_channel(client, config, channel_id, search_term, max_age_hours)
            channel_data = json.loads(channel_result)
            if "error" not in channel_data:
                matches = channel_data.get("matches", [])
                if matches:
                    all_matches[channel_id] = {
                        "matches_found": len(matches),
                        "matches": matches,
                        "source_file": channel_data.get("source_file", "unknown")
                    }
                    total_matches += len(matches)
        
        # Prepare response
        response_data = {
            "target": validated_team,
            "target_type": "team",
            "search_term": search_term,
            "channels_searched": len(team_channels),
            "channels_with_matches": len(all_matches),
            "total_matches": total_matches,
            "matches_by_channel": all_matches,
            "search_patterns_used": _get_search_patterns(client, config, search_term)
        }
        
        return create_success_response(response_data)
        
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response("Failed to search team channels", str(e))


def _check_and_dump_if_needed(client, config, channel_id: str, max_age_hours: int = 24) -> str:
    """Check if channel data is fresh, dump if needed"""
    try:
        dump_dir = config.get("data_collection", {}).get("dump_directory", "slack_dumps")
        
        # Check if dump directory exists
        if not os.path.exists(dump_dir):
            os.makedirs(dump_dir, exist_ok=True)
        
        # Check if dump file exists for this channel
        filename = f"{channel_id}_slack_dump.txt"
        filepath = os.path.join(dump_dir, filename)
        
        needs_dump = False
        
        if not os.path.exists(filepath):
            # No dump exists, need to create one
            needs_dump = True
        else:
            # Check if existing dump is fresh enough
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            # Check if file is older than max_age_hours
            if datetime.now() - file_time > timedelta(hours=max_age_hours):
                needs_dump = True
        
        if needs_dump:
            # Get channel history using async function
            def run_async():
                return asyncio.run(client.get_channel_history(channel_id))
            
            # Run in a separate thread to avoid event loop conflicts
            result = None
            def target():
                nonlocal result
                result = run_async()
            
            thread = threading.Thread(target=target)
            thread.start()
            thread.join()
            
            if result is None:
                raise Exception("Failed to get channel history")
            
            messages = result
            
            # Create new dump (overwrite existing file)
            filename = f"{channel_id}_slack_dump.txt"
            filepath = os.path.join(dump_dir, filename)
            
            # Write messages to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Slack Channel Dump\n")
                f.write(f"# Channel ID: {channel_id}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Total Messages: {len(messages)}\n\n")
                
                for message in messages:
                    # Extract full message content using enhanced extraction
                    extracted = _extract_full_message_content(message, config)
                    timestamp = datetime.fromtimestamp(float(extracted['timestamp']))
                    display_name = extracted['display_name']
                    full_content = extracted['full_content']
                    
                    f.write(f"[{timestamp.isoformat()}] {display_name}: {full_content}\n")
            
            # Also create parsed version
            parsed_dir = config.get("data_collection", {}).get("parsed_directory", "slack_dumps_parsed")
            os.makedirs(parsed_dir, exist_ok=True)
            
            parsed_filename = f"{channel_id}_slack_dump_parsed.txt"
            parsed_filepath = os.path.join(parsed_dir, parsed_filename)
            
            # Get channel name from config
            channel_name = _get_channel_name_from_config(config, channel_id)
            
            # Write parsed messages to file with Google Docs-friendly formatting
            with open(parsed_filepath, 'w', encoding='utf-8') as f:
                f.write(f"Slack Channel Dump\n")
                f.write(f"Channel: {channel_name}\n")
                f.write(f"Channel ID: {channel_id}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Messages: {len(messages)}\n")
                f.write(f"{'='*80}\n\n")
                
                for i, message in enumerate(messages):
                    # Extract full message content using enhanced extraction
                    extracted = _extract_full_message_content(message, config)
                    timestamp = datetime.fromtimestamp(float(extracted['timestamp']))
                    user = extracted['display_name']
                    text = extracted['full_content']  # Use rich content if available
                    
                    # Enhanced parsing: clean up Slack formatting
                    parsed_text = text
                    
                    # Get mappings for user mentions
                    user_mappings = config.get('user_display_names', {})
                    bot_mappings = config.get('bot_display_names', {})
                    
                    # Replace user mentions in message content with display names
                    def replace_user_mention(match):
                        mentioned_user_id = match.group(1)
                        # Check both user and bot mappings
                        display_name = user_mappings.get(mentioned_user_id) or bot_mappings.get(mentioned_user_id, mentioned_user_id)
                        return f"@{display_name}"
                    parsed_text = re.sub(r'<@([A-Z0-9]+)>', replace_user_mention, parsed_text)
                    # Remove Slack channel links and replace with readable format
                    parsed_text = re.sub(r'<#([A-Z0-9]+)\|([^>]+)>', r'#\2', parsed_text)
                    # Remove general links but keep the URL
                    parsed_text = re.sub(r'<([^|>]+)\|([^>]+)>', r'\2 (\1)', parsed_text)
                    parsed_text = re.sub(r'<([^>]+)>', r'\1', parsed_text)
                    
                    # Format for Google Docs readability
                    formatted_date = timestamp.strftime('%Y-%m-%d %H:%M')
                    
                    # Write message with clear formatting
                    f.write(f"Message {i+1} - {formatted_date}\n")
                    f.write(f"From: {user}\n")
                    f.write(f"{'-'*40}\n")
                    
                    # Split long messages into paragraphs for better readability
                    if parsed_text.strip():
                        # Split by double newlines or long lines
                        paragraphs = parsed_text.split('\n\n')
                        for paragraph in paragraphs:
                            if paragraph.strip():
                                # Clean up the paragraph
                                clean_paragraph = paragraph.strip().replace('\n', ' ')
                                # Break very long lines
                                if len(clean_paragraph) > 100:
                                    words = clean_paragraph.split()
                                    current_line = ""
                                    for word in words:
                                        if len(current_line + word) > 100:
                                            f.write(f"{current_line.strip()}\n")
                                            current_line = word + " "
                                        else:
                                            current_line += word + " "
                                    if current_line.strip():
                                        f.write(f"{current_line.strip()}\n")
                                else:
                                    f.write(f"{clean_paragraph}\n")
                    else:
                        f.write("[No text content]\n")
                    
                    f.write(f"\n")
            
            return create_success_response({
                "action": "dumped",
                "channel_id": channel_id,
                "messages_count": len(messages),
                "file_path": filepath,
                "filename": filename,
                "parsed_file_path": parsed_filepath,
                "parsed_filename": parsed_filename,
                "channel_name": channel_name
            })
        else:
            return create_success_response({
                "action": "cached",
                "channel_id": channel_id,
                "message": "Using existing fresh data"
            })
            
    except Exception as e:
        return create_error_response("Failed to check and dump channel data", str(e))


def _get_channel_name_from_config(config, channel_id: str) -> str:
    """Extract the actual channel name from the config file by reading the raw YAML"""
    try:
        import yaml
        
        # Get the config file path
        config_path = config.get('_config_path', 'config/slack.yaml')
        
        # Read the raw YAML file to extract comments
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find the line with the channel ID and extract the comment
        for line in lines:
            if f'"{channel_id}"' in line and '#' in line:
                # Extract the comment part (everything after #)
                comment_part = line.split('#', 1)[1].strip()
                if comment_part:
                    # Remove any leading/trailing whitespace and return
                    return f"#{comment_part}"
        
        # Fallback: use team name if no comment found
        slack_channels = config.get("slack_channels", {})
        team_id = slack_channels.get(channel_id, "unknown")
        return f"#{team_id}-channel"
        
    except Exception as e:
        # Fallback: use team name
        slack_channels = config.get("slack_channels", {})
        team_id = slack_channels.get(channel_id, "unknown")
        return f"#{team_id}-channel"


def _extract_full_message_content(message: dict, config: dict) -> dict:
    """Extract full message content including rich app/bot messages"""
    
    # Base fields
    timestamp = message.get('ts')
    user_id = message.get('user', 'Unknown')
    basic_text = message.get('text', '')
    app_id = message.get('app_id')
    bot_id = message.get('bot_id')
    
    # Initialize result
    result = {
        'timestamp': timestamp,
        'user_id': user_id,
        'app_id': app_id,
        'bot_id': bot_id,
        'display_name': 'Unknown',  # Will be set after extracting content
        'basic_text': basic_text,
        'rich_content': '',
        'full_content': basic_text
    }
    
    # Extract rich content from blocks
    if 'blocks' in message:
        block_texts = []
        for block in message['blocks']:
            if block.get('type') == 'section' and 'text' in block:
                block_text = block['text'].get('text', '')
                if block_text:
                    block_texts.append(block_text)
            elif block.get('type') == 'context' and 'elements' in block:
                for element in block['elements']:
                    if element.get('type') == 'text':
                        block_text = element.get('text', '')
                        if block_text:
                            block_texts.append(block_text)
        
        if block_texts:
            result['rich_content'] = '\n'.join(block_texts)
    
    # Extract content from attachments (common in app messages)
    if 'attachments' in message:
        attachment_texts = []
        
        for attachment in message['attachments']:
            # Main attachment text
            if 'text' in attachment:
                attachment_texts.append(attachment['text'])
            
            # Author information
            if 'author_name' in attachment:
                attachment_texts.append(f"From: {attachment['author_name']}")
            
            # Footer (metadata)
            if 'footer' in attachment:
                attachment_texts.append(f"Sender: {attachment['footer']}")
                
            # Title if present
            if 'title' in attachment:
                attachment_texts.append(f"Title: {attachment['title']}")
        
        if attachment_texts:
            if result['rich_content']:
                result['rich_content'] += '\n\n' + '\n'.join(attachment_texts)
            else:
                result['rich_content'] = '\n'.join(attachment_texts)
    
    # Combine rich content with basic text
    if result['rich_content']:
        result['full_content'] = result['rich_content']
        if basic_text and basic_text.strip() and basic_text.strip() != '*Alert*':
            result['full_content'] += '\n' + basic_text
    else:
        result['full_content'] = basic_text
    
    # Set display name using pattern detection based on full content
    result['display_name'] = _get_message_sender_name(user_id, bot_id, app_id, result['full_content'], config)
    
    return result


def _get_message_sender_name(user_id: str, bot_id: str, app_id: str, message_content: str, config: dict) -> str:
    """Get display name for message sender (user, bot, or app) with pattern detection"""
    
    # Priority: Bot ID mapping > User ID mapping > Pattern detection > Raw IDs
    if bot_id:
        bot_mappings = config.get('bot_display_names', {})
        if bot_id in bot_mappings:
            return bot_mappings[bot_id]
        else:
            return f"Bot-{bot_id[:8]}"  # Truncated bot ID
    
    # Check for app-based bot (fallback)
    if app_id:
        app_mappings = config.get('app_display_names', {})  # Future enhancement
        if app_id in app_mappings:
            return app_mappings[app_id]
        else:
            return f"App-{app_id[:8]}"  # Truncated app ID
    
    # User mapping
    if user_id and user_id != 'Unknown':
        user_mappings = config.get('user_display_names', {})
        return user_mappings.get(user_id, user_id)
    
    # Pattern-based detection for known message types
    if message_content:
        message_lower = message_content.lower()
        
        # RHIVOS maintenance alerts
        if ('rhivos' in message_lower or 'auto-toolchain.redhat.com' in message_lower or 
            'rhivos-webserver' in message_lower or 'rhivos webserver' in message_lower):
            return 'Rhivos-webserver notifier'
            
        # SP-RHIVOS alerts
        if ('sp-rhivos' in message_lower or 'sp rhivos' in message_lower or
            'software platform rhivos' in message_lower):
            return 'SP-RHIVOS notifier'
            
        # Assessment bot patterns
        if ('assessment' in message_lower and ('deployment' in message_lower or 'automated' in message_lower)):
            return 'Assessment bot'
    
    # Channel-specific message detection
    # Check if this is likely a RHIVOS maintenance alert based on pattern
    if message_content == '*Alert*':
        # These are likely RHIVOS maintenance alerts since they:
        # 1. Consistently appear on specific days/times
        # 2. Contain only '*Alert*' text
        # 3. Come from unknown/system sources
        return 'Rhivos-webserver notifier'
    
    return 'Unknown'


def _get_search_patterns(client, config, search_term: str) -> list:
    # Add mapped variations
    try:
        user_mappings = config.get('user_display_names', {})
        bot_mappings = config.get('bot_display_names', {})
        
        patterns = [search_term.lower()]
        
        # Add mapped variations
        if search_term.lower() in user_mappings:
            patterns.append(user_mappings[search_term.lower()].lower())
        
        # Add bot mapping variations
        if search_term.lower() in bot_mappings.values():
            patterns.append(search_term.lower())
        
        # Add reverse mappings
        for display_name, mention in user_mappings.items():
            if mention.lower() == search_term.lower():
                patterns.append(display_name.lower())
        
        return list(set(patterns))  # Remove duplicates
    except:
        return [search_term.lower()]


def _get_channel_name_from_config(config, channel_id: str) -> str:
    """Extract channel name from config comments"""
    try:
        config_file = config.get("config_file", "config/slack.yaml")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if channel_id in line:
                    # Look for comment with channel name
                    if '#' in line:
                        comment = line.split('#')[-1].strip()
                        if comment:
                            return comment
                    # If no comment found, return generic name
                    return f"Channel {channel_id}"
    except:
        pass
    
    return f"Channel {channel_id}"
