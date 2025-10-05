#!/bin/bash

echo "🧹 Cleaning up Work Planner MCP containers..."

# Stop and remove any running containers
podman ps -q --filter "ancestor=localhost/work-planner:latest" | xargs -r podman stop
podman ps -q --filter "ancestor=localhost/work-planner:latest" | xargs -r podman rm

# Remove any stopped containers
podman ps -aq --filter "ancestor=localhost/work-planner:latest" | xargs -r podman rm

# Also clean up any containers with work-planner in the name
podman ps -aq --filter "name=work-planner" | xargs -r podman stop
podman ps -aq --filter "name=work-planner" | xargs -r podman rm

echo "✅ Cleanup complete!" 