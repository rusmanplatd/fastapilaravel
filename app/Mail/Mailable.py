from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import jinja2


@dataclass
class MailMessage:
    """Mail message data structure."""
    
    to: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    from_email: Optional[str] = None
    reply_to: Optional[str] = None
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    priority: int = 3  # 1=highest, 5=lowest


class Mailable(ABC):
    """Laravel-style Mailable base class."""
    
    def __init__(self) -> None:
        self.to_addresses: List[str] = []
        self.cc_addresses: List[str] = []
        self.bcc_addresses: List[str] = []
        self.from_address: Optional[str] = None
        self.reply_to_address: Optional[str] = None
        self.subject_line: str = ""
        self.view_name: Optional[str] = None
        self.view_data: Dict[str, Any] = {}
        self.text_view: Optional[str] = None
        self.markdown_view: Optional[str] = None
        self.attach_files: List[Dict[str, Any]] = []
        self.mail_headers: Dict[str, str] = {}
        self.mail_priority: int = 3
        
        # Template environment
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader("resources/views/emails"),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    @abstractmethod
    def build(self) -> Mailable:
        """Build the mailable."""
        pass
    
    def to(self, addresses: Union[str, List[str]]) -> Mailable:
        """Set the to addresses."""
        if isinstance(addresses, str):
            self.to_addresses = [addresses]
        else:
            self.to_addresses = addresses
        return self
    
    def cc(self, addresses: Union[str, List[str]]) -> Mailable:
        """Set the cc addresses."""
        if isinstance(addresses, str):
            self.cc_addresses = [addresses]
        else:
            self.cc_addresses = addresses
        return self
    
    def bcc(self, addresses: Union[str, List[str]]) -> Mailable:
        """Set the bcc addresses."""
        if isinstance(addresses, str):
            self.bcc_addresses = [addresses]
        else:
            self.bcc_addresses = addresses
        return self
    
    def from_email(self, address: str, name: Optional[str] = None) -> Mailable:
        """Set the from address."""
        if name:
            self.from_address = f"{name} <{address}>"
        else:
            self.from_address = address
        return self
    
    def reply_to(self, address: str) -> Mailable:
        """Set the reply-to address."""
        self.reply_to_address = address
        return self
    
    def subject(self, subject: str) -> Mailable:
        """Set the email subject."""
        self.subject_line = subject
        return self
    
    def view(self, view: str, data: Optional[Dict[str, Any]] = None) -> Mailable:
        """Set the email view template."""
        self.view_name = view
        if data:
            self.view_data.update(data)
        return self
    
    def text(self, view: str, data: Optional[Dict[str, Any]] = None) -> Mailable:
        """Set the text view template."""
        self.text_view = view
        if data:
            self.view_data.update(data)
        return self
    
    def markdown(self, view: str, data: Optional[Dict[str, Any]] = None) -> Mailable:
        """Set the markdown view template."""
        self.markdown_view = view
        if data:
            self.view_data.update(data)
        return self
    
    def attach(self, file_path: str, name: Optional[str] = None, mime_type: Optional[str] = None) -> Mailable:
        """Attach a file to the email."""
        attachment = {
            "path": file_path,
            "name": name or Path(file_path).name,
            "mime_type": mime_type
        }
        self.attach_files.append(attachment)
        return self
    
    def attach_data(self, data: bytes, name: str, mime_type: str) -> Mailable:
        """Attach raw data to the email."""
        attachment = {
            "data": data,
            "name": name,
            "mime_type": mime_type
        }
        self.attach_files.append(attachment)
        return self
    
    def with_headers(self, headers: Dict[str, str]) -> Mailable:
        """Add custom headers."""
        self.mail_headers.update(headers)
        return self
    
    def priority(self, level: int) -> Mailable:
        """Set email priority (1=highest, 5=lowest)."""
        self.mail_priority = level
        return self
    
    def with_data(self, **kwargs: Any) -> Mailable:
        """Add data to be passed to the view."""
        self.view_data.update(kwargs)
        return self
    
    def render_view(self, view_name: str) -> str:
        """Render a view template."""
        try:
            template = self.template_env.get_template(f"{view_name}.html")
            return template.render(**self.view_data)
        except jinja2.TemplateNotFound:
            return f"Template {view_name} not found"
    
    def render_text_view(self, view_name: str) -> str:
        """Render a text view template."""
        try:
            template = self.template_env.get_template(f"{view_name}.txt")
            return template.render(**self.view_data)
        except jinja2.TemplateNotFound:
            return f"Template {view_name} not found"
    
    def to_mail_message(self) -> MailMessage:
        """Convert mailable to mail message."""
        # Build the mailable first
        self.build()
        
        message = MailMessage()
        message.to = self.to_addresses
        message.cc = self.cc_addresses
        message.bcc = self.bcc_addresses
        message.from_email = self.from_address
        message.reply_to = self.reply_to_address
        message.subject = self.subject_line
        message.attachments = self.attach_files
        message.headers = self.mail_headers
        message.priority = self.mail_priority
        
        # Render views
        if self.view_name:
            message.html_body = self.render_view(self.view_name)
        
        if self.text_view:
            message.text_body = self.render_text_view(self.text_view)
        
        if self.markdown_view:
            # Convert markdown to HTML
            try:
                import markdown
                md_content = self.render_view(self.markdown_view)
                message.html_body = markdown.markdown(md_content)
            except ImportError:
                # Fallback if markdown not installed
                message.html_body = self.render_view(self.markdown_view)
        
        return message


class MailManager:
    """Laravel-style mail manager."""
    
    def __init__(self) -> None:
        self.default_driver = "smtp"
        self.drivers: Dict[str, Any] = {}
    
    def send(self, mailable: Mailable) -> bool:
        """Send a mailable."""
        message = mailable.to_mail_message()
        
        # Here you would implement actual email sending
        # For now, just print the message
        print(f"Sending email: {message.subject} to {message.to}")
        return True
    
    def queue(self, mailable: Mailable, queue_name: str = "emails") -> str:
        """Queue a mailable for later sending."""
        from app.Jobs.Examples.SendEmailJob import SendEmailJob
        
        message = mailable.to_mail_message()
        return str(SendEmailJob.dispatch(
            to_email=",".join(message.to),
            subject=message.subject,
            body=message.html_body or message.text_body
        ))
    
    def later(self, delay: int, mailable: Mailable, queue_name: str = "emails") -> str:
        """Queue a mailable for later sending with delay."""
        from app.Jobs.Examples.SendEmailJob import SendEmailJob
        
        message = mailable.to_mail_message()
        job = SendEmailJob(
            to_email=",".join(message.to),
            subject=message.subject,
            body=message.html_body or message.text_body
        )
        job.options.delay = delay
        return str(job.__class__.dispatch(
            to_email=",".join(message.to),
            subject=message.subject,
            body=message.html_body or message.text_body
        ))


# Global mail manager instance
mail_manager = MailManager()