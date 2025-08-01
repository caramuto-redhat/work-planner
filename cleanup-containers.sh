#!/bin/bash

echo "🧹 Cleaning up Jira MCP containers..."

# Stop and remove any running containers
podman ps -q --filter "ancestor=docker.io/library/jira-mcp-features-master-web:latest" | xargs -r podman stop
podman ps -q --filter "ancestor=docker.io/library/jira-mcp-features-master-web:latest" | xargs -r podman rm

# Remove any stopped containers
podman ps -aq --filter "ancestor=docker.io/library/jira-mcp-features-master-web:latest" | xargs -r podman rm

# Also clean up any containers with jira-mcp in the name
podman ps -aq --filter "name=jira-mcp" | xargs -r podman stop
podman ps -aq --filter "name=jira-mcp" | xargs -r podman rm

echo "✅ Cleanup complete!" 