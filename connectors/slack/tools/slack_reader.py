"""
Simple Slack Data Reader
Reads Slack dump files and automatically ensures latest data
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_channel_id, validate_team_name
import os
import asyncio
import threading
import json
from datetime import datetime, timedelta


def check_and_dump_if_needed(client, config, channel_id: str, max_age_hours: int = 24) -> str:
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
                    timestamp = datetime.fromtimestamp(float(message['ts']))
                    user = message.get('user', 'Unknown')
                    text = message.get('text', '')
                    
                    f.write(f"[{timestamp.isoformat()}] {user}: {text}\n")
            
            return create_success_response({
                "action": "dumped",
                "channel_id": channel_id,
                "messages_count": len(messages),
                "file_path": filepath,
                "filename": filename
            })
        else:
            return create_success_response({
                "action": "cached",
                "channel_id": channel_id,
                "message": "Using existing fresh data"
            })
            
    except Exception as e:
        return create_error_response("Failed to check and dump channel data", str(e))


def read_slack_channel_tool(client, config):
    """Create read_slack_channel tool function"""
    
    def read_slack_channel(channel_id: str, max_age_hours: int = 24) -> str:
        """Read the latest Slack dump for a specific channel. Automatically dumps fresh data if needed."""
        try:
            # Input validation
            validated_channel_id = validate_channel_id(channel_id)
            
            # First, ensure we have fresh data
            dump_result = check_and_dump_if_needed(client, config, validated_channel_id, max_age_hours)
            dump_data = json.loads(dump_result)
            if "error" in dump_data:
                return dump_result  # Return the original error response
            
            dump_dir = config.get("data_collection", {}).get("dump_directory", "slack_dumps")
            
            # Find the dump file for this channel
            filename = f"{validated_channel_id}_slack_dump.txt"
            filepath = os.path.join(dump_dir, filename)
            
            if not os.path.exists(filepath):
                return create_error_response(f"No Slack dump found for channel '{validated_channel_id}' after attempting to create one.")
            
            # Read content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get file stats
            stat = os.stat(filepath)
            
            return create_success_response({
                "channel_id": validated_channel_id,
                "data": content,
                "source_file": filename,
                "file_path": filepath,
                "file_size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "data_action": dump_data.get("action", "unknown"),
                "note": "Raw Slack data for LLM analysis - automatically refreshed if needed"
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to read Slack channel", str(e))
    
    return read_slack_channel


def read_team_slack_data_tool(client, config):
    """Create read_team_slack_data tool function"""
    
    def read_team_slack_data(team: str, max_age_hours: int = 24) -> str:
        """Read all Slack data for a team. Automatically dumps fresh data if needed."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Get team's channels from slack-config.yaml
            slack_channels = config.get("slack_channels", {})
            team_channels = [channel_id for channel_id, team_id in slack_channels.items() if team_id == validated_team]
            
            if not team_channels:
                return create_error_response(f"No Slack channels found for team '{team}'")
            
            # Create read_slack_channel tool function
            read_tool = read_slack_channel_tool(client, config)
            
            all_data = {}
            errors = []
            actions_taken = []
            
            for channel_id in team_channels:
                result = read_tool(channel_id, max_age_hours)
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
                "team": validated_team,
                "channels": list(all_data.keys()),
                "data": all_data,
                "errors": errors,
                "actions_taken": actions_taken,
                "note": "Raw Slack data for all team channels - automatically refreshed if needed - let LLM analyze"
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to read team Slack data", str(e))
    
    return read_team_slack_data


def list_slack_dumps_tool(client, config):
    """Create list_slack_dumps tool function"""
    
    def list_slack_dumps(team: str = None) -> str:
        """List all available Slack dumps, optionally filtered by team."""
        try:
            dump_dir = config.get("data_collection", {}).get("dump_directory", "slack_dumps")
            
            # Check if dump directory exists
            if not os.path.exists(dump_dir):
                return create_success_response({
                    "dumps": [],
                    "count": 0,
                    "note": "No dump directory found. Run dump_slack_channel first."
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


def get_slack_dump_summary_tool(client, config):
    """Create get_slack_dump_summary tool function"""
    
    def get_slack_dump_summary(team: str) -> str:
        """Get a summary of Slack dumps for a team."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Get team's channels from slack-config.yaml
            slack_channels = config.get("slack_channels", {})
            team_channels = [channel_id for channel_id, team_id in slack_channels.items() if team_id == validated_team]
            
            if not team_channels:
                return create_error_response(f"No Slack channels found for team '{team}'")
            
            # Get dumps for this team
            list_tool = list_slack_dumps_tool(client, config)
            dumps_result = list_tool(validated_team)
            dumps_data = json.loads(dumps_result)
            if "error" in dumps_data:
                return dumps_result  # Return the original error response
            dumps = dumps_data["dumps"]
            
            # Calculate summary statistics
            total_dumps = len(dumps)
            total_size = sum(dump["size_bytes"] for dump in dumps)
            channels_with_dumps = len(set(dump["channel_id"] for dump in dumps))
            
            # Get latest dump for each channel
            latest_dumps = {}
            for dump in dumps:
                channel_id = dump["channel_id"]
                if channel_id not in latest_dumps or dump["created"] > latest_dumps[channel_id]["created"]:
                    latest_dumps[channel_id] = dump
            
            return create_success_response({
                "team": validated_team,
                "total_dumps": total_dumps,
                "total_size_bytes": total_size,
                "channels_with_dumps": channels_with_dumps,
                "configured_channels": team_channels,
                "latest_dumps": latest_dumps,
                "summary": f"Team '{team}' has {total_dumps} dumps across {channels_with_dumps} channels"
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to get Slack dump summary", str(e))
    
    return get_slack_dump_summary


def force_fresh_slack_dump_tool(client, config):
    """Create force_fresh_slack_dump tool function"""
    
    def force_fresh_slack_dump(team: str) -> str:
        """Force a fresh dump of all Slack channels for a team (ignores cache)."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Get team's channels from slack-config.yaml
            slack_channels = config.get("slack_channels", {})
            team_channels = [channel_id for channel_id, team_id in slack_channels.items() if team_id == validated_team]
            
            if not team_channels:
                return create_error_response(f"No Slack channels found for team '{team}'")
            
            results = []
            errors = []
            
            for channel_id in team_channels:
                # Force dump by setting max_age_hours to 0
                result = check_and_dump_if_needed(client, config, channel_id, max_age_hours=0)
                result_data = json.loads(result)
                if "error" not in result_data:
                    results.append(result_data)
                else:
                    errors.append(f"Channel {channel_id}: {result_data['error']}")
            
            return create_success_response({
                "team": validated_team,
                "channels_processed": len(results),
                "results": results,
                "errors": errors,
                "note": "Forced fresh dump of all team channels"
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to force fresh Slack dump", str(e))
    
    return force_fresh_slack_dump
