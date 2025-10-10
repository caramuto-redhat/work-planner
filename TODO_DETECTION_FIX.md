# Paul TODO Detection Fix - Slack Mention Support

## Problem Identified

The TODO list was failing to detect comments mentioning Paul Caramuto's name in Slack channels (e.g., #toolchain-sla) because:

1. **How Slack stores mentions**: When someone types `@Paul` in Slack, it's stored as `<@U04N9LTR47M>` (the user ID), not as plain text "paul"
2. **Old detection logic**: The code was only searching for plain text patterns like `"paul"`, `"pacaramu"`, `"@paul"`, `"@pacaramu"`
3. **Result**: All Slack mentions using the `@mention` feature were being missed

## Solution Implemented

### Option 1: Check for User ID Directly (Chosen Approach)

**Why this approach?**
- ✅ **Reliable**: Matches actual Slack mentions (how Slack stores them)
- ✅ **Generic**: Can be easily configured for any user
- ✅ **Straightforward**: No text conversion overhead needed
- ✅ **Catches real mentions**: When someone types `@Paul` in Slack, it becomes `<@U04N9LTR47M>`

### Changes Made

#### 1. Configuration File: `config/mail_template.yaml`

Added new configuration section for Paul TODO detection:

```yaml
# Paul TODO Detection Configuration
# Configure user ID and patterns for TODO item detection
paul_todo_config:
  user_id: "U04N9LTR47M"  # Paul's Slack user ID (primary detection method)
  additional_patterns:     # Fallback plain text patterns (case-insensitive)
    - "paul"
    - "pacaramu"
```

**Benefits:**
- User ID is configurable (not hardcoded)
- Can be adapted for other users by changing the config
- Maintains fallback patterns for plain text mentions

#### 2. Script Updates: `.github/workflows/scripts/github_daily_report.py`

**a) Added configuration loader function:**
```python
def _load_paul_todo_config():
    """Load Paul TODO detection configuration from mail_template.yaml"""
    try:
        import yaml
        with open('config/mail_template.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config.get('paul_todo_config', {})
    except Exception as e:
        print(f'  ⚠️  Warning: Could not load Paul TODO config: {e}')
        # Fallback to default values
        return {
            'user_id': 'U04N9LTR47M',
            'additional_patterns': ['paul', 'pacaramu']
        }
```

**b) Updated `collect_team_data()` to load config:**
```python
# Load Paul TODO detection configuration
paul_todo_config = _load_paul_todo_config()

team_data = {
    ...
    'paul_todo_config': paul_todo_config  # Include Paul TODO config
}
```

**c) Updated `generate_paul_todo_items()` detection logic:**

**Slack mention detection:**
```python
# Load Paul TODO detection configuration
paul_config = team_data.get('paul_todo_config', {})
paul_user_id = paul_config.get('user_id', 'U04N9LTR47M')
additional_patterns = paul_config.get('additional_patterns', ['paul', 'pacaramu'])

print(f'  🔍 Using detection patterns: Slack mention <@{paul_user_id}>, text patterns: {additional_patterns}')

# Check if message mentions Paul using configured patterns
text = msg.get('text', '')
text_lower = text.lower()

# Check for Slack mention format (case-sensitive) or plain text patterns (case-insensitive)
if f'<@{paul_user_id}>' in text or any(pattern.lower() in text_lower for pattern in additional_patterns):
    paul_messages.append({...})
```

**Jira mention detection:**
```python
# Use configured patterns for Jira detection (case-insensitive)
if any(pattern.lower() in field_value.lower() for pattern in additional_patterns):
    paul_mentioned = True
    break
```

## Purpose: Daily Activity Digest

**Important**: This is not just a "TODO list" - it's a **daily activity digest** showing all conversations and tickets where Paul is involved.

The goal is to give Paul a **quick overview at first glance** of:
- What activities he's involved in
- What conversations he's participating in  
- What Jira tickets need his attention
- Where he committed to taking action

The AI then analyzes this context and suggests action items with clear references (Slack channels and Jira tickets), so Paul can quickly decide what needs focus that day.

## How It Works Now

### Detection Priority:

#### Slack Messages:
Captures messages where Paul is **involved** in the conversation:
1. **Messages mentioning Paul** - `<@U04N9LTR47M>` (Slack mentions) or plain text patterns
2. **Messages sent BY Paul** - Using his Slack user ID `U04N9LTR47M`

This provides a complete view of all activities Paul is involved in, not just when others mention him.

#### Jira Tickets:
- **Plain text patterns** - `paul`, `pacaramu`, `rhn-support-pacaramu` (case-insensitive)
- **Searched fields**: summary, description, comment, assignee, reporter
- **Why include Jira user ID?** The assignee/reporter fields often contain the Jira username (e.g., "rhn-support-pacaramu") rather than the display name, so this catches tickets assigned to or reported by Paul even if his name isn't mentioned in the text.

### Example Scenarios:

#### Slack Messages:
| Message in Slack | Sender | Detected? | Reason |
|-----------------|--------|-----------|--------|
| "Hey @Paul, can you review?" | Alice | ✅ YES | Slack mention `<@U04N9LTR47M>` |
| "Paul, please check this" | Bob | ✅ YES | Plain text "paul" |
| "I will classify each service..." | **Paul** | ✅ YES | **Paul is the sender** |
| "Let me handle the deployment" | **Paul** | ✅ YES | **Paul is the sender** |
| "@pacaramu needs to approve" | Charlie | ✅ YES | Plain text "pacaramu" |

#### Jira Tickets:
| Field | Content | Detected? | Reason |
|-------|---------|-----------|--------|
| Assignee | `{"name": "rhn-support-pacaramu", "displayName": "Paul Caramuto"}` | ✅ YES | Jira user ID match |
| Reporter | `{"name": "rhn-support-pacaramu"}` | ✅ YES | Jira user ID match |
| Summary | "Paul needs to review KONFLUX-6851" | ✅ YES | Plain text "paul" |
| Description | "Assigned to pacaramu for approval" | ✅ YES | Plain text "pacaramu" |
| Comment | "@rhn-support-pacaramu can you check?" | ✅ YES | Jira user ID match |

## Making it Generic for Other Users

To adapt this for another user (e.g., "Jane Doe"):

1. **Find the Slack user ID:**
   - In Slack, click on the user's profile
   - Click "More" → "Copy member ID"
   - Example: `U05ABCD1234`

2. **Update `config/mail_template.yaml`:**
   ```yaml
   jane_todo_config:
     user_id: "U05ABCD1234"  # Jane's Slack user ID
     additional_patterns:
       - "jane"
       - "jdoe"
       - "jane doe"
   ```

3. **Create similar function for Jane's TODOs:**
   - Copy `generate_paul_todo_items()`
   - Rename to `generate_jane_todo_items()`
   - Load `jane_todo_config` instead of `paul_todo_config`

## Testing

To verify the fix works:

1. **Manual test in Slack:**
   - Post a message with `@Paul` mention in #toolchain-sla
   - Post a message with plain text "paul" in the same channel
   - Run the daily report workflow

2. **Check output logs:**
   - Look for: `🔍 Using detection patterns: Slack mention <@U04N9LTR47M>, text patterns: ['paul', 'pacaramu', 'rhn-support-pacaramu']`
   - Look for: `📱 Found X Paul mentions in toolchain-sla`
   - Look for: `📝 Found X Slack mentions and Y Jira mentions`

3. **Verify email:**
   - Check that the TODO section includes items from #toolchain-sla
   - Verify both `@mention` and plain text mentions are captured
   - Verify Jira tickets assigned to you (e.g., [KONFLUX-6851](https://issues.redhat.com/browse/KONFLUX-6851)) are included

## Files Modified

1. **config/mail_template.yaml** - Added `paul_todo_config` section
2. **.github/workflows/scripts/github_daily_report.py** - Updated detection logic

## Key Improvement: Jira User ID Added

After initial implementation, we discovered that the Jira assignee/reporter fields often contain the Jira username (e.g., `rhn-support-pacaramu`) rather than the display name. By adding the Jira user ID to the search patterns, we now catch:

✅ **All tickets assigned to Paul** - Even if "Paul" or "pacaramu" isn't mentioned in the title/description  
✅ **All tickets reported by Paul** - Automatically included in TODO detection  
✅ **Mentions in comments** - When users reference `@rhn-support-pacaramu` in Jira comments

**Example:** [KONFLUX-6851](https://issues.redhat.com/browse/KONFLUX-6851) - This ticket is assigned to `rhn-support-pacaramu` and will now be detected even if "Paul" isn't mentioned in the summary.

## Search Pattern Summary

| Platform | Primary Detection | Additional Patterns |
|----------|------------------|---------------------|
| **Slack** | `<@U04N9LTR47M>` (user mention) | `paul`, `pacaramu`, `rhn-support-pacaramu` |
| **Jira** | `paul`, `pacaramu`, `rhn-support-pacaramu` | Searches: summary, description, comment, assignee, reporter |

## Related Documentation

- Main Feature: `PAUL_TODO_EMAIL_FEATURE.md`
- Architecture: `ARCHITECTURE_DIAGRAM.md`
- Slack Config: `config/slack.yaml` (contains user ID mappings at line 120)

