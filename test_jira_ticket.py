#!/usr/bin/env python3
"""
Test script to simulate Jira ticket field inspection
Since we don't have access to actual Jira credentials, we'll simulate
what the GitHub Actions script would see based on the user's description.
"""

import os
import sys
import json

def test_jira_ticket():
    """Test Jira ticket field inspection simulation"""
    
    print("🔍 Simulating Jira ticket field inspection for VROOM-33058")
    print("=" * 60)
    
    # Based on the user's description, the "Active Sprint" field contains:
    # "Active Sprint: Auto Toolchain Sprint 112 ends 2025/10/15"
    
    # Let's simulate different possible field formats that Jira might return
    simulated_ticket_formats = [
        {
            "key": "VROOM-33058",
            "summary": "Test ticket for sprint detection",
            "status": "In Progress",
            "assignee": "Test User",
            "Active Sprint": "Auto Toolchain Sprint 112 ends 2025/10/15",  # Direct string
            "customfield_10020": [{"name": "Auto Toolchain Sprint 112 ends 2025/10/15"}],  # Array with dict
            "customfield_10021": ["Auto Toolchain Sprint 112 ends 2025/10/15"],  # Array with string
            "sprint": [{"value": "Auto Toolchain Sprint 112 ends 2025/10/15"}],  # Array with value
            "updated": "2025-10-05T18:00:00.000+0000"
        },
        {
            "key": "VROOM-33058",
            "summary": "Test ticket for sprint detection",
            "status": "In Progress", 
            "assignee": "Test User",
            "Active Sprint": [{"name": "Auto Toolchain Sprint 112 ends 2025/10/15"}],  # Array format
            "updated": "2025-10-05T18:00:00.000+0000"
        },
        {
            "key": "VROOM-33058",
            "summary": "Test ticket for sprint detection",
            "status": "In Progress",
            "assignee": "Test User", 
            "Active Sprint": [{"value": "Auto Toolchain Sprint 112 ends 2025/10/15"}],  # Array with value
            "updated": "2025-10-05T18:00:00.000+0000"
        }
    ]
    
    for i, issue in enumerate(simulated_ticket_formats, 1):
        print(f"\n🔍 Testing Format {i}:")
        print("=" * 30)
        
        print(f"✅ Found ticket: {issue.get('key', 'Unknown')}")
        print(f"📋 Summary: {issue.get('summary', 'No summary')}")
        
        print("\n🔍 Sprint-related fields:")
        print("-" * 30)
        sprint_fields = []
        for field_name, field_value in issue.items():
            if 'sprint' in field_name.lower() or 'active' in field_name.lower():
                sprint_fields.append((field_name, field_value))
                print(f"🎯 {field_name}: {field_value}")
        
        print(f"\n✅ Found {len(sprint_fields)} sprint-related fields")
        
        print("\n🔍 Testing 'Active Sprint' field detection:")
        print("-" * 40)
        if 'Active Sprint' in issue:
            active_sprint_value = issue['Active Sprint']
            print(f"✅ Found 'Active Sprint' field: {active_sprint_value}")
            print(f"📊 Type: {type(active_sprint_value)}")
            
            # Test our detection logic
            sprint_name = None
            if isinstance(active_sprint_value, list) and active_sprint_value:
                print(f"📊 List length: {len(active_sprint_value)}")
                print(f"📊 First item: {active_sprint_value[0]}")
                print(f"📊 First item type: {type(active_sprint_value[0])}")
                
                if isinstance(active_sprint_value[0], dict):
                    print(f"📊 Dict keys: {list(active_sprint_value[0].keys())}")
                    sprint_name = active_sprint_value[0].get('name', active_sprint_value[0].get('value', 'Unknown Sprint'))
                    for key, value in active_sprint_value[0].items():
                        print(f"   {key}: {value}")
                else:
                    sprint_name = str(active_sprint_value[0])
            else:
                sprint_name = str(active_sprint_value)
            
            print(f"\n🎯 Detected sprint name: {sprint_name}")
            print(f"🎯 Email title would be: '🎫 Active Sprint \"{sprint_name}\" Tickets'")
        else:
            print("❌ 'Active Sprint' field not found")
    
    print("\n" + "=" * 60)
    print("🔍 CONCLUSION:")
    print("Based on the user's description, the 'Active Sprint' field should contain:")
    print("'Auto Toolchain Sprint 112 ends 2025/10/15'")
    print("\nThe GitHub Actions script should detect this and show:")
    print("'🎫 Active Sprint \"Auto Toolchain Sprint 112 ends 2025/10/15\" Tickets'")

if __name__ == "__main__":
    test_jira_ticket()
