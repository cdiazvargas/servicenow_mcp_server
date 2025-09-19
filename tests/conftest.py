"""Pytest configuration and fixtures."""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Generator

import pytest
from unittest.mock import AsyncMock, MagicMock

from servicenow_mcp_server.auth import AuthenticationManager
from servicenow_mcp_server.config import Settings
from servicenow_mcp_server.knowledge_synthesis import KnowledgeSynthesisService
from servicenow_mcp_server.servicenow_client import ServiceNowKnowledgeClient
from servicenow_mcp_server.types import (
    AuthMethod,
    KnowledgeArticle,
    SearchResult,
    ServiceNowConfig,
    UserContext,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings fixture."""
    # Set test environment variables
    os.environ.update({
        "SERVICENOW_INSTANCE_URL": "https://test.service-now.com",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only",
        "JWT_ALGORITHM": "HS256",
        "LOG_LEVEL": "debug",
    })
    
    return Settings()


@pytest.fixture
def servicenow_config(test_settings: Settings) -> ServiceNowConfig:
    """ServiceNow configuration fixture."""
    return test_settings.to_servicenow_config()


@pytest.fixture
def mock_user_context() -> UserContext:
    """Mock user context fixture."""
    return UserContext(
        user_id="test-user-123",
        username="test.user",
        roles=["employee", "knowledge"],
        session_token="mock-jwt-token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        auth_method=AuthMethod.JWT
    )


@pytest.fixture
def sample_knowledge_articles() -> list[KnowledgeArticle]:
    """Sample knowledge articles for testing."""
    return [
        KnowledgeArticle(
            sys_id="article-1",
            number="KB001",
            short_description="Employee Vacation Policy",
            text="Employees are entitled to vacation time based on years of service. Full-time employees receive 2 weeks initially, increasing to 3 weeks after 2 years.",
            topic="HR",
            category="Policies",
            subcategory="Time Off",
            workflow_state="published",
            roles="employee",
            can_read_user_criteria="",
            created_by="admin",
            created_on="2024-01-01 10:00:00",
            updated_by="admin",
            updated_on="2024-01-01 10:00:00",
            view_count=100,
            helpful_count=25,
            article_type="policy",
            direct_link="https://test.service-now.com/kb_view.do?sysparm_article=KB001"
        ),
        KnowledgeArticle(
            sys_id="article-2",
            number="KB002",
            short_description="Vacation Request Process",
            text="To request vacation: 1. Log into Employee Self Service 2. Submit vacation request 3. Wait for manager approval 4. Vacation time will be deducted",
            topic="HR",
            category="Procedures",
            subcategory="Time Off",
            workflow_state="published",
            roles="employee",
            can_read_user_criteria="",
            created_by="admin",
            created_on="2024-01-01 11:00:00",
            updated_by="admin",
            updated_on="2024-01-01 11:00:00",
            view_count=75,
            helpful_count=20,
            article_type="procedure",
            direct_link="https://test.service-now.com/kb_view.do?sysparm_article=KB002"
        ),
        KnowledgeArticle(
            sys_id="article-3",
            number="KB003",
            short_description="Manager Disciplinary Procedures",
            text="Managers should follow these steps for disciplinary actions: 1. Document the issue 2. Meet with HR 3. Schedule employee meeting 4. Follow up",
            topic="Management",
            category="Procedures",
            subcategory="Discipline",
            workflow_state="published",
            roles="manager",
            can_read_user_criteria="",
            created_by="admin",
            created_on="2024-01-01 12:00:00",
            updated_by="admin",
            updated_on="2024-01-01 12:00:00",
            view_count=50,
            helpful_count=15,
            article_type="procedure",
            direct_link="https://test.service-now.com/kb_view.do?sysparm_article=KB003"
        )
    ]


@pytest.fixture
def sample_search_result(sample_knowledge_articles: list[KnowledgeArticle]) -> SearchResult:
    """Sample search result fixture."""
    return SearchResult(
        articles=sample_knowledge_articles[:2],  # First 2 articles
        total_count=2,
        search_context="vacation policy",
        related_topics=["HR", "Policies", "Time Off"],
        query_time_ms=150.5
    )


@pytest.fixture
def auth_manager(servicenow_config: ServiceNowConfig) -> AuthenticationManager:
    """Authentication manager fixture."""
    return AuthenticationManager(servicenow_config)


@pytest.fixture
def knowledge_synthesis_service() -> KnowledgeSynthesisService:
    """Knowledge synthesis service fixture."""
    return KnowledgeSynthesisService()


@pytest.fixture
def mock_servicenow_client(servicenow_config: ServiceNowConfig) -> ServiceNowKnowledgeClient:
    """Mock ServiceNow client fixture."""
    auth_manager = AsyncMock()
    client = ServiceNowKnowledgeClient(servicenow_config, auth_manager)
    
    # Mock HTTP client
    client._client = AsyncMock()
    
    return client


@pytest.fixture
def mock_httpx_response() -> MagicMock:
    """Mock httpx response fixture."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"result": []}
    return response


# Test data fixtures
@pytest.fixture
def valid_jwt_payload() -> Dict[str, any]:
    """Valid JWT payload for testing."""
    return {
        "sub": "test-user-123",
        "username": "test.user",
        "roles": ["employee", "knowledge"],
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "iss": "test-issuer"
    }


@pytest.fixture
def servicenow_api_response() -> Dict[str, any]:
    """Sample ServiceNow API response."""
    return {
        "result": [
            {
                "sys_id": "article-1",
                "number": "KB001",
                "short_description": "Test Article",
                "text": "Test article content",
                "topic": "Test",
                "category": "Testing",
                "subcategory": "",
                "workflow_state": "published",
                "roles": "employee",
                "can_read_user_criteria": "",
                "sys_created_by": "admin",
                "sys_created_on": "2024-01-01 10:00:00",
                "sys_updated_by": "admin",
                "sys_updated_on": "2024-01-01 10:00:00",
                "view_count": "10",
                "helpful_count": "5",
                "article_type": "knowledge"
            }
        ]
    }
