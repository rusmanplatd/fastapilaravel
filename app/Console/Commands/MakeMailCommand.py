from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeMailCommand(Command):
    """Generate a new mailable class."""
    
    signature = "make:mail {name : The name of the mailable} {--markdown : Generate a markdown template} {--force : Overwrite existing files}"
    description = "Create a new mailable class"
    help = "Generate a new mailable class for sending emails"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        markdown = self.option("markdown")
        force = self.option("force")
        
        if not name:
            self.error("Mailable name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Mail"):
            name += "Mail"
        
        mail_path = Path(f"app/Mail/{name}.py")
        mail_path.parent.mkdir(parents=True, exist_ok=True)
        
        if mail_path.exists() and not force:
            if not self.confirm(f"Mailable {name} already exists. Overwrite?"):
                self.info("Mailable creation cancelled.")
                return
        
        # Generate the mailable class
        content = self._generate_mail_content(name, markdown)
        mail_path.write_text(content)
        
        # Generate email template if requested
        if markdown:
            self._generate_markdown_template(name)
        else:
            self._generate_html_template(name)
        
        self.info(f"✅ Mailable created: {mail_path}")
        
        template_name = self._get_template_name(name)
        if markdown:
            self.comment(f"Markdown template created at: resources/views/emails/{template_name}.md")
        else:
            self.comment(f"HTML template created at: resources/views/emails/{template_name}.html")
        
        self.comment("Update the build() method with your email content")
    
    def _generate_mail_content(self, mail_name: str, markdown: bool = False) -> str:
        """Generate mailable content."""
        template_method = "markdown" if markdown else "view"
        template_name = self._get_template_name(mail_name)
        
        return f'''from __future__ import annotations

from typing import Any, Dict, Optional
from .Mailable import Mailable


class {mail_name}(Mailable):
    """Mailable class for sending emails."""
    
    def __init__(self, **kwargs: Any) -> None:
        """Initialize the mailable with data."""
        super().__init__()
        self.data = kwargs
    
    def build(self) -> Mailable:
        """Build the email."""
        return (self
                .subject("Your Subject Here")
                .{template_method}("emails.{template_name}")
                .with_data(**self.data))
    
    # Example with specific data
    # def __init__(self, user: User, message: str) -> None:
    #     super().__init__()
    #     self.user = user
    #     self.message = message
    # 
    # def build(self) -> Mailable:
    #     return (self
    #             .subject(f"Message for {{self.user.name}}")
    #             .{template_method}("emails.{template_name}")
    #             .with_data(
    #                 user=self.user,
    #                 message=self.message,
    #                 app_name="Your App"
    #             ))
'''
    
    def _get_template_name(self, mail_name: str) -> str:
        """Get the template name from mail class name."""
        # Convert camelCase to snake_case and remove 'mail' suffix
        name = mail_name.replace('Mail', '')
        # Convert CamelCase to snake_case
        import re
        template_name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        return template_name
    
    def _generate_html_template(self, mail_name: str) -> None:
        """Generate HTML email template."""
        template_name = self._get_template_name(mail_name)
        template_path = Path(f"resources/views/emails/{template_name}.html")
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not template_path.exists():
            content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ subject }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }
        .content {
            background-color: #ffffff;
            padding: 30px;
            border-left: 1px solid #dee2e6;
            border-right: 1px solid #dee2e6;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
            color: #6c757d;
            border-radius: 0 0 8px 8px;
            border-top: 1px solid #dee2e6;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 16px 0;
        }
        .button:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ app_name|default("Your Application") }}</h1>
    </div>
    
    <div class="content">
        <h2>Hello{% if user %} {{ user.name }}{% endif %}!</h2>
        
        <p>This is your email content. Update this template with your message.</p>
        
        <!-- Example dynamic content -->
        {% if message %}
        <p>{{ message }}</p>
        {% endif %}
        
        <!-- Example button -->
        <!-- <a href="#" class="button">Call to Action</a> -->
        
        <p>Thank you for using our service!</p>
    </div>
    
    <div class="footer">
        <p>&copy; {{ "now"|date("Y") }} {{ app_name|default("Your Application") }}. All rights reserved.</p>
        <p>
            <a href="#">Unsubscribe</a> | 
            <a href="#">Contact Us</a>
        </p>
    </div>
</body>
</html>'''
            template_path.write_text(content)
    
    def _generate_markdown_template(self, mail_name: str) -> None:
        """Generate Markdown email template."""
        template_name = self._get_template_name(mail_name)
        template_path = Path(f"resources/views/emails/{template_name}.md")
        template_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not template_path.exists():
            content = '''@component('mail::message')
# Hello{% if user %} {{ user.name }}{% endif %}!

This is your email content written in Markdown. Update this template with your message.

{% if message %}
{{ message }}
{% endif %}

@component('mail::button', {'url': '#'})
Call to Action
@endcomponent

Thanks for using our service!

Best regards,  
{{ app_name|default("Your Application") }}

@component('mail::subcopy')
If you're having trouble clicking the "Call to Action" button, copy and paste the URL below into your web browser: [#](#)
@endcomponent
@endcomponent
'''
            template_path.write_text(content)
# Register the command
from app.Console.Artisan import register_command
register_command(MakeMailCommand)
