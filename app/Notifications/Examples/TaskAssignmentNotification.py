from __future__ import annotations

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone

from app.Notifications.Notification import Notification, MailMessage

if TYPE_CHECKING:
    import importlib
    _users_module = importlib.import_module("database.migrations.2025_08_10_122400_create_users_table")
    User = _users_module.User
    from app.Notifications.Channels.PushChannel import PushMessage
    from app.Notifications.Channels.SlackChannel import SlackMessage
    from app.Notifications.Channels.DiscordChannel import DiscordMessage
    from app.Notifications.Channels.WebhookChannel import WebhookMessage


class TaskAssignmentNotification(Notification):
    """Task assignment notification for team collaboration."""
    
    def __init__(
        self, 
        task_title: str, 
        task_description: str, 
        assigned_by: str,
        due_date: Optional[datetime] = None,
        priority: str = 'medium',
        project_name: Optional[str] = None
    ):
        super().__init__()
        self.task_title = task_title
        self.task_description = task_description
        self.assigned_by = assigned_by
        self.due_date = due_date
        self.priority = priority
        self.project_name = project_name
    
    def via(self, notifiable: Any) -> List[str]:
        """Get the notification's delivery channels - focus on collaboration tools."""
        return ['database', 'mail', 'push', 'slack', 'discord', 'webhook']
    
    def to_database(self, notifiable: Any) -> Dict[str, Any]:
        """Get the database representation."""
        return {
            'title': f'New Task: {self.task_title}',
            'message': f'You have been assigned a new task by {self.assigned_by}',
            'type': 'task',
            'icon': 'clipboard-list',
            'action_url': f'/tasks/{self.task_title.lower().replace(" ", "-")}',
            'task_title': self.task_title,
            'task_description': self.task_description,
            'assigned_by': self.assigned_by,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'project_name': self.project_name
        }
    
    def to_mail(self, notifiable: Any) -> Optional[MailMessage]:
        """Get the mail representation."""
        user_name = getattr(notifiable, 'name', 'Team Member')
        
        lines = [
            f'Task: **{self.task_title}**',
            f'Assigned by: {self.assigned_by}',
            f'Priority: {self.priority.title()}',
            ''
        ]
        
        if self.project_name:
            lines.append(f'Project: {self.project_name}')
        
        if self.due_date:
            lines.append(f'Due Date: {self.due_date.strftime("%B %d, %Y at %I:%M %p")}')
        
        lines.extend([
            '',
            'Description:',
            self.task_description,
            '',
            'Please review the task details and update your progress as you work on it.'
        ])
        
        return MailMessage(
            subject=f'📋 New Task Assignment: {self.task_title}',
            greeting=f'Hello {user_name}!',
            line='You have been assigned a new task.',
            action_text='View Task',
            action_url=f'/tasks/{self.task_title.lower().replace(" ", "-")}',
            lines=lines,
            salutation='Best regards,\nThe Project Team'
        )
    
    def to_push(self, notifiable: Any) -> Optional['PushMessage']:
        """Get the push notification representation."""
        from app.Notifications.Channels.PushChannel import PushMessage
        
        priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(self.priority, '📋')
        
        return PushMessage(
            title=f'{priority_emoji} New Task Assignment',
            body=f'{self.task_title} - assigned by {self.assigned_by}',
            icon='task',
            click_action=f'/tasks/{self.task_title.lower().replace(" ", "-")}',
            data={
                'task_title': self.task_title,
                'assigned_by': self.assigned_by,
                'priority': self.priority,
                'due_date': self.due_date.isoformat() if self.due_date else None,
                'project': self.project_name or 'General'
            }
        )
    
    def to_slack(self, notifiable: Any) -> Optional['SlackMessage']:
        """Get the Slack representation."""
        from app.Notifications.Channels.SlackChannel import SlackMessage
        
        priority_color = {'high': 'danger', 'medium': 'warning', 'low': 'good'}.get(self.priority, 'good')
        priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(self.priority, '📋')
        
        fields = [
            {"title": "Assigned by", "value": self.assigned_by, "short": True},
            {"title": "Priority", "value": f"{priority_emoji} {self.priority.title()}", "short": True}
        ]
        
        if self.project_name:
            fields.append({"title": "Project", "value": self.project_name, "short": True})
        
        if self.due_date:
            fields.append({"title": "Due Date", "value": self.due_date.strftime("%Y-%m-%d %H:%M"), "short": True})
        
        attachment = {
            "color": priority_color,
            "title": f"📋 New Task: {self.task_title}",
            "text": self.task_description,
            "fields": fields,
            "actions": [
                {
                    "type": "button",
                    "text": "View Task",
                    "url": f"/tasks/{self.task_title.lower().replace(' ', '-')}",
                    "style": "primary"
                }
            ]
        }
        
        return SlackMessage(
            text=f"New task assigned to <@{getattr(notifiable, 'slack_user_id', 'user')}>",
            username="Task Bot",
            icon_emoji=":clipboard:",
            attachments=[attachment]
        )
    
    def to_discord(self, notifiable: Any) -> Optional['DiscordMessage']:
        """Get the Discord representation."""
        from app.Notifications.Channels.DiscordChannel import DiscordMessage, DiscordEmbed
        
        priority_colors = {'high': 0xff0000, 'medium': 0xffa500, 'low': 0x00ff00}
        priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(self.priority, '📋')
        
        fields = [
            {"name": "Assigned by", "value": self.assigned_by, "inline": True},
            {"name": "Priority", "value": f"{priority_emoji} {self.priority.title()}", "inline": True}
        ]
        
        if self.project_name:
            fields.append({"name": "Project", "value": self.project_name, "inline": True})
        
        if self.due_date:
            fields.append({"name": "Due Date", "value": self.due_date.strftime("%Y-%m-%d %H:%M UTC"), "inline": True})
        
        embed = DiscordEmbed(
            title="📋 New Task Assignment",
            description=f"**{self.task_title}**\n\n{self.task_description}",
            color=priority_colors.get(self.priority, 0x0099ff),
            fields=fields,
            footer={"text": "Task Management System"}
        )
        
        return DiscordMessage(
            content=f"<@{getattr(notifiable, 'discord_user_id', '123')}> You have a new task assignment!",
            username="Task Bot",
            embeds=[embed]
        )
    
    def to_webhook(self, notifiable: Any) -> Optional['WebhookMessage']:
        """Get the webhook representation for project management tools."""
        from app.Notifications.Channels.WebhookChannel import WebhookMessage, WebhookChannel
        
        payload = WebhookChannel.create_standard_payload(
            event='task.assigned',
            data={
                'task_title': self.task_title,
                'task_description': self.task_description,
                'assigned_by': self.assigned_by,
                'assigned_to': getattr(notifiable, 'email', 'Unknown'),
                'priority': self.priority,
                'due_date': self.due_date.isoformat() if self.due_date else None,
                'project_name': self.project_name,
                'status': 'assigned'
            },
            notifiable_type=notifiable.__class__.__name__,
            notifiable_id=str(notifiable.id),
            notification_type=self.__class__.__name__
        )
        
        return WebhookMessage(
            payload=payload,
            headers={
                'X-Task-Priority': self.priority,
                'X-Project': self.project_name or 'general',
                'X-Event-Type': 'task_assignment'
            }
        )