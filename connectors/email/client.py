"""
Email Client for Work Planner MCP Server
Handles email sending, validation, and template rendering, and inbox reading via IMAP
"""

import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from email.header import decode_header
import re
from datetime import datetime, timedelta
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


class InboxReader:
    """IMAP client for reading emails from inbox"""
    
    def __init__(self, imap_config: Dict[str, Any]):
        """Initialize inbox reader with IMAP configuration"""
        self.imap_config = imap_config
        self.filtering_config = imap_config.get('filtering', {})
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            server = self.imap_config.get('server', 'imap.gmail.com')
            port = self.imap_config.get('port', 993)
            security = self.imap_config.get('security', 'ssl')
            
            username = os.getenv('EMAIL_USERNAME')
            password = os.getenv('EMAIL_PASSWORD')
            
            if not username or not password:
                logger.error("Missing EMAIL_USERNAME or EMAIL_PASSWORD environment variables")
                return False
            
            # Connect based on security type
            if security == 'ssl':
                self.connection = imaplib.IMAP4_SSL(server, port)
            else:
                self.connection = imaplib.IMAP4(server, port)
                if security == 'tls':
                    self.connection.starttls()
            
            # Login
            self.connection.login(username, password)
            logger.info(f"Successfully connected to IMAP server: {server}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {str(e)}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        try:
            if self.connection:
                self.connection.logout()
                logger.info("Disconnected from IMAP server")
        except Exception as e:
            logger.warning(f"Error disconnecting from IMAP: {str(e)}")
    
    def fetch_emails(self, days_back: int = 30, folder: str = 'INBOX') -> List[Dict[str, Any]]:
        """
        Fetch emails from inbox
        
        Args:
            days_back: Number of days to look back
            folder: IMAP folder to read from
            
        Returns:
            List of email dictionaries with parsed content
        """
        try:
            if not self.connection:
                if not self.connect():
                    return []
            
            # Select folder
            self.connection.select(folder, readonly=True)
            
            # Calculate date range
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            
            # Search for emails
            unread_only = self.filtering_config.get('unread_only', False)
            if unread_only:
                search_criteria = f'(UNSEEN SINCE {since_date})'
            else:
                search_criteria = f'(SINCE {since_date})'
            
            status, messages = self.connection.search(None, search_criteria)
            
            if status != 'OK':
                logger.error(f"Failed to search emails: {status}")
                return []
            
            email_ids = messages[0].split()
            max_emails = self.filtering_config.get('max_emails', 100)
            
            # Limit number of emails
            email_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
            
            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email_by_id(email_id)
                if email_data and self._should_include_email(email_data):
                    emails.append(email_data)
            
            logger.info(f"Fetched {len(emails)} emails from {folder} (last {days_back} days)")
            return emails
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {str(e)}")
            return []
    
    def _fetch_email_by_id(self, email_id: bytes) -> Optional[Dict[str, Any]]:
        """Fetch and parse a single email by ID"""
        try:
            status, msg_data = self.connection.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                return None
            
            # Parse email
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Decode subject
            subject = self._decode_header(email_message['Subject'])
            
            # Get sender
            from_header = email_message.get('From', '')
            
            # Get date
            date_str = email_message.get('Date', '')
            email_date = self._parse_date(date_str)
            
            # Get body
            body = self._get_email_body(email_message)
            
            return {
                'id': email_id.decode(),
                'from': from_header,
                'subject': subject,
                'date': email_date,
                'body': body,
                'raw_date': date_str
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse email {email_id}: {str(e)}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ''
        
        try:
            decoded_parts = decode_header(header)
            decoded_str = ''
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    decoded_str += part.decode(encoding or 'utf-8', errors='ignore')
                else:
                    decoded_str += part
            return decoded_str
        except Exception as e:
            logger.warning(f"Failed to decode header: {str(e)}")
            return str(header)
    
    def _get_email_body(self, email_message) -> str:
        """Extract email body (plain text preferred)"""
        body = ''
        
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # Skip attachments
                    if 'attachment' in content_disposition:
                        continue
                    
                    # Get plain text
                    if content_type == 'text/plain':
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                                break
                        except Exception as e:
                            logger.warning(f"Failed to decode email part: {str(e)}")
                    
                    # Fall back to HTML if no plain text
                    elif content_type == 'text/html' and not body:
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='ignore')
                        except Exception as e:
                            logger.warning(f"Failed to decode HTML part: {str(e)}")
            else:
                # Not multipart - get payload directly
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
        
        except Exception as e:
            logger.error(f"Failed to extract email body: {str(e)}")
        
        return body
    
    def _parse_date(self, date_str: str) -> str:
        """Parse email date to ISO format"""
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {str(e)}")
            return date_str
    
    def _should_include_email(self, email_data: Dict[str, Any]) -> bool:
        """Check if email should be included based on filtering rules"""
        # Check sender exclusions
        exclude_senders = self.filtering_config.get('exclude_senders', [])
        sender = email_data.get('from', '').lower()
        for excluded in exclude_senders:
            if excluded.lower() in sender:
                return False
        
        # Check subject exclusions
        exclude_subjects = self.filtering_config.get('exclude_subjects', [])
        subject = email_data.get('subject', '').lower()
        for excluded in exclude_subjects:
            if excluded.lower() in subject:
                return False
        
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """Test IMAP connection"""
        try:
            if self.connect():
                # Try to list folders
                status, folders = self.connection.list()
                self.disconnect()
                
                return {
                    'success': True,
                    'server': self.imap_config.get('server'),
                    'port': self.imap_config.get('port'),
                    'folders_count': len(folders) if status == 'OK' else 0
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to connect'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
