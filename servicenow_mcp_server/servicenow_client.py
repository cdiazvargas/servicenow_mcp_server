"""ServiceNow API client for knowledge management."""

import asyncio
from typing import Dict, List, Optional

import httpx
import structlog
from pydantic import ValidationError

from .auth import AuthenticationManager
from .types import (
    AuthenticationError,
    KnowledgeArticle,
    SearchResult,
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
    
    async def search_knowledge_articles(
        self, 
        query: str, 
        user_id: str, 
        limit: int = 10
    ) -> SearchResult:
        """Search ServiceNow knowledge articles."""
        try:
            logger.info(
                "Searching knowledge articles",
                query=query,
                user_id=user_id,
                limit=limit
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
            
            # Build query parameters
            params = {
                "sysparm_query": f"short_descriptionLIKE{query}^ORtextLIKE{query}",
                "sysparm_limit": str(limit),
                "sysparm_fields": "sys_id,number,short_description,text,topic,category,subcategory,workflow_state,roles,can_read_user_criteria,sys_created_by,sys_created_on,sys_updated_by,sys_updated_on,view_count,helpful_count,article_type",
                "sysparm_display_value": "true"
            }
            
            # Add role-based filtering if user has specific roles
            if user_context.roles:
                role_filter = "^OR".join([f"rolesLIKE{role}" for role in user_context.roles])
                params["sysparm_query"] += f"^({role_filter}^ORroles=)"
            
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
                        view_count=int(item.get("view_count") or 0),
                        helpful_count=int(item.get("helpful_count") or 0),
                        article_type=item.get("article_type", ""),
                        direct_link=f"{self.config.instance_url}/kb_view.do?sysparm_article={item.get('number', '')}"
                    )
                    articles.append(article)
                except ValidationError as e:
                    logger.warning("Failed to parse article", error=str(e), article_data=item)
                    continue
            
            # Extract related topics from search results
            related_topics = list(set([
                article.topic for article in articles 
                if article.topic and article.topic.strip()
            ]))
            
            search_result = SearchResult(
                articles=articles,
                total_count=len(articles),
                search_context=query,
                related_topics=related_topics[:5]  # Limit to 5 related topics
            )
            
            logger.info(
                "Knowledge search completed",
                query=query,
                results_count=len(articles),
                user_id=user_id
            )
            
            return search_result
            
        except AuthenticationError:
            raise
        except ServiceNowAPIError:
            raise
        except Exception as e:
            logger.error("Knowledge search failed", error=str(e), query=query)
            raise ServiceNowAPIError(
                code="SEARCH_ERROR",
                message=f"Failed to search knowledge articles: {str(e)}"
            )
    
    async def get_knowledge_article(self, article_id: str, user_id: str) -> Optional[KnowledgeArticle]:
        """Get a specific knowledge article by ID."""
        try:
            logger.info(
                "Fetching knowledge article",
                article_id=article_id,
                user_id=user_id
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
            
            # Build article URL
            article_url = f"{self.config.instance_url}/api/now/table/kb_knowledge/{article_id}"
            
            # Query parameters
            params = {
                "sysparm_fields": "sys_id,number,short_description,text,topic,category,subcategory,workflow_state,roles,can_read_user_criteria,sys_created_by,sys_created_on,sys_updated_by,sys_updated_on,view_count,helpful_count,article_type",
                "sysparm_display_value": "true"
            }
            
            # Make API request
            response = await client.get(
                article_url,
                params=params,
                headers={"Authorization": f"Bearer {user_context.session_token}"}
            )
            
            if response.status_code == 401:
                raise AuthenticationError(
                    code="UNAUTHORIZED",
                    message="Invalid or expired authentication token",
                    requires_reauth=True
                )
            elif response.status_code == 404:
                logger.warning("Article not found", article_id=article_id)
                return None
            elif response.status_code != 200:
                raise ServiceNowAPIError(
                    code="API_ERROR",
                    message=f"ServiceNow API error: {response.status_code}",
                    status_code=response.status_code,
                    api_response=response.json() if response.content else None
                )
            
            data = response.json()
            result = data.get("result")
            
            if not result:
                return None
            
            try:
                article = KnowledgeArticle(
                    sys_id=result.get("sys_id", ""),
                    number=result.get("number", ""),
                    short_description=result.get("short_description", ""),
                    text=result.get("text") or "",
                    topic=result.get("topic", ""),
                    category=result.get("category"),
                    subcategory=result.get("subcategory", ""),
                    workflow_state=result.get("workflow_state", ""),
                    roles=result.get("roles", ""),
                    can_read_user_criteria=result.get("can_read_user_criteria", ""),
                    created_by=result.get("sys_created_by", ""),
                    created_on=result.get("sys_created_on", ""),
                    updated_by=result.get("sys_updated_by", ""),
                    updated_on=result.get("sys_updated_on", ""),
                    view_count=int(result.get("view_count") or 0),
                    helpful_count=int(result.get("helpful_count") or 0),
                    article_type=result.get("article_type", ""),
                    direct_link=f"{self.config.instance_url}/kb_view.do?sysparm_article={result.get('number', '')}"
                )
                
                # Check if user has access to this article based on roles
                if article.role_list and user_context.roles:
                    if not any(role in user_context.roles for role in article.role_list):
                        logger.warning(
                            "User does not have access to article",
                            user_id=user_id,
                            article_id=article_id,
                            required_roles=article.role_list,
                            user_roles=user_context.roles
                        )
                        return None
                
                logger.info(
                    "Article fetched successfully",
                    article_id=article_id,
                    user_id=user_id
                )
                
                return article
                
            except ValidationError as e:
                logger.error("Failed to parse article", error=str(e), article_data=result)
                return None
            
        except AuthenticationError:
            raise
        except ServiceNowAPIError:
            raise
        except Exception as e:
            logger.error("Failed to fetch article", error=str(e), article_id=article_id)
            raise ServiceNowAPIError(
                code="FETCH_ERROR",
                message=f"Failed to fetch knowledge article: {str(e)}"
            )