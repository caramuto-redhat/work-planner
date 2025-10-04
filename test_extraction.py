#!/usr/bin/env python3
"""
Test the enhanced message extraction logic
"""

import sys
import os
sys.path.append('/Users/pacaramu/Documents/Git/work-planner')

def test_extraction():
    """Test the enhanced extraction logic"""
    
    try:
        from connectors.slack.tools.unified_slack_tools import _extract_full_message_content, _get_message_sender_name
        
        # Test config (what we set up)
        config = {
            'bot_display_names': {
                "B1234567890": "Rhivos-webserver notifier",
                "B06B9BCD456": "SP-RHIVOS notifier",
                "B1234567891": "Assessment bot"
            },
            'user_display_names': {
                "U1234567890": "Test User"
            }
        }
        
        print("🧪 Testing Enhanced Message Extraction Logic")
        print("=" * 80)
        
        # Test case 1: Regular user message
        user_message = {
            'ts': '1695945601.850599',
            'user': 'U1234567890',
            'text': 'Hey team, what about the deployment?',
            'app_id': None,
            'bot_id': None
        }
        
        print("\n📝 TEST 1: Regular User Message")
        print("-" * 40)
        extracted_user = _extract_full_message_content(user_message, config)
        print(f"Input text: {user_message['text']}")
        print(f"Display name: {extracted_user['display_name']}")
        print(f"Full content: {extracted_user['full_content'][:50]}...")
        
        # Test case 2: Bot message with rich content (RHIVOS-style)
        bot_message = {
            'ts': '1695945601.850599',
            'user': None,
            'app_id': 'A1234567890',
            'bot_id': 'B1234567890',
            'text': '*Alert*',
            'attachments': [
                {
                    'text': 'The RHIVOS webserver at rhivos.auto-toolchain.redhat.com will instantiate self maintenance ten minutes from now. The maintenance work is expected to last approximately five minutes.',
                    'author_name': 'Rhivos-webserver',
                    'footer': 'Rhivos-webserver | Host: ip-10-30-75-235.us-east-2.aws.redhat.com | Time: 2025-09-28 22:00:01'
                }
            ]
        }
        
        print("\n🤖 TEST 2: Bot Message with Rich Content")
        print("-" * 40)
        extracted_bot = _extract_full_message_content(bot_message, config)
        print(f"Input text: {bot_message['text']}")
        print(f"Display name: {extracted_bot['display_name']}")
        print(f"Bot ID: {extracted_bot['bot_id']}")
        print(f"Rich content: {extracted_bot['rich_content'][:100]}...")
        print(f"Full content: {extracted_bot['full_content'][:150]}...")
        
        # Test case 3: Message without bot_id but with app_id (common)
        app_message = {
            'ts': '1695945601.850599',
            'user': None,
            'app_id': 'A1234567890',
            'bot_id': None,  # No bot_id, only app_id
            'text': '*Alert*',
            'attachments': [
                {
                    'text': 'System maintenance scheduled',
                    'author_name': 'Auto-notifier'
                }
            ]
        }
        
        print("\n📱 TEST 3: App Message (no bot_id)")
        print("-" * 40)
        extracted_app = _extract_full_message_content(app_message, config)
        print(f"Input text: {app_message['text']}")
        print(f"Display name: {extracted_app['display_name']}")
        print(f"App ID: {extracted_app['app_id']}")
        print(f"Bot ID: {extracted_app['bot_id']}")
        print(f"Full content: {extracted_app['full_content']}")
        
        print("\n✅ CONCLUSION:")
        print("If your RHIVOS messages don't have bot_id field populated,")
        print("they would fall back to showing 'App-A1234567' instead of 'Rhivos-webserver notifier'")
        print("Check the actual Slack API response structure to identify the correct field.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraction()
