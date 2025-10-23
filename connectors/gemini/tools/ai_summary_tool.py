"""
AI Summary Tool for Work Planner
Performs scheduled AI analysis using Gemini AI based on schedule.yaml configuration
"""

from utils.responses import create_error_response, create_success_response
from .gemini_helpers import (
    analyze_slack_data,
    analyze_jira_data,
    generate_email_summary,
    send_summary_email
)
from datetime import datetime


def ai_summary_tool(client, config):
    """Create ai_summary tool function"""
    
    def ai_summary(team: str = None, send_email: bool = False) -> str:
        """Execute AI summary analysis based on schedule.yaml configuration.
        
        Args:
            team: Team name for analysis (e.g., toolchain, foa, assessment, boa)
            send_email: Whether to send the summary via email automatically
        """
        try:
            # AI Summary is always enabled for GitHub Actions workflow
            # Results container
            results = {
                "team": team or "all_teams",
                "timestamp": datetime.now().isoformat(),
                "analysis_results": {},
                "errors": []
            }
            
            # Perform Slack analysis
            try:
                slack_results = analyze_slack_data(client, config, team)
                results["analysis_results"]["slack"] = slack_results
            except Exception as e:
                error_msg = f"Slack analysis failed: {str(e)}"
                results["errors"].append(error_msg)
            
            # Perform Jira analysis
            try:
                jira_results = analyze_jira_data(client, config, team)
                results["analysis_results"]["jira"] = jira_results
            except Exception as e:
                error_msg = f"Jira analysis failed: {str(e)}"
                results["errors"].append(error_msg)
            
            # Generate email summary if we have data
            email_results = {}
            try:
                if 'slack' in results["analysis_results"] or 'jira' in results["analysis_results"]:
                    email_results = generate_email_summary(client, config, results["analysis_results"])
                    results["analysis_results"]["email"] = email_results
            except Exception as e:
                error_msg = f"Email summary generation failed: {str(e)}"
                results["errors"].append(error_msg)
            
            # Send email if requested
            email_sent = False
            if send_email and email_results:
                try:
                    email_sent = send_summary_email(results["analysis_results"], team or "all_teams", email_results)
                    results["email_sent"] = email_sent
                except Exception as e:
                    error_msg = f"Failed to send email: {str(e)}"
                    results["errors"].append(error_msg)
                    results["email_sent"] = False
            
            return create_success_response(results)
            
        except Exception as e:
            return create_error_response("Failed to execute AI summary", str(e))
    
    return ai_summary
