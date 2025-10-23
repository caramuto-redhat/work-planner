"""
Email Inbox TODO Extraction Tool
MCP tool for extracting actionable TODO items from email inbox using Gemini AI
"""

import json
from typing import Dict, Any, List
from utils.responses import create_error_response, create_success_response
from connectors.email.client import InboxReader
from connectors.email.config import EmailConfig
from connectors.gemini.client import GeminiClient
from connectors.gemini.config import GeminiConfig


def extract_email_todos_tool(email_config: EmailConfig, gemini_config_dict: Dict[str, Any]):
    """Create extract_email_todos tool function"""
    
    def extract_email_todos(days_back: int = 30) -> str:
        """
        Extract actionable TODO items from email inbox using Gemini AI natural language understanding.
        
        Analyzes emails from the past N days and intelligently identifies tasks that require action,
        including direct requests, implicit action items, questions, and commitments.
        
        Args:
            days_back: Number of days to look back (default: 30)
            
        Returns:
            JSON response with extracted TODO items, urgency, deadlines, and context
            
        Example:
            extract_email_todos(days_back=30)
        """
        try:
            print(f"\n📧 Starting email TODO extraction (last {days_back} days)...")
            
            # Get TODO extraction configuration
            todo_config = gemini_config_dict.get('todo_extraction', {})
            if not todo_config.get('enabled', False):
                return create_error_response(
                    "TODO extraction disabled",
                    "todo_extraction.enabled is false in gemini.yaml"
                )
            
            email_source_config = todo_config.get('sources', {}).get('email', {})
            if not email_source_config.get('enabled', True):
                return create_error_response(
                    "Email TODO extraction disabled",
                    "todo_extraction.sources.email.enabled is false in gemini.yaml"
                )
            
            # Initialize inbox reader
            imap_config = email_config.get_imap_config()
            inbox_reader = InboxReader(imap_config)
            
            # Fetch emails
            print(f"📥 Fetching emails from inbox...")
            emails = inbox_reader.fetch_emails(days_back=days_back)
            inbox_reader.disconnect()
            
            if not emails:
                return create_success_response({
                    'emails_analyzed': 0,
                    'todos_found': 0,
                    'todos': [],
                    'message': 'No emails found in the specified time range'
                })
            
            print(f"✅ Fetched {len(emails)} emails")
            
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
            email_prompt_template = prompts.get('email_prompt', '')
            
            # Extract TODOs from each email
            print(f"🤖 Analyzing emails for TODOs using Gemini AI...")
            all_todos = []
            confidence_threshold = todo_config.get('detection', {}).get('confidence_threshold', 0.6)
            max_todos_per_email = todo_config.get('detection', {}).get('max_todos_per_item', 3)
            priority_weight = email_source_config.get('priority_weight', 1.2)
            
            for idx, email_data in enumerate(emails, 1):
                try:
                    # Build email prompt
                    email_prompt = email_prompt_template.format(
                        email_from=email_data.get('from', 'Unknown'),
                        email_subject=email_data.get('subject', 'No subject'),
                        email_date=email_data.get('date', 'Unknown'),
                        email_body=email_data.get('body', '')[:2000]  # Limit body length
                    )
                    
                    # Combine system prompt and email prompt
                    full_prompt = f"{system_prompt}\n\n{email_prompt}"
                    
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
                            print(f"  ⚠️  Email {idx}/{len(emails)}: Invalid response format (not a list)")
                            continue
                        
                        # Filter by confidence and limit
                        filtered_todos = [
                            todo for todo in todos 
                            if float(todo.get('confidence', 0)) >= confidence_threshold
                        ][:max_todos_per_email]
                        
                        # Add metadata and apply priority weight
                        for todo in filtered_todos:
                            todo['source'] = 'email'
                            todo['metadata'] = {
                                'from': email_data.get('from', 'Unknown'),
                                'subject': email_data.get('subject', 'No subject'),
                                'date': email_data.get('date', 'Unknown')
                            }
                            # Apply priority weight if urgency is specified
                            if 'urgency' in todo:
                                todo['original_urgency'] = todo['urgency']
                                todo['priority_weight'] = priority_weight
                        
                        all_todos.extend(filtered_todos)
                        
                        if filtered_todos:
                            print(f"  ✅ Email {idx}/{len(emails)}: Found {len(filtered_todos)} TODO(s)")
                        else:
                            print(f"  ⚪ Email {idx}/{len(emails)}: No TODOs")
                    
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️  Email {idx}/{len(emails)}: Failed to parse JSON response: {e}")
                        continue
                
                except Exception as e:
                    print(f"  ❌ Email {idx}/{len(emails)}: Analysis failed: {e}")
                    continue
            
            # Sort by urgency and confidence
            urgency_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            all_todos.sort(
                key=lambda x: (
                    urgency_order.get(x.get('urgency', 'low'), 4),
                    -float(x.get('confidence', 0))
                )
            )
            
            print(f"\n✅ Email TODO extraction complete!")
            print(f"   📊 Emails analyzed: {len(emails)}")
            print(f"   📋 TODOs found: {len(all_todos)}")
            
            return create_success_response({
                'emails_analyzed': len(emails),
                'todos_found': len(all_todos),
                'todos': all_todos,
                'analysis_period': f'Last {days_back} days',
                'confidence_threshold': confidence_threshold,
                'priority_weight': priority_weight
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Email TODO extraction failed: {e}")
            return create_error_response(
                "Email TODO extraction failed",
                f"{str(e)}\n\n{error_details}"
            )
    
    return extract_email_todos

