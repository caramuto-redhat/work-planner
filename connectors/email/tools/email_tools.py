"""
Email Tools for Work Planner MCP Server
MCP tools for email operations
"""

import json
from typing import Dict, Any, List, Optional
from utils.responses import create_error_response, create_success_response
from utils.validators import validate_team_name
from .email_helpers import (
    format_daily_summary_content,
    format_alert_content,
    generate_files_summary
)
from ..client import EmailClient
from ..config import EmailConfig


def send_email_tool(client, config):
    """Create send_email tool function"""
    
    def send_email(
        template_name: str,
        recipients: str,  # Comma-separated list of email addresses
        subject: str = None,
        content: str = None,
        attachment_paths: str = None,  # Comma-separated list of file paths
        cc_recipients: str = None,  # Comma-separated CC recipients
        bcc_recipients: str = None   # Comma-separated BCC recipients
    ) -> str:
        """
        Send email using specified template and recipients.
        
        Args:
            template_name: Name of email template to use
            recipients: Comma-separated list of recipient email addresses
            subject: Override subject (optional)
            content: Email content (optional, can use template variables)
            attachment_paths: Comma-separated list of file paths to attach
            cc_recipients: Comma-separated CC recipients (optional)
            bcc_recipients: Comma-separated BCC recipients (optional)
            
        Returns:
            Email send status and details
        """
        try:
            # Parse recipients lists
            recipient_list = [email.strip() for email in recipients.split(',') if email.strip()]
            cc_list = [email.strip() for email in cc_recipients.split(',')] if cc_recipients else None
            bcc_list = [email.strip() for email in bcc_recipients.split(',')] if bcc_recipients else None
            
            # Parse attachment paths
            attachment_list = [path.strip() for path in attachment_paths.split(',')] if attachment_paths else None
            
            # Prepare content data
            content_data = {}
            if subject:
                content_data['subject'] = subject
            if content:
                content_data['content'] = content
            
            # Send email
            result = client.send_email(
                template_name=template_name,
                recipients=recipient_list,
                content_data=content_data,
                attachments=attachment_list,
                cc_recipients=cc_list,
                bcc_recipients=bcc_list
            )
            
            if result['success']:
                return create_success_response({
                    "message": "Email sent successfully",
                    "template_used": template_name,
                    "recipients_count": result['recipients_count'],
                    "recipients": result['recipients'],
                    "subject": result['subject'],
                    "attachments_count": result.get('attachments_count', 0),
                    "send_details": result.get('send_details', {})
                })
            else:
                return create_error_response(f"Failed to send email: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            return create_error_response("Failed to send email", str(e))
    
    return send_email


def send_daily_summary_tool(client, config):
    """Create send_daily_summary tool function"""
    
    def send_daily_summary(
        team: str,
        slack_summary: str = None,
        jira_summary: str = None,
        action_items: str = None,
        blockers: str = None,
        metrics: str = None  # JSON string with metrics data
    ) -> str:
        """
        Send daily summary email for a team with Slack and Jira insights.
        
        Args:
            team: Team name (e.g., toolchain, foa, assessment, boa)
            slack_summary: Summary of Slack conversations
            jira_summary: Summary of Jira tickets and progress
            action_items: List of action items and assignments
            blockers: List of blockers and issues
            metrics: JSON string with team metrics (issues resolved, velocity, etc.)
            
        Returns:
            Email send status and details
        """
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Parse metrics if provided
            metrics_data = {}
            if metrics:
                try:
                    metrics_data = json.loads(metrics)
                except json.JSONDecodeError:
                    metrics_data = {"raw_metrics": metrics}
            
            # Prepare summary data
            summary_data = {
                'content': format_daily_summary_content(
                    slack_summary, jira_summary, action_items, blockers, metrics_data
                ),
                **(metrics_data or {})
            }
            
            # Send email
            result = client.send_daily_summary(validated_team, summary_data)
            
            if result['success']:
                return create_success_response({
                    "message": "Daily summary email sent successfully",
                    "team": validated_team,
                    "template_used": "daily_summary",
                    "recipients_count": result['recipients_count'],
                    "recipients": result['recipients'],
                    "subject": result['subject']
                })
            else:
                return create_error_response(f"Failed to send daily summary: {result.get('error', 'Unknown error')}")
                
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to send daily summary", str(e))
    
    return send_daily_summary


def send_alert_tool(client, config):
    """Create send_alert tool function"""
    
    def send_alert(
        alert_type: str,
        severity: str = "medium",  # low, medium, high, critical
        message: str = None,
        details: str = None,
        affected_team: str = None,
        resolution_steps: str = None
    ) -> str:
        """
        Send alert notification email.
        
        Args:
            alert_type: Type of alert (e.g., "system_down", "data_collection_failed", "high_error_rate")
            severity: Alert severity level (low, medium, high, critical)
            message: Main alert message
            
        Returns:
            Email send status and details
        """
        try:
            # Prepare alert content data
            alert_content = {
                'content': format_alert_content(severity, message, details, affected_team, resolution_steps),
                'severity': severity,
                'affected_team': affected_team or 'Multiple Teams'
            }
            
            # Send alert
            result = client.send_alert(alert_type, alert_content)
            
            if result['success']:
                return create_success_response({
                    "message": "Alert email sent successfully",
                    "alert_type": alert_type,
                    "severity": severity,
                    "template_used": "alert",
                    "recipients_count": result['recipients_count'],
                    "recipients": result['recipients'],
                    "subject": result['subject']
                })
            else:
                return create_error_response(f"Failed to send alert: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            return create_error_response("Failed to send alert", str(e))
    
    return send_alert


def send_data_collection_report_tool(client, config):
    """Create send_data_collection_report tool function"""
    
    def send_data_collection_report(
        team: str,
        slack_channels_count: int = 0,
        slack_messages_count: int = 0,
        jira_issues_count: int = 0,
        jira_filter: str = "All Issues",
        attachment_paths: str = None  # Comma-separated list of files
    ) -> str:
        """
        Send data collection report with optional file attachments.
        
        Args:
            team: Team name
            slack_channels_count: Number of Slack channels processed
            slack_messages_count: Number of Slack messages collected
            jira_issues_count: Number of Jira issues collected
            jira_filter: Jira search filter used
            attachment_paths: Comma-separated list of file paths to attach
            
        Returns:
            Email send status and details
        """
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Parse attachment paths
            attachment_list = [path.strip() for path in attachment_paths.split(',')] if attachment_paths else None
            
            # Prepare collection data
            collection_data = {
                'suspect_channels_count': slack_channels_count,
                'slack_messages_count': slack_messages_count,
                'jira_issues_count': jira_issues_count,
                'jira_filter': jira_filter,
                'files_summary': generate_files_summary(attachment_list)
            }
            
            # Send report
            result = client.send_data_collection_report(validated_team, collection_data, attachment_list)
            
            if result['success']:
                return create_success_response({
                    "message": "Data collection report sent successfully",
                    "team": validated_team,
                    "template_used": "data_collection_report",
                    "recipients_count": result['recipients_count'],
                    "recipients": result['recipients'],
                    "subject": result['subject'],
                    "attachments_count": result.get('attachments_count', 0)
                })
            else:
                return create_error_response(f"Failed to send data collection report: {result.get('error', 'Unknown error')}")
                
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to send data collection report", str(e))
    
    return send_data_collection_report


def test_email_connection_tool(client, config):
    """Create test_email_connection tool function"""
    
    def test_email_connection() -> str:
        """
        Test email configuration and SMTP connection.
        
        Returns:
            Connection test results and configuration details
        """
        try:
            # Test SMTP connection
            connection_result = client.test_email_connection()
            
            # Get environment variable status
            econfig = EmailConfig()
            env_status = econfig.check_env_variables()
            
            # Get configuration summary
            config_summary = {
                "provider": {
                    "type": econfig.get_provider_config().get('type'),
                    "server": econfig.get_provider_config().get('smtp_server'),
                    "port": econfig.get_provider_config().get('smtp_port'),
                    "security": econfig.get_provider_config().get('security')
                },
                "templates": list(econfig.get_templates().keys()),
                "recipients": {
                    "default_count": len(econfig.get_recipients_config().get('default', [])),
                    "team_recipes": len(econfig.get_recipients_config().get('teams', {}))
                },
                "automation": econfig.get_automation_config().get('auto_send', {})
            }
            
            return create_success_response({
                "connection_test": connection_result,
                "environment_status": env_status,
                "configuration_summary": config_summary,
                "ready": connection_result.get('success', False) and env_status.get('all_set', False)
            })
                
        except Exception as e:
            return create_error_response("Failed to test email connection", str(e))
    
    return test_email_connection


def get_email_config_tool(client, config):
    """Create get_email_config tool function"""
    
    def get_email_config(section: str = "all") -> str:
        """
        Get email configuration details.
        
        Args:
            section: Configuration section to return (provider, recipients, templates, delivery, all)
            
        Returns:
            Email configuration details
        """
        try:
            econfig = EmailConfig()
            
            if section == "all":
                config_data = econfig.get_config()
            elif section == "provider":
                config_data = econfig.get_provider_config()
            elif section == "recipients":
                config_data = econfig.get_recipients_config()
            elif section == "templates":
                config_data = econfig.get_templates()
            elif section == "delivery":
                config_data = econfig.get_delivery_config()
            elif section == "validation":
                config_data = econfig.get_validation_config()
            elif section == "automation":
                config_data = econfig.get_automation_config()
            elif section == "urls":
                config_data = econfig.get_urls()
            else:
                return create_error_response(f"Unknown configuration section: {section}. Valid sections: all, provider, recipients, templates, delivery, validation, automation, urls")
            
            return create_success_response({
                "configuration_section": section,
                "data": config_data,
                "valid": econfig.validate_config(),
                "file_path": econfig.config_path
            })
                
        except Exception as e:
            return create_error_response("Failed to get email configuration", str(e))
    
    return get_email_config
