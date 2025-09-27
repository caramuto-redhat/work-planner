# Deployment Guide

This guide covers different deployment options for the Work Planner MCP Server.

## 🚀 GitHub Secrets Setup

### Step 1: Add Repository Secrets

1. **Go to your repository:** https://github.com/caramuto-redhat/work-planner
2. **Click "Settings"** tab
3. **Click "Secrets and variables"** → **"Actions"**
4. **Click "New repository secret"** for each secret:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `JIRA_URL` | `https://issues.redhat.com` | Jira instance URL |
| `JIRA_API_TOKEN` | `your_actual_token` | Your Jira API token |
| `SLACK_XOXC_TOKEN` | `your_actual_token` | Slack web API token |
| `SLACK_XOXD_TOKEN` | `your_actual_token` | Slack cookie token |
| `LOGS_CHANNEL_ID` | `C0000000000` | Slack channel for logs |

### Step 2: Verify Secrets

After adding all secrets, you should see them listed in the "Repository secrets" section.

## 🐳 Container Deployment

### Using GitHub Actions

The repository includes a GitHub Actions workflow that automatically:
- Tests the application with GitHub secrets
- Builds the container
- Pushes to both GitHub Container Registry and Quay.io
- Deploys to your preferred platform

### Manual Container Build

```bash
# Clone the repository
git clone https://github.com/caramuto-redhat/work-planner.git
cd work-planner

# Build the container
make build

# Run with GitHub secrets (if available)
docker run -i --rm \
  -e JIRA_URL="$JIRA_URL" \
  -e JIRA_API_TOKEN="$JIRA_API_TOKEN" \
  -e SLACK_XOXC_TOKEN="$SLACK_XOXC_TOKEN" \
  -e SLACK_XOXD_TOKEN="$SLACK_XOXD_TOKEN" \
  -e LOGS_CHANNEL_ID="$LOGS_CHANNEL_ID" \
  work-planner:latest
```

### Deploy to Quay.io

```bash
# Set your Quay.io credentials
export QUAY_USERNAME=your-quay-username
export QUAY_TOKEN=your-quay-token

# Deploy using the provided script
./deploy-quay.sh

# Or manually:
podman build -t quay.io/rhn-support-pacaramu/work-planner:latest .
echo "$QUAY_TOKEN" | podman login quay.io -u "$QUAY_USERNAME" --password-stdin
podman push quay.io/rhn-support-pacaramu/work-planner:latest
```

## 🔧 Local Development

### Option 1: Using .env file

```bash
# Copy example environment file
cp example.env .env

# Edit with your actual values
nano .env

# Run the server
python server.py
```

### Option 2: Using environment variables

```bash
# Set environment variables
export JIRA_URL="https://issues.redhat.com"
export JIRA_API_TOKEN="your_token_here"
export SLACK_XOXC_TOKEN="your_token_here"
export SLACK_XOXD_TOKEN="your_token_here"
export LOGS_CHANNEL_ID="C0000000000"

# Run the server
python server.py
```

## 🔒 Security Best Practices

1. **Never commit real secrets** to the repository
2. **Use GitHub secrets** for production deployments
3. **Keep local .env files** in `.gitignore`
4. **Rotate tokens regularly**
5. **Use least-privilege access** for API tokens

## 🧪 Testing with GitHub Secrets

The repository includes a test workflow that verifies GitHub secrets are properly loaded:

```yaml
# .github/workflows/test.yml
- name: Test with GitHub Secrets
  env:
    JIRA_URL: ${{ secrets.JIRA_URL }}
    JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
    SLACK_XOXC_TOKEN: ${{ secrets.SLACK_XOXC_TOKEN }}
    SLACK_XOXD_TOKEN: ${{ secrets.SLACK_XOXD_TOKEN }}
    LOGS_CHANNEL_ID: ${{ secrets.LOGS_CHANNEL_ID }}
  run: python -c "import os; print('Secrets loaded:', bool(os.getenv('JIRA_URL')))"
```

## 📊 Monitoring

### Health Check

The MCP server provides a built-in health check:

```bash
# Test if the server is running
curl -X POST http://localhost:8000/health
```

### Logs

Monitor application logs for:
- Successful API connections
- Error messages
- Performance metrics

## 🚨 Troubleshooting

### Common Issues

1. **"Missing environment variables"**
   - Check if GitHub secrets are properly set
   - Verify secret names match exactly
   - Ensure secrets are not empty

2. **"Authentication failed"**
   - Verify API tokens are valid
   - Check token permissions
   - Ensure tokens haven't expired

3. **"Connection timeout"**
   - Check network connectivity
   - Verify API endpoints are accessible
   - Check firewall settings

### Debug Mode

Enable debug logging by setting:

```bash
export DEBUG=1
python server.py
```

## 📈 Scaling

### Horizontal Scaling

- Deploy multiple container instances
- Use a load balancer
- Implement health checks

### Vertical Scaling

- Increase container resources
- Optimize database queries
- Cache frequently accessed data

## 🔄 Updates

### Automatic Updates

- GitHub Actions can automatically deploy updates
- Use semantic versioning for releases
- Test updates in staging environment first

### Manual Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild container
make build

# Restart services
make restart
```
