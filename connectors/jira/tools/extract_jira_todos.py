"""
Jira TODO Extraction Tool
MCP tool for extracting actionable TODO items from Jira issues and comments using Gemini AI
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from utils.responses import create_error_response, create_success_response
from connectors.gemini.client import GeminiClient


def extract_jira_todos_tool(jira_client, jira_config: Dict[str, Any], gemini_config_dict: Dict[str, Any]):
    """Create extract_jira_todos tool function"""
    
    def extract_jira_todos(
        team: Optional[str] = None,
        include_assigned: bool = True,
        include_comments: bool = True,
        days_back: int = 30
    ) -> str:
        """
        Extract actionable TODO items from Jira issues and comments using Gemini AI natural language understanding.
        
        Analyzes Jira issues, descriptions, and comments to identify tasks requiring action,
        including @mentions, blockers, review requests, and implicit action items.
        
        Args:
            team: Team name to filter issues (optional, analyzes all teams if not specified)
            include_assigned: Include assigned issues (default: True)
            include_comments: Analyze issue comments for TODOs (default: True)
            days_back: Number of days to look back for updated issues (default: 30)
            
        Returns:
            JSON response with extracted TODO items, urgency, deadlines, and context
            
        Example:
            extract_jira_todos(team="toolchain", days_back=30)
        """
        try:
            print(f"\n🎫 Starting Jira TODO extraction...")
            if team:
                print(f"   Team: {team}")
            print(f"   Days back: {days_back}")
            
            # Get TODO extraction configuration
            todo_config = gemini_config_dict.get('todo_extraction', {})
            if not todo_config.get('enabled', False):
                return create_error_response(
                    "TODO extraction disabled",
                    "todo_extraction.enabled is false in gemini.yaml"
                )
            
            jira_source_config = todo_config.get('sources', {}).get('jira', {})
            if not jira_source_config.get('enabled', True):
                return create_error_response(
                    "Jira TODO extraction disabled",
                    "todo_extraction.sources.jira.enabled is false in gemini.yaml"
                )
            
            # Build JQL query
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            if team:
                # Resolve team alias
                resolved_team = jira_client.resolve_team_alias(team)
                if resolved_team not in jira_config.get("teams", {}):
                    return create_error_response(
                        "Team not found",
                        f"Team '{team}' not found (resolved to '{resolved_team}')"
                    )
                
                team_config = jira_config["teams"][resolved_team]
                project = team_config["project"]
                jql = f'project = "{project}" AND updated >= "{since_date}"'
            else:
                # All projects
                jql = f'updated >= "{since_date}"'
            
            jql += ' ORDER BY updated DESC'
            
            # Fetch issues
            print(f"📥 Fetching Jira issues...")
            max_results = 100
            issues = jira_client.search_issues(jql, max_results=max_results)
            
            if not issues:
                return create_success_response({
                    'issues_analyzed': 0,
                    'todos_found': 0,
                    'todos': [],
                    'message': 'No Jira issues found in the specified time range'
                })
            
            print(f"✅ Fetched {len(issues)} issues")
            
            # Initialize Gemini client for TODO extraction
            todo_model_config = {
                'model': todo_config.get('model', 'models/gemini-2.0-flash'),
                'generation_config': {
                    'temperature': todo_config.get('temperature', 0.3),
                    'top_p': 0.9,
                    'top_k': 40,
                    'max_output_tokens': todo_config.get('max_output_tokens', 2000)
                }
            }
            gemini_client = GeminiClient(todo_model_config)
            
            # Get prompts
            prompts = todo_config.get('prompts', {})
            system_prompt = prompts.get('system_prompt', '')
            jira_prompt_template = prompts.get('jira_prompt', '')
            
            # Extract TODOs from each issue
            print(f"🤖 Analyzing Jira issues for TODOs using Gemini AI...")
            all_todos = []
            confidence_threshold = todo_config.get('detection', {}).get('confidence_threshold', 0.6)
            max_todos_per_issue = todo_config.get('detection', {}).get('max_todos_per_item', 3)
            priority_weight = jira_source_config.get('priority_weight', 1.0)
            
            analyze_descriptions = jira_source_config.get('analyze_descriptions', True)
            
            for idx, issue in enumerate(issues, 1):
                try:
                    # Get issue details
                    issue_key = issue.get('key', 'Unknown')
                    issue_summary = issue.get('summary', 'No summary')
                    issue_status = issue.get('status', 'Unknown')
                    assignee = issue.get('assignee', 'Unassigned')
                    priority = issue.get('priority', 'None')
                    issue_url = issue.get('url', '')
                    
                    # Get description
                    description = issue.get('description', 'No description')
                    if not description or description == 'No description':
                        description = 'No description provided'
                    # Handle description being a dict or other complex type
                    if isinstance(description, dict):
                        description = str(description)
                    
                    # Get comments
                    comments_text = "No comments"
                    if include_comments:
                        comments_field = issue.get('comment', {})
                        if isinstance(comments_field, dict) and 'comments' in comments_field:
                            comments_list = comments_field.get('comments', [])
                            if comments_list:
                                # Format recent comments
                                recent_comments = comments_list[-5:]  # Last 5 comments
                                comments_formatted = []
                                for comment in recent_comments:
                                    author = comment.get('author', {}).get('displayName', 'Unknown')
                                    body = comment.get('body', '')
                                    if isinstance(body, dict):
                                        body = str(body)
                                    comments_formatted.append(f"- {author}: {body[:200]}")
                                comments_text = '\n'.join(comments_formatted)
                    
                    # Build Jira prompt
                    jira_prompt = jira_prompt_template.format(
                        issue_key=issue_key,
                        issue_summary=issue_summary,
                        issue_status=issue_status,
                        assignee=assignee,
                        priority=priority,
                        description=str(description)[:1000] if analyze_descriptions else 'Description analysis disabled',
                        comments=comments_text[:1000]
                    )
                    
                    # Combine system prompt and jira prompt
                    full_prompt = f"{system_prompt}\n\n{jira_prompt}"
                    
                    # Get Gemini analysis
                    response = gemini_client.generate_content(full_prompt)
                    
                    # Parse JSON response
                    try:
                        # Clean response (remove markdown code blocks if present)
                        response_cleaned = response.strip()
                        if response_cleaned.startswith('```json'):
                            response_cleaned = response_cleaned[7:]
                        if response_cleaned.startswith('```'):
                            response_cleaned = response_cleaned[3:]
                        if response_cleaned.endswith('```'):
                            response_cleaned = response_cleaned[:-3]
                        response_cleaned = response_cleaned.strip()
                        
                        todos = json.loads(response_cleaned)
                        
                        if not isinstance(todos, list):
                            print(f"  ⚠️  Issue {idx}/{len(issues)} ({issue_key}): Invalid response format (not a list)")
                            continue
                        
                        # Filter by confidence and limit
                        filtered_todos = [
                            todo for todo in todos 
                            if float(todo.get('confidence', 0)) >= confidence_threshold
                        ][:max_todos_per_issue]
                        
                        # Add metadata and apply priority weight
                        for todo in filtered_todos:
                            todo['source'] = 'jira'
                            todo['metadata'] = {
                                'issue_key': issue_key,
                                'issue_link': issue_url,
                                'issue_status': issue_status,
                                'assignee': assignee,
                                'priority': priority
                            }
                            # Apply priority weight if urgency is specified
                            if 'urgency' in todo:
                                todo['original_urgency'] = todo['urgency']
                                todo['priority_weight'] = priority_weight
                        
                        all_todos.extend(filtered_todos)
                        
                        if filtered_todos:
                            print(f"  ✅ Issue {idx}/{len(issues)} ({issue_key}): Found {len(filtered_todos)} TODO(s)")
                        else:
                            print(f"  ⚪ Issue {idx}/{len(issues)} ({issue_key}): No TODOs")
                    
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️  Issue {idx}/{len(issues)} ({issue_key}): Failed to parse JSON response: {e}")
                        continue
                
                except Exception as e:
                    print(f"  ❌ Issue {idx}/{len(issues)}: Analysis failed: {e}")
                    continue
            
            # Sort by urgency and confidence
            urgency_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            all_todos.sort(
                key=lambda x: (
                    urgency_order.get(x.get('urgency', 'low'), 4),
                    -float(x.get('confidence', 0))
                )
            )
            
            print(f"\n✅ Jira TODO extraction complete!")
            print(f"   📊 Issues analyzed: {len(issues)}")
            print(f"   📋 TODOs found: {len(all_todos)}")
            
            return create_success_response({
                'issues_analyzed': len(issues),
                'todos_found': len(all_todos),
                'todos': all_todos,
                'analysis_period': f'Last {days_back} days',
                'team': team or 'All teams',
                'confidence_threshold': confidence_threshold,
                'priority_weight': priority_weight
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Jira TODO extraction failed: {e}")
            return create_error_response(
                "Jira TODO extraction failed",
                f"{str(e)}\n\n{error_details}"
            )
    
    return extract_jira_todos

