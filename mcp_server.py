"""
MCP Server Implementation

This module implements the Model Context Protocol server that:
1. Registers available tools
2. Validates tool requests from the LLM
3. Executes tools and returns results
4. Enforces strict separation between reasoning (LLM) and execution (tools)
"""

import json
from typing import Dict, Any, List, Optional, Tuple
import tools


class MCPServer:
    """
    MCP Server that manages tool registry and execution.
    
    The server acts as a strict boundary between the LLM (reasoning)
    and the actual tool execution (deterministic operations).
    """
    
    def __init__(self):
        """Initialize the MCP server with available tools."""
        self.tools = {
            'read_file': {
                'name': 'read_file',
                'description': 'Reads a log file from the filesystem. Returns file content.',
                'parameters': {
                    'file_path': {
                        'type': 'string',
                        'description': 'Path to the log file to read'
                    }
                }
            },
            'parse_logs': {
                'name': 'parse_logs',
                'description': 'Parses raw log text and extracts structured information including timestamp, level, service, and message.',
                'parameters': {
                    'log_text': {
                        'type': 'string',
                        'description': 'Raw log file content to parse'
                    }
                }
            },
            'analyze_logs': {
                'name': 'analyze_logs',
                'description': 'Analyzes parsed log entries to extract statistics including error counts, log level distribution, and top services with errors.',
                'parameters': {
                    'parsed_logs': {
                        'type': 'array',
                        'description': 'List of parsed log dictionaries from parse_logs tool'
                    }
                }
            }
        }
        
        # Tool execution mapping
        self.tool_executors = {
            'read_file': tools.read_file,
            'parse_logs': tools.parse_logs,
            'analyze_logs': tools.analyze_logs
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Returns list of available tools for the LLM.
        
        Returns:
            List of tool definitions
        """
        return list(self.tools.values())
    
    def validate_tool_request(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates a tool request against the tool registry.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if tool_name not in self.tools:
            return False, f"Unknown tool: {tool_name}. Available tools: {list(self.tools.keys())}"
        
        tool_def = self.tools[tool_name]
        required_params = set(tool_def['parameters'].keys())
        provided_params = set(arguments.keys())
        
        # Check if all required parameters are provided
        missing_params = required_params - provided_params
        if missing_params:
            return False, f"Missing required parameters: {missing_params}"
        
        return True, None
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a tool with the provided arguments.
        
        This is the ONLY way tools can be executed. The LLM cannot
        access files or execute code directly - it must go through
        this MCP server.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Dictionary with execution results
        """
        # Validate tool request
        is_valid, error_message = self.validate_tool_request(tool_name, arguments)
        if not is_valid:
            return {
                'success': False,
                'error': error_message
            }
        
        # Execute the tool
        try:
            executor = self.tool_executors[tool_name]
            
            # Handle different argument types
            if tool_name == 'read_file':
                result = executor(arguments['file_path'])
            elif tool_name == 'parse_logs':
                result = executor(arguments['log_text'])
            elif tool_name == 'analyze_logs':
                result = executor(arguments['parsed_logs'])
            else:
                result = {'success': False, 'error': f'Unknown tool executor: {tool_name}'}
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Tool execution error: {str(e)}'
            }
    
    def parse_tool_request(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """
        Parses a tool request from the LLM's JSON response.
        
        Expected format: {"tool": "tool_name", "arguments": {...}}
        
        Args:
            llm_response: Raw response from the LLM
            
        Returns:
            Dictionary with 'tool' and 'arguments' keys, or None if invalid
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(llm_response.strip())
            
            # Validate structure
            if not isinstance(parsed, dict):
                return None
            
            if 'tool' not in parsed or 'arguments' not in parsed:
                return None
            
            tool_name = parsed['tool']
            arguments = parsed['arguments']
            
            if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                return None
            
            return {
                'tool': tool_name,
                'arguments': arguments
            }
            
        except json.JSONDecodeError:
            # Try to extract JSON from text if wrapped
            json_match = None
            # Look for JSON object in the response
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                try:
                    json_str = llm_response[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict) and 'tool' in parsed and 'arguments' in parsed:
                        return {
                            'tool': parsed['tool'],
                            'arguments': parsed['arguments']
                        }
                except json.JSONDecodeError:
                    pass
            
            return None
