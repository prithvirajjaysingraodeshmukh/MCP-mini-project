# MCP-Based Log Analysis Agent using Gemini Pro

A complete implementation of a log analysis system that demonstrates the Model Context Protocol (MCP) architecture, where an LLM (Gemini Pro) performs reasoning and decision-making, while an MCP server handles all deterministic tool execution.

## What is MCP?

**Model Context Protocol (MCP)** is an architectural pattern that enforces strict separation between:

1. **Reasoning Layer (LLM)**: The language model makes decisions about what actions to take
2. **Execution Layer (MCP Server)**: A deterministic server that executes tools based on LLM requests

### Key Principles

- **LLM Never Accesses Files Directly**: The LLM cannot read files, execute code, or access the filesystem
- **Tool-Based Execution**: All operations must go through registered tools via the MCP server
- **Strict JSON Communication**: The LLM communicates tool requests using strict JSON format only
- **Validation & Security**: The MCP server validates all tool requests against an allow-list

## Why Gemini Pro?

Gemini Pro was chosen for this project because:

1. **Strong Reasoning Capabilities**: Excellent at understanding user queries and determining appropriate tool sequences
2. **JSON Generation**: Reliable JSON output when properly prompted
3. **Cost-Effective**: Competitive pricing for API usage
4. **Accessibility**: Easy to integrate via Google's Generative AI SDK

## Architecture

```
┌─────────────┐
│   User UI   │  (Streamlit)
│  (app.py)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Agent     │  (agent.py)
│ Gemini Pro  │  • Receives user query
│             │  • Decides which tools to call
│             │  • Formats tool requests as JSON
└──────┬──────┘
       │ JSON tool requests
       ▼
┌─────────────┐
│ MCP Server  │  (mcp_server.py)
│             │  • Validates tool requests
│             │  • Executes tools
│             │  • Returns results
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Tools    │  (tools.py)
│             │  • read_file()
│             │  • parse_logs()
│             │  • analyze_logs()
└─────────────┘
```

### Component Responsibilities

1. **app.py (Streamlit UI)**
   - Provides web interface for user interaction
   - Displays analysis results and agent explanations
   - Shows structured data (charts, tables, metrics)

2. **agent.py (Gemini Pro Agent)**
   - Manages conversation with Gemini Pro
   - Enforces strict JSON tool request format
   - Coordinates tool execution via MCP server
   - Synthesizes final answers from tool results

3. **mcp_server.py (MCP Server)**
   - Registers available tools
   - Validates tool requests against allow-list
   - Executes tools and returns results
   - Enforces security boundaries

4. **tools.py (Tool Implementations)**
   - `read_file()`: Reads log files from filesystem
   - `parse_logs()`: Parses raw log text into structured format
   - `analyze_logs()`: Computes statistics and insights

## How Tool Execution is Separated from Reasoning

### The Separation

1. **LLM (Gemini Pro)**:
   - Receives user query
   - Reasons about what information is needed
   - Decides which tools to call and in what order
   - Formats tool requests as JSON: `{"tool": "tool_name", "arguments": {...}}`
   - **Cannot** access files, execute code, or perform operations directly

2. **MCP Server**:
   - Receives JSON tool requests from LLM
   - Validates tool name against allow-list
   - Validates arguments match tool requirements
   - Executes the tool function
   - Returns deterministic results

3. **Tools**:
   - Implement deterministic operations
   - Have no knowledge of the LLM
   - Return structured results

### Example Flow

```
User: "Analyze errors in the log file"

1. Agent sends query to Gemini Pro
2. Gemini Pro responds: {"tool": "read_file", "arguments": {"file_path": "data/application.log"}}
3. MCP Server validates and executes read_file()
4. Result returned to Agent
5. Agent sends result + next step to Gemini Pro
6. Gemini Pro responds: {"tool": "parse_logs", "arguments": {"log_text": "..."}}
7. MCP Server executes parse_logs()
8. Process continues until analysis complete
9. Gemini Pro synthesizes final answer from all tool results
```

## Project Structure

```
mcp-log-agent/
├── app.py              # Streamlit UI
├── agent.py            # Gemini Pro interaction and coordination
├── mcp_server.py       # MCP server with tool registry
├── tools.py            # Tool implementations
├── data/
│   └── application.log # Sample log file
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Installation

1. **Clone or download this project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Get a Gemini API key**:
   - Visit: https://makersuite.google.com/app/apikey
   - Create a new API key
   - Copy the key

## Running the Project

1. **Start the Streamlit application**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser**:
   - The app will open automatically at `http://localhost:8501`
   - Or navigate manually to the URL shown in the terminal

3. **Configure the app**:
   - Enter your Gemini API key in the sidebar
   - Optionally adjust the log file path (default: `data/application.log`)

4. **Ask questions**:
   - Type a question about the logs (e.g., "Analyze errors in the log file")
   - Click "Analyze Logs"
   - View the agent's explanation and structured results

## Example Queries

- "Analyze errors in the log file"
- "What are the top services with errors?"
- "Show me the log level distribution"
- "How many warnings are in the logs?"
- "Which service has the most errors?"

## Features

- ✅ **Strict MCP Architecture**: LLM never accesses files directly
- ✅ **JSON-Only Tool Requests**: Enforced strict JSON format
- ✅ **Tool Validation**: All tool requests validated against allow-list
- ✅ **Structured Analysis**: Error counts, log level distribution, service statistics
- ✅ **Interactive UI**: Streamlit interface with charts and tables
- ✅ **Complete Implementation**: No placeholders, fully runnable

## Technical Details

### Tool Request Format

The LLM must request tools using this exact JSON format:

```json
{
  "tool": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

### Available Tools

1. **read_file(file_path: str)**
   - Reads a log file from the filesystem
   - Returns file content and metadata

2. **parse_logs(log_text: str)**
   - Parses raw log text
   - Extracts timestamp, level, service, message
   - Returns structured log entries

3. **analyze_logs(parsed_logs: list)**
   - Analyzes parsed log entries
   - Computes statistics (error counts, distributions)
   - Identifies top services with errors
   - Returns comprehensive analysis

### Error Handling

- Invalid JSON responses are retried once with clearer instructions
- Tool execution errors are returned to the LLM for handling
- File not found errors are caught and reported
- All errors are displayed in the UI

## License

This project is provided as-is for educational and demonstration purposes.

## Notes

- The sample log file (`data/application.log`) contains realistic log entries with various log levels and services
- The agent is configured with a maximum of 10 tool call iterations to prevent infinite loops
- All tool executions are logged and displayed in the UI for transparency
