"""
Gemini AI Tools
MCP tools for AI-powered analysis and summarization
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_team_name
from ..client import GeminiClient
from ..config import GeminiConfig
import json
import os


def analyze_slack_data_tool(client, config):
    """Create analyze_slack_data tool function"""
    
    def analyze_slack_data(team: str, analysis_type: str = "summary") -> str:
        """Analyze Slack data for a team using Gemini AI."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Initialize Gemini client
            gemini_config = GeminiConfig()
            gemini_client = GeminiClient(gemini_config.get_config())
            
            # Get team's Slack data (this would need to be implemented)
            # For now, we'll use a placeholder
            slack_data = {
                "team": validated_team,
                "channels": [],
                "messages": [],
                "note": "Slack data integration needed"
            }
            
            # Analyze data using Gemini
            analysis_result = gemini_client.analyze_slack_data(slack_data, analysis_type)
            
            return create_success_response({
                "team": validated_team,
                "analysis_type": analysis_type,
                "analysis_result": analysis_result,
                "model_info": gemini_client.get_model_info()
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to analyze Slack data", str(e))
    
    return analyze_slack_data


def analyze_jira_data_tool(client, config):
    """Create analyze_jira_data tool function"""
    
    def analyze_jira_data(team: str, analysis_type: str = "summary") -> str:
        """Analyze Jira data for a team using Gemini AI."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Initialize Gemini client
            gemini_config = GeminiConfig()
            gemini_client = GeminiClient(gemini_config.get_config())
            
            # Get team's Jira data (this would need to be implemented)
            # For now, we'll use a placeholder
            jira_data = {
                "team": validated_team,
                "issues": [],
                "projects": [],
                "note": "Jira data integration needed"
            }
            
            # Analyze data using Gemini
            analysis_result = gemini_client.analyze_jira_data(jira_data, analysis_type)
            
            return create_success_response({
                "team": validated_team,
                "analysis_type": analysis_type,
                "analysis_result": analysis_result,
                "model_info": gemini_client.get_model_info()
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to analyze Jira data", str(e))
    
    return analyze_jira_data


def generate_email_summary_tool(client, config):
    """Create generate_email_summary tool function"""
    
    def generate_email_summary(team: str) -> str:
        """Generate email summary combining Slack and Jira data using Gemini AI."""
        try:
            # Input validation
            validated_team = validate_team_name(team)
            
            # Initialize Gemini client
            gemini_config = GeminiConfig()
            gemini_client = GeminiClient(gemini_config.get_config())
            
            # Get team's data (this would need to be implemented)
            # For now, we'll use placeholders
            slack_data = {
                "team": validated_team,
                "channels": [],
                "messages": [],
                "note": "Slack data integration needed"
            }
            
            jira_data = {
                "team": validated_team,
                "issues": [],
                "projects": [],
                "note": "Jira data integration needed"
            }
            
            # Generate email summary using Gemini
            email_summary = gemini_client.generate_email_summary(slack_data, jira_data)
            
            return create_success_response({
                "team": validated_team,
                "email_summary": email_summary,
                "model_info": gemini_client.get_model_info()
            })
            
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to generate email summary", str(e))
    
    return generate_email_summary


def custom_ai_analysis_tool(client, config):
    """Create custom_ai_analysis tool function"""
    
    def custom_ai_analysis(prompt: str, data: str = "") -> str:
        """Perform custom AI analysis using Gemini with a custom prompt."""
        try:
            # Initialize Gemini client
            gemini_config = GeminiConfig()
            gemini_client = GeminiClient(gemini_config.get_config())
            
            # Prepare context if data is provided
            context = None
            if data:
                try:
                    context = {"custom_data": data}
                except:
                    context = {"custom_data": str(data)}
            
            # Generate analysis using Gemini
            analysis_result = gemini_client.generate_content(prompt, context)
            
            return create_success_response({
                "prompt": prompt,
                "analysis_result": analysis_result,
                "model_info": gemini_client.get_model_info()
            })
            
        except Exception as e:
            return create_error_response("Failed to perform custom AI analysis", str(e))
    
    return custom_ai_analysis
