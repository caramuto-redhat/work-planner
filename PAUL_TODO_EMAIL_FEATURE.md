# Paul Caramuto Consolidated TODO Email Feature

## Overview
This feature adds a consolidated TODO email for Paul Caramuto that aggregates action items from all teams (Toolchain, FOA, Assessment, BOA) into a single, prioritized list.

## Implementation Summary

### 1. New Email Template
**File**: `config/mail_template.yaml`

Added `paul_todo_summary` template with:
- **Subject**: "📋 Paul Caramuto - Consolidated TODO List - {date}"
- **Summary Statistics**: Total TODOs, teams covered, Slack/Jira mentions
- **Consolidated Action Items**: AI-generated prioritized list across all teams
- **TODO Items by Team**: Organized breakdown by team

### 2. Modified Workflow Script
**File**: `.github/workflows/scripts/github_daily_report.py`

#### Key Changes:

1. **New Function: `send_paul_consolidated_todo_email()`** (lines 1077-1173)
   - Aggregates Paul's TODOs from all teams
   - Generates consolidated AI summary using Gemini
   - Formats TODOs by team with statistics
   - Sends email using the new template

2. **Modified Function: `send_team_email()`** (line 1021)
   - Now accepts `paul_todo_items` as parameter
   - Avoids regenerating TODOs (optimization)

3. **Modified Function: `main()`** (lines 1176-1244)
   - Stores Paul's TODO data in `all_team_todos` dictionary
   - Tracks Slack and Jira mention counts per team
   - Generates Paul's TODOs once per team (no duplication)
   - Sends consolidated TODO email after all team emails

## Email Workflow

### Previous Workflow (4 emails)
```
1. Toolchain Team Report
2. FOA Team Report  
3. Assessment Team Report
4. BOA Team Report
```

### New Workflow (5 emails)
```
1. Toolchain Team Report (with team-specific Paul TODOs)
2. FOA Team Report (with team-specific Paul TODOs)
3. Assessment Team Report (with team-specific Paul TODOs)
4. BOA Team Report (with team-specific Paul TODOs)
5. Paul Consolidated TODO Summary (all teams aggregated)
```

## Data Collection Pattern

### Optimized Approach
- **Paul's TODOs generated once per team** (line 1214)
- **Stored in memory** for both team email and consolidated email
- **No duplicate API calls** for TODO generation
- **Same data reused** for both purposes

### Data Flow
```
For each team:
  1. Collect team data (Slack + Jira)
  2. Generate AI analysis
  3. Generate Paul TODO items (ONCE) ← stored
  4. Send team email (uses stored TODOs)
  5. Store in all_team_todos for later

After all teams:
  6. Generate consolidated AI summary from all_team_todos
  7. Send Paul consolidated TODO email
```

## Email Content Structure

### Paul Consolidated TODO Email Contains:

1. **Summary Statistics**
   - Total teams covered (4)
   - Total Slack mentions across all teams
   - Total Jira mentions across all teams
   - Search period (configurable, default 30 days)

2. **Consolidated Action Items**
   - AI-generated prioritized list (5-7 items)
   - De-duplicated across teams
   - Format: `[PRIORITY] Action item - (Related teams: X, Y)`
   - Priorities: HIGH, MEDIUM, LOW

3. **TODO Items by Team**
   - Toolchain Team section
     - Slack mentions count
     - Jira mentions count
     - Team-specific TODOs
   - FOA Team section (same structure)
   - Assessment Team section (same structure)
   - BOA Team section (same structure)

## Configuration

### Time Ranges (config/mail_template.yaml)
```yaml
time_ranges:
  slack:
    paul_todo_search_days: 30  # How far back to search for Paul mentions
```

### Recipients (config/mail_template.yaml)
```yaml
recipients:
  default: ["pacaramu@redhat.com"]
```

## Benefits

### 1. **Single Consolidated View**
- Paul gets one comprehensive TODO list instead of checking 4 separate emails
- Easy to prioritize across all teams

### 2. **No Duplicate Work**
- TODOs generated once per team
- Reused for both team emails and consolidated email
- Efficient API usage

### 3. **AI-Powered Prioritization**
- Consolidated AI analysis identifies highest priority items
- De-duplicates similar items across teams
- Groups related items together

### 4. **Context Preserved**
- Individual team emails still show team-specific TODOs
- Consolidated email shows both overall priorities and team breakdowns

### 5. **Configurable Search Period**
- Control how far back to search for Paul mentions
- Configured in mail_template.yaml

## API Calls Summary

### Previous (without consolidated email):
- Slack: ~20-24 calls
- Jira: ~8 calls
- Gemini: ~24-28 calls
- **Total**: ~50+ calls

### Current (with consolidated email):
- Slack: ~20-24 calls (same)
- Jira: ~8 calls (same)
- Gemini: ~29-33 calls (+1 for consolidated summary)
- **Total**: ~55+ calls

**Impact**: Only +1 additional Gemini API call for consolidated summary

## Testing

To test this feature:

1. **Manual Test**: Run the workflow manually
   ```bash
   # From GitHub Actions UI, trigger: "Daily Team Report - Jira & Slack Summary"
   ```

2. **Check Email**: Verify 5 emails are received:
   - 4 team reports with team-specific Paul TODOs
   - 1 consolidated Paul TODO summary

3. **Verify Content**:
   - Consolidated email shows all teams
   - Statistics are accurate
   - AI-generated priorities make sense
   - Team-specific sections are complete

## Future Enhancements

Potential improvements:
1. **Configurable Recipients**: Different recipients for consolidated email
2. **Priority Filters**: Option to only show HIGH priority items
3. **Time-based Sections**: Group by urgency (today, this week, later)
4. **Link to Team Emails**: Add references to specific team reports
5. **Completion Tracking**: Mark items as done in future runs
6. **Trend Analysis**: Compare TODO counts over time

## Files Modified

1. `config/mail_template.yaml` - Added `paul_todo_summary` template
2. `.github/workflows/scripts/github_daily_report.py` - Added consolidation logic

## Related Documentation

- Email Setup: `EMAIL_SETUP.md`
- Architecture: `ARCHITECTURE_DIAGRAM.md`
- Main README: `README.md`

