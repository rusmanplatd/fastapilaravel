"""Common JSON type definitions for the application.

This module provides reusable type definitions for JSON-like data structures
to replace explicit Any types throughout the codebase.
"""

from __future__ import annotations

from typing import Union, Dict, List

# JSON-compatible value types
JsonValue = Union[
    str, 
    int, 
    float, 
    bool, 
    None, 
    List['JsonValue'], 
    Dict[str, 'JsonValue']
]

# Common JSON object structures
JsonObject = Dict[str, JsonValue]
JsonArray = List[JsonValue]

# JWT/Token related types
JWTPayload = Dict[str, JsonValue]
JWTHeader = Dict[str, JsonValue]
TokenClaims = Dict[str, JsonValue]

# HTTP/API related types
HTTPHeaders = Dict[str, str]
QueryParams = Dict[str, Union[str, List[str]]]
FormData = Dict[str, Union[str, List[str]]]

# Configuration types
ConfigValue = Union[str, int, float, bool, None, List['ConfigValue'], Dict[str, 'ConfigValue']]
ConfigDict = Dict[str, ConfigValue]

# Database/Model related types
ModelAttributes = Dict[str, JsonValue]
DatabaseRow = Dict[str, JsonValue]
FilterCriteria = Dict[str, JsonValue]

# OAuth2 related types
OAuth2Claims = Dict[str, JsonValue]
OAuth2Scopes = List[str]
OAuth2TokenData = Dict[str, JsonValue]

# Cryptographic types
JWKDict = Dict[str, JsonValue]
KeyMaterial = Union[str, bytes, Dict[str, JsonValue]]

# Error/Response types
ErrorDetails = Dict[str, JsonValue]
APIResponse = Dict[str, JsonValue]
ValidationErrors = Dict[str, List[str]]

# Event/Message types
EventData = Dict[str, JsonValue]
MessagePayload = Dict[str, JsonValue]
NotificationData = Dict[str, JsonValue]

# Cache/Storage types
CacheValue = JsonValue
StorageMetadata = Dict[str, JsonValue]

# Analytics/Metrics types
MetricsData = Dict[str, Union[int, float, str, bool]]
AnalyticsEvent = Dict[str, JsonValue]