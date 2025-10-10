"""
Gemini Configuration
Handles loading and validation of Gemini configuration
"""

import os
import yaml
from typing import Dict, Any, Optional
from utils.responses import create_error_response, create_success_response


class GeminiConfig:
    """Configuration manager for Gemini AI connector"""
    
    @staticmethod
    def load(config_path: str) -> Dict[str, Any]:
        """Load Gemini configuration from YAML file (static method for compatibility)"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config or GeminiConfig._get_static_default_config()
        except FileNotFoundError:
            print(f"Warning: Gemini configuration file not found: {config_path}. Using defaults.")
            return GeminiConfig._get_static_default_config()
        except yaml.YAMLError as e:
            print(f"Error parsing Gemini configuration file {config_path}: {e}. Using defaults.")
            return GeminiConfig._get_static_default_config()
        except Exception as e:
            print(f"Warning: Could not load Gemini config from {config_path}: {e}. Using defaults.")
            return GeminiConfig._get_static_default_config()
    
    @staticmethod
    def _get_static_default_config() -> Dict[str, Any]:
        """Get default configuration (static method)"""
        return {
            'model': 'models/gemini-2.0-flash',
            'generation_config': {
                'temperature': 0.7,
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 2048
            }
        }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize Gemini configuration"""
        self.config_path = config_path or os.path.join('config', 'gemini.yaml')
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                return config or {}
            else:
                # Return default configuration
                return self._get_default_config()
        except Exception as e:
            print(f"Warning: Could not load Gemini config from {self.config_path}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration (prompts are now inline in tools)"""
        return {
            'model': 'models/gemini-2.0-flash',
            'generation_config': {
                'temperature': 0.7,
                'top_p': 0.9,
                'top_k': 40,
                'max_output_tokens': 2048
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration"""
        return self.config
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model-specific configuration"""
        return {
            'model': self.config.get('model', 'models/gemini-2.0-flash'),
            'generation_config': self.config.get('generation_config', {})
        }
    
    def get_prompts(self) -> Dict[str, Any]:
        """Get all configured prompts"""
        return self.config.get('prompts', {})
    
    def get_prompt(self, category: str, prompt_type: str) -> str:
        """Get a specific prompt by category and type"""
        prompts = self.config.get('prompts', {})
        category_prompts = prompts.get(category, {})
        return category_prompts.get(prompt_type, "")
    
    def validate_config(self) -> bool:
        """Validate the current configuration"""
        try:
            # Check required fields
            required_fields = ['model']
            for field in required_fields:
                if field not in self.config:
                    print(f"Warning: Missing required field '{field}' in Gemini config")
                    return False
            
            # Validate model name
            valid_models = ['models/gemini-2.0-flash', 'models/gemini-2.5-flash', 'models/gemini-flash-latest', 'models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-1.0-pro', 'gemini-pro']
            if self.config.get('model') not in valid_models:
                print(f"Warning: Invalid model '{self.config.get('model')}' in Gemini config")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error validating Gemini config: {e}")
            return False
