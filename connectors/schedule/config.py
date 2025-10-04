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
        service_config = self.config.get(service, {})
        
        # Check if this service uses the global schedule
        global_schedule_enabled = service_config.get('global_schedule', False)
        
        if global_schedule_enabled:
            # Use the global schedule if it exists, otherwise fall back to individual schedule
            global_schedule = self.config.get('schedule', service_config.get('schedule', '0 0 * * *'))
            return global_schedule
        else:
            # Use individual schedule
            return service_config.get('schedule', '0 0 * * *')
    
    def get_teams(self, service: str) -> List[Dict[str, Any]]:
        """Get teams configuration for a service"""
        return self.config.get(service, {}).get('teams', [])
    
    def get_global_schedule(self) -> str:
        """Get the global schedule"""
        return self.config.get('schedule', '0 6 * * *')
    
    def services_using_global_schedule(self) -> List[str]:
        """Get list of services that use the global schedule"""
        services = []
        global_enabled_services = ['slack', 'jira', 'ai_summary', 'cleanup']
        
        for service in global_enabled_services:
            service_config = self.config.get(service, {})
            if service_config.get('global_schedule', False):
                services.append(service)
        
        return services
    
    def services_using_individual_schedule(self) -> List[str]:
        """Get list of services that use individual schedules"""
        services = []
        all_services = ['slack', 'jira', 'ai_summary', 'cleanup']
        
        for service in all_services:
            service_config = self.config.get(service, {})
            if not service_config.get('global_schedule', False):
                services.append(service)
        
        return services
    
    def get_team_config(self, service: str, team_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific team and service"""
        teams = self.get_teams(service)
        return next((team for team in teams if team.get('name') == team_name), None)
    
    def get_ai_summary_config(self) -> Dict[str, Any]:
        """Get AI summary configuration"""
        return self.config.get('ai_summary', {})
    
    def get_ai_summary_email_config(self) -> Dict[str, Any]:
        """Get AI summary email configuration"""
        ai_summary_config = self.get_ai_summary_config()
        return ai_summary_config.get('email', {})
    
    def is_ai_summary_email_enabled(self) -> bool:
        """Check if AI summary email sending is enabled"""
        email_config = self.get_ai_summary_email_config()
        return email_config.get('enabled', False)
    
    def get_ai_summary_teams(self) -> List[Dict[str, Any]]:
        """Get teams configuration for AI summary"""
        ai_summary_config = self.get_ai_summary_config()
        return ai_summary_config.get('teams', [])
    
    def get_jira_tickets_filter(self, team_name: str) -> str:
        """Get the Jira tickets filter for a specific team"""
        team_config = self.get_team_config('jira', team_name)
        if team_config and 'tickets' in team_config:
            return team_config['tickets']
        return "All In Progress"  # Default filter
    
    def has_service_config(self, service: str) -> bool:
        """Check if a service has configuration defined"""
        return service in self.config
    
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
            required_sections = ['global', 'slack', 'jira', 'ai_summary', 'cleanup']
            for section in required_sections:
                if section not in self.config:
                    print(f"Warning: Missing required section '{section}' in schedule config")
                    return False
            
            # Validate cron schedules
            import re
            # Standard cron format: minute hour day month dayofweek
            cron_pattern = r'^(\*|[0-5]?\d) (\*|[01]?\d|2[0-3]) (\*|3[01]|[12]?\d|[1-9]) (\*|1[0-2]|[1-9]) (\*|[0-6])$'
            
            for service in ['slack', 'jira', 'ai_summary', 'cleanup']:
                schedule = self.get_schedule(service)
                if not re.match(cron_pattern, schedule):
                    print(f"Warning: Invalid cron schedule '{schedule}' for service '{service}'")
                    return False
            
            # Validate team configurations
            for service in ['slack', 'jira']:
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
        services = ['slack', 'jira', 'ai_summary', 'cleanup']
        
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
