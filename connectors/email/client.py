"""
Email Client for Work Planner MCP Server
Handles email sending, validation, and template rendering
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailClient:
    """Email client for sending various types of notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize email client with configuration"""
        self.config = config
        self.provider_config = config.get('provider', {})
        self.recipients_config = config.get('recipients', {})
        self.templates = config.get('templates', {})
        self.delivery_config = config.get('delivery', {})
        self.validation_config = config.get('validation', {})
        self.automation_config = config.get('automation', {})
        
        # Validate configuration
        if not self._validate_config():
            raise ValueError("Invalid email configuration")
    
    def _validate_config(self) -> bool:
        """Validate email configuration"""
        required_env_vars = ['EMAIL_USERNAME', 'EMAIL_PASSWORD']
        
        for var in required_env_vars:
            if not os.getenv(var):
                logger.error(f"Missing required environment variable: {var}")
                return False
        
        # Validate SMTP settings
        if not self.provider_config.get('smtp_server'):
            logger.error("SMTP server not configured")
            return False
        
        # Validate templates
        required_templates = ['team_daily_report_with_todo']
        for template in required_templates:
            if template not in self.templates:
                logger.error(f"Missing required template: {template}")
                return False
        
        return True
    
    def send_email(self, 
                   template_name: str, 
                   recipients: List[str], 
                   content_data: Dict[str, Any],
                   attachments: Optional[List[str]] = None,
                   cc_recipients: Optional[List[str]] = None,
                   bcc_recipients: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send email using specified template
        
        Args:
            template_name: Name of template to use
            recipients: List of recipient email addresses
            content_data: Data to fill template variables
            attachments: Optional list of file paths to attach
            cc_recipients:carbon copy recipients
            bcc_recipients:blind carbon copy recipients
            
        Returns:
            Dict with send status and details
        """
        try:
            # Get template configuration
            template_config = self.templates.get(template_name)
            if not template_config:
                return {
                    'success': False,
                    'error': f'Template "{template_name}" not found',
                    'template_name': template_name
                }
            
            # Validate recipients if enabled
            if self.validation_config.get('validate_recipients', True):
                invalid_recipients = [email for email in recipients if not self._validate_email(email)]
                if invalid_recipients:
                    return {
                        'success': False,
                        'error': f'Invalid email addresses: {invalid_recipients}',
                        'template_name': template_name
                    }
            
            # Create message
            if template_config.get('format') == 'html':
                msg = MIMEMultipart('alternative')
            else:
                msg = MIMEMultipart()
            
            # Set headers
            subject = self._render_template(template_config['subject'], content_data)
            msg['Subject'] = subject
            msg['From'] = os.getenv('EMAIL_FROM', os.getenv('EMAIL_USERNAME'))
            msg['To'] = ', '.join(recipients)
            
            if cc_recipients:
                msg['Cc'] = ', '.join(cc_recipients)
            
            # Add BCC headers (BCC recipients are added to sendmail call)
            all_recipients = recipients.copy()
            if cc_recipients:
                all_recipients.extend(cc_recipients)
            if bcc_recipients:
                all_recipients.extend(bcc_recipients)
            
            # Add body content
            body_content = self._render_template(template_config['body_template'], content_data)
            
            if template_config.get('format') == 'html':
                msg.attach(MIMEText(body_content, 'html'))
            else:
                msg.attach(MIMEText(body_content, 'plain'))
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as f:
                            attachment = MIMEApplication(f.read())
                            attachment.add_header(
                                'Content-Disposition', 
                                'attachment', 
                                filename=os.path.basename(attachment_path)
                            )
                            msg.attach(attachment)
                        logger.info(f"Added attachment: {attachment_path}")
                    else:
                        logger.warning(f"Attachment file not found: {attachment_path}")
            
            # Send email
            success_info = self._send_smtp_email(msg, all_recipients)
            
            return {
                'success': True,
                'template_name': template_name,
                'recipients_count': len(all_recipients),
                'recipients': all_recipients,
                'subject': subject,
                'attachments_count': len(attachments) if attachments else 0,
                'send_details': success_info
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'template_name': template_name
            }
    
    def send_daily_summary(self, team: str, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send daily summary email for a team"""
        # Get team-specific recipients
        recipients = self._get_team_recipients(team)
        
        # Prepare content data
        content_data = {
            'team': team.title(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            **(summary_data or {}),
            'dashboard_url': self.config.get('urls', {}).get('dashboard_url', '#'),
            'stop_notifications_url': self.config.get('urls', {}).get('stop_notifications_url', '#'),
            'support_email': self.config.get('urls', {}).get('support_email', 'support@example.com')
        }
        
        return self.send_email('daily_summary', recipients, content_data)
    
    def send_alert(self, alert_type: str, alert_content: Dict[str, Any]) -> Dict[str, Any]:
        """Send alert notification"""
        # Get admin alert recipients
        recipients = self.recipients_config.get('admin_alerts', self.recipients_config.get('default', []))
        
        # Prepare content data
        content_data = {
            'alert_type': alert_type,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            **(alert_content or {}),
            'dashboard_url': self.config.get('urls', {}).get('dashboard_url', '#'),
            'stop_notifications_url': self.config.get('urls', {}).get('stop_notifications_url', '#')
        }
        
        return self.send_email('alert', recipients, content_data)
    
    def send_data_collection_report(self, 
                                   team: str, 
                                   collection_data: Dict[str, Any],
                                   attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """Send data collection report with optional attachments"""
        # Get team-specific recipients
        recipients = self._get_team_recipients(team)
        
        # Prepare content data
        content_data = {
            'team': team,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            **(collection_data or {}),
            'dashboard_url': self.config.get('urls', {}).get('dashboard_url', '#'),
            'stop_notifications_url': self.config.get('urls', {}).get('stop_notifications_url', '#'),
            'support_email': self.config.get('urls', {}).get('support_email', 'support@example.com')
        }
        
        return self.send_email('data_collection_report', recipients, content_data, attachments)
    
    def _get_team_recipients(self, team: str) -> List[str]:
        """Get recipients from simplified configuration"""
        # Simplified configuration - just return the single email address
        email = self.recipients_config.get('email', 'pacaramu@redhat.com')
        return [email] if email else []
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Render template with data using simple string formatting"""
        try:
            # Add default values for common variables
            default_data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'time': datetime.now().strftime('%H:%M:%S'),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            default_data.update(data)
            
            return template.format(**default_data)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            # Return template with unsubstituted variables
            return template.format(**{k: f'{{{k}}}' for k in data.keys()})
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def _send_smtp_email(self, msg: MIMEMultipart, recipients: List[str]) -> Dict[str, Any]:
        """Send email via SMTP with retry logic"""
        max_attempts = self.delivery_config.get('retry', {}).get('max_attempts', 3)
        delay_seconds = self.delivery_config.get('retry', {}).get('delay_seconds', 30)
        
        smtp_server = self.provider_config.get('smtp_server', 'smtp.gmail.com')
        smtp_port = self.provider_config.get('smtp_port', 587)
        security = self.provider_config.get('security', 'tls')
        
        username = os.getenv('EMAIL_USERNAME')
        password = os.getenv('EMAIL_PASSWORD')
        
        for attempt in range(max_attempts):
            try:
                # Connect to SMTP server
                server = smtplib.SMTP(smtp_server, smtp_port)
                
                if security == 'tls':
                    server.starttls()
                elif security == 'ssl':
                    server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                
                # Authenticate
                server.login(username, password)
                
                # Send email
                server.sendmail(username, recipients, msg.as_string())
                server.quit()
                
                logger.info(f"Email sent successfully to {len(recipients)} recipients")
                return {
                    'status': 'success',
                    'recipients_count': len(recipients),
                    'server': smtp_server,
                    'attempt': attempt + 1
                }
                
            except Exception as e:
                logger.warning(f"SMTP send attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_attempts - 1:
                    import time
                    time.sleep(delay_seconds)
                else:
                    raise Exception(f"Failed to send email after {max_attempts} attempts: {str(e)}")
        
        return {
            'status': 'failed',
            'error': 'Max retry attempts exceeded'
        }
    
    def get_template_names(self) -> List[str]:
        """Get list of available email templates"""
        return list(self.templates.keys())
    
    def get_team_recipients(self, team: str) -> Dict[str, Any]:
        """Get recipient information for a team"""
        return {
            'team': team,
            'recipients': self._get_team_recipients(team),
            'has_team_specific': team in self.recipients_config.get('teams', {}),
            'default_recipients': self.recipients_config.get('default', [])
        }
    
    def test_email_connection(self) -> Dict[str, Any]:
        """Test SMTP connection without sending email"""
        try:
            smtp_server = self.provider_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = self.provider_config.get('smtp_port', 587)
            security = self.provider_config.get('security', 'tls')
            
            username = os.getenv('EMAIL_USERNAME')
            password = os.getenv('EMAIL_PASSWORD')
            
            if not username or not password:
                return {
                    'success': False,
                    'error': 'Missing EMAIL_USERNAME or EMAIL_PASSWORD environment variables'
                }
            
            # Test connection
            server = smtplib.SMTP(smtp_server, smtp_port)
            
            if security == 'tls':
                server.starttls()
            elif security == 'ssl':
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            
            server.login(username, password)
            server.quit()
            
            return {
                'success': True,
                'provider': {
                    'type': self.provider_config.get('type'),
                    'server': smtp_server,
                    'port': smtp_port,
                    'security': security
                },
                'username': username
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': self.provider_config
            }
