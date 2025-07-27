# **Jira Team Reporting System Structure**

## **Overview**
This system generates automated weekly/monthly reports for development teams by querying Jira tickets, using AI to summarize work, and sending detailed emails to stakeholders.

## **Team Organization Structure**

### **Project Context**
- **Main Project**: "Automotive Feature Teams" 
- **Jira Server**: Red Hat Jira (issues.redhat.com)
- **Reporting Frequency**: Weekly (configurable to monthly/quarterly)

### **Team Configurations**
```yaml
Teams:
  ToolChain Team:
    Members: 
      - Sameera Kalgudi (rhn-support-skalgudi)
      - Ozan Unsal (rhn-support-ounsal) 
      - Marcel Banas (mabanas@redhat.com)
    Focus: Development tools and infrastructure

  FoA Team (Features on Automotive):
    Members:
      - Nisha Saini (rhn-support-nsaini)
      - Ryan Smith (rsmit106)
    Focus: Testing automotive features

  BoA Team (Backend on Automotive):
    Members:
      - Jan Onderka (jonderka@redhat.com)
    Focus: Backend development

  Assessment Team:
    Members:
      - Joe Simmons-Talbott (rhn-support-josimmon)
    Focus: Assessment and evaluation
```

## **JQL Query Generation**

### **Base Query Template**
```jql
project = "Automotive Feature Teams" 
AND assignee in ({team_assignees}) 
AND (
  statusCategory = "{status}" 
  OR (statusCategory = "Done" AND resolutiondate >= -{period_days}d)
) 
ORDER BY issuetype DESC, updatedDate DESC, createdDate DESC
```

### **Query Types Generated Per Team**
1. **In Progress Tickets**: `statusCategory = "In Progress"`
2. **To Do Tickets**: `statusCategory = "To Do"`
3. **Recently Closed**: `statusCategory = "Done" AND resolutiondate >= -7d`

### **Team Query Examples**
- **FoA Team**: `assignee in ("rhn-support-nsaini", "rsmit106")`
- **BoA Team**: `assignee in ("jonderka@redhat.com")`
- **ToolChain Team**: `assignee in ("rhn-support-skalgudi", "rhn-support-ounsal", "mabanas@redhat.com")`
- **Assessment Team**: `assignee in ("rhn-support-josimmon")`

## **AI Summarization Strategy**

### **Multi-Level Analysis**
1. **Individual Ticket Comments**: Summarize actual work done
2. **Ticket Descriptions**: Summarize planned objectives
3. **Overall Team Report**: Comprehensive analysis with sections:
   - Priority Attention Needed (stale/unassigned epics)
   - Current Work (grouped by owner, narrative format)
   - Recently Closed Issues (outcomes)
   - Productivity Suggestions (specific, non-generic)

### **Assignee-Specific Summaries**
For each team member, generate:
- **Assigned Work (In Progress)**: What they're currently working on
- **Actual Work**: What they accomplished (from comments)
- **Planned Work (To-Do)**: Upcoming tasks and objectives

### **AI Prompts Used**
- **Grace Period**: 10 days (tickets older than this flagged as needing attention)
- **Comment Filtering**: Exclude "bot", "automation", "jenkins" authors
- **Output Format**: HTML for email rendering, narrative style (no bullet points)

## **Email Workflow**

### **Dual Email System**
1. **Detailed Report Email**:
   - Subject: `"{TeamName} Weekly Status Report - {date}"`
   - Content: Full ticket details + AI analysis
   - Recipients: Team stakeholders

2. **Summary Email**:
   - Subject: `"[SUMMARY] {TeamName} Weekly Status Report - {date}"`
   - Content: AI-generated assignee summaries only
   - Format: Planned vs Actual work comparison

### **Email Configuration Per Team**
```yaml
Example - FoA Team:
  subject: "FoA Team Weekly Status Report - 2025-01-27"
  message: "Weekly status update for FoA team testing"
  recipients: ["pacaramu@redhat.com"]
```

## **Key Features for MCP Integration**

### **Dynamic Team Queries**
- Teams defined in YAML configuration
- Automatic JQL generation based on assignee lists
- Configurable reporting periods (weekly/monthly/quarterly)

### **AI Provider Support**
- **Current**: Gemini (gemini-1.5-flash)
- **Fallback**: OpenAI (gpt-4o)
- Environment variable based API keys

### **Data Processing Flow**
1. **Query Execution**: Separate queries for In Progress, To Do, Done tickets
2. **Data Enrichment**: Epic linking, comment extraction, metadata processing
3. **AI Analysis**: Multiple prompt templates for different summary types
4. **Report Generation**: HTML formatting with proper linking
5. **Email Delivery**: SMTP with HTML content and structured subjects

### **Error Handling & Filtering**
- Grace period validation (10 days default)
- Bot comment filtering
- Missing epic detection
- Stale ticket identification

## **Configuration File Structure**

### **Team Definitions**
```yaml
team_configs:
  user_group_1:
    name: "ToolChain Team"
    assignees:
      - "rhn-support-skalgudi"
      - "rhn-support-ounsal"
      - "mabanas@redhat.com"
    email:
      subject: "ToolChain Team {period_title} Status Report - {date}"
      message: "{period_description} for ToolChain team development"
      recipients:
        - "pacaramu@redhat.com"

  user_group_3:
    name: "FoA Team"
    assignees:
      - "rhn-support-nsaini"
      - "rsmit106"
    email:
      subject: "FoA Team {period_title} Status Report - {date}"
      message: "{period_description} for FoA team testing"
      recipients:
        - "pacaramu@redhat.com"

  user_group_4:
    name: "BoA Team"
    assignees:
      - "jonderka@redhat.com"
    email:
      subject: "BoA Team {period_title} Status Report - {date}"
      message: "{period_description} for BoA team development"
      recipients:
        - "pacaramu@redhat.com"

  user_group_2:
    name: "Assessment Team"
    assignees:
      - "rhn-support-josimmon"
    email:
      subject: "Assessment Team {period_title} Status Report - {date}"
      message: "{period_description} for Assessment team development"
      recipients:
        - "pacaramu@redhat.com"
```

### **User Mappings**
```yaml
jira_users:
  rhn-support-nsaini:
    display_name: "Nisha Saini"
    email: "nsaini@redhat.com"
    team: "FoA"
    role: "Developer"

  rsmit106:
    display_name: "Ryan Smith"
    email: "rsmit@redhat.com"
    team: "FoA"
    role: "Developer"

  "jonderka@redhat.com":
    display_name: "Jan Onderka"
    email: "jonderka@redhat.com"
    team: "BoA"
    role: "Developer"

  rhn-support-josimmon:
    display_name: "Joe Simmons-Talbott"
    email: "josimmon@redhat.com"
    team: "Assessment"
    role: "Developer"

  rhn-support-skalgudi:
    display_name: "Sameera Kalgudi"
    email: "skalgudi@redhat.com"
    team: "ToolChain"
    role: "Developer"

  rhn-support-ounsal:
    display_name: "Ozan Unsal"
    email: "ounsal@redhat.com"
    team: "ToolChain"
    role: "Developer"

  "mabanas@redhat.com":
    display_name: "Marcel Banas"
    email: "mabanas@redhat.com"
    team: "ToolChain"
    role: "Developer"
```

### **Report Settings**
```yaml
settings:
  update_grace_days: 10
  exclude_comment_authors:
    - "bot"
    - "automation"
    - "jenkins"
  current_period: "weekly"  # weekly, monthly, quarterly
  ai_provider: "gemini"
  enable_ai_summary: true
  enable_assignee_summary_email: true
```

## **Usage Commands**

### **Generate Team Reports**
```bash
# FoA Team weekly report
python jira-report.py -c jira-config.yaml -g user_group_3 -S https://issues.redhat.com -T {api_token} -u {email} -w {password}

# BoA Team weekly report  
python jira-report.py -c jira-config.yaml -g user_group_4 -S https://issues.redhat.com -T {api_token} -u {email} -w {password}

# ToolChain Team weekly report
python jira-report.py -c jira-config.yaml -g user_group_1 -S https://issues.redhat.com -T {api_token} -u {email} -w {password}

# Assessment Team weekly report
python jira-report.py -c jira-config.yaml -g user_group_2 -S https://issues.redhat.com -T {api_token} -u {email} -w {password}
```

### **Local Testing (No Email)**
```bash
python jira-report.py -c jira-config.yaml -g user_group_3 -S https://issues.redhat.com -T {api_token} -u {email} --local
```

## **Integration Points for MCP Projects**

### **Data Sources**
- **Jira REST API**: `/rest/api/2/search` for JQL queries
- **Authentication**: Basic Auth with username + API token
- **Pagination**: Handle maxResults and startAt for large datasets

### **AI Integration**
- **Input**: Ticket data (descriptions, comments, metadata)
- **Processing**: Multiple prompt templates for different analysis types
- **Output**: Structured HTML reports with narrative summaries

### **Team Context**
- **FoA Team**: Nisha and Ryan focus on testing automotive features
- **BoA Team**: Jan handles backend development
- **ToolChain Team**: Sameera, Ozan, and Marcel work on development infrastructure
- **Assessment Team**: Joe handles evaluation and assessment tasks

This structure allows you to automatically track team progress, identify blockers, and provide stakeholders with both detailed and summarized views of development work across multiple specialized teams.

---

*This template provides a complete blueprint for replicating or integrating with the Jira team reporting system in MCP-based projects.* 