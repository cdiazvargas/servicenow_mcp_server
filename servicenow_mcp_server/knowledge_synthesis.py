"""Knowledge synthesis service for combining and formatting knowledge articles."""

import html
import re
from typing import List, Set, Tuple

import structlog

from .types import KnowledgeArticle, SearchResult, SourceArticle, SynthesizedResponse

logger = structlog.get_logger(__name__)


class KnowledgeSynthesisService:
    """Service for synthesizing knowledge articles into coherent responses."""
    
    def __init__(self):
        # Common procedure indicators
        self.procedure_indicators = [
            "step", "first", "then", "next", "finally", "procedure", 
            "process", "follow", "instructions", "guide"
        ]
        
        # Action words that indicate procedural steps
        self.action_words = [
            "click", "navigate", "select", "enter", "submit", "open", 
            "go to", "access", "login", "fill", "choose", "complete"
        ]
    
    def synthesize_response(
        self, 
        search_result: SearchResult, 
        original_query: str
    ) -> SynthesizedResponse:
        """Synthesize a comprehensive response from search results."""
        articles = search_result.articles
        
        if not articles:
            return self._create_no_results_response()
        
        logger.info(
            "Synthesizing knowledge response",
            query=original_query,
            article_count=len(articles)
        )
        
        # Rank articles by relevance
        ranked_articles = self._rank_articles_by_relevance(articles, original_query)
        
        # Create synthesized answer
        answer = self._create_synthesized_answer(ranked_articles, original_query)
        
        # Extract procedures if available
        procedures = self._extract_procedures(ranked_articles[:2])  # Top 2 articles
        
        # Generate follow-up suggestions
        followup_suggestions = self._generate_followup_suggestions(
            ranked_articles, search_result.related_topics, original_query
        )
        
        # Create source article references
        source_articles = [
            SourceArticle(
                title=article.short_description,
                link=article.direct_link,
                relevance=self._calculate_relevance_score(article, original_query)
            )
            for article in ranked_articles[:5]  # Top 5 articles
        ]
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(ranked_articles, original_query)
        
        return SynthesizedResponse(
            answer=answer,
            source_articles=source_articles,
            related_topics=search_result.related_topics[:5],
            step_by_step_procedures=procedures if procedures else None,
            followup_suggestions=followup_suggestions,
            confidence_score=confidence_score
        )
    
    def format_response_for_oi(self, response: SynthesizedResponse) -> str:
        """Format synthesized response for OI consumption."""
        formatted = response.answer
        
        # Add step-by-step procedures
        if response.step_by_step_procedures:
            formatted += "\n\n**Step-by-step procedure:**\n"
            for i, step in enumerate(response.step_by_step_procedures, 1):
                formatted += f"{i}. {step}\n"
        
        # Add source articles
        if response.source_articles:
            formatted += "\n\n**Source articles for reference:**\n"
            for source in response.source_articles:
                formatted += f"• [{source.title}]({source.link})\n"
        
        # Add related topics
        if response.related_topics:
            topics_str = ", ".join(response.related_topics)
            formatted += f"\n\n**Related topics:** {topics_str}"
        
        # Add follow-up suggestions
        if response.followup_suggestions:
            formatted += "\n\n**You might also want to ask:**\n"
            for suggestion in response.followup_suggestions:
                formatted += f"• {suggestion}\n"
        
        return formatted
    
    def _create_no_results_response(self) -> SynthesizedResponse:
        """Create response when no articles are found."""
        return SynthesizedResponse(
            answer=(
                "I couldn't find information about this in our ServiceNow knowledge base. "
                "Click here to submit a request for personalized assistance."
            ),
            source_articles=[],
            related_topics=[],
            followup_suggestions=[
                "Submit a request for personalized assistance",
                "Try searching with different keywords",
                "Contact your IT support team"
            ],
            confidence_score=0.0
        )
    
    def _rank_articles_by_relevance(
        self, 
        articles: List[KnowledgeArticle], 
        query: str
    ) -> List[KnowledgeArticle]:
        """Rank articles by relevance to the query."""
        scored_articles = [
            (article, self._calculate_relevance_score(article, query))
            for article in articles
        ]
        
        # Sort by relevance score (descending)
        scored_articles.sort(key=lambda x: x[1], reverse=True)
        
        return [article for article, _ in scored_articles]
    
    def _calculate_relevance_score(self, article: KnowledgeArticle, query: str) -> float:
        """Calculate relevance score for an article."""
        score = 0.0
        query_lower = query.lower()
        title_lower = article.short_description.lower()
        text_lower = self._clean_text(article.text).lower()
        
        # Title matches (highest weight)
        if query_lower in title_lower:
            score += 100.0
        
        # Exact phrase match in content
        if query_lower in text_lower:
            score += 50.0
        
        # Individual word matches
        query_words = query_lower.split()
        for word in query_words:
            if len(word) > 2:  # Ignore very short words
                if word in title_lower:
                    score += 20.0
                if word in text_lower:
                    score += 10.0
        
        # Boost based on article metrics
        score += min(article.view_count * 0.1, 20.0)  # Max 20 points
        score += min(article.helpful_count * 2.0, 30.0)  # Max 30 points
        
        # Boost recent articles
        # Note: Would need date parsing for full implementation
        # For now, just ensure score is within reasonable range
        
        return min(score, 100.0)  # Cap at 100
    
    def _create_synthesized_answer(
        self, 
        articles: List[KnowledgeArticle], 
        query: str
    ) -> str:
        """Create a synthesized answer from multiple articles."""
        if not articles:
            return "No relevant knowledge articles found for your query."
        
        primary_article = articles[0]
        supporting_articles = articles[1:3]  # Up to 2 supporting articles
        
        answer = "Based on our knowledge base:\n\n"
        
        # Start with the most relevant article
        primary_info = self._extract_key_information(primary_article.text)
        answer += primary_info
        
        # Add information from supporting articles
        for article in supporting_articles:
            additional_info = self._extract_key_information(article.text)
            if additional_info and not self._is_redundant_information(answer, additional_info):
                answer += f"\n\nAdditional Information:\n{additional_info}"
        
        return answer
    
    def _extract_key_information(self, article_text: str) -> str:
        """Extract key information from article text."""
        # Clean HTML and normalize text
        clean_text = self._clean_text(article_text)
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in clean_text.split('\n') if len(p.strip()) > 20]
        
        if not paragraphs:
            return clean_text[:500] + ("..." if len(clean_text) > 500 else "")
        
        # Return first substantial paragraph
        first_paragraph = paragraphs[0]
        return first_paragraph[:500] + ("..." if len(first_paragraph) > 500 else "")
    
    def _clean_text(self, text: str) -> str:
        """Clean HTML tags and normalize text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _is_redundant_information(self, existing_answer: str, new_info: str) -> bool:
        """Check if new information is redundant with existing answer."""
        existing_words = set(existing_answer.lower().split())
        new_words = set(new_info.lower().split())
        
        if not new_words:
            return True
        
        # Calculate overlap percentage
        overlap = len(existing_words.intersection(new_words))
        overlap_percentage = overlap / len(new_words)
        
        return overlap_percentage > 0.7  # 70% overlap threshold
    
    def _extract_procedures(self, articles: List[KnowledgeArticle]) -> List[str]:
        """Extract step-by-step procedures from articles."""
        procedures = []
        
        for article in articles:
            steps = self._find_step_by_step_instructions(article.text)
            if steps:
                procedures.extend(steps)
                break  # Use first good procedure found
        
        return procedures[:10]  # Limit to 10 steps
    
    def _find_step_by_step_instructions(self, text: str) -> List[str]:
        """Find step-by-step instructions in text."""
        clean_text = self._clean_text(text)
        
        # Look for numbered lists (1. 2. 3. or 1) 2) 3))
        numbered_pattern = r'(?:^|\n)\s*(\d+)[.\)]\s*([^\n]+)'
        numbered_matches = re.findall(numbered_pattern, clean_text, re.MULTILINE)
        
        if len(numbered_matches) >= 2:
            return [f"{num}. {step.strip()}" for num, step in numbered_matches]
        
        # Look for bullet points with step indicators
        lines = clean_text.split('\n')
        procedure_lines = []
        
        for line in lines:
            line = line.strip()
            line_lower = line.lower()
            
            # Check for bullet points with procedure indicators
            if (line.startswith(('-', '*', '•')) and 
                any(indicator in line_lower for indicator in self.procedure_indicators)):
                procedure_lines.append(line)
            
            # Check for lines starting with action words
            elif any(line_lower.startswith(word) for word in self.action_words):
                procedure_lines.append(line)
        
        return procedure_lines[:10] if len(procedure_lines) >= 2 else []
    
    def _generate_followup_suggestions(
        self,
        articles: List[KnowledgeArticle],
        related_topics: List[str],
        original_query: str
    ) -> List[str]:
        """Generate follow-up suggestions based on content and query."""
        suggestions = []
        query_lower = original_query.lower()
        
        # Add related topic suggestions
        for topic in related_topics[:3]:
            if topic:
                suggestions.append(f"Learn more about {topic}")
        
        # Add specific follow-up questions based on query content
        if any(word in query_lower for word in ['vacation', 'time off', 'leave']):
            suggestions.extend([
                "What if I'm taking vacation during a company holiday?",
                "How do I request emergency time off?",
                "What's the vacation approval process?"
            ])
        
        elif any(word in query_lower for word in ['expense', 'reimbursement', 'receipt']):
            suggestions.extend([
                "What expenses are reimbursable?",
                "How long does expense approval take?",
                "What documentation do I need for expenses?"
            ])
        
        elif any(word in query_lower for word in ['benefits', 'enrollment', 'insurance']):
            suggestions.extend([
                "When is open enrollment?",
                "How do I change my benefits?",
                "What benefits am I eligible for?"
            ])
        
        elif any(word in query_lower for word in ['password', 'login', 'access']):
            suggestions.extend([
                "How do I reset my password?",
                "What if I'm locked out of my account?",
                "How do I set up two-factor authentication?"
            ])
        
        # Add general suggestions if no specific ones found
        if len(suggestions) < 3:
            suggestions.extend([
                "Contact HR for personalized assistance",
                "Browse related knowledge articles",
                "Submit a detailed support request"
            ])
        
        # Remove duplicates and limit to 5
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
                if len(unique_suggestions) >= 5:
                    break
        
        return unique_suggestions
    
    def _calculate_confidence_score(
        self, 
        articles: List[KnowledgeArticle], 
        query: str
    ) -> float:
        """Calculate confidence score for the synthesized response."""
        if not articles:
            return 0.0
        
        # Base confidence on number of articles
        article_score = min(len(articles) / 5.0, 1.0)  # Max at 5 articles
        
        # Factor in relevance of top article
        top_relevance = self._calculate_relevance_score(articles[0], query) / 100.0
        
        # Factor in article quality metrics
        quality_score = 0.0
        for article in articles[:3]:  # Top 3 articles
            article_quality = min(
                (article.view_count * 0.01 + article.helpful_count * 0.1) / 10.0,
                1.0
            )
            quality_score += article_quality
        
        quality_score = quality_score / min(len(articles), 3)  # Average
        
        # Combine scores
        confidence = (article_score * 0.4 + top_relevance * 0.4 + quality_score * 0.2)
        
        return min(confidence, 1.0)
