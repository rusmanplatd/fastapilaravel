from __future__ import annotations

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio

# Optional imports for different mail drivers
try:
    import aiosmtplib
except ImportError:
    aiosmtplib = None

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, To, Cc, Bcc, Attachment, FileContent, FileName, FileType
except ImportError:
    sendgrid = None

from app.Jobs.Job import Job
from app.Support.Facades.Log import Log
from app.Support.Facades.Config import Config


class SendEmailJob(Job):
    """
    Production email sending job with support for multiple mail drivers.
    """
    
    def __init__(
        self, 
        to_email: str, 
        subject: str, 
        body: str,
        template: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> None:
        super().__init__()
        self.to_email = to_email
        self.subject = subject
        self.body = body
        self.template = template
        self.context = context or {}
        self.attachments = attachments or []
        self.cc = cc or []
        self.bcc = bcc or []
        self.reply_to = reply_to
        
        # Configure job options
        self.options.queue = "emails"
        self.options.max_attempts = 3
        self.options.timeout = 300  # 5 minutes
        self.options.tags = ["email", "notification"]
        self.options.priority = 5
    
    def handle(self) -> None:
        """Send the email using configured mail driver."""
        try:
            mail_driver = Config.get('mail.driver', 'smtp')
            
            if mail_driver == 'smtp':
                self._send_via_smtp()
            elif mail_driver == 'ses':
                self._send_via_ses()
            elif mail_driver == 'sendgrid':
                self._send_via_sendgrid()
            elif mail_driver == 'log':
                self._send_via_log()
            else:
                raise ValueError(f"Unsupported mail driver: {mail_driver}")
                
            Log.info(f"Email sent successfully to {self.to_email} with subject: {self.subject}")
            
        except Exception as e:
            Log.error(f"Failed to send email to {self.to_email}: {str(e)}")
            raise
    
    def _send_via_smtp(self) -> None:
        """Send email via SMTP."""
        smtp_config = Config.get('mail.smtp', {})
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = self.subject
        msg['From'] = smtp_config.get('from_email', 'noreply@example.com')
        msg['To'] = self.to_email
        
        if self.cc:
            msg['Cc'] = ', '.join(self.cc)
        if self.reply_to:
            msg['Reply-To'] = self.reply_to
        
        # Render template if provided
        if self.template:
            body_content = self._render_template(self.template, self.context)
        else:
            body_content = self.body
        
        # Add HTML and plain text parts
        html_part = MIMEText(body_content, 'html')
        msg.attach(html_part)
        
        # Add attachments
        for attachment in self.attachments:
            self._add_attachment(msg, attachment)
        
        # Send email
        with smtplib.SMTP(smtp_config.get('host', 'localhost'), smtp_config.get('port', 587)) as server:
            if smtp_config.get('encryption') == 'tls':
                server.starttls(context=ssl.create_default_context())
            
            if smtp_config.get('username') and smtp_config.get('password'):
                server.login(smtp_config['username'], smtp_config['password'])
            
            recipients = [self.to_email] + self.cc + self.bcc
            server.send_message(msg, to_addrs=recipients)
    
    def _send_via_ses(self) -> None:
        """Send email via AWS SES."""
        if not boto3:
            raise ImportError("boto3 is required for SES mail driver. Install with: pip install boto3")
        
        try:
            
            ses_config = Config.get('mail.ses', {})
            
            # Create SES client
            ses_client = boto3.client(
                'ses',
                region_name=ses_config.get('region', 'us-east-1'),
                aws_access_key_id=ses_config.get('access_key'),
                aws_secret_access_key=ses_config.get('secret_key')
            )
            
            # Render template if provided
            if self.template:
                body_content = self._render_template(self.template, self.context)
            else:
                body_content = self.body
            
            destination = {
                'ToAddresses': [self.to_email]
            }
            
            if self.cc:
                destination['CcAddresses'] = self.cc
            if self.bcc:
                destination['BccAddresses'] = self.bcc
            
            # Send email
            response = ses_client.send_email(
                Destination=destination,
                Message={
                    'Body': {
                        'Html': {
                            'Charset': 'UTF-8',
                            'Data': body_content,
                        },
                    },
                    'Subject': {
                        'Charset': 'UTF-8',
                        'Data': self.subject,
                    },
                },
                Source=ses_config.get('from_email', 'noreply@example.com'),
                ReplyToAddresses=[self.reply_to] if self.reply_to else [],
            )
            
            Log.info(f"SES Message ID: {response['MessageId']}")
        except ClientError as e:
            raise Exception(f"SES error: {e.response['Error']['Message']}")
    
    def _send_via_sendgrid(self) -> None:
        """Send email via SendGrid."""
        if not sendgrid:
            raise ImportError("sendgrid is required for SendGrid mail driver. Install with: pip install sendgrid")
        
        try:
            import base64
            
            sendgrid_config = Config.get('mail.sendgrid', {})
            
            sg = sendgrid.SendGridAPIClient(api_key=sendgrid_config.get('api_key'))
            
            # Render template if provided
            if self.template:
                body_content = self._render_template(self.template, self.context)
            else:
                body_content = self.body
            
            from_email = sendgrid_config.get('from_email', 'noreply@example.com')
            to_emails = [To(self.to_email)]
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_emails,
                subject=self.subject,
                html_content=body_content
            )
            
            # Add CC recipients
            if self.cc:
                mail.cc = [Cc(email) for email in self.cc]
            
            # Add BCC recipients
            if self.bcc:
                mail.bcc = [Bcc(email) for email in self.bcc]
            
            # Add attachments
            for attachment_data in self.attachments:
                if 'file_path' in attachment_data:
                    file_path = Path(attachment_data['file_path'])
                    if file_path.exists():
                        with open(file_path, 'rb') as f:
                            data = f.read()
                        encoded_data = base64.b64encode(data).decode()
                        
                        attachment = Attachment(
                            FileContent(encoded_data),
                            FileName(attachment_data.get('name', file_path.name)),
                            FileType(attachment_data.get('type', 'application/octet-stream'))
                        )
                        mail.attachment = attachment
            
            # Send email
            response = sg.send(mail)
            Log.info(f"SendGrid response status: {response.status_code}")
            
        except Exception as e:
            raise Exception(f"SendGrid error: {str(e)}")
    
    def _send_via_log(self) -> None:
        """Log email instead of sending (useful for testing)."""
        log_message = f"""
========== EMAIL LOG ==========
To: {self.to_email}
CC: {', '.join(self.cc) if self.cc else 'None'}
BCC: {', '.join(self.bcc) if self.bcc else 'None'}
Subject: {self.subject}
Reply-To: {self.reply_to or 'None'}
Template: {self.template or 'None'}
Context: {self.context}
Body:
{self.body[:500]}{'...' if len(self.body) > 500 else ''}
Attachments: {len(self.attachments)} files
===============================
        """
        Log.info(log_message)
        print(log_message)  # Also print for visibility
    
    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        try:
            from jinja2 import Environment, FileSystemLoader
            
            templates_dir = Path('resources/views/emails')
            if not templates_dir.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)
            
            env = Environment(loader=FileSystemLoader(str(templates_dir)))
            template_obj = env.get_template(f"{template}.html")
            return template_obj.render(**context)
            
        except ImportError:
            Log.warning("Jinja2 not available for template rendering, using plain body")
            return self.body
        except Exception as e:
            Log.warning(f"Template rendering failed: {e}, using plain body")
            return self.body
    
    def _add_attachment(self, msg: MIMEMultipart, attachment_data: Dict[str, Any]) -> None:
        """Add attachment to email message."""
        if 'file_path' in attachment_data:
            file_path = Path(attachment_data['file_path'])
            if file_path.exists():
                with open(file_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment_data.get("name", file_path.name)}',
                )
                msg.attach(part)
    
    def failed(self, exception: Exception) -> None:
        """Handle email sending failure."""
        Log.error(f"SendEmailJob failed for {self.to_email}: {str(exception)}")
        
        # Could send failure notification to admins
        # Could retry with different mail driver
        # Could store in failed jobs table for manual review
        
        # Log detailed failure information
        failure_context = {
            'to_email': self.to_email,
            'subject': self.subject,
            'template': self.template,
            'error': str(exception),
            'attempt': getattr(self, 'attempt', 1)
        }
        
        Log.error("Email sending failure details", failure_context)
    
    def get_display_name(self) -> str:
        """Custom display name for the job."""
        return f"Send email: {self.subject} -> {self.to_email}"
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize job data for storage."""
        data = super().serialize()
        data["data"] = {
            "to_email": self.to_email,
            "subject": self.subject,
            "body": self.body,
            "template": self.template,
            "context": self.context,
            "attachments": self.attachments,
            "cc": self.cc,
            "bcc": self.bcc,
            "reply_to": self.reply_to
        }
        return data
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> SendEmailJob:
        """Deserialize job from stored data."""
        job_data = data.get("data", {})
        job = cls(
            to_email=job_data["to_email"],
            subject=job_data["subject"],
            body=job_data["body"],
            template=job_data.get("template"),
            context=job_data.get("context", {}),
            attachments=job_data.get("attachments", []),
            cc=job_data.get("cc", []),
            bcc=job_data.get("bcc", []),
            reply_to=job_data.get("reply_to")
        )
        
        # Restore options
        if "options" in data:
            options_data = data["options"]
            job.options.queue = options_data.get("queue", "emails")
            job.options.max_attempts = options_data.get("max_attempts", 3)
            job.options.timeout = options_data.get("timeout", 300)
            job.options.tags = options_data.get("tags", ["email", "notification"])
            job.options.priority = options_data.get("priority", 5)
        
        return job

    @classmethod
    def send_welcome_email(cls, user_email: str, user_name: str) -> str:
        """Convenience method to send welcome email."""
        return cls.dispatch(
            to_email=user_email,
            subject="Welcome to FastAPI Laravel!",
            template="welcome",
            context={
                "user_name": user_name,
                "app_name": Config.get('app.name', 'FastAPI Laravel'),
                "app_url": Config.get('app.url', 'http://localhost:8000')
            }
        )
    
    @classmethod
    def send_password_reset_email(cls, user_email: str, reset_token: str, user_name: str) -> str:
        """Convenience method to send password reset email."""
        reset_url = f"{Config.get('app.url', 'http://localhost:8000')}/reset-password?token={reset_token}&email={user_email}"
        
        return cls.dispatch(
            to_email=user_email,
            subject="Password Reset Request",
            template="password-reset",
            context={
                "user_name": user_name,
                "reset_url": reset_url,
                "app_name": Config.get('app.name', 'FastAPI Laravel')
            }
        )
    
    @classmethod
    def send_verification_email(cls, user_email: str, verification_token: str, user_name: str) -> str:
        """Convenience method to send email verification."""
        verification_url = f"{Config.get('app.url', 'http://localhost:8000')}/verify-email?token={verification_token}&email={user_email}"
        
        return cls.dispatch(
            to_email=user_email,
            subject="Please Verify Your Email Address",
            template="verify-email",
            context={
                "user_name": user_name,
                "verification_url": verification_url,
                "app_name": Config.get('app.name', 'FastAPI Laravel')
            }
        )