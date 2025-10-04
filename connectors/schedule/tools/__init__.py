"""
Schedule Management Tools
MCP tools for managing scheduled data collection
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_team_name
from ..config import ScheduleConfig
import json
import os
from datetime import datetime


def get_schedule_status_tool(client, config):
    """Create get_schedule_status tool function"""
    
    def get_schedule_status() -> str:
        """Get the current status of all scheduled data collection services."""
        try:
            schedule_config = ScheduleConfig()
            
            # Validate configuration
            if not schedule_config.validate_config():
                return create_error_response("Schedule configuration is invalid")
            
            # Get status for all services
            status_data = {
                "configuration": {
                    "config_file": schedule_config.config_path,
                    "enabled_services": schedule_config.get_enabled_services(),
                    "valid": schedule_config.validate_config()
                },
                "global_schedule": {
                    "schedule": schedule_config.get_global_schedule(),
                    "services_using_global": schedule_config.services_using_global_schedule(),
                    "services_using_individual": schedule_config.services_using_individual_schedule()
                },
                "ai_summary_config": {
                    "enabled": schedule_config.config.get('ai_summary', {}).get('enabled', False),
                    "slack_analysis": schedule_config.config.get('ai_summary', {}).get('slack_analysis', False),
                    "jira_analysis": schedule_config.config.get('ai_summary', {}).get('jira_analysis', False),
                    "email_summary": schedule_config.config.get('ai_summary', {}).get('email_summary', False)
                },
                "services": {},
                "teams": {},
                "timing": {
                    "next_run_times": schedule_config.get_next_run_times(),
                    "current_time": datetime.now().isoformat()
                }
            }
            
            # Get status for each service
            for service in schedule_config.get_enabled_services():
                service_config = schedule_config.config.get(service, {})
                service_status = {
                    "enabled": schedule_config.is_enabled(service),
                    "configured": schedule_config.has_service_config(service),
                    "schedule_type": "global" if service_config.get('global_schedule', False) else "individual",
                    "schedule": schedule_config.get_schedule(service),
                    "next_run": schedule_config.get_next_run_times().get(service, 'unknown')
                }
                
                # Add service-specific configuration
                if service == 'ai_summary':
                    service_status.update({
                        "slack_analysis": service_config.get('slack_analysis', False),
                        "jira_analysis": service_config.get('jira_analysis', False),
                        "email_summary": service_config.get('email_summary', False)
                    })
                else:
                    # For slack and jira, add team information
                    teams = schedule_config.get_teams(service)
                    service_status["teams_count"] = len(teams)
                    status_data["teams"][service] = teams
                
                status_data["services"][service] = service_status
            
            return create_success_response(status_data)
            
        except Exception as e:
            return create_error_response("Failed to get schedule status", str(e))
    
    return get_schedule_status