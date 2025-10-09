# Gemini Configuration Simplification

## Summary

The `config/gemini.yaml` file has been significantly simplified by removing all unused prompt templates and configuration sections. Prompts are now defined inline in the code where they're actually used.

## Changes Made

### 1. **Simplified `config/gemini.yaml`** (204 lines → 13 lines)

**Removed:**
- ❌ All prompt templates (`prompts` section - ~140 lines)
  - Slack analysis prompts (summary, highlights, action_items, blockers)
  - Jira analysis prompts (summary, blockers, progress)
  - Email summary prompt
  - Custom analysis prompts (trend_analysis, performance_review)
- ❌ Analysis types configuration (`analysis_types` section)
- ❌ Output formatting configuration (`output_formatting` section)

**Kept:**
- ✅ Model configuration (`model: "models/gemini-2.0-flash"`)
- ✅ Generation configuration (temperature, top_p, top_k, max_output_tokens)

### 2. **Updated `connectors/gemini/tools/ai_summary_tool.py`**

Changed from config-based prompts to inline prompts:
- Slack analysis now uses inline prompt definitions
- Jira analysis now uses inline prompt definitions
- Email summary generation now uses inline prompts

**Before:**
```python
prompts_config = gemini_config.get('prompts', {}).get('slack_analysis', {})
if 'summary' in prompts_config:
    summary_prompt = prompts_config['summary'].format(data=slack_data)
```

**After:**
```python
summary_prompt = f"""
Analyze the following Slack conversation data and provide a concise summary including:
1. Key discussion topics and decisions
2. Important announcements or updates
...
Slack Data: {slack_data}
"""
```

### 3. **Updated `connectors/gemini/config.py`**

Removed prompts from default configuration:
- `_get_default_config()` now only returns model and generation_config
- Existing prompt-related methods (`get_prompts()`, `get_prompt()`) still work but return empty results

## Why This Simplification?

### 1. **Prompts Not Used in Email Workflow**
The main use case (daily team report emails via GitHub Actions) creates prompts inline in `github_daily_report.py` and never uses the config prompts.

### 2. **Reduced Configuration Overhead**
- Easier to maintain prompts where they're actually used
- Prompts can be customized per use case in code
- No need to sync between config file and code

### 3. **Better Code Locality**
- Prompts are now visible where they're used
- Easier to understand what each analysis does
- Changes to prompts don't require config file updates

### 4. **Simplified Configuration**
- `gemini.yaml` now only contains what's actually needed
- Clearer separation between configuration (model settings) and logic (prompts)
- Follows principle of "configuration for behavior, not for content"

## Impact Analysis

### ✅ **No Breaking Changes for Email Workflow**
- The GitHub Actions workflow (`github_daily_report.py`) never used config prompts
- All email generation will continue working exactly as before

### ✅ **MCP Tools Still Work**
- MCP tools (`analyze_slack_data_tool`, `analyze_jira_data_tool`, etc.) updated to use inline prompts
- Tools will generate the same analysis results
- Client methods already had fallback prompts

### ⚠️ **Config-Based Prompt Customization No Longer Supported**
- If someone was customizing prompts via `gemini.yaml`, they'll need to modify the code instead
- This was likely not being used (email workflow never used it)

## File Size Reduction

- **Before**: 204 lines
- **After**: 13 lines
- **Reduction**: 93.6% smaller

## Testing Recommendations

1. **Test Email Workflow** (primary use case):
   ```bash
   # Manually trigger GitHub Actions workflow
   # Or run locally: python .github/workflows/scripts/github_daily_report.py
   ```

2. **Test MCP Tools** (if used via Cursor):
   ```bash
   # Through Cursor AI, ask for:
   "analyze toolchain team slack data"
   "analyze assessment team jira data"
   ```

3. **Verify Configuration Loads**:
   ```bash
   python3 -c "
   from connectors.gemini.config import GeminiConfig
   config = GeminiConfig()
   print('Model:', config.get_config()['model'])
   print('Generation config:', config.get_config()['generation_config'])
   "
   ```

## Migration Notes

### If You Were Using Config Prompts

If you were customizing prompts in `gemini.yaml`, you now need to modify them directly in the code:

**For Email Workflow Prompts:**
- Edit: `.github/workflows/scripts/github_daily_report.py`
- Search for: `prompt = f"""` to find inline prompts

**For MCP Tool Prompts:**
- Edit: `connectors/gemini/tools/ai_summary_tool.py`
- Update the inline prompt definitions in each function

## Benefits

1. ✅ **Simpler Configuration** - Only essential settings remain
2. ✅ **Better Code Visibility** - Prompts are where they're used
3. ✅ **Easier Maintenance** - No config/code sync issues
4. ✅ **More Flexible** - Each use case can customize prompts independently
5. ✅ **Cleaner Architecture** - Separation of config vs content

## Related Files

- `config/gemini.yaml` - Main configuration file (simplified)
- `connectors/gemini/config.py` - Configuration loader (updated)
- `connectors/gemini/tools/ai_summary_tool.py` - MCP tools (updated to inline prompts)
- `connectors/gemini/client.py` - Client methods (already had fallback prompts)
- `.github/workflows/scripts/github_daily_report.py` - Email workflow (unchanged - never used config prompts)

## Conclusion

The simplification successfully reduces the `gemini.yaml` file to only essential configuration (model and generation settings), while moving prompts inline where they're actually used. This makes the codebase more maintainable and easier to understand, with no breaking changes to the email workflow.

