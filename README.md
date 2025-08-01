# Jira MCP Server

A clean, minimal Model Context Protocol (MCP) server for querying Jira issues. This server provides 6 MCP tools for interacting with Jira through Cursor's AI assistant.

**🎯 This project is designed to work ONLY through MCP tools - no direct scripts or manual queries.**

## 🎯 Features

### MCP Tools Available

1. **`search_issues`** - Search Jira issues using JQL queries
2. **`get_team_issues`** - Get issues for specific teams with optional organization filtering
3. **`get_project_info`** - Get basic project information
4. **`get_user_info`** - Get user information
5. **`list_teams`** - List all configured teams
6. **`list_organizations`** - List all configured organizations

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create environment file with your Jira credentials
make setup
# Edit ~/.rh-jira-mcp-features-master-web.env with your Jira URL and API token
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

**💡 Note**: If you already have a working MCP configuration (like `jiraMCP2`), you may not need to run this command unless you want to reset to the default configuration.

### 4. Use in Cursor

The MCP server will be available in Cursor as `jiraMcp`. You can now ask the AI assistant to:

- "Get me toolchain tickets in progress"
- "Show me issues assigned to the SP team"
- "Search for critical VROOM tickets"
- "List all available teams"

**✅ All queries go through MCP tools automatically**

## 📁 Project Structure

```
jira-mcp-features-master-web/
├── server.py              # Main MCP server with 6 tools
├── jira-config.yaml       # Team and organization configurations
├── requirements.txt        # Python dependencies
├── Containerfile          # Container definition
├── example.mcp.json       # Cursor MCP configuration
├── example.env            # Environment variables template
├── Makefile               # Build and setup commands
└── README.md              # This file
```

## 🔧 Configuration

### Teams Configuration

The server is configured for the following teams:

- **ToolChain Team** (`rhivos-ft-auto-toolchain`)
- **Assessment Team** (`rhivos-ft-auto-assessment`)
- **FoA Team** (`rhivos-ft-auto-foa`)
- **BoA Team** (`rhivos-ft-auto-boa`)

### Organizations

- **SP Organization** - Includes all team members

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
podman build -t localhost/jira-mcp-features-master-web:latest .
# Or use the Docker Hub image:
# docker.io/library/jira-mcp-features-master-web:latest

# Run
podman run -i --rm --env-file ~/.rh-jira-mcp-features-master-web.env localhost/jira-mcp-features-master-web:latest
# Or use the Docker Hub image:
# podman run -i --rm --env-file ~/.rh-jira-mcp-features-master-web.env docker.io/library/jira-mcp-features-master-web:latest
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
make clean          # Clean up container and cache
make test           # Test server locally
make cursor-config  # Setup Cursor MCP configuration
make setup          # Setup environment file
make help           # Show available commands
```

## 📋 Environment Variables

Create `~/.rh-jira-mcp-features-master-web.env` with:

```bash
JIRA_URL=https://your-jira-instance.atlassian.net
JIRA_API_TOKEN=your-jira-api-token
```

## 🎯 MCP Tools Usage

### search_issues
```json
{
  "jql": "project = 'Automotive Feature Teams' AND 'AssignedTeam' = 'rhivos-ft-auto-toolchain'",
  "max_results": 20
}
```

### get_team_issues
```json
{
  "team": "toolchain",
  "status": "In Progress",
  "organization": "SP"
}
```

### get_project_info
```json
{
  "project_key": "VROOM"
}
```

### get_user_info
```json
{
  "username": "rhn-support-skalgudi"
}
```

## 🚫 No Direct Scripts

**This project is designed to work exclusively through MCP tools:**

- ❌ **No direct Python scripts** for querying Jira
- ❌ **No manual API calls** outside of MCP protocol
- ❌ **No development/testing scripts** in production
- ✅ **All queries go through MCP tools** automatically
- ✅ **Clean, minimal container** with only essential files
- ✅ **Cursor AI integration** for seamless tool usage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 