"""
Simple Slack Data Dumper
Fetches Slack channel data and saves as text files
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_channel_id, validate_team_name
import os
from datetime import datetime
import asyncio
import threading
import json


def dump_slack_channel_tool(client, config):
    """Create dump_slack_channel tool function"""
    
    def dump_slack_channel(channel_id: str) -> str:
        """Dump a specific Slack channel to text file."""
        try:
            # Input validation
            validated_channel_id = validate_channel_id(channel_id)
            
            # Get channel history using async function
            def run_async():
                return asyncio.run(client.get_channel_history(validated_channel_id))
            
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
            
            # Create filename without timestamp (single file per channel)
            filename = f"{validated_channel_id}_slack_dump.txt"
            filepath = os.path.join(dump_dir, filename)
            
            # Write messages to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Slack Channel Dump\n")
                f.write(f"# Channel ID: {validated_channel_id}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Total Messages: {len(messages)}\n\n")
                
                for message in messages:
                    timestamp = datetime.fromtimestamp(float(message['ts']))
                    user = message.get('user', 'Unknown')
                    text = message.get('text', '')
                    
                    f.write(f"[{timestamp.isoformat()}] {user}: {text}\n")
            
            return create_success_response({
                "channel_id": validated_channel_id,
                "messages_count": len(messages),
                "file_path": filepath,
                "filename": filename
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to dump Slack channel", str(e))
    
    return dump_slack_channel


def dump_team_slack_data_tool(client, config):
    """Create dump_team_slack_data tool function"""
    
    def dump_team_slack_data(team: str) -> str:
        """Dump all Slack channels for a team."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Get team's channels from slack-config.yaml
            slack_channels = config.get("slack_channels", {})
            team_channels = [channel_id for channel_id, team_id in slack_channels.items() if team_id == validated_team]
            
            if not team_channels:
                return create_error_response(f"No Slack channels found for team '{team}'")
            
            # Create dump_slack_channel tool function
            dump_tool = dump_slack_channel_tool(client, config)
            
            results = []
            for channel_id in team_channels:
                result = dump_tool(channel_id)
                result_data = json.loads(result)
                if "error" not in result_data:
                    results.append(result_data)
            
            return create_success_response({
                "team": validated_team,
                "channels_processed": len(results),
                "results": results
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to dump team Slack data", str(e))
    
    return dump_team_slack_data


def list_team_slack_channels_tool(client, config):
    """Create list_team_slack_channels tool function"""
    
    def list_team_slack_channels(team: str) -> str:
        """List all Slack channels configured for a team."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Get team's channels from slack-config.yaml
            slack_channels = config.get("slack_channels", {})
            team_channels = [channel_id for channel_id, team_id in slack_channels.items() if team_id == validated_team]
            
            return create_success_response({
                "team": validated_team,
                "channels": team_channels,
                "count": len(team_channels)
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to list team Slack channels", str(e))
    
    return list_team_slack_channels
