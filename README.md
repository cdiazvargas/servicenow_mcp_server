# ServiceNow Knowledge MCP Server

A Python-based MCP (Model Context Protocol) server that integrates ServiceNow Knowledge Base with your company's OI (AI assistant), providing role-based access to knowledge articles with **JWT token authentication**.

## 🚀 Key Features

- **JWT Token Authentication**: Native support for JWT tokens as the primary authentication method
- **Async/Await**: Full asynchronous implementation for better performance
- **Structured Logging**: JSON-structured logging with configurable levels
- **Type Safety**: Complete type hints with Pydantic models
- **Better Error Handling**: Comprehensive error handling with detailed logging
- **Background Tasks**: Automatic session cleanup and maintenance

## 📋 Core Functionality

- **JWT Authentication**: Primary authentication using JWT tokens from your existing integration
- **OAuth 2.0 Fallback**: Falls back to OAuth when JWT is not available
- **Role-Based Access Control**: Respects ServiceNow user roles and permissions
- **Knowledge Search**: Comprehensive search across accessible knowledge articles
- **Context Synthesis**: Combines multiple articles into coherent responses
- **Real-time Status Updates**: Provides search progress feedback
- **Audit Logging**: All access is logged with actual user identity

## 🛠️ Prerequisites

- Python 3.9+
- ServiceNow instance with JWT token integration or OAuth 2.0 configured
- ServiceNow user account with appropriate knowledge base permissions
- MCP-compatible client (Claude Desktop, OI, etc.)

## ⚡ Quick Start

### 1. Setup Python Environment

```bash
# Navigate to project directory
cd "ServiceNow MCP Server"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
vim .env
```

**For JWT Authentication (Recommended):**
```env
SERVICENOW_INSTANCE_URL=https://your-company.service-now.com
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### 3. Run the Server

```bash
# Start the server
python -m servicenow_mcp_server.main

# With debug logging
LOG_LEVEL=debug python -m servicenow_mcp_server.main
```

### 4. Test Authentication

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

## 🔐 JWT Authentication Integration

Your JWT tokens should include the following claims:

```json
{
  "sub": "user-sys-id",           // ServiceNow user ID
  "username": "user.name",        // ServiceNow username  
  "roles": ["employee", "knowledge_reader"],  // User roles
  "iat": 1640995200,             // Issued at
  "exp": 1641081600,             // Expiration
  "iss": "your-company"          // Issuer (optional)
}
```

### Integration Example

```python
import jwt
from datetime import datetime, timedelta

def generate_servicenow_jwt(user_id: str, username: str, roles: list[str]) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "roles": roles,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iss": "your-company"
    }
    
    return jwt.encode(payload, "your-jwt-secret-key", algorithm="HS256")
```

## 🔧 MCP Tools Available

### 1. `authenticate_user`
Authenticate with JWT token or OAuth credentials

### 2. `search_knowledge`
Search ServiceNow knowledge articles with role-based access and synthesis

### 3. `get_article`
Retrieve specific knowledge articles

### 4. `get_user_context`
Get current user session information

### 5. `clear_user_session`
Clear user authentication session

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=servicenow_mcp_server

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

## 🏗️ Integration with OI

### Claude Desktop Integration

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

## 📊 Configuration Options

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SERVICENOW_INSTANCE_URL` | Your ServiceNow instance URL | Yes | - |
| `JWT_SECRET_KEY` | JWT secret key for token verification | Yes* | - |
| `JWT_ALGORITHM` | JWT algorithm | No | HS256 |
| `JWT_EXPIRATION_HOURS` | JWT token expiration in hours | No | 24 |
| `SERVICENOW_CLIENT_ID` | OAuth client ID (fallback) | Yes* | - |
| `SERVICENOW_CLIENT_SECRET` | OAuth client secret (fallback) | Yes* | - |
| `LOG_LEVEL` | Logging level (debug/info/warning/error) | No | info |
| `LOG_FORMAT` | Log format (json/text) | No | json |

*Either JWT or OAuth credentials must be provided.

## 🚀 Development

### Code Formatting

```bash
# Format code
black servicenow_mcp_server/
isort servicenow_mcp_server/

# Type checking
mypy servicenow_mcp_server/

# Linting
flake8 servicenow_mcp_server/
```

### Using Makefile

```bash
# See all available commands
make help

# Development setup
make dev-setup

# Run tests
make test

# Format code
make format

# Run all checks
make check-all
```

## 🐛 Troubleshooting

### Common Issues

1. **JWT Verification Failed:**
   ```bash
   # Check JWT secret configuration
   echo $JWT_SECRET_KEY
   
   # Verify JWT token format
   python -c "import jwt; print(jwt.decode('your-token', verify=False))"
   ```

2. **Import Errors:**
   ```bash
   # Ensure virtual environment is activated
   which python
   
   # Install in development mode
   pip install -e .
   ```

3. **ServiceNow Connection Issues:**
   ```bash
   # Test connectivity
   curl -I https://your-instance.service-now.com
   
   # Check configuration
   python -c "from servicenow_mcp_server.config import load_settings; print(load_settings())"
   ```

### Debug Mode

```bash
# Enable debug logging
LOG_LEVEL=debug python -m servicenow_mcp_server.main
```

## 📈 Example Scenarios

### Scenario 1: Employee Vacation Query
```
User: "What is our vacation policy?"
OI: → authenticate_user(jwt_token) → search_knowledge(query="vacation policy")
OI: Returns comprehensive policy with procedures and links
```

### Scenario 2: Manager Access to Sensitive Procedures
```
User: "How do I handle disciplinary actions?"
OI: → JWT with manager roles → search restricted management procedures
OI: Returns management-specific procedures (not accessible to regular employees)
```

### Scenario 3: Follow-up Context Maintenance
```
User: "What if I'm taking vacation during a company holiday?"
OI: → Contextual search with previous query context
OI: Returns specific holiday vacation policy information
```

## 📁 Project Structure

```
ServiceNow MCP Server/
├── servicenow_mcp_server/           # Python package
│   ├── __init__.py                  # Package initialization
│   ├── main.py                      # Entry point with CLI
│   ├── server.py                    # MCP server implementation
│   ├── auth.py                      # JWT + OAuth authentication
│   ├── servicenow_client.py         # Async ServiceNow API client
│   ├── knowledge_synthesis.py       # Knowledge synthesis service
│   ├── config.py                    # Configuration with Pydantic
│   ├── types.py                     # Type definitions
│   └── utils.py                     # Utility functions
├── tests/                           # Comprehensive test suite
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Modern Python packaging
├── Makefile                         # Development commands
├── QUICKSTART.md                    # 5-minute setup guide
└── .env.example                     # Environment template
```

## 📞 Support

For issues with the implementation:

1. Check the debug logs: `LOG_LEVEL=debug python -m servicenow_mcp_server.main`
2. Verify JWT token format and claims
3. Test ServiceNow connectivity
4. Review the comprehensive test suite for examples
5. See `QUICKSTART_PYTHON.md` for quick setup guide

## 🎉 Production Ready

The Python implementation is production-ready and includes:

- ✅ **JWT-first authentication** with your existing integration
- ✅ **Better async performance** with Python asyncio
- ✅ **Structured logging** with JSON output
- ✅ **Type safety** with Pydantic models
- ✅ **Comprehensive test suite** with pytest
- ✅ **Background task management** for maintenance

Your ServiceNow Knowledge MCP Server is ready to integrate with your company's OI system using JWT tokens!

## 📖 Additional Documentation

- **`QUICKSTART.md`** - Get running in 5 minutes
- **`DEPLOYMENT.md`** - Production deployment guide
- **`TESTING.md`** - Testing methodology and examples
- **`PROJECT_SUMMARY.md`** - Complete project overview