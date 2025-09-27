"""
Jira configuration loader
"""

from typing import Dict, Any


class JiraConfig:
    """Jira configuration loader"""
    
    @staticmethod
    def load(config_path: str) -> Dict[str, Any]:
        """Load Jira configuration from YAML file"""
        import yaml
        
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
            
            # Validate required sections
            required_sections = ['teams', 'organizations', 'user_display_names']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required configuration section: {section}")
            
            return config
            
        except FileNotFoundError:
            raise RuntimeError(f"Jira configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise RuntimeError(f"Error parsing Jira configuration file {config_path}: {e}")
