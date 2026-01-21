"""
Gemini Pro Agent Implementation

This module handles interaction with Gemini Pro LLM, enforcing
strict JSON-only tool requests and managing the conversation flow.
"""

import json
import google.generativeai as genai
from typing import Dict, Any, Optional, List
from mcp_server import MCPServer


class GeminiAgent:
    """
    Agent that uses Gemini Pro for reasoning and MCP server for execution.
    
    The agent enforces strict separation:
    - Gemini Pro: Reasoning and decision-making
    - MCP Server: Tool execution (deterministic operations)
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini Pro agent.
        
        Args:
            api_key: Google Gemini API key
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemma-3-4b-it')
        self.mcp_server = MCPServer()
        
        # System prompt that enforces strict JSON tool requests
        self.system_prompt = """You are a log analysis assistant. Your role is to analyze ONLY the provided log files.

CRITICAL RULES:
1. You CANNOT read files or execute code directly.
2. You MUST use tools via the MCP (Model Context Protocol) server.
3. The only available log files are the ones listed below. NEVER invent new file names (e.g., do NOT use log.txt if not listed).
4. When you need to use a tool, respond ONLY with valid JSON in this exact format:
   {"tool": "tool_name", "arguments": {"param1": "value1", "param2": "value2"}}
5. Do NOT include any text before or after the JSON.
6. Do NOT explain what you're doing - just return the JSON.

Available tools:
- read_logs(file_names): Reads allowed log files (default + uploaded) and returns contents
- parse_logs(log_text): Parses raw log text into structured format
- analyze_logs(parsed_logs): Analyzes parsed logs to extract statistics

Workflow:
1. Use read_logs with an explicit list of allowed file names to get content.
2. Use parse_logs on the retrieved content.
3. Use analyze_logs on parsed entries.
4. Provide a natural language summary using tool results.

If a needed log file is not listed, state that it is unavailable instead of inventing a name."""
    
    def get_tool_descriptions(self) -> str:
        """
        Get formatted tool descriptions for the LLM.
        
        Returns:
            String describing available tools
        """
        tools = self.mcp_server.get_available_tools()
        descriptions = []
        for tool in tools:
            desc = f"- {tool['name']}: {tool['description']}"
            params = []
            for param_name, param_info in tool['parameters'].items():
                params.append(f"  {param_name} ({param_info['type']}): {param_info['description']}")
            if params:
                desc += "\n  Parameters:\n" + "\n".join(params)
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to extract JSON tool request from LLM response.
        
        Args:
            response: Raw response from Gemini Pro
            
        Returns:
            Parsed tool request or None
        """
        # Try direct JSON parsing
        parsed = self.mcp_server.parse_tool_request(response)
        if parsed:
            return parsed
        
        # Try to find JSON in code blocks
        if '```json' in response:
            start = response.find('```json') + 7
            end = response.find('```', start)
            if end > start:
                json_str = response[start:end].strip()
                parsed = self.mcp_server.parse_tool_request(json_str)
                if parsed:
                    return parsed
        
        if '```' in response:
            start = response.find('```') + 3
            end = response.find('```', start)
            if end > start:
                json_str = response[start:end].strip()
                if json_str.startswith('{'):
                    parsed = self.mcp_server.parse_tool_request(json_str)
                    if parsed:
                        return parsed
        
        return None
    
    def process_query(self, user_query: str, available_files: List[str], max_iterations: int = 10) -> Dict[str, Any]:
        """
        Process a user query by coordinating between Gemini Pro and MCP server.

        Args:
            user_query: User's question about logs
            available_files: List of allowed file names/paths for this session
            max_iterations: Maximum number of tool calls allowed

        Returns:
            Dictionary with final answer and execution history
        """
        conversation_history = []
        tool_results = []
        self.mcp_server.set_available_files(available_files)

        # Build initial prompt with system instructions and available files
        available_files_text = "\n".join(f"- {name}" for name in available_files)
        prompt = f"""{self.system_prompt}

Available log files:
{available_files_text}

User request:
{user_query}

Remember: If you need to use a tool, respond ONLY with JSON: {{"tool": "tool_name", "arguments": {{...}}}}

What is the first tool you need to call?"""

        iteration = 0
        tool_phase_complete = False

        while iteration < max_iterations and not tool_phase_complete:
            iteration += 1

            # Get response from Gemini Pro
            try:
                full_prompt = prompt
                if conversation_history:
                    full_prompt += "\n\nPrevious conversation:\n" + "\n".join(conversation_history[-3:])

                response = self.model.generate_content(full_prompt)
                response_text = response.text.strip()

                # Try to extract tool request
                tool_request = self._extract_json_from_response(response_text)

                if tool_request:
                    # Execute tool via MCP server
                    tool_name = tool_request['tool']
                    tool_args = tool_request['arguments']

                    result = self.mcp_server.execute_tool(tool_name, tool_args)
                    tool_results.append({
                        'tool': tool_name,
                        'arguments': tool_args,
                        'result': result
                    })

                    # Update conversation history
                    conversation_history.append(f"Tool call: {tool_name} with args: {json.dumps(tool_args)}")
                    conversation_history.append(f"Tool result: {json.dumps(result, indent=2)}")

                    # Check if we need to continue or provide final answer
                    if result.get('success'):
                        if tool_name == 'analyze_logs':
                            # Tool phase is complete - exit loop and enter ANSWER MODE
                            tool_phase_complete = True
                        else:
                            # Continue with next tool
                            prompt = f"""Tool "{tool_name}" executed successfully. Result: {json.dumps(result, indent=2)}

What is the next tool you need to call? Remember: respond ONLY with JSON if calling a tool."""
                    else:
                        # Tool execution failed
                        error_prompt = f"""Tool execution failed: {result.get('error', 'Unknown error')}

What should you do next? You can try a different tool or provide an answer based on what you know."""
                        prompt = error_prompt
                else:
                    # No tool request found - retry with clearer instructions
                    prompt = f"""Your response was not valid JSON. Please respond ONLY with JSON in this format:
{{"tool": "tool_name", "arguments": {{"param": "value"}}}}

User question: {user_query}
Available tools: {', '.join(self.mcp_server.tools.keys())}"""

            except Exception as e:
                return {
                    'success': False,
                    'error': f'Error in agent processing: {str(e)}',
                    'tool_results': tool_results,
                    'final_answer': None
                }

        # ANSWER MODE: Generate final natural language response
        final_answer = None
        if tool_results:
            try:
                answer_prompt = f"""You are now in ANSWER MODE.

CRITICAL RULES FOR ANSWER MODE:
- Do NOT return JSON
- Do NOT request tools
- Do NOT include tool syntax in your response
- ONLY provide a natural language explanation for the user

User question:
{user_query}

Tool execution results:
{json.dumps(tool_results, indent=2)}

Provide a clear, concise explanation that directly answers the user's question.
Focus on insights, patterns, and key issues found in the logs."""

                answer_response = self.model.generate_content(
                    answer_prompt,
                    generation_config={"temperature": 0.4}
                )
                final_answer = answer_response.text.strip()

            except Exception as e:
                final_answer = f"Tool execution completed but failed to generate summary: {str(e)}"

        if not final_answer:
            final_answer = "I was unable to complete the analysis. Please check the tool execution results."

        return {
            'success': True,
            'final_answer': final_answer,
            'tool_results': tool_results,
            'iterations': iteration
        }
