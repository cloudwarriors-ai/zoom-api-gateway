from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class CustomException(HTTPException):
    """Base exception class for custom exceptions."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class DatabaseException(CustomException):
    """Exception raised for database-related errors."""
    
    def __init__(
        self,
        detail: str = "Database operation failed",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(CustomException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(
        self,
        detail: str = "Resource not found",
        status_code: int = status.HTTP_404_NOT_FOUND,
    ):
        super().__init__(status_code=status_code, detail=detail)


class ValidationException(CustomException):
    """Exception raised for validation errors."""
    
    def __init__(
        self,
        detail: str = "Validation error",
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
    ):
        super().__init__(status_code=status_code, detail=detail)


class UnauthorizedException(CustomException):
    """Exception raised for authentication errors."""
    
    def __init__(
        self,
        detail: str = "Not authenticated",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
    ):
        super().__init__(status_code=status_code, detail=detail)


class ForbiddenException(CustomException):
    """Exception raised for authorization errors."""
    
    def __init__(
        self,
        detail: str = "Not authorized",
        status_code: int = status.HTTP_403_FORBIDDEN,
    ):
        super().__init__(status_code=status_code, detail=detail)


class ZoomAPIException(CustomException):
    """Exception raised for Zoom API-related errors."""
    
    def __init__(
        self,
        detail: str = "Zoom API error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        super().__init__(status_code=status_code, detail=detail)


class RateLimitException(CustomException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        status_code: int = status.HTTP_429_TOO_MANY_REQUESTS,
    ):
        super().__init__(status_code=status_code, detail=detail)


class TransformationError(Exception):
    """Exception raised for data transformation errors."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)