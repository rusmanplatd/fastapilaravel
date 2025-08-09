from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING, Callable
from abc import ABC, abstractmethod
from fastapi import Request, HTTPException
from app.Http.Requests.FormRequest import FormRequest

if TYPE_CHECKING:
    pass


class BaseFormRequest(FormRequest):
    """
    Laravel-style Base Form Request.
    
    Provides common functionality for all form requests in the application.
    """
    
    def authorize(self) -> bool:
        """
        Determine if the user is authorized to make this request.
        
        By default, all requests are authorized. Override this method
        to add authorization logic.
        """
        return True
    
    def rules(self) -> Dict[str, Union[str, List[str]]]:
        """
        Get the validation rules that apply to the request.
        
        Override this method to define validation rules.
        """
        return {}
    
    def messages(self) -> Dict[str, str]:
        """
        Get custom validation messages.
        
        Override this method to provide custom error messages.
        """
        return {}
    
    def attributes(self) -> Dict[str, str]:
        """
        Get custom attribute names for validation errors.
        
        Override this method to provide custom attribute names.
        """
        return {}
    
    def prepare_for_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare the data for validation.
        
        Override this method to modify data before validation.
        """
        return self._trim_strings(data)
    
    def _trim_strings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trim whitespace from string values."""
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.strip()
        return data
    
    def after_validation(self, data: Dict[str, Any]) -> None:
        """
        Hook called after successful validation.
        
        Override this method to add post-validation logic.
        """
        pass
    
    def with_validator(self, validator: Any) -> BaseFormRequest:
        """
        Add custom validation logic.
        
        @param validator: Custom validator instance
        @return: Self for chaining
        """
        if not hasattr(self, '_custom_validators'):
            self._custom_validators = []
        self._custom_validators.append(validator)
        return self
    
    def sometimes(self, field: str, rules: Union[str, List[str]], callback: Callable[..., bool]) -> BaseFormRequest:
        """
        Add conditional validation rules.
        
        @param field: Field name
        @param rules: Validation rules
        @param callback: Callback to determine if rules should apply
        @return: Self for chaining
        """
        if not hasattr(self, '_conditional_rules'):
            self._conditional_rules = []
        self._conditional_rules.append({
            'field': field,
            'rules': rules,
            'callback': callback
        })
        return self
    
    def replace(self, data: Dict[str, Any]) -> BaseFormRequest:
        """
        Replace the request data.
        
        @param data: New request data
        @return: Self for chaining
        """
        self._data = data.copy()
        return self
    
    def merge(self, data: Dict[str, Any]) -> BaseFormRequest:
        """
        Merge additional data into the request.
        
        @param data: Data to merge
        @return: Self for chaining
        """
        if hasattr(self, '_data'):
            self._data.update(data)
        else:
            self._data = data.copy()
        return self
    
    def validate_resolved(self) -> Dict[str, Any]:
        """
        Get the validated data from a resolved form request.
        
        This method assumes validation has already been performed.
        """
        return self.validated()
    
    def get_validator_instance(self) -> Any:
        """
        Get the validator instance for the request.
        
        @return: Validator instance
        """
        from app.Validation.Validator import Validator
        
        validator = Validator(self.validated(), self.rules(), self.messages())
        
        return validator
    
    def fail_unauthorized(self, message: str = "This action is unauthorized.") -> None:
        """
        Throw an unauthorized exception.
        
        @param message: Error message
        """
        raise HTTPException(status_code=403, detail=message)
    
    def fail_validation(self, errors: Dict[str, List[str]]) -> None:
        """
        Throw a validation exception.
        
        @param errors: Validation errors
        """
        raise HTTPException(
            status_code=422,
            detail={
                "message": "The given data was invalid.",
                "errors": errors
            }
        )