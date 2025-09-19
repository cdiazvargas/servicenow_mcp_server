"""Authentication handling for ServiceNow MCP Server."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

import httpx
import jwt
import structlog
from pydantic import ValidationError

from .types import (
    AuthMethod,
    AuthenticationError,
    JWTPayload,
    ServiceNowConfig,
    UserContext,
)

logger = structlog.get_logger(__name__)


class AuthenticationManager:
    """Handles authentication for ServiceNow MCP Server."""
    
    def __init__(self, config: ServiceNowConfig):
        self.config = config
        self.user_sessions: Dict[str, UserContext] = {}
        self._session_lock = asyncio.Lock()
    
    async def authenticate_with_jwt(self, jwt_token: str) -> UserContext:
        """Authenticate user using JWT token."""
        try:
            logger.info("Authenticating user with JWT token")
            
            if not self.config.jwt_secret_key:
                raise AuthenticationError(
                    code="JWT_CONFIG_ERROR",
                    message="JWT secret key not configured",
                    requires_reauth=True
                )
            
            # Decode and verify JWT token
            payload = jwt.decode(
                jwt_token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm]
            )
            
            # Validate payload structure
            jwt_payload = JWTPayload.model_validate(payload)
            
            # Create user context
            user_context = UserContext(
                user_id=jwt_payload.sub,
                username=jwt_payload.username,
                roles=jwt_payload.roles,
                session_token=jwt_token,
                expires_at=datetime.fromtimestamp(jwt_payload.exp),
                auth_method=AuthMethod.JWT
            )
            
            # Verify token is not expired
            if user_context.is_expired():
                raise AuthenticationError(
                    code="JWT_EXPIRED",
                    message="JWT token has expired",
                    requires_reauth=True
                )
            
            # Store session
            async with self._session_lock:
                self.user_sessions[user_context.user_id] = user_context
            
            logger.info(
                "JWT authentication successful",
                user_id=user_context.user_id,
                username=user_context.username,
                roles=user_context.roles
            )
            
            return user_context
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                code="JWT_EXPIRED",
                message="JWT token has expired",
                requires_reauth=True
            )
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(
                code="JWT_INVALID",
                message=f"Invalid JWT token: {str(e)}",
                requires_reauth=True
            )
        except ValidationError as e:
            raise AuthenticationError(
                code="JWT_PAYLOAD_INVALID",
                message=f"Invalid JWT payload structure: {str(e)}",
                requires_reauth=True
            )
        except Exception as e:
            logger.error("JWT authentication failed", error=str(e))
            raise AuthenticationError(
                code="JWT_AUTH_ERROR",
                message=f"JWT authentication failed: {str(e)}",
                requires_reauth=True
            )
    
    async def authenticate_with_oauth(self, username: str, password: str) -> UserContext:
        """Authenticate user using OAuth 2.0 (fallback method)."""
        try:
            logger.info("Authenticating user with OAuth", username=username)
            
            if not self.config.client_id or not self.config.client_secret:
                raise AuthenticationError(
                    code="OAUTH_CONFIG_ERROR",
                    message="OAuth client credentials not configured",
                    requires_reauth=True
                )
            
            # OAuth token request
            token_url = f"{self.config.instance_url}/oauth_token.do"
            
            async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                        "username": username,
                        "password": password
                    }
                )
                
                if response.status_code != 200:
                    raise AuthenticationError(
                        code="OAUTH_FAILED",
                        message=f"OAuth authentication failed: {response.status_code}",
                        requires_reauth=True
                    )
                
                token_data = response.json()
                access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                
                if not access_token:
                    raise AuthenticationError(
                        code="OAUTH_NO_TOKEN",
                        message="No access token received from ServiceNow",
                        requires_reauth=True
                    )
                
                # Get user profile and roles
                user_profile = await self._get_user_profile(access_token)
                user_roles = await self._get_user_roles(access_token, user_profile["sys_id"])
                
                user_context = UserContext(
                    user_id=user_profile["sys_id"],
                    username=user_profile["user_name"],
                    roles=user_roles,
                    session_token=access_token,
                    expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                    auth_method=AuthMethod.OAUTH
                )
                
                # Store session
                async with self._session_lock:
                    self.user_sessions[user_context.user_id] = user_context
                
                logger.info(
                    "OAuth authentication successful",
                    user_id=user_context.user_id,
                    username=user_context.username,
                    roles=user_context.roles
                )
                
                return user_context
                
        except httpx.RequestError as e:
            logger.error("OAuth request failed", error=str(e))
            raise AuthenticationError(
                code="OAUTH_REQUEST_ERROR",
                message=f"Failed to connect to ServiceNow: {str(e)}",
                requires_reauth=True
            )
        except Exception as e:
            logger.error("OAuth authentication failed", error=str(e))
            raise AuthenticationError(
                code="OAUTH_AUTH_ERROR",
                message=f"OAuth authentication failed: {str(e)}",
                requires_reauth=True
            )
    
    async def _get_user_profile(self, access_token: str) -> Dict:
        """Get user profile from ServiceNow."""
        profile_url = f"{self.config.instance_url}/api/now/v1/user/profile"
        
        async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
            response = await client.get(
                profile_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise AuthenticationError(
                    code="PROFILE_FETCH_ERROR",
                    message=f"Failed to fetch user profile: {response.status_code}",
                    requires_reauth=True
                )
            
            return response.json()["result"]
    
    async def _get_user_roles(self, access_token: str, user_id: str) -> list[str]:
        """Get user roles from ServiceNow."""
        roles_url = f"{self.config.instance_url}/api/now/table/sys_user_has_role"
        
        async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
            response = await client.get(
                roles_url,
                params={
                    "sysparm_query": f"user={user_id}",
                    "sysparm_fields": "role.name"
                },
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                logger.warning(
                    "Failed to fetch user roles", 
                    status_code=response.status_code,
                    user_id=user_id
                )
                return ["knowledge"]  # Default ServiceNow knowledge role
            
            roles_data = response.json()["result"]
            return [
                role.get("role", {}).get("name", "")
                for role in roles_data
                if role.get("role", {}).get("name")
            ]
    
    async def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context by user ID."""
        async with self._session_lock:
            return self.user_sessions.get(user_id)
    
    async def refresh_user_session(self, user_id: str) -> UserContext:
        """Refresh user session if needed."""
        user_context = await self.get_user_context(user_id)
        
        if not user_context:
            raise AuthenticationError(
                code="SESSION_NOT_FOUND",
                message="No session found for user",
                requires_reauth=True
            )
        
        # Check if session is close to expiring
        time_until_expiry = (user_context.expires_at - datetime.utcnow()).total_seconds()
        refresh_threshold = self.config.jwt_expiration_hours * 3600 / 10  # 10% of expiry time
        
        if time_until_expiry > refresh_threshold:
            return user_context  # Session is still valid
        
        if user_context.auth_method == AuthMethod.JWT:
            # JWT tokens cannot be refreshed, require re-authentication
            raise AuthenticationError(
                code="JWT_REFRESH_REQUIRED",
                message="JWT token cannot be refreshed, please re-authenticate",
                requires_reauth=True
            )
        
        # For OAuth, we would implement token refresh here
        # For now, require re-authentication
        raise AuthenticationError(
            code="SESSION_EXPIRED",
            message="Session expired, please re-authenticate",
            requires_reauth=True
        )
    
    async def clear_user_session(self, user_id: str) -> bool:
        """Clear user session."""
        async with self._session_lock:
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
                logger.info("User session cleared", user_id=user_id)
                return True
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        expired_count = 0
        current_time = datetime.utcnow()
        
        async with self._session_lock:
            expired_users = [
                user_id for user_id, context in self.user_sessions.items()
                if context.expires_at <= current_time
            ]
            
            for user_id in expired_users:
                del self.user_sessions[user_id]
                expired_count += 1
        
        if expired_count > 0:
            logger.info("Cleaned up expired sessions", count=expired_count)
        
        return expired_count
    
    def generate_jwt_token(
        self, 
        user_id: str, 
        username: str, 
        roles: list[str],
        expiration_hours: Optional[int] = None
    ) -> str:
        """Generate a JWT token for a user (utility method)."""
        if not self.config.jwt_secret_key:
            raise ValueError("JWT secret key not configured")
        
        expiration_hours = expiration_hours or self.config.jwt_expiration_hours
        exp_time = datetime.utcnow() + timedelta(hours=expiration_hours)
        
        payload = JWTPayload(
            sub=user_id,
            username=username,
            roles=roles,
            iat=int(datetime.utcnow().timestamp()),
            exp=int(exp_time.timestamp()),
            iss="servicenow-mcp-server"
        )
        
        return jwt.encode(
            payload.model_dump(),
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm
        )
    
    async def authenticate_with_oauth_token(self, oauth_token: str) -> UserContext:
        """Authenticate user using an existing OAuth token."""
        try:
            logger.info("Authenticating user with OAuth token")
            
            # Get user profile using the OAuth token
            # For OAuth client credentials, we create a service user context
            async with httpx.AsyncClient(timeout=self.config.api_timeout) as client:
                # Test the token by making a simple API call
                test_response = await client.get(
                    f"{self.config.instance_url}/api/now/table/kb_knowledge",
                    params={"sysparm_limit": "1"},
                    headers={"Authorization": f"Bearer {oauth_token}"}
                )
                
                if test_response.status_code != 200:
                    raise AuthenticationError(
                        code="OAUTH_TOKEN_INVALID",
                        message=f"OAuth token validation failed: {test_response.status_code}",
                        requires_reauth=True
                    )
                
                # For OAuth client credentials, create a service user context
                # Since this is client credentials flow, we don't have a specific user
                user_id = "oauth_service_user"
                username = "oauth_service"
                
                # For client credentials, assign basic service roles
                roles = ["mcp_user", "knowledge"]
                
                # Create user context
                user_context = UserContext(
                    user_id=user_id,
                    username=username,
                    roles=roles,
                    session_token=oauth_token,
                    expires_at=datetime.utcnow() + timedelta(minutes=30),  # OAuth tokens typically expire in 30 minutes
                    auth_method=AuthMethod.OAUTH
                )
                
                # Store session
                async with self._session_lock:
                    self.user_sessions[user_context.user_id] = user_context
                
                logger.info(
                    "OAuth token authentication successful",
                    user_id=user_context.user_id,
                    username=user_context.username,
                    roles=user_context.roles
                )
                
                return user_context
                
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("OAuth token authentication failed", error=str(e))
            raise AuthenticationError(
                code="OAUTH_TOKEN_ERROR",
                message=f"OAuth token authentication failed: {str(e)}",
                requires_reauth=True
            )