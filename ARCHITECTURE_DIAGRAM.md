# Features Teams MCP Server - Current Architecture

## 🏗️ System Overview

This diagram shows the current, cleaned-up architecture of the Features Teams MCP Server after consolidation and cleanup.

## 📁 Current Project Structure

```
features-teams/
├── server.py                    # Main MCP server (direct imports)
├── connectors/                  # Modular connector system
│   ├── jira/                   # Jira connector
│   │   ├── client.py           # Jira API client
│   │   ├── config.py           # Jira config loader
│   │   └── tools/              # Jira MCP tools
│   │       ├── __init__.py     # Tool registration
│   │       ├── search_issues.py
│   │       ├── get_team_issues.py
│   │       ├── get_project_info.py
│   │       ├── get_user_info.py
│   │       ├── list_teams.py
│   │       └── list_organizations.py
│   └── slack/                  # Slack connector
│       ├── client.py           # Slack API client
│       ├── config.py           # Slack config loader
│       └── tools/              # Slack MCP tools
│           ├── __init__.py     # Tool registration
│           ├── slack_dumper.py
│           ├── slack_reader.py
│           └── search_slack_mentions.py
├── config/                     # Configuration files
│   ├── jira.yaml              # Jira teams & organizations
│   └── slack.yaml             # Slack channels & user mappings
├── utils/                      # Shared utilities
│   ├── responses.py            # Response helpers
│   └── validators.py           # Input validation
├── slack_dumps_parsed/            # Parsed Slack dumps with real names
├── slack_dumps/               # Slack data cache
└── [container files]          # Containerfile, Makefile, etc.
```

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Features Teams MCP Server                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   MCP Client    │    │   MCP Server    │    │  Connectors │ │
│  │   (Cursor AI)   │    │   (server.py)   │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • Tool requests │    │ • Direct imports│    │ • Jira      │ │
│  │ • Natural lang  │    │ • Tool registry │    │ • Slack     │ │
│  │ • Results       │    │ • Error handling│    │ • Future... │ │
│  │                 │    │                 │    │             │ │
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
│  │                 │    │ • user mappings │    │ • Data dumps│ │
│  │ "Search Slack   │    │                 │    │             │ │
│  │  mentions"      │    │                 │    │             │ │
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

### Slack Tools (10 tools)
```
┌─────────────────────────────────────────────────────────────────┐
│                        Slack Connector                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Slack Client   │    │  Slack Config   │    │ Slack Tools │ │
│  │                 │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • API wrapper   │    │ • Channel maps  │    │ • dump_slack_channel│ │
│  │ • Auth handling │    │ • User mappings │    │ • dump_team_slack_data│ │
│  │ • Data fetching │    │ • Data settings │    │ • read_slack_channel│ │
│  │ • Auto-caching  │    │ • Team mappings │    │ • read_team_slack_data│ │
│  │                 │    │                 │    │ • list_slack_dumps│ │
│  │                 │    │                 │    │ • get_slack_dump_summary│ │
│  │                 │    │                 │    │ • force_fresh_slack_dump│ │
│  │                 │    │                 │    │ • search_slack_mentions│ │
│  │                 │    │                 │    │ • search_team_slack_mentions│ │
│  │                 │    │                 │    │ • list_team_slack_channels│ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuration System

### Configuration Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  config/jira   │    │  config/slack   │    │ consolidated_   │
│     .yaml      │    │     .yaml       │    │ user_mapping    │
│                 │    │                 │    │     .yaml       │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ teams:          │    │ slack_channels: │    │ user_mappings:  │
│   toolchain:    │    │   "C123":       │    │   "U123":       │
│     name:       │    │     "toolchain" │    │     "John Doe"  │
│     members:    │    │                 │    │                 │
│       - "John"  │    │ user_display_   │    │ # Master user   │
│       - "Jane"  │    │   names:        │    │ # mapping file  │
│                 │    │   "U123":       │    │ # (reference)   │
│ organizations:  │    │     "John Doe"  │    │                 │
│   SP:           │    │                 │    │                 │
│     - "John"    │    │ data_collection:│    │                 │
│     - "Jane"    │    │   history_days: │    │                 │
│                 │    │     30          │    │                 │
│ user_display_   │    │   dump_dir:     │    │                 │
│   names:        │    │     "dumps"     │    │                 │
│   "John":       │    │                 │    │                 │
│     "jdoe"      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server (server.py)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Jira Connector │    │ Slack Connector │    │   Utils     │ │
│  │                 │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • Loads jira    │    │ • Loads slack   │    │ • Response  │ │
│  │   config        │    │   config        │    │   helpers   │ │
│  │ • Creates       │    │ • Creates       │    │ • Validators│ │
│  │   JiraClient    │    │   SlackClient   │    │ • Error     │ │
│  │ • Registers     │    │ • Registers     │    │   handling  │ │
│  │   6 tools       │    │   10 tools      │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 User Mapping System

### Consolidated User Mapping Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                    User Mapping System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ consolidated_   │    │  config/slack   │    │  config/jira│ │
│  │ user_mapping    │    │     .yaml       │    │     .yaml   │ │
│  │     .yaml       │    │                 │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ # Master file   │    │ # Slack tools   │    │ # Jira tools│ │
│  │ user_mappings:  │    │ user_display_   │    │ user_display_│ │
│  │   "U123":       │    │   names:        │    │   names:    │ │
│  │     "John Doe"  │    │   "U123":       │    │   "John":   │ │
│  │   "U456":       │    │     "John Doe"  │    │     "jdoe"  │ │
│  │     "Jane Smith"│    │   "U456":       │    │   "Jane":   │ │
│  │                 │    │     "Jane Smith"│    │     "jsmith"│ │
│  │ # 42+ mappings  │    │                 │    │             │ │
│  │ # Conflicts     │    │ # Used by       │    │ # Used by   │ │
│  │ # resolved      │    │ # search tools  │    │ # team      │ │
│  │                 │    │                 │    │ # filtering │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│           │                       │                       │     │
│           │                       │                       │     │
│           ▼                       ▼                       ▼     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    MCP Tools                               │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │ • search_slack_mentions → Uses slack.yaml mappings         │ │
│  │ • get_team_issues → Uses jira.yaml mappings                │ │
│  │ • All tools get consistent user identification             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Key Architectural Benefits

### ✅ **Simplified Structure**
- **Direct imports** in server.py (no complex auto-discovery)
- **Clean separation** between Jira and Slack connectors
- **Modular tools** with clear responsibilities

### ✅ **Consolidated Configuration**
- **Single source of truth** for user mappings (`config/slack.yaml`)
- **Separate configs** for different services (`jira.yaml`, `slack.yaml`)
- **Consistent user identification** across all tools

### ✅ **Efficient Data Flow**
- **Slack auto-caching** with smart refresh logic
- **Jira direct queries** with proper error handling
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
│     │ • Import all 10 tools                                    │
│     │ • Register with @mcp.tool()                              │
│     │                                                           │
│     ▼                                                           │
│  4. Register built-in tools                                     │
│     │ • list_available_tools()                                 │
│     │                                                           │
│     ▼                                                           │
│  5. Server ready (17 total tools)                              │
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

### Slack Tools (10)
- `dump_slack_channel` - Dump channel data
- `dump_team_slack_data` - Dump all team channels
- `read_slack_channel` - Read channel data (auto-refresh)
- `read_team_slack_data` - Read all team data
- `list_slack_dumps` - List available dumps
- `get_slack_dump_summary` - Dump statistics
- `force_fresh_slack_dump` - Force refresh
- `search_slack_mentions` - Search mentions
- `search_team_slack_mentions` - Team-wide search
- `list_team_slack_channels` - List team channels

### Built-in Tools (1)
- `list_available_tools` - List all available tools

**Total: 17 MCP Tools**

## 🎯 Future Extensibility

The current architecture supports easy extension:

1. **New Connectors**: Add new `connectors/new_service/` directory
2. **New Tools**: Add to existing connector's `tools/` directory
3. **New Configs**: Add new `config/new_service.yaml`
4. **Server Updates**: Import and register new connector in `server.py`

This architecture provides a clean, maintainable foundation for the Features Teams MCP Server.
