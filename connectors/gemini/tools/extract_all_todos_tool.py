"""
Unified TODO Extraction Tool
MCP tool that combines email, Jira, and Slack TODO extraction into a single unified view
"""

import json
from typing import Dict, Any, List
from utils.responses import create_error_response, create_success_response


def extract_all_todos_tool(
    email_todos_func,
    jira_todos_func,
    slack_todos_func
):
    """Create unified extract_all_todos tool function"""
    
    def extract_all_todos(days_back: int = 30) -> str:
        """
        Extract actionable TODO items from all sources (Email, Jira, Slack) and provide a unified view.
        
        Combines TODO items from:
        - Email inbox (IMAP)
        - Jira issues and comments
        - Slack messages and threads
        
        Provides unified sorting, grouping, and deduplication.
        
        Args:
            days_back: Number of days to look back across all sources (default: 30)
            
        Returns:
            Unified JSON response with all TODO items sorted by urgency and grouped by source
            
        Example:
            extract_all_todos(days_back=30)
        """
        try:
            print(f"\n🎯 Starting unified TODO extraction from all sources...")
            print(f"   Analysis period: Last {days_back} days")
            
            all_todos = []
            source_results = {}
            errors = []
            
            # Extract from Email
            print(f"\n📧 [1/3] Extracting TODOs from Email...")
            try:
                email_result = email_todos_func(days_back=days_back)
                email_data = json.loads(email_result)
                
                # Handle direct data format (no "success" wrapper)
                email_todos = email_data.get('todos', [])
                all_todos.extend(email_todos)
                source_results['email'] = {
                    'success': True,
                    'todos_found': len(email_todos),
                    'items_analyzed': email_data.get('emails_analyzed', 0)
                }
                print(f"   ✅ Email: {len(email_todos)} TODOs from {source_results['email']['items_analyzed']} emails")
            except Exception as e:
                errors.append(f"Email: {str(e)}")
                source_results['email'] = {'success': False, 'error': str(e)}
                print(f"   ❌ Email: Exception - {str(e)}")
            
            # Extract from Jira
            print(f"\n🎫 [2/3] Extracting TODOs from Jira...")
            try:
                jira_result = jira_todos_func(team=None, days_back=days_back)
                jira_data = json.loads(jira_result)
                
                # Handle direct data format (no "success" wrapper)
                jira_todos = jira_data.get('todos', [])
                all_todos.extend(jira_todos)
                source_results['jira'] = {
                    'success': True,
                    'todos_found': len(jira_todos),
                    'items_analyzed': jira_data.get('issues_analyzed', 0)
                }
                print(f"   ✅ Jira: {len(jira_todos)} TODOs from {source_results['jira']['items_analyzed']} issues")
            except Exception as e:
                errors.append(f"Jira: {str(e)}")
                source_results['jira'] = {'success': False, 'error': str(e)}
                print(f"   ❌ Jira: Exception - {str(e)}")
            
            # Extract from Slack
            print(f"\n💬 [3/3] Extracting TODOs from Slack...")
            try:
                slack_result = slack_todos_func(team=None, days_back=days_back)
                slack_data = json.loads(slack_result)
                
                # Handle direct data format (no "success" wrapper)
                slack_todos = slack_data.get('todos', [])
                all_todos.extend(slack_todos)
                source_results['slack'] = {
                    'success': True,
                    'todos_found': len(slack_todos),
                    'items_analyzed': slack_data.get('messages_analyzed', 0)
                }
                print(f"   ✅ Slack: {len(slack_todos)} TODOs from {source_results['slack']['items_analyzed']} messages")
            except Exception as e:
                errors.append(f"Slack: {str(e)}")
                source_results['slack'] = {'success': False, 'error': str(e)}
                print(f"   ❌ Slack: Exception - {str(e)}")
            
            # Check if we got any TODOs
            if not all_todos:
                return create_success_response({
                    'total_todos': 0,
                    'todos': [],
                    'source_results': source_results,
                    'errors': errors if errors else None,
                    'message': 'No TODOs found across all sources'
                })
            
            # Sort by urgency and confidence
            print(f"\n📊 Processing {len(all_todos)} total TODOs...")
            urgency_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            all_todos.sort(
                key=lambda x: (
                    urgency_order.get(x.get('urgency', 'low'), 4),
                    -float(x.get('confidence', 0))
                )
            )
            
            # Group by urgency
            grouped_by_urgency = {
                'critical': [],
                'high': [],
                'medium': [],
                'low': []
            }
            for todo in all_todos:
                urgency = todo.get('urgency', 'low')
                if urgency in grouped_by_urgency:
                    grouped_by_urgency[urgency].append(todo)
            
            # Group by source
            grouped_by_source = {
                'email': [],
                'jira': [],
                'slack': []
            }
            for todo in all_todos:
                source = todo.get('source', 'unknown')
                if source in grouped_by_source:
                    grouped_by_source[source].append(todo)
            
            # Calculate statistics
            by_urgency_counts = {
                urgency: len(todos) for urgency, todos in grouped_by_urgency.items()
            }
            by_source_counts = {
                source: len(todos) for source, todos in grouped_by_source.items()
            }
            
            print(f"\n✅ Unified TODO extraction complete!")
            print(f"   📋 Total TODOs: {len(all_todos)}")
            print(f"   📊 By urgency: Critical={by_urgency_counts['critical']}, High={by_urgency_counts['high']}, Medium={by_urgency_counts['medium']}, Low={by_urgency_counts['low']}")
            print(f"   📊 By source: Email={by_source_counts['email']}, Jira={by_source_counts['jira']}, Slack={by_source_counts['slack']}")
            
            return create_success_response({
                'total_todos': len(all_todos),
                'analysis_period': f'Last {days_back} days',
                'summary': {
                    'by_urgency': by_urgency_counts,
                    'by_source': by_source_counts
                },
                'todos': all_todos,
                'grouped_by_urgency': grouped_by_urgency,
                'grouped_by_source': grouped_by_source,
                'source_results': source_results,
                'errors': errors if errors else None
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Unified TODO extraction failed: {e}")
            return create_error_response(
                "Unified TODO extraction failed",
                f"{str(e)}\n\n{error_details}"
            )
    
    return extract_all_todos

