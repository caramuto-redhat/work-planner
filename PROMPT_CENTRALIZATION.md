# Prompt Centralization in Gemini Config

## Summary

All AI prompts used by the email workflow have been centralized in `config/gemini.yaml`. Prompts are now loaded from the config file with automatic fallbacks to inline prompts if the config is unavailable.

## Changes Made

### 1. **Added Prompts to `config/gemini.yaml`**

Added 5 email workflow prompts to the configuration file:

1. **`slack_channel_analysis`** - Analyzes individual Slack channel activity
2. **`team_executive_summary`** - Generates executive summary across all channels
3. **`paul_todo_items`** - Extracts Paul's TODO items from Slack/Jira mentions
4. **`jira_analysis`** - Analyzes Jira tickets for team insights
5. **`paul_consolidated_todo`** - Consolidates TODOs across all teams

Each prompt uses template variables (e.g., `{team}`, `{channel_name}`, `{activity_days}`) that get filled in at runtime.

### 2. **Updated `github_daily_report.py`**

Added prompt loading functionality:

**New Function:**
```python
def _load_gemini_prompts():
    """Load AI prompts from gemini.yaml config"""
    try:
        import yaml
        with open('config/gemini.yaml', 'r') as f:
            config = yaml.safe_load(f)
        return config.get('prompts', {})
    except Exception as e:
        print(f'  ⚠️  Warning: Could not load Gemini prompts: {e}')
        return {}
```

**Updated Each Prompt Usage:**
- Load prompts from config using `_load_gemini_prompts()`
- Use `prompts.get('prompt_name', fallback)` pattern
- Format prompt template with runtime variables
- Inline fallback prompts ensure system always works

**Example Pattern:**
```python
prompts = _load_gemini_prompts()
prompt_template = prompts.get('slack_channel_analysis', """
[Inline fallback prompt here]
""")

prompt = prompt_template.format(
    team=team_name,
    channel_name=channel_name,
    activity_days=7,
    messages=message_text
)
```

## Benefits

### 1. **Centralized Prompt Management**
- ✅ All prompts in one place (`config/gemini.yaml`)
- ✅ Easy to modify without touching code
- ✅ Version control for prompt changes
- ✅ Can compare and rollback prompt versions

### 2. **Non-Technical Editing**
- ✅ Product managers can tune prompts
- ✅ No Python knowledge required
- ✅ No code deployments needed
- ✅ Just edit YAML and restart workflow

### 3. **Flexibility**
- ✅ Easy A/B testing of different prompts
- ✅ Environment-specific prompts possible
- ✅ Team-specific prompt variations
- ✅ Dynamic prompt adjustments

### 4. **Fallback Safety**
- ✅ System works even if config file is missing
- ✅ Inline fallbacks ensure reliability
- ✅ No breaking changes
- ✅ Graceful degradation

## How to Modify Prompts

### Method 1: Edit Config File (Recommended)

1. Open `config/gemini.yaml`
2. Find the prompt you want to modify (e.g., `slack_channel_analysis`)
3. Edit the prompt text
4. Save the file
5. Next workflow run will use the new prompt

**Example - Make Slack analysis more detailed:**
```yaml
prompts:
  slack_channel_analysis: |
    Analyze the last {activity_days} days in "{channel_name}" for {team} team.
    
    Recent Messages ({message_count} messages):
    {messages}
    
    Provide a DETAILED summary covering:
    1. Main topics and discussions (be specific)
    2. Key decisions with context
    3. All blockers and risks
    4. Team collaboration patterns and effectiveness
    5. Recommendations for next steps
    
    Focus on actionable insights.
```

### Method 2: Override Inline (Development)

If you're testing and don't want to modify the config:
1. Edit `.github/workflows/scripts/github_daily_report.py`
2. Modify the inline fallback prompt in the code
3. For production, move the change to `gemini.yaml`

## Prompt Variables Reference

Each prompt has specific variables that must be included:

### `slack_channel_analysis`
- `{activity_days}` - Number of days analyzed
- `{channel_name}` - Slack channel name
- `{team}` - Team name
- `{message_count}` - Number of messages
- `{messages}` - Formatted message text

### `team_executive_summary`
- `{team}` - Team name
- `{activity_days}` - Days analyzed
- `{total_messages}` - Total message count
- `{channel_count}` - Number of channels
- `{ticket_count}` - Number of Jira tickets
- `{max_tickets}` - Max tickets analyzed
- `{channel_summaries}` - Channel summary text

### `paul_todo_items`
- `{slack_summary}` - Slack mentions summary
- `{jira_summary}` - Jira mentions summary

### `jira_analysis`
- `{team}` - Team name
- `{ticket_count}` - Number of tickets
- `{ticket_summaries}` - Formatted ticket list

### `paul_consolidated_todo`
- `{team_count}` - Number of teams
- `{team_todos}` - All team TODO summaries

## Testing

### Test Config Loading
```bash
cd /Users/pacaramu/Documents/Git/work-planner
python3 -c "
import yaml
config = yaml.safe_load(open('config/gemini.yaml'))
prompts = config.get('prompts', {})
print(f'Prompts found: {len(prompts)}')
print(f'Names: {list(prompts.keys())}')
"
```

### Test Prompt Formatting
```python
import yaml
config = yaml.safe_load(open('config/gemini.yaml'))
prompt_template = config['prompts']['slack_channel_analysis']

# Test with sample data
prompt = prompt_template.format(
    activity_days=7,
    channel_name='toolchain-release-readiness',
    team='toolchain',
    message_count=10,
    messages='Sample messages here'
)
print(prompt)
```

### Test Workflow (Manual)
```bash
# Trigger GitHub Actions workflow manually
# or
python .github/workflows/scripts/github_daily_report.py
```

## Verification

Configuration has been verified:
```
✅ Config loaded successfully
✅ Prompts found: 5
✅ Prompt names: ['slack_channel_analysis', 'team_executive_summary', 
                 'paul_todo_items', 'jira_analysis', 'paul_consolidated_todo']
```

## Backward Compatibility

✅ **Fully backward compatible:**
- If `config/gemini.yaml` is missing → uses inline fallbacks
- If prompts section is missing → uses inline fallbacks
- If specific prompt is missing → uses inline fallback for that prompt
- System never fails due to missing prompts

## Best Practices

### 1. **Always Include All Variables**
When editing prompts, ensure all `{variable}` placeholders are present.

### 2. **Test Before Deploying**
Test prompt changes locally before committing to git.

### 3. **Document Prompt Changes**
When changing prompts significantly, note the reason in git commit message.

### 4. **Keep Fallbacks in Sync**
If you permanently change a prompt in `gemini.yaml`, consider updating the inline fallback too.

### 5. **Use Clear Instructions**
Prompts should be specific about:
- What to analyze
- What format to use
- How detailed to be
- What to prioritize

## Example Use Cases

### Make Analysis More Concise
```yaml
slack_channel_analysis: |
  Summarize the last {activity_days} days in "{channel_name}" in 1-2 sentences.
  Messages: {messages}
  Focus only on critical updates and blockers.
```

### Make Analysis More Detailed
```yaml
jira_analysis: |
  Provide comprehensive analysis of {ticket_count} Jira tickets for {team}:
  
  Tickets: {ticket_summaries}
  
  Include:
  1. Detailed status breakdown
  2. Risk assessment for each blocker
  3. Resource allocation recommendations
  4. Sprint velocity insights
  5. Individual ticket concerns
  6. Timeline projections
```

### Change TODO Format
```yaml
paul_todo_items: |
  Create a prioritized TODO list for Paul from:
  {slack_summary}
  {jira_summary}
  
  Format as markdown checklist:
  - [ ] [HIGH] Item description (Source: Team X)
  - [ ] [MEDIUM] Item description (Source: Slack #channel)
  
  Sort by urgency and group by context.
```

## Related Files

- `config/gemini.yaml` - Prompt configuration
- `.github/workflows/scripts/github_daily_report.py` - Workflow script
- `GEMINI_CONFIG_SIMPLIFICATION.md` - Previous simplification
- `PAUL_TODO_EMAIL_FEATURE.md` - Paul TODO feature docs

## Conclusion

All email workflow prompts are now centralized in `config/gemini.yaml`, making them easy to modify without code changes while maintaining full backward compatibility through inline fallbacks.

