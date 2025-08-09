# Twilio base exceptions type stub

from typing import Optional

class TwilioRestException(Exception):
    msg: str
    code: Optional[int]
    status: Optional[int]
    
    def __init__(self, message: str = ..., code: Optional[int] = None, status: Optional[int] = None) -> None: ...