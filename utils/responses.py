"""
Response utilities for MCP tools
"""

import json
from typing import Dict, Any


def create_error_response(error_msg: str, details: str = None) -> str:
    """Create consistent error responses."""
    response = {"error": error_msg}
    if details:
        response["details"] = details
    return json.dumps(response, indent=2)


def create_success_response(data: Dict, message: str = None) -> str:
    """Create consistent success responses."""
    response = data.copy()
    if message:
        response["message"] = message
    return json.dumps(response, indent=2)
