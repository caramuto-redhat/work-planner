#!/bin/bash

# Work Planner MCP Server Wrapper
# This script handles proper container lifecycle management

set -e

# Configuration
CONTAINER_NAME="work-planner-container"
IMAGE_NAME="localhost/work-planner:latest"
ENV_FILE="/Users/pacaramu/.rh-work-planner.env"

# Function to cleanup container
cleanup() {
    echo "🧹 Cleaning up container..."
    podman stop "$CONTAINER_NAME" 2>/dev/null || true
    podman rm "$CONTAINER_NAME" 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM EXIT

# Check if container is already running
if podman ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "⚠️  Container $CONTAINER_NAME is already running"
    echo "🔄 Stopping existing container..."
    podman stop "$CONTAINER_NAME"
    podman rm "$CONTAINER_NAME"
fi

# Start the container
echo "🚀 Starting Work Planner MCP Server..."
podman run -i --rm --name "$CONTAINER_NAME" \
    --env-file "$ENV_FILE" \
    -v "/Users/pacaramu/Documents/Git/work-planner/connectors/slack/slack_dump/slack_dumps:/app/connectors/slack/slack_dump/slack_dumps" \
    -v "/Users/pacaramu/Documents/Git/work-planner/connectors/slack/slack_dump/slack_dumps_parsed:/app/connectors/slack/slack_dump/slack_dumps_parsed" \
    "$IMAGE_NAME"
