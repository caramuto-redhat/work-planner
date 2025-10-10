# MCP/Workflow Synchronization Fix - Summary

## Problem Identified

The MCP tools and GitHub workflow were using **different sprint extraction logic**, causing inconsistent results:

### GitHub Workflow (✅ Working)
- Used `customfield_12310940` (correct field)
- Filtered for `state=ACTIVE` sprints
- Inline regex extraction (lines 797-835)

### MCP Tools (❌ Broken)
- Used wrong fields: `customfield_10020`, `customfield_10010`
- Missing active sprint state filtering
- Resulted in `filtered_to_sprint: null`

## Root Cause

**Code duplication** - the same logic was implemented separately in two places with different implementations.

## Solution Applied

### 1. Created Shared Utility (`utils/sprint_helpers.py`)

Refactored to use the **exact same logic** as the working GitHub workflow:

```python
def extract_active_sprint_from_issue(issue: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract ACTIVE sprint name and number from a Jira issue.
    Uses the same logic as the GitHub workflow for consistency.
    """
    # Check for customfield_12310940 (the actual sprint field)
    sprint_data = issue.get('customfield_12310940', [])
    
    # Look for ACTIVE sprint first
    for sprint_string in sprint_data:
        state_match = re.search(r'state=([^,]+)', sprint_str)
        if state_match and state_match.group(1) == 'ACTIVE':
            name_match = re.search(r'name=([^,]+)', sprint_str)
            # Extract sprint number from name
            return sprint_name, sprint_num
```

**Key changes:**
- ✅ Uses correct field: `customfield_12310940`
- ✅ Filters for `state=ACTIVE`
- ✅ Returns both sprint name and number
- ✅ Matches workflow logic exactly

### 2. Updated MCP Tools

Both MCP tools now use the shared utility:

**`connectors/jira/tools/get_team_issues.py`**:
```python
from utils.sprint_helpers import filter_issues_by_latest_sprint

# Already using shared utility (but it was broken)
if filter_to_latest_sprint and issues:
    issues, latest_sprint_num = filter_issues_by_latest_sprint(issues)
```

**`connectors/jira/tools/jira_data_collection.py`**:
```python
from utils.sprint_helpers import filter_issues_by_latest_sprint

# Already using shared utility (but it was broken)
if filter_to_latest_sprint and issues:
    issues, latest_sprint_num = filter_issues_by_latest_sprint(issues)
```

### 3. Updated GitHub Workflow

Refactored **3 locations** in `.github/workflows/scripts/github_daily_report.py` to use shared utility instead of inline duplication:

#### Location 1: `_get_sprint_title()` (line 795)
**Before** (43 lines of duplicated regex):
```python
for sprint_string in sprint_data:
    sprint_str = str(sprint_string)
    state_match = re.search(r'state=([^,]+)', sprint_str)
    if state_match and state_match.group(1) == 'ACTIVE':
        name_match = re.search(r'name=([^,]+)', sprint_str)
        # ... 38 more lines
```

**After** (3 lines):
```python
from utils.sprint_helpers import extract_active_sprint_from_issue

sprint_name, sprint_num = extract_active_sprint_from_issue(issue)
```

#### Location 2: Sprint sorting (line 998)
**Before** (12 lines):
```python
has_active_sprint = False
if 'customfield_12310940' in issue:
    sprint_data = issue.get('customfield_12310940', [])
    # ... 9 more lines of regex
```

**After** (2 lines):
```python
sprint_name, sprint_num = extract_active_sprint_from_issue(issue)
has_active_sprint = sprint_name is not None
```

#### Location 3: Sprint display (line 1020)
**Before** (16 lines):
```python
sprint_info = "No Sprint"
if 'customfield_12310940' in issue:
    sprint_data = issue.get('customfield_12310940', [])
    for sprint_string in sprint_data:
        # ... 12 more lines of regex
```

**After** (5 lines):
```python
sprint_name, sprint_num = extract_active_sprint_from_issue(issue)
if sprint_name:
    sprint_info = f"🏃 {sprint_name} (Active)"
else:
    sprint_info = "No Sprint"
```

## Impact

### Code Reduction
- **Removed**: ~71 lines of duplicated sprint extraction logic
- **Added**: 1 shared utility function
- **Net**: Cleaner, more maintainable codebase

### Consistency
- ✅ MCP tools now use same logic as workflow
- ✅ Single source of truth for sprint extraction
- ✅ Same field (`customfield_12310940`) everywhere
- ✅ Same active sprint filtering everywhere

### Expected Results
After rebuilding MCP container:
```json
{
  "filtered_to_sprint": 112,
  "sprint_filter_applied": true,
  "count": 20,
  "original_count": 48
}
```

## Files Modified

1. ✅ `utils/sprint_helpers.py` - Fixed sprint extraction logic
2. ✅ `.github/workflows/scripts/github_daily_report.py` - Removed duplication, use shared utility
3. ✅ `KEEPING_MCP_WORKFLOW_IN_SYNC.md` - Documentation for future maintenance
4. ✅ `SYNC_FIX_SUMMARY.md` - This summary

## Testing Checklist

- [ ] Rebuild MCP container: `make build`
- [ ] Restart Cursor to reload MCP server
- [ ] Test MCP: Call `get_team_issues(team="toolchain")`
- [ ] Verify: `filtered_to_sprint: 112` (not null)
- [ ] Verify: Ticket count matches dashboard (should be ~20 in Sprint 112)
- [ ] Test workflow: Run GitHub Actions daily report
- [ ] Compare: Sprint names and numbers should match between MCP and workflow

## Key Takeaway

**Never duplicate logic between MCP and workflow - always share through utilities.**

This prevents drift and ensures consistent behavior across all automation systems.

