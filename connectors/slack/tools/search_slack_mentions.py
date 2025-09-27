"""
Search Slack mentions tool
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_channel_id, validate_team_name
import json


def search_slack_mentions_tool(client, config):
    """Create search_slack_mentions tool function"""
    
    def search_slack_mentions(channel_id: str, search_term: str, max_age_hours: int = 24) -> str:
        """Search for specific mentions or names in a Slack channel."""
        try:
            # Input validation
            validated_channel_id = validate_channel_id(channel_id)
            
            # First, get the channel data using the slack_reader tool
            from .slack_reader import read_slack_channel_tool
            read_tool = read_slack_channel_tool(client, config)
            channel_result = read_tool(validated_channel_id, max_age_hours)
            
            channel_data = json.loads(channel_result)
            if "error" in channel_data:
                return channel_result  # Return the original error response
            
            # Extract the Slack data
            slack_data = channel_data.get("data", "")
            if not slack_data:
                return create_error_response("No Slack data available for search")
            
            # Search for mentions
            matches = client.search_slack_mentions(slack_data, search_term)
            
            # Prepare response
            response_data = {
                "channel_id": validated_channel_id,
                "search_term": search_term,
                "matches_found": len(matches),
                "matches": matches,
                "source_file": channel_data.get("source_file", "unknown"),
                "data_action": channel_data.get("data_action", "unknown"),
                "search_patterns_used": _get_search_patterns(client, config, search_term)
            }
            
            return create_success_response(response_data)
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to search Slack mentions", str(e))
    
    return search_slack_mentions


def search_team_slack_mentions_tool(client, config):
    """Create search_team_slack_mentions tool function"""
    
    def search_team_slack_mentions(team: str, search_term: str, max_age_hours: int = 24) -> str:
        """Search for specific mentions or names across all channels for a team."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Get team channels
            slack_channels = config.get('slack_channels', {})
            team_channels = [channel_id for channel_id, team_id in slack_channels.items() 
                           if team_id.lower() == validated_team.lower()]
            
            if not team_channels:
                return create_error_response(f"No channels found for team: {team}")
            
            # Create search_slack_mentions tool function
            search_tool = search_slack_mentions_tool(client, config)
            
            all_matches = {}
            total_matches = 0
            
            # Search each channel
            for channel_id in team_channels:
                channel_result = search_tool(channel_id, search_term, max_age_hours)
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
                "team": validated_team,
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
            return create_error_response("Failed to search team Slack mentions", str(e))
    
    return search_team_slack_mentions


def _get_search_patterns(client, config, search_term: str) -> list:
    """Get the search patterns that will be used for the search term"""
    try:
        user_mappings = config.get('user_display_names', {})
        
        patterns = [search_term.lower()]
        
        # Add mapped variations
        if search_term.lower() in user_mappings:
            patterns.append(user_mappings[search_term.lower()].lower())
        
        # Add reverse mappings
        for display_name, mention in user_mappings.items():
            if mention.lower() == search_term.lower():
                patterns.append(display_name.lower())
        
        return list(set(patterns))  # Remove duplicates
    except:
        return [search_term.lower()]
