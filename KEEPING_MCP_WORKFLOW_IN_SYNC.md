# Keeping MCP Tools and GitHub Workflows in Sync

## Overview
This document explains how to maintain consistency between MCP tools and GitHub workflow automation.

## Architecture - Shared Components

### 1. **Shared Configuration** (`config/jira.yaml`)
Both MCP tools and GitHub workflows read from the same configuration file:

```yaml
# config/jira.yaml
query_filters:          # Used by GitHub workflows
  statuses: ["In Progress", "To Do", "In Review"]
  order_by: "updated DESC"
  additional_jql: 'AND sprint in openSprints()'

mcp_query_filters:      # Used by MCP tools
  default_status: "In Progress"
  order_by: "updated DESC"
  additional_jql: 'AND sprint in openSprints()'
  filter_to_latest_sprint: true
```

**Best Practice**: Keep both sections in sync when possible, or document why they differ.

### 2. **Shared Utility Functions** (`utils/`)
Both systems use the same utility modules to ensure identical behavior:

#### Sprint Extraction (`utils/sprint_helpers.py`)
- **Function**: `extract_active_sprint_from_issue(issue)`
- **Used By**: 
  - MCP tools: `get_team_issues.py`, `jira_data_collection.py`
  - GitHub workflow: `.github/workflows/scripts/github_daily_report.py`
- **Purpose**: Extract active sprint information from Jira issues using `customfield_12310940`

```python
# Both MCP and workflow use this:
from utils.sprint_helpers import extract_active_sprint_from_issue

sprint_name, sprint_num = extract_active_sprint_from_issue(issue)
```

#### Response Formatting (`utils/responses.py`)
- **Functions**: `create_success_response()`, `create_error_response()`
- **Used By**: All MCP tools
- **Purpose**: Standardized JSON response format

#### Input Validation (`utils/validators.py`)
- **Functions**: `validate_team_name()`, etc.
- **Used By**: All MCP tools
- **Purpose**: Input sanitization and validation

### 3. **Shared Clients** (`connectors/`)
Both systems use identical client implementations:

#### Jira Client (`connectors/jira/client.py`)
```python
from connectors.jira.client import JiraClient
from connectors.jira.config import JiraConfig

jira_config = JiraConfig.load('config/jira.yaml')
jira_client = JiraClient(jira_config)
```

#### Slack Client (`connectors/slack/client.py`)
```python
from connectors.slack.client import SlackClient
from connectors.slack.config import SlackConfig
```

#### Gemini Client (`connectors/gemini/client.py`)
```python
from connectors.gemini.client import GeminiClient
from connectors.gemini.config import GeminiConfig
```

## Synchronization Rules

### ✅ DO: Keep These in Sync

1. **Sprint Extraction Logic**
   - Always use `utils/sprint_helpers.py`
   - Never duplicate sprint parsing regex inline
   - Always target `customfield_12310940` for sprint data

2. **Configuration Reading**
   - Both should read from `config/jira.yaml`
   - Document any differences between `query_filters` and `mcp_query_filters`

3. **Client Implementations**
   - Use the same client classes from `connectors/`
   - Share JQL building logic through client methods

4. **Error Handling**
   - Use same response format utilities where applicable

### ⚠️ ALLOWED: Different Configurations

Some differences are intentional and acceptable:

1. **Status Filtering**:
   - **GitHub Workflow**: Uses `query_filters.statuses` (list of multiple statuses)
   - **MCP Tools**: Uses `mcp_query_filters.default_status` (single status default)
   - **Reason**: Different use cases - workflow needs comprehensive reports, MCP needs focused queries

2. **Sprint Filtering**:
   - **GitHub Workflow**: Uses `additional_jql: 'AND sprint in openSprints()'`
   - **MCP Tools**: Uses same JQL + post-processing with `filter_to_latest_sprint: true`
   - **Reason**: MCP tools filter to single latest sprint for focused view

## How to Add New Features While Staying in Sync

### Example: Adding New Sprint Logic

❌ **BAD - Duplicating Logic**:
```python
# In GitHub workflow
for sprint_string in sprint_data:
    sprint_str = str(sprint_string)
    state_match = re.search(r'state=([^,]+)', sprint_str)
    # ... duplicate regex logic

# In MCP tool
sprint_fields = ['customfield_10020', 'customfield_10010']  # Wrong fields!
for field_name in sprint_fields:
    sprint_data = fields.get(field_name)
    # ... different logic
```

✅ **GOOD - Shared Utility**:
```python
# In utils/sprint_helpers.py (shared)
def extract_active_sprint_from_issue(issue):
    sprint_data = issue.get('customfield_12310940', [])
    # ... single source of truth

# In GitHub workflow
from utils.sprint_helpers import extract_active_sprint_from_issue
sprint_name, sprint_num = extract_active_sprint_from_issue(issue)

# In MCP tool (same!)
from utils.sprint_helpers import extract_active_sprint_from_issue
sprint_name, sprint_num = extract_active_sprint_from_issue(issue)
```

## Testing Synchronization

After making changes, verify both systems behave consistently:

### 1. Test MCP Tools
```bash
# Rebuild MCP container
make build

# Restart Cursor to reload MCP server

# Test in Cursor
# Call: get_team_issues(team="toolchain")
# Verify sprint filtering and ticket count
```

### 2. Test GitHub Workflow
```bash
# Run locally
cd .github/workflows/scripts
python github_daily_report.py

# Or trigger workflow manually in GitHub Actions UI
```

### 3. Compare Results
- Same sprint numbers should appear
- Ticket counts should be similar (accounting for config differences)
- Sprint names should match exactly

## File Structure Reference

```
work-planner/
├── config/
│   └── jira.yaml              # Shared configuration
├── utils/
│   ├── sprint_helpers.py      # Shared sprint logic ⭐
│   ├── responses.py           # Shared response format
│   └── validators.py          # Shared validation
├── connectors/
│   ├── jira/
│   │   ├── client.py          # Shared Jira client ⭐
│   │   ├── config.py          # Config loader
│   │   └── tools/             # MCP tools only
│   │       ├── get_team_issues.py
│   │       └── jira_data_collection.py
│   ├── slack/
│   │   └── client.py          # Shared Slack client ⭐
│   └── gemini/
│       └── client.py          # Shared Gemini client ⭐
└── .github/workflows/scripts/
    └── github_daily_report.py # GitHub workflow script

⭐ = Shared between MCP and workflow
```

## Commit Best Practices

When modifying shared components:

```bash
# Good commit messages
git commit -m "refactor: move sprint logic to shared utils for MCP/workflow sync"
git commit -m "fix: update both MCP and workflow to use customfield_12310940"
git commit -m "config: align mcp_query_filters with workflow query_filters"

# Bad commit messages
git commit -m "fix mcp"
git commit -m "update sprint"
```

## Summary

**Key Principle**: **Never duplicate logic - always share through utilities**

1. ✅ Share: Utilities, clients, configuration files
2. ✅ Sync: Sprint logic, field names, JQL patterns
3. ⚠️ Document: Intentional configuration differences
4. ✅ Test: Both systems after changes

This ensures MCP tools and GitHub workflows provide consistent results and are easier to maintain.

