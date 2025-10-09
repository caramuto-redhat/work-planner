# Configurable Jira Query Filters

## Overview

Jira query filters are now configurable in `config/jira.yaml`, allowing you to easily change which tickets appear in daily team reports without modifying code.

## Configuration Location

**File:** `config/jira.yaml`

```yaml
query_filters:
  # Status filter for team tickets
  statuses:
    - "In Progress"
    - "To Do"
    - "In Review"
  
  # Sort order for query results
  order_by: "updated DESC"
  
  # Optional: Additional JQL filter fragments
  # additional_jql: 'AND priority in (High, Highest)'
```

## Configuration Options

### 1. **`statuses`** (List of strings)
Controls which ticket statuses are included in reports.

**Default:**
```yaml
statuses:
  - "In Progress"
  - "To Do"
  - "In Review"
```

**Common Variations:**

**Only In Progress:**
```yaml
statuses:
  - "In Progress"
```

**Include Blocked Tickets:**
```yaml
statuses:
  - "In Progress"
  - "To Do"
  - "In Review"
  - "Blocked"
```

**Add Code Review:**
```yaml
statuses:
  - "In Progress"
  - "To Do"
  - "In Review"
  - "Code Review"
  - "Ready for Review"
```

### 2. **`order_by`** (String)
Controls how tickets are sorted in the results.

**Default:** `"updated DESC"` (most recently updated first)

**Options:**
- `"updated DESC"` - Recently updated first
- `"updated ASC"` - Oldest updated first
- `"created DESC"` - Recently created first
- `"priority DESC, updated DESC"` - Highest priority first, then by update date
- `"assignee ASC, updated DESC"` - Grouped by assignee

### 3. **`additional_jql`** (String, Optional)
Add custom JQL filter fragments to further refine results.

**Examples:**

**High Priority Only:**
```yaml
additional_jql: 'AND priority in (High, Highest)'
```

**Specific Labels:**
```yaml
additional_jql: 'AND labels in (critical, urgent)'
```

**Updated Recently:**
```yaml
additional_jql: 'AND updated >= -7d'
```

**Multiple Conditions:**
```yaml
additional_jql: 'AND priority in (High, Highest) AND updated >= -14d'
```

**Exclude Specific Statuses:**
```yaml
additional_jql: 'AND status != "Waiting for Customer"'
```

## How It Works

### Generated JQL Queries

The workflow builds JQL queries dynamically from the configuration:

**Team Tickets Query:**
```jql
project = "Automotive Feature Teams" 
AND "AssignedTeam" = "{team_assigned_team}" 
AND status IN ("In Progress", "To Do", "In Review")
{additional_jql if provided}
ORDER BY {order_by}
```

**SP Organization Tickets Query:**
```jql
project = "Automotive Feature Teams" 
AND "AssignedTeam" = "{team_assigned_team}" 
AND assignee in ("{sp_members}")
AND status IN ("In Progress", "To Do", "In Review")
{additional_jql if provided}
ORDER BY {order_by}
```

### Code Implementation

Located in `.github/workflows/scripts/github_daily_report.py` (lines 360-391):

```python
# Get query filters from config
query_filters = jira_config.get('query_filters', {})
statuses = query_filters.get('statuses', ['In Progress', 'To Do', 'In Review'])
order_by = query_filters.get('order_by', 'updated DESC')
additional_jql = query_filters.get('additional_jql', '')

# Build status filter
status_list = '", "'.join(statuses)
status_filter = f'status IN ("{status_list}")'

# Build complete query
toolchain_jql = f'project = "Automotive Feature Teams" AND "AssignedTeam" = "{assigned_team}" AND {status_filter}'
if additional_jql:
    toolchain_jql += f' {additional_jql}'
toolchain_jql += f' ORDER BY {order_by}'
```

## Common Use Cases

### Use Case 1: Focus Only on Active Work
Show only tickets currently being worked on:

```yaml
query_filters:
  statuses:
    - "In Progress"
  order_by: "updated DESC"
```

### Use Case 2: Include Everything Except Done
Show all active work including blocked tickets:

```yaml
query_filters:
  statuses:
    - "In Progress"
    - "To Do"
    - "In Review"
    - "Blocked"
    - "Code Review"
  order_by: "updated DESC"
```

### Use Case 3: High Priority Items Only
Focus on critical work:

```yaml
query_filters:
  statuses:
    - "In Progress"
    - "To Do"
  order_by: "priority DESC, updated DESC"
  additional_jql: 'AND priority in (High, Highest)'
```

### Use Case 4: Recent Activity Only
Show only tickets updated in the last 7 days:

```yaml
query_filters:
  statuses:
    - "In Progress"
    - "To Do"
    - "In Review"
  order_by: "updated DESC"
  additional_jql: 'AND updated >= -7d'
```

### Use Case 5: Sprint-Focused View
Show only tickets in active sprints:

```yaml
query_filters:
  statuses:
    - "In Progress"
    - "To Do"
  order_by: "updated DESC"
  additional_jql: 'AND sprint in openSprints()'
```

## Testing Configuration

### Test Config Loads
```bash
cd /Users/pacaramu/Documents/Git/work-planner
python3 -c "
import yaml
with open('config/jira.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
query_filters = config.get('query_filters', {})
print('Statuses:', query_filters.get('statuses', []))
print('Order by:', query_filters.get('order_by', 'updated DESC'))
print('Additional JQL:', query_filters.get('additional_jql', '(none)'))
"
```

### Test Generated JQL
```bash
python3 -c "
import yaml
with open('config/jira.yaml', 'r') as f:
    config = yaml.safe_load(f)
    
query_filters = config.get('query_filters', {})
statuses = query_filters.get('statuses', ['In Progress'])
status_list = '\", \"'.join(statuses)
status_filter = f'status IN (\"{status_list}\")'
print('Generated status filter:', status_filter)
"
```

### Verify in Workflow
When the workflow runs, check the logs for:
```
🎫 Team JQL: project = "Automotive Feature Teams" AND "AssignedTeam" = "rhivos-pdr-auto-toolchain" AND status IN ("In Progress", "To Do", "In Review") ORDER BY updated DESC
🎫 Found X team tickets
```

## Fallback Behavior

If the configuration is missing or malformed:
- **Default statuses:** `["In Progress", "To Do", "In Review"]`
- **Default order:** `"updated DESC"`
- **No additional JQL** is applied

The system will always work with sensible defaults.

## Impact on Reports

Changing these filters affects:
1. ✅ **Team daily report emails** - Tickets shown in each team email
2. ✅ **Paul TODO email** - Jira tickets considered for TODO extraction
3. ✅ **AI analysis** - Tickets included in AI-generated insights
4. ✅ **Sprint title detection** - Which tickets are considered for active sprint

## Best Practices

### 1. **Keep Statuses Relevant**
Only include statuses that represent active work:
- ✅ In Progress, To Do, In Review
- ❌ Don't include "Done" or "Closed" unless specifically needed

### 2. **Use Consistent Ordering**
Stick with `"updated DESC"` for most cases - shows recent activity first

### 3. **Test Additional JQL**
Test any `additional_jql` in Jira's issue navigator first to ensure it's valid

### 4. **Document Changes**
When changing filters, note the reason in git commit message

### 5. **Consider Email Length**
More statuses = more tickets = longer emails
- Balance comprehensiveness with readability
- Use ticket limits (`ticket_limit_per_team`) to control length

## Troubleshooting

### No Tickets Appear
**Problem:** Email shows "No active tickets found"

**Solutions:**
1. Check if statuses exist in your Jira project
2. Verify status names match exactly (case-sensitive)
3. Remove `additional_jql` to test if it's too restrictive

### Too Many Tickets
**Problem:** Email is too long

**Solutions:**
1. Reduce statuses (e.g., only "In Progress")
2. Add `additional_jql` to filter (e.g., priority, updated date)
3. Adjust ticket limits in `config/mail_template.yaml`

### Invalid JQL Error
**Problem:** Workflow fails with JQL error

**Solutions:**
1. Check `additional_jql` syntax in Jira issue navigator
2. Ensure quotes are properly escaped
3. Remove `additional_jql` to isolate the issue

## Related Configuration

### Ticket Display Limits
Controlled in `config/mail_template.yaml`:
```yaml
time_ranges:
  jira:
    ticket_limit_per_team: 15      # Max tickets per team
    ticket_limit_per_org: 10       # Max tickets per organization
    max_tickets_for_analysis: 20   # Max for AI analysis
```

### Team Configuration
Teams and assigned team values in `config/jira.yaml`:
```yaml
teams:
  toolchain:
    assigned_team: "rhivos-pdr-auto-toolchain"
```

## Related Files

- `config/jira.yaml` - Query filter configuration
- `.github/workflows/scripts/github_daily_report.py` - Implementation
- `config/mail_template.yaml` - Ticket display limits
- `PAUL_TODO_EMAIL_FEATURE.md` - Paul TODO feature
- `PROMPT_CENTRALIZATION.md` - AI prompt configuration

## Conclusion

Jira query filters are now fully configurable, making it easy to customize which tickets appear in your daily team reports without touching any code. Simply edit `config/jira.yaml`, commit, and the next workflow run will use your new filters.

