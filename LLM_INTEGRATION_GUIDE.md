# 🤖 LLM Integration Guide for ServiceNow MCP Server

Your ServiceNow MCP server is ready for LLM integration! Here's how to test it with actual LLMs using the Python implementation.

## 🎯 Quick Start Options

### Option 1: Claude Desktop (Recommended - Easiest)

1. **Install Claude Desktop**: https://claude.ai/download

2. **Configure Claude Desktop**:
   ```bash
   # Copy the config file to Claude's directory
   cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Restart Claude Desktop**

4. **Test it**:
   - Open Claude Desktop
   - Ask: "What ServiceNow tools do you have available?"
   - Ask: "Help me find information about vacation policies"
   - Ask: "Search for password requirements in ServiceNow"

### Option 2: Python MCP Client

1. **Install MCP client**:
   ```bash
   pip install mcp
   ```

2. **Create test script**:
   ```python
   import asyncio
   import json
   from mcp.client.session import ClientSession
   from mcp.client.stdio import stdio_client
   from mcp import StdioServerParameters

   async def test_servicenow_mcp():
       # Connect to ServiceNow MCP server
       server_params = StdioServerParameters(
           command="python",
           args=["-m", "servicenow_mcp_server.main"],
           env={
               "SERVICENOW_INSTANCE_URL": "https://your-instance.service-now.com",
               "JWT_SECRET_KEY": "your-jwt-secret"
           }
       )

       async with stdio_client(server_params) as (read, write):
           async with ClientSession(read, write) as session:
               await session.initialize()
               
               # List available tools
               tools = await session.list_tools()
               print("Available tools:", [tool.name for tool in tools.tools])
               
               # Test JWT authentication
               result = await session.call_tool("authenticate_user", {
                   "jwt_token": "your-jwt-token-here"
               })
               print("Auth result:", result.content)
               
               # Test knowledge search
               search_result = await session.call_tool("search_knowledge", {
                   "query": "vacation policy",
                   "user_id": "user-from-auth-result",
                   "synthesize": True
               })
               print("Search result:", search_result.content)

   # Run the test
   asyncio.run(test_servicenow_mcp())
   ```

### Option 3: Custom LLM Integration

Use the provided test scripts:
```bash
# Test the complete integration flow
python test_mcp_integration.py

# Test with simulated conversations
python test_ollama_integration.py
```

## 🔧 Production Setup

### 1. Environment Configuration

Ensure your `.env` file has real ServiceNow credentials:
```env
# Primary authentication (JWT)
SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com/
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Fallback authentication (OAuth)
SERVICENOW_CLIENT_ID=your_oauth_client_id
SERVICENOW_CLIENT_SECRET=your_oauth_client_secret

# Logging and performance
LOG_LEVEL=info
LOG_FORMAT=json
```

### 2. JWT Token Integration

For seamless corporate integration:

```python
import jwt
from datetime import datetime, timedelta

def generate_servicenow_jwt(user_id: str, username: str, roles: list[str]) -> str:
    """Generate JWT token for ServiceNow MCP integration."""
    payload = {
        "sub": user_id,           # ServiceNow user sys_id
        "username": username,     # ServiceNow username
        "roles": roles,           # User's ServiceNow roles
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp()),
        "iss": "your-company"     # Your company identifier
    }
    
    return jwt.encode(payload, "your-jwt-secret-key", algorithm="HS256")

# Example: Generate token for employee
employee_token = generate_servicenow_jwt(
    user_id="emp123456",
    username="john.doe",
    roles=["employee", "knowledge"]
)

# Example: Generate token for manager  
manager_token = generate_servicenow_jwt(
    user_id="mgr789012", 
    username="jane.manager",
    roles=["employee", "manager", "knowledge", "knowledge_admin"]
)
```

### 3. LLM Configuration Examples

#### For Claude Desktop:
```json
{
  "mcpServers": {
    "servicenow-knowledge": {
      "command": "python",
      "args": ["-m", "servicenow_mcp_server.main"],
      "cwd": "/path/to/ServiceNow MCP Server",
      "env": {
        "SERVICENOW_INSTANCE_URL": "https://your-company.service-now.com",
        "JWT_SECRET_KEY": "your-jwt-secret-key",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

#### For Ollama + MCP:
```bash
# Install Ollama and MCP support
curl -fsSL https://ollama.ai/install.sh | sh
pip install mcp

# Create Ollama MCP configuration
cat > ~/.ollama/mcp_config.json << EOF
{
  "mcp_servers": {
    "servicenow": {
      "command": "python",
      "args": ["-m", "servicenow_mcp_server.main"],
      "env": {
        "SERVICENOW_INSTANCE_URL": "https://your-instance.service-now.com",
        "JWT_SECRET_KEY": "your-jwt-secret"
      }
    }
  }
}
EOF
```

#### For Custom Python LLM:
```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters

class ServiceNowLLMIntegration:
    def __init__(self, jwt_secret: str, instance_url: str):
        self.server_params = StdioServerParameters(
            command="python",
            args=["-m", "servicenow_mcp_server.main"],
            env={
                "SERVICENOW_INSTANCE_URL": instance_url,
                "JWT_SECRET_KEY": jwt_secret,
                "LOG_LEVEL": "info"
            }
        )
        self.session = None
    
    async def start(self):
        """Start MCP session."""
        self.read, self.write = await stdio_client(self.server_params).__aenter__()
        self.session = await ClientSession(self.read, self.write).__aenter__()
        await self.session.initialize()
    
    async def authenticate_user(self, jwt_token: str):
        """Authenticate user with JWT token."""
        return await self.session.call_tool("authenticate_user", {
            "jwt_token": jwt_token
        })
    
    async def search_knowledge(self, query: str, user_id: str, synthesize: bool = True):
        """Search ServiceNow knowledge base."""
        return await self.session.call_tool("search_knowledge", {
            "query": query,
            "user_id": user_id,
            "synthesize": synthesize
        })
    
    async def process_user_query(self, user_query: str, jwt_token: str):
        """Process complete user query with authentication and search."""
        # Authenticate
        auth_result = await self.authenticate_user(jwt_token)
        if not auth_result.content[0].text:
            raise Exception("Authentication failed")
        
        auth_data = json.loads(auth_result.content[0].text)
        user_id = auth_data["user_id"]
        
        # Search knowledge
        search_result = await self.search_knowledge(user_query, user_id)
        return search_result.content[0].text

# Usage example
async def main():
    integration = ServiceNowLLMIntegration(
        jwt_secret="your-jwt-secret",
        instance_url="https://your-instance.service-now.com"
    )
    
    await integration.start()
    
    # Process user queries
    user_jwt = generate_servicenow_jwt("user123", "john.doe", ["employee"])
    response = await integration.process_user_query(
        "What is our vacation policy?", 
        user_jwt
    )
    
    print("LLM Response:", response)

asyncio.run(main())
```

## 💬 Example LLM Conversations

Once connected, you can have conversations like:

### JWT Authentication Flow
**User**: "What's our company's vacation policy?"

**LLM Process**:
1. Detects ServiceNow query
2. Requests JWT token from user context
3. Calls `authenticate_user` tool
4. Calls `search_knowledge` tool
5. Synthesizes response

**LLM Response**: "Based on your ServiceNow knowledge base, here's your vacation policy: [comprehensive synthesized response with procedures and links]"

### OAuth Fallback Flow
**User**: "How do I reset my password?"

**LLM Process**:
1. Attempts JWT authentication (if configured)
2. Falls back to OAuth credential request
3. Authenticates with ServiceNow
4. Searches for password reset procedures
5. Returns step-by-step instructions

**LLM Response**: "Here are the steps to reset your password: [step-by-step procedure from ServiceNow knowledge base]"

### Manager-Level Query
**User**: "What are the disciplinary procedures for employees?"

**LLM Process**:
1. Authenticates with JWT containing manager roles
2. Searches manager-restricted knowledge articles
3. Returns sensitive management procedures
4. Maintains audit trail

**LLM Response**: "Based on your manager-level access, here are the disciplinary procedures: [management-specific content]"

## 🔍 Available Tools

Your LLM will have access to these ServiceNow tools:

1. **authenticate_user** 
   - JWT token authentication (primary)
   - OAuth credential authentication (fallback)
   - Returns user context with roles

2. **search_knowledge** 
   - Search with role-based filtering
   - Intelligent response synthesis
   - Follow-up suggestions

3. **get_article** 
   - Retrieve specific articles by ID
   - Respect access permissions
   - Return formatted content

4. **get_user_context** 
   - Get current session info
   - Check permissions and roles
   - Validate session status

5. **clear_user_session** 
   - Sign out user
   - Clear authentication
   - Security cleanup

## 🚀 Testing Workflow

### 1. Start with Tool Discovery
```python
tools = await session.list_tools()
print("Available tools:", [tool.name for tool in tools.tools])
```

### 2. Test JWT Authentication
```python
auth_result = await session.call_tool("authenticate_user", {
    "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
})
```

### 3. Test Knowledge Search
```python
search_result = await session.call_tool("search_knowledge", {
    "query": "vacation policy",
    "user_id": "user123",
    "synthesize": True
})
```

### 4. Test Error Handling
```python
# Test with invalid JWT
try:
    await session.call_tool("authenticate_user", {"jwt_token": "invalid"})
except Exception as e:
    print("Expected error:", e)
```

## 🛠️ Troubleshooting

### Common Issues:

1. **"Tools not found"**: 
   ```bash
   # Check server startup
   python -m servicenow_mcp_server.main
   
   # Verify server responds
   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m servicenow_mcp_server.main
   ```

2. **"JWT authentication failed"**:
   ```bash
   # Verify JWT secret
   echo $JWT_SECRET_KEY
   
   # Test JWT token format
   python -c "import jwt; print(jwt.decode('your-token', verify=False))"
   ```

3. **"ServiceNow connection failed"**:
   ```bash
   # Test ServiceNow connectivity
   curl -I https://your-instance.service-now.com
   
   # Check environment variables
   python -c "from servicenow_mcp_server.config import load_settings; print(load_settings())"
   ```

4. **"Permission denied"**:
   - Check user roles in ServiceNow
   - Verify knowledge article permissions
   - Ensure articles are published

### Debug Commands:
```bash
# Start server with debug logging
LOG_LEVEL=debug python -m servicenow_mcp_server.main

# Run integration tests
python test_mcp_integration.py

# Test specific authentication
python -c "
import asyncio
from servicenow_mcp_server.auth import AuthenticationManager
from servicenow_mcp_server.config import load_settings

async def test_auth():
    config = load_settings()
    auth_mgr = AuthenticationManager(config)
    result = await auth_mgr.authenticate_with_jwt('your-jwt-token')
    print('Auth result:', result)

asyncio.run(test_auth())
"
```

## 🎯 Success Metrics

Your integration is working when:
- ✅ LLM can discover all 5 ServiceNow tools
- ✅ JWT authentication succeeds with proper role extraction
- ✅ OAuth fallback works for non-JWT scenarios
- ✅ Knowledge search returns relevant results
- ✅ Role-based access control is enforced
- ✅ Response synthesis provides comprehensive answers
- ✅ Error handling gracefully manages failures

## 🔄 Next Steps

1. **Production Deployment**: Deploy to your production environment with proper secrets management
2. **JWT Integration**: Connect with your existing corporate authentication system
3. **User Training**: Train users on how to ask effective ServiceNow questions
4. **Monitoring**: Set up logging and monitoring for usage patterns
5. **Customization**: Add more ServiceNow tools as business needs expand

## 📊 Performance Optimization

### Connection Pooling
```python
# Configure connection pooling in client
import httpx

async_client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    timeout=httpx.Timeout(10.0)
)
```

### Caching Strategy
```python
# Implement response caching
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=100)
def cache_knowledge_search(query: str, user_roles: str):
    # Cache search results for identical queries and roles
    pass
```

### Async Best Practices
```python
# Use async/await for all ServiceNow calls
async def batch_knowledge_search(queries: list[str], user_id: str):
    tasks = [
        session.call_tool("search_knowledge", {"query": q, "user_id": user_id})
        for q in queries
    ]
    return await asyncio.gather(*tasks)
```

---

🎉 **Congratulations!** Your ServiceNow MCP server is ready for production LLM integration with comprehensive JWT authentication and knowledge synthesis capabilities!
