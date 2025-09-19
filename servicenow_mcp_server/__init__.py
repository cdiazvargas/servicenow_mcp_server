"""ServiceNow Knowledge MCP Server

An MCP (Model Context Protocol) server that integrates ServiceNow Knowledge Base 
with your company's OI (AI assistant), providing role-based access to knowledge 
articles with JWT token authentication.
"""

__version__ = "1.0.0"
__author__ = "GoDaddy"
__email__ = "cdiazvargas@godaddy.com"

from .server import ServiceNowMCPServer
from .types import (
    KnowledgeArticle,
    SearchResult,
    SynthesizedResponse,
    UserContext,
    ServiceNowConfig,
)

__all__ = [
    "ServiceNowMCPServer",
    "KnowledgeArticle",
    "SearchResult", 
    "SynthesizedResponse",
    "UserContext",
    "ServiceNowConfig",
]
