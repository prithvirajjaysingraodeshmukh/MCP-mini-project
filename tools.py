"""
MCP Tool Implementations

This module contains the actual tool implementations that perform
deterministic operations on log data. These tools are called by the
MCP server based on requests from the LLM.
"""

import re
from typing import List, Dict, Any
from collections import Counter, defaultdict


def read_file(file_path: str) -> Dict[str, Any]:
    """
    Reads a log file from the filesystem.
    
    Args:
        file_path: Path to the log file
        
    Returns:
        Dictionary with 'success' status and 'content' or 'error' message
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            'success': True,
            'content': content,
            'file_path': file_path,
            'lines_count': len(content.splitlines())
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': f'File not found: {file_path}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error reading file: {str(e)}'
        }


def parse_logs(log_text: str) -> Dict[str, Any]:
    """
    Parses log text and extracts structured information.
    
    Expected log format:
    YYYY-MM-DD HH:MM:SS LEVEL [service-name] message
    
    Args:
        log_text: Raw log file content
        
    Returns:
        Dictionary with parsed log entries and metadata
    """
    log_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+) \[([^\]]+)\] (.+)'
    
    parsed_logs = []
    lines = log_text.strip().split('\n')
    
    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue
            
        match = re.match(log_pattern, line)
        if match:
            timestamp, level, service, message = match.groups()
            parsed_logs.append({
                'line_number': line_num,
                'timestamp': timestamp,
                'level': level.upper(),
                'service': service,
                'message': message
            })
        else:
            # Handle unparseable lines
            parsed_logs.append({
                'line_number': line_num,
                'timestamp': None,
                'level': 'UNKNOWN',
                'service': 'unknown',
                'message': line
            })
    
    return {
        'success': True,
        'parsed_logs': parsed_logs,
        'total_lines': len(parsed_logs),
        'parseable_lines': len([log for log in parsed_logs if log['timestamp'] is not None])
    }


def analyze_logs(parsed_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes parsed log entries to extract statistics.
    
    Args:
        parsed_logs: List of parsed log dictionaries
        
    Returns:
        Dictionary with analysis results including:
        - Log level distribution
        - Error counts
        - Top services with errors
        - Service-level statistics
    """
    if not parsed_logs:
        return {
            'success': False,
            'error': 'No logs to analyze'
        }
    
    # Count log levels
    level_counts = Counter(log['level'] for log in parsed_logs)
    
    # Count errors by service
    service_errors = defaultdict(int)
    service_warnings = defaultdict(int)
    service_info = defaultdict(int)
    
    error_logs = []
    warning_logs = []
    
    for log in parsed_logs:
        level = log['level']
        service = log['service']
        
        if level == 'ERROR':
            service_errors[service] += 1
            error_logs.append(log)
        elif level == 'WARN':
            service_warnings[service] += 1
            warning_logs.append(log)
        elif level == 'INFO':
            service_info[service] += 1
    
    # Get top services with errors
    top_error_services = sorted(
        service_errors.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Get top services with warnings
    top_warning_services = sorted(
        service_warnings.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Service-level statistics
    service_stats = {}
    all_services = set(log['service'] for log in parsed_logs)
    for service in all_services:
        service_stats[service] = {
            'total': sum(1 for log in parsed_logs if log['service'] == service),
            'errors': service_errors.get(service, 0),
            'warnings': service_warnings.get(service, 0),
            'info': service_info.get(service, 0)
        }
    
    return {
        'success': True,
        'total_logs': len(parsed_logs),
        'level_distribution': dict(level_counts),
        'error_count': level_counts.get('ERROR', 0),
        'warning_count': level_counts.get('WARN', 0),
        'info_count': level_counts.get('INFO', 0),
        'top_error_services': [{'service': s, 'count': c} for s, c in top_error_services],
        'top_warning_services': [{'service': s, 'count': c} for s, c in top_warning_services],
        'service_statistics': service_stats,
        'error_logs_sample': error_logs[:5],  # Sample of first 5 errors
        'warning_logs_sample': warning_logs[:5]  # Sample of first 5 warnings
    }
