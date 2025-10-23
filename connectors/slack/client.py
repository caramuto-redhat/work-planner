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
    
    async def get_channel_history(self, channel_id: str, latest_date: str = None, days_back: int = None) -> List[Dict[str, Any]]:
        """Get channel history using Slack API, defaults to config history_days"""
        from datetime import datetime, timedelta
        
        # Get days_back from config if not specified
        if days_back is None:
            days_back = self.config.get('data_collection', {}).get('history_days', 30)
        
        headers = {
            "Authorization": f"Bearer {self.xoxc_token}",
            "Content-Type": "application/json",
        }
        cookies = {"d": self.xoxd_token}
        
        url = f"{self.base_url}/conversations.history"
        
        # Calculate oldest timestamp based on config or parameter
        oldest_dt = datetime.now() - timedelta(days=days_back)
        oldest_timestamp = int(oldest_dt.timestamp())
        
        payload = {
            "channel": channel_id,
            "limit": 1000,  # Fetch up to 1000 messages (Slack API maximum)
            "oldest": str(oldest_timestamp)  # Default to last 30 days
        }
        
        print(f"📅 Fetching messages from the last {days_back} days (since {oldest_dt.strftime('%Y-%m-%d')})")
        
        # Add latest date if provided
        if latest_date:
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
                    
                    print(f"📊 Fetched {len(messages)} messages")
                    
                    # DEBUG: Log sample message fields
                    import json
                    if messages:
                        sample_msg = messages[0]
                        print(f"🔍 Sample message fields: {list(sample_msg.keys())}")
                        
                        # Check for Ryan Smith's message specifically
                        for msg in messages:
                            if 'prefix' in str(msg.get('text', '')).lower():
                                print(f"🎯 Found Ryan's message!")
                                print(f"   Fields: {list(msg.keys())}")
                                print(f"   ts: {msg.get('ts')}")
                                print(f"   thread_ts: {msg.get('thread_ts', 'NOT PRESENT')}")
                                print(f"   reply_count: {msg.get('reply_count', 'NOT PRESENT')}")
                                print(f"   reply_users_count: {msg.get('reply_users_count', 'NOT PRESENT')}")
                    
                    # CRITICAL INSIGHT: conversations.history does NOT include thread_ts in PARENT messages!
                    # Only the REPLIES have thread_ts. We need to check messages for potential replies.
                    # To avoid timing out, only check RECENT messages (last 7 days)
                    from datetime import datetime, timedelta
                    
                    cutoff_time = datetime.now() - timedelta(days=7)
                    cutoff_ts = float(cutoff_time.timestamp())
                    
                    recent_messages = [m for m in messages if float(m.get('ts', 0)) >= cutoff_ts]
                    print(f"🧵 Checking {len(recent_messages)}/{len(messages)} recent messages (last 7 days) for thread replies...")
                    
                    all_messages = []
                    thread_replies_by_ts = {}
                    checked = 0
                    threads_found = 0
                    errors = 0
                    
                    # Check each recent message to see if it has replies
                    for message in recent_messages:
                        checked += 1
                        if checked % 5 == 0:
                            print(f"  Progress: {checked}/{len(recent_messages)} checked, {threads_found} threads found, {errors} errors...")
                        
                        msg_ts = message.get('ts')
                        if msg_ts and msg_ts not in thread_replies_by_ts:
                            try:
                                # Try to fetch replies for this message
                                replies = await self.get_thread_replies(channel_id, msg_ts)
                                # If there's more than 1 message (parent + replies), this is a thread
                                if len(replies) > 1:
                                    threads_found += 1
                                    thread_replies_by_ts[msg_ts] = replies
                                    msg_preview = str(message.get('text', ''))[:40]
                                    print(f"  ✓ Found thread: '{msg_preview}...' has {len(replies)-1} replies")
                            except Exception as e:
                                errors += 1
                                if errors <= 3:  # Only log first 3 errors
                                    print(f"  ⚠️  Error checking ts={msg_ts}: {str(e)[:60]}")
                    
                    print(f"✅ Thread check complete: {threads_found} threads found, {errors} errors")
                    
                    # Now merge messages with their thread replies
                    for message in messages:
                        all_messages.append(message)
                        
                        # If this message is a thread parent, add its replies
                        msg_ts = message.get('ts')
                        if msg_ts in thread_replies_by_ts:
                            replies = thread_replies_by_ts[msg_ts]
                            # Skip the first reply as it's the parent message itself
                            if len(replies) > 1:
                                all_messages.extend(replies[1:])
                    
                    if threads_found > 0:
                        print(f"✅ Fetched {threads_found} threads, total {len(all_messages)} messages (including replies)")
                    else:
                        print(f"✅ No threads found in the fetched messages")
                    
                    return all_messages
                else:
                    raise RuntimeError(f"Slack API error: {data.get('error', 'Unknown error')}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to fetch Slack channel history: {str(e)}")
    
    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Get all replies in a thread using Slack API"""
        # For XOXC/XOXD tokens, use GET with query params (mimics browser behavior)
        headers = {
            "Authorization": f"Bearer {self.xoxc_token}",
        }
        cookies = {"d": self.xoxd_token}
        
        url = f"{self.base_url}/conversations.replies"
        
        # Use query parameters with GET request for user token compatibility
        params = {
            "channel": channel_id,
            "ts": thread_ts,
            "limit": 1000,
            "inclusive": True  # Include the parent message
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Try GET request first (common for user tokens)
                response = await client.get(
                    url, headers=headers, cookies=cookies, params=params, timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("ok"):
                    replies = data.get("messages", [])
                    # Mark each reply with thread context for better formatting
                    for reply in replies:
                        reply['is_thread_reply'] = True
                        reply['parent_thread_ts'] = thread_ts
                    return replies
                else:
                    # Log the error but don't crash - some errors are expected
                    error_msg = data.get('error', 'Unknown error')
                    print(f"    API error for ts={thread_ts}: {error_msg}")
                    raise RuntimeError(f"Slack API error: {error_msg}")
                    
            except Exception as e:
                raise RuntimeError(f"Failed to fetch thread replies: {str(e)}")
    
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
