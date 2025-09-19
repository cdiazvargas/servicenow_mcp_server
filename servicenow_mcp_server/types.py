"""Type definitions for ServiceNow Knowledge MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AuthMethod(str, Enum):
    """Authentication methods."""
    JWT = "jwt"
    OAUTH = "oauth"
    BASIC = "basic"


class SearchType(str, Enum):
    """Article search types."""
    CONTENT = "content"  # Search in title and content (default)
    SYS_ID = "sys_id"   # Search by exact sys_id
    NUMBER = "number"   # Search by article number
    TITLE_EXACT = "title_exact"  # Exact title match
    TITLE_PARTIAL = "title_partial"  # Partial title match


class ServiceNowConfig(BaseModel):
    """ServiceNow instance configuration."""
    instance_url: HttpUrl
    auth_method: AuthMethod = AuthMethod.JWT
    
    # JWT Configuration
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # OAuth Configuration (fallback)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    
    # API Configuration
    api_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


class UserContext(BaseModel):
    """User authentication and authorization context."""
    user_id: str
    username: str
    roles: List[str]
    session_token: str
    expires_at: datetime
    auth_method: AuthMethod
    
    def is_expired(self) -> bool:
        """Check if the user session is expired."""
        return datetime.utcnow() >= self.expires_at
    
    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)


class KnowledgeArticle(BaseModel):
    """ServiceNow knowledge article representation."""
    sys_id: str
    number: str
    short_description: str
    text: Optional[str] = None
    topic: str = ""
    category: Optional[str] = None
    subcategory: str = ""
    workflow_state: str
    roles: str = ""
    can_read_user_criteria: str = ""
    created_by: str
    created_on: str
    updated_by: str
    updated_on: str
    view_count: int = 0
    helpful_count: int = 0
    article_type: str = ""
    direct_link: str
    
    @property
    def role_list(self) -> List[str]:
        """Get roles as a list."""
        if not self.roles:
            return []
        return [role.strip() for role in self.roles.split(",") if role.strip()]


class SearchResult(BaseModel):
    """Knowledge article search results."""
    articles: List[KnowledgeArticle]
    total_count: int
    search_context: str
    related_topics: List[str]
    query_time_ms: Optional[float] = None


class SourceArticle(BaseModel):
    """Source article reference in synthesized response."""
    title: str
    link: str
    relevance: float = Field(ge=0.0, le=100.0)


class SynthesizedResponse(BaseModel):
    """Synthesized knowledge response."""
    answer: str
    source_articles: List[SourceArticle]
    related_topics: List[str]
    step_by_step_procedures: Optional[List[str]] = None
    followup_suggestions: List[str]
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class MCPError(Exception):
    """Base error class for MCP operations."""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class AuthenticationError(MCPError):
    """Authentication-specific error."""
    def __init__(self, code: str, message: str, requires_reauth: bool = True, auth_url: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(code, message, details)
        self.requires_reauth = requires_reauth
        self.auth_url = auth_url


class ValidationError(MCPError):
    """Validation error."""
    def __init__(self, code: str, message: str, validation_errors: List[Dict[str, Any]] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(code, message, details)
        self.validation_errors = validation_errors or []


class ServiceNowAPIError(MCPError):
    """ServiceNow API error."""
    def __init__(self, code: str, message: str, status_code: Optional[int] = None, api_response: Optional[Dict[str, Any]] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(code, message, details)
        self.status_code = status_code
        self.api_response = api_response


# JWT Token payload structure
class JWTPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # Subject (user ID)
    username: str
    roles: List[str]
    iat: int  # Issued at
    exp: int  # Expiration time
    iss: Optional[str] = None  # Issuer
    aud: Optional[str] = None  # Audience


# Request/Response models for MCP tools
class AuthenticateUserRequest(BaseModel):
    """Request model for authenticate_user tool."""
    jwt_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class AuthenticateUserResponse(BaseModel):
    """Response model for authenticate_user tool."""
    success: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    message: str
    error: Optional[str] = None


class SearchKnowledgeRequest(BaseModel):
    """Request model for search_knowledge tool."""
    query: str
    user_id: str
    limit: int = Field(default=10, ge=1, le=50)
    synthesize: bool = True
    include_related: bool = True
    search_type: SearchType = SearchType.CONTENT


class SearchKnowledgeResponse(BaseModel):
    """Response model for search_knowledge tool."""
    success: bool
    synthesized_response: Optional[SynthesizedResponse] = None
    raw_articles: Optional[List[KnowledgeArticle]] = None
    error: Optional[str] = None


class GetArticleRequest(BaseModel):
    """Request model for get_article tool."""
    article_id: str
    user_id: str


class GetArticleResponse(BaseModel):
    """Response model for get_article tool."""
    success: bool
    article: Optional[KnowledgeArticle] = None
    error: Optional[str] = None


class GetUserContextRequest(BaseModel):
    """Request model for get_user_context tool."""
    user_id: str


class GetUserContextResponse(BaseModel):
    """Response model for get_user_context tool."""
    authenticated: bool
    user_id: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    is_expired: bool = False
