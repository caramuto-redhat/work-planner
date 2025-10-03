"""
Slack client wrapper
"""

import os
import httpx
import json
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse


class SlackClient:
    """Slack client wrapper"""
    
    def __init__(self, config: dict):
        self.config = config
        self.xoxc_token = os.getenv('SLACK_XOXC_TOKEN')
        self.xoxd_token = os.getenv('SLACK_XOXD_TOKEN')
        self.base_url = "https://slack.com/api"
        
        if not all([self.xoxc_token, self.xoxd_token]):
            raise RuntimeError("Missing SLACK_XOXC_TOKEN or SLACK_XOXD_TOKEN environment variables")
    
    async def get_channel_history(self, channel_id: str, latest_date: str = None) -> List[Dict[str, Any]]:
        """Get channel history using Slack API"""
        headers = {
            "Authorization": f"Bearer {self.xoxc_token}",
            "Content-Type": "application/json",
        }
        cookies = {"d": self.xoxd_token}
        
        url = f"{self.base_url}/conversations.history"
        payload = {
            "channel": channel_id,
            "limit": 1000,  # Fetch up to 1000 messages (Slack API maximum)
            "oldest": "0"   # Start from the beginning of channel history
        }
        
        # Add latest date if provided
        if latest_date:
            from datetime import datetime
            try:
                # Convert date string to Unix timestamp
                dt = datetime.strptime(latest_date, "%Y-%m-%d")
                timestamp = int(dt.timestamp())
                payload["latest"] = str(timestamp)
            except ValueError:
                raise ValueError(f"Invalid date format. Use YYYY-MM-DD format. Got: {latest_date}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=headers, cookies=cookies, json=payload, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("ok"):
                    messages = data.get("messages", [])
                    # Reverse to get oldest first (Slack returns newest first by default)
                    messages.reverse()
                    return messages
                else:
                    raise RuntimeError(f"Slack API error: {data.get('error', 'Unknown error')}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to fetch Slack channel history: {str(e)}")
    
    async def download_attachment(self, url: str, filename: str = None) -> Optional[str]:
        """Download an attachment file from Slack"""
        try:
            headers = {
                "Authorization": f"Bearer {self.xoxc_token}",
            }
            cookies = {"d": self.xoxd_token}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, cookies=cookies, timeout=30.0)
                response.raise_for_status()
                
                # Determine filename from URL if not provided
                if not filename:
                    parsed_url = urlparse(url)
                    filename = parsed_url.path.split('/')[-1]
                    if not filename:
                        filename = "attachment"
                
                return filename, response.content
                
        except Exception as e:
            print(f"Warning: Failed to download attachment {url}: {str(e)}")
            return None, None
    
    def get_message_attachments(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from a message"""
        attachments = []
        
        # Check for files attachment
        if 'files' in message:
            for file_info in message.get('files', []):
                attachment_info = {
                    'id': file_info.get('id'),
                    'name': file_info.get('name', 'unnamed'),
                    'title': file_info.get('title', ''),
                    'mimetype': file_info.get('mimetype', ''),
                    'filetype': file_info.get('filetype', ''),
                    'url_private': file_info.get('url_private'),
                    'url_private_download': file_info.get('url_private_download'),
                    'size': file_info.get('size', 0),
                    'thumb_360': file_info.get('thumb_360'),
                    'preview': file_info.get('preview', ''),
                }
                attachments.append(attachment_info)
        
        # Check for blocks attachments (for uploaded files)
        if 'blocks' in message:
            for block in message.get('blocks', []):
                if block.get('type') == 'file':
                    element = block.get('elements', [{}])[0]
                    file_info = element.get('external_id', {})
                    if file_info:
                        attachment_info = {
                            'id': file_info.get('id'),
                            'name': file_info.get('name', 'unnamed'),
                            'title': file_info.get('title', ''),
                            'mimetype': file_info.get('mimetype', ''),
                            'filetype': file_info.get('filetype', ''),
                            'url_private': '',
                            'url_private_download': '',
                            'size': file_info.get('size', 0),
                            'preview': file_info.get('preview', ''),
                        }
                        attachments.append(attachment_info)
        
        return attachments
    
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
