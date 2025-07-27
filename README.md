# redhat-ai-tools/jira-mcp-features-master

A containerized Python MCP server for Cursor to provide access to Jira.

> [!IMPORTANT]
> This project is experimental and was initially created as a learning exercise.
> Be aware there are more capable and mature Jira MCP solutions available,
> such as [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian),
> and Atlassian's own [MCP Server](https://www.atlassian.com/platform/remote-mcp-server).

See also [redhat-ai-tools/jira-mcp-snowflake](https://github.com/redhat-ai-tools/jira-mcp-snowflake)
which provides another way to access Red Hat Jira data.

## Prerequisites

- **podman** - Install with `sudo dnf install podman` (Fedora/RHEL) or `brew install podman` (macOS)
- **make** - Usually pre-installed on most systems

## Quick Start

1. **Get the code**
  ```bash
  git clone git@github.com:caramuto-redhat/slack-mcp-features-master.git
  cd jira-mcp-features-master
  ```
2. **Build the image & configure Cursor**<br>
  This also creates a `~/.rh-jira-mcp-features-master.env` file like [this](example.env).
  ```bash
  make setup
  ```

3. **Prepare a Jira token**
   * Go to [Red Hat Jira Personal Access Tokens](https://issues.redhat.com/secure/ViewProfile.jspa?selectedTab=com.atlassian.pats.pats-plugin:jira-user-personal-access-tokens) and create a token
   * Edit the `.rh-jira-mcp-features-master.env` file in your home directory and paste in the token

To confirm it's working, run Cursor, go to Settings and click on "Tools &
Integrations". Under MCP Tools you should see "jiraMcp" with 26 tools enabled.

## Available Tools

This MCP server provides the following tools:

### Issue Search
- `get_jira` - Get details for a specific Jira issue by key.
- `search_issues` - Search issues using JQL

### Project Management
- `list_projects` - List all projects
- `get_project` - Get project details by key
- `get_project_components` - Get components for a project
- `get_project_versions` - Get versions for a project
- `get_project_roles` - Get roles for a project
- `get_project_permission_scheme` - Get permission scheme for a project
- `get_project_issue_types` - Get issue types for a project

### Board & Sprint Management
- `list_boards` - List all boards
- `get_board` - Get board details by ID
- `list_sprints` - List sprints for a board
- `get_sprint` - Get sprint details by ID
- `get_issues_for_board` - Get issues for a board
- `get_issues_for_sprint` - Get issues for a sprint

### User Management
- `search_users` - Search users by query
- `get_user` - Get user details by account ID
- `get_current_user` - Get current user info
- `get_assignable_users_for_project` - Get assignable users for a project
- `get_assignable_users_for_issue` - Get assignable users for an issue

### Team Reporting & Analytics
- `get_team_config` - Get the current team configuration
- `list_teams` - List all configured teams
- `generate_team_jql` - Generate JQL query for a specific team and query type
- `get_team_issues` - Get issues for a specific team with enhanced data
- `generate_team_report` - Generate comprehensive team reports with AI analysis
- `send_team_report_email` - Send team reports via email

## Team Reporting Features

This MCP server includes advanced team reporting capabilities that can generate automated weekly/monthly status reports with AI-powered analysis.

### Key Features

- **Multi-Team Support**: Configure multiple teams with different assignees and focus areas
- **AI-Powered Analysis**: Uses Gemini or OpenAI to summarize work and provide insights
- **Automated Email Reports**: Send HTML reports directly to stakeholders
- **Dynamic JQL Generation**: Automatically creates queries based on team configuration
- **Comprehensive Analytics**: Track in-progress, todo, and recently completed work

### Team Configuration

Teams are configured in `jira-config.yaml`. Example configuration:

```yaml
team_configs:
  user_group_1:
    name: "ToolChain Team"
    assignees:
      - "rhn-support-skalgudi"
      - "rhn-support-ounsal"
      - "mabanas@redhat.com"
    focus: "Development tools and infrastructure"
    email:
      subject: "ToolChain Team {period_title} Status Report - {date}"
      message: "{period_description} for ToolChain team development"
      recipients:
        - "manager@company.com"
```

### AI Configuration

To enable AI-powered summaries, add API keys to your environment:

```bash
# For Google Gemini (recommended)
GEMINI_API_KEY=your_gemini_api_key

# For OpenAI (alternative)
OPENAI_API_KEY=your_openai_api_key
```

### Email Configuration

To enable automated email reports:

```bash
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
```

### Usage Examples

```bash
# List all configured teams
list_teams()

# Generate a report for the FoA team
generate_team_report("user_group_3", include_ai_summary=True, send_email=False)

# Get current issues for ToolChain team
get_team_issues("user_group_1", query_type="in_progress", include_comments=True)

# Send a report via email
send_team_report_email("user_group_3", report_data)
```

## Development Commands

- `make build` - Build the image
- `make run` - Run the container
- `make clean` - Clean up the built image
- `make cursor-config` - Modify `~/.cursor/mcp.json` to install this MCP Server
- `make setup` - Builds the image, configures Cursor, and creates `~/.rh-jira-mcp-features-master.env` if it doesn't exist

## Troubleshooting

### Server Not Starting
- Confirm that `make run` works
- Check that the JIRA_API_TOKEN is correct
- Verify the image was built successfully with `podman images jira-mcp-features-master`
- Go to the "Output" tab in Cursor's bottom pane, choose "MCP Logs" from the drop-down select and examine the logs there

### Connection Issues
- Restart Cursor after configuration changes
- Check Cursor's developer console for error messages
- Verify the Jira URL is accessible from your network

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
