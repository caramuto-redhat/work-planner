# Work Planner MCP Server

A comprehensive Model Context Protocol (MCP) server for querying Jira issues, Slack discussions, AI-powered analysis, and scheduled data collection. This server provides 21 MCP tools for comprehensive team insights through Cursor's AI assistant.

**🎯 This project is designed to work ONLY through MCP tools - no direct scripts or manual queries.**

## 🎯 Features

### MCP Tools Available (21 total)

#### Jira Tools (6 tools)
1. **`search_issues`** - Search Jira issues using JQL queries
2. **`get_team_issues`** - Get issues for specific teams with optional organization filtering
3. **`get_project_info`** - Get basic project information
4. **`get_user_info`** - Get user information
5. **`list_teams`** - List all configured teams
6. **`list_organizations`** - List all configured organizations

#### Slack Tools (5 tools)
7. **`dump_slack_data`** - Dump Slack data for channels or teams
8. **`read_slack_data`** - Read Slack data (auto-refreshes if needed)
9. **`search_slack_data`** - Search for mentions in Slack channels
10. **`list_slack_channels`** - List all Slack channels
11. **`list_slack_dumps`** - List available Slack dump files

#### AI Analysis Tools (4 tools)
12. **`analyze_slack_data`** - Analyze Slack data using Gemini AI
13. **`analyze_jira_data`** - Analyze Jira data using Gemini AI
14. **`generate_email_summary`** - Generate email summary combining Slack and Jira data
15. **`custom_ai_analysis`** - Perform custom AI analysis with custom prompts

#### Schedule Management Tools (5 tools)
16. **`get_schedule_status`** - Get current status of scheduled data collection
17. **`run_scheduled_collection`** - Run scheduled data collection for services
18. **`update_schedule_config`** - Update schedule configuration
19. **`add_team_to_schedule`** - Add team to schedule configuration
20. **`remove_team_from_schedule`** - Remove team from schedule configuration

#### Built-in Tools (1 tool)
21. **`list_available_tools`** - List all available MCP tools

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create environment file with your credentials
make setup
# Edit ~/.rh-work-planner.env with your Jira URL, API token, and Slack tokens
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

**💡 Note**: If you already have a working MCP configuration (like `workPlannerMcp`), you may not need to run this command unless you want to reset to the default configuration.

### 4. Use in Cursor

The MCP server will be available in Cursor as `workPlannerMcp`. You can now ask the AI assistant to:

- "Get me toolchain tickets in progress"
- "Show me issues assigned to the SP team"
- "Search for critical VROOM tickets"
- "Read toolchain team Slack discussions"
- "Search for mentions of 'deployment' in Slack"
- "Analyze toolchain team Slack data"
- "Generate email summary for assessment team"
- "Check schedule status"
- "List all available teams"

**✅ All queries go through MCP tools automatically**

## 📁 Project Structure

```
work-planner/
├── server.py                    # Main MCP server (direct imports)
├── connectors/                  # Modular connector system
│   ├── jira/                   # Jira connector
│   │   ├── client.py           # Jira API client
│   │   ├── config.py           # Jira config loader
│   │   └── tools/              # Jira MCP tools (6 tools)
│   ├── slack/                  # Slack connector
│   │   ├── client.py           # Slack API client
│   │   ├── config.py           # Slack config loader
│   │   ├── tools/              # Slack MCP tools (5 tools)
│   │   └── slack_dump/         # Slack data organization
│   │       ├── slack_dumps/    # Raw Slack data cache
│   │       └── slack_dumps_parsed/ # Parsed Slack dumps with real names
│   ├── gemini/                 # Gemini AI connector
│   │   ├── client.py           # Gemini API client
│   │   ├── config.py           # Gemini config loader
│   │   └── tools/              # AI analysis tools (4 tools)
│   └── schedule/               # Schedule management connector
│       ├── config.py           # Schedule config loader
│       └── tools/              # Schedule tools (5 tools)
├── config/                     # Configuration files
│   ├── jira.yaml              # Jira teams & organizations
│   ├── slack.yaml             # Slack channels & user mappings
│   ├── gemini.yaml            # Gemini AI configuration
│   └── schedule.yaml          # Schedule configuration
├── utils/                      # Shared utilities
│   ├── responses.py            # Response helpers
│   └── validators.py           # Input validation
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

The project uses a clean, modular architecture where each service has its own connector:

- **`connectors/jira/`** - Jira API integration with 6 MCP tools
- **`connectors/slack/`** - Slack API integration with 5 MCP tools
- **`connectors/gemini/`** - AI analysis integration with 4 MCP tools
- **`connectors/schedule/`** - Schedule management with 5 MCP tools
- **`config/`** - Service-specific configuration files
- **`utils/`** - Shared utilities and helpers

### Direct Import Pattern

The server uses a simple, direct import pattern:
```python
# server.py
from connectors.jira.tools import search_issues_tool, get_team_issues_tool, ...
from connectors.slack.tools import read_slack_data_tool, search_slack_data_tool, ...
from connectors.gemini.tools import analyze_slack_data_tool, generate_email_summary_tool, ...
from connectors.schedule.tools import get_schedule_status_tool, run_scheduled_collection_tool, ...
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

1. **`config/slack.yaml`** - Single source of truth for all user mappings (150+ mappings)
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
│                    Work Planner MCP Server                    │
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
podman build -t localhost/work-planner:latest .

# Run from different registries
# Local build:
podman run -i --rm --env-file ~/.rh-work-planner.env localhost/work-planner:latest

# GitHub Container Registry:
podman run -i --rm --env-file ~/.rh-work-planner.env ghcr.io/caramuto-redhat/work-planner:latest

# Quay.io:
podman run -i --rm --env-file ~/.rh-work-planner.env quay.io/rhn-support-pacaramu/work-planner:latest
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

### Slack Tools

#### read_slack_data
```json
{
  "target": "toolchain",
  "max_age_hours": 24
}
```

#### search_slack_data
```json
{
  "target": "toolchain",
  "search_term": "deployment",
  "max_age_hours": 24
}
```

### AI Analysis Tools

#### analyze_slack_data
```json
{
  "team": "toolchain",
  "analysis_type": "summary"
}
```

#### generate_email_summary
```json
{
  "team": "toolchain"
}
```

### Schedule Management Tools

#### get_schedule_status
```json
{}
```

#### run_scheduled_collection
```json
{
  "service": "slack",
  "team": "toolchain"
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
"dump fresh slack data for toolchain team"

# Search for mentions across team channels
"search for 'deployment' mentions in toolchain team"

# Check what dumps are available
"list slack dumps for toolchain team"
```

## 🤖 AI Analysis Integration

### Overview
The MCP server includes Gemini AI integration for intelligent analysis of Slack and Jira data, enabling automated insights and email summaries.

### Features
- **Slack Analysis**: Summarize discussions, extract action items, identify blockers
- **Jira Analysis**: Project status reports, progress tracking, issue analysis
- **Email Summaries**: Professional daily/weekly team summaries
- **Custom Analysis**: Flexible AI analysis with custom prompts

### Configuration
Configure Gemini AI settings in `config/gemini.yaml`:
```yaml
model: "models/gemini-2.0-flash"
generation_config:
  temperature: 0.7
  max_output_tokens: 2048
```

### Usage Examples

```bash
# Analyze team Slack discussions
"analyze toolchain team slack data"

# Generate project status from Jira
"analyze assessment team jira data"

# Create email summary
"generate email summary for toolchain team"

# Custom analysis
"perform custom AI analysis with prompt: 'What are the main themes in this data?'"
```

## 📅 Schedule Management

### Overview
The MCP server includes comprehensive schedule management for automated data collection and analysis.

### Features
- **Automated Data Collection**: Scheduled Slack and Jira data collection
- **AI Analysis Scheduling**: Automated AI analysis and email generation
- **Team Management**: Add/remove teams from scheduled services
- **Configuration Management**: Update schedule settings dynamically

### Configuration
Configure schedules in `config/schedule.yaml`:
```yaml
slack:
  enabled: true
  schedule: "0 6 * * *"  # Daily at 6 AM UTC
  teams:
    - name: "toolchain"
      channels: "all"
      max_age_hours: 24
```

### Usage Examples

```bash
# Check schedule status
"get schedule status"

# Run data collection
"run scheduled collection for slack"

# Update schedule configuration
"update schedule config for slack team toolchain max_age_hours to 12"

# Add team to schedule
"add team to schedule for slack team assessment"
```

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
make run-quay       # Run using Quay.io image
make clean          # Clean up container and cache
make test           # Test server locally
make cursor-config  # Setup Cursor MCP configuration
make setup          # Setup environment file
make help           # Show available commands
```

### Deploy to Quay.io

```bash
# Set your Quay.io credentials
export QUAY_USERNAME=your-quay-username
export QUAY_TOKEN=your-quay-token

# Deploy to Quay.io
./deploy-quay.sh
```

## 📋 Environment Variables

### Local Development

Create `~/.rh-work-planner.env` with:

```bash
# Required Jira Configuration
JIRA_URL=https://issues.redhat.com
JIRA_API_TOKEN=your_jira_api_token_here

# Required Slack Configuration
SLACK_XOXC_TOKEN=xoxc-your-slack-web-token-here
SLACK_XOXD_TOKEN=xoxd-your-slack-cookie-token-here
LOGS_CHANNEL_ID=C0000000000

# Optional Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
```

### GitHub Secrets (Recommended for Production)

For production deployments and CI/CD, use GitHub repository secrets:

1. **Go to Repository Settings** → **Secrets and variables** → **Actions**
2. **Add these secrets:**
   - `JIRA_URL` = `https://issues.redhat.com`
   - `JIRA_API_TOKEN` = `your_actual_jira_api_token`
   - `SLACK_XOXC_TOKEN` = `your_actual_slack_xoxc_token`
   - `SLACK_XOXD_TOKEN` = `your_actual_slack_xoxd_token`
   - `LOGS_CHANNEL_ID` = `your_actual_logs_channel_id`
   - `GEMINI_API_KEY` = `your_actual_gemini_api_key`

The application automatically uses GitHub secrets when available, falling back to local environment variables.

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
- **AI Analysis**: Intelligent analysis of Slack and Jira data
- **Schedule Management**: Automated data collection and analysis
- **Email Summaries**: Professional team communication

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

**AI Analysis:**
- Intelligent summarization of team discussions
- Project status analysis from Jira data
- Professional email summaries
- Custom analysis capabilities

**Schedule Management:**
- Automated data collection
- Configurable team schedules
- Dynamic configuration updates
- Service status monitoring

### 🔧 Technical Features

- **Containerized**: Runs in Podman/Docker for consistency
- **MCP Protocol**: Full Model Context Protocol compliance
- **Error Handling**: Graceful fallbacks and comprehensive error messages
- **Caching**: User display name caching for performance
- **Flexible Queries**: Supports both team-based and assignee-based filtering
- **Modular Architecture**: Clean separation between connectors
- **Consolidated Configuration**: Single source of truth for user mappings
- **AI Integration**: Gemini AI for intelligent analysis
- **Schedule Management**: Automated data collection and processing

## 📊 Quick Visual Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    Work Planner MCP Server                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │   Jira Tools    │    │  Slack Tools    │    │   AI Tools   │ │
│  │   (6 tools)     │    │   (5 tools)     │    │   (4 tools)  │ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • search_issues │    │ • dump_slack_   │    │ • analyze_  │ │
│  │ • get_team_     │    │   data          │    │   slack_data│ │
│  │   issues        │    │ • read_slack_   │    │ • analyze_  │ │
│  │ • get_project_  │    │   data          │    │   jira_data │ │
│  │   info          │    │ • search_slack_  │    │ • generate_ │ │
│  │ • get_user_info │    │   data          │    │   email_    │ │
│  │ • list_teams    │    │ • list_slack_   │    │   summary   │ │
│  │ • list_orgs     │    │   channels       │    │ • custom_ai_│ │
│  │                 │    │ • list_slack_    │    │   analysis  │ │
│  │                 │    │   dumps          │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ Schedule Tools   │    │   Built-in      │    │   Total     │ │
│  │   (5 tools)      │    │   (1 tool)      │    │   (21 tools)│ │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────┤ │
│  │ • get_schedule_  │    │ • list_         │    │             │ │
│  │   status         │    │   available_    │    │             │ │
│  │ • run_scheduled_ │    │   tools         │    │             │ │
│  │   collection     │    │                 │    │             │ │
│  │ • update_       │    │                 │    │             │ │
│  │   schedule_     │    │                 │    │             │ │
│  │   config         │    │                 │    │             │ │
│  │ • add_team_to_  │    │                 │    │             │ │
│  │   schedule       │    │                 │    │             │ │
│  │ • remove_team_   │    │                 │    │             │ │
│  │   from_schedule  │    │                 │    │             │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                                                                 │
│  📊 For detailed diagrams: ARCHITECTURE_DIAGRAM.md             │
└─────────────────────────────────────────────────────────────────┘
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.