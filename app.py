"""
Streamlit UI for MCP-Based Log Analysis Agent

This module provides a simple web interface for interacting with
the log analysis agent powered by Gemini Pro and MCP tools.
"""

import streamlit as st
import json
import os
from agent import GeminiAgent


def format_tool_result(result: dict) -> str:
    """Format a tool result for display."""
    if result.get('success'):
        return json.dumps(result, indent=2)
    else:
        return f"Error: {result.get('error', 'Unknown error')}"


def display_analysis_results(tool_results: list):
    """Display structured analysis results from analyze_logs tool."""
    # Find the analyze_logs result
    analysis_result = None
    for tool_result in tool_results:
        if tool_result['tool'] == 'analyze_logs' and tool_result['result'].get('success'):
            analysis_result = tool_result['result']
            break
    
    if not analysis_result:
        return
    
    st.subheader("📊 Analysis Results")
    
    # Error counts
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Errors", analysis_result.get('error_count', 0))
    with col2:
        st.metric("Total Warnings", analysis_result.get('warning_count', 0))
    with col3:
        st.metric("Total Info Logs", analysis_result.get('info_count', 0))
    
    st.divider()
    
    # Log level distribution
    st.subheader("Log Level Distribution")
    level_dist = analysis_result.get('level_distribution', {})
    if level_dist:
        st.bar_chart(level_dist)
    
    st.divider()
    
    # Top services with errors
    st.subheader("Top Services with Errors")
    top_error_services = analysis_result.get('top_error_services', [])
    if top_error_services:
        error_data = {item['service']: item['count'] for item in top_error_services}
        st.bar_chart(error_data)
        
        # Display as table
        st.write("**Details:**")
        for item in top_error_services:
            st.write(f"- **{item['service']}**: {item['count']} errors")
    else:
        st.info("No errors found in logs.")
    
    st.divider()
    
    # Service statistics
    st.subheader("Service Statistics")
    service_stats = analysis_result.get('service_statistics', {})
    if service_stats:
        # Create a summary table
        stats_data = []
        for service, stats in service_stats.items():
            stats_data.append({
                'Service': service,
                'Total': stats['total'],
                'Errors': stats['errors'],
                'Warnings': stats['warnings'],
                'Info': stats['info']
            })
        st.dataframe(stats_data, use_container_width=True)
    
    st.divider()
    
    # Sample error logs
    error_samples = analysis_result.get('error_logs_sample', [])
    if error_samples:
        st.subheader("Sample Error Logs")
        with st.expander("View Error Samples"):
            for error_log in error_samples:
                st.code(f"[{error_log['timestamp']}] {error_log['level']} [{error_log['service']}] {error_log['message']}")


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="MCP Log Analysis Agent",
        page_icon="📋",
        layout="wide"
    )
    
    st.title("📋 MCP-Based Log Analysis Agent")
    st.markdown("**Powered by Gemini Pro + Model Context Protocol**")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            help="Enter your Google Gemini API key"
        )
        
        st.markdown("---")
        st.markdown("### 📖 About")
        st.markdown("""
        This application demonstrates the Model Context Protocol (MCP):
        
        - **LLM (Gemini Pro)**: Reasoning and decision-making
        - **MCP Server**: Tool execution (deterministic operations)
        - **Strict Separation**: LLM never accesses files directly
        
        The agent analyzes log files by:
        1. Reading the log file
        2. Parsing log entries
        3. Analyzing statistics
        4. Providing insights
        """)
    
    # Check if API key is provided
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API key in the sidebar to continue.")
        st.info("You can get a Gemini API key from: https://makersuite.google.com/app/apikey")
        return
    
    # Initialize agent
    try:
        agent = GeminiAgent(api_key)
    except Exception as e:
        st.error(f"Failed to initialize agent: {str(e)}")
        return
    
    # Main interface
    st.header("💬 Ask a Question About the Logs")

    # Analysis type selection
    analysis_type = st.radio(
        "Select analysis focus:",
        ["Overview", "Error-focused", "Warning-focused", "Service-focused"],
        horizontal=True
    )

    # File uploader for multiple files
    os.makedirs("data/uploads", exist_ok=True)
    uploaded_files = st.file_uploader(
        "Upload additional log files (.log or .txt)",
        type=["log", "txt"],
        accept_multiple_files=True
    )

    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

    # Save uploaded files and track their paths
    new_uploaded_paths = []
    if uploaded_files:
        for up in uploaded_files:
            safe_name = os.path.basename(up.name)
            dest_path = os.path.join("data/uploads", safe_name)
            with open(dest_path, "wb") as f:
                f.write(up.read())
            new_uploaded_paths.append(dest_path)

        # Update session state (deduplicate)
        current = set(st.session_state.uploaded_files)
        current.update(new_uploaded_paths)
        st.session_state.uploaded_files = sorted(current)

    available_files = ["data/application.log"] + st.session_state.get('uploaded_files', [])

    st.markdown("**Available log files:**")
    for fpath in available_files:
        st.write(f"- {fpath}")

    # Example queries
    example_queries = [
        "Analyze errors in the log file",
        "What are the top services with errors?",
        "Show me the log level distribution",
        "How many warnings are in the logs?",
        "Which service has the most errors?"
    ]
    
    st.markdown("**Example queries:**")
    cols = st.columns(len(example_queries))
    for i, query in enumerate(example_queries):
        with cols[i]:
            if st.button(query, key=f"example_{i}", use_container_width=True):
                st.session_state.user_query = query
    
    # User input
    user_query = st.text_input(
        "Your question:",
        value=st.session_state.get('user_query', ''),
        placeholder="e.g., Analyze errors in the log file"
    )
    
    # Analyze button
    if st.button("🔍 Analyze Logs", type="primary", use_container_width=True):
        if not available_files:
            st.error("No available log files. Upload a log or use the default.")
            return
        
        # Build combined prompt
        combined_prompt = f"Analysis type: {analysis_type}\nUser question: {user_query}\nAvailable log files: {available_files}"

        # Process query
        with st.spinner("🤖 Agent is analyzing logs..."):
            result = agent.process_query(combined_prompt, available_files=available_files)
        
        # Store result in session state
        st.session_state.analysis_result = result
        
        # Display results
        if result.get('success'):
            st.success("✅ Analysis complete!")
            
            # Display final answer
            st.header("🤖 Agent's Explanation")
            st.markdown(result.get('final_answer', 'No explanation provided.'))
            
            st.divider()
            
            # Display structured results
            tool_results = result.get('tool_results', [])
            if tool_results:
                display_analysis_results(tool_results)
                
                # Show tool execution history
                with st.expander("🔧 Tool Execution History"):
                    for i, tool_result in enumerate(tool_results, 1):
                        st.markdown(f"**Step {i}: {tool_result['tool']}**")
                        st.json(tool_result['result'])
                        st.markdown("---")
        else:
            st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            if result.get('tool_results'):
                st.json(result['tool_results'])
    
    # Display previous results if available
    if 'analysis_result' in st.session_state:
        result = st.session_state.analysis_result
        if result.get('success'):
            st.divider()
            st.header("📋 Previous Analysis")
            st.markdown(result.get('final_answer', ''))
            display_analysis_results(result.get('tool_results', []))


if __name__ == "__main__":
    main()
