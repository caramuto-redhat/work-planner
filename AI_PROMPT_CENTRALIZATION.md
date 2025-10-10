# AI Prompt Centralization - Removing Hardcoded Fallbacks

## Problem Identified

The codebase had **duplicate and inconsistent AI prompts**:

1. **Primary prompts** in `config/gemini.yaml` (intended to control all AI behavior)
2. **Hardcoded fallback prompts** in `github_daily_report.py` (used if gemini.yaml prompts not found)

### Issues This Caused:

❌ **Inconsistent AI behavior** - Two different prompt versions could produce different outputs  
❌ **Maintenance nightmare** - Had to update prompts in two places  
❌ **Configuration bypass** - The hardcoded fallbacks meant gemini.yaml wasn't truly the single source of truth  
❌ **Silent failures** - If gemini.yaml was misconfigured, the system would silently use different prompts

### Example of Duplication:

**In `gemini.yaml` (lines 51-60):**
```yaml
paul_todo_items: |
  generate a list of suggested action items
  
  Format:
  - Slack channel <channel_name>: <action item>
  - Jira ticket <ticket_key>: <action item>
```

**In `github_daily_report.py` (lines 741-755) - HARDCODED:**
```python
prompt_template = prompts.get('paul_todo_items', """
    generate a concise TODO list
    
    Format:
    1. [Priority] Action item description
    Use priorities: HIGH, MEDIUM, LOW
""")
```

**Result**: DIFFERENT formats, DIFFERENT instructions! 🚨

## Solution Implemented

### Removed ALL Hardcoded Fallback Prompts

Updated **5 locations** in `github_daily_report.py` to:
1. Load prompts from `gemini.yaml` ONLY
2. Fail explicitly with clear error messages if prompts are missing
3. No silent fallbacks to hardcoded prompts

### Changes Made:

#### 1. **`slack_channel_analysis` (Lines 490-496)**

**Before:**
```python
prompt_template = prompts.get('slack_channel_analysis', """
<HARDCODED 13-LINE FALLBACK PROMPT>
""")
```

**After:**
```python
prompt_template = prompts.get('slack_channel_analysis')

if not prompt_template:
    print(f'  ⚠️  slack_channel_analysis prompt not found in gemini.yaml, skipping AI analysis')
    channel_summaries[channel_name] = "AI prompt configuration missing"
    continue
```

#### 2. **`team_executive_summary` (Lines 537-543)**

**Before:**
```python
prompt_template = prompts.get('team_executive_summary', """
<HARDCODED 17-LINE FALLBACK PROMPT>
""")
```

**After:**
```python
prompt_template = prompts.get('team_executive_summary')

if not prompt_template:
    print(f'  ⚠️  team_executive_summary prompt not found in gemini.yaml')
    channel_summaries['overall'] = "Executive summary unavailable - prompt configuration missing"
    return channel_summaries
```

#### 3. **`paul_todo_items` (Lines 740-747)**

**Before:**
```python
prompt_template = prompts.get('paul_todo_items', """
<HARDCODED 15-LINE FALLBACK PROMPT>
""")
```

**After:**
```python
prompt_template = prompts.get('paul_todo_items')

if not prompt_template:
    error_msg = "ERROR: 'paul_todo_items' prompt not found in config/gemini.yaml"
    print(f'  ❌ {error_msg}')
    return error_msg
```

#### 4. **`jira_analysis` (Lines 933-938)**

**Before:**
```python
prompt_template = prompts.get('jira_analysis', """
<HARDCODED 13-LINE FALLBACK PROMPT>
""")
```

**After:**
```python
prompt_template = prompts.get('jira_analysis')

if not prompt_template:
    print(f'  ⚠️  jira_analysis prompt not found in gemini.yaml')
    return '<p><em>Jira analysis unavailable - prompt configuration missing</em></p>'
```

#### 5. **`paul_consolidated_todo` (Lines 1126-1140)**

**Before:**
```python
prompt_template = prompts.get('paul_consolidated_todo', """
<HARDCODED 14-LINE FALLBACK PROMPT>
""")
```

**After:**
```python
prompt_template = prompts.get('paul_consolidated_todo')

if not prompt_template:
    print(f'  ⚠️  paul_consolidated_todo prompt not found in gemini.yaml')
    consolidated_todos_text = "Consolidated TODO analysis unavailable - prompt configuration missing"
else:
    # Use the prompt from gemini.yaml
    consolidated_prompt = prompt_template.format(...)
    consolidated_todos_text = gemini_client.generate_content(consolidated_prompt)
```

## Benefits of This Change

### ✅ **Single Source of Truth**
- ALL AI prompts are now ONLY in `config/gemini.yaml`
- No more hunting through Python code to find prompt variations

### ✅ **Explicit Error Handling**
- If prompts are missing, you get clear error messages
- No silent fallbacks to potentially outdated/inconsistent prompts

### ✅ **Easy Prompt Updates**
- Change prompts in ONE place: `gemini.yaml`
- No need to touch Python code for prompt tweaks

### ✅ **Better Testing**
- Can easily test different prompts by editing `gemini.yaml`
- No risk of accidentally using hardcoded fallbacks

### ✅ **Consistent AI Behavior**
- All runs use the SAME prompts from config
- No surprises from fallback prompts behaving differently

## Is the Filtering Redundant?

**No!** The current workflow makes sense:

### Step 1: Python Filtering (Efficiency)
```python
# Filter messages that mention Paul
if f'<@{paul_user_id}>' in text or any(pattern in text_lower...):
    paul_messages.append(...)
```

**Purpose**: 
- Reduces data volume before sending to AI
- Saves API costs (only relevant messages sent)
- Faster processing

### Step 2: AI Analysis (Intelligence)
```python
# Send filtered content to Gemini AI
todo_items = gemini_client.generate_content(todo_prompt)
```

**Purpose**:
- Analyzes context and extracts actionable items
- Prioritizes items (HIGH/MEDIUM/LOW)
- Deduplicates similar mentions
- Generates concise summaries

**This is NOT redundant** - it's **cost-effective intelligent processing**!

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                 config/gemini.yaml                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │ All AI Prompts (Single Source of Truth)          │  │
│  │ - slack_channel_analysis                         │  │
│  │ - team_executive_summary                         │  │
│  │ - paul_todo_items                                │  │
│  │ - jira_analysis                                  │  │
│  │ - paul_consolidated_todo                         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│          github_daily_report.py                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 1. Filter relevant data (Paul mentions)          │  │
│  │ 2. Load prompts from gemini.yaml                 │  │
│  │ 3. Fail explicitly if prompts missing            │  │
│  │ 4. Pass filtered data to Gemini AI               │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              Gemini AI Processing                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Uses prompts from gemini.yaml to:                │  │
│  │ - Analyze context                                │  │
│  │ - Extract action items                           │  │
│  │ - Prioritize tasks                               │  │
│  │ - Deduplicate mentions                           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Testing

To verify all prompts are being loaded correctly:

1. **Check logs for warnings:**
   ```bash
   # Should NOT see any of these:
   ⚠️  slack_channel_analysis prompt not found
   ⚠️  team_executive_summary prompt not found
   ❌  ERROR: 'paul_todo_items' prompt not found
   ```

2. **Verify gemini.yaml has all required prompts:**
   ```yaml
   prompts:
     slack_channel_analysis: |
       ...
     team_executive_summary: |
       ...
     paul_todo_items: |
       ...
     jira_analysis: |
       ...
     paul_consolidated_todo: |
       ...
   ```

3. **Test prompt changes:**
   - Edit a prompt in `gemini.yaml`
   - Run workflow
   - Verify AI output reflects the change (no fallback to old hardcoded prompt)

## Files Modified

- **github_daily_report.py** - Removed 5 hardcoded fallback prompts (removed ~70 lines of duplicate prompt text)

## Related Documentation

- Main Prompt Config: `config/gemini.yaml`
- TODO Detection Fix: `TODO_DETECTION_FIX.md`
- Architecture: `ARCHITECTURE_DIAGRAM.md`

