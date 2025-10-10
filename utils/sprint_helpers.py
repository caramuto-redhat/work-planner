"""
Sprint extraction and filtering utilities

This module uses the same logic as GitHub workflow actions to ensure consistency.
"""

import re
from typing import List, Dict, Any, Optional, Tuple


def extract_active_sprint_from_issue(issue: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract ACTIVE sprint name and number from a Jira issue.
    Uses the same logic as the GitHub workflow for consistency.
    
    Args:
        issue: Jira issue dictionary (from search results)
        
    Returns:
        Tuple of (sprint_name, sprint_number) or (None, None) if no active sprint
    """
    if not isinstance(issue, dict):
        return None, None
    
    # Check for customfield_12310940 (the actual sprint field used in our Jira instance)
    sprint_data = issue.get('customfield_12310940', [])
    
    if not sprint_data or len(sprint_data) == 0:
        return None, None
    
    # Look for the ACTIVE sprint first
    for sprint_string in sprint_data:
        sprint_str = str(sprint_string)
        
        # Check if this sprint is ACTIVE
        state_match = re.search(r'state=([^,]+)', sprint_str)
        if state_match and state_match.group(1) == 'ACTIVE':
            # Extract sprint name from the active sprint
            name_match = re.search(r'name=([^,]+)', sprint_str)
            if name_match:
                sprint_name = name_match.group(1)
                # Extract sprint number from the name
                sprint_num = _extract_sprint_number_from_name(sprint_name)
                return sprint_name, sprint_num
    
    # If no active sprint found, fall back to first sprint
    sprint_string = str(sprint_data[0])
    name_match = re.search(r'name=([^,]+)', sprint_string)
    if name_match:
        sprint_name = name_match.group(1)
        sprint_num = _extract_sprint_number_from_name(sprint_name)
        return sprint_name, sprint_num
    
    return None, None


def _extract_sprint_number_from_name(sprint_name: str) -> Optional[int]:
    """
    Extract numeric sprint number from sprint name.
    
    Args:
        sprint_name: Sprint name like "Automotive Feature Teams Sprint 112"
        
    Returns:
        Sprint number or None
    """
    if not sprint_name:
        return None
    
    # Extract number from sprint name using regex
    # Matches patterns like "Sprint 112", "Automotive Feature Teams Sprint 112", etc.
    match = re.search(r'Sprint\s+(\d+)', sprint_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Try to find any number at the end of the string
    match = re.search(r'(\d+)\s*$', sprint_name)
    if match:
        return int(match.group(1))
    
    return None


def filter_issues_by_latest_sprint(issues: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """
    Filter issues to only include those in the latest ACTIVE sprint.
    Uses the same logic as the GitHub workflow for consistency.
    
    Args:
        issues: List of Jira issues
        
    Returns:
        Tuple of (filtered_issues, latest_sprint_number)
    """
    if not issues:
        return [], None
    
    # Extract sprint info from all issues
    issue_sprint_map = []
    sprint_counts = {}
    
    for issue in issues:
        sprint_name, sprint_num = extract_active_sprint_from_issue(issue)
        
        if sprint_name and sprint_num is not None:
            issue_sprint_map.append((issue, sprint_name, sprint_num))
            sprint_counts[sprint_name] = sprint_counts.get(sprint_name, 0) + 1
    
    if not issue_sprint_map:
        # No sprint information found, return all issues
        return issues, None
    
    # Get the most common sprint (like the workflow does)
    most_common_sprint_name = max(sprint_counts, key=sprint_counts.get)
    
    # Extract sprint number from the most common sprint
    latest_sprint_num = None
    for _, sprint_name, sprint_num in issue_sprint_map:
        if sprint_name == most_common_sprint_name:
            latest_sprint_num = sprint_num
            break
    
    # Filter to only issues in the most common/latest sprint
    filtered_issues = [
        issue for issue, sprint_name, _ in issue_sprint_map
        if sprint_name == most_common_sprint_name
    ]
    
    return filtered_issues, latest_sprint_num


def get_sprint_summary(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get a summary of sprint distribution across issues.
    Uses the same logic as the GitHub workflow for consistency.
    
    Args:
        issues: List of Jira issues
        
    Returns:
        Dictionary with sprint summary information
    """
    sprint_counts = {}
    no_sprint_count = 0
    
    for issue in issues:
        sprint_name, sprint_num = extract_active_sprint_from_issue(issue)
        if sprint_num is not None:
            sprint_counts[sprint_num] = sprint_counts.get(sprint_num, 0) + 1
        else:
            no_sprint_count += 1
    
    return {
        "sprint_counts": sprint_counts,
        "no_sprint_count": no_sprint_count,
        "total_issues": len(issues),
        "sprints_found": sorted(sprint_counts.keys(), reverse=True) if sprint_counts else []
    }

