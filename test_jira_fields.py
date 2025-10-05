#!/usr/bin/env python3
"""
Test script to check what fields are actually returned by the updated JiraClient
"""

import os
import sys
import json

def test_jira_fields():
    """Test what fields are returned by JiraClient"""
    
    # Add project root to path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    try:
        from connectors.jira.config import JiraConfig
        from connectors.jira.client import JiraClient
        
        print("🔍 Testing JiraClient field extraction...")
        
        # Load config
        jira_config = JiraConfig.load("config/jira.yaml")
        
        # Set environment variables if not set
        if not os.getenv('JIRA_URL'):
            os.environ['JIRA_URL'] = 'https://issues.redhat.com'
        if not os.getenv('JIRA_API_TOKEN'):
            print("❌ JIRA_API_TOKEN not set - cannot test actual Jira connection")
            print("🔍 This would require actual Jira credentials to test")
            return
        
        # Create client
        jira_client = JiraClient(jira_config)
        
        print("🔍 Searching for VROOM-33058...")
        
        # Search for the ticket
        jql = "key = VROOM-33058"
        issues = jira_client.search_issues(jql, max_results=1)
        
        if not issues:
            print("❌ No ticket found")
            return
        
        issue = issues[0]
        print(f"✅ Found ticket: {issue.get('key')}")
        
        print("\n🔍 All available fields:")
        print("=" * 50)
        for field_name, field_value in issue.items():
            print(f"{field_name}: {field_value}")
        
        print("\n🔍 Sprint-related fields:")
        print("=" * 50)
        sprint_fields = []
        for field_name, field_value in issue.items():
            if 'sprint' in field_name.lower() or 'active' in field_name.lower():
                sprint_fields.append((field_name, field_value))
                print(f"🎯 {field_name}: {field_value}")
        
        if not sprint_fields:
            print("❌ No sprint-related fields found")
        else:
            print(f"\n✅ Found {len(sprint_fields)} sprint-related fields")
            
        print("\n🔍 Checking for 'Active Sprint' field specifically:")
        print("=" * 50)
        if 'Active Sprint' in issue:
            active_sprint_value = issue['Active Sprint']
            print(f"✅ Found 'Active Sprint' field: {active_sprint_value}")
            print(f"📊 Type: {type(active_sprint_value)}")
        else:
            print("❌ 'Active Sprint' field not found")
            print("🔍 Available field names containing 'sprint' or 'active':")
            for field_name in issue.keys():
                if 'sprint' in field_name.lower() or 'active' in field_name.lower():
                    print(f"   - {field_name}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jira_fields()
