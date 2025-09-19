# 🧪 ServiceNow Knowledge MCP Server - Testing Guide

This guide shows you how to test the Python ServiceNow Knowledge MCP Server at different levels.

## 🚀 **Quick Test Setup**

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install in development mode for testing
pip install -e .
```

## 🧪 **1. Unit Tests**

Test individual components in isolation:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_knowledge_synthesis.py -v

# Run with coverage report
pytest tests/unit/ --cov=servicenow_mcp_server --cov-report=html

# Run specific test method
pytest tests/unit/test_knowledge_synthesis.py::TestKnowledgeSynthesisService::test_synthesize_with_articles -v
```

### Create Test Environment
```bash
# Create test environment file
cp .env.example .env.test

# Edit .env.test for testing
echo "SERVICENOW_INSTANCE_URL=https://test.service-now.com
JWT_SECRET_KEY=test-secret-key-for-testing-only
JWT_ALGORITHM=HS256
LOG_LEVEL=debug" > .env.test
```

## 🔧 **2. Integration Tests**

Test the complete system with mock ServiceNow responses:

```bash
# Create integration test file
mkdir -p tests/integration
```

Create `tests/integration/test_mcp_server.py`:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from servicenow_mcp_server.server import ServiceNowMCPServer
from servicenow_mcp_server.config import load_settings

@pytest.mark.asyncio
async def test_authentication_flow():
    """Test complete authentication flow."""
    settings = load_settings()
    config = settings.to_servicenow_config()
    server = ServiceNowMCPServer(config)
    
    # Test JWT authentication
    jwt_token = "test.jwt.token"
    
    # Mock the authentication
    with patch.object(server.auth_manager, 'authenticate_with_jwt') as mock_auth:
        mock_auth.return_value = AsyncMock()
        
        result = await server._handle_authenticate_user({
            "jwt_token": jwt_token
        })
        
        assert len(result) == 1
        assert result[0].type == "text"

@pytest.mark.asyncio 
async def test_knowledge_search_flow():
    """Test complete knowledge search flow."""
    # Implementation for search testing
    pass
```

Run integration tests:
```bash
pytest tests/integration/ -v
```

## 🌐 **3. End-to-End Testing**

Test the MCP server as a black box:

### Manual MCP Testing

Create `test_mcp_manually.py`:

```python
#!/usr/bin/env python3
"""Manual MCP server testing script."""

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timedelta
import jwt

async def test_mcp_server():
    """Test MCP server manually."""
    
    # 1. Test JWT token generation
    def generate_test_jwt():
        payload = {
            "sub": "test-user-123",
            "username": "test.user",
            "roles": ["employee", "knowledge"],
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "iss": "test-issuer"
        }
        return jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    
    test_jwt = generate_test_jwt()
    print(f"Generated test JWT: {test_jwt[:50]}...")
    
    # 2. Test authentication
    auth_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "authenticate_user",
            "arguments": {
                "jwt_token": test_jwt
            }
        }
    }
    
    print("\n🔐 Testing Authentication...")
    print(f"Request: {json.dumps(auth_request, indent=2)}")
    
    # 3. Test knowledge search (would require authenticated user)
    search_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_knowledge",
            "arguments": {
                "query": "vacation policy",
                "user_id": "test-user-123",
                "synthesize": True
            }
        }
    }
    
    print("\n🔍 Testing Knowledge Search...")
    print(f"Request: {json.dumps(search_request, indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
```

Run manual testing:
```bash
python test_mcp_manually.py
```

## 📡 **4. Live Server Testing**

Test against a running MCP server:

### Start the Server
```bash
# Terminal 1: Start MCP server
source venv/bin/activate
python -m servicenow_mcp_server.main
```

### Test with Curl (Alternative Terminal)
```bash
# Terminal 2: Test with curl/echo

# Test 1: Authentication
echo '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "authenticate_user",
    "arguments": {
      "jwt_token": "test.jwt.token"
    }
  }
}' | python -m servicenow_mcp_server.main

# Test 2: List available tools
echo '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}' | python -m servicenow_mcp_server.main

# Test 3: Search knowledge (requires authentication first)
echo '{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "query": "vacation policy",
      "user_id": "test-user-123",
      "synthesize": true
    }
  }
}' | python -m servicenow_mcp_server.main
```

## 🔬 **5. Component Testing**

Test individual components:

### Test JWT Authentication
```python
# test_jwt_auth.py
import asyncio
from servicenow_mcp_server.auth import AuthenticationManager
from servicenow_mcp_server.types import ServiceNowConfig, AuthMethod
import jwt
from datetime import datetime, timedelta

async def test_jwt_auth():
    config = ServiceNowConfig(
        instance_url="https://test.service-now.com",
        auth_method=AuthMethod.JWT,
        jwt_secret_key="test-secret-key"
    )
    
    auth_manager = AuthenticationManager(config)
    
    # Generate test JWT
    payload = {
        "sub": "test-user",
        "username": "test.user",
        "roles": ["employee"],
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    }
    token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
    
    # Test authentication
    try:
        user_context = await auth_manager.authenticate_with_jwt(token)
        print(f"✅ JWT Auth Success: {user_context.username}")
        print(f"   Roles: {user_context.roles}")
        print(f"   Expires: {user_context.expires_at}")
    except Exception as e:
        print(f"❌ JWT Auth Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_jwt_auth())
```

Run component test:
```bash
python test_jwt_auth.py
```

### Test Knowledge Synthesis
```python
# test_synthesis.py
from servicenow_mcp_server.knowledge_synthesis import KnowledgeSynthesisService
from servicenow_mcp_server.types import KnowledgeArticle, SearchResult

def test_synthesis():
    service = KnowledgeSynthesisService()
    
    # Create test article
    article = KnowledgeArticle(
        sys_id="test-1",
        number="KB001",
        short_description="Test Vacation Policy",
        text="Employees get vacation time. Step 1: Request vacation. Step 2: Get approval.",
        topic="HR",
        category="Policies",
        subcategory="",
        workflow_state="published",
        roles="employee",
        can_read_user_criteria="",
        created_by="admin",
        created_on="2024-01-01",
        updated_by="admin", 
        updated_on="2024-01-01",
        view_count=10,
        helpful_count=5,
        article_type="policy",
        direct_link="https://test.com/kb001"
    )
    
    search_result = SearchResult(
        articles=[article],
        total_count=1,
        search_context="vacation policy",
        related_topics=["HR", "Policies"]
    )
    
    # Test synthesis
    response = service.synthesize_response(search_result, "vacation policy")
    print(f"✅ Synthesis Success")
    print(f"   Answer: {response.answer[:100]}...")
    print(f"   Source Articles: {len(response.source_articles)}")
    print(f"   Procedures: {response.step_by_step_procedures}")

if __name__ == "__main__":
    test_synthesis()
```

## 🎯 **6. Performance Testing**

Test server performance:

```python
# test_performance.py
import asyncio
import time
from servicenow_mcp_server.knowledge_synthesis import KnowledgeSynthesisService

async def performance_test():
    service = KnowledgeSynthesisService()
    
    # Test search performance
    start_time = time.time()
    
    for i in range(100):
        # Simulate synthesis operations
        service._calculate_relevance_score(
            type('Article', (), {
                'short_description': 'Test Article',
                'text': 'Test content for performance testing',
                'view_count': 10,
                'helpful_count': 5
            })(),
            'test query'
        )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Performance Test Complete")
    print(f"   100 operations in {duration:.3f} seconds")
    print(f"   {100/duration:.1f} operations per second")

if __name__ == "__main__":
    asyncio.run(performance_test())
```

## 🔧 **7. Using Make Commands**

The project includes Make commands for testing:

```bash
# Run all tests
make test

# Run tests with coverage
make test-cov

# Run format and tests
make quick-test

# Run all checks (format, lint, test)
make check-all

# Development setup
make dev-setup
```

## 🐛 **8. Debugging Tests**

### Debug Mode
```bash
# Run tests with debug output
LOG_LEVEL=debug pytest tests/unit/ -v -s

# Run specific test with debugging
pytest tests/unit/test_knowledge_synthesis.py::TestKnowledgeSynthesisService::test_synthesize_with_articles -v -s --pdb
```

### Test Configuration
```bash
# Use test-specific configuration
TEST_ENV=true pytest tests/

# Run tests with specific markers
pytest -m "not integration" tests/
```

## 📊 **9. Test Coverage**

```bash
# Generate coverage report
pytest --cov=servicenow_mcp_server --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## 🎉 **Test Results Verification**

Your tests should verify:

- ✅ **Authentication**: JWT tokens are validated correctly
- ✅ **Authorization**: Role-based access control works
- ✅ **Knowledge Search**: Articles are found and filtered properly
- ✅ **Synthesis**: Multiple articles are combined coherently
- ✅ **Error Handling**: Graceful failure and user feedback
- ✅ **Performance**: Response times are acceptable
- ✅ **MCP Protocol**: Tools are registered and callable

## 🚨 **Common Test Issues**

1. **Missing Environment Variables**: Ensure `.env.test` is configured
2. **Import Errors**: Make sure package is installed with `pip install -e .`
3. **Async Test Issues**: Use `@pytest.mark.asyncio` for async tests
4. **Mock ServiceNow**: Use `respx` to mock HTTP requests to ServiceNow

This testing approach ensures your ServiceNow Knowledge MCP Server works correctly at all levels! 🎯

