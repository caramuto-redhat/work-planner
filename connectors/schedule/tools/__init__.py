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
            
            # Get enabled services
            enabled_services = schedule_config.get_enabled_services()
            
            # Get next run times
            next_runs = schedule_config.get_next_run_times()
            
            # Get team configurations
            teams_by_service = {}
            for service in ['slack', 'jira', 'ai_analysis', 'email_summary']:
                teams_by_service[service] = schedule_config.get_teams(service)
            
            # Get global settings
            global_config = schedule_config.get_global_config()
            
            return create_success_response({
                "schedule_status": "active",
                "enabled_services": enabled_services,
                "next_run_times": next_runs,
                "teams_by_service": teams_by_service,
                "global_settings": global_config,
                "timezone": schedule_config.get_timezone(),
                "retention_days": schedule_config.get_retention_days(),
                "max_age_hours": schedule_config.get_max_age_hours(),
                "config_valid": schedule_config.validate_config()
            })
            
        except Exception as e:
            return create_error_response("Failed to get schedule status", str(e))
    
    return get_schedule_status


def run_scheduled_collection_tool(client, config):
    """Create run_scheduled_collection tool function"""
    
    def run_scheduled_collection(service: str = "all", team: str = None) -> str:
        """
        Run scheduled data collection for a specific service or all services.
        
        Args:
            service: Service to run (slack, jira, ai_analysis, email_summary, all)
            team: Optional team name to limit collection to specific team
        """
        try:
            schedule_config = ScheduleConfig()
            
            if not schedule_config.validate_config():
                return create_error_response("Schedule configuration is invalid")
            
            results = {}
            errors = []
            
            # Determine which services to run
            if service == "all":
                services_to_run = schedule_config.get_enabled_services()
            else:
                if not schedule_config.is_enabled(service):
                    return create_error_response(f"Service '{service}' is not enabled")
                services_to_run = [service]
            
            # Run each service
            for svc in services_to_run:
                try:
                    result = _run_service_collection(svc, team, schedule_config)
                    results[svc] = result
                except Exception as e:
                    error_msg = f"Error running {svc}: {str(e)}"
                    errors.append(error_msg)
                    results[svc] = {"error": error_msg}
            
            return create_success_response({
                "service": service,
                "team": team,
                "services_run": services_to_run,
                "results": results,
                "errors": errors,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return create_error_response("Failed to run scheduled collection", str(e))
    
    return run_scheduled_collection


def update_schedule_config_tool(client, config):
    """Create update_schedule_config tool function"""
    
    def update_schedule_config(service: str, setting: str, value: str) -> str:
        """
        Update schedule configuration for a specific service.
        
        Args:
            service: Service name (slack, jira, ai_analysis, email_summary, global)
            setting: Setting name to update
            value: New value for the setting
            
        Examples:
            - update_schedule_config('slack', 'include_attachments', 'true')
            - update_schedule_config('slack', 'enabled', 'false')
            - update_schedule_config('global', 'timezone', 'EST')
        """
        try:
            schedule_config = ScheduleConfig()
            
            # Validate service
            valid_services = ['slack', 'jira', 'ai_analysis', 'email_summary', 'cleanup', 'notifications', 'global']
            if service not in valid_services:
                return create_error_response(f"Invalid service '{service}'. Valid services: {valid_services}")
            
            # Update the configuration
            if service not in schedule_config.config:
                schedule_config.config[service] = {}
            
            # Handle different value types
            if value.lower() in ['true', 'false']:
                schedule_config.config[service][setting] = value.lower() == 'true'
            elif value.isdigit():
                schedule_config.config[service][setting] = int(value)
            else:
                schedule_config.config[service][setting] = value
            
            # Save the updated configuration
            import yaml
            with open(schedule_config.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(schedule_config.config, f, default_flow_style=False, indent=2)
            
            return create_success_response({
                "service": service,
                "setting": setting,
                "value": schedule_config.config[service][setting],
                "config_updated": True,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return create_error_response("Failed to update schedule config", str(e))
    
    return update_schedule_config


def add_team_to_schedule_tool(client, config):
    """Create add_team_to_schedule tool function"""
    
    def add_team_to_schedule(service: str, team_name: str, max_age_hours: int = 24, channels: str = "all", jql_query: str = "", analysis_types: str = "summary", combine_slack_jira: bool = True, recipients: str = "", include_analysis: bool = True) -> str:
        """
        Add a team to the schedule configuration for a specific service.
        
        Args:
            service: Service name (slack, jira, ai_analysis, email_summary)
            team_name: Name of the team to add
            max_age_hours: Maximum age in hours before forcing fresh data
            channels: Channels to include (for slack service)
            jql_query: JQL query for jira service
            analysis_types: Comma-separated analysis types for ai_analysis service
            combine_slack_jira: Whether to combine Slack and Jira data for ai_analysis
            recipients: Comma-separated email recipients for email_summary service
            include_analysis: Whether to include analysis in email_summary
        """
        try:
            # Validate team name
            validated_team = validate_team_name(team_name)
            
            # Validate service
            valid_services = ['slack', 'jira', 'ai_analysis', 'email_summary']
            if service not in valid_services:
                return create_error_response(f"Invalid service '{service}'. Valid services: {valid_services}")
            
            schedule_config = ScheduleConfig()
            
            # Check if team already exists
            existing_teams = schedule_config.get_teams(service)
            if any(team.get('name') == validated_team for team in existing_teams):
                return create_error_response(f"Team '{validated_team}' already exists in {service} schedule")
            
            # Create team configuration
            team_config = {
                "name": validated_team,
                "max_age_hours": max_age_hours
            }
            
            # Add service-specific configuration
            if service == 'slack':
                team_config["channels"] = channels
            elif service == 'jira':
                team_config["jql_query"] = jql_query or f'project = "AUTO" AND team = "{validated_team}"'
            elif service == 'ai_analysis':
                team_config["analysis_types"] = analysis_types.split(',') if analysis_types else ['summary']
                team_config["combine_slack_jira"] = combine_slack_jira
            elif service == 'email_summary':
                team_config["recipients"] = recipients.split(',') if recipients else []
                team_config["include_analysis"] = include_analysis
            
            # Add team to configuration
            if service not in schedule_config.config:
                schedule_config.config[service] = {"enabled": True, "teams": []}
            
            schedule_config.config[service]["teams"].append(team_config)
            
            # Save the updated configuration
            import yaml
            with open(schedule_config.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(schedule_config.config, f, default_flow_style=False, indent=2)
            
            return create_success_response({
                "service": service,
                "team": validated_team,
                "team_config": team_config,
                "added": True,
                "timestamp": datetime.now().isoformat()
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to add team to schedule", str(e))
    
    return add_team_to_schedule


def remove_team_from_schedule_tool(client, config):
    """Create remove_team_from_schedule tool function"""
    
    def remove_team_from_schedule(service: str, team_name: str) -> str:
        """
        Remove a team from the schedule configuration for a specific service.
        
        Args:
            service: Service name (slack, jira, ai_analysis, email_summary)
            team_name: Name of the team to remove
        """
        try:
            # Validate team name
            validated_team = validate_team_name(team_name)
            
            # Validate service
            valid_services = ['slack', 'jira', 'ai_analysis', 'email_summary']
            if service not in valid_services:
                return create_error_response(f"Invalid service '{service}'. Valid services: {valid_services}")
            
            schedule_config = ScheduleConfig()
            
            # Find and remove the team
            teams = schedule_config.get_teams(service)
            original_count = len(teams)
            
            schedule_config.config[service]["teams"] = [
                team for team in teams if team.get('name') != validated_team
            ]
            
            removed_count = original_count - len(schedule_config.config[service]["teams"])
            
            if removed_count == 0:
                return create_error_response(f"Team '{validated_team}' not found in {service} schedule")
            
            # Save the updated configuration
            import yaml
            with open(schedule_config.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(schedule_config.config, f, default_flow_style=False, indent=2)
            
            return create_success_response({
                "service": service,
                "team": validated_team,
                "removed": True,
                "teams_remaining": len(schedule_config.config[service]["teams"]),
                "timestamp": datetime.now().isoformat()
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to remove team from schedule", str(e))
    
    return remove_team_from_schedule


def toggle_slack_attachments_tool(client, config):
    """Create toggle_slack_attachments tool function"""
    
    def toggle_slack_attachments(enable: bool = None) -> str:
        """
        Toggle whether to include Slack file attachments in scheduled dumps.
        
        Args:
            enable: True to enable attachments, False to disable, None to toggle current setting
        """
        try:
            schedule_config = ScheduleConfig()
            
            # Get current setting
            current_setting = schedule_config.get_include_attachments()
            
            if enable is None:
                # Toggle current setting
                new_setting = not current_setting
            else:
                new_setting = enable
            
            # Update the configuration
            if 'slack' not in schedule_config.config:
                schedule_config.config['slack'] = {}
            
            schedule_config.config['slack']['include_attachments'] = new_setting
            
            # Save the updated configuration
            import yaml
            with open(schedule_config.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(schedule_config.config, f, default_flow_style=False, indent=2)
            
            action = "toggled" if enable is None else "set"
            status = "enabled" if new_setting else "disabled"
            
            return create_success_response({
                "action": action,
                "previous_setting": current_setting,
                "new_setting": new_setting,
                "status": status,
                "slack_attachments": new_setting,
                "config_updated": True,
                "next_scheduled_run": schedule_config.get_next_run_times().get('slack', 'unknown'),
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return create_error_response("Failed to toggle Slack attachments setting", str(e))
    
    return toggle_slack_attachments


# Helper function for running service collection
def _run_service_collection(service: str, team: str, schedule_config: ScheduleConfig) -> dict:
    """Run data collection for a specific service"""
    
    if service == "slack":
        # Import and run Slack collection
        from ..slack.tools.unified_slack_tools import dump_slack_data_tool
        from ..slack.client import SlackClient
        from ..slack.config import SlackConfig
        
        slack_config = SlackConfig.load('config/slack.yaml')
        slack_client = SlackClient(slack_config)
        
        # Check if attachments should be included
        include_attachments = schedule_config.get_include_attachments()
        if include_attachments:
            # Add attachment configuration to slack config for the session
            slack_config.config['data_collection'] = slack_config.config.get('data_collection', {})
            slack_config.config['data_collection']['attachments_directory'] = 'connectors/slack/slack_dump/slack_attachments'
        
        dump_tool = dump_slack_data_tool(slack_client, slack_config)
        
        teams_to_process = [team] if team else [t['name'] for t in schedule_config.get_teams('slack')]
        
        results = {}
        for team_name in teams_to_process:
            result = dump_tool(team_name)
            results[team_name] = json.loads(result)
        
        return {
            "service": "slack", 
            "teams_processed": teams_to_process, 
            "results": results,
            "include_attachments": include_attachments
        }
    
    elif service == "jira":
        # Import and run Jira collection
        from ..jira.tools.search_issues import search_issues_tool
        from ..jira.client import JiraClient
        from ..jira.config import JiraConfig
        
        jira_config = JiraConfig.load('config/jira.yaml')
        jira_client = JiraClient(jira_config)
        search_tool = search_issues_tool(jira_client, jira_config)
        
        teams_to_process = [team] if team else [t['name'] for t in schedule_config.get_teams('jira')]
        
        results = {}
        for team_name in teams_to_process:
            team_config = schedule_config.get_team_config('jira', team_name)
            if team_config:
                jql_query = team_config.get('jql_query', f'project = "AUTO" AND team = "{team_name}"')
                result = search_tool(jql_query, max_results=1000)
                results[team_name] = json.loads(result)
        
        return {"service": "jira", "teams_processed": teams_to_process, "results": results}
    
    elif service == "ai_analysis":
        # Import and run AI analysis
        from ..gemini.tools import analyze_slack_data_tool, analyze_jira_data_tool
        from ..gemini.client import GeminiClient
        from ..gemini.config import GeminiConfig
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        
        teams_to_process = [team] if team else [t['name'] for t in schedule_config.get_teams('ai_analysis')]
        
        results = {}
        for team_name in teams_to_process:
            team_config = schedule_config.get_team_config('ai_analysis', team_name)
            if team_config:
                analysis_types = team_config.get('analysis_types', ['summary'])
                team_results = {}
                
                for analysis_type in analysis_types:
                    slack_analysis_tool = analyze_slack_data_tool(gemini_client, gemini_config.get_config())
                    slack_result = slack_analysis_tool(team_name, analysis_type)
                    team_results[f"slack_{analysis_type}"] = json.loads(slack_result)
                    
                    if team_config.get('combine_slack_jira', False):
                        jira_analysis_tool = analyze_jira_data_tool(gemini_client, gemini_config.get_config())
                        jira_result = jira_analysis_tool(team_name, analysis_type)
                        team_results[f"jira_{analysis_type}"] = json.loads(jira_result)
                
                results[team_name] = team_results
        
        return {"service": "ai_analysis", "teams_processed": teams_to_process, "results": results}
    
    elif service == "email_summary":
        # Import and run email summary generation
        from ..gemini.tools import generate_email_summary_tool
        from ..gemini.client import GeminiClient
        from ..gemini.config import GeminiConfig
        
        gemini_config = GeminiConfig()
        gemini_client = GeminiClient(gemini_config.get_config())
        
        teams_to_process = [team] if team else [t['name'] for t in schedule_config.get_teams('email_summary')]
        
        results = {}
        for team_name in teams_to_process:
            team_config = schedule_config.get_team_config('email_summary', team_name)
            if team_config:
                email_tool = generate_email_summary_tool(gemini_client, gemini_config.get_config())
                result = email_tool(team_name)
                results[team_name] = json.loads(result)
        
        return {"service": "email_summary", "teams_processed": teams_to_process, "results": results}
    
    else:
        raise ValueError(f"Unknown service: {service}")
