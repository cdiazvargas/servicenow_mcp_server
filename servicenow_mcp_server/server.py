"""ServiceNow Knowledge MCP Server implementation."""

import asyncio
import json
from typing import Any, Dict, List, Optional

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)
from pydantic import ValidationError

from .auth import AuthenticationManager
from .knowledge_synthesis import KnowledgeSynthesisService
from .servicenow_client import ServiceNowKnowledgeClient
from .types import (
    AuthenticateUserRequest,
    AuthenticateUserResponse,
    AuthenticationError,
    GetArticleRequest,
    GetArticleResponse,
    GetUserContextRequest,
    GetUserContextResponse,
    SearchKnowledgeRequest,
    SearchKnowledgeResponse,
    ServiceNowConfig,
)

logger = structlog.get_logger(__name__)


class ServiceNowMCPServer:
    """ServiceNow Knowledge MCP Server."""
    
    def __init__(self, config: ServiceNowConfig):
        self.config = config
        self.auth_manager = AuthenticationManager(config)
        self.servicenow_client = ServiceNowKnowledgeClient(config, self.auth_manager)
        self.synthesis_service = KnowledgeSynthesisService()
        
        # Create MCP server
        self.server = Server("servicenow-knowledge-server")
        self._setup_tools()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def _setup_tools(self) -> None:
        """Setup MCP tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools."""
            logger.info("handle_list_tools called")
            return [
                Tool(
                    name="authenticate_user",
                    description="Authenticate a user with ServiceNow using OAuth token or credentials. For OAuth tokens, use username='oauth_token' and the OAuth token as password.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "jwt_token": {
                                "type": "string",
                                "description": "JWT token for authentication"
                            },
                            "username": {
                                "type": "string", 
                                "description": "ServiceNow username or 'oauth_token' for OAuth authentication"
                            },
                            "password": {
                                "type": "string",
                                "description": "ServiceNow password or OAuth token when username='oauth_token'"
                            }
                        },
                        "anyOf": [
                            {"required": ["jwt_token"]},
                            {"required": ["username", "password"]}
                        ]
                    }
                ),
                Tool(
                    name="search_knowledge",
                    description="Search ServiceNow knowledge articles with role-based access control",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for knowledge articles"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "The authenticated user ID"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of articles to return (default: 10)",
                                "minimum": 1,
                                "maximum": 50,
                                "default": 10
                            },
                            "synthesize": {
                                "type": "boolean",
                                "description": "Whether to synthesize a response from multiple articles (default: true)",
                                "default": True
                            }
                        },
                        "required": ["query", "user_id"]
                    }
                ),
                Tool(
                    name="get_article",
                    description="Get a specific knowledge article by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "article_id": {
                                "type": "string",
                                "description": "The sys_id of the knowledge article"
                            },
                            "user_id": {
                                "type": "string", 
                                "description": "The authenticated user ID"
                            }
                        },
                        "required": ["article_id", "user_id"]
                    }
                ),
                Tool(
                    name="get_user_context",
                    description="Get the current user context and session information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The user ID to get context for"
                            }
                        },
                        "required": ["user_id"]
                    }
                ),
                Tool(
                    name="clear_user_session",
                    description="Clear a user session and require re-authentication",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The user ID to clear session for"
                            }
                        },
                        "required": ["user_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            try:
                logger.info("Tool call received", tool=name, user_id=arguments.get("user_id"))
                
                if name == "authenticate_user":
                    return await self._handle_authenticate_user(arguments)
                elif name == "search_knowledge":
                    return await self._handle_search_knowledge(arguments)
                elif name == "get_article":
                    return await self._handle_get_article(arguments)
                elif name == "get_user_context":
                    return await self._handle_get_user_context(arguments)
                elif name == "clear_user_session":
                    return await self._handle_clear_user_session(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"Unknown tool: {name}",
                            "code": "UNKNOWN_TOOL"
                        })
                    )]
                    
            except Exception as e:
                logger.error("Tool call failed", tool=name, error=str(e))
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": f"Tool execution failed: {str(e)}",
                        "code": "TOOL_EXECUTION_ERROR"
                    })
                )]
    
    async def _handle_authenticate_user(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle user authentication."""
        try:
            request = AuthenticateUserRequest.model_validate(arguments)
            
            if request.jwt_token:
                # JWT authentication
                logger.info("Authenticating user with JWT token")
                user_context = await self.auth_manager.authenticate_with_jwt(request.jwt_token)
                
                response = AuthenticateUserResponse(
                    success=True,
                    user_id=user_context.user_id,
                    username=user_context.username,
                    roles=user_context.roles,
                    expires_at=user_context.expires_at,
                    message=f"Successfully authenticated via JWT. User has {len(user_context.roles)} role(s): {', '.join(user_context.roles)}"
                )
                
            elif request.username and request.password:
                if request.username == "oauth_token":
                    # Direct OAuth token authentication
                    logger.info("Authenticating user with OAuth token")
                    user_context = await self.auth_manager.authenticate_with_oauth_token(request.password)
                    
                    response = AuthenticateUserResponse(
                        success=True,
                        user_id=user_context.user_id,
                        username=user_context.username,
                        roles=user_context.roles,
                        expires_at=user_context.expires_at,
                        message=f"Successfully authenticated via OAuth token. User has {len(user_context.roles)} role(s): {', '.join(user_context.roles)}"
                    )
                else:
                    # OAuth username/password authentication
                    logger.info("Authenticating user with OAuth", username=request.username)
                    user_context = await self.auth_manager.authenticate_with_oauth(
                        request.username, request.password
                    )
                    
                    response = AuthenticateUserResponse(
                        success=True,
                        user_id=user_context.user_id,
                        username=user_context.username,
                        roles=user_context.roles,
                        expires_at=user_context.expires_at,
                        message=f"Successfully authenticated via OAuth. User has {len(user_context.roles)} role(s): {', '.join(user_context.roles)}"
                    )
            else:
                response = AuthenticateUserResponse(
                    success=False,
                    message="Either jwt_token or username+password must be provided",
                    error="MISSING_CREDENTIALS"
                )
            
            return [TextContent(type="text", text=response.model_dump_json())]
            
        except AuthenticationError as e:
            logger.warning("Authentication failed", error=e.message)
            response = AuthenticateUserResponse(
                success=False,
                message=e.message,
                error=e.code
            )
            return [TextContent(type="text", text=response.model_dump_json())]
            
        except ValidationError as e:
            logger.error("Authentication request validation failed", error=str(e))
            response = AuthenticateUserResponse(
                success=False,
                message="Invalid request parameters",
                error="VALIDATION_ERROR"
            )
            return [TextContent(type="text", text=response.model_dump_json())]
    
    async def _handle_search_knowledge(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle knowledge search."""
        try:
            request = SearchKnowledgeRequest.model_validate(arguments)
            
            logger.info(
                "Searching knowledge articles",
                query=request.query,
                user_id=request.user_id,
                synthesize=request.synthesize
            )
            
            # Search articles
            search_result = await self.servicenow_client.search_knowledge_articles(
                query=request.query,
                user_id=request.user_id,
                limit=request.limit
            )
            
            if request.synthesize:
                # Synthesize response
                synthesized = self.synthesis_service.synthesize_response(
                    search_result, request.query
                )
                formatted_response = self.synthesis_service.format_response_for_oi(synthesized)
                
                return [TextContent(type="text", text=formatted_response)]
            else:
                # Return raw search results
                response = SearchKnowledgeResponse(
                    success=True,
                    raw_articles=search_result.articles
                )
                return [TextContent(type="text", text=response.model_dump_json())]
                
        except AuthenticationError as e:
            logger.warning("Authentication error during search", error=e.message)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": e.message,
                    "code": e.code,
                    "requires_reauth": e.requires_reauth,
                    "auth_url": e.auth_url
                })
            )]
            
        except ValidationError as e:
            logger.error("Search request validation failed", error=str(e))
            return [TextContent(
                type="text",
                text="Invalid search parameters. Please check your request and try again."
            )]
            
        except Exception as e:
            logger.error("Knowledge search failed", error=str(e))
            return [TextContent(
                type="text", 
                text="I encountered an error while searching the ServiceNow knowledge base. Please try again or contact support if the issue persists."
            )]
    
    async def _handle_get_article(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get article request."""
        try:
            request = GetArticleRequest.model_validate(arguments)
            
            logger.info(
                "Fetching knowledge article",
                article_id=request.article_id,
                user_id=request.user_id
            )
            
            article = await self.servicenow_client.get_knowledge_article(
                request.article_id, request.user_id
            )
            
            if article:
                response = GetArticleResponse(
                    success=True,
                    article=article
                )
            else:
                response = GetArticleResponse(
                    success=False,
                    error="Article not found or you do not have permission to access it."
                )
            
            return [TextContent(type="text", text=response.model_dump_json())]
            
        except AuthenticationError as e:
            logger.warning("Authentication error during article fetch", error=e.message)
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": e.message,
                    "code": e.code,
                    "requires_reauth": e.requires_reauth
                })
            )]
            
        except ValidationError as e:
            logger.error("Get article request validation failed", error=str(e))
            return [TextContent(
                type="text",
                text="Invalid article request parameters."
            )]
            
        except Exception as e:
            logger.error("Failed to fetch article", error=str(e))
            return [TextContent(
                type="text",
                text="Failed to retrieve the article. Please check the article ID and try again."
            )]
    
    async def _handle_get_user_context(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get user context request."""
        try:
            request = GetUserContextRequest.model_validate(arguments)
            
            user_context = await self.auth_manager.get_user_context(request.user_id)
            
            if user_context:
                response = GetUserContextResponse(
                    authenticated=True,
                    user_id=user_context.user_id,
                    username=user_context.username,
                    roles=user_context.roles,
                    expires_at=user_context.expires_at,
                    is_expired=user_context.is_expired()
                )
            else:
                response = GetUserContextResponse(
                    authenticated=False,
                    is_expired=True
                )
            
            return [TextContent(type="text", text=response.model_dump_json())]
            
        except ValidationError as e:
            logger.error("Get user context request validation failed", error=str(e))
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "Invalid request parameters",
                    "code": "VALIDATION_ERROR"
                })
            )]
    
    async def _handle_clear_user_session(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle clear user session request."""
        try:
            request = GetUserContextRequest.model_validate(arguments)  # Same schema
            
            success = await self.auth_manager.clear_user_session(request.user_id)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": success,
                    "message": "User session cleared successfully." if success else "No session found."
                })
            )]
            
        except ValidationError as e:
            logger.error("Clear session request validation failed", error=str(e))
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "Invalid request parameters",
                    "code": "VALIDATION_ERROR"
                })
            )]
    
    async def start_background_tasks(self) -> None:
        """Start background maintenance tasks."""
        async def cleanup_expired_sessions():
            """Periodically clean up expired sessions."""
            while True:
                try:
                    await asyncio.sleep(300)  # Run every 5 minutes
                    expired_count = await self.auth_manager.cleanup_expired_sessions()
                    if expired_count > 0:
                        logger.info("Cleaned up expired sessions", count=expired_count)
                except Exception as e:
                    logger.error("Error during session cleanup", error=str(e))
        
        self._cleanup_task = asyncio.create_task(cleanup_expired_sessions())
        logger.info("Background tasks started")
    
    async def stop_background_tasks(self) -> None:
        """Stop background maintenance tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        logger.info("Background tasks stopped")
    
    async def run(self) -> None:
        """Run the MCP server."""
        try:
            logger.info(
                "Starting ServiceNow Knowledge MCP Server",
                instance_url=str(self.config.instance_url),
                auth_method=self.config.auth_method.value
            )
            
            # Start background tasks
            await self.start_background_tasks()
            
            # Run the server
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream, 
                    write_stream,
                    self.server.create_initialization_options()
                )
                
        except Exception as e:
            logger.error("Server error", error=str(e))
            raise
        finally:
            # Cleanup
            await self.stop_background_tasks()
            await self.servicenow_client.close()
            logger.info("ServiceNow Knowledge MCP Server stopped")
