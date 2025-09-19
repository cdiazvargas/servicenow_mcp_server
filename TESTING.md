# ServiceNow Knowledge MCP Server - Testing Guide

This guide covers testing the ServiceNow Knowledge MCP Server to ensure it meets all acceptance criteria.

## Test Setup

### Prerequisites
- ServiceNow test instance with sample knowledge articles
- Test users with different role configurations
- MCP client for testing (can use command line tools)

### Test Data Setup

Create test knowledge articles in ServiceNow with proper role-based access:

1. **Public Article** (accessible to all users)
   - Title: "General Company Information"
   - Category: "General"
   - Roles: (empty - public access)
   - Workflow State: Published

2. **Employee Article** (accessible to employees)
   - Title: "Employee Vacation Policy"
   - Category: "HR Policies"
   - Roles: "employee,knowledge_reader"
   - Workflow State: Published

3. **Manager Article** (accessible to managers)
   - Title: "Disciplinary Procedures"
   - Category: "Management"
   - Roles: "manager,knowledge_reader"
   - Workflow State: Published

4. **IT Article** (accessible to IT administrators)
   - Title: "Server Maintenance Procedures"
   - Category: "IT Documentation"
   - Roles: "it_administrator,knowledge_reader"
   - Workflow State: Published

5. **Contractor Article** (accessible to contractors)
   - Title: "Contractor Guidelines"
   - Category: "External"
   - Roles: "contractor,knowledge_reader"
   - Workflow State: Published

### Test Users

Create test users with different role assignments:

1. **Regular Employee**
   - Username: `test.employee`
   - Roles: `employee`, `knowledge_reader`

2. **Manager**
   - Username: `test.manager`
   - Roles: `employee`, `manager`, `knowledge_reader`

3. **IT Administrator**
   - Username: `test.itadmin`
   - Roles: `employee`, `it_administrator`, `knowledge_reader`

4. **Contractor**
   - Username: `test.contractor`
   - Roles: `contractor`, `knowledge_reader`

## Testing Framework

### Manual Test Cases

#### Test Case 1: Authentication Flow

**Acceptance Criteria:** JWT-First Authentication with OAuth Fallback

**Sub-test 1.1: JWT Authentication**
```bash
# Test JWT authentication
echo '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "authenticate_user",
    "arguments": {
      "jwt_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
  }
}' | python -m servicenow_mcp_server.main

# Expected Response:
# {
#   "success": true,
#   "user_id": "user-sys-id",
#   "username": "test.employee", 
#   "roles": ["employee", "knowledge_reader"],
#   "expires_at": "2024-12-17T15:30:00.000Z",
#   "auth_method": "jwt"
# }
```

**Sub-test 1.2: OAuth Fallback Authentication**
```bash
# Test OAuth authentication
echo '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "authenticate_user",
    "arguments": {
      "username": "test.employee",
      "password": "test_password"
    }
  }
}' | python -m servicenow_mcp_server.main

# Expected Response:
# {
#   "success": true,
#   "user_id": "user-sys-id",
#   "username": "test.employee",
#   "roles": ["employee", "knowledge_reader"],
#   "expires_at": "2024-12-17T15:30:00.000Z",
#   "auth_method": "oauth"
# }
```

**Test Steps:**
1. Authenticate each test user type
2. Verify role information is correctly returned
3. Test invalid credentials
4. Verify session context is established

#### Test Case 2: Role-Based Knowledge Search

**Acceptance Criteria:** Knowledge Base Query Requirements + Pass-Through Authentication

**Sub-test 2.1: Regular Employee Access**
```bash
# Search as regular employee
echo '{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "query": "vacation policy",
      "user_id": "employee-user-id",
      "synthesize": true
    }
  }
}' | python -m servicenow_mcp_server.main

# Expected: Can access Public and Employee articles only
# Should NOT return Manager or IT articles
# Response should include synthesized answer with source articles
```

**Sub-test 2.2: Manager Access**
```bash
# Search as manager
echo '{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "query": "disciplinary procedures",
      "user_id": "manager-user-id",
      "synthesize": true
    }
  }
}' | python -m servicenow_mcp_server.main

# Expected: Can access Public, Employee, and Manager articles
# Should return management-level knowledge articles with synthesis
```

**Sub-test 2.3: IT Administrator Access**
```bash
# Search as IT admin
echo '{
  "jsonrpc": "2.0", 
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "query": "server maintenance",
      "user_id": "itadmin-user-id",
      "synthesize": true
    }
  }
}' | python -m servicenow_mcp_server.main

# Expected: Can access technical documentation and system procedures
# Should include step-by-step procedures for technical tasks
```

**Sub-test 2.4: Contractor Access**
```bash
# Search as contractor  
echo '{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "search_knowledge",
    "arguments": {
      "query": "company policies",
      "user_id": "contractor-user-id",
      "synthesize": true
    }
  }
}' | python -m servicenow_mcp_server.main

# Expected: Limited to contractor-accessible knowledge articles only
# Should NOT include employee-specific or internal procedures
```

#### Test Case 3: Knowledge Synthesis

**Acceptance Criteria:** OI Enterprise Interface Requirements

**Sub-test 3.1: Comprehensive Answer Synthesis**
```bash
# Test synthesis of multiple articles
curl -X POST http://localhost:3000/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vacation policy",
    "userId": "employee-user-id",
    "synthesize": true,
    "limit": 5
  }'

# Expected Response Format:
# - Direct answers synthesized from multiple relevant articles
# - Step-by-step procedures when applicable
# - Links to original ServiceNow knowledge articles
# - Related topics or articles that might be helpful
```

**Sub-test 3.2: Step-by-Step Procedures**
```bash
# Test procedure extraction
curl -X POST http://localhost:3000/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "expense report submission",
    "userId": "employee-user-id",
    "synthesize": true
  }'

# Expected: Should include step-by-step procedures if available
```

#### Test Case 4: Context Maintenance

**Acceptance Criteria:** Knowledge Base Query Requirements (Follow-up Questions)

```bash
# Initial search
curl -X POST http://localhost:3000/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vacation policy",
    "userId": "employee-user-id",
    "synthesize": true
  }'

# Follow-up search with context
curl -X POST http://localhost:3000/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vacation during company holiday",
    "userId": "employee-user-id",
    "synthesize": true
  }'

# Expected: Should maintain context and search for additional relevant articles
```

#### Test Case 5: Error Handling

**Acceptance Criteria:** OI Enterprise Interface Requirements

**Sub-test 5.1: No Articles Found**
```bash
# Search for non-existent information
curl -X POST http://localhost:3000/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "completely non-existent topic xyz123",
    "userId": "employee-user-id",
    "synthesize": true
  }'

# Expected Response:
# "I couldn't find information about this in our ServiceNow knowledge base. 
#  Click here to submit a request for personalized assistance."
```

**Sub-test 5.2: Session Expiry**
```bash
# Use expired session
curl -X POST http://localhost:3000/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vacation policy",
    "userId": "expired-user-id",
    "synthesize": true
  }'

# Expected: Should gracefully prompt for re-authentication
```

**Sub-test 5.3: Permission Denied**
```bash
# Try to access restricted article as contractor
curl -X POST http://localhost:3000/tools/get_article \
  -H "Content-Type: application/json" \
  -d '{
    "articleId": "manager-only-article-id",
    "userId": "contractor-user-id"
  }'

# Expected: Should inform user that article is not accessible
```

#### Test Case 6: Vague Query Handling

**Acceptance Criteria:** OI Enterprise Interface Requirements

```bash
# Test vague query
curl -X POST http://localhost:3000/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "query": "benefits enrollment",
    "userId": "employee-user-id",
    "synthesize": true
  }'

# Expected Response should include clarification:
# "I found articles about health insurance enrollment, 401k setup, and FSA configuration. 
#  Which would you like to know about?"
```

### Automated Test Suite

Create automated tests using pytest:

```python
# tests/integration/test_mcp_server.py
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch
from servicenow_mcp_server.server import ServiceNowMCPServer
from servicenow_mcp_server.config import load_settings
from servicenow_mcp_server.types import UserContext, AuthMethod
from datetime import datetime, timedelta

@pytest.fixture
async def mcp_server():
    """Fixture to create MCP server for testing."""
    settings = load_settings()
    config = settings.to_servicenow_config()
    server = ServiceNowMCPServer(config)
    yield server
    # Cleanup
    await server.cleanup()

@pytest.mark.asyncio
class TestAuthentication:
    async def test_jwt_authentication_success(self, mcp_server):
        """Test successful JWT authentication."""
        mock_user_context = UserContext(
            user_id="test-user-123",
            username="test.employee",
            roles=["employee", "knowledge_reader"],
            session_token="test-jwt-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(mcp_server.auth_manager, 'authenticate_with_jwt', 
                         return_value=mock_user_context):
            result = await mcp_server._handle_authenticate_user({
                "jwt_token": "test.jwt.token"
            })
            
            assert len(result) == 1
            assert result[0].type == "text"
            response_data = json.loads(result[0].text)
            assert response_data["success"] is True
            assert response_data["username"] == "test.employee"
            assert "employee" in response_data["roles"]

    async def test_oauth_authentication_success(self, mcp_server):
        """Test successful OAuth authentication.""" 
        mock_user_context = UserContext(
            user_id="test-user-456",
            username="test.manager",
            roles=["manager", "employee", "knowledge_reader"],
            session_token="test-oauth-token",
            expires_at=datetime.utcnow() + timedelta(minutes=30),
            auth_method=AuthMethod.OAUTH
        )
        
        with patch.object(mcp_server.auth_manager, 'authenticate_with_oauth',
                         return_value=mock_user_context):
            result = await mcp_server._handle_authenticate_user({
                "username": "test.manager",
                "password": "test_password"
            })
            
            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert response_data["success"] is True
            assert response_data["username"] == "test.manager"
            assert "manager" in response_data["roles"]

    async def test_authentication_failure(self, mcp_server):
        """Test authentication failure handling."""
        from servicenow_mcp_server.types import AuthenticationError
        
        with patch.object(mcp_server.auth_manager, 'authenticate_with_jwt',
                         side_effect=AuthenticationError("JWT_INVALID", "Invalid token", True)):
            result = await mcp_server._handle_authenticate_user({
                "jwt_token": "invalid.jwt.token"
            })
            
            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert response_data["success"] is False
            assert "error" in response_data

@pytest.mark.asyncio 
class TestRoleBasedAccess:
    async def test_employee_access_restrictions(self, mcp_server):
        """Test that employees can only access appropriate articles."""
        # Mock employee user context
        employee_context = UserContext(
            user_id="employee-123",
            username="test.employee", 
            roles=["employee", "knowledge_reader"],
            session_token="employee-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(mcp_server.auth_manager, 'get_user_context',
                         return_value=employee_context):
            with patch.object(mcp_server.servicenow_client, 'search_knowledge_articles') as mock_search:
                # Mock search result with employee-accessible articles only
                mock_search.return_value = AsyncMock(articles=[], total_count=0)
                
                result = await mcp_server._handle_search_knowledge({
                    "query": "vacation policy",
                    "user_id": "employee-123",
                    "synthesize": False
                })
                
                # Verify role-based query was built correctly
                mock_search.assert_called_once()
                call_args = mock_search.call_args
                assert "employee" in str(call_args)

    async def test_manager_access_privileges(self, mcp_server):
        """Test that managers can access management articles."""
        manager_context = UserContext(
            user_id="manager-456",
            username="test.manager",
            roles=["manager", "employee", "knowledge_reader"],
            session_token="manager-token", 
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(mcp_server.auth_manager, 'get_user_context',
                         return_value=manager_context):
            with patch.object(mcp_server.servicenow_client, 'search_knowledge_articles') as mock_search:
                mock_search.return_value = AsyncMock(articles=[], total_count=0)
                
                result = await mcp_server._handle_search_knowledge({
                    "query": "disciplinary procedures",
                    "user_id": "manager-456",
                    "synthesize": False
                })
                
                # Verify manager roles are included in search
                mock_search.assert_called_once()
                call_args = mock_search.call_args
                assert "manager" in str(call_args)

@pytest.mark.asyncio
class TestKnowledgeSynthesis:
    async def test_synthesis_response_format(self, mcp_server):
        """Test that synthesized responses include all required elements."""
        user_context = UserContext(
            user_id="test-user",
            username="test.user",
            roles=["employee"],
            session_token="test-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(mcp_server.auth_manager, 'get_user_context',
                         return_value=user_context):
            with patch.object(mcp_server.servicenow_client, 'search_knowledge_articles') as mock_search:
                # Mock article for synthesis
                from servicenow_mcp_server.types import KnowledgeArticle
                mock_article = KnowledgeArticle(
                    sys_id="art-123",
                    number="KB001",
                    short_description="Vacation Policy",
                    text="Employees get vacation. Step 1: Request time off. Step 2: Get approval.",
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
                
                mock_search.return_value = AsyncMock(articles=[mock_article], total_count=1)
                
                result = await mcp_server._handle_search_knowledge({
                    "query": "vacation policy",
                    "user_id": "test-user",
                    "synthesize": True
                })
                
                assert len(result) == 1
                response_text = result[0].text
                assert "Based on our knowledge base:" in response_text
                assert "Source articles for reference:" in response_text
                assert "You might also want to ask:" in response_text

    async def test_step_by_step_extraction(self, mcp_server):
        """Test extraction of step-by-step procedures."""
        # Test would verify procedure extraction logic
        from servicenow_mcp_server.knowledge_synthesis import KnowledgeSynthesisService
        
        synthesis_service = KnowledgeSynthesisService()
        
        # Test text with clear steps
        test_text = "Step 1: Submit request. Step 2: Get approval. Step 3: Take vacation."
        steps = synthesis_service._find_step_by_step_instructions(test_text)
        
        assert len(steps) >= 2  # Should find the steps
        assert "Step 1" in steps[0]

@pytest.mark.asyncio
class TestErrorHandling:
    async def test_no_articles_found(self, mcp_server):
        """Test handling when no articles are found."""
        user_context = UserContext(
            user_id="test-user",
            username="test.user", 
            roles=["employee"],
            session_token="test-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(mcp_server.auth_manager, 'get_user_context',
                         return_value=user_context):
            with patch.object(mcp_server.servicenow_client, 'search_knowledge_articles') as mock_search:
                # Return empty search result
                mock_search.return_value = AsyncMock(articles=[], total_count=0)
                
                result = await mcp_server._handle_search_knowledge({
                    "query": "completely non-existent topic xyz123",
                    "user_id": "test-user",
                    "synthesize": True
                })
                
                assert len(result) == 1
                response_text = result[0].text
                assert "couldn't find information" in response_text
                assert "submit a request for personalized assistance" in response_text

    async def test_session_expiry_handling(self, mcp_server):
        """Test graceful handling of expired sessions."""
        with patch.object(mcp_server.auth_manager, 'get_user_context',
                         return_value=None):  # No user context = expired session
            result = await mcp_server._handle_search_knowledge({
                "query": "vacation policy",
                "user_id": "expired-user-id",
                "synthesize": True
            })
            
            assert len(result) == 1
            response_data = json.loads(result[0].text)
            assert response_data["success"] is False
            assert "authentication" in response_data.get("error", "").lower()
```
```

### Performance Tests

```python
# tests/performance/test_performance.py
import pytest
import time
import asyncio
from unittest.mock import patch, AsyncMock
from servicenow_mcp_server.server import ServiceNowMCPServer
from servicenow_mcp_server.config import load_settings
from servicenow_mcp_server.types import UserContext, AuthMethod
from datetime import datetime, timedelta

@pytest.mark.asyncio
class TestPerformance:
    async def test_knowledge_search_performance(self):
        """Test that knowledge search completes within 5 seconds."""
        settings = load_settings()
        config = settings.to_servicenow_config()
        server = ServiceNowMCPServer(config)
        
        user_context = UserContext(
            user_id="perf-test-user",
            username="perf.test",
            roles=["employee"],
            session_token="perf-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(server.auth_manager, 'get_user_context',
                         return_value=user_context):
            with patch.object(server.servicenow_client, 'search_knowledge_articles') as mock_search:
                mock_search.return_value = AsyncMock(articles=[], total_count=0)
                
                start_time = time.time()
                
                result = await server._handle_search_knowledge({
                    "query": "vacation policy",
                    "user_id": "perf-test-user",
                    "synthesize": True
                })
                
                duration = time.time() - start_time
                assert duration < 5.0, f"Knowledge search took {duration:.2f}s, should be < 5s"

    async def test_authentication_performance(self):
        """Test that authentication completes within 3 seconds."""
        settings = load_settings()
        config = settings.to_servicenow_config()
        server = ServiceNowMCPServer(config)
        
        mock_user_context = UserContext(
            user_id="auth-perf-user",
            username="auth.test",
            roles=["employee"],
            session_token="auth-perf-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(server.auth_manager, 'authenticate_with_jwt',
                         return_value=mock_user_context):
            start_time = time.time()
            
            result = await server._handle_authenticate_user({
                "jwt_token": "test.jwt.token"
            })
            
            duration = time.time() - start_time
            assert duration < 3.0, f"Authentication took {duration:.2f}s, should be < 3s"

    async def test_concurrent_requests_performance(self):
        """Test handling multiple concurrent requests."""
        settings = load_settings()
        config = settings.to_servicenow_config()
        server = ServiceNowMCPServer(config)
        
        user_context = UserContext(
            user_id="concurrent-user",
            username="concurrent.test",
            roles=["employee"],
            session_token="concurrent-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        async def mock_search_with_delay(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
            return AsyncMock(articles=[], total_count=0)
        
        with patch.object(server.auth_manager, 'get_user_context',
                         return_value=user_context):
            with patch.object(server.servicenow_client, 'search_knowledge_articles',
                             side_effect=mock_search_with_delay):
                
                start_time = time.time()
                
                # Execute 5 concurrent searches
                tasks = []
                for i in range(5):
                    task = server._handle_search_knowledge({
                        "query": f"test query {i}",
                        "user_id": "concurrent-user",
                        "synthesize": False
                    })
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks)
                
                duration = time.time() - start_time
                
                # Should complete all 5 searches in less than 1 second total
                # (since they run concurrently, not sequentially)
                assert duration < 1.0, f"Concurrent searches took {duration:.2f}s, should be < 1s"
                assert len(results) == 5, "Should have completed all 5 searches"
```

### Load Testing

Use pytest with asyncio for load testing the MCP server:

```python
# tests/load/test_load.py
import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock
from servicenow_mcp_server.server import ServiceNowMCPServer
from servicenow_mcp_server.config import load_settings
from servicenow_mcp_server.types import UserContext, AuthMethod
from datetime import datetime, timedelta

@pytest.mark.asyncio
class TestLoadHandling:
    async def test_authentication_load(self):
        """Test authentication under load."""
        settings = load_settings()
        config = settings.to_servicenow_config()
        server = ServiceNowMCPServer(config)
        
        mock_user_context = UserContext(
            user_id="load-test-user",
            username="load.test",
            roles=["employee"],
            session_token="load-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(server.auth_manager, 'authenticate_with_jwt',
                         return_value=mock_user_context):
            
            # Simulate 50 concurrent authentication requests
            start_time = time.time()
            
            tasks = []
            for i in range(50):
                task = server._handle_authenticate_user({
                    "jwt_token": f"test.jwt.token.{i}"
                })
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            duration = time.time() - start_time
            
            # All should complete successfully
            successful_auths = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_auths) == 50
            
            # Should handle load efficiently
            assert duration < 10.0, f"50 auths took {duration:.2f}s, should be < 10s"

    async def test_knowledge_search_load(self):
        """Test knowledge search under load."""
        settings = load_settings()
        config = settings.to_servicenow_config()
        server = ServiceNowMCPServer(config)
        
        user_context = UserContext(
            user_id="search-load-user",
            username="search.load",
            roles=["employee"],
            session_token="search-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        async def mock_search_with_realistic_delay(*args, **kwargs):
            await asyncio.sleep(0.2)  # Simulate realistic ServiceNow response time
            return AsyncMock(articles=[], total_count=0)
        
        with patch.object(server.auth_manager, 'get_user_context',
                         return_value=user_context):
            with patch.object(server.servicenow_client, 'search_knowledge_articles',
                             side_effect=mock_search_with_realistic_delay):
                
                # Simulate 20 concurrent search requests
                start_time = time.time()
                
                tasks = []
                for i in range(20):
                    task = server._handle_search_knowledge({
                        "query": f"vacation policy {i}",
                        "user_id": "search-load-user",
                        "synthesize": True
                    })
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                duration = time.time() - start_time
                
                # All should complete successfully
                successful_searches = [r for r in results if not isinstance(r, Exception)]
                assert len(successful_searches) == 20
                
                # Should handle concurrent load efficiently
                assert duration < 5.0, f"20 searches took {duration:.2f}s, should be < 5s"

    async def test_mixed_load_scenario(self):
        """Test mixed authentication and search load."""
        settings = load_settings()
        config = settings.to_servicenow_config()
        server = ServiceNowMCPServer(config)
        
        # Setup mocks for both auth and search
        mock_user_context = UserContext(
            user_id="mixed-load-user",
            username="mixed.load",
            roles=["employee"], 
            session_token="mixed-token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            auth_method=AuthMethod.JWT
        )
        
        with patch.object(server.auth_manager, 'authenticate_with_jwt',
                         return_value=mock_user_context):
            with patch.object(server.auth_manager, 'get_user_context',
                             return_value=mock_user_context):
                with patch.object(server.servicenow_client, 'search_knowledge_articles') as mock_search:
                    mock_search.return_value = AsyncMock(articles=[], total_count=0)
                    
                    start_time = time.time()
                    
                    tasks = []
                    
                    # Mix of auth and search requests
                    for i in range(30):
                        if i % 3 == 0:  # Every 3rd request is auth
                            task = server._handle_authenticate_user({
                                "jwt_token": f"mixed.jwt.{i}"
                            })
                        else:  # Others are searches
                            task = server._handle_search_knowledge({
                                "query": f"mixed query {i}",
                                "user_id": "mixed-load-user",
                                "synthesize": bool(i % 2)  # Mix synthesized and non-synthesized
                            })
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    duration = time.time() - start_time
                    
                    # All should complete successfully
                    successful_requests = [r for r in results if not isinstance(r, Exception)]
                    assert len(successful_requests) == 30
                    
                    # Should handle mixed load efficiently
                    assert duration < 8.0, f"30 mixed requests took {duration:.2f}s, should be < 8s"
```

Run load tests:
```bash
# Run load tests specifically
pytest tests/load/ -v

# Run load tests with detailed output
pytest tests/load/ -v -s --tb=short

# Run specific load test
pytest tests/load/test_load.py::TestLoadHandling::test_authentication_load -v
```

## Test Execution

### Running All Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests  
pytest tests/integration/ -v

# Performance tests
pytest tests/performance/ -v

# Load tests
pytest tests/load/ -v

# All tests with coverage
pytest --cov=servicenow_mcp_server --cov-report=html --cov-report=term

# Quick test run (unit tests only)
pytest tests/unit/ -x -v

# Run tests with specific markers
pytest -m "not slow" tests/
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test ServiceNow MCP Server

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Create virtual environment
      run: |
        python -m venv venv
        source venv/bin/activate
        
    - name: Install dependencies
      run: |
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install -e .
      
    - name: Run unit tests
      run: |
        source venv/bin/activate
        pytest tests/unit/ -v --cov=servicenow_mcp_server
      
    - name: Run integration tests
      run: |
        source venv/bin/activate
        pytest tests/integration/ -v
      env:
        SERVICENOW_INSTANCE_URL: ${{ secrets.SERVICENOW_TEST_URL }}
        JWT_SECRET_KEY: ${{ secrets.JWT_TEST_SECRET }}
        SERVICENOW_CLIENT_ID: ${{ secrets.SERVICENOW_TEST_CLIENT_ID }}
        SERVICENOW_CLIENT_SECRET: ${{ secrets.SERVICENOW_TEST_CLIENT_SECRET }}
        
    - name: Run performance tests
      run: |
        source venv/bin/activate
        pytest tests/performance/ -v
        
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Test Results Verification

### Acceptance Criteria Checklist

- [ ] **Knowledge Base Query Requirements**
  - [ ] Searches ServiceNow knowledge articles user has access to
  - [ ] Provides comprehensive answers from multiple articles
  - [ ] Includes step-by-step procedures when applicable
  - [ ] Provides links to original ServiceNow articles
  - [ ] Suggests related topics and articles
  - [ ] Maintains context for follow-up questions

- [ ] **Pass-Through Authentication Requirements**
  - [ ] Regular employees see only Employee/Public access articles
  - [ ] Managers see management-level knowledge articles
  - [ ] IT Administrators see restricted IT knowledge articles
  - [ ] Contractors see only contractor-accessible articles
  - [ ] Audit logs show actual user identity

- [ ] **OI Enterprise Interface Requirements**
  - [ ] Inherits corporate authentication and ServiceNow role context
  - [ ] Handles vague questions with clarifying options
  - [ ] Provides status updates during processing
  - [ ] Handles cases where no relevant articles exist
  - [ ] Gracefully handles session expiry

- [ ] **ServiceNow Integration Specifics**
  - [ ] Uses ServiceNow Knowledge Management API
  - [ ] Respects role-based access controls
  - [ ] Handles ServiceNow session expiry gracefully

### Test Coverage Report

Generate test coverage:
```bash
pytest --cov=servicenow_mcp_server --cov-report=html --cov-report=term
```

Target coverage metrics:
- Lines: >85%
- Functions: >90%
- Branches: >80%
- Statements: >85%

### Regression Testing

Before releases, run full regression test suite:
```bash
# Run all test suites
pytest tests/ -v --cov=servicenow_mcp_server

# Verify specific acceptance criteria
pytest tests/integration/ -k "acceptance" -v

# Performance benchmarks
pytest tests/performance/ -v

# Run tests with different Python versions
python3.9 -m pytest tests/
python3.10 -m pytest tests/
python3.11 -m pytest tests/
```
