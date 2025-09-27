# Features Teams MCP Server

A clean, modular Model Context Protocol (MCP) server for querying Jira issues and Slack discussions. This server provides 17 MCP tools for comprehensive team insights through Cursor's AI assistant.

**🎯 This project is designed to work ONLY through MCP tools - no direct scripts or manual queries.**

## 🎯 Features

### MCP Tools Available

#### Jira Tools (6 tools)
1. **`search_issues`** - Search Jira issues using JQL queries
2. **`get_team_issues`** - Get issues for specific teams with optional organization filtering
3. **`get_project_info`** - Get basic project information
4. **`get_user_info`** - Get user information
5. **`list_teams`** - List all configured teams
6. **`list_organizations`** - List all configured organizations

#### Slack Tools (10 tools)
7. **`dump_slack_channel`** - Dump Slack channel data to files
8. **`dump_team_slack_data`** - Dump all team Slack channels
9. **`read_slack_channel`** - Read Slack channel data (auto-refreshes if needed)
10. **`read_team_slack_data`** - Read all team Slack data
11. **`list_slack_dumps`** - List available Slack dump files
12. **`get_slack_dump_summary`** - Get summary statistics for team dumps
13. **`force_fresh_slack_dump`** - Force fresh dump of all team channels
14. **`search_slack_mentions`** - Search for mentions in Slack channels
15. **`search_team_slack_mentions`** - Search mentions across all team channels
16. **`list_team_slack_channels`** - List Slack channels for a team

#### Built-in Tools (1 tool)
17. **`list_available_tools`** - List all available MCP tools

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create environment file with your credentials
make setup
# Edit ~/.rh-features-teams.env with your Jira URL, API token, and Slack tokens
```

### 2. Build Container

```bash
make build
```

### 3. Configure Cursor

```bash
make cursor-config
```

**⚠️ Warning**: The `make cursor-config` command will **overwrite** your existing `~/.cursor/mcp.json` file. This means:
- Any existing MCP server configurations will be **replaced**
- You'll get the default configuration from `example.mcp.json`
- If you have custom MCP server configurations, they will be lost

**💡 Note**: If you already have a working MCP configuration (like `featuresTeamsMcp`), you may not need to run this command unless you want to reset to the default configuration.

### 4. Use in Cursor

The MCP server will be available in Cursor as `featuresTeamsMcp`. You can now ask the AI assistant to:

- "Get me toolchain tickets in progress"
- "Show me issues assigned to the SP team"
- "Search for critical VROOM tickets"
- "Read toolchain team Slack discussions"
- "Search for mentions of 'deployment' in Slack"
- "List all available teams"

**✅ All queries go through MCP tools automatically**

## 📁 Project Structure

```
features-teams/
├── server.py                    # Main MCP server (direct imports)
├── connectors/                  # Modular connector system
│   ├── jira/                   # Jira connector
│   │   ├── client.py           # Jira API client
│   │   ├── config.py           # Jira config loader
│   │   └── tools/              # Jira MCP tools (6 tools)
│   └── slack/                  # Slack connector
│       ├── client.py           # Slack API client
│       ├── config.py           # Slack config loader
│       └── tools/              # Slack MCP tools (10 tools)
├── config/                     # Configuration files
│   ├── jira.yaml              # Jira teams & organizations
│   └── slack.yaml             # Slack channels & user mappings
├── utils/                      # Shared utilities
│   ├── responses.py            # Response helpers
│   └── validators.py           # Input validation
├── slack_dumps_parsed/            # Parsed Slack dumps with real names
├── slack_dumps/               # Slack data cache
├── requirements.txt            # Python dependencies
├── Containerfile              # Container definition
├── example.mcp.json           # Cursor MCP configuration
├── example.env                # Environment variables template
├── Makefile                   # Build and setup commands
├── cleanup-containers.sh      # Container cleanup script
├── ARCHITECTURE_DIAGRAM.md    # Visual architecture diagrams
└── README.md                  # This file
```

## 🏗️ Architecture

### Modular Connector System

The project uses a clean, modular architecture where each service (Jira, Slack) has its own connector:

- **`connectors/jira/`** - Jira API integration with 6 MCP tools
- **`connectors/slack/`** - Slack API integration with 10 MCP tools
- **`config/`** - Service-specific configuration files
- **`utils/`** - Shared utilities and helpers

### Direct Import Pattern

The server uses a simple, direct import pattern:
```python
# server.py
from connectors.jira.tools import search_issues_tool, get_team_issues_tool, ...
from connectors.slack.tools import read_slack_channel_tool, search_slack_mentions_tool, ...
```

### Benefits of This Architecture
- **Modularity** - Each connector is self-contained
- **Maintainability** - Easy to locate and modify specific tools
- **Scalability** - Simple to add new connectors or tools
- **Clean Separation** - Clear separation of concerns
- **No Dead Code** - Removed unused auto-discovery and base classes

## 🔧 Configuration

### Teams Configuration

The server is configured for the following teams with their Jira `AssignedTeam` values:

- **ToolChain Team** (`rhivos-pdr-auto-toolchain`) - Core toolchain and infrastructure work
- **Assessment Team** (`rhivos-fusa-assessment`) - Assessment and validation work
- **FoA Team** (`rhivos-fusa-foa`) - Focus of Attention work
- **BoA Team** (`rhivos-pdr-base-os-automotive`) - Back of Attention work

### Organizations

- **SP Organization** - Strategic Planning team members across all teams

### User Mapping System

The system uses a consolidated user mapping approach:

1. **`config/slack.yaml`** - Single source of truth for all user mappings (57+ mappings)
2. **`config/jira.yaml`** - Jira-specific user mappings for team filtering

### Configuration Structure

The configuration files use a flexible approach:
- **Display Names**: Human-readable names like "Sameera Kalgudi" for easy configuration
- **Automatic Resolution**: System automatically maps display names to Jira usernames
- **Team Filtering**: Can filter by specific team members or show all team work
- **Organization Filtering**: Can filter by organization members within teams

## 🎯 How Configuration Enables Smart Filtering

> 📊 **For detailed visual diagrams and flow charts, see [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)**

### Team vs Organization Filtering

```
┌─────────────────────────────────────────────────────────────────┐
│                    Features Teams MCP Server                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Team Query    │    │ Organization    │    │   Result    │ │
│  │                 │    │   Filter        │    │             │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ toolchain       │    │ SP              │    │ SP members  │ │
│  │ (no org)        │    │                 │    │ only        │ │
│  │                 │    │                 │    │             │ │
│  │ → All team      │    │ → Team members  │    │ → Filtered  │ │
│  │   tickets       │    │   in SP org     │    │   tickets   │ │
│  │                 │    │                 │    │             │ │
│  │ → Uses          │    │ → Uses          │    │ → Shows     │ │
│  │   AssignedTeam  │    │   assignee      │    │   relevant  │ │
│  │   field        │    │   filtering     │    │   work       │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Example Queries                          │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │ • "Get toolchain tickets" → All team work                  │ │
│  │ • "Get toolchain tickets for SP" → SP members only         │ │
│  │ • "Get assessment tickets" → All assessment work           │ │
│  │ • "Get FoA tickets for SP" → FoA team + SP org filter      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🐳 Container Usage

### Build and Run

```bash
# Build the container
make build

# Run the container
make run
```

### Manual Container Commands

```bash
# Build
podman build -t localhost/features-teams:latest .
# Or use the Docker Hub image:
# docker.io/library/features-teams:latest

# Run
podman run -i --rm --env-file ~/.rh-features-teams.env localhost/features-teams:latest
# Or use the Docker Hub image:
# podman run -i --rm --env-file ~/.rh-features-teams.env docker.io/library/features-teams:latest
```

## 🎯 MCP Tools Usage

### Jira Tools

#### search_issues
```json
{
  "jql": "project = 'Automotive Feature Teams' AND 'AssignedTeam' = 'rhivos-pdr-auto-toolchain'",
  "max_results": 20
}
```

#### get_team_issues
```json
{
  "team": "toolchain",
  "status": "In Progress",
  "organization": "SP"
}
```

#### Smart Filtering Examples

**Get all toolchain tickets (no organization filter):**
```json
{
  "team": "toolchain",
  "status": "In Progress"
}
```
*Result: All tickets assigned to the toolchain team using `AssignedTeam = "rhivos-pdr-auto-toolchain"`*

**Get toolchain tickets for SP organization only:**
```json
{
  "team": "toolchain",
  "status": "In Progress",
  "organization": "SP"
}
```
*Result: Only tickets assigned to toolchain team members who are also in the SP organization*

### Slack Tools

#### read_team_slack_data
```json
{
  "team": "toolchain",
  "max_age_hours": 24
}
```

#### search_slack_mentions
```json
{
  "channel_id": "C04U16VAWL9",
  "search_term": "deployment",
  "max_age_hours": 24
}
```

#### search_team_slack_mentions
```json
{
  "team": "toolchain",
  "search_term": "bug",
  "max_age_hours": 24
}
```

## 💬 Slack Integration

### Overview
The MCP server includes comprehensive Slack integration to read team channel discussions and correlate them with Jira tickets for comprehensive team insights.

### Configuration
1. **Set up Slack tokens** in your `.env` file:
   ```bash
   cp example.env .env
   # Edit .env with your actual Slack tokens
   ```

2. **Configure channel mappings** in `config/slack.yaml`:
   ```yaml
   slack_channels:
     "C04U16VAWL9": "toolchain"  # #toolchain-release-readiness
     "C05BYR06B0V": "toolchain"  # #toolchain-infra
     "C064MPL86N6": "toolchain"  # #toolchain-errata
     "C0910QFKTSN": "toolchain"  # #toolchain-AI
     "C095CUUBNM9": "toolchain"  # #toolchain-sla
   ```

### Slack Tools Features

#### Automatic Data Management
- **Smart Caching**: Automatically checks if Slack data is fresh (default: 24 hours)
- **Auto-Dump**: Creates fresh dumps when data is stale
- **Seamless Reading**: Always returns the latest data without manual intervention

#### User Mapping Integration
- **Consolidated Mappings**: Uses `config/slack.yaml` as single source of truth for user identification
- **Search Enhancement**: Search tools can find mentions by both display names and user IDs
- **Consistent Identification**: Same user mappings used across Jira and Slack tools

### Usage Examples

```bash
# Read team Slack data (auto-refreshes if needed)
"read toolchain team slack data"

# Read specific channel
"read slack channel C04U16VAWL9"

# Force fresh data for analysis
"force fresh slack dump for toolchain team"

# Search for mentions across team channels
"search for 'deployment' mentions in toolchain team"

# Check what dumps are available
"list slack dumps for toolchain team"

# Get summary of team data
"get slack dump summary for toolchain team"
```

### Data Flow
1. **User Request**: "Get toolchain team comprehensive status"
2. **Auto-Check**: System checks if Slack data is fresh
3. **Auto-Dump**: If stale, automatically fetches latest Slack data
4. **Data Reading**: Reads the fresh Slack dump files
5. **LLM Analysis**: Raw Slack data is provided to LLM for analysis
6. **Combined Results**: Jira tickets + Slack discussions in unified response

### Benefits
- ✅ **Always Fresh Data**: Automatic refresh ensures latest information
- ✅ **Zero Maintenance**: No manual dump management required
- ✅ **LLM-Ready**: Raw text data perfect for AI analysis
- ✅ **Team Context**: Correlate Jira work with Slack discussions
- ✅ **Comprehensive View**: Combine structured (Jira) and unstructured (Slack) data
- ✅ **User Identification**: Consistent user mapping across all tools

## 🛠️ Development

### Local Testing

```bash
# Test the server locally
make test
```

### Available Commands

```bash
make build          # Build the container
make run            # Run the container
make clean          # Clean up container and cache
make test           # Test server locally
make cursor-config  # Setup Cursor MCP configuration
make setup          # Setup environment file
make help           # Show available commands
```

## 📋 Environment Variables

Create `~/.rh-features-teams.env` with:

```bash
# Required Jira Configuration
JIRA_URL=https://issues.redhat.com
JIRA_API_TOKEN=your_jira_api_token_here

# Required Slack Configuration
SLACK_XOXC_TOKEN=xoxc-your-slack-web-token-here
SLACK_XOXD_TOKEN=xoxd-your-slack-cookie-token-here
LOGS_CHANNEL_ID=C0000000000
```

## 🔄 Display Name Resolution System

### How It Works

The system automatically converts human-readable engineer names to Jira usernames for queries and back to display names for results:

```yaml
# User display names mapping: Engineer Name -> Jira Username
user_display_names:
  "Sameera Kalgudi": "rhn-support-skalgudi"    # Engineer Name → Jira Username
  "Ozan Unsal": "rhn-support-ounsal"           # Engineer Name → Jira Username
  "Marcel Banas": "mabanas@redhat.com"         # Engineer Name → Jira Username
  "Nisha Saini": "rhn-support-nsaini"          # Engineer Name → Jira Username
  "Ryan Smith": "rsmit106"                     # Engineer Name → Jira Username
  "Jan Onderka": "jonderka@redhat.com"         # Engineer Name → Jira Username
  "Joe Simmons-Talbott": "rhn-support-josimmon" # Engineer Name → Jira Username

# Configuration (human-readable)
teams:
  toolchain:
    members:
      - "Sameera Kalgudi"      # Display name
      - "Ozan Unsal"           # Display name
      - "Marcel Banas"         # Display name
```

**Benefits:**
- ✅ **Easy Configuration**: Use familiar engineer names instead of cryptic Jira usernames
- ✅ **Bidirectional Mapping**: Engineer names → Jira usernames for queries, Jira usernames → Engineer names for display
- ✅ **Case-Insensitive**: "sameera kalgudi" works the same as "Sameera Kalgudi"
- ✅ **Automatic Resolution**: System handles username conversion transparently
- ✅ **Flexible Queries**: Can filter by team, organization, or both
- ✅ **Maintainable**: Update engineer names without changing Jira usernames
- ✅ **Consistent**: Same mappings used across Jira and Slack tools

## 🚫 No Direct Scripts

**This project is designed to work exclusively through MCP tools:**

- ❌ **No direct Python scripts** for querying Jira or Slack
- ❌ **No manual API calls** outside of MCP protocol
- ❌ **No development/testing scripts** in production
- ✅ **All queries go through MCP tools** automatically
- ✅ **Clean, minimal container** with only essential files
- ✅ **Cursor AI integration** for seamless tool usage

## 🚀 Current System Capabilities

### ✅ What's Working

- **Team Queries**: Get all tickets for any configured team
- **Organization Filtering**: Filter team tickets by organization membership
- **Display Name Resolution**: Automatic mapping of human names to Jira usernames
- **Proper Jira Integration**: Uses correct `AssignedTeam` field values
- **Comprehensive Coverage**: Finds all team tickets regardless of assignment method
- **Slack Integration**: Read and search team Slack discussions
- **User Mapping**: Consistent user identification across Jira and Slack
- **Auto-Caching**: Smart Slack data management with automatic refresh

### 🎯 Example Results

**Toolchain Team (No Organization Filter):**
- 20+ tickets in progress
- 13+ team members discovered
- Infrastructure, toolchain, and product pipeline work
- Uses `AssignedTeam = "rhivos-pdr-auto-toolchain"`

**Toolchain Team + SP Organization Filter:**
- Only tickets assigned to SP organization members
- Focused view of strategic planning work
- Uses assignee filtering with resolved usernames

**Slack Integration:**
- Automatic data refresh for team channels
- Search capabilities across all team discussions
- User identification using consolidated mappings
- LLM-ready raw text data for analysis

### 🔧 Technical Features

- **Containerized**: Runs in Podman/Docker for consistency
- **MCP Protocol**: Full Model Context Protocol compliance
- **Error Handling**: Graceful fallbacks and comprehensive error messages
- **Caching**: User display name caching for performance
- **Flexible Queries**: Supports both team-based and assignee-based filtering
- **Modular Architecture**: Clean separation between Jira and Slack connectors
- **Consolidated Configuration**: Single source of truth for user mappings

## 📊 Quick Visual Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    Features Teams MCP Server                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Jira Tools    │    │  Slack Tools    │    │   Built-in  │ │
│  │   (6 tools)     │    │   (10 tools)    │    │   (1 tool)  │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • search_issues │    │ • read_slack_   │    │ • list_     │ │
│  │ • get_team_     │    │   channel       │    │   available_│ │
│  │   issues        │    │ • search_slack_ │    │   tools     │ │
│  │ • get_project_  │    │   mentions      │    │             │ │
│  │   info          │    │ • dump_slack_   │    │             │ │
│  │ • get_user_info │    │   channel       │    │             │ │
│  │ • list_teams    │    │ • force_fresh_  │    │             │ │
│  │ • list_orgs     │    │   slack_dump    │    │             │ │
│  │                 │    │ • [4 more...]   │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
│  📊 For detailed diagrams: ARCHITECTURE_DIAGRAM.md             │
└─────────────────────────────────────────────────────────────────┘
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.