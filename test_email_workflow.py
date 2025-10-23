#!/usr/bin/env python3
"""
Test email workflow configuration
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def test_email_config():
    """Test email configuration"""
    print('🔍 Testing Email Configuration...\n')
    
    # Check environment variables
    print('1. Checking Environment Variables:')
    env_vars = {
        'EMAIL_USERNAME': os.getenv('EMAIL_USERNAME'),
        'EMAIL_PASSWORD': os.getenv('EMAIL_PASSWORD'),
        'EMAIL_FROM': os.getenv('EMAIL_FROM'),
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
    }
    
    for var, value in env_vars.items():
        if value:
            masked = value[:10] + '...' if len(value) > 10 else value
            print(f'   ✅ {var}: {masked}')
        else:
            print(f'   ❌ {var}: NOT SET')
    
    print()
    
    # Try to load email config
    print('2. Testing Email Config Load:')
    try:
        from connectors.email.config import EmailConfig
        email_config = EmailConfig()
        config = email_config.get_config()
        
        print(f'   ✅ EmailConfig loaded successfully')
        print(f'   ✅ Config keys: {list(config.keys())}')
        
        # Check SMTP settings
        smtp_config = email_config.get_smtp_config()
        print(f'   ✅ SMTP server: {smtp_config.get("server")}:{smtp_config.get("port")}')
        
        # Validate config
        if email_config.validate_config():
            print(f'   ✅ Config validation PASSED')
        else:
            print(f'   ❌ Config validation FAILED')
            
    except Exception as e:
        print(f'   ❌ Failed to load email config: {e}')
        return False
    
    print()
    
    # Try to create email client
    print('3. Testing Email Client:')
    try:
        from connectors.email.client import EmailClient
        email_client = EmailClient(config)
        print(f'   ✅ EmailClient created successfully')
        
        # Check if we can prepare a test email
        templates = email_config.get_templates()
        if 'paul_todo_summary' in templates:
            print(f'   ✅ paul_todo_summary template found')
        else:
            print(f'   ❌ paul_todo_summary template NOT FOUND')
            
    except Exception as e:
        print(f'   ❌ Failed to create email client: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # Test email sending capability (dry run)
    print('4. Testing Email Sending (Dry Run):')
    try:
        # Get recipients
        recipients = config.get('recipients', {}).get('default', [])
        print(f'   Recipients: {recipients}')
        
        if not recipients:
            print(f'   ❌ No recipients configured!')
            return False
        
        print(f'   ✅ Would send to: {", ".join(recipients)}')
        
    except Exception as e:
        print(f'   ❌ Failed email send test: {e}')
        return False
    
    print()
    print('✅ All email configuration tests PASSED!')
    print()
    print('💡 If workflow failed, check GitHub Actions logs for:')
    print('   - Email connection errors')
    print('   - SMTP authentication failures')
    print('   - Template rendering errors')
    print('   - Network/firewall issues')
    
    return True


if __name__ == '__main__':
    # Load environment from .env file if it exists
    env_file = os.path.expanduser('~/.rh-work-planner.env')
    if os.path.exists(env_file):
        print(f'📁 Loading environment from: {env_file}\n')
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    success = test_email_config()
    sys.exit(0 if success else 1)

