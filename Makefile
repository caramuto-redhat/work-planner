# Jira MCP Server Makefile
# Clean, minimal version for production MCP server only
# All queries go through MCP tools - no direct scripts

.PHONY: build run clean cursor-config setup help

# Environment file path
ENV_FILE = ~/.rh-jira-mcp-features-master-web.env

# Build the container
build:
	@echo "🔨 Building Jira MCP Server container..."
	@podman build -t localhost/jira-mcp-features-master-web:latest .
	@echo "💡 Using local build. Docker Hub image available: docker.io/library/jira-mcp-features-master-web:latest"

# Run the container
run:
	@echo "🚀 Running Jira MCP Server container..."
	@podman run -i --rm --env-file $(ENV_FILE) localhost/jira-mcp-features-master-web:latest

# Run using Docker Hub image
run-dockerhub:
	@echo "🚀 Running Jira MCP Server from Docker Hub..."
	@podman run -i --rm --env-file $(ENV_FILE) docker.io/library/jira-mcp-features-master-web:latest

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@podman rmi localhost/jira-mcp-features-master-web:latest 2>/dev/null || true
	@rm -rf __pycache__
	@rm -f *.pyc
	@rm -rf venv

# Setup cursor configuration
cursor-config:
	@echo "📝 Setting up Cursor MCP configuration..."
	@cp example.mcp.json ~/.cursor/mcp.json
	@echo "✅ Cursor MCP configuration copied to ~/.cursor/mcp.json"
	@echo "🔄 Restart Cursor to load the MCP server"

# Setup environment
setup:
	@echo "🔧 Setting up environment..."
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "📝 Creating environment file at $(ENV_FILE)"; \
		cp example.env $(ENV_FILE); \
		echo "⚠️  Please edit $(ENV_FILE) with your Jira credentials"; \
	else \
		echo "✅ Environment file already exists at $(ENV_FILE)"; \
	fi

# Help
help:
	@echo "Available commands:"
	@echo "  build        - Build the container"
	@echo "  run          - Run the container"
	@echo "  run-dockerhub - Run using Docker Hub image"
	@echo "  clean        - Clean up container and cache"
	@echo "  cursor-config - Setup Cursor MCP configuration"
	@echo "  setup        - Setup environment file"
	@echo "  help         - Show this help"
	@echo ""
	@echo "🎯 This project works ONLY through MCP tools in Cursor"
	@echo "   No direct scripts or manual queries needed"
