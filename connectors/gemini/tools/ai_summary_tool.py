"""
AI Summary Tool for Work Planner
Performs scheduled AI analysis using Gemini AI based on schedule.yaml configuration
"""

from utils.responses import create_error_response, create_success_response
import os
import yaml
import json
from datetime import datetime
from typing import Dict, Any, List

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
                slack_results = _analyze_slack_data(client, config, team)
                results["analysis_results"]["slack"] = slack_results
            except Exception as e:
                error_msg = f"Slack analysis failed: {str(e)}"
                results["errors"].append(error_msg)
            
            # Perform Jira analysis
            try:
                jira_results = _analyze_jira_data(client, config, team)
                results["analysis_results"]["jira"] = jira_results
            except Exception as e:
                error_msg = f"Jira analysis failed: {str(e)}"
                results["errors"].append(error_msg)
            
            # Generate email summary if we have data
            email_results = {}
            try:
                if 'slack' in results["analysis_results"] or 'jira' in results["analysis_results"]:
                    email_results = _generate_email_summary(client, config, results["analysis_results"])
                    results["analysis_results"]["email"] = email_results
            except Exception as e:
                error_msg = f"Email summary generation failed: {str(e)}"
                results["errors"].append(error_msg)
            
            # Send email if requested
            email_sent = False
            if send_email and email_results:
                try:
                    email_sent = _send_summary_email(results["analysis_results"], team or "all_teams", email_results)
                    results["email_sent"] = email_sent
                except Exception as e:
                    error_msg = f"Failed to send email: {str(e)}"
                    results["errors"].append(error_msg)
                    results["email_sent"] = False
            
            return create_success_response(results)
            
        except Exception as e:
            return create_error_response("Failed to execute AI summary", str(e))
    
    return ai_summary


def _analyze_slack_data(client, config, team: str = None) -> Dict[str, Any]:
    """Analyze Slack data for a specific team or all teams"""
    try:
        # Load Gemini configuration
        gemini_config = _load_gemini_config()
        
        # Read Slack data
        slack_data = _read_slack_dump_data(team)
        
        # Perform analysis using Gemini prompts
        analysis_results = {}
        
        # Use the prompts from gemini.yaml
        prompts_config = gemini_config.get('prompts', {}).get('slack_analysis', {})
        
        # Summary analysis
        if 'summary' in prompts_config:
            summary_prompt = prompts_config['summary'].format(data=slack_data)
            summary_result = client.generate_content(summary_prompt)
            analysis_results['summary'] = summary_result
        
        # Highlights analysis
        if 'highlights' in prompts_config:
            highlights_prompt = prompts_config['highlights'].format(data=slack_data)
            highlights_result = client.generate_content(highlights_prompt)
            analysis_results['highlights'] = highlights_result
        
        # Action items analysis
        if 'action_items' in prompts_config:
            action_items_prompt = prompts_config['action_items'].format(data=slack_data)
            action_items_result = client.generate_content(action_items_prompt)
            analysis_results['action_items'] = action_items_result
        
        # Blockers analysis
        if 'blockers' in prompts_config:
            blockers_prompt = prompts_config['blockers'].format(data=slack_data)
            blockers_result = client.generate_content(blockers_prompt)
            analysis_results['blockers'] = blockers_result
        
        return {
            "team": team or "all_teams",
            "analysis_types_completed": list(analysis_results.keys()),
            "results": analysis_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise Exception(f"Failed to analyze Slack data: {str(e)}")


def _analyze_jira_data(client, config, team: str = None) -> Dict[str, Any]:
    """Analyze Jira data for a specific team or all teams"""
    try:
        # Load Gemini configuration
        gemini_config = _load_gemini_config()
        
        # Read Jira data
        jira_data = _read_jira_dump_data(team)
        
        # Perform analysis using Gemini prompts
        analysis_results = {}
        
        # Use the prompts from gemini.yaml
        prompts_config = gemini_config.get('prompts', {}).get('jira_analysis', {})
        
        # Summary analysis
        if 'summary' in prompts_config:
            summary_prompt = prompts_config['summary'].format(data=jira_data)
            summary_result = client.generate_content(summary_prompt)
            analysis_results['summary'] = summary_result
        
        # Blockers analysis
        if 'blockers' in prompts_config:
            blockers_prompt = prompts_config['blockers'].format(data=jira_data)
            blockers_result = client.generate_content(blockers_prompt)
            analysis_results['blockers'] = blockers_result
        
        # Progress analysis
        if 'progress' in prompts_config:
            progress_prompt = prompts_config['progress'].format(data=jira_data)
            progress_result = client.generate_content(progress_prompt)
            analysis_results['progress'] = progress_result
        
        return {
            "team": team or "all_teams",
            "analysis_types_completed": list(analysis_results.keys()),
            "results": analysis_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise Exception(f"Failed to analyze Jira data: {str(e)}")


def _generate_email_summary(client, config, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate email summary combining Slack and Jira analysis results"""
    try:
        # Load Gemini configuration
        gemini_config = _load_gemini_config()
        
        # Get the email summary prompt
        email_prompt_template = gemini_config.get('prompts', {}).get('email_summary', '')
        if not email_prompt_template:
            raise Exception("Email summary prompt not found in gemini.yaml")
        
        # Format the prompt with actual analysis data
        email_prompt = email_prompt_template.format(
            slack_data=analysis_results.get('slack', {}).get('results', {}).get('summary', 'No Slack data available'),
            jira_data=analysis_results.get('jira', {}).get('results', {}).get('summary', 'No Jira data available')
        )
        
        # Generate email summary
        email_content = client.generate_content(email_prompt)
        
        return {
            "email_content": email_content,
            "analysis_based_on": list(analysis_results.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise Exception(f"Failed to generate email summary: {str(e)}")


def _load_gemini_config() -> Dict[str, Any]:
    """Load Gemini configuration from gemini.yaml"""
    try:
        config_path = os.path.join('config', 'gemini.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise Exception(f"Failed to load Gemini configuration: {str(e)}")


def _read_slack_dump_data(team: str = None) -> str:
    """Read Slack dump data for analysis"""
    try:
        # Implementation would read from generated Slack dumps
        # For now, return placeholder indicating data source
        return f"Slack analysis data for team: {team or 'all_teams'} - Implementation needed to read actual dump files"
    except Exception as e:
        raise Exception(f"Failed to read Slack dump data: {str(e)}")


def _send_summary_email(analysis_results: Dict[str, Any], team: str, email_results: Dict[str, Any]) -> bool:
    """Send summary email using the email connector with Slack and Jira analysis content"""
    try:
        from connectors.email.client import EmailClient
        from connectors.email.config import EmailConfig
        from datetime import datetime
        
        email_config = EmailConfig()
        email_client = EmailClient(email_config.get_config())
        
        # Extract content from analysis results
        slack_analysis = ""
        jira_analysis = ""
        email_summary = ""
        
        # Extract Slack analysis content
        if 'slack' in analysis_results:
            slack_data = analysis_results['slack']
            results = slack_data.get('results', {})
            
            slack_parts = []
            if results.get('summary'):
                slack_parts.append(f"<p><strong>Summary:</strong> {results['summary']}</p>")
            if results.get('action_items'):
                slack_parts.append(f"<p><strong>Action Items:</strong> {results['action_items']}</p>")
            if results.get('blockers'):
                slack_parts.append(f"<p><strong>Blockers:</strong> {results['blockers']}</p>")
            
            slack_analysis = "<br>".join(slack_parts) if slack_parts else "<p>No Slack analysis available</p>"
        
        # Extract Jira analysis content  
        if 'jira' in analysis_results:
            jira_data = analysis_results['jira']
            results = jira_data.get('results', {})
            
            jira_parts = []
            if results.get('summary'):
                jira_parts.append(f"<p><strong>Summary:</strong> {results['summary']}</p>")
            if results.get('blockers'):
                jira_parts.append(f"<p><strong>Blockers:</strong> {results['blockers']}</p>")
            if results.get('progress'):
                jira_parts.append(f"<p><strong>Progress:</strong> {results['progress']}</p>")
                
            jira_analysis = "<br>".join(jira_parts) if jira_parts else "<p>No Jira analysis available</p>"
        
        # Extract final email summary
        email_summary = email_results.get('email_content', f"Daily summary for team {team}")
        
        # Prepare content for email template
        summary_data = {
            'slack_analysis': slack_analysis,
            'jira_analysis': jira_analysis,
            'email_summary': email_summary,
            'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        # Send email using simplified configuration
        result = email_client.send_daily_summary(team, summary_data)
        
        if result['success']:
            print(f"✅ Daily summary email sent successfully to team {team}")
            print(f"📧 Recipients: {', '.join(result['recipients'])}")
            return True
        else:
            print(f"❌ Failed to send daily summary email: {result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ Error sending summary email: {str(e)}")
    return False


def _read_jira_dump_data(team: str = None) -> str:
    """Read Jira dump data for analysis"""
    try:
        if not team:
            return "[JIRA DATA] Multiple team dumps available; use dump_jira_team_data tool first"
        
        # Try to read actual Jira dump files if they exist
        dump_dir = "jira_dumps"
        tickets_filter = "All In Progress"  # Default filter from schedule.yaml
        
        # Try JSON format first (preferred for structured data)
        json_filename = f"{team}_{tickets_filter.lower().replace(' ', '_')}_jira_dump.json"
        json_filepath = os.path.join(dump_dir, json_filename)
        
        if os.path.exists(json_filepath):
            with open(json_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Format for AI analysis
            issues_text = f"[JIRA DATA] Team: {team}\n"
            issues_text += f"Filter: {tickets_filter}\n"
            issues_text += f"Total Issues: {data.get('total_issues', 0)}\n"
            issues_text += f"Generated: {data.get('generated', 'Unknown')}\n\n"
            
            for issue in data.get('issues', []):
                issues_text += f"Issue: {issue.get('key', 'N/A')}\n"
                issues_text += f"Title: {issue.get('summary', 'No summary')}\n"
                issues_text += f"Status: { issue.get('status', 'Unknown')}\n"
                issues_text += f"Type: {issue.get('type', 'Unknown')}\n"
                issues_text += f"Priority: {issue.get('priority', 'Unknown')}\n"
                issues_text += f"Assignee: {issue.get('assignee', {}).get('name', 'Unassigned')}\n"
                issues_text += f"Reporter: {issue.get('reporter', {}).get('name', 'Unknown')}\n"
                issues_text += f"Created: {issue.get('created', 'Unknown')}\n"
                issues_text += f"Updated: {issue.get('updated', 'Unknown')}\n"
                issues_text += f"Description: {issue.get('description', 'No description')[:200]}{'...' if len(issue.get('description', '')) > 200 else ''}\n\n"
            
            return issues_text
        
        # Try text format as fallback
        txt_filename = f"{team}_{tickets_filter.lower().replace(' ', '_')}_jira_dump.txt"
        txt_filepath = os.path.join(dump_dir, txt_filename)
        
        if os.path.exists(txt_filepath):
            with open(txt_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return f"[JIRA DATA] Team: {team}\n\n" + content
        
        # No dump file found
        return f"[JIRA DATA] No dump file found for team '{team}'. Please use dump_jira_team_data tool first to collect current data."
        
    except Exception as e:
        return f"[JIRA DATA] Error reading dump for team '{team}': {str(e)}. Use dump_jira_team_data tool first."
        # Implementation would read from generated Jira dumps
        # For now, return placeholder indicating data source
        return f"Jira analysis data for team: {team or 'all_teams'} - Implementation needed to read actual issue dumps"
    except Exception as e:
        raise Exception(f"Failed to read Jira dump data: {str(e)}")
