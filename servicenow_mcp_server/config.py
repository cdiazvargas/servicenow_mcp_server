"""Configuration management for ServiceNow MCP Server."""

import logging
import os
import sys
from typing import Optional

import structlog
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from .types import AuthMethod, LogLevel, ServiceNowConfig

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ServiceNow Configuration
    servicenow_instance_url: str = Field(..., description="ServiceNow instance URL")
    
    # JWT Authentication Configuration
    jwt_secret_key: Optional[str] = Field(None, description="JWT secret key for token verification")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(24, description="JWT token expiration in hours")
    
    # OAuth Configuration (fallback)
    servicenow_client_id: Optional[str] = Field(None, description="ServiceNow OAuth client ID")
    servicenow_client_secret: Optional[str] = Field(None, description="ServiceNow OAuth client secret")
    
    # MCP Server Configuration
    mcp_server_name: str = Field("servicenow-knowledge-server", description="MCP server name")
    mcp_server_version: str = Field("1.0.0", description="MCP server version")
    
    # Logging Configuration
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    log_format: str = Field("json", description="Log format (json or text)")
    
    # Authentication Configuration
    auth_timeout_seconds: int = Field(300, description="Authentication timeout in seconds")
    session_refresh_threshold_seconds: int = Field(600, description="Session refresh threshold")
    max_concurrent_sessions: int = Field(100, description="Maximum concurrent user sessions")
    
    # ServiceNow API Configuration
    servicenow_api_timeout: int = Field(30, description="ServiceNow API timeout in seconds")
    servicenow_max_retries: int = Field(3, description="Maximum API retry attempts")
    servicenow_retry_delay: float = Field(1.0, description="Delay between retries in seconds")
    
    @property
    def auth_method(self) -> AuthMethod:
        """Determine authentication method based on configuration."""
        if self.jwt_secret_key:
            return AuthMethod.JWT
        elif self.servicenow_client_id and self.servicenow_client_secret:
            return AuthMethod.OAUTH
        else:
            raise ValueError("No valid authentication method configured")
    
    def to_servicenow_config(self) -> ServiceNowConfig:
        """Convert to ServiceNowConfig object."""
        return ServiceNowConfig(
            instance_url=self.servicenow_instance_url,
            auth_method=self.auth_method,
            jwt_secret_key=self.jwt_secret_key,
            jwt_algorithm=self.jwt_algorithm,
            jwt_expiration_hours=self.jwt_expiration_hours,
            client_id=self.servicenow_client_id,
            client_secret=self.servicenow_client_secret,
            api_timeout=self.servicenow_api_timeout,
            max_retries=self.servicenow_max_retries,
            retry_delay=self.servicenow_retry_delay
        )


def load_settings() -> Settings:
    """Load application settings with validation."""
    try:
        settings = Settings()
        logger.info(
            "Configuration loaded successfully",
            servicenow_url=settings.servicenow_instance_url,
            auth_method=settings.auth_method.value,
            log_level=settings.log_level.value,
            server_name=settings.mcp_server_name
        )
        return settings
    except ValidationError as e:
        logger.error("Configuration validation failed", errors=e.errors())
        raise
    except Exception as e:
        logger.error("Failed to load configuration", error=str(e))
        raise


def validate_required_env_vars() -> None:
    """Validate that required environment variables are set."""
    required_vars = ["SERVICENOW_INSTANCE_URL"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    # Check for authentication configuration
    has_jwt = os.getenv("JWT_SECRET_KEY")
    has_oauth = os.getenv("SERVICENOW_CLIENT_ID") and os.getenv("SERVICENOW_CLIENT_SECRET")
    
    if not has_jwt and not has_oauth:
        missing_vars.extend([
            "JWT_SECRET_KEY (or SERVICENOW_CLIENT_ID + SERVICENOW_CLIENT_SECRET)"
        ])
    
    if missing_vars:
        error_msg = (
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please copy env_example_python to .env and configure the required values."
        )
        logger.error("Configuration validation failed", missing_vars=missing_vars)
        raise ValueError(error_msg)


def setup_logging(settings: Settings) -> None:
    """Setup structured logging."""
    log_level = settings.log_level.value.upper()
    
    # Map log level string to logging constant
    log_level_constant = getattr(logging, log_level, logging.INFO)
    
    # Configure standard library logging to go to stderr
    logging.basicConfig(
        level=log_level_constant,
        stream=sys.stderr,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # For MCP servers, all logging must go to stderr (not stdout)
    # because stdout is reserved for JSON-RPC communication
    class StderrLoggerFactory:
        """Logger factory that writes to stderr."""
        def __call__(self, name: str = None):
            return structlog.PrintLogger(file=sys.stderr)
    
    if settings.log_format == "json":
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level_constant),
            logger_factory=StderrLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(log_level_constant),
            logger_factory=StderrLoggerFactory(),
            cache_logger_on_first_use=True,
        )
