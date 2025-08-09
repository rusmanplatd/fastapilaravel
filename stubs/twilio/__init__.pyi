# Twilio type stub for mypy compatibility

from typing import Any, Optional

class TwilioException(Exception):
    def __init__(self, message: str = ...) -> None: ...

class TwilioRestException(TwilioException):
    def __init__(self, message: str = ..., code: Optional[int] = None, status: Optional[int] = None) -> None: ...

class MessageInstance:
    sid: str
    status: str
    
    def __init__(self, **kwargs: Any) -> None: ...

class MessagesAPI:
    def create(self, to: str, from_: str, body: str) -> MessageInstance: ...

class TwilioClient:
    messages: MessagesAPI
    
    def __init__(self, account_sid: str, auth_token: str) -> None: ...