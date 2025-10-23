# Slack Thread Replies Implementation

## Summary

This document describes the implementation of thread reply capture in the Slack MCP tools.

## Changes Made

### 1. Added `get_thread_replies()` Method to SlackClient
**File:** `connectors/slack/client.py`

Added a new async method that calls the Slack `conversations.replies` API endpoint to fetch all replies in a thread:

```python
async def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
    """Get all replies in a thread using Slack API"""
    # Calls conversations.replies endpoint
    # Marks each reply with 'is_thread_reply' and 'parent_thread_ts' fields
```

### 2. Modified `get_channel_history()` Method
**File:** `connectors/slack/client.py`

Enhanced the method to:
- Check each message for `reply_count > 0` (indicates the message has thread replies)
- Call `get_thread_replies()` for messages with threads
- Add all thread replies to the messages list (skipping the parent message which is returned first)
- Continue on error to avoid breaking if individual thread fetches fail

```python
# Fetch thread replies for messages that have threads
all_messages = []
for message in messages:
    all_messages.append(message)
    
    # Check if message has thread replies (reply_count > 0 means it has replies)
    if message.get('reply_count', 0) > 0:
        try:
            thread_replies = await self.get_thread_replies(channel_id, message['ts'])
            # Skip the first reply as it's the parent message itself
            if len(thread_replies) > 1:
                all_messages.extend(thread_replies[1:])
        except Exception as e:
            print(f"Warning: Failed to fetch thread replies for message {message.get('ts')}: {str(e)}")
```

### 3. Updated Dump Formatting
**File:** `connectors/slack/tools/unified_slack_tools.py`

Modified three locations in the dump functions to format thread replies with visual indicators:

#### Raw Dumps (3 locations):
```python
# Mark thread replies with indentation
if message.get('is_thread_reply') and message.get('thread_ts') != message.get('ts'):
    f.write(f"  ↳ [{timestamp.isoformat()}] {display_name}: {full_content}\n")
else:
    f.write(f"[{timestamp.isoformat()}] {display_name}: {full_content}\n")
```

#### Parsed Dumps (3 locations):
```python
# Write message with clear formatting (indicate thread replies)
is_thread_reply = message.get('is_thread_reply') and message.get('thread_ts') != message.get('ts')
if is_thread_reply:
    f.write(f"  Thread Reply {i+1} - {formatted_date}\n")
    f.write(f"  From: {user}\n")
    f.write(f"  {'-'*38}\n")
else:
    f.write(f"Message {i+1} - {formatted_date}\n")
    f.write(f"From: {user}\n")
    f.write(f"{'-'*40}\n")
```

## How It Works

1. **Detection**: When fetching channel history, the Slack API returns messages with a `reply_count` field if they have thread replies
2. **Fetching**: For each message with `reply_count > 0`, we make an additional API call to `conversations.replies`
3. **Insertion**: Thread replies are inserted immediately after their parent message in chronological order
4. **Formatting**: Thread replies are marked with:
   - `↳` prefix and indentation in raw dumps
   - "Thread Reply" label and indentation in parsed dumps

## Visual Format Examples

### Raw Dump Format:
```
[2025-10-11T14:53:03.918809] Ryan Smith: Hi all, does anyone know where this `/` prefix came from?
  ↳ [2025-10-11T14:55:12.123456] John Doe: I think it was added in the last deployment
  ↳ [2025-10-11T14:56:30.234567] Jane Smith: Yes, confirmed. Check PR#1234
[2025-10-11T15:00:00.000000] Other User: Next topic...
```

### Parsed Dump Format:
```
Message 1 - 2025-10-11 14:53
From: Ryan Smith
----------------------------------------
Hi all, does anyone know where this `/` prefix came from?

  Thread Reply 2 - 2025-10-11 14:55
  From: John Doe
  --------------------------------------
  I think it was added in the last deployment

  Thread Reply 3 - 2025-10-11 14:56
  From: Jane Smith
  --------------------------------------
  Yes, confirmed. Check PR#1234

Message 4 - 2025-10-11 15:00
From: Other User
----------------------------------------
Next topic...
```

## How to Verify

### Method 1: Check Message Counts
Before this change, dumps only included top-level messages. After this change, the message count should be higher if threads exist in the channel.

Compare:
- Old dumps: ~1000 messages (API limit for conversations.history)
- New dumps: 1000+ messages (includes thread replies)

### Method 2: Search for Thread Indicators
```bash
# Search for thread reply indicators in raw dumps
grep "  ↳" connectors/slack/slack_dump/slack_dumps/*.txt

# Search for thread reply indicators in parsed dumps
grep "Thread Reply" connectors/slack/slack_dump/slack_dumps_parsed/*.txt
```

### Method 3: Test with Known Threaded Message
If you know a message has replies (e.g., via Slack UI), search for it and verify the replies appear immediately after:

```bash
# Find the message
grep -A 5 "auto-product-build-downstream" connectors/slack/slack_dump/slack_dumps/C04JDFLHJN6_slack_dump.txt
```

### Method 4: Run Test Script
```bash
cd /Users/pacaramu/Documents/Git/work-planner
source venv/bin/activate
# Set environment variables
export SLACK_XOXC_TOKEN="your-token"
export SLACK_XOXD_TOKEN="your-token"
python test_thread_detection.py
```

This will show:
- How many messages have threads
- How many thread replies were fetched
- Details about specific threaded messages

## Important Notes

1. **API Limits**: Each thread requires an additional API call. Channels with many threads may take longer to dump.

2. **Error Handling**: If fetching a specific thread fails, the dump continues with other messages. A warning is printed to console.

3. **Thread Detection**: Only messages with `reply_count > 0` trigger thread fetching. This field is set by Slack when a message has replies.

4. **Parent Message**: The `conversations.replies` API returns the parent message as the first item. We skip it since we already have it from `conversations.history`.

5. **Chronological Order**: Thread replies are inserted immediately after their parent message, preserving the conversational flow.

## Testing Status

✅ Implementation completed
✅ Code changes applied to client.py
✅ Code changes applied to unified_slack_tools.py (3 locations)
✅ No linter errors
⚠️ Verification pending: Need to check if specific messages have `reply_count` field

## Next Steps

To fully verify the implementation is working:

1. **Check the Slack API Response**: Verify that Slack is actually including `reply_count` in the messages
2. **Test with Known Thread**: Find a message in Slack UI that has replies, then verify it appears with thread replies in the dump
3. **Compare Message Counts**: Compare old vs new dumps to see if more messages are captured

If no thread replies appear after this implementation, it may indicate:
- The specific channels don't have many threaded conversations
- Slack API may not be returning `reply_count` field (API version or permission issue)
- Need to check Slack workspace settings or API parameters

