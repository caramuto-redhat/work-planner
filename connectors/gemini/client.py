"""
Gemini AI Client
Handles communication with Google's Gemini API
"""

import os
import json
from typing import Dict, List, Optional, Any
from utils.responses import create_error_response, create_success_response

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiClient:
    """Client for interacting with Google's Gemini AI API"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Gemini client with configuration"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed")
        
        self.config = config
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        model_name = config.get('model', 'models/gemini-2.0-flash')
        self.model = genai.GenerativeModel(model_name)
        
        # Set generation config (exact match with working repository)
        generation_config = config.get('generation_config', {})
        if generation_config:
            # Use simple dictionary approach like working repository
            self.generation_config = {
                "temperature": generation_config.get('temperature', 0.7),
                "top_p": generation_config.get('top_p', 0.9),
                "top_k": generation_config.get('top_k', 40),
                "max_output_tokens": generation_config.get('max_output_tokens', 2048),
            }
        else:
            self.generation_config = {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
    
    def generate_content(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate content using Gemini API"""
        try:
            # Enhance prompt with context if provided
            if context:
                enhanced_prompt = self._enhance_prompt_with_context(prompt, context)
            else:
                enhanced_prompt = prompt
            
            # Generate response with generation config (like working repository)
            response = self.model.generate_content(
                enhanced_prompt,
                generation_config=self.generation_config
            )
            
            if response.text:
                return response.text
            else:
                return "No response generated from Gemini API"
                
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def analyze_slack_data(self, slack_data: Dict[str, Any], analysis_type: str = "summary") -> str:
        """Analyze Slack data using Gemini"""
        try:
            # Get analysis prompt from config
            prompt_template = self.config.get('prompts', {}).get('slack_analysis', {}).get(analysis_type, "")
            
            if not prompt_template:
                prompt_template = f"Analyze the following Slack data and provide a {analysis_type}:"
            
            # Prepare context
            context = {
                'data_type': 'slack',
                'analysis_type': analysis_type,
                'data': slack_data
            }
            
            return self.generate_content(prompt_template, context)
            
        except Exception as e:
            raise Exception(f"Slack analysis error: {str(e)}")
    
    def analyze_jira_data(self, jira_data: Dict[str, Any], analysis_type: str = "summary") -> str:
        """Analyze Jira data using Gemini"""
        try:
            # Get analysis prompt from config
            prompt_template = self.config.get('prompts', {}).get('jira_analysis', {}).get(analysis_type, "")
            
            if not prompt_template:
                prompt_template = f"Analyze the following Jira data and provide a {analysis_type}:"
            
            # Prepare context
            context = {
                'data_type': 'jira',
                'analysis_type': analysis_type,
                'data': jira_data
            }
            
            return self.generate_content(prompt_template, context)
            
        except Exception as e:
            raise Exception(f"Jira analysis error: {str(e)}")
    
    def generate_email_summary(self, slack_data: Dict[str, Any], jira_data: Dict[str, Any]) -> str:
        """Generate email summary combining Slack and Jira data"""
        try:
            # Get email summary prompt from config
            prompt_template = self.config.get('prompts', {}).get('email_summary', "")
            
            if not prompt_template:
                prompt_template = """
                Create a professional email summary combining the following data:
                
                Slack Activity: {slack_data}
                Jira Issues: {jira_data}
                
                Please provide:
                1. Key highlights from team activity
                2. Important issues and blockers
                3. Recommendations for next steps
                4. Overall team status
                """
            
            # Prepare context
            context = {
                'data_type': 'combined',
                'analysis_type': 'email_summary',
                'slack_data': slack_data,
                'jira_data': jira_data
            }
            
            return self.generate_content(prompt_template, context)
            
        except Exception as e:
            raise Exception(f"Email summary generation error: {str(e)}")
    
    def _enhance_prompt_with_context(self, prompt: str, context: Dict[str, Any]) -> str:
        """Enhance prompt with context data"""
        try:
            # Format context data for inclusion in prompt
            context_str = json.dumps(context, indent=2)
            
            # Combine prompt with context
            enhanced_prompt = f"""
{prompt}

Context Data:
{context_str}

Please analyze the context data and provide your response based on the prompt above.
"""
            return enhanced_prompt
            
        except Exception as e:
            # If context enhancement fails, return original prompt
            return prompt
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            'model_name': self.model.model_name,
            'api_key_configured': bool(self.api_key),
            'generation_config': self.model.generation_config.__dict__ if hasattr(self.model, 'generation_config') else {}
        }
