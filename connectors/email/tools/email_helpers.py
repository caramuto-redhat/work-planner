"""
Email Helper Functions
Shared utilities for Email MCP tools
"""

import os


def format_daily_summary_content(slack_summary, jira_summary, action_items, blockers, metrics):
    """Format daily summary content sections"""
    sections = []
    
    if metrics and isinstance(metrics, dict):
        sections.append("<div class='metrics'>")
        for key, value in metrics.items():
            sections.append(f"<div class='metric'><div class='metric-value'>{value}</div><div class='metric-label'>{key}</div></div>")
        sections.append("</div>")
    
    if slack_summary:
        sections.append("<div class='section'><h2>💬 Slack Summary</h2>" + slack_summary + "</div>")
    
    if jira_summary:
        sections.append("<div class='section'><h2>🎯 Jira Summary</h2>" + jira_summary + "</div>")
    
    if action_items:
        sections.append("<div class='section'><h2>✅ Action Items</h2><div class='action-item'>" + action_items + "</div></div>")
    
    if blockers:
        sections.append("<div class='section'><h2>🚨 Blockers & Issues</h2><div class='blocker'>" + blockers + "</div></div>")
    
    return "\n".join(sections) if sections else "<p>No activity data available for this period.</p>"


def format_alert_content(severity, message, details, affected_team, resolution_steps):
    """Format alert content"""
    content = []
    
    if severity:
        severity_colors = {
            'low': '#28a745',
            'medium': '#ffc107', 
            'high': '#fd7e14',
            'critical': '#dc3545'
        }
        color = severity_colors.get(severity.lower(), '#6c757d')
        content.append(f"<p><strong style='color: {color}'>Severity:</strong> {severity.upper()}</p>")
    
    if affected_team:
        content.append(f"<p><strong>Affected Team:</strong> {affected_team}</p>")
    
    if message:
        content.append(f"<div class='alert-content'><strong>Alert Message:</strong><br>{message}</div>")
    
    if details:
        content.append(f"<div class='alert-content'><strong>Details:</strong><br>{details}</div>")
    
    if resolution_steps:
        content.append(f"<div class='alert-content'><strong>Suggested Resolution:</strong><br>{resolution_steps}</div>")
    
    return "\n".join(content)


def generate_files_summary(attachment_paths):
    """Generate summary of attached files"""
    if not attachment_paths:
        return "No attachments"
    
    file_details = []
    for path in attachment_paths:
        if os.path.exists(path):
            size = os.path.getsize(path)
            size_mb = size / (1024 * 1024)
            file_details.append(f"- {os.path.basename(path)} ({size_mb:.2f} MB)")
        else:
            file_details.append(f"- {os.path.basename(path)} (file not found)")
    
    return "\n".join(file_details)








