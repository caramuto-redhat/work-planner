#!/usr/bin/env python3
"""
Test script for TODO Extraction Tools
Tests all 4 new MCP tools with small samples
"""

import os
import json

# Load environment variables from .env file if it exists
env_file = '.env'
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

print('\n' + '='*70)
print('🧪 TODO EXTRACTION TOOLS - TEST SUITE')
print('='*70)

# Test 1: Email TODO Extraction
print('\n📧 [1/4] Testing Email TODO Extraction...')
print('-'*70)
try:
    from connectors.email.config import EmailConfig
    from connectors.email.tools.inbox_tools import extract_email_todos_tool
    from connectors.gemini.config import GeminiConfig
    
    email_config = EmailConfig()
    gemini_config = GeminiConfig.load('config/gemini.yaml')
    
    email_tool = extract_email_todos_tool(email_config, gemini_config)
    print('   📥 Extracting TODOs from last 7 days of emails...')
    result = email_tool(days_back=7)
    
    data = json.loads(result)
    if data.get('success'):
        summary = data['data']
        print(f'   ✅ SUCCESS')
        print(f'   📊 Emails analyzed: {summary.get("emails_analyzed", 0)}')
        print(f'   📋 TODOs found: {summary.get("todos_found", 0)}')
        
        if summary.get('todos_found', 0) > 0:
            print(f'\n   Sample TODOs:')
            for todo in summary.get('todos', [])[:3]:  # Show first 3
                print(f'      • [{todo.get("urgency", "?")}] {todo.get("description", "")[:60]}...')
    else:
        print(f'   ⚠️  ERROR: {data.get("error", "Unknown error")}')
        print(f'   Details: {data.get("details", "")}')
except Exception as e:
    print(f'   ❌ EXCEPTION: {str(e)}')
    import traceback
    traceback.print_exc()

# Test 2: Jira TODO Extraction
print('\n🎫 [2/4] Testing Jira TODO Extraction...')
print('-'*70)
try:
    from connectors.jira.client import JiraClient
    from connectors.jira.config import JiraConfig
    from connectors.jira.tools.extract_jira_todos import extract_jira_todos_tool
    
    jira_config = JiraConfig.load('config/jira.yaml')
    jira_client = JiraClient(jira_config)
    
    jira_tool = extract_jira_todos_tool(jira_client, jira_config, gemini_config)
    print('   📥 Extracting TODOs from last 7 days of Jira issues...')
    result = jira_tool(team='toolchain', days_back=7)
    
    data = json.loads(result)
    if data.get('success'):
        summary = data['data']
        print(f'   ✅ SUCCESS')
        print(f'   📊 Issues analyzed: {summary.get("issues_analyzed", 0)}')
        print(f'   📋 TODOs found: {summary.get("todos_found", 0)}')
        
        if summary.get('todos_found', 0) > 0:
            print(f'\n   Sample TODOs:')
            for todo in summary.get('todos', [])[:3]:  # Show first 3
                print(f'      • [{todo.get("urgency", "?")}] {todo.get("description", "")[:60]}...')
    else:
        print(f'   ⚠️  ERROR: {data.get("error", "Unknown error")}')
except Exception as e:
    print(f'   ❌ EXCEPTION: {str(e)}')

# Test 3: Slack TODO Extraction
print('\n💬 [3/4] Testing Slack TODO Extraction...')
print('-'*70)
try:
    from connectors.slack.client import SlackClient
    from connectors.slack.config import SlackConfig
    from connectors.slack.tools.extract_slack_todos import extract_slack_todos_tool
    
    slack_config = SlackConfig.load('config/slack.yaml')
    slack_client = SlackClient(slack_config)
    
    slack_tool = extract_slack_todos_tool(slack_client, slack_config, gemini_config)
    print('   📥 Extracting TODOs from last 7 days of Slack messages...')
    result = slack_tool(team='toolchain', days_back=7)
    
    data = json.loads(result)
    if data.get('success'):
        summary = data['data']
        print(f'   ✅ SUCCESS')
        print(f'   📊 Messages analyzed: {summary.get("messages_analyzed", 0)}')
        print(f'   📋 TODOs found: {summary.get("todos_found", 0)}')
        
        if summary.get('todos_found', 0) > 0:
            print(f'\n   Sample TODOs:')
            for todo in summary.get('todos', [])[:3]:  # Show first 3
                print(f'      • [{todo.get("urgency", "?")}] {todo.get("description", "")[:60]}...')
    else:
        print(f'   ⚠️  ERROR: {data.get("error", "Unknown error")}')
except Exception as e:
    print(f'   ❌ EXCEPTION: {str(e)}')

# Test 4: Unified TODO Extraction
print('\n🎯 [4/4] Testing Unified TODO Extraction...')
print('-'*70)
try:
    from connectors.gemini.tools.extract_all_todos_tool import extract_all_todos_tool
    
    # Create tool instances
    email_tool_func = extract_email_todos_tool(email_config, gemini_config)
    jira_tool_func = extract_jira_todos_tool(jira_client, jira_config, gemini_config)
    slack_tool_func = extract_slack_todos_tool(slack_client, slack_config, gemini_config)
    
    unified_tool = extract_all_todos_tool(email_tool_func, jira_tool_func, slack_tool_func)
    print('   📥 Extracting TODOs from ALL sources (last 7 days)...')
    result = unified_tool(days_back=7)
    
    data = json.loads(result)
    if data.get('success'):
        summary = data['data']
        print(f'   ✅ SUCCESS')
        print(f'   📋 Total TODOs: {summary.get("total_todos", 0)}')
        print(f'\n   By Source:')
        by_source = summary.get('summary', {}).get('by_source', {})
        print(f'      📧 Email: {by_source.get("email", 0)}')
        print(f'      🎫 Jira: {by_source.get("jira", 0)}')
        print(f'      💬 Slack: {by_source.get("slack", 0)}')
        print(f'\n   By Urgency:')
        by_urgency = summary.get('summary', {}).get('by_urgency', {})
        print(f'      🔴 Critical: {by_urgency.get("critical", 0)}')
        print(f'      🟠 High: {by_urgency.get("high", 0)}')
        print(f'      🟡 Medium: {by_urgency.get("medium", 0)}')
        print(f'      🟢 Low: {by_urgency.get("low", 0)}')
    else:
        print(f'   ⚠️  ERROR: {data.get("error", "Unknown error")}')
except Exception as e:
    print(f'   ❌ EXCEPTION: {str(e)}')
    import traceback
    traceback.print_exc()

print('\n' + '='*70)
print('✅ TEST SUITE COMPLETE')
print('='*70 + '\n')

