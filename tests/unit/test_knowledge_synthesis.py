"""Unit tests for knowledge synthesis service."""

import pytest

from servicenow_mcp_server.knowledge_synthesis import KnowledgeSynthesisService
from servicenow_mcp_server.types import KnowledgeArticle, SearchResult


class TestKnowledgeSynthesisService:
    """Test cases for KnowledgeSynthesisService."""
    
    def test_synthesize_empty_results(self, knowledge_synthesis_service: KnowledgeSynthesisService):
        """Test synthesis with empty search results."""
        empty_result = SearchResult(
            articles=[],
            total_count=0,
            search_context="test query",
            related_topics=[]
        )
        
        response = knowledge_synthesis_service.synthesize_response(empty_result, "test query")
        
        assert "couldn't find information" in response.answer
        assert len(response.source_articles) == 0
        assert "Submit a request for personalized assistance" in response.followup_suggestions
        assert response.confidence_score == 0.0
    
    def test_synthesize_with_articles(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService,
        sample_search_result: SearchResult
    ):
        """Test synthesis with actual articles."""
        response = knowledge_synthesis_service.synthesize_response(
            sample_search_result, "vacation policy"
        )
        
        assert "Based on our knowledge base" in response.answer
        assert len(response.source_articles) == 2
        assert response.source_articles[0].title == "Employee Vacation Policy"
        assert len(response.related_topics) == 3
        assert len(response.followup_suggestions) > 0
        assert response.confidence_score > 0.0
    
    def test_extract_procedures(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService,
        sample_knowledge_articles: list[KnowledgeArticle]
    ):
        """Test procedure extraction from articles."""
        # Use the vacation request article which has numbered steps
        vacation_article = sample_knowledge_articles[1]
        
        procedures = knowledge_synthesis_service._extract_procedures([vacation_article])
        
        assert len(procedures) > 0
        assert any("1." in step for step in procedures)
        assert any("Log into Employee Self Service" in step for step in procedures)
    
    def test_relevance_scoring(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService,
        sample_knowledge_articles: list[KnowledgeArticle]
    ):
        """Test relevance scoring for articles."""
        article = sample_knowledge_articles[0]  # Vacation policy article
        
        # Test exact title match
        score1 = knowledge_synthesis_service._calculate_relevance_score(article, "Employee Vacation Policy")
        
        # Test partial match
        score2 = knowledge_synthesis_service._calculate_relevance_score(article, "vacation")
        
        # Test no match
        score3 = knowledge_synthesis_service._calculate_relevance_score(article, "unrelated topic")
        
        assert score1 > score2 > score3
        assert score1 > 50.0  # Should get high score for title match
    
    def test_followup_suggestions_vacation(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService,
        sample_search_result: SearchResult
    ):
        """Test vacation-specific follow-up suggestions."""
        response = knowledge_synthesis_service.synthesize_response(
            sample_search_result, "vacation policy"
        )
        
        vacation_suggestions = [
            s for s in response.followup_suggestions
            if "vacation" in s.lower() or "holiday" in s.lower()
        ]
        
        assert len(vacation_suggestions) > 0
        assert any("company holiday" in suggestion for suggestion in vacation_suggestions)
    
    def test_followup_suggestions_expense(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService
    ):
        """Test expense-specific follow-up suggestions."""
        # Create expense-related search result
        expense_result = SearchResult(
            articles=[],
            total_count=0,
            search_context="expense report",
            related_topics=["Finance", "Expenses"]
        )
        
        response = knowledge_synthesis_service.synthesize_response(
            expense_result, "expense report"
        )
        
        expense_suggestions = [
            s for s in response.followup_suggestions
            if "expense" in s.lower()
        ]
        
        assert len(expense_suggestions) > 0
    
    def test_format_response_for_oi(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService,
        sample_search_result: SearchResult
    ):
        """Test formatting response for OI consumption."""
        response = knowledge_synthesis_service.synthesize_response(
            sample_search_result, "vacation policy"
        )
        
        formatted = knowledge_synthesis_service.format_response_for_oi(response)
        
        assert "Based on our knowledge base" in formatted
        assert "**Source articles for reference:**" in formatted
        assert "**Related topics:**" in formatted
        assert "**You might also want to ask:**" in formatted
        
        # Check for markdown links
        assert "[Employee Vacation Policy]" in formatted
        assert "(https://test.service-now.com/" in formatted
    
    def test_format_response_with_procedures(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService,
        sample_search_result: SearchResult
    ):
        """Test formatting response with step-by-step procedures."""
        response = knowledge_synthesis_service.synthesize_response(
            sample_search_result, "vacation request process"
        )
        
        formatted = knowledge_synthesis_service.format_response_for_oi(response)
        
        if response.step_by_step_procedures:
            assert "**Step-by-step procedure:**" in formatted
            assert "1." in formatted
    
    def test_clean_text(self, knowledge_synthesis_service: KnowledgeSynthesisService):
        """Test HTML cleaning functionality."""
        html_text = "<p>This is <strong>bold</strong> text with <a href='#'>links</a>.</p>"
        
        cleaned = knowledge_synthesis_service._clean_text(html_text)
        
        assert "<p>" not in cleaned
        assert "<strong>" not in cleaned
        assert "This is bold text with links." in cleaned
    
    def test_redundancy_detection(self, knowledge_synthesis_service: KnowledgeSynthesisService):
        """Test redundant information detection."""
        existing_text = "This is about vacation policy and time off procedures"
        
        # Similar text should be detected as redundant
        redundant_text = "This discusses vacation policy and time off"
        is_redundant1 = knowledge_synthesis_service._is_redundant_information(
            existing_text, redundant_text
        )
        
        # Different text should not be redundant
        different_text = "This covers expense report submission guidelines"
        is_redundant2 = knowledge_synthesis_service._is_redundant_information(
            existing_text, different_text
        )
        
        assert is_redundant1 is True
        assert is_redundant2 is False
    
    def test_confidence_calculation(
        self,
        knowledge_synthesis_service: KnowledgeSynthesisService,
        sample_knowledge_articles: list[KnowledgeArticle]
    ):
        """Test confidence score calculation."""
        # High confidence with multiple relevant articles
        confidence1 = knowledge_synthesis_service._calculate_confidence_score(
            sample_knowledge_articles, "vacation policy"
        )
        
        # Lower confidence with single article
        confidence2 = knowledge_synthesis_service._calculate_confidence_score(
            sample_knowledge_articles[:1], "vacation policy"
        )
        
        # Very low confidence with irrelevant query
        confidence3 = knowledge_synthesis_service._calculate_confidence_score(
            sample_knowledge_articles[:1], "completely unrelated topic"
        )
        
        assert 0.0 <= confidence1 <= 1.0
        assert 0.0 <= confidence2 <= 1.0
        assert 0.0 <= confidence3 <= 1.0
        assert confidence1 > confidence2 > confidence3
