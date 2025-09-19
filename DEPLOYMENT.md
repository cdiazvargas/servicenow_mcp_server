# ServiceNow Knowledge MCP Server - Deployment Guide

This guide covers deploying the Python ServiceNow Knowledge MCP Server in various environments.

## Prerequisites

- Python 3.9 or higher
- ServiceNow instance with JWT integration or OAuth 2.0 configured
- MCP-compatible client (Claude Desktop, OI, etc.)

## Environment Setup

### 1. ServiceNow Configuration

Before deploying, ensure your ServiceNow instance is properly configured:

#### OAuth Application Setup (Fallback Authentication)
1. Navigate to **System OAuth > Application Registry**
2. Click **New** → **Create an OAuth API endpoint for external clients**
3. Configure the application:
   ```
   Name: ServiceNow Knowledge MCP Server
   Client ID: [Generate or use custom ID]
   Client Secret: [Generate secure secret]
   Grant Types: ✓ Password ✓ Refresh Token ✓ Client Credentials
   ```

#### JWT Integration Setup (Primary Authentication)
1. Configure JWT secret key in your existing authentication system
2. Ensure JWT tokens include required claims:
   - `sub`: ServiceNow user sys_id
   - `username`: ServiceNow username
   - `roles`: User's ServiceNow roles array
   - `iat`: Issued at timestamp
   - `exp`: Expiration timestamp
3. Use the same JWT secret for both your auth system and MCP server

#### User Roles and Permissions
Ensure users have appropriate roles:
- `knowledge` - Basic knowledge article access (standard ServiceNow role)
- `knowledge_manager` - Full knowledge management (if needed)
- Custom roles based on your organizational structure

#### Knowledge Base Configuration
1. Verify knowledge articles are properly categorized
2. Set appropriate access controls (roles, user criteria)
3. Ensure articles are in "Published" state
4. Test search functionality in ServiceNow UI

### 2. Python Environment Setup

Create Python environment and configuration:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy example configuration
cp .env.example .env

# Edit configuration
vim .env
```

Required environment variables:
```env
# ServiceNow Instance
SERVICENOW_INSTANCE_URL=https://your-company.service-now.com

# JWT Authentication (Primary)
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# OAuth Authentication (Fallback)
SERVICENOW_CLIENT_ID=your-oauth-client-id
SERVICENOW_CLIENT_SECRET=your-oauth-client-secret

# Logging and Performance
LOG_LEVEL=info
LOG_FORMAT=json
```

## Deployment Options

### Option 1: Local Development

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies with development tools
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Start in development mode
python -m servicenow_mcp_server.main

# Or with debug logging
LOG_LEVEL=debug python -m servicenow_mcp_server.main
```

### Option 2: Production Server

```bash
# Activate virtual environment
source venv/bin/activate

# Install production dependencies only
pip install -r requirements.txt --no-dev

# Start server
python -m servicenow_mcp_server.main

# Or with production configuration
LOG_LEVEL=info LOG_FORMAT=json python -m servicenow_mcp_server.main
```

### Option 3: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the package
RUN pip install -e .

# Create non-root user
RUN addgroup --gid 1001 --system python
RUN adduser --uid 1001 --system --group python
USER python

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
  CMD python -c "import sys; sys.exit(0)"

# Start application
CMD ["python", "-m", "servicenow_mcp_server.main"]
```

Build and run:
```bash
# Build Docker image
docker build -t servicenow-mcp-server .

# Run container
docker run -d \
  --name servicenow-mcp \
  --env-file .env \
  servicenow-mcp-server
```

### Option 4: Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  servicenow-mcp:
    build: .
    container_name: servicenow-knowledge-mcp
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
```

Deploy:
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f servicenow-mcp

# Stop services
docker-compose down
```

## MCP Client Integration

### Claude Desktop Integration

Add to Claude Desktop configuration file (`claude_desktop_config.json`):

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
        "SERVICENOW_CLIENT_ID": "your-client-id",
        "SERVICENOW_CLIENT_SECRET": "your-client-secret",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

### OI Integration

Configure OI to use the MCP server:

1. **Add MCP Server Configuration:**
   ```json
   {
     "mcpServers": [
       {
         "name": "servicenow-knowledge",
         "transport": "stdio",
         "command": "python",
         "args": ["-m", "servicenow_mcp_server.main"],
         "cwd": "/path/to/ServiceNow MCP Server",
         "env": {
           "SERVICENOW_INSTANCE_URL": "https://your-company.service-now.com",
           "JWT_SECRET_KEY": "your-jwt-secret-key",
           "SERVICENOW_CLIENT_ID": "your-client-id",
           "SERVICENOW_CLIENT_SECRET": "your-client-secret"
         }
       }
     ]
   }
   ```

2. **Configure Authentication Flow:**
   - **Primary**: OI passes JWT tokens from corporate auth system to `authenticate_user` tool
   - **Fallback**: OI prompts users for ServiceNow credentials for OAuth authentication
   - Session context is maintained for subsequent requests
   - Role-based access automatically enforced based on JWT claims or ServiceNow user roles

## Monitoring and Logging

### Log Configuration

Set appropriate log levels for different environments:

```bash
# Development - verbose logging
LOG_LEVEL=debug

# Staging - standard logging
LOG_LEVEL=info

# Production - minimal logging
LOG_LEVEL=warn
```

### Health Checks

The MCP server includes built-in health monitoring through structured logging:

```python
# Health check via process monitoring
ps aux | grep "servicenow_mcp_server.main"

# Check server responsiveness
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python -m servicenow_mcp_server.main

# Monitor via logs
tail -f logs/servicenow_mcp.log | grep "health\|error\|authentication"
```

### Monitoring Integration

Monitor key metrics:
- Authentication success/failure rates
- Knowledge search response times
- Session expiry rates
- API error rates

Sample monitoring queries:
```bash
# Authentication failures
grep "Authentication failed" logs/*.log | wc -l

# Search performance
grep "Knowledge search" logs/*.log | grep "duration"

# Session expiries
grep "Session expired" logs/*.log | wc -l
```

## Security Considerations

### Production Security Checklist

- [ ] ServiceNow instance uses HTTPS
- [ ] OAuth client secret is securely stored
- [ ] Environment variables are not logged
- [ ] User credentials are not persisted
- [ ] Session tokens expire appropriately
- [ ] Network access is restricted (if applicable)
- [ ] Regular security updates are applied

### Network Security

If deploying on-premises:
```bash
# Restrict network access
iptables -A INPUT -p tcp --dport 3000 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 3000 -j DROP
```

### SSL/TLS Configuration

Ensure ServiceNow communication uses TLS 1.2+ (automatically handled by httpx):
```python
# TLS configuration is handled automatically by httpx client
# Verify TLS settings in client logs:
LOG_LEVEL=debug python -m servicenow_mcp_server.main

# Check TLS version in use:
python -c "
import httpx
import ssl
print(f'Default SSL context: {ssl.create_default_context().protocol}')
"
```

## Troubleshooting Deployment

### Common Issues

1. **OAuth Configuration Errors:**
   ```bash
   # Test OAuth setup
   curl -X POST https://your-instance.service-now.com/oauth_token.do \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "grant_type=password&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&username=test&password=test"
   ```

2. **Network Connectivity:**
   ```bash
   # Test ServiceNow connectivity
   curl -I https://your-instance.service-now.com
   
   # Test from container
   docker exec servicenow-mcp curl -I https://your-instance.service-now.com
   ```

3. **Permission Issues:**
   ```bash
   # Check user roles
   curl -X GET "https://your-instance.service-now.com/api/now/table/sys_user_has_role?sysparm_query=user=YOUR_USER_ID" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### Debug Mode

Enable debug logging for troubleshooting:
```bash
LOG_LEVEL=debug python -m servicenow_mcp_server.main

# Or with structured logging output
LOG_LEVEL=debug LOG_FORMAT=json python -m servicenow_mcp_server.main

# Debug specific components
PYTHONPATH=. python -c "
import asyncio
from servicenow_mcp_server.config import load_settings
from servicenow_mcp_server.auth import AuthenticationManager

async def debug_auth():
    settings = load_settings()
    config = settings.to_servicenow_config()
    auth_mgr = AuthenticationManager(config)
    print(f'Auth manager initialized: {auth_mgr}')

asyncio.run(debug_auth())
"
```

### Performance Tuning

For high-volume environments:
```env
# JWT token expiration (longer for better performance)
JWT_EXPIRATION_HOURS=8  # 8 hours instead of default 24

# Adjust API timeouts
API_TIMEOUT_SECONDS=30  # ServiceNow API timeout

# Optimize search performance
KNOWLEDGE_SEARCH_LIMIT=10  # Limit search results
SYNTHESIS_MAX_ARTICLES=5   # Max articles for synthesis

# Logging optimization
LOG_LEVEL=warn  # Reduce log verbosity in production
LOG_FORMAT=json  # Structured logging for better parsing
```

## Scaling Considerations

### Horizontal Scaling

The MCP server is stateless except for session management. For horizontal scaling:

1. **Use External Session Store:**
   - Redis for session management
   - Database for persistent storage

2. **Load Balancing:**
   - Not typically needed for MCP servers
   - Each client connects to one server instance

3. **Resource Limits:**
   ```yaml
   # docker-compose.yml
   services:
     servicenow-mcp:
       deploy:
         resources:
           limits:
             memory: 512M
             cpus: '0.5'
           reservations:
             memory: 256M
             cpus: '0.25'
   ```

### Monitoring at Scale

```bash
# Monitor memory usage
docker stats servicenow-mcp

# Monitor Python process
ps aux | grep servicenow_mcp_server | grep -v grep

# Monitor response times (JSON structured logs)
grep "knowledge search" logs/*.log | jq '.duration' | sort -n

# Monitor error rates
grep '"level":"error"' logs/*.log | wc -l

# Monitor authentication success rate
grep "authentication" logs/*.log | jq 'select(.success == true)' | wc -l
```

## Backup and Recovery

### Configuration Backup
```bash
# Backup configuration
tar -czf servicenow-mcp-config-$(date +%Y%m%d).tar.gz .env docker-compose.yml

# Backup logs
tar -czf servicenow-mcp-logs-$(date +%Y%m%d).tar.gz logs/
```

### Disaster Recovery
1. Ensure ServiceNow access is restored
2. Redeploy MCP server with backed-up configuration
3. Test authentication and knowledge search
4. Verify role-based access controls
