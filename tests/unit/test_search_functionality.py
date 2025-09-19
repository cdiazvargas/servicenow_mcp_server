"""Unit tests for enhanced search functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from servicenow_mcp_server.servicenow_client import ServiceNowKnowledgeClient
from servicenow_mcp_server.types import (
    KnowledgeArticle,
    SearchType,
    ServiceNowConfig,
    UserContext,
)


class TestSearchFunctionality:
    """Test cases for enhanced search functionality."""
    
    def test_build_search_query_content_search(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test content search query building (default behavior)."""
        query = mock_servicenow_client._build_search_query(
            "vacation policy", 
            mock_user_context, 
            SearchType.CONTENT
        )
        
        # Should search in both title and text fields
        assert "short_descriptionLIKE%vacation policy%" in query
        assert "textLIKE%vacation policy%" in query
        assert "workflow_state=published" in query
        assert "^OR" in query  # Should have OR condition
    
    def test_build_search_query_sys_id_search(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test sys_id exact search query building."""
        sys_id = "abc123-def456-ghi789"
        query = mock_servicenow_client._build_search_query(
            sys_id,
            mock_user_context,
            SearchType.SYS_ID
        )
        
        # Should search for sys_id with LIKE operator (updated implementation)
        assert f"sys_idLIKE%{sys_id}%" in query
        assert "workflow_state=published" in query
    
    def test_build_search_query_number_search(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test article number exact search query building."""
        number = "KB001234"
        query = mock_servicenow_client._build_search_query(
            number,
            mock_user_context,
            SearchType.NUMBER
        )
        
        # Should search for exact number match
        assert f"number={number}" in query
        assert "workflow_state=published" in query
        # Should not have LIKE operators for number search
        assert "LIKE" not in query.split("number=")[1].split("^")[0]
    
    def test_build_search_query_title_exact_search(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test exact title search query building."""
        title = "Employee Vacation Policy"
        query = mock_servicenow_client._build_search_query(
            title,
            mock_user_context,
            SearchType.TITLE_EXACT
        )
        
        # Should search for title with LIKE operator (updated implementation)
        assert f"short_descriptionLIKE%{title}%" in query
        assert "workflow_state=published" in query
    
    def test_build_search_query_title_partial_search(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test partial title search query building."""
        title_part = "vacation"
        query = mock_servicenow_client._build_search_query(
            title_part,
            mock_user_context,
            SearchType.TITLE_PARTIAL
        )
        
        # Should search for partial title match with LIKE
        assert f"short_descriptionLIKE%{title_part}%" in query
        assert "workflow_state=published" in query
        # Should not search in text field for title-only search
        assert "textLIKE" not in query
    
    def test_build_search_query_role_filtering(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test that role-based filtering is preserved in all search types."""
        # Test with content search
        query = mock_servicenow_client._build_search_query(
            "test query",
            mock_user_context,
            SearchType.CONTENT
        )
        
        # Should include role filtering
        assert "rolesLIKE%employee%" in query
        assert "rolesLIKE%knowledge%" in query
        assert "roles=NULL" in query or "roles=)" in query  # Public articles
    
    def test_build_search_query_special_characters_escaping(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test that special characters are properly escaped."""
        query_with_quotes = "test's policy"
        query = mock_servicenow_client._build_search_query(
            query_with_quotes,
            mock_user_context,
            SearchType.CONTENT
        )
        
        # Should escape single quotes
        assert "test\\'s policy" in query
    
    def test_build_search_query_empty_query(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test behavior with empty query."""
        query = mock_servicenow_client._build_search_query(
            "",
            mock_user_context,
            SearchType.CONTENT
        )
        
        # Should return basic published filter
        assert query == "workflow_state=published"
    
    def test_build_search_query_whitespace_handling(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test that whitespace is properly handled."""
        query_with_spaces = "  vacation policy  "
        query = mock_servicenow_client._build_search_query(
            query_with_spaces,
            mock_user_context,
            SearchType.CONTENT
        )
        
        # Should trim whitespace
        assert "vacation policy" in query
        assert "  vacation policy  " not in query
    
    @pytest.mark.asyncio
    async def test_search_knowledge_articles_with_search_type(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test that search_knowledge_articles properly uses search_type parameter."""
        # Mock auth manager to return user context
        mock_servicenow_client.auth_manager.get_user_context = AsyncMock(return_value=mock_user_context)
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mock response for get_article (single article)
        mock_response.json.return_value = {
            "result": {
                "sys_id": "test-article-id",
                "number": "KB001",
                "short_description": "Test Article",
                "text": "Test content",
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
        }
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_servicenow_client._client = mock_client
        
        # Test sys_id search
        result = await mock_servicenow_client.search_knowledge_articles(
            query="test-article-id",
            user_id="test-user",
            limit=10,
            search_type=SearchType.SYS_ID
        )
        
        # Verify the API was called (for get_article, not search)
        mock_client.get.assert_called()
        call_args = mock_client.get.call_args
        
        # For sys_id search, it should call get_article endpoint
        assert "/kb_knowledge/test-article-id" in call_args.args[0]
        
        # Check result structure
        assert len(result.articles) == 1
        assert result.articles[0].sys_id == "test-article-id"
        assert result.articles[0].number == "KB001"
        assert result.total_count == 1
    
    def test_search_type_enum_values(self):
        """Test that SearchType enum has all expected values."""
        assert SearchType.CONTENT == "content"
        assert SearchType.SYS_ID == "sys_id"
        assert SearchType.NUMBER == "number"
        assert SearchType.TITLE_EXACT == "title_exact"
        assert SearchType.TITLE_PARTIAL == "title_partial"
    
    def test_default_search_type(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test that content search is the default behavior."""
        # Call without search_type parameter
        query = mock_servicenow_client._build_search_query(
            "test query",
            mock_user_context
        )
        
        # Should behave like content search (default)
        assert "short_descriptionLIKE%test query%" in query
        assert "textLIKE%test query%" in query
        assert "^OR" in query


class TestSearchTypeCoverage:
    """Test coverage for different search scenarios."""
    
    def test_sys_id_search_scenario(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test a realistic sys_id search scenario."""
        # 32-character sys_id (typical ServiceNow format)
        sys_id = "a1b2c3d4e5f6789012345678901234567"
        query = mock_servicenow_client._build_search_query(
            sys_id,
            mock_user_context,
            SearchType.SYS_ID
        )
        
        assert f"sys_idLIKE%{sys_id}%" in query
        assert "workflow_state=published" in query
    
    def test_article_number_search_scenario(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test a realistic article number search scenario."""
        # Typical knowledge base article number
        number = "KB0010042"
        query = mock_servicenow_client._build_search_query(
            number,
            mock_user_context,
            SearchType.NUMBER
        )
        
        assert f"number={number}" in query
        assert "workflow_state=published" in query
    
    def test_title_search_scenarios(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test realistic title search scenarios."""
        # Exact title match
        exact_title = "Employee Onboarding Checklist"
        exact_query = mock_servicenow_client._build_search_query(
            exact_title,
            mock_user_context,
            SearchType.TITLE_EXACT
        )
        
        assert f"short_descriptionLIKE%{exact_title}%" in exact_query
        
        # Partial title match
        partial_title = "onboarding"
        partial_query = mock_servicenow_client._build_search_query(
            partial_title,
            mock_user_context,
            SearchType.TITLE_PARTIAL
        )
        
        assert f"short_descriptionLIKE%{partial_title}%" in partial_query
    
    def test_complex_content_search(self, mock_servicenow_client: ServiceNowKnowledgeClient, mock_user_context: UserContext):
        """Test complex content search with multiple words."""
        complex_query = "password reset procedure"
        query = mock_servicenow_client._build_search_query(
            complex_query,
            mock_user_context,
            SearchType.CONTENT
        )
        
        # Should search in both title and content
        assert f"short_descriptionLIKE%{complex_query}%" in query
        assert f"textLIKE%{complex_query}%" in query
        assert "^OR" in query
