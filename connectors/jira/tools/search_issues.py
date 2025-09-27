"""
Search Jira issues using JQL query
"""

from utils.responses import create_error_response, create_success_response
from utils.validators import validate_jql, validate_max_results


def search_issues_tool(client, config):
    """Create search_issues tool function"""
    
    def search_issues(jql: str, max_results: int = 20) -> str:
        """Search Jira issues using JQL query."""
        try:
            # Input validation
            validated_jql = validate_jql(jql)
            validated_max_results = validate_max_results(max_results)
            
            issues = client.search_issues(validated_jql, validated_max_results)
            return create_success_response({
                "issues": issues,
                "count": len(issues),
                "jql": validated_jql
            })
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response("Failed to search issues", str(e))
    
    return search_issues
