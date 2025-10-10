# Broken Tools Cleanup

## Summary

Removed 3 broken email MCP tools that referenced non-existent email templates.

## Templates That Actually Exist

| Template Name | Purpose |
|--------------|---------|
| `team_daily_report_with_todo` | Full daily team report with AI analysis, Slack activity, Jira tickets, and Paul's action items |
| `paul_todo_summary` | Consolidated TODO summary across all teams for Paul |

## Templates That DON'T Exist (Referenced by Broken Tools)

| Template Name | Broken Tools That Used It |
|--------------|---------------------------|
| `daily_summary` | `send_daily_summary_tool`, `ai_summary_tool` (email part) |
| `alert` | `send_alert_tool` |
| `data_collection_report` | `send_data_collection_report_tool` |

## Changes Made

### 1. Removed Broken Email Tools from `server.py`

**Removed Tools:**
- ❌ `send_daily_summary_tool` - Used non-existent `daily_summary` template
- ❌ `send_alert_tool` - Used non-existent `alert` template
- ❌ `send_data_collection_report_tool` - Used non-existent `data_collection_report` template

**Kept Tools:**
- ✅ `send_email_tool` - Generic tool, can use any template
- ✅ `test_email_connection_tool` - Doesn't use templates
- ✅ `get_email_config_tool` - Doesn't use templates

### 2. Disabled Email Sending in `ai_summary` Tool

The `ai_summary` tool's email functionality was broken (used the non-existent `daily_summary` template), so we:
- Disabled the email sending part
- Added clear warning messages
- The tool still works for AI analysis, just doesn't send emails
- Recommends using GitHub Actions workflow for full email reports

## Working Email Solution

For sending the full daily team reports (the ones with AI analysis, Paul's action items, etc.), use:

**Option 1: GitHub Actions Workflow** (Current working solution)
- Scheduled runs daily
- Full data collection, AI analysis, and email delivery
- Uses the proper `team_daily_report_with_todo` template

**Option 2: Manual Email via `send_email` Tool**
```
Use send_email tool with template_name="team_daily_report_with_todo"
```
Note: You'd need to manually collect and format the data

**Option 3: Create New MCP Tool** (Future enhancement)
- Wrap the GitHub Actions workflow logic
- Make it available as an MCP tool
- One-command: "Generate and send daily report for toolchain team"

## Tools Count Update

| Before | After |
|--------|-------|
| 23 total tools | 20 total tools |
| 6 email tools | 3 email tools |

## Files Modified

1. **server.py** - Removed broken tool registrations and imports
2. **connectors/gemini/tools/ai_summary_tool.py** - Disabled email sending part

## Recommendation

Create a new MCP tool that wraps the GitHub Actions workflow (`github_daily_report.py`) to make it easily triggerable through Cursor without needing to run GitHub Actions.

