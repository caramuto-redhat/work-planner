# Container Directory

This directory contains all container and deployment-related files for the Work Planner MCP Server.

## Files

### `Containerfile`
- **Purpose**: Container definition for building the MCP server image
- **Usage**: Used by GitHub Actions to build and push container images
- **Base**: Python 3.11 slim image

### `run-mcp-server.sh`
- **Purpose**: Script to run the MCP server locally
- **Usage**: `./run-mcp-server.sh`
- **Features**: Sets up environment, installs dependencies, runs server

### `cleanup-containers.sh`
- **Purpose**: Clean up local Docker containers and images
- **Usage**: `./cleanup-containers.sh`
- **Features**: Removes containers, images, and cleans up Docker cache

### `example.env`
- **Purpose**: Template for environment variables
- **Usage**: Copy to `.env` and fill in your values
- **Contains**: All required environment variables with examples

### `example.mcp.json`
- **Purpose**: Example MCP configuration for Cursor
- **Usage**: Copy to your Cursor MCP configuration
- **Contains**: Sample configuration for connecting to the MCP server

### `local.mcp.json`
- **Purpose**: Local MCP configuration for development
- **Usage**: Used for local testing and development
- **Contains**: Local server configuration

## Usage

### Local Development
```bash
# Copy environment template
cp example.env .env
# Edit .env with your values

# Run the server
./run-mcp-server.sh
```

### Container Building
```bash
# Build container
docker build -f Containerfile -t work-planner-mcp .

# Run container
docker run -p 8000:8000 work-planner-mcp
```

### Cleanup
```bash
# Clean up Docker resources
./cleanup-containers.sh
```

## Environment Variables

See `example.env` for all required environment variables:

- **Slack**: `SLACK_XOXC_TOKEN`, `SLACK_XOXD_TOKEN`
- **Jira**: `JIRA_URL`, `JIRA_API_TOKEN`
- **AI**: `GEMINI_API_KEY`
- **Email**: `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_FROM`

## MCP Configuration

See `example.mcp.json` for Cursor MCP configuration:

```json
{
  "mcpServers": {
    "work-planner": {
      "command": "python",
      "args": ["server.py"],
      "env": {
        "SLACK_XOXC_TOKEN": "your_token",
        "JIRA_URL": "your_jira_url"
      }
    }
  }
}
```
