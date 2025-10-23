# Unified TODO Extraction Implementation Plan

**Status:** 📋 Planning Phase  
**Created:** 2024-11-21  
**Goal:** Extract actionable TODO items from Email, Jira, and Slack using Gemini AI natural language understanding

---

## 🎯 Vision

Create a unified TODO extraction system that analyzes all work communications and intelligently extracts actionable tasks:

```
TODO Items from:
├── 📧 Emails (Gmail inbox)
├── 🎫 Jira (issues & comments)
└── 💬 Slack (messages & threads)
```

---

## 📊 Current State Analysis

### What We Have:

| Connector | Current Capability | TODO Detection |
|-----------|-------------------|----------------|
| **Email** | ❌ Sending only (SMTP) | ❌ None |
| **Jira** | ✅ Fetch issues, reports | ❌ None (just status tracking) |
| **Slack** | ✅ Dump messages, search | ❌ None (just message storage) |

### What We're Building:

| Connector | New Capability | TODO Detection |
|-----------|----------------|----------------|
| **Email** | ✅ Read inbox via IMAP | ✅ **NEW** Gemini NLU extraction |
| **Jira** | ✅ Enhanced issue analysis | ✅ **NEW** Gemini NLU extraction |
| **Slack** | ✅ Enhanced message analysis | ✅ **NEW** Gemini NLU extraction |

---

## 🏗️ Architecture Design

### Unified Configuration - `config/gemini.yaml`

All three connectors use the **same unified TODO extraction configuration**:

```yaml
# Unified TODO Extraction from Email, Jira, and Slack
todo_extraction:
  enabled: true
  
  # AI Model settings (shared across all sources)
  model: "gemini-1.5-flash"
  temperature: 0.3
  max_output_tokens: 2000
  
  # Detection settings (shared)
  detection:
    confidence_threshold: 0.6
    max_todos_per_item: 3
  
  # Source-specific settings
  sources:
    email:
      enabled: true
      priority_weight: 1.2  # Emails get 20% urgency boost
      
    jira:
      enabled: true
      priority_weight: 1.0
      analyze_assigned_issues: true
      analyze_comments: true  # Extract from @mentions in comments
      analyze_descriptions: true
      
    slack:
      enabled: true
      priority_weight: 0.9  # Slack is more casual
      analyze_direct_messages: true
      analyze_mentions: true
      analyze_thread_replies: true
  
  # Unified system prompt (works for all sources)
  prompts:
    system_prompt: |
      You are an expert at analyzing professional communications (emails, Jira issues, Slack messages) 
      and extracting actionable TODO items using natural language understanding.
      
      Intelligent criteria for identifying tasks:
      
      1. **Direct Instructions & Explicit Requests**: 
         - Direct assignments, @mentions, clear commands
         - Questions requiring response
      
      2. **Implicit Actions & Strong Verbs**:
         - Action verbs: review, approve, finalize, send, update, test, document
         - "We need to...", "Let's...", "Please..."
      
      3. **Context from Key People**:
         - Prioritize managers, team leads, stakeholders
         - Direct 1-on-1 communications
      
      4. **Deadlines and Urgency**:
         - Due dates, sprint deadlines, release dates
         - "ASAP", "urgent", "by EOD", "before meeting"
      
      5. **Decision & Approval Requests**:
         - "needs your approval", "please review", "waiting on you"
      
      Output format: JSON array with description, urgency, deadline, context, confidence
    
    # Email-specific extraction prompt
    email_prompt: |
      Analyze this email for actionable TODOs.
      
      From: {email_from}
      Subject: {email_subject}
      Date: {email_date}
      
      {email_body}
      
      Extract actionable TODOs with description, urgency (critical/high/medium/low), 
      deadline (YYYY-MM-DD or null), context, and confidence (0.0-1.0).
      
      Return JSON array or [] if no TODOs.
    
    # Jira-specific extraction prompt
    jira_prompt: |
      Analyze this Jira issue for actionable TODOs for the assignee/mentioned user.
      
      Issue: {issue_key} - {issue_summary}
      Status: {issue_status}
      Assigned: {assignee}
      Priority: {priority}
      
      Description:
      {description}
      
      Recent Comments:
      {comments}
      
      Focus on:
      - Action items in comments (especially @mentions)
      - Blockers needing resolution
      - Review/approval requests
      - Testing or documentation needs
      - Specific tasks within the issue
      
      Extract actionable TODOs with description, urgency, deadline, context, and confidence.
      Return JSON array or [] if no TODOs.
    
    # Slack-specific extraction prompt  
    slack_prompt: |
      Analyze this Slack message/thread for actionable TODOs for the user.
      
      Channel: {channel}
      From: {sender}
      Date: {date}
      
      Message:
      {message}
      
      Thread Context:
      {thread_context}
      
      Focus on:
      - Direct questions or requests to the user
      - @mentions asking for action
      - Commitments made by the user
      - Follow-up requests
      - Shared team tasks
      
      Extract actionable TODOs with description, urgency, deadline, context, and confidence.
      Return JSON array or [] if no TODOs.
```

---

## 📁 File Structure Changes

### New Files to Create:

```
config/
├── email.yaml (NEW) - Email infrastructure config
└── gemini.yaml (UPDATE) - Add todo_extraction section

connectors/email/
├── client.py (EXTEND) - Add InboxReader class
├── config.py (UPDATE) - Load email.yaml
└── tools/
    ├── inbox_tools.py (NEW) - extract_email_todos_tool
    └── inbox_helpers.py (NEW) - Email TODO helpers

connectors/jira/tools/
├── extract_jira_todos.py (NEW) - extract_jira_todos_tool
└── jira_todo_helpers.py (NEW) - Jira TODO helpers

connectors/slack/tools/
├── extract_slack_todos.py (NEW) - extract_slack_todos_tool
└── slack_todo_helpers.py (NEW) - Slack TODO helpers

connectors/gemini/tools/
└── extract_all_todos_tool.py (NEW) - Unified extraction

server.py (UPDATE) - Register 4 new tools
```

---

## 🔧 Implementation Phases

### Phase 1: Email TODO Extraction (NEW) - 2 hours

**Priority:** 🔴 High

**Files to create:**
1. `config/email.yaml` - Email infrastructure settings (IMAP, filtering)
2. `connectors/email/client.py` - Add `InboxReader` class with IMAP support
3. `connectors/email/config.py` - Load email.yaml
4. `connectors/email/tools/inbox_tools.py` - Main MCP tool
5. `connectors/email/tools/inbox_helpers.py` - Helper functions

**What it does:**
- Connect to Gmail via IMAP (reuse EMAIL_USERNAME, EMAIL_PASSWORD)
- Fetch emails from past 30 days
- Filter out automated emails, newsletters
- Use Gemini to extract TODOs using natural language understanding
- Return structured TODO list

**MCP Tool:**
```python
extract_email_todos(days_back: int = 30) -> str
```

**Output Example:**
```json
{
  "success": true,
  "emails_analyzed": 45,
  "todos_found": 8,
  "todos": [
    {
      "source": "email",
      "description": "Review Q4 budget proposal",
      "urgency": "high",
      "deadline": "2024-11-29",
      "context": "Manager needs approval before meeting",
      "confidence": 0.95,
      "metadata": {
        "from": "manager@redhat.com",
        "subject": "Q4 Budget Review"
      }
    }
  ]
}
```

---

### Phase 2: Jira TODO Extraction (ENHANCE EXISTING) - 1.5 hours

**Priority:** 🟡 Medium

**Files to create:**
1. `connectors/jira/tools/extract_jira_todos.py` - Main MCP tool
2. `connectors/jira/tools/jira_todo_helpers.py` - Helper functions

**What it does:**
- Reuse existing `jira_client` to fetch issues
- Analyze issue descriptions for implicit tasks
- Analyze comments for @mentions and action items
- Use Gemini to extract TODOs
- Return structured TODO list

**MCP Tool:**
```python
extract_jira_todos(
    team: str = None,
    include_assigned: bool = True,
    include_comments: bool = True,
    days_back: int = 30
) -> str
```

**Output Example:**
```json
{
  "success": true,
  "issues_analyzed": 23,
  "todos_found": 12,
  "todos": [
    {
      "source": "jira",
      "description": "Add test coverage for authentication module",
      "urgency": "high",
      "deadline": "2024-12-01",
      "context": "Comment from QA lead requesting unit tests",
      "confidence": 0.92,
      "metadata": {
        "issue_key": "RHEL-1234",
        "issue_link": "https://issues.redhat.com/browse/RHEL-1234",
        "comment_author": "qa_lead@redhat.com"
      }
    }
  ]
}
```

---

### Phase 3: Slack TODO Extraction (ENHANCE EXISTING) - 1.5 hours

**Priority:** 🟡 Medium

**Files to create:**
1. `connectors/slack/tools/extract_slack_todos.py` - Main MCP tool
2. `connectors/slack/tools/slack_todo_helpers.py` - Helper functions

**What it does:**
- Reuse existing Slack dumps from `unified_slack_tools.py`
- Analyze messages for @mentions of user
- Analyze DMs for action requests
- Analyze thread replies for follow-ups
- Use Gemini to extract TODOs
- Return structured TODO list

**MCP Tool:**
```python
extract_slack_todos(
    team: str = None,
    include_dms: bool = True,
    include_mentions: bool = True,
    days_back: int = 30
) -> str
```

**Output Example:**
```json
{
  "success": true,
  "messages_analyzed": 156,
  "todos_found": 4,
  "todos": [
    {
      "source": "slack",
      "description": "Share CI/CD pipeline documentation with team",
      "urgency": "medium",
      "deadline": null,
      "context": "@paul in #toolchain-general requesting docs",
      "confidence": 0.85,
      "metadata": {
        "channel": "#toolchain-general",
        "message_link": "https://redhat.slack.com/...",
        "mentioned_by": "teammate"
      }
    }
  ]
}
```

---

### Phase 4: Unified TODO Extraction - 1 hour

**Priority:** 🟢 Nice-to-have

**Files to create:**
1. `connectors/gemini/tools/extract_all_todos_tool.py` - Unified extraction tool

**What it does:**
- Call all three extraction tools (email, Jira, Slack)
- Merge results
- Deduplicate similar TODOs (e.g., same task mentioned in email + Jira)
- Sort by urgency and deadline
- Group by source and urgency

**MCP Tool:**
```python
extract_all_todos(days_back: int = 30) -> str
```

**Output Example:**
```json
{
  "success": true,
  "analysis_period": "2024-10-22 to 2024-11-21 (30 days)",
  "summary": {
    "total_todos": 24,
    "by_source": {
      "email": 8,
      "jira": 12,
      "slack": 4
    },
    "by_urgency": {
      "critical": 2,
      "high": 8,
      "medium": 10,
      "low": 4
    }
  },
  "todos": [...],
  "grouped_by_urgency": {...},
  "grouped_by_source": {...}
}
```

---

## 🎯 New MCP Tools Summary

```python
# Individual source extraction
extract_email_todos(days_back: int = 30)
extract_jira_todos(team: str = None, days_back: int = 30)
extract_slack_todos(team: str = None, days_back: int = 30)

# Unified extraction (Phase 4)
extract_all_todos(days_back: int = 30)
```

---

## ⏱️ Implementation Timeline

| Phase | Task | Time | Cumulative |
|-------|------|------|------------|
| **Phase 1** | Email TODO extraction | 2 hours | 2 hours |
| **Phase 2** | Jira TODO extraction | 1.5 hours | 3.5 hours |
| **Phase 3** | Slack TODO extraction | 1.5 hours | 5 hours |
| **Phase 4** | Unified extraction | 1 hour | 6 hours |
| **Total** | | **6 hours** | |

---

## 🔑 Key Architecture Decisions

1. ✅ **Unified configuration in `gemini.yaml`** - All TODO extraction uses same AI settings
2. ✅ **Hybrid approach maintained** - New tool files + helper files (consistent with existing patterns)
3. ✅ **Reuse existing connectors** - Leverage existing Jira/Slack data fetching
4. ✅ **Natural language analysis** - No manual keywords, let Gemini understand context
5. ✅ **Consistent output format** - All tools return same JSON structure
6. ✅ **Same authentication** - Reuse EMAIL_USERNAME/EMAIL_PASSWORD for IMAP

---

## 🔐 Authentication

**Email (IMAP):**
- Uses existing `EMAIL_USERNAME` env var (pacaramu@redhat.com)
- Uses existing `EMAIL_PASSWORD` env var (Gmail App Password)
- Same credentials work for both SMTP (sending) and IMAP (reading)

**Jira:**
- Uses existing Jira authentication from `connectors/jira/client.py`

**Slack:**
- Uses existing Slack authentication from `connectors/slack/client.py`

**No new credentials needed!**

---

## 📊 Benefits

1. **Automated task discovery** - Never miss action items from emails, Jira, or Slack
2. **Intelligent prioritization** - AI understands context and urgency
3. **Context preservation** - Know why each task is important and who requested it
4. **Unified view** - See all TODOs in one place
5. **Configurable** - Adjust time ranges, filters, and thresholds
6. **No manual keywords** - Gemini's natural language understanding adapts to your communication style

---

## 💡 Smart Features (Future Enhancements)

1. **Deduplication** - Same task mentioned in email + Jira + Slack = 1 TODO
2. **Context Linking** - Show which sources mentioned the same task
3. **Priority Boost** - Same TODO from multiple sources = higher urgency
4. **Smart Grouping** - By project, by person, by deadline, by team
5. **Auto-dismiss** - TODOs from resolved Jira issues or old threads
6. **Trend Analysis** - Track what types of tasks are most common
7. **Notification Integration** - Alert on critical TODOs

---

## 🚀 Getting Started

When ready to implement:

### Step 1: Start with Phase 1 (Email)
```bash
# 1. Create email.yaml configuration
# 2. Add InboxReader to email/client.py
# 3. Create inbox_tools.py and inbox_helpers.py
# 4. Update gemini.yaml with todo_extraction section
# 5. Test with your Gmail inbox
```

### Step 2: Add Phase 2 (Jira)
```bash
# 1. Create extract_jira_todos.py
# 2. Create jira_todo_helpers.py
# 3. Test with your Jira issues
```

### Step 3: Add Phase 3 (Slack)
```bash
# 1. Create extract_slack_todos.py
# 2. Create slack_todo_helpers.py
# 3. Test with your Slack messages
```

### Step 4: Add Phase 4 (Unified)
```bash
# 1. Create extract_all_todos_tool.py
# 2. Test unified extraction
```

---

## 📝 Notes

- This plan leverages Gemini's natural language understanding instead of manual keywords
- All AI configuration is centralized in `gemini.yaml` for consistency
- Architecture follows existing project patterns (hybrid approach, MCP tools)
- Incremental implementation - each phase delivers value independently
- No new dependencies required (imaplib is built-in Python)

---

**Last Updated:** 2024-11-21  
**Status:** Ready for implementation when needed








