"""
Slack client wrapper
"""

import os
import httpx
from typing import List, Dict, Any


class SlackClient:
    """Slack client wrapper"""
    
    def __init__(self, config: dict):
        self.config = config
        self.xoxc_token = os.getenv('SLACK_XOXC_TOKEN')
        self.xoxd_token = os.getenv('SLACK_XOXD_TOKEN')
        self.base_url = "https://slack.com/api"
        
        if not all([self.xoxc_token, self.xoxd_token]):
            raise RuntimeError("Missing SLACK_XOXC_TOKEN or SLACK_XOXD_TOKEN environment variables")
    
    async def get_channel_history(self, channel_id: str) -> List[Dict[str, Any]]:
        """Get channel history using Slack API"""
        headers = {
            "Authorization": f"Bearer {self.xoxc_token}",
            "Content-Type": "application/json",
        }
        cookies = {"d": self.xoxd_token}
        
        url = f"{self.base_url}/conversations.history"
        payload = {"channel": channel_id}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=headers, cookies=cookies, json=payload, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("ok"):
                    return data.get("messages", [])
                else:
                    raise RuntimeError(f"Slack API error: {data.get('error', 'Unknown error')}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to fetch Slack channel history: {str(e)}")
    
    def search_slack_mentions(self, slack_data: str, search_term: str) -> List[str]:
        """Search for specific mentions or names in Slack data"""
        try:
            # Load user display names from slack config
            user_mappings = self.config.get('user_display_names', {})
            
            # Create search patterns for the term
            search_patterns = [search_term.lower()]
            
            # Add mapped variations if they exist
            if search_term.lower() in user_mappings:
                search_patterns.append(user_mappings[search_term.lower()].lower())
            
            # Add reverse mappings
            for display_name, mention in user_mappings.items():
                if mention.lower() == search_term.lower():
                    search_patterns.append(display_name.lower())
            
            # Search through the data
            lines = slack_data.split('\n')
            matches = []
            
            for line in lines:
                line_lower = line.lower()
                for pattern in search_patterns:
                    if pattern in line_lower:
                        matches.append(line.strip())
                        break
            
            return matches
        except Exception as e:
            raise RuntimeError(f"Failed to search Slack mentions: {str(e)}")
