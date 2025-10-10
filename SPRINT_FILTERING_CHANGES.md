# Automatic Latest Sprint Filtering - Implementation Summary

## Overview
Implemented automatic filtering to the latest/highest sprint number when multiple open sprints exist.

## Changes Made

### 1. Configuration (`config/jira.yaml`)
Added new configuration option:
```yaml
mcp_query_filters:
  # Filter to only the latest sprint when multiple open sprints exist
  # When true, post-processes results to keep only tickets from the highest sprint number
  filter_to_latest_sprint: true
```

### 2. New Utility Module (`utils/sprint_helpers.py`)
Created comprehensive sprint extraction and filtering functions:
- `extract_sprint_number()` - Extract sprint number from various Jira sprint data formats
- `extract_issue_sprint_number()` - Extract sprint number from a Jira issue
- `filter_issues_by_latest_sprint()` - Filter issues to only the latest sprint
- `get_sprint_summary()` - Get sprint distribution statistics

**Key Features:**
- Handles multiple sprint data formats (string, dict, list)
- Extracts numbers from sprint names like "Automotive Feature Teams Sprint 112"
- Returns the highest sprint number when multiple sprints are found
- Robust regex-based extraction with fallback patterns

### 3. Updated MCP Tools

#### `connectors/jira/tools/get_team_issues.py`
- Reads `filter_to_latest_sprint` from config
- Applies sprint filtering after JQL query execution
- Returns additional fields:
  - `filtered_to_sprint`: Sprint number filtered to
  - `sprint_filter_applied`: Boolean flag
  - `original_count`: Count before filtering

#### `connectors/jira/tools/jira_data_collection.py`
- Same filtering logic as `get_team_issues.py`
- Updates both text and JSON dump files with sprint info
- Includes sprint metadata in dump headers

## How It Works

1. **JQL Query**: Uses `sprint in openSprints()` to get all tickets in open sprints
2. **Sprint Extraction**: Parses sprint information from each issue's fields
   - Checks common custom fields: `sprint`, `customfield_10020`, `customfield_10010`, `sprints`
   - Extracts numeric sprint ID from sprint names
3. **Filtering**: Identifies the highest sprint number and keeps only those tickets
4. **Response**: Returns filtered results with sprint metadata

## Example

**Before filtering (multiple open sprints):**
- Sprint 110: 5 tickets
- Sprint 111: 8 tickets
- Sprint 112: 35 tickets
- **Total: 48 tickets**

**After filtering (filter_to_latest_sprint: true):**
- Sprint 112: 35 tickets
- **Total: 35 tickets**

## Testing

To test the implementation:
1. **Restart Cursor** to load updated code
2. Use MCP tool: `get_team_issues(team="toolchain")`
3. Check response for:
   - `filtered_to_sprint: 112`
   - `count: 35` (or actual ticket count in Sprint 112)
   - `original_count: 48` (before filtering)

## Configuration Options

### Enable Latest Sprint Filtering
```yaml
mcp_query_filters:
  filter_to_latest_sprint: true
  additional_jql: 'AND sprint in openSprints()'
```

### Disable (Get All Open Sprint Tickets)
```yaml
mcp_query_filters:
  filter_to_latest_sprint: false
  additional_jql: 'AND sprint in openSprints()'
```

### Filter to Specific Sprint
```yaml
mcp_query_filters:
  filter_to_latest_sprint: false
  additional_jql: 'AND sprint = 112'
```

## Benefits

1. **Automatic**: No manual sprint number updates needed
2. **Flexible**: Can be toggled via configuration
3. **Transparent**: Returns metadata about filtering applied
4. **Robust**: Handles various Jira sprint data formats
5. **Non-breaking**: When disabled, behaves like before

## Files Modified

- `config/jira.yaml` - Added `filter_to_latest_sprint` config
- `utils/sprint_helpers.py` - New file with sprint utilities
- `connectors/jira/tools/get_team_issues.py` - Added sprint filtering
- `connectors/jira/tools/jira_data_collection.py` - Added sprint filtering

## Container Rebuild

Container rebuilt successfully:
```bash
make build
✅ Container built: work-planner:latest
```

## Next Steps

**User Action Required:**
1. **Restart Cursor** to reload the MCP server with updated code
2. Test with: "pull toolchain tickets" or use `get_team_issues` MCP tool
3. Verify `filtered_to_sprint: 112` in response
4. Check ticket count matches current Sprint 112 count (35 expected based on dashboard)

