# GitLab CI/CD Setup Instructions

## 🔧 **Step 1: Configure GitLab CI/CD Variables**

In your GitLab project at [https://gitlab.cee.redhat.com/pacaramu/work-planner](https://gitlab.cee.redhat.com/pacaramu/work-planner):

1. Go to **Settings** → **CI/CD** → **Variables**
2. Add these variables (mark as **Protected** and **Masked**):

| Variable | Value | Description |
|----------|-------|-------------|
| `JIRA_URL` | `https://issues.redhat.com` | Your Jira instance URL |
| `JIRA_API_TOKEN` | `your_jira_token` | Your Jira API token |
| `SLACK_XOXC_TOKEN` | `your_slack_token` | Slack Bot User OAuth Token |
| `SLACK_XOXD_TOKEN` | `your_slack_token` | Slack User OAuth Token |
| `LOGS_CHANNEL_ID` | `C1234567890` | Slack channel ID for logs |

## 🚀 **Step 2: Push to GitLab**

```bash
# Add GitLab remote
git remote add gitlab https://gitlab.cee.redhat.com/pacaramu/work-planner.git

# Push to GitLab
git push gitlab main
```

## 🔄 **Step 3: Automated Build Process**

1. **Push triggers CI/CD**: Every push to `main` branch triggers the pipeline
2. **Container builds**: GitLab CI/CD builds the container with embedded secrets
3. **Registry push**: Container is pushed to GitLab Container Registry
4. **Ready to use**: Container is available at `registry.gitlab.cee.redhat.com/pacaramu/work-planner:latest`

## 🎯 **Step 4: Use in Cursor MCP**

Your MCP configuration is already updated to use GitLab:

```json
{
  "mcpServers": {
    "workPlannerMcp": {
      "command": "bash",
      "args": [
        "-c",
        "podman run -i --rm --name work-planner-container -v /Users/pacaramu/Documents/Git/work-planner/slack_dumps:/app/slack_dumps registry.gitlab.cee.redhat.com/pacaramu/work-planner:latest"
      ],
      "description": "Work Planner MCP server from GitLab Container Registry with embedded secrets"
    }
  }
}
```

## ✅ **Benefits of GitLab Integration**

- **All-in-one**: Source code, CI/CD, and container registry in one place
- **Enterprise**: Red Hat's internal GitLab instance
- **Security**: CI/CD variables are encrypted and protected
- **Automation**: Every push automatically builds and deploys
- **Monitoring**: Built-in pipeline monitoring and logs

## 🔍 **Monitoring**

- **Pipeline Status**: [https://gitlab.cee.redhat.com/pacaramu/work-planner/-/pipelines](https://gitlab.cee.redhat.com/pacaramu/work-planner/-/pipelines)
- **Container Registry**: [https://gitlab.cee.redhat.com/pacaramu/work-planner/-/container_registry](https://gitlab.cee.redhat.com/pacaramu/work-planner/-/container_registry)
- **CI/CD Logs**: Available in the pipeline view
