"""
Unified Slack Tools
Combines individual channel and team operations into unified tools
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_channel_id, validate_team_name
from .slack_helpers import (
    dump_single_channel,
    dump_team_channels,
    read_single_channel,
    read_team_channels,
    search_single_channel,
    search_team_channels,
    check_and_dump_if_needed,
    get_channel_name_from_config
)
import os
import json
from datetime import datetime


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
                return dump_single_channel(client, config, target, latest_date)
            else:
                # It's a team name - dump all team channels
                return dump_team_channels(client, config, target, latest_date)
                
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
                return read_single_channel(client, config, target, max_age_hours)
            else:
                # It's a team name - read all team channels
                return read_team_channels(client, config, target, max_age_hours)
                
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
                return search_single_channel(client, config, target, search_term, max_age_hours)
            else:
                # It's a team name - search all team channels
                return search_team_channels(client, config, target, search_term, max_age_hours)
                
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
