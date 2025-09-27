#!/bin/bash

echo "🧹 Cleaning up Features Teams MCP containers..."

# Stop and remove any running containers
podman ps -q --filter "ancestor=localhost/features-teams:latest" | xargs -r podman stop
podman ps -q --filter "ancestor=localhost/features-teams:latest" | xargs -r podman rm

# Remove any stopped containers
podman ps -aq --filter "ancestor=localhost/features-teams:latest" | xargs -r podman rm

# Also clean up any containers with features-teams in the name
podman ps -aq --filter "name=features-teams" | xargs -r podman stop
podman ps -aq --filter "name=features-teams" | xargs -r podman rm

echo "✅ Cleanup complete!" 