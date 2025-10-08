#!/usr/bin/env python3
"""
Debug script for GitHub Actions workflow
Run this locally to test the same environment as GitHub Actions
"""

import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = [
        'SLACK_XOXC_TOKEN',
        'SLACK_XOXD_TOKEN', 
        'JIRA_URL',
        'JIRA_API_TOKEN',
        'GEMINI_API_KEY',
        'EMAIL_USERNAME',
        'EMAIL_PASSWORD',  # Note: GitHub uses EMAIL_TOKEN
        'EMAIL_FROM'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: NOT SET")
        else:
            print(f"✅ {var}: SET")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {missing_vars}")
        return False
    else:
        print("\n✅ All environment variables are set!")
        return True

def check_email_config():
    """Check email configuration"""
    print("\n🔍 Checking Email Configuration...")
    
    try:
        from connectors.email.config import EmailConfig
        
        email_config = EmailConfig()
        config = email_config.get_config()
        
        print(f"✅ Email config loaded: {bool(config)}")
        print(f"✅ Config keys: {list(config.keys()) if config else 'None'}")
        
        # Validate config
        if email_config.validate_config():
            print("✅ Email config validation passed")
            return True
        else:
            print("❌ Email config validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Email config error: {e}")
        return False

def test_email_sending():
    """Test email sending"""
    print("\n🔍 Testing Email Sending...")
    
    try:
        from connectors.email.client import EmailClient
        from connectors.email.config import EmailConfig
        
        email_config = EmailConfig()
        config = email_config.get_config()
        
        if not email_config.validate_config():
            print("❌ Email config validation failed")
            return False
            
        email_client = EmailClient(config)
        
        # Test with a simple template
        result = email_client.send_email(
            template_name='team_daily_report_with_todo',
            recipients=config['recipients']['default'],
            content_data={
                'team': 'TEST',
                'date': '2024-01-01',
                'generated_time': '2024-01-01 12:00 UTC',
                'executive_summary': 'Test summary',
                'paul_todo_items': 'Test TODO items',
                'slack_channel_details': 'Test Slack details',
                'ai_channel_summaries': 'Test AI summaries',
                'sprint_title': 'Test Sprint',
                'jira_ticket_details': 'Test Jira details',
                'slack_activity_days': 7,
                'jira_ticket_limit': 15
            }
        )
        
        if result.get('success'):
            print("✅ Test email sent successfully!")
            return True
        else:
            print(f"❌ Test email failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Email sending error: {e}")
        return False

def main():
    """Main debug function"""
    print("🚀 GitHub Actions Workflow Debug Tool")
    print("=" * 50)
    
    # Check environment
    env_ok = check_environment()
    
    # Check email config
    config_ok = check_email_config()
    
    # Test email sending
    if env_ok and config_ok:
        email_ok = test_email_sending()
        
        if email_ok:
            print("\n🎉 All tests passed! The workflow should work.")
        else:
            print("\n❌ Email sending failed. Check your email credentials.")
    else:
        print("\n❌ Basic checks failed. Fix the issues above first.")

if __name__ == '__main__':
    main()
