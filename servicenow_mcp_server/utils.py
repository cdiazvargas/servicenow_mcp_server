"""Utility functions for ServiceNow MCP Server."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import structlog

logger = structlog.get_logger(__name__)


def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON string, returning None on error."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Failed to parse JSON", text=text[:100], error=str(e))
        return None


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize object to JSON string."""
    try:
        return json.dumps(obj, default=str, **kwargs)
    except (TypeError, ValueError) as e:
        logger.warning("Failed to serialize to JSON", error=str(e))
        return json.dumps({"error": "Serialization failed"})


def format_datetime(dt: datetime) -> str:
    """Format datetime for consistent output."""
    return dt.isoformat() + "Z" if dt else ""


def clean_string(text: str, max_length: Optional[int] = None) -> str:
    """Clean and normalize string."""
    if not text:
        return ""
    
    # Remove extra whitespace
    cleaned = " ".join(text.split())
    
    # Truncate if needed
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length - 3] + "..."
    
    return cleaned


def extract_error_message(error: Exception) -> str:
    """Extract meaningful error message from exception."""
    if hasattr(error, 'message'):
        return str(error.message)
    return str(error)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple dictionaries, with later dicts taking precedence."""
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get nested value from dictionary using dot notation."""
    try:
        keys = path.split('.')
        current = data
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError, AttributeError):
        return default


def set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
    """Set nested value in dictionary using dot notation."""
    keys = path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def validate_url(url: str) -> bool:
    """Validate URL format."""
    import re
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url))


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """Mask sensitive data in dictionary for logging."""
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'secret', 'token', 'key', 'auth', 'credential',
            'jwt', 'bearer', 'authorization'
        ]
    
    masked = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            if isinstance(value, str) and len(value) > 8:
                masked[key] = f"{value[:4]}****{value[-4:]}"
            else:
                masked[key] = "****"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            masked[key] = value
    
    return masked


def calculate_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay for retries."""
    delay = base_delay * (2 ** attempt)
    return min(delay, max_delay)


def parse_servicenow_datetime(date_str: str) -> Optional[datetime]:
    """Parse ServiceNow datetime string."""
    if not date_str:
        return None
    
    # ServiceNow typically uses format: 2024-01-01 12:00:00
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    logger.warning("Failed to parse ServiceNow datetime", date_str=date_str)
    return None


def build_servicenow_query(conditions: Dict[str, Union[str, List[str]]]) -> str:
    """Build ServiceNow query string from conditions."""
    query_parts = []
    
    for field, value in conditions.items():
        if isinstance(value, list):
            # OR conditions for multiple values
            field_conditions = [f"{field}={v}" for v in value]
            if field_conditions:
                query_parts.append("(" + "^OR".join(field_conditions) + ")")
        else:
            query_parts.append(f"{field}={value}")
    
    return "^".join(query_parts)


def estimate_text_complexity(text: str) -> float:
    """Estimate text complexity score (0.0 to 1.0)."""
    if not text:
        return 0.0
    
    # Basic complexity factors
    length_score = min(len(text) / 1000, 1.0)  # Longer = more complex
    
    # Sentence count
    sentences = text.count('.') + text.count('!') + text.count('?')
    sentence_score = min(sentences / 10, 1.0)
    
    # Technical terms (simple heuristic)
    technical_indicators = [
        'api', 'url', 'http', 'server', 'database', 'configure', 
        'admin', 'policy', 'procedure', 'system'
    ]
    technical_count = sum(1 for term in technical_indicators if term in text.lower())
    technical_score = min(technical_count / 5, 1.0)
    
    # Combine scores
    complexity = (length_score * 0.4 + sentence_score * 0.3 + technical_score * 0.3)
    return complexity
