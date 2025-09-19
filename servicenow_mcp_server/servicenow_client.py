"""ServiceNow API client for knowledge management."""

import asyncio
import urllib.parse
from typing import Dict, List, Optional

import httpx
import structlog
from pydantic import ValidationError

from .auth import AuthenticationManager
from .types import (
    AuthenticationError,
    KnowledgeArticle,
    SearchResult,
    SearchType,
    ServiceNowAPIError,
    ServiceNowConfig,
    UserContext,
)

logger = structlog.get_logger(__name__)


class ServiceNowKnowledgeClient:
    """ServiceNow Knowledge Management API client."""
    
    def __init__(self, config: ServiceNowConfig, auth_manager: AuthenticationManager):
        self.config = config
        self.auth_manager = auth_manager
        self._client = None
        self._client_lock = asyncio.Lock()
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    self._client = httpx.AsyncClient(
                        timeout=self.config.api_timeout,
                        follow_redirects=True,
                        headers={
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "User-Agent": "ServiceNow-MCP-Server/1.0.0"
                        }
                    )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _build_search_query(self, query: str, user_context: UserContext, search_type: SearchType = SearchType.CONTENT) -> str:
        """Build ServiceNow search query with proper formatting."""
        # Clean and encode the search query
        clean_query = query.strip()
        if not clean_query:
            return "workflow_state=published"
        
        # Build search condition based on search type
        if search_type == SearchType.SYS_ID:
            # For sys_id searches, try LIKE approach since exact match might have issues
            # sys_ids are typically 32-character strings, so partial match should work
            escaped_query = clean_query.replace("'", "\\'").replace("%", "\\%").strip()
            search_condition = f"sys_idLIKE%{escaped_query}%"
        elif search_type == SearchType.NUMBER:
            # Number search works, keep as-is with exact match
            escaped_query = clean_query.replace("'", "\\'").strip()
            search_condition = f"number={escaped_query}"
        elif search_type == SearchType.TITLE_EXACT:
            # For title exact match, use same approach as working content search
            # but without OR condition - just search in short_description
            escaped_query = clean_query.replace("'", "\\'").replace("%", "\\%")
            search_condition = f"short_descriptionLIKE%{escaped_query}%"
        elif search_type == SearchType.TITLE_PARTIAL:
            # Partial title match - same as title exact for now since exact wasn't working
            escaped_query = clean_query.replace("'", "\\'").replace("%", "\\%")
            search_condition = f"short_descriptionLIKE%{escaped_query}%"
        else:  # SearchType.CONTENT (default - this works)
            # Keep the working content search as-is
            escaped_query = clean_query.replace("'", "\\'").replace("%", "\\%")
            base_conditions = [
                f"short_descriptionLIKE%{escaped_query}%",
                f"textLIKE%{escaped_query}%"
            ]
            search_condition = "(" + "^OR".join(base_conditions) + ")"
        
        # Always filter for published articles only
        query_parts = [
            "workflow_state=published",
            search_condition
        ]
        
        # Add role-based filtering
        if user_context.roles:
            # Create role conditions - articles with matching roles OR no roles (public)
            role_conditions = []
            for role in user_context.roles:
                role_conditions.append(f"rolesLIKE%{role}%")
            
            # Allow articles with no roles (public access) or matching roles
            role_filter = "(" + "^OR".join(role_conditions) + "^ORroles=NULL^ORroles=)"
            query_parts.append(role_filter)
        else:
            # If no roles, only show public articles (empty roles field)
            query_parts.append("(roles=NULL^ORroles=)")
        
        return "^".join(query_parts)
    
    async def search_knowledge_articles(
        self, 
        query: str, 
        user_id: str, 
        limit: int = 10,
        search_type: SearchType = SearchType.CONTENT
    ) -> SearchResult:
        """Search ServiceNow knowledge articles."""
        try:
            logger.info(
                "Searching knowledge articles",
                query=query,
                user_id=user_id,
                limit=limit,
                search_type=search_type
            )
            
            # Special handling for sys_id searches - use get_article instead
            if search_type == SearchType.SYS_ID:
                logger.debug("Using get_article method for sys_id search")
                article = await self.get_article(query, user_id)
                if article:
                    return SearchResult(
                        articles=[article],
                        total_count=1,
                        search_context=f"sys_id:{query}",
                        related_topics=[article.topic] if article.topic else []
                    )
                else:
                    return SearchResult(
                        articles=[],
                        total_count=0,
                        search_context=f"sys_id:{query}",
                        related_topics=[]
                    )
            
            # Get user context for role-based access
            user_context = await self.auth_manager.get_user_context(user_id)
            if not user_context or user_context.is_expired():
                raise AuthenticationError(
                    code="SESSION_EXPIRED",
                    message="User session expired. Please authenticate again.",
                    requires_reauth=True
                )
            
            client = await self._get_client()
            
            # Build search URL
            search_url = f"{self.config.instance_url}/api/now/table/kb_knowledge"
            
            # Build the search query
            search_query = self._build_search_query(query, user_context, search_type)
            
            # Build query parameters
            params = {
                "sysparm_query": search_query,
                "sysparm_limit": str(limit),
                "sysparm_fields": "sys_id,number,short_description,text,topic,category,subcategory,workflow_state,roles,can_read_user_criteria,sys_created_by,sys_created_on,sys_updated_by,sys_updated_on,view_count,helpful_count,article_type",
                "sysparm_display_value": "true",
                "sysparm_order_by": "sys_updated_on",
                "sysparm_order_direction": "desc"
            }
            
            logger.debug(
                "ServiceNow search query",
                original_query=query,
                search_type=search_type,
                final_query=search_query,
                params=params
            )
            
            # Make API request
            response = await client.get(
                search_url,
                params=params,
                headers={"Authorization": f"Bearer {user_context.session_token}"}
            )
            
            if response.status_code == 401:
                raise AuthenticationError(
                    code="UNAUTHORIZED",
                    message="Invalid or expired authentication token",
                    requires_reauth=True
                )
            elif response.status_code != 200:
                raise ServiceNowAPIError(
                    code="API_ERROR",
                    message=f"ServiceNow API error: {response.status_code}",
                    status_code=response.status_code,
                    api_response=response.json() if response.content else None
                )
            
            data = response.json()
            articles = []
            
            # Log the response for debugging
            logger.debug(
                "ServiceNow API response",
                status_code=response.status_code,
                result_count=len(data.get("result", [])),
                has_error=data.get("error") is not None
            )
            
            # Check for API errors in response
            if data.get("error"):
                logger.error(
                    "ServiceNow API returned error",
                    error=data["error"],
                    query=search_query
                )
                raise ServiceNowAPIError(
                    code="API_QUERY_ERROR",
                    message=f"ServiceNow query error: {data['error']}",
                    api_response=data
                )
            
            for item in data.get("result", []):
                try:
                    article = KnowledgeArticle(
                        sys_id=item.get("sys_id", ""),
                        number=item.get("number", ""),
                        short_description=item.get("short_description", ""),
                        text=item.get("text") or "",
                        topic=item.get("topic", ""),
                        category=item.get("category"),
                        subcategory=item.get("subcategory", ""),
                        workflow_state=item.get("workflow_state", ""),
                        roles=item.get("roles", ""),
                        can_read_user_criteria=item.get("can_read_user_criteria", ""),
                        created_by=item.get("sys_created_by", ""),
                        created_on=item.get("sys_created_on", ""),
                        updated_by=item.get("sys_updated_by", ""),
                        updated_on=item.get("sys_updated_on", ""),
                        view_count=int(item.get("view_count", 0) or 0),
                        helpful_count=int(item.get("helpful_count", 0) or 0),
                        article_type=item.get("article_type", ""),
                        direct_link=f"{self.config.instance_url}/nav_to.do?uri=kb_knowledge.do?sys_id={item.get('sys_id')}"
                    )
                    articles.append(article)
                except ValidationError as e:
                    logger.warning(
                        "Failed to parse knowledge article",
                        item=item,
                        error=str(e)
                    )
                    continue
            
            # Generate related topics from categories and topics
            related_topics = set()
            for article in articles:
                if article.topic:
                    related_topics.add(article.topic)
                if article.category:
                    related_topics.add(article.category)
            
            search_result = SearchResult(
                articles=articles,
                total_count=len(articles),
                search_context=query,
                related_topics=list(related_topics)[:10]  # Limit to 10
            )
            
            logger.info(
                "Knowledge search completed",
                query=query,
                results_count=len(articles),
                user_id=user_id
            )
            
            return search_result
            
        except (AuthenticationError, ServiceNowAPIError):
            raise
        except Exception as e:
            logger.error(
                "Knowledge search failed",
                query=query,
                user_id=user_id,
                error=str(e)
            )
            raise ServiceNowAPIError(
                code="SEARCH_ERROR",
                message=f"Knowledge search failed: {str(e)}",
                status_code=500
            )
    
    async def get_article(self, article_id: str, user_id: str) -> Optional[KnowledgeArticle]:
        """Get a specific knowledge article by ID."""
        try:
            logger.info(
                "Getting knowledge article",
                article_id=article_id,
                user_id=user_id
            )
            
            # Get user context for access control
            user_context = await self.auth_manager.get_user_context(user_id)
            if not user_context or user_context.is_expired():
                raise AuthenticationError(
                    code="SESSION_EXPIRED",
                    message="User session expired. Please authenticate again.",
                    requires_reauth=True
                )
            
            client = await self._get_client()
            
            # Build article URL
            article_url = f"{self.config.instance_url}/api/now/table/kb_knowledge/{article_id}"
            
            # Make API request
            response = await client.get(
                article_url,
                headers={"Authorization": f"Bearer {user_context.session_token}"}
            )
            
            if response.status_code == 401:
                raise AuthenticationError(
                    code="UNAUTHORIZED",
                    message="Invalid or expired authentication token",
                    requires_reauth=True
                )
            elif response.status_code == 404:
                return None
            elif response.status_code != 200:
                raise ServiceNowAPIError(
                    code="API_ERROR",
                    message=f"ServiceNow API error: {response.status_code}",
                    status_code=response.status_code
                )
            
            data = response.json()
            result = data.get("result", {})
            
            # Handle both single item and list responses
            if isinstance(result, list):
                if not result:
                    return None
                item = result[0]  # Get first item from list
            else:
                item = result
            
            if not item:
                return None
            
            article = KnowledgeArticle(
                sys_id=item.get("sys_id", ""),
                number=item.get("number", ""),
                short_description=item.get("short_description", ""),
                text=item.get("text") or "",
                topic=item.get("topic", ""),
                category=item.get("category"),
                subcategory=item.get("subcategory", ""),
                workflow_state=item.get("workflow_state", ""),
                roles=item.get("roles", ""),
                can_read_user_criteria=item.get("can_read_user_criteria", ""),
                created_by=item.get("sys_created_by", ""),
                created_on=item.get("sys_created_on", ""),
                updated_by=item.get("sys_updated_by", ""),
                updated_on=item.get("sys_updated_on", ""),
                view_count=int(item.get("view_count", 0) or 0),
                helpful_count=int(item.get("helpful_count", 0) or 0),
                article_type=item.get("article_type", ""),
                direct_link=f"{self.config.instance_url}/nav_to.do?uri=kb_knowledge.do?sys_id={item.get('sys_id')}"
            )
            
            logger.info(
                "Article retrieved successfully",
                article_id=article_id,
                title=article.short_description
            )
            
            return article
            
        except (AuthenticationError, ServiceNowAPIError):
            raise
        except Exception as e:
            logger.error(
                "Failed to get article",
                article_id=article_id,
                user_id=user_id,
                error=str(e)
            )
            raise ServiceNowAPIError(
                code="GET_ARTICLE_ERROR",
                message=f"Failed to get article: {str(e)}",
                status_code=500
            )