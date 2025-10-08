#!/usr/bin/env python3
"""
Quick test to verify email configuration is working
"""

import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_email_config():
    """Test email configuration"""
    print("🔍 Testing Email Configuration...")
    
    try:
        from connectors.email.config import EmailConfig
        from connectors.email.client import EmailClient
        
        # Test config loading
        email_config = EmailConfig()
        config = email_config.get_config()
        
        print(f"✅ Config loaded: {bool(config)}")
        print(f"✅ Config keys: {list(config.keys())}")
        
        # Test provider config
        provider_config = email_config.get_provider_config()
        print(f"✅ Provider config: {provider_config}")
        
        # Test validation
        if email_config.validate_config():
            print("✅ Email config validation passed")
        else:
            print("❌ Email config validation failed")
            return False
        
        # Test client creation
        try:
            email_client = EmailClient(config)
            print("✅ Email client created successfully")
            
            # Test provider config in client
            print(f"✅ Client provider config: {email_client.provider_config}")
            
            return True
            
        except Exception as e:
            print(f"❌ Email client creation failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Email config test failed: {e}")
        return False

if __name__ == '__main__':
    test_email_config()
