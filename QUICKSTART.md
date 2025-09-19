# ServiceNow Knowledge MCP Server - Quick Start

Get your ServiceNow Knowledge MCP Server running in 5 minutes with JWT authentication!

## ⚡ Quick Setup

### 1. Prerequisites Check
- [ ] Python 3.9+ installed
- [ ] ServiceNow instance with JWT integration
- [ ] Your JWT secret key and algorithm

### 2. Python Environment Setup (1 minute)

```bash
# Navigate to project directory
cd "ServiceNow MCP Server"

# Create and activate virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
vim .env
```

**For JWT Authentication (Recommended):**
```env
SERVICENOW_INSTANCE_URL=https://your-company.service-now.com
JWT_SECRET_KEY=your-jwt-secret-key-from-existing-integration
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
LOG_LEVEL=info
```

**For OAuth Fallback (if no JWT):**
```env
SERVICENOW_INSTANCE_URL=https://your-company.service-now.com
SERVICENOW_CLIENT_ID=your-oauth-client-id
SERVICENOW_CLIENT_SECRET=your-oauth-client-secret
LOG_LEVEL=info
```

### 4. Start the Server (30 seconds)

```bash
# Start the server
python -m servicenow_mcp_server.main

# Or with debug logging
LOG_LEVEL=debug python -m servicenow_mcp_server.main
```

You should see:
```
[2024-12-17T10:30:00Z] INFO: Starting ServiceNow Knowledge MCP Server
[2024-12-17T10:30:00Z] INFO: Instance URL: https://your-company.service-now.com
[2024-12-17T10:30:00Z] INFO: Auth method: jwt
[2024-12-17T10:30:00Z] INFO: Background tasks started
```

### 5. Test with JWT Token (1 minute)

In another terminal, test with your JWT token:

```bash
# Test JWT authentication
echo '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "authenticate_user",
    "arguments": {
      "jwt_token": "your-jwt-token-here"
    }
  }
}' | python -m servicenow_mcp_server.main
```

Expected success response:
```json
{
  "success": true,
  "user_id": "user-sys-id",
  "username": "user.name",
  "roles": ["employee", "knowledge_reader"],
  "expires_at": "2024-12-17T15:30:00Z",
  "message": "Successfully authenticated via JWT. User has 2 role(s): employee, knowledge_reader"
}
```

## 🧪 Test Knowledge Search

Once authenticated, test knowledge search:

```bash
echo '{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "query": "vacation policy",
      "user_id": "your-user-id-from-auth-response",
      "synthesize": true
    }
  }
}' | python -m servicenow_mcp_server.main
```

## 🔧 JWT Token Generation

If you need to generate JWT tokens for testing:

```python
import jwt
from datetime import datetime, timedelta

def generate_test_jwt():
    payload = {
        "sub": "test-user-123",
        "username": "test.user",
        "roles": ["employee", "knowledge_reader"],
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=24)).timestamp()),
        "iss": "test-issuer"
    }
    
    return jwt.encode(payload, "your-jwt-secret-key", algorithm="HS256")

# Generate and print test token
print(generate_test_jwt())
```

## 🔧 Integration with OI/Claude Desktop

### For Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "servicenow-knowledge": {
      "command": "python",
      "args": ["-m", "servicenow_mcp_server.main"],
      "cwd": "/path/to/ServiceNow MCP Server",
      "env": {
        "SERVICENOW_INSTANCE_URL": "https://your-company.service-now.com",
        "JWT_SECRET_KEY": "your-jwt-secret-key"
      }
    }
  }
}
```

### For Custom OI Integration

```python
import asyncio
from mcp.client import ClientSession, StdioServerParameters

async def test_oi_integration():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "servicenow_mcp_server.main"],
        env={"JWT_SECRET_KEY": "your-secret"}
    )
    
    async with ClientSession(server_params) as session:
        await session.initialize()
        
        # Your OI can now use the MCP tools
        result = await session.call_tool("search_knowledge", {
            "query": "vacation policy",
            "user_id": "user-123"
        })
```

## 🎪 Demo Scenarios

### Scenario 1: Employee with JWT Token
```python
# Your existing auth system generates:
jwt_token = generate_jwt_for_user(user_id="emp123", roles=["employee"])

# OI calls:
authenticate_user(jwt_token=jwt_token)
search_knowledge(query="What is our vacation policy?", user_id="emp123")
```

### Scenario 2: Manager with Elevated Access
```python
# Manager JWT with additional roles:
jwt_token = generate_jwt_for_user(
    user_id="mgr456", 
    roles=["employee", "manager", "knowledge_reader"]
)

# Manager can access management procedures:
search_knowledge(query="disciplinary procedures", user_id="mgr456")
```

## 🚨 Troubleshooting

### "JWT decode failed"
```bash
# Check JWT secret in environment
echo $JWT_SECRET_KEY

# Verify JWT token claims
python -c "import jwt; print(jwt.decode('your-token', verify=False))"

# Check algorithm match
grep JWT_ALGORITHM .env
```

### "Module not found" 
```bash
# Ensure virtual environment is activated
which python

# Check if in virtual environment
echo $VIRTUAL_ENV

# Reinstall in development mode
pip install -e .
```

### "ServiceNow connection failed"
```bash
# Test ServiceNow connectivity
curl -I https://your-instance.service-now.com

# Check configuration loading
python -c "from servicenow_mcp_server.config import load_settings; print(load_settings().servicenow_instance_url)"
```

### Server won't start
```bash
# Check Python version (needs 3.9+)
python --version

# Check dependencies
pip install -r requirements.txt

# Try with debug logging
LOG_LEVEL=debug python -m servicenow_mcp_server.main
```

## 🧪 Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=servicenow_mcp_server

# Run specific test
pytest tests/unit/test_knowledge_synthesis.py -v
```

## 📊 Development Commands

```bash
# Format code
black servicenow_mcp_server/
isort servicenow_mcp_server/

# Type checking
mypy servicenow_mcp_server/

# Run linting
flake8 servicenow_mcp_server/

# Install in development mode
pip install -e ".[dev]"
```

## 📈 Next Steps

1. **Review Documentation**: Check `README.md` for detailed configuration
2. **Set Up JWT Integration**: Connect with your existing JWT auth system
3. **Create Test Knowledge Articles**: Set up sample articles in ServiceNow
4. **Production Deployment**: Follow deployment best practices for Python apps

## 🎯 Key Features

- **JWT-first authentication** for seamless integration
- **Async/await** for high performance
- **Structured logging** with JSON output
- **Type safety** with Pydantic models
- **Comprehensive test suite** with pytest
- **Background task management** for maintenance

## 🎉 Congratulations!

Your ServiceNow Knowledge MCP Server is now running with JWT authentication! 

The server provides powerful knowledge search and synthesis capabilities with:
- ✅ JWT-first authentication
- ✅ High-performance async operations
- ✅ Structured logging
- ✅ Type safety with Pydantic
- ✅ Easy integration with existing JWT systems

Your OI can now access ServiceNow knowledge articles with proper role-based security!
