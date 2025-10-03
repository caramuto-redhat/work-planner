"""
Schedule Configuration Loader
Handles loading and validation of data collection schedule configuration
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class ScheduleConfig:
    """Configuration manager for data collection schedule"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize schedule configuration"""
        self.config_path = config_path or os.path.join('config', 'schedule.yaml')
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
            print(f"Warning: Could not load schedule config from {self.config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'global': {
                'timezone': 'UTC',
                'retention_days': 30,
                'max_age_hours': 24
            },
            'slack': {
                'enabled': True,
                'schedule': '0 6 * * *',
                'teams': [],
                'include_attachments': False
            },
            'jira': {
                'enabled': True,
                'schedule': '0 7 * * *',
                'teams': []
            },
            'ai_analysis': {
                'enabled': True,
                'schedule': '0 8 * * *',
                'teams': []
            },
            'email_summary': {
                'enabled': True,
                'schedule': '0 9 * * *',
                'teams': []
            },
            'cleanup': {
                'enabled': True,
                'schedule': '0 2 * * 0',
                'retention_days': 30,
                'keep_latest': 10,
                'compress_old': True
            },
            'notifications': {
                'enabled': True,
                'slack_channel': '',
                'on_success': True,
                'on_failure': True,
                'on_warning': True
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration"""
        return self.config
    
    def is_enabled(self, service: str) -> bool:
        """Check if a service is enabled"""
        return self.config.get(service, {}).get('enabled', False)
    
    def get_schedule(self, service: str) -> str:
        """Get the cron schedule for a service"""
        return self.config.get(service, {}).get('schedule', '0 0 * * *')
    
    def get_teams(self, service: str) -> List[Dict[str, Any]]:
        """Get teams configuration for a service"""
        return self.config.get(service, {}).get('teams', [])
    
    def get_team_config(self, service: str, team_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific team and service"""
        teams = self.get_teams(service)
        return next((team for team in teams if team.get('name') == team_name), None)
    
    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration settings"""
        return self.config.get('global', {})
    
    def get_retention_days(self) -> int:
        """Get data retention period in days"""
        return self.get_global_config().get('retention_days', 30)
    
    def get_max_age_hours(self) -> int:
        """Get maximum age before forcing fresh dump"""
        return self.get_global_config().get('max_age_hours', 24)
    
    def get_timezone(self) -> str:
        """Get configured timezone"""
        return self.get_global_config().get('timezone', 'UTC')
    
    def get_notification_config(self) -> Dict[str, Any]:
        """Get notification configuration"""
        return self.config.get('notifications', {})
    
    def should_notify(self, notification_type: str) -> bool:
        """Check if notifications are enabled for a specific type"""
        notifications = self.get_notification_config()
        return notifications.get('enabled', False) and notifications.get(notification_type, False)
    
    def get_include_attachments(self) -> bool:
        """Get whether to include attachments in Slack dumps"""
        return self.config.get('slack', {}).get('include_attachments', False)
    
    def get_cleanup_config(self) -> Dict[str, Any]:
        """Get cleanup configuration"""
        return self.config.get('cleanup', {})
    
    def validate_config(self) -> bool:
        """Validate the current configuration"""
        try:
            # Check required sections
            required_sections = ['global', 'slack', 'jira', 'ai_analysis', 'email_summary']
            for section in required_sections:
                if section not in self.config:
                    print(f"Warning: Missing required section '{section}' in schedule config")
                    return False
            
            # Validate cron schedules
            import re
            cron_pattern = r'^(\*|([0-5]?\d)) (\*|([01]?\d|2[0-3])) (\*|([012]?\d|3[01])) (\*|([0-6]))$'
            
            for service in ['slack', 'jira', 'ai_analysis', 'email_summary', 'cleanup']:
                schedule = self.get_schedule(service)
                if not re.match(cron_pattern, schedule):
                    print(f"Warning: Invalid cron schedule '{schedule}' for service '{service}'")
                    return False
            
            # Validate team configurations
            for service in ['slack', 'jira', 'ai_analysis', 'email_summary']:
                teams = self.get_teams(service)
                for team in teams:
                    if 'name' not in team:
                        print(f"Warning: Team missing 'name' field in {service} configuration")
                        return False
            
            return True
            
        except Exception as e:
            print(f"Error validating schedule config: {e}")
            return False
    
    def get_enabled_services(self) -> List[str]:
        """Get list of enabled services"""
        enabled = []
        services = ['slack', 'jira', 'ai_analysis', 'email_summary', 'cleanup']
        
        for service in services:
            if self.is_enabled(service):
                enabled.append(service)
        
        return enabled
    
    def get_next_run_times(self) -> Dict[str, str]:
        """Get next run times for all enabled services"""
        from croniter import croniter
        from datetime import datetime
        
        next_runs = {}
        now = datetime.now()
        
        for service in self.get_enabled_services():
            schedule = self.get_schedule(service)
            try:
                cron = croniter(schedule, now)
                next_run = cron.get_next(datetime)
                next_runs[service] = next_run.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                next_runs[service] = f"Error: {e}"
        
        return next_runs
