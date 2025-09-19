#!/bin/bash

# ServiceNow MCP Server Startup Script with Environment
# This ensures all environment variables are properly set before starting the server

# Change to the correct directory, this is an example
cd "/Users/yourUser/Documents/Cursor Projects/ServiceNow MCP Server"

# Set all required environment variables
export PYTHONPATH="Path to your project"
export SERVICENOW_INSTANCE_URL="https://yourinstance.service-now.com/"
export SERVICENOW_CLIENT_ID="servicenow_client_id"
export SERVICENOW_CLIENT_SECRET="servicenow_client_secret"
export JWT_SECRET_KEY="your-jwt-secret-key-here"
export JWT_ALGORITHM="HS256"
export JWT_EXPIRATION_HOURS="24"
export LOG_LEVEL="info"
export LOG_FORMAT="json"
export AUTH_TIMEOUT_SECONDS="300"
export SESSION_REFRESH_THRESHOLD_SECONDS="600"
export MAX_CONCURRENT_SESSIONS="100"
export SERVICENOW_API_TIMEOUT="30"
export SERVICENOW_MAX_RETRIES="3"
export SERVICENOW_RETRY_DELAY="1.0"

# Start the server with the virtual environment Python
exec "Your Project Folder/venv/bin/python" -m servicenow_mcp_server.main
