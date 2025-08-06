from fastapi import HTTPException, status
from typing import Optional, Dict, Any


class BaseController:
    def success_response(self, data: Any = None, message: str = "Success", status_code: int = 200):
        return {
            "success": True,
            "message": message,
            "data": data,
            "status_code": status_code
        }
    
    def error_response(self, message: str = "Error", status_code: int = 400, errors: Optional[Dict] = None):
        raise HTTPException(
            status_code=status_code,
            detail={
                "success": False,
                "message": message,
                "errors": errors
            }
        )
    
    def not_found(self, message: str = "Resource not found"):
        self.error_response(message, status.HTTP_404_NOT_FOUND)
    
    def unauthorized(self, message: str = "Unauthorized"):
        self.error_response(message, status.HTTP_401_UNAUTHORIZED)
    
    def forbidden(self, message: str = "Forbidden"):
        self.error_response(message, status.HTTP_403_FORBIDDEN)
    
    def validation_error(self, message: str = "Validation failed", errors: Optional[Dict] = None):
        self.error_response(message, status.HTTP_422_UNPROCESSABLE_ENTITY, errors)