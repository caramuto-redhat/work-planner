"""
Email Configuration Manager for Work Planner MCP Server
Loads and manages email configuration from config/mail_template.yaml
"""

import os
import yaml
from typing import Dict, Any, Optional, List

class EmailConfig:
    """Configuration manager for email settings"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize email configuration"""
        self.config_path = config_path or os.path.join('config', 'mail_template.yaml')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                return config or {}
            else:
                # Return default configuration
                return self._get_default_config()
        except Exception as e:
            print(f"Warning: Could not load email config from {self.config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default email configuration"""
        return {
            'provider': {
                'type': 'gmail_smtp',
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'security': 'tls'
            },
            'recipients': {
                'default': ['pacaramu@redhat.com'],
                'teams': {},
                'admin_alerts': ['pacaramu@redhat.com']
            },
            'templates': {
                'daily_summary': {
                    'subject': 'Daily Team Summary - {team} - {date}',
                    'priority': 'normal',
                    'format': 'html',
                    'body_template': '<h1>Daily Team Summary</h1><p>Team: {team}</p><p>Date: {date}</p>{content}'
                },
                'alert': {
                    'subject': 'Alert - {alert_type} - {date}',
                    'priority': 'high',
                    'format': 'html',
                    'body_template': '<h1>Alert</h1><h2>{alert_type}</h2><p>{content}</p>'
                },
                'data_collection_report': {
                    'subject': 'Data Collection Report - {date}',
                    'priority': 'normal',
                    'format': 'plain',
                    'body_template': 'Data Collection Report\\nTeam: {team}\\nDate: {date}\\n{content}'
                }
            },
            'delivery': {
                'timezone': 'UTC',
                'retry': {
                    'max_attempts': 3,
                    'delay_seconds': 30
                },
                'batch_size': 10,
                'rate_limit': {
                    'enabled': True,
                    'max_per_hour': 20
                },
                'tracking': {
                    'enabled': True,
                    'track_opens': False,
                    'track_clicks': False
                }
            },
            'validation': {
                'validate_recipients': True,
                'auto_correct_typos': False,
                'required_fields': ['subject', 'content']
            },
            'automation': {
                'auto_send': {
                    'daily_summary': True,
                    'alerts': True,
                    'data_collection_report': True
                },
                'conditions': {
                    'send_only_on_updates': False,
                    'send_empty_reports': True,
                    'include_attachments': False
                }
            },
            'urls': {
                'dashboard_url': 'https://work-planner.example.com/dashboard',
                'stop_notifications_url': 'https://work-planner.example.com/unsubscribe',
                'support_email': 'pacaramu@redhat.com'
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration"""
        return self.config
    
    def get_provider_config(self) -> Dict[str, Any]:
        """Get email provider configuration"""
        return self.config.get('provider', {})
    
    def get_recipients_config(self) -> Dict[str, Any]:
        """Get recipients configuration"""
        return self.config.get('recipients', {})
    
    def get_templates(self) -> Dict[str, Any]:
        """Get email templates"""
        return self.config.get('templates', {})
    
    def get_delivery_config(self) -> Dict[str, Any]:
        """Get email delivery configuration"""
        return self.config.get('delivery', {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get email validation configuration"""
        return self.config.get('validation', {})
    
    def get_automation_config(self) -> Dict[str, Any]:
        """Get email automation configuration"""
        return self.config.get('automation', {})
    
    def get_urls(self) -> Dict[str, str]:
        """Get external URLs configuration"""
        return self.config.get('urls', {})
    
    def get_team_recipients(self, team: str) -> List[str]:
        """Get recipients for a specific team"""
        team_recipients = self.config.get('recipients', {}).get('teams', {}).get(team, [])
        default_recipients = self.config.get('recipients', {}).get('default', [])
        return team_recipients if team_recipients else default_recipients
    
    def get_template_config(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific template"""
        templates = self.get_templates()
        return templates.get(template_name)
    
    def is_template_enabled(self, template_name: str) -> bool:
        """Check if a template is enabled for auto-send"""
        auto_send_config = self.get_automation_config().get('auto_send', {})
        return auto_send_config.get(template_name, True)
    
    def validate_config(self) -> bool:
        """Validate the email configuration"""
        try:
            # Check required sections
            required_sections = ['provider', 'recipients', 'templates']
            for section in required_sections:
                if section not in self.config:
                    print(f"Error: Missing required section '{section}' in email config")
                    return False
            
            # Validate provider config
            provider = self.get_provider_config()
            if not provider.get('smtp_server'):
                print("Error: SMTP server not configured in email config")
                return False
            
            # Validate templates
            templates = self.get_templates()
            required_templates = ['daily_summary', 'alert', 'data_collection_report']
            for template in required_templates:
                if template not in templates:
                    print(f"Error: Missing required template '{template}' in email config")
                    return False
            
            # Validate recipient configuration
            recipients = self.get_recipients_config()
            if not recipients.get('default'):
                print("Warning: No default recipients configured in email config")
            
            return True
            
        except Exception as e:
            print(f"Error validating email config: {e}")
            return False
    
    def get_env_requirements(self) -> List[str]:
        """Get list of required environment variables"""
        return [
            'EMAIL_USERNAME',
            'EMAIL_PASSWORD', 
            'EMAIL_FROM'  # Optional, defaults to EMAIL_USERNAME
        ]
    
    def check_env_variables(self) -> Dict[str, Any]:
        """Check if required environment variables are set"""
        requirements = self.get_env_requirements()
        status = {}
        
        for var in requirements:
            status[var] = {
                'set': bool(os.getenv(var)),
                'value': '***' if os.getenv(var) else None
            }
        
        return {
            'all_set': all(status[var]['set'] for var in requirements),
            'requirements': status
        }
    
    def reload_config(self) -> bool:
        """Reload configuration from file"""
        try:
            self.config = self._load_config()
            return self.validate_config()
        except Exception as e:
            print(f"Error reloading email config: {e}")
            return False

