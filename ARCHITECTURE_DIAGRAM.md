# Work Planner MCP Server - Current Architecture

## 🏗️ System Overview

This diagram shows the current, comprehensive architecture of the Work Planner MCP Server with all four connectors: Jira, Slack, Gemini AI, and Schedule Management.

## 📁 Current Project Structure

```
work-planner/
├── server.py                    # Main MCP server (direct imports)
├── connectors/                  # Modular connector system
│   ├── jira/                   # Jira connector
│   │   ├── client.py           # Jira API client
│   │   ├── config.py           # Jira config loader
│   │   └── tools/              # Jira MCP tools (6 tools)
│   │       ├── __init__.py     # Tool registration
│   │       ├── search_issues.py
│   │       ├── get_team_issues.py
│   │       ├── get_project_info.py
│   │       ├── get_user_info.py
│   │       ├── list_teams.py
│   │       └── list_organizations.py
│   ├── slack/                  # Slack connector
│   │   ├── client.py           # Slack API client
│   │   ├── config.py           # Slack config loader
│   │   ├── tools/              # Slack MCP tools (5 tools)
│   │   │   ├── __init__.py     # Tool registration
│   │   │   ├── unified_slack_tools.py
│   │   │   ├── slack_dumper.py
│   │   │   ├── slack_reader.py
│   │   │   └── search_slack_mentions.py
│   │   └── slack_dump/         # Slack data organization
│   │       ├── slack_dumps/    # Raw Slack data cache
│   │       └── slack_dumps_parsed/ # Parsed Slack dumps with real names
│   ├── gemini/                 # Gemini AI connector
│   │   ├── client.py           # Gemini API client
│   │   ├── config.py           # Gemini config loader
│   │   └── tools/              # AI analysis tools (4 tools)
│   │       ├── __init__.py     # Tool registration
│   │       ├── analyze_slack_data.py
│   │       ├── analyze_jira_data.py
│   │       ├── generate_email_summary.py
│   │       └── custom_ai_analysis.py
│   └── schedule/               # Schedule management connector
│       ├── config.py           # Schedule config loader
│       └── tools/              # Schedule tools (5 tools)
│           ├── __init__.py     # Tool registration
│           ├── get_schedule_status.py
│           ├── run_scheduled_collection.py
│           ├── update_schedule_config.py
│           ├── add_team_to_schedule.py
│           └── remove_team_from_schedule.py
├── config/                     # Configuration files
│   ├── jira.yaml              # Jira teams & organizations
│   ├── slack.yaml             # Slack channels & user mappings
│   ├── gemini.yaml            # Gemini AI configuration
│   └── schedule.yaml          # Schedule configuration
├── utils/                      # Shared utilities
│   ├── responses.py            # Response helpers
│   └── validators.py           # Input validation
└── [container files]          # Containerfile, Makefile, etc.
```

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Work Planner MCP Server                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   MCP Client    │    │   MCP Server    │    │  Connectors │ │
│  │   (Cursor AI)   │    │   (server.py)   │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • Tool requests │    │ • Direct imports│    │ • Jira      │ │
│  │ • Natural lang  │    │ • Tool registry │    │ • Slack     │ │
│  │ • Results       │    │ • Error handling│    │ • Gemini    │ │
│  │                 │    │                 │    │ • Schedule  │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│           │                       │                       │     │
│           │                       │                       │     │
│           ▼                       ▼                       ▼     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   User Query    │    │  Configuration  │    │   External  │ │
│  │                 │    │                 │    │   APIs      │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ "Get toolchain  │    │ • jira.yaml     │    │ • Jira API  │ │
│  │  tickets"       │    │ • slack.yaml    │    │ • Slack API │ │
│  │                 │    │ • gemini.yaml   │    │ • Gemini AI │ │
│  │ "Analyze team   │    │ • schedule.yaml │    │ • Data dumps│ │
│  │  data"          │    │ • user mappings │    │ • Schedules │ │
│  │                 │    │                 │    │             │ │
│  │ "Generate       │    │                 │    │             │ │
│  │  email summary" │    │                 │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🛠️ Tool Architecture

### Jira Tools (6 tools)
```
┌─────────────────────────────────────────────────────────────────┐
│                        Jira Connector                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Jira Client   │    │   Jira Config   │    │  Jira Tools │ │
│  │                 │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • API wrapper   │    │ • Teams config  │    │ • search_issues│ │
│  │ • Auth handling │    │ • Organizations │    │ • get_team_issues│ │
│  │ • Query builder │    │ • User mappings │    │ • get_project_info│ │
│  │ • Error handling│    │ • Team aliases  │    │ • get_user_info│ │
│  │                 │    │                 │    │ • list_teams│ │
│  │                 │    │                 │    │ • list_organizations│ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Slack Tools (5 tools)
```
┌─────────────────────────────────────────────────────────────────┐
│                        Slack Connector                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Slack Client   │    │  Slack Config   │    │ Slack Tools │ │
│  │                 │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • API wrapper   │    │ • Channel maps  │    │ • dump_slack_data│ │
│  │ • Auth handling │    │ • User mappings │    │ • read_slack_data│ │
│  │ • Data fetching │    │ • Data settings │    │ • search_slack_data│ │
│  │ • Auto-caching  │    │ • Team mappings │    │ • list_slack_channels│ │
│  │                 │    │                 │    │ • list_slack_dumps│ │
│  │                 │    │                 │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Gemini AI Tools (4 tools)
```
┌─────────────────────────────────────────────────────────────────┐
│                        Gemini AI Connector                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ Gemini Client   │    │ Gemini Config    │    │ AI Tools    │ │
│  │                 │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • API wrapper   │    │ • Model config  │    │ • analyze_slack_data│ │
│  │ • Auth handling │    │ • Prompts       │    │ • analyze_jira_data│ │
│  │ • Content gen  │    │ • Analysis types│    │ • generate_email_summary│ │
│  │ • Error handling│    │ • Output format │    │ • custom_ai_analysis│ │
│  │                 │    │                 │    │             │ │
│  │                 │    │                 │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Schedule Management Tools (5 tools)
```
┌─────────────────────────────────────────────────────────────────┐
│                    Schedule Management Connector                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ Schedule Client │    │ Schedule Config │    │ Schedule    │ │
│  │                 │    │                 │    │ Tools       │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • Cron handling │    │ • Service config│    │ • get_schedule_status│ │
│  │ • Task execution│    │ • Team schedules│    │ • run_scheduled_collection│ │
│  │ • Error handling│    │ • Global settings│    │ • update_schedule_config│ │
│  │ • Status tracking│    │ • Notifications │    │ • add_team_to_schedule│ │
│  │                 │    │                 │    │ • remove_team_from_schedule│ │
│  │                 │    │                 │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration System

### Configuration Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  config/jira   │    │  config/slack   │    │ config/gemini  │    │ config/schedule │
│     .yaml      │    │     .yaml       │    │     .yaml       │    │     .yaml       │
│                 │    │                 │    │                 │    │                 │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ teams:          │    │ slack_channels: │    │ model:          │    │ global:         │
│   toolchain:    │    │   "C123":       │    │   "gemini-2.0"  │    │   timezone: UTC │
│     name:       │    │     "toolchain" │    │                 │    │                 │
│     members:    │    │                 │    │ generation_     │    │ slack:          │
│       - "John"  │    │ user_display_   │    │   config:       │    │   enabled: true │
│       - "Jane"  │    │   names:        │    │     temperature │    │   schedule:     │
│                 │    │   "U123":       │    │     max_tokens  │    │     "0 6 * * *"│
│ organizations:  │    │     "John Doe"  │    │                 │    │                 │
│   SP:           │    │                 │    │ prompts:        │    │ teams:          │
│     - "John"    │    │ data_collection:│    │   slack_analysis│    │   - name: toolchain│
│     - "Jane"    │    │   history_days: │    │   jira_analysis │    │     channels: all│
│                 │    │     30          │    │   email_summary│    │                 │
│ user_display_   │    │   dump_dir:     │    │   custom_analysis│    │ cleanup:        │
│   names:        │    │     "dumps"     │    │                 │    │   enabled: true │
│   "John":       │    │                 │    │ analysis_types: │    │   schedule:     │
│     "jdoe"      │    │                 │    │   slack: [...]  │    │     "0 2 * * 0"│
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              MCP Server (server.py)                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Jira Connector │    │ Slack Connector │    │ Gemini Connector│    │Schedule Conn│ │
│  │                 │    │                 │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • Loads jira    │    │ • Loads slack   │    │ • Loads gemini  │    │ • Loads     │ │
│  │   config        │    │   config        │    │   config        │    │   schedule  │ │
│  │ • Creates       │    │ • Creates       │    │ • Creates       │    │   config    │ │
│  │   JiraClient    │    │   SlackClient   │    │   GeminiClient  │    │ • Creates   │ │
│  │ • Registers     │    │ • Registers     │    │ • Registers     │    │   ScheduleClient│ │
│  │   6 tools       │    │   5 tools       │    │   4 tools       │    │ • Registers │ │
│  │                 │    │                 │    │                 │    │   5 tools    │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 🎯 User Mapping System

### Consolidated User Mapping Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                    User Mapping System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  config/slack   │    │  config/jira    │    │  config/    │ │
│  │     .yaml       │    │     .yaml       │    │  gemini.yaml│ │
│  │                 │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ # Slack tools   │    │ # Jira tools    │    │ # AI tools  │ │
│  │ user_display_   │    │ user_display_   │    │ # Uses same  │ │
│  │   names:        │    │   names:        │    │ # user maps  │ │
│  │   "U123":       │    │   "John":       │    │ # for context│ │
│  │     "John Doe"  │    │     "jdoe"      │    │             │ │
│  │   "U456":       │    │   "Jane":       │    │ # Analysis   │ │
│  │     "Jane Smith"│    │     "jsmith"    │    │ # prompts    │ │
│  │                 │    │                 │    │ # include    │ │
│  │ # 150+ mappings │    │ # Team configs  │    │ # user info  │ │
│  │ # Used by       │    │ # Used by       │    │             │ │
│  │ # search tools  │    │ # team          │    │             │ │
│  │                 │    │ # filtering     │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│           │                       │                       │     │
│           │                       │                       │     │
│           ▼                       ▼                       ▼     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    MCP Tools                               │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │ • search_slack_data → Uses slack.yaml mappings            │ │
│  │ • get_team_issues → Uses jira.yaml mappings                │ │
│  │ • analyze_slack_data → Uses both for context               │ │
│  │ • All tools get consistent user identification             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Key Architectural Benefits

### ✅ **Comprehensive Integration**
- **Four Connectors**: Jira, Slack, Gemini AI, and Schedule Management
- **21 MCP Tools**: Complete coverage of team workflow needs
- **Unified Interface**: Single MCP server for all team operations

### ✅ **Simplified Structure**
- **Direct imports** in server.py (no complex auto-discovery)
- **Clean separation** between all connectors
- **Modular tools** with clear responsibilities

### ✅ **Consolidated Configuration**
- **Single source of truth** for user mappings (`config/slack.yaml`)
- **Separate configs** for different services
- **Consistent user identification** across all tools

### ✅ **Efficient Data Flow**
- **Slack auto-caching** with smart refresh logic
- **Jira direct queries** with proper error handling
- **AI analysis** with intelligent prompts
- **Schedule management** with automated collection
- **Unified response format** across all tools

### ✅ **Maintainable Code**
- **No dead code** (removed unused BaseConnector, auto-discovery)
- **Clear file organization** with logical grouping
- **Easy to extend** with new connectors or tools

## 🔄 Tool Registration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Tool Registration                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. server.py starts                                            │
│     │                                                           │
│     ▼                                                           │
│  2. Import Jira connector                                       │
│     │ • Load jira.yaml config                                  │
│     │ • Create JiraClient                                      │
│     │ • Import all 6 tools                                     │
│     │ • Register with @mcp.tool()                              │
│     │                                                           │
│     ▼                                                           │
│  3. Import Slack connector                                      │
│     │ • Load slack.yaml config                                 │
│     │ • Create SlackClient                                     │
│     │ • Import all 5 tools                                     │
│     │ • Register with @mcp.tool()                              │
│     │                                                           │
│     ▼                                                           │
│  4. Import Gemini connector                                     │
│     │ • Load gemini.yaml config                                │
│     │ • Create GeminiClient                                    │
│     │ • Import all 4 tools                                     │
│     │ • Register with @mcp.tool()                              │
│     │                                                           │
│     ▼                                                           │
│  5. Import Schedule connector                                   │
│     │ • Load schedule.yaml config                              │
│     │ • Create ScheduleClient                                  │
│     │ • Import all 5 tools                                     │
│     │ • Register with @mcp.tool()                              │
│     │                                                           │
│     ▼                                                           │
│  6. Register built-in tools                                     │
│     │ • list_available_tools()                                 │
│     │                                                           │
│     ▼                                                           │
│  7. Server ready (21 total tools)                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Current Tool Inventory

### Jira Tools (6)
- `search_issues` - JQL-based issue search
- `get_team_issues` - Team-specific issue queries
- `get_project_info` - Project metadata
- `get_user_info` - User information
- `list_teams` - Available teams
- `list_organizations` - Available organizations

### Slack Tools (5)
- `dump_slack_data` - Dump channel or team data
- `read_slack_data` - Read channel or team data (auto-refresh)
- `search_slack_data` - Search mentions in channels or teams
- `list_slack_channels` - List all Slack channels
- `list_slack_dumps` - List available dumps

### AI Analysis Tools (4)
- `analyze_slack_data` - Analyze Slack data using Gemini AI
- `analyze_jira_data` - Analyze Jira data using Gemini AI
- `generate_email_summary` - Generate email summary combining data
- `custom_ai_analysis` - Perform custom AI analysis with prompts

### Schedule Management Tools (5)
- `get_schedule_status` - Get current schedule status
- `run_scheduled_collection` - Run scheduled data collection
- `update_schedule_config` - Update schedule configuration
- `add_team_to_schedule` - Add team to schedule
- `remove_team_from_schedule` - Remove team from schedule

### Built-in Tools (1)
- `list_available_tools` - List all available tools

**Total: 21 MCP Tools**

## 🔄 Data Collection and Analysis Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                Data Collection and Analysis Flow               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Schedule       │    │   Data Sources  │    │   AI        │ │
│  │   Management     │    │                 │    │   Analysis   │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • Cron schedules │    │ • Jira API      │    │ • Slack     │ │
│  │ • Team configs   │    │ • Slack API    │    │   analysis   │ │
│  │ • Service status │    │ • Data dumps   │    │ • Jira      │ │
│  │ • Auto cleanup   │    │ • User mappings │    │   analysis   │ │
│  │                 │    │                 │    │ • Email     │ │
│  │                 │    │                 │    │   summaries │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│           │                       │                       │     │
│           │                       │                       │     │
│           ▼                       ▼                       ▼     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Automated Workflow                      │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │ 1. Schedule triggers data collection                       │ │
│  │ 2. Slack data dumped and cached                            │ │
│  │ 3. Jira data queried and stored                             │ │
│  │ 4. AI analysis performed on collected data                  │ │
│  │ 5. Email summaries generated                                │ │
│  │ 6. Results available through MCP tools                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Future Extensibility

The current architecture supports easy extension:

1. **New Connectors**: Add new `connectors/new_service/` directory
2. **New Tools**: Add to existing connector's `tools/` directory
3. **New Configs**: Add new `config/new_service.yaml`
4. **Server Updates**: Import and register new connector in `server.py`

This architecture provides a clean, maintainable foundation for the Work Planner MCP Server with comprehensive team workflow support.