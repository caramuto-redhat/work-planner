# Scripts Directory

This directory contains standalone scripts for GitHub Actions and other automated processes.

## Architecture Separation

### 🎯 **MCP Tools (for Cursor)**
- Located in `connectors/*/tools/`
- Used by Cursor AI assistant
- Interactive, real-time queries
- Examples: `search_issues`, `analyze_slack_data`, `generate_jira_team_report`

### 🤖 **GitHub Actions Scripts (for Automation)**
- Located in `scripts/`
- Used by GitHub Actions workflows
- Automated, scheduled execution
- Examples: `github_daily_report.py`

## Key Benefits

### ✅ **No Code Duplication**
- GitHub scripts reuse existing MCP tool functionality
- Single source of truth for data collection logic
- Consistent behavior between Cursor and GitHub Actions

### ✅ **Clean Separation**
- MCP tools focus on interactive use
- GitHub scripts focus on automation
- Easy to maintain and debug

### ✅ **Reusable Components**
- GitHub scripts import and use existing MCP tools
- Shared configuration and client logic
- Consistent error handling and logging

## Files

### `github_daily_report.py`
- **Purpose**: Generate daily team reports for GitHub Actions
- **Reuses**: All existing MCP tools (Slack, Jira, Gemini, Email)
- **Output**: HTML emails with team summaries
- **Schedule**: Runs daily at 6 AM UTC via GitHub Actions

## Usage

### GitHub Actions
```yaml
- name: Generate Daily Team Report
  run: python scripts/github_daily_report.py
```

### Local Testing
```bash
# Set environment variables
export SLACK_XOXC_TOKEN="your_token"
export JIRA_URL="your_jira_url"
# ... other env vars

# Run the script
python scripts/github_daily_report.py
```

## Adding New Scripts

When adding new GitHub Actions scripts:

1. **Reuse Existing Tools**: Import and use existing MCP tools
2. **Follow Naming Convention**: `github_*.py` for GitHub Actions scripts
3. **Document Purpose**: Add comments explaining what the script does
4. **Handle Errors**: Use consistent error handling patterns
5. **Update This README**: Document new scripts here
