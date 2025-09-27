#!/bin/bash
# Build and push to Quay.io for corporate VPN access

set -e

echo "🔨 Building Features Teams MCP Server for Quay.io..."

# Build the container
echo "Building container image..."
podman build -t quay.io/caramuto-redhat/features-teams:latest .

# Login to Quay.io
echo "Logging into Quay.io..."
source ~/.rh-features-teams.env
echo $QUAY_TOKEN | podman login quay.io -u caramuto-redhat --password-stdin

# Push to Quay.io
echo "Pushing to Quay.io..."
podman push quay.io/caramuto-redhat/features-teams:latest

echo "✅ Container pushed to Quay.io successfully!"
echo "📍 Image: quay.io/caramuto-redhat/features-teams:latest"
echo "🔧 MCP configuration updated to use Quay.io"
