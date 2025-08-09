from __future__ import annotations

from typing import Optional
from app.Enums.BaseEnum import StringEnum, IntegerEnum, MetadataEnum, SelectableEnum


class HttpStatusEnum(IntegerEnum):
    """HTTP status code enum."""
    
    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # 3xx Redirection  
    MOVED_PERMANENTLY = 301
    FOUND = 302
    NOT_MODIFIED = 304
    TEMPORARY_REDIRECT = 307
    PERMANENT_REDIRECT = 308
    
    # 4xx Client Error
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    CONFLICT = 409
    GONE = 410
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # 5xx Server Error
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    
    def is_success(self) -> bool:
        """Check if status code indicates success."""
        return 200 <= self.value < 300
    
    def is_redirect(self) -> bool:
        """Check if status code indicates redirection."""
        return 300 <= self.value < 400
    
    def is_client_error(self) -> bool:
        """Check if status code indicates client error."""
        return 400 <= self.value < 500
    
    def is_server_error(self) -> bool:
        """Check if status code indicates server error."""
        return 500 <= self.value < 600


class GenderEnum(SelectableEnum):
    """Gender enum with inclusive options."""
    
    MALE: Optional[GenderEnum] = None
    FEMALE: Optional[GenderEnum] = None
    NON_BINARY: Optional[GenderEnum] = None
    PREFER_NOT_TO_SAY: Optional[GenderEnum] = None
    OTHER: Optional[GenderEnum] = None
    
    @classmethod
    def _initialize_cases(cls) -> None:
        """Initialize enum cases if not already done."""
        if cls.MALE is None:
            cls.MALE = cls('male', 'Male', 'primary', 'fas fa-mars')
            cls.FEMALE = cls('female', 'Female', 'pink', 'fas fa-venus')
            cls.NON_BINARY = cls('non_binary', 'Non-binary', 'purple', 'fas fa-transgender')
            cls.PREFER_NOT_TO_SAY = cls('prefer_not_to_say', 'Prefer not to say', 'secondary', 'fas fa-user')
            cls.OTHER = cls('other', 'Other', 'info', 'fas fa-question')
    
    @classmethod
    def cases(cls) -> list['GenderEnum']:  # type: ignore[override]
        cls._initialize_cases()
        return super().cases()  # type: ignore[return-value]


class PaymentStatusEnum(MetadataEnum):
    """Payment status enum."""
    
    PENDING: Optional[PaymentStatusEnum] = None
    PROCESSING: Optional[PaymentStatusEnum] = None
    COMPLETED: Optional[PaymentStatusEnum] = None
    FAILED: Optional[PaymentStatusEnum] = None
    CANCELLED: Optional[PaymentStatusEnum] = None
    REFUNDED: Optional[PaymentStatusEnum] = None
    PARTIALLY_REFUNDED: Optional[PaymentStatusEnum] = None
    
    @classmethod
    def _initialize_cases(cls) -> None:
        """Initialize enum cases if not already done."""
        if cls.PENDING is None:
            cls.PENDING = cls('pending', 'Pending Payment', 'warning', 'fas fa-clock')
            cls.PROCESSING = cls('processing', 'Processing Payment', 'info', 'fas fa-spinner')
            cls.COMPLETED = cls('completed', 'Payment Completed', 'success', 'fas fa-check-circle')
            cls.FAILED = cls('failed', 'Payment Failed', 'danger', 'fas fa-times-circle')
            cls.CANCELLED = cls('cancelled', 'Payment Cancelled', 'secondary', 'fas fa-ban')
            cls.REFUNDED = cls('refunded', 'Payment Refunded', 'dark', 'fas fa-undo')
            cls.PARTIALLY_REFUNDED = cls('partially_refunded', 'Partially Refunded', 'warning', 'fas fa-undo-alt')
    
    @classmethod
    def cases(cls) -> list['PaymentStatusEnum']:  # type: ignore[override]
        cls._initialize_cases()
        return super().cases()  # type: ignore[return-value]
    
    def is_final(self) -> bool:
        """Check if this is a final status (no further changes expected)."""
        return self.value in ['completed', 'failed', 'cancelled', 'refunded']
    
    def is_successful(self) -> bool:
        """Check if payment was successful."""
        return self.value in ['completed', 'refunded', 'partially_refunded']
    
    def can_refund(self) -> bool:
        """Check if payment can be refunded."""
        return self.value in ['completed', 'partially_refunded']


class OrderStatusEnum(MetadataEnum):
    """Order status enum."""
    
    CART: Optional[OrderStatusEnum] = None
    PENDING: Optional[OrderStatusEnum] = None
    CONFIRMED: Optional[OrderStatusEnum] = None
    PROCESSING: Optional[OrderStatusEnum] = None
    SHIPPED: Optional[OrderStatusEnum] = None
    DELIVERED: Optional[OrderStatusEnum] = None
    CANCELLED: Optional[OrderStatusEnum] = None
    RETURNED: Optional[OrderStatusEnum] = None
    
    @classmethod
    def _initialize_cases(cls) -> None:
        """Initialize enum cases if not already done."""
        if cls.CART is None:
            cls.CART = cls('cart', 'In Cart', 'secondary', 'fas fa-shopping-cart')
            cls.PENDING = cls('pending', 'Pending Confirmation', 'warning', 'fas fa-clock')
            cls.CONFIRMED = cls('confirmed', 'Order Confirmed', 'info', 'fas fa-check')
            cls.PROCESSING = cls('processing', 'Processing Order', 'primary', 'fas fa-cogs')
            cls.SHIPPED = cls('shipped', 'Order Shipped', 'success', 'fas fa-shipping-fast')
            cls.DELIVERED = cls('delivered', 'Order Delivered', 'success', 'fas fa-box-open')
            cls.CANCELLED = cls('cancelled', 'Order Cancelled', 'danger', 'fas fa-times')
            cls.RETURNED = cls('returned', 'Order Returned', 'dark', 'fas fa-undo')
    
    @classmethod
    def cases(cls) -> list['OrderStatusEnum']:  # type: ignore[override]
        cls._initialize_cases()
        return super().cases()  # type: ignore[return-value]
    
    def can_cancel(self) -> bool:
        """Check if order can be cancelled."""
        return self.value in ['cart', 'pending', 'confirmed']
    
    def can_ship(self) -> bool:
        """Check if order can be shipped."""
        return self.value in ['confirmed', 'processing']
    
    def is_completed(self) -> bool:
        """Check if order is completed."""
        return self.value in ['delivered', 'returned']


class NotificationTypeEnum(StringEnum):
    """Notification type enum."""
    
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'
    ALERT = 'alert'
    
    def bootstrap_class(self) -> str:
        """Get Bootstrap alert class."""
        classes = {
            'info': 'alert-info',
            'success': 'alert-success', 
            'warning': 'alert-warning',
            'error': 'alert-danger',
            'alert': 'alert-primary'
        }
        return classes.get(self.value, 'alert-secondary')
    
    def icon_class(self) -> str:
        """Get FontAwesome icon class."""
        icons = {
            'info': 'fas fa-info-circle',
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle', 
            'error': 'fas fa-times-circle',
            'alert': 'fas fa-bell'
        }
        return icons.get(self.value, 'fas fa-circle')


class PermissionScopeEnum(StringEnum):
    """Permission scope enum for authorization."""
    
    READ = 'read'
    WRITE = 'write'
    DELETE = 'delete'
    MANAGE = 'manage'
    ADMIN = 'admin'
    
    def includes(self, other: 'PermissionScopeEnum') -> bool:
        """Check if this scope includes another scope."""
        hierarchy = {
            'read': 1,
            'write': 2,
            'delete': 3,
            'manage': 4,
            'admin': 5
        }
        
        return hierarchy.get(self.value, 0) >= hierarchy.get(other.value, 0)


class ContentTypeEnum(StringEnum):
    """Content type enum for media files."""
    
    # Images
    JPEG = 'image/jpeg'
    PNG = 'image/png'
    GIF = 'image/gif'
    WEBP = 'image/webp'
    SVG = 'image/svg+xml'
    
    # Documents
    PDF = 'application/pdf'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    
    # Text
    TEXT = 'text/plain'
    CSV = 'text/csv'
    HTML = 'text/html'
    CSS = 'text/css'
    JAVASCRIPT = 'text/javascript'
    JSON = 'application/json'
    XML = 'application/xml'
    
    # Video
    MP4 = 'video/mp4'
    WEBM = 'video/webm'
    AVI = 'video/x-msvideo'
    
    # Audio
    MP3 = 'audio/mpeg'
    WAV = 'audio/wav'
    OGG = 'audio/ogg'
    
    def is_image(self) -> bool:
        """Check if content type is an image."""
        return self.value.startswith('image/')
    
    def is_video(self) -> bool:
        """Check if content type is a video."""
        return self.value.startswith('video/')
    
    def is_audio(self) -> bool:
        """Check if content type is audio."""
        return self.value.startswith('audio/')
    
    def is_document(self) -> bool:
        """Check if content type is a document."""
        document_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ]
        return self.value in document_types
    
    def file_extension(self) -> str:
        """Get typical file extension for this content type."""
        extensions = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
            'application/pdf': '.pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
            'text/plain': '.txt',
            'text/csv': '.csv',
            'text/html': '.html',
            'text/css': '.css',
            'text/javascript': '.js',
            'application/json': '.json',
            'application/xml': '.xml',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'video/x-msvideo': '.avi',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/ogg': '.ogg'
        }
        return extensions.get(self.value, '')


class TimeZoneEnum(SelectableEnum):
    """Common timezone enum."""
    
    UTC: Optional[TimeZoneEnum] = None
    US_EASTERN: Optional[TimeZoneEnum] = None
    US_CENTRAL: Optional[TimeZoneEnum] = None
    US_MOUNTAIN: Optional[TimeZoneEnum] = None
    US_PACIFIC: Optional[TimeZoneEnum] = None
    EUROPE_LONDON: Optional[TimeZoneEnum] = None
    EUROPE_PARIS: Optional[TimeZoneEnum] = None
    ASIA_TOKYO: Optional[TimeZoneEnum] = None
    ASIA_SHANGHAI: Optional[TimeZoneEnum] = None
    AUSTRALIA_SYDNEY: Optional[TimeZoneEnum] = None
    
    @classmethod
    def _initialize_cases(cls) -> None:
        """Initialize enum cases if not already done."""
        if cls.UTC is None:
            cls.UTC = cls('UTC', 'UTC (Coordinated Universal Time)')
            cls.US_EASTERN = cls('America/New_York', 'US Eastern Time')
            cls.US_CENTRAL = cls('America/Chicago', 'US Central Time')
            cls.US_MOUNTAIN = cls('America/Denver', 'US Mountain Time')
            cls.US_PACIFIC = cls('America/Los_Angeles', 'US Pacific Time')
            cls.EUROPE_LONDON = cls('Europe/London', 'London Time')
            cls.EUROPE_PARIS = cls('Europe/Paris', 'Central European Time')
            cls.ASIA_TOKYO = cls('Asia/Tokyo', 'Japan Standard Time')
            cls.ASIA_SHANGHAI = cls('Asia/Shanghai', 'China Standard Time')
            cls.AUSTRALIA_SYDNEY = cls('Australia/Sydney', 'Australian Eastern Time')
    
    @classmethod
    def cases(cls) -> list['TimeZoneEnum']:  # type: ignore[override]
        cls._initialize_cases()
        return super().cases()  # type: ignore[return-value]


class LanguageEnum(SelectableEnum):
    """Language/locale enum."""
    
    ENGLISH: Optional[LanguageEnum] = None
    SPANISH: Optional[LanguageEnum] = None
    FRENCH: Optional[LanguageEnum] = None
    GERMAN: Optional[LanguageEnum] = None
    ITALIAN: Optional[LanguageEnum] = None
    PORTUGUESE: Optional[LanguageEnum] = None
    RUSSIAN: Optional[LanguageEnum] = None
    CHINESE: Optional[LanguageEnum] = None
    JAPANESE: Optional[LanguageEnum] = None
    KOREAN: Optional[LanguageEnum] = None
    
    @classmethod
    def _initialize_cases(cls) -> None:
        """Initialize enum cases if not already done."""
        if cls.ENGLISH is None:
            cls.ENGLISH = cls('en', 'English', 'primary', '🇺🇸')
            cls.SPANISH = cls('es', 'Español', 'warning', '🇪🇸')
            cls.FRENCH = cls('fr', 'Français', 'info', '🇫🇷')
            cls.GERMAN = cls('de', 'Deutsch', 'dark', '🇩🇪')
            cls.ITALIAN = cls('it', 'Italiano', 'success', '🇮🇹')
            cls.PORTUGUESE = cls('pt', 'Português', 'secondary', '🇵🇹')
            cls.RUSSIAN = cls('ru', 'Русский', 'danger', '🇷🇺')
            cls.CHINESE = cls('zh', '中文', 'warning', '🇨🇳')
            cls.JAPANESE = cls('ja', '日本語', 'info', '🇯🇵')
            cls.KOREAN = cls('ko', '한국어', 'primary', '🇰🇷')
    
    @classmethod
    def cases(cls) -> list['LanguageEnum']:  # type: ignore[override]
        cls._initialize_cases()
        return super().cases()  # type: ignore[return-value]
    
    @property
    def flag(self) -> str:
        """Get flag emoji."""
        return self.icon or ''