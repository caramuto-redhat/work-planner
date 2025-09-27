#!/bin/bash

echo "🚀 Deploying Work Planner to Quay.io..."

# Check if required environment variables are set
if [ -z "$QUAY_USERNAME" ] || [ -z "$QUAY_TOKEN" ]; then
    echo "❌ Error: QUAY_USERNAME and QUAY_TOKEN environment variables must be set"
    echo "   Set them with:"
    echo "   export QUAY_USERNAME=your-quay-username"
    echo "   export QUAY_TOKEN=your-quay-token"
    exit 1
fi

# Build the container
echo "🔨 Building container..."
podman build -t quay.io/rhn-support-pacaramu/work-planner:latest .

# Login to Quay.io
echo "🔐 Logging in to Quay.io..."
echo "$QUAY_TOKEN" | podman login quay.io -u "$QUAY_USERNAME" --password-stdin

# Push to Quay.io
echo "📤 Pushing to Quay.io..."
podman push quay.io/rhn-support-pacaramu/work-planner:latest

echo "✅ Successfully deployed to Quay.io!"
echo "   Image: quay.io/rhn-support-pacaramu/work-planner:latest"
echo ""
echo "🚀 You can now run it with:"
echo "   make run-quay"
echo "   or"
echo "   podman run -i --rm --env-file ~/.rh-work-planner.env quay.io/rhn-support-pacaramu/work-planner:latest"
