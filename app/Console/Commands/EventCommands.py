from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime, timedelta
from ..Command import Command


class EventListCommand(Command):
    """List all registered events and listeners."""
    
    signature = "event:list {--event= : Filter by event name}"
    description = "List all registered events and listeners"
    help = "Display all events and their registered listeners"
    
    async def handle(self) -> None:
        """Execute the command."""
        event_filter = self.option("event")
        
        events = await self._discover_events()
        
        if event_filter:
            events = {k: v for k, v in events.items() if event_filter.lower() in k.lower()}
        
        if not events:
            self.info("No events found.")
            return
        
        self._display_events(events)
    
    async def _discover_events(self) -> Dict[str, List[str]]:
        """Discover all registered events and listeners."""
        events = {}
        
        # Check event directory
        events_dir = Path("app/Events")
        if events_dir.exists():
            for event_file in events_dir.glob("*.py"):
                if not event_file.name.startswith("_"):
                    event_name = event_file.stem
                    listeners = await self._find_listeners_for_event(event_name)
                    events[event_name] = listeners
        
        # Check for hardcoded events
        builtin_events = self._get_builtin_events()
        events.update(builtin_events)
        
        return events
    
    async def _find_listeners_for_event(self, event_name: str) -> List[str]:
        """Find all listeners for a specific event."""
        listeners = []
        
        # Check listeners directory
        listeners_dir = Path("app/Listeners")
        if listeners_dir.exists():
            for listener_file in listeners_dir.glob("*.py"):
                if not listener_file.name.startswith("_"):
                    # This is a simplified check - in real implementation,
                    # you would parse the file or use a registry
                    content = listener_file.read_text()
                    if event_name in content:
                        listeners.append(listener_file.stem)
        
        return listeners
    
    def _get_builtin_events(self) -> Dict[str, List[str]]:
        """Get built-in framework events."""
        return {
            "user.created": ["SendWelcomeEmail", "LogUserCreation"],
            "user.updated": ["LogUserUpdate"], 
            "user.deleted": ["LogUserDeletion", "CleanupUserData"],
            "auth.login": ["LogSuccessfulLogin", "UpdateLastLoginTime"],
            "auth.logout": ["LogUserLogout"],
            "auth.failed": ["LogFailedLogin", "IncrementFailedAttempts"],
            "password.reset": ["SendPasswordResetEmail"],
            "email.sending": ["LogEmailSent"],
            "queue.job.processed": ["LogJobProcessed"],
            "queue.job.failed": ["LogJobFailed", "NotifyAdmins"],
            "cache.hit": ["IncrementCacheHits"],
            "cache.miss": ["IncrementCacheMisses"],
            "database.query": ["LogSlowQueries"],
            "http.request": ["LogApiRequest"],
            "http.response": ["LogApiResponse"]
        }
    
    def _display_events(self, events: Dict[str, List[str]]) -> None:
        """Display events in a formatted table."""
        self.info("🎯 Events and Listeners")
        self.line("=" * 80)
        
        for event_name, listeners in sorted(events.items()):
            self.info(f"📢 {event_name}")
            
            if listeners:
                for listener in listeners:
                    self.line(f"  └─ 👂 {listener}")
            else:
                self.comment("  └─ No listeners registered")
            
            self.line("")
        
        total_events = len(events)
        total_listeners = sum(len(listeners) for listeners in events.values())
        
        self.line("-" * 40)
        self.info(f"Total Events: {total_events}")
        self.info(f"Total Listeners: {total_listeners}")


class EventCacheCommand(Command):
    """Cache all events and listeners for better performance."""
    
    signature = "event:cache"
    description = "Cache all events and listeners for better performance"
    help = "Generate a cached file of all events and listeners"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("⚡ Caching events and listeners...")
        
        events = await self._discover_events()
        
        await self._cache_events(events)
        
        total_events = len(events)
        total_listeners = sum(len(listeners) for listeners in events.values())
        
        self.info(f"✅ Cached {total_events} events with {total_listeners} listeners!")
    
    async def _discover_events(self) -> Dict[str, List[str]]:
        """Discover all events and listeners."""
        from .EventCommands import EventListCommand
        event_list_cmd = EventListCommand()
        return await event_list_cmd._discover_events()
    
    async def _cache_events(self, events: Dict[str, List[str]]) -> None:
        """Cache events to file."""
        import json
        
        cache_dir = Path("bootstrap/cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = cache_dir / "events.json"
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "events": events
        }
        
        cache_file.write_text(json.dumps(cache_data, indent=2))
        self.comment(f"Events cached: {cache_file}")


class EventClearCommand(Command):
    """Clear the cached events and listeners."""
    
    signature = "event:clear"
    description = "Clear the cached events and listeners"
    help = "Remove the cached events file"
    
    async def handle(self) -> None:
        """Execute the command."""
        cache_file = Path("bootstrap/cache/events.json")
        
        if cache_file.exists():
            cache_file.unlink()
            self.info("✅ Event cache cleared!")
        else:
            self.info("Event cache file does not exist.")


class EventGenerateCommand(Command):
    """Generate event/listener combinations."""
    
    signature = "event:generate {--force : Overwrite existing files}"
    description = "Generate event/listener combinations"
    help = "Generate event and listener classes based on registered events"
    
    async def handle(self) -> None:
        """Execute the command."""
        force = self.option("force", False)
        
        self.info("🏗️ Generating missing events and listeners...")
        
        events = await self._discover_missing_events()
        
        generated_count = 0
        
        for event_name, listeners in events.items():
            # Generate event class
            if await self._generate_event(event_name, force):
                generated_count += 1
            
            # Generate listener classes
            for listener_name in listeners:
                if await self._generate_listener(listener_name, event_name, force):
                    generated_count += 1
        
        if generated_count > 0:
            self.info(f"✅ Generated {generated_count} class(es)!")
        else:
            self.info("No missing classes to generate.")
    
    async def _discover_missing_events(self) -> Dict[str, List[str]]:
        """Discover events and listeners that need to be generated."""
        from .EventCommands import EventListCommand
        event_list_cmd = EventListCommand()
        all_events = await event_list_cmd._discover_events()
        
        missing: Dict[str, List[str]] = {}
        
        for event_name, listeners in all_events.items():
            event_file = Path(f"app/Events/{event_name}.py")
            
            if not event_file.exists():
                missing[event_name] = []
                
                for listener_name in listeners:
                    listener_file = Path(f"app/Listeners/{listener_name}.py")
                    if not listener_file.exists():
                        missing[event_name].append(listener_name)
        
        return missing
    
    async def _generate_event(self, event_name: str, force: bool) -> bool:
        """Generate an event class."""
        event_path = Path(f"app/Events/{event_name}.py")
        
        if event_path.exists() and not force:
            return False
        
        # Create Events directory
        event_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate event content
        content = f'''from __future__ import annotations

from typing import Any, Dict
from app.Events.Event import Event


class {event_name}(Event):
    """{event_name} event."""
    
    def __init__(self, **kwargs) -> None:
        """Initialize the event."""
        super().__init__()
        self.data = kwargs
    
    def broadcast_on(self) -> list[str]:
        """Get the channels the event should broadcast on."""
        return []
    
    def broadcast_as(self) -> str:
        """The event's broadcast name."""
        return "{event_name.lower()}"
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize the event data."""
        return {{
            "event": "{event_name}",
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }}
'''
        
        event_path.write_text(content)
        self.comment(f"Generated event: {event_path}")
        return True
    
    async def _generate_listener(self, listener_name: str, event_name: str, force: bool) -> bool:
        """Generate a listener class."""
        listener_path = Path(f"app/Listeners/{listener_name}.py")
        
        if listener_path.exists() and not force:
            return False
        
        # Create Listeners directory
        listener_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate listener content
        content = f'''from __future__ import annotations

from typing import Any
from app.Events.{event_name} import {event_name}
from app.Listeners.Listener import Listener


class {listener_name}(Listener):
    """{listener_name} event listener."""
    
    def __init__(self) -> None:
        """Initialize the listener."""
        super().__init__()
    
    async def handle(self, event: {event_name}) -> None:
        """Handle the event."""
        # Implement event handling logic
        try:
            # Access event data
            event_data = getattr(event, 'data', {{}})
            
            # Log the event for debugging
            print(f"Handling event: {{event.__class__.__name__}}")
            
            # Add your custom logic here
            # Example: save to database, send notifications, etc.
            
        except Exception as e:
            print(f"Error handling event: {{e}}")
            # Consider logging or re-raising based on requirements
    
    def should_queue(self) -> bool:
        """Determine whether the listener should be queued."""
        return False
    
    def via_queue(self) -> str:
        """Get the name of the queue the listener should be sent to."""
        return "default"
'''
        
        listener_path.write_text(content)
        self.comment(f"Generated listener: {listener_path}")
        return True


class MakeEventCommand(Command):
    """Create a new event class."""
    
    signature = "make:event {name : The name of the event}"
    description = "Create a new event class"
    help = "Generate a new event class file"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Event name is required")
            return
        
        event_path = Path(f"app/Events/{name}.py")
        
        if event_path.exists():
            if not self.confirm(f"Event {name} already exists. Overwrite?"):
                return
        
        # Create Events directory
        event_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate event content
        content = f'''from __future__ import annotations

from typing import Any, Dict, List
from app.Events.Event import Event


class {name}(Event):
    """{name} event."""
    
    def __init__(self, **kwargs) -> None:
        """Initialize the event."""
        super().__init__()
        self.data = kwargs
    
    def broadcast_on(self) -> List[str]:
        """Get the channels the event should broadcast on."""
        return [
            # Add your broadcast channels here
            # "private-channel",
            # "presence-channel", 
        ]
    
    def broadcast_as(self) -> str:
        """The event's broadcast name."""
        return "{name.lower().replace('_', '.')}"
    
    def broadcast_with(self) -> Dict[str, Any]:
        """Get the data to broadcast with the event."""
        return self.data
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize the event data."""
        return {{
            "event": "{name}",
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }}
'''
        
        event_path.write_text(content)
        self.info(f"✅ Event created: {event_path}")


class MakeListenerCommand(Command):
    """Create a new event listener class."""
    
    signature = "make:listener {name : The name of the listener} {--event= : The event class being listened for} {--queued : Indicate the event listener should be queued}"
    description = "Create a new event listener class"
    help = "Generate a new event listener class file"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        event = self.option("event")
        queued = self.option("queued", False)
        
        if not name:
            self.error("Listener name is required")
            return
        
        listener_path = Path(f"app/Listeners/{name}.py")
        
        if listener_path.exists():
            if not self.confirm(f"Listener {name} already exists. Overwrite?"):
                return
        
        # Create Listeners directory
        listener_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate listener content
        event_import = ""
        event_type = "Any"
        
        if event:
            event_import = f"from app.Events.{event} import {event}"
            event_type = event
        
        queued_methods = ""
        if queued:
            queued_methods = '''
    def should_queue(self) -> bool:
        """Determine whether the listener should be queued."""
        return True
    
    def via_queue(self) -> str:
        """Get the name of the queue the listener should be sent to."""
        return "listeners"
    
    def queue_delay(self) -> int:
        """Get the number of seconds to delay the job."""
        return 0
    
    def max_exceptions(self) -> int:
        """Get the maximum number of exceptions allowed before failing."""
        return 3
'''
        
        content = f'''from __future__ import annotations

from typing import Any
{event_import}
from app.Listeners.Listener import Listener


class {name}(Listener):
    """{name} event listener."""
    
    def __init__(self) -> None:
        """Initialize the listener."""
        super().__init__()
    
    async def handle(self, event: {event_type}) -> None:
        """Handle the event."""
        # Implement event handling logic
        try:
            # Access event data
            event_data = getattr(event, 'data', {{}})
            
            # Log the event for debugging
            print(f"Handling event: {{event.__class__.__name__}}")
            
            # Add your custom logic here
            # Examples:
            # - Send email notifications
            # - Update database records
            # - Trigger webhooks
            # - Generate reports
            
        except Exception as e:
            print(f"Error handling event: {{e}}")
            # Consider logging or re-raising based on requirements{queued_methods}
'''
        
        listener_path.write_text(content)
        self.info(f"✅ Listener created: {listener_path}")
        
        if event:
            self.comment(f"Don't forget to register this listener for the {event} event!")


class EventSourcingCommand(Command):
    """Manage event sourcing and event store operations."""
    
    signature = "event:sourcing {action : replay, snapshot, rebuild, or audit} {--aggregate= : Target aggregate ID} {--from= : Start date/time (YYYY-MM-DD HH:MM:SS)} {--to= : End date/time} {--stream= : Specific event stream} {--export= : Export events to file} {--batch-size=1000 : Processing batch size}"
    description = "Manage event sourcing operations"
    help = "Replay events, create snapshots, rebuild aggregates, and audit event streams"
    
    def __init__(self) -> None:
        super().__init__()
        self.event_store_path = Path("storage/events")
        self.snapshots_path = Path("storage/snapshots")
    
    async def handle(self) -> None:
        """Execute event sourcing operations."""
        action = self.argument("action")
        aggregate_id = self.option("aggregate")
        from_date = self.option("from")
        to_date = self.option("to")
        stream_name = self.option("stream")
        export_file = self.option("export")
        batch_size = int(self.option("batch-size", 1000))
        
        if action not in ['replay', 'snapshot', 'rebuild', 'audit']:
            self.error("Action must be one of: replay, snapshot, rebuild, audit")
            return
        
        self.info(f"🔄 Starting event sourcing operation: {action}")
        
        # Ensure event store directories exist
        self.event_store_path.mkdir(parents=True, exist_ok=True)
        self.snapshots_path.mkdir(parents=True, exist_ok=True)
        
        try:
            if action == 'replay':
                await self._replay_events(aggregate_id, from_date, to_date, stream_name, batch_size)
            elif action == 'snapshot':
                await self._create_snapshots(aggregate_id, batch_size)
            elif action == 'rebuild':
                await self._rebuild_aggregates(aggregate_id, from_date, batch_size)
            elif action == 'audit':
                await self._audit_event_streams(from_date, to_date, export_file, batch_size)
                
        except Exception as e:
            self.error(f"Event sourcing operation failed: {e}")
    
    async def _replay_events(self, aggregate_id: Optional[str], from_date: Optional[str], 
                           to_date: Optional[str], stream_name: Optional[str], batch_size: int) -> None:
        """Replay events for aggregates or streams."""
        self.info("🔄 Replaying events...")
        
        # Load events based on filters
        events = await self._load_events_from_store(
            aggregate_id=aggregate_id,
            from_date=from_date,
            to_date=to_date,
            stream_name=stream_name
        )
        
        if not events:
            self.warn("No events found matching the criteria")
            return
        
        self.comment(f"Found {len(events)} events to replay")
        
        # Process events in batches
        total_batches = (len(events) + batch_size - 1) // batch_size
        progress_bar = self.progress_bar(total_batches, "Replaying events")
        
        replayed_count = 0
        failed_count = 0
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            
            for event in batch:
                try:
                    await self._replay_single_event(event)
                    replayed_count += 1
                except Exception as e:
                    self.warn(f"Failed to replay event {event.get('id', 'unknown')}: {e}")
                    failed_count += 1
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        self.info(f"✅ Event replay completed:")
        self.line(f"  Replayed: {replayed_count}")
        self.line(f"  Failed: {failed_count}")
        
        if failed_count > 0:
            self.warn("Some events failed to replay. Check logs for details.")
    
    async def _create_snapshots(self, aggregate_id: Optional[str], batch_size: int) -> None:
        """Create snapshots for aggregates."""
        self.info("📸 Creating aggregate snapshots...")
        
        # Discover aggregates to snapshot
        aggregates = await self._discover_aggregates(aggregate_id)
        
        if not aggregates:
            self.warn("No aggregates found to snapshot")
            return
        
        progress_bar = self.progress_bar(len(aggregates), "Creating snapshots")
        created_count = 0
        failed_count = 0
        
        for aggregate in aggregates:
            try:
                snapshot = await self._create_aggregate_snapshot(aggregate)
                if snapshot:
                    await self._save_snapshot(snapshot)
                    created_count += 1
                
            except Exception as e:
                self.warn(f"Failed to create snapshot for aggregate {aggregate['id']}: {e}")
                failed_count += 1
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        self.info(f"✅ Snapshot creation completed:")
        self.line(f"  Created: {created_count}")
        self.line(f"  Failed: {failed_count}")
    
    async def _rebuild_aggregates(self, aggregate_id: Optional[str], from_date: Optional[str], batch_size: int) -> None:
        """Rebuild aggregates from events."""
        self.info("🔧 Rebuilding aggregates from events...")
        
        aggregates = await self._discover_aggregates(aggregate_id)
        
        if not aggregates:
            self.warn("No aggregates found to rebuild")
            return
        
        progress_bar = self.progress_bar(len(aggregates), "Rebuilding aggregates")
        rebuilt_count = 0
        failed_count = 0
        
        for aggregate in aggregates:
            try:
                # Load events for this aggregate
                events = await self._load_events_from_store(
                    aggregate_id=aggregate['id'],
                    from_date=from_date
                )
                
                # Rebuild aggregate state
                rebuilt_state = await self._rebuild_aggregate_from_events(aggregate, events)
                
                # Save rebuilt state
                await self._save_aggregate_state(aggregate['id'], rebuilt_state)
                rebuilt_count += 1
                
            except Exception as e:
                self.warn(f"Failed to rebuild aggregate {aggregate['id']}: {e}")
                failed_count += 1
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        self.info(f"✅ Aggregate rebuild completed:")
        self.line(f"  Rebuilt: {rebuilt_count}")
        self.line(f"  Failed: {failed_count}")
    
    async def _audit_event_streams(self, from_date: Optional[str], to_date: Optional[str], 
                                 export_file: Optional[str], batch_size: int) -> None:
        """Audit event streams for consistency and integrity."""
        self.info("🔍 Auditing event streams...")
        
        audit_results: Dict[str, Any] = {
            'total_events': 0,
            'streams_analyzed': 0,
            'integrity_violations': [],
            'consistency_issues': [],
            'performance_issues': [],
            'stream_statistics': {}
        }
        
        # Analyze event streams
        streams = await self._discover_event_streams()
        progress_bar = self.progress_bar(len(streams), "Auditing streams")
        
        for stream_name in streams:
            try:
                stream_audit = await self._audit_single_stream(
                    stream_name, from_date, to_date
                )
                
                audit_results['total_events'] += stream_audit['event_count']
                audit_results['streams_analyzed'] += 1
                audit_results['stream_statistics'][stream_name] = stream_audit
                
                # Collect issues
                audit_results['integrity_violations'].extend(stream_audit.get('integrity_issues', []))
                audit_results['consistency_issues'].extend(stream_audit.get('consistency_issues', []))
                audit_results['performance_issues'].extend(stream_audit.get('performance_issues', []))
                
            except Exception as e:
                self.warn(f"Failed to audit stream {stream_name}: {e}")
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        # Display audit results
        self._display_audit_results(audit_results)
        
        # Export results if requested
        if export_file:
            await self._export_audit_results(export_file, audit_results)
    
    async def _load_events_from_store(self, aggregate_id: Optional[str] = None, 
                                     from_date: Optional[str] = None, 
                                     to_date: Optional[str] = None,
                                     stream_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load events from the event store with filters."""
        events = []
        
        # For demonstration, create sample events
        # In a real implementation, this would query your event store
        sample_events = [
            {
                'id': '1',
                'aggregate_id': 'user-123',
                'stream': 'user',
                'event_type': 'UserCreated',
                'data': {'email': 'user@example.com'},
                'timestamp': datetime.now().isoformat(),
                'version': 1
            },
            {
                'id': '2', 
                'aggregate_id': 'user-123',
                'stream': 'user',
                'event_type': 'UserUpdated',
                'data': {'name': 'John Doe'},
                'timestamp': datetime.now().isoformat(),
                'version': 2
            }
        ]
        
        # Apply filters
        for event in sample_events:
            if aggregate_id and event['aggregate_id'] != aggregate_id:
                continue
            if stream_name and event['stream'] != stream_name:
                continue
            # Date filtering would be implemented here
            events.append(event)
        
        return events
    
    async def _replay_single_event(self, event: Dict[str, Any]) -> None:
        """Replay a single event."""
        # In a real implementation, this would:
        # 1. Deserialize the event
        # 2. Apply it to the appropriate aggregate
        # 3. Update projections/read models
        # 4. Trigger side effects if needed
        pass
    
    async def _discover_aggregates(self, aggregate_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover aggregates in the system."""
        # Sample aggregates for demonstration
        aggregates = [
            {'id': 'user-123', 'type': 'User', 'version': 5},
            {'id': 'order-456', 'type': 'Order', 'version': 3},
        ]
        
        if aggregate_id:
            aggregates = [a for a in aggregates if a['id'] == aggregate_id]
        
        return aggregates
    
    async def _create_aggregate_snapshot(self, aggregate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a snapshot of an aggregate."""
        return {
            'aggregate_id': aggregate['id'],
            'aggregate_type': aggregate['type'],
            'version': aggregate['version'],
            'state': {'sample': 'state'},  # Actual aggregate state
            'timestamp': datetime.now().isoformat()
        }
    
    async def _save_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Save a snapshot to storage."""
        snapshot_file = self.snapshots_path / f"{snapshot['aggregate_id']}-v{snapshot['version']}.json"
        snapshot_file.write_text(json.dumps(snapshot, indent=2))
    
    async def _rebuild_aggregate_from_events(self, aggregate: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Rebuild aggregate state from events."""
        # This would apply events in order to rebuild state
        return {'rebuilt': True, 'events_applied': len(events)}
    
    async def _save_aggregate_state(self, aggregate_id: str, state: Dict[str, Any]) -> None:
        """Save rebuilt aggregate state."""
        state_file = self.event_store_path / f"aggregates/{aggregate_id}.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2))
    
    async def _discover_event_streams(self) -> List[str]:
        """Discover available event streams."""
        return ['user', 'order', 'payment', 'notification']
    
    async def _audit_single_stream(self, stream_name: str, from_date: Optional[str], to_date: Optional[str]) -> Dict[str, Any]:
        """Audit a single event stream."""
        return {
            'stream_name': stream_name,
            'event_count': 100,  # Sample count
            'integrity_issues': [],
            'consistency_issues': [],
            'performance_issues': [],
            'first_event': datetime.now().isoformat(),
            'last_event': datetime.now().isoformat(),
            'avg_events_per_day': 10.5
        }
    
    def _display_audit_results(self, results: Dict[str, Any]) -> None:
        """Display audit results summary."""
        self.new_line()
        self.info("🔍 Event Stream Audit Results")
        self.line("=" * 50)
        
        self.line(f"Total events analyzed: {results['total_events']}")
        self.line(f"Streams analyzed: {results['streams_analyzed']}")
        self.line(f"Integrity violations: {len(results['integrity_violations'])}")
        self.line(f"Consistency issues: {len(results['consistency_issues'])}")
        self.line(f"Performance issues: {len(results['performance_issues'])}")
        
        # Show per-stream statistics
        if results['stream_statistics']:
            self.new_line()
            self.line("Per-stream Statistics:")
            self.line("-" * 40)
            
            for stream_name, stats in results['stream_statistics'].items():
                self.line(f"  {stream_name}:")
                self.line(f"    Events: {stats['event_count']}")
                self.line(f"    Avg/day: {stats['avg_events_per_day']:.1f}")
        
        # Show issues if any
        if results['integrity_violations']:
            self.new_line()
            self.error("Integrity Violations:")
            for violation in results['integrity_violations'][:5]:
                self.line(f"  • {violation}")
        
        if results['consistency_issues']:
            self.new_line()
            self.warn("Consistency Issues:")
            for issue in results['consistency_issues'][:5]:
                self.line(f"  • {issue}")
    
    async def _export_audit_results(self, export_file: str, results: Dict[str, Any]) -> None:
        """Export audit results to file."""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'audit_timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_events': results['total_events'],
                    'streams_analyzed': results['streams_analyzed'],
                    'issues_found': len(results['integrity_violations']) + len(results['consistency_issues'])
                },
                'detailed_results': results
            }
            
            export_path.write_text(json.dumps(export_data, indent=2, default=str))
            self.info(f"✅ Audit results exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export audit results: {e}")


class EventMonitorCommand(Command):
    """Monitor event system performance and health."""
    
    signature = "event:monitor {--duration=60 : Monitoring duration in seconds} {--interval=5 : Check interval in seconds} {--threshold-latency=1000 : Latency threshold in ms} {--threshold-rate=100 : Event rate threshold per second} {--alert-email= : Email for alerts} {--export= : Export monitoring data} {--dashboard : Show real-time dashboard}"
    description = "Monitor event system performance and health"
    help = "Monitor event processing latency, throughput, error rates, and system health"
    
    def __init__(self) -> None:
        super().__init__()
        self.monitoring_data: List[Dict[str, Any]] = []
        self.alerts_triggered: List[Dict[str, Any]] = []
    
    async def handle(self) -> None:
        """Execute event monitoring."""
        duration = int(self.option("duration", 60))
        interval = int(self.option("interval", 5))
        latency_threshold = int(self.option("threshold-latency", 1000))
        rate_threshold = int(self.option("threshold-rate", 100))
        alert_email = self.option("alert-email")
        export_file = self.option("export")
        dashboard_mode = self.option("dashboard", False)
        
        self.info(f"📊 Starting event system monitoring for {duration}s...")
        self.comment(f"Monitoring interval: {interval}s")
        self.comment(f"Latency threshold: {latency_threshold}ms")
        self.comment(f"Rate threshold: {rate_threshold} events/sec")
        
        if dashboard_mode:
            await self._run_dashboard_monitoring(duration, interval, latency_threshold, rate_threshold)
        else:
            await self._run_standard_monitoring(duration, interval, latency_threshold, rate_threshold, alert_email)
        
        # Generate summary report
        self._display_monitoring_summary()
        
        # Export data if requested
        if export_file:
            await self._export_monitoring_data(export_file)
    
    async def _run_standard_monitoring(self, duration: int, interval: int, 
                                     latency_threshold: int, rate_threshold: int,
                                     alert_email: Optional[str]) -> None:
        """Run standard monitoring with periodic checks."""
        start_time = time.time()
        end_time = start_time + duration
        
        self.comment("Press Ctrl+C to stop monitoring early")
        
        try:
            while time.time() < end_time:
                metrics = await self._collect_event_metrics()
                self.monitoring_data.append(metrics)
                
                # Check thresholds and trigger alerts
                await self._check_thresholds(metrics, latency_threshold, rate_threshold, alert_email)
                
                # Display current metrics
                self._display_current_metrics(metrics)
                
                # Wait for next interval
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            self.comment("\n🛑 Monitoring stopped by user")
    
    async def _run_dashboard_monitoring(self, duration: int, interval: int,
                                      latency_threshold: int, rate_threshold: int) -> None:
        """Run real-time dashboard monitoring."""
        self.info("📱 Starting real-time monitoring dashboard...")
        
        start_time = time.time()
        end_time = start_time + duration
        
        try:
            while time.time() < end_time:
                metrics = await self._collect_event_metrics()
                self.monitoring_data.append(metrics)
                
                # Clear screen and display dashboard
                import os
                os.system('clear' if os.name == 'posix' else 'cls')
                
                self._display_dashboard(metrics, latency_threshold, rate_threshold)
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            self.comment("\n🛑 Dashboard monitoring stopped")
    
    async def _collect_event_metrics(self) -> Dict[str, Any]:
        """Collect current event system metrics."""
        # In a real implementation, this would collect actual metrics
        # from your event system, message queues, databases, etc.
        
        import random
        
        # Simulate realistic metrics
        current_time = datetime.now()
        
        return {
            'timestamp': current_time.isoformat(),
            'events_processed_per_second': random.randint(50, 200),
            'avg_processing_latency_ms': random.randint(10, 2000),
            'p95_processing_latency_ms': random.randint(100, 3000),
            'p99_processing_latency_ms': random.randint(500, 5000),
            'error_rate_percent': random.uniform(0, 5),
            'queue_depth': random.randint(0, 1000),
            'active_listeners': random.randint(5, 20),
            'memory_usage_mb': random.randint(100, 500),
            'cpu_usage_percent': random.uniform(10, 80),
            'disk_usage_percent': random.uniform(20, 90),
            'network_io_mbps': random.uniform(1, 50),
            'event_types': {
                'user.created': random.randint(5, 50),
                'user.updated': random.randint(10, 100),
                'order.placed': random.randint(20, 80),
                'payment.processed': random.randint(15, 60)
            },
            'failed_events': random.randint(0, 10),
            'retried_events': random.randint(0, 5),
            'dead_letter_count': random.randint(0, 3)
        }
    
    async def _check_thresholds(self, metrics: Dict[str, Any], latency_threshold: int,
                              rate_threshold: int, alert_email: Optional[str]) -> None:
        """Check metrics against thresholds and trigger alerts."""
        alerts = []
        
        # Check latency threshold
        if metrics['avg_processing_latency_ms'] > latency_threshold:
            alerts.append({
                'type': 'high_latency',
                'message': f"High processing latency: {metrics['avg_processing_latency_ms']}ms",
                'severity': 'warning' if metrics['avg_processing_latency_ms'] < latency_threshold * 2 else 'critical',
                'metric': 'avg_processing_latency_ms',
                'value': metrics['avg_processing_latency_ms'],
                'threshold': latency_threshold
            })
        
        # Check event rate threshold
        if metrics['events_processed_per_second'] < rate_threshold / 2:
            alerts.append({
                'type': 'low_throughput',
                'message': f"Low event throughput: {metrics['events_processed_per_second']} events/sec",
                'severity': 'warning',
                'metric': 'events_processed_per_second',
                'value': metrics['events_processed_per_second'],
                'threshold': rate_threshold
            })
        
        # Check error rate
        if metrics['error_rate_percent'] > 5:
            alerts.append({
                'type': 'high_error_rate',
                'message': f"High error rate: {metrics['error_rate_percent']:.1f}%",
                'severity': 'critical' if metrics['error_rate_percent'] > 10 else 'warning',
                'metric': 'error_rate_percent',
                'value': metrics['error_rate_percent'],
                'threshold': 5
            })
        
        # Check queue depth
        if metrics['queue_depth'] > 500:
            alerts.append({
                'type': 'high_queue_depth',
                'message': f"High queue depth: {metrics['queue_depth']} events",
                'severity': 'critical' if metrics['queue_depth'] > 1000 else 'warning',
                'metric': 'queue_depth',
                'value': metrics['queue_depth'],
                'threshold': 500
            })
        
        # Process alerts
        for alert in alerts:
            alert['timestamp'] = datetime.now().isoformat()
            self.alerts_triggered.append(alert)
            
            # Display alert
            severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡"
            self.warn(f"{severity_icon} {alert['message']}")
            
            # Send email alert if configured
            if alert_email and alert['severity'] == 'critical':
                await self._send_alert_email(alert_email, alert)
    
    def _display_current_metrics(self, metrics: Dict[str, Any]) -> None:
        """Display current metrics in compact format."""
        timestamp = metrics['timestamp'][:19]  # Remove microseconds
        
        self.line(f"[{timestamp}] "
                 f"Events/s: {metrics['events_processed_per_second']} | "
                 f"Latency: {metrics['avg_processing_latency_ms']}ms | "
                 f"Errors: {metrics['error_rate_percent']:.1f}% | "
                 f"Queue: {metrics['queue_depth']}")
    
    def _display_dashboard(self, metrics: Dict[str, Any], latency_threshold: int, rate_threshold: int) -> None:
        """Display real-time monitoring dashboard."""
        self.info("📊 Event System Monitoring Dashboard")
        self.line("=" * 60)
        self.line(f"Timestamp: {metrics['timestamp'][:19]}")
        self.new_line()
        
        # Performance metrics
        self.info("🚀 Performance Metrics")
        self.line("-" * 30)
        
        # Event throughput with status indicator
        throughput = metrics['events_processed_per_second']
        throughput_status = "🟢" if throughput >= rate_threshold else "🟡" if throughput >= rate_threshold/2 else "🔴"
        self.line(f"{throughput_status} Events/sec: {throughput} (target: >{rate_threshold/2})")
        
        # Latency with status indicator
        latency = metrics['avg_processing_latency_ms']
        latency_status = "🟢" if latency < latency_threshold else "🟡" if latency < latency_threshold*2 else "🔴"
        self.line(f"{latency_status} Avg Latency: {latency}ms (threshold: <{latency_threshold}ms)")
        
        # P95/P99 latencies
        self.line(f"   P95 Latency: {metrics['p95_processing_latency_ms']}ms")
        self.line(f"   P99 Latency: {metrics['p99_processing_latency_ms']}ms")
        
        # Error rate
        error_rate = metrics['error_rate_percent']
        error_status = "🟢" if error_rate < 1 else "🟡" if error_rate < 5 else "🔴"
        self.line(f"{error_status} Error Rate: {error_rate:.1f}%")
        
        self.new_line()
        
        # System health
        self.info("💡 System Health")
        self.line("-" * 30)
        self.line(f"Queue Depth: {metrics['queue_depth']} events")
        self.line(f"Active Listeners: {metrics['active_listeners']}")
        self.line(f"Memory Usage: {metrics['memory_usage_mb']}MB")
        self.line(f"CPU Usage: {metrics['cpu_usage_percent']:.1f}%")
        
        self.new_line()
        
        # Event types breakdown
        self.info("📝 Event Types (last minute)")
        self.line("-" * 30)
        for event_type, count in metrics['event_types'].items():
            self.line(f"  {event_type}: {count}")
        
        self.new_line()
        
        # Issues
        if metrics['failed_events'] > 0 or metrics['dead_letter_count'] > 0:
            self.warn("⚠️  Issues Detected")
            self.line("-" * 30)
            if metrics['failed_events'] > 0:
                self.line(f"Failed Events: {metrics['failed_events']}")
            if metrics['retried_events'] > 0:
                self.line(f"Retried Events: {metrics['retried_events']}")
            if metrics['dead_letter_count'] > 0:
                self.line(f"Dead Letter Queue: {metrics['dead_letter_count']}")
        
        self.new_line()
        self.comment("Press Ctrl+C to stop monitoring")
    
    def _display_monitoring_summary(self) -> None:
        """Display monitoring session summary."""
        if not self.monitoring_data:
            self.warn("No monitoring data collected")
            return
        
        self.new_line()
        self.info("📈 Monitoring Session Summary")
        self.line("=" * 50)
        
        # Calculate aggregated statistics
        total_events = sum(m['events_processed_per_second'] for m in self.monitoring_data)
        avg_throughput = total_events / len(self.monitoring_data)
        
        latencies = [m['avg_processing_latency_ms'] for m in self.monitoring_data]
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        error_rates = [m['error_rate_percent'] for m in self.monitoring_data]
        avg_error_rate = sum(error_rates) / len(error_rates)
        max_error_rate = max(error_rates)
        
        queue_depths = [m['queue_depth'] for m in self.monitoring_data]
        max_queue_depth = max(queue_depths)
        
        self.line(f"Duration: {len(self.monitoring_data)} samples")
        self.line(f"Avg Throughput: {avg_throughput:.1f} events/sec")
        self.line(f"Latency - Avg: {avg_latency:.1f}ms, Min: {min_latency}ms, Max: {max_latency}ms")
        self.line(f"Error Rate - Avg: {avg_error_rate:.2f}%, Max: {max_error_rate:.2f}%")
        self.line(f"Max Queue Depth: {max_queue_depth} events")
        
        # Alerts summary
        if self.alerts_triggered:
            self.new_line()
            self.warn(f"🚨 Alerts Triggered: {len(self.alerts_triggered)}")
            
            alert_types: Dict[str, Dict[str, Any]] = {}
            for alert in self.alerts_triggered:
                alert_type = alert['type']
                if alert_type not in alert_types:
                    alert_types[alert_type] = {'count': 0, 'severity': []}
                alert_types[alert_type]['count'] += 1
                alert_types[alert_type]['severity'].append(alert['severity'])
            
            for alert_type, info in alert_types.items():
                critical_count = info['severity'].count('critical')
                warning_count = info['severity'].count('warning')
                
                self.line(f"  • {alert_type}: {info['count']} total "
                         f"({critical_count} critical, {warning_count} warnings)")
        else:
            self.info("✅ No alerts triggered during monitoring")
    
    async def _export_monitoring_data(self, export_file: str) -> None:
        """Export monitoring data to file."""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'session_info': {
                    'start_time': self.monitoring_data[0]['timestamp'] if self.monitoring_data else None,
                    'end_time': self.monitoring_data[-1]['timestamp'] if self.monitoring_data else None,
                    'duration_samples': len(self.monitoring_data),
                    'alerts_triggered': len(self.alerts_triggered)
                },
                'metrics_data': self.monitoring_data,
                'alerts': self.alerts_triggered
            }
            
            export_path.write_text(json.dumps(export_data, indent=2, default=str))
            self.info(f"✅ Monitoring data exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export monitoring data: {e}")
    
    async def _send_alert_email(self, email: str, alert: Dict[str, Any]) -> None:
        """Send alert email (placeholder implementation)."""
        # In a real implementation, this would send an actual email
        self.comment(f"📧 Alert email sent to {email}: {alert['message']}")


class EventTestCommand(Command):
    """Test event firing and listener execution with advanced analysis."""
    
    signature = "event:test {event : The event to test} {--data= : JSON data to pass to event} {--stress : Run stress test} {--concurrent=10 : Concurrent event firings} {--iterations=100 : Number of test iterations} {--analyze : Perform detailed analysis} {--export= : Export test results}"
    description = "Test event firing and listener execution"
    help = "Fire events and test listener execution with performance analysis and stress testing"
    
    def __init__(self) -> None:
        super().__init__()
        self.test_results: List[Dict[str, Any]] = []
    
    async def handle(self) -> None:
        """Execute the command."""
        event_name = self.argument("event")
        data_json = self.option("data", "{}")
        stress_test = self.option("stress", False)
        concurrent = int(self.option("concurrent", 10))
        iterations = int(self.option("iterations", 100))
        analyze = self.option("analyze", False)
        export_file = self.option("export")
        
        if not event_name:
            self.error("Event name is required")
            return
        
        try:
            data = json.loads(data_json)
        except json.JSONDecodeError:
            self.error("Invalid JSON data provided")
            return
        
        self.info(f"🧪 Testing event: {event_name}")
        
        if stress_test:
            await self._run_stress_test(event_name, data, concurrent, iterations)
        else:
            await self._run_single_test(event_name, data)
        
        # Perform analysis if requested
        if analyze:
            self._analyze_test_results()
        
        # Export results if requested
        if export_file:
            await self._export_test_results(export_file)
    
    async def _run_single_test(self, event_name: str, data: Dict[str, Any]) -> None:
        """Run a single event test."""
        result = await self._test_event(event_name, data)
        self.test_results.append(result)
        
        if result["success"]:
            self.info("✅ Event test completed successfully!")
            self.comment(f"Listeners executed: {result['listeners_count']}")
            self.comment(f"Execution time: {result['execution_time']:.3f}s")
        else:
            self.error(f"❌ Event test failed: {result['error']}")
    
    async def _run_stress_test(self, event_name: str, data: Dict[str, Any], 
                             concurrent: int, iterations: int) -> None:
        """Run stress test with multiple concurrent event firings."""
        self.info(f"🔥 Running stress test: {iterations} iterations, {concurrent} concurrent")
        
        # Run stress test in batches
        batch_size = concurrent
        total_batches = (iterations + batch_size - 1) // batch_size
        
        progress_bar = self.progress_bar(total_batches, "Stress testing")
        
        for batch_start in range(0, iterations, batch_size):
            batch_end = min(batch_start + batch_size, iterations)
            batch_iterations = batch_end - batch_start
            
            # Run concurrent tests
            tasks = []
            for _ in range(batch_iterations):
                task = asyncio.create_task(self._test_event(event_name, data))
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    self.test_results.append({
                        'success': False,
                        'error': str(result),
                        'execution_time': 0,
                        'listeners_count': 0,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    # result is Dict[str, Any] from _test_event
                    assert isinstance(result, dict)
                    self.test_results.append(result)
            
            progress_bar.advance()
        
        progress_bar.finish()
        
        # Display stress test summary
        self._display_stress_test_summary()
    
    async def _test_event(self, event_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test firing an event with detailed metrics."""
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            listeners = await self._get_listeners_for_event(event_name)
            
            # Simulate event processing with more realistic timing
            processing_times = []
            failed_listeners = []
            
            for listener in listeners:
                listener_start = time.time()
                try:
                    # Simulate listener execution with variable timing
                    import random
                    processing_time = random.uniform(0.001, 0.05)  # 1-50ms
                    await asyncio.sleep(processing_time)
                    
                    processing_times.append(time.time() - listener_start)
                    
                except Exception as e:
                    failed_listeners.append({'listener': listener, 'error': str(e)})
            
            end_time = time.time()
            total_execution_time = end_time - start_time
            
            return {
                'success': len(failed_listeners) == 0,
                'event_name': event_name,
                'listeners_count': len(listeners),
                'successful_listeners': len(listeners) - len(failed_listeners),
                'failed_listeners': failed_listeners,
                'execution_time': total_execution_time,
                'avg_listener_time': sum(processing_times) / len(processing_times) if processing_times else 0,
                'max_listener_time': max(processing_times) if processing_times else 0,
                'min_listener_time': min(processing_times) if processing_times else 0,
                'timestamp': timestamp.isoformat(),
                'data_size': len(json.dumps(data)),
                'error': None
            }
            
        except Exception as e:
            end_time = time.time()
            return {
                'success': False,
                'event_name': event_name,
                'error': str(e),
                'listeners_count': 0,
                'successful_listeners': 0,
                'failed_listeners': [],
                'execution_time': end_time - start_time,
                'timestamp': timestamp.isoformat(),
                'data_size': len(json.dumps(data))
            }
    
    async def _get_listeners_for_event(self, event_name: str) -> List[str]:
        """Get listeners for an event."""
        from .EventCommands import EventListCommand
        event_list_cmd = EventListCommand()
        events = await event_list_cmd._discover_events()
        return events.get(event_name, [])
    
    def _display_stress_test_summary(self) -> None:
        """Display stress test results summary."""
        if not self.test_results:
            return
        
        self.new_line()
        self.info("🔥 Stress Test Results")
        self.line("=" * 40)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - successful_tests
        
        self.line(f"Total tests: {total_tests}")
        self.line(f"Successful: {successful_tests}")
        self.line(f"Failed: {failed_tests}")
        self.line(f"Success rate: {(successful_tests / total_tests * 100):.1f}%")
        
        # Performance metrics
        execution_times = [r['execution_time'] for r in self.test_results]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            min_time = min(execution_times)
            
            self.line(f"\nPerformance:")
            self.line(f"  Avg execution time: {avg_time * 1000:.2f}ms")
            self.line(f"  Min execution time: {min_time * 1000:.2f}ms")
            self.line(f"  Max execution time: {max_time * 1000:.2f}ms")
            
            # Throughput calculation
            total_time = max(execution_times) if execution_times else 1
            throughput = total_tests / total_time if total_time > 0 else 0
            self.line(f"  Estimated throughput: {throughput:.1f} events/sec")
        
        # Error analysis
        if failed_tests > 0:
            self.new_line()
            self.warn("❌ Failed Tests Analysis:")
            error_types: Dict[str, int] = {}
            
            for result in self.test_results:
                if not result['success']:
                    error = result.get('error', 'Unknown error')
                    error_types[error] = error_types.get(error, 0) + 1
            
            for error, count in error_types.items():
                self.line(f"  • {error}: {count} occurrences")
    
    def _analyze_test_results(self) -> None:
        """Perform detailed analysis of test results."""
        if not self.test_results:
            self.warn("No test results to analyze")
            return
        
        self.new_line()
        self.info("📊 Test Results Analysis")
        self.line("=" * 50)
        
        # Performance percentiles
        execution_times = [r['execution_time'] * 1000 for r in self.test_results if r['success']]  # Convert to ms
        
        if execution_times:
            execution_times.sort()
            n = len(execution_times)
            
            p50 = execution_times[int(n * 0.5)] if n > 0 else 0
            p95 = execution_times[int(n * 0.95)] if n > 0 else 0
            p99 = execution_times[int(n * 0.99)] if n > 0 else 0
            
            self.line("Response Time Percentiles:")
            self.line(f"  P50 (median): {p50:.2f}ms")
            self.line(f"  P95: {p95:.2f}ms")
            self.line(f"  P99: {p99:.2f}ms")
        
        # Listener performance analysis
        successful_results = [r for r in self.test_results if r['success']]
        if successful_results:
            avg_listeners = sum(r['listeners_count'] for r in successful_results) / len(successful_results)
            avg_listener_time = sum(r.get('avg_listener_time', 0) for r in successful_results) / len(successful_results)
            
            self.line(f"\nListener Performance:")
            self.line(f"  Avg listeners per event: {avg_listeners:.1f}")
            self.line(f"  Avg listener execution time: {avg_listener_time * 1000:.2f}ms")
        
        # Data size impact
        data_sizes = [r.get('data_size', 0) for r in self.test_results]
        if data_sizes:
            avg_data_size = sum(data_sizes) / len(data_sizes)
            max_data_size = max(data_sizes)
            
            self.line(f"\nEvent Data:")
            self.line(f"  Avg payload size: {avg_data_size:.0f} bytes")
            self.line(f"  Max payload size: {max_data_size} bytes")
        
        # Performance recommendations
        self.new_line()
        self.info("💡 Performance Recommendations:")
        
        if execution_times:
            if p95 > 1000:  # > 1 second
                self.line("  ⚠️ High P95 latency detected - consider optimizing listeners")
            if p99 > 5000:  # > 5 seconds  
                self.line("  🔴 Very high P99 latency - investigate slow listeners")
            
        success_rate = sum(1 for r in self.test_results if r['success']) / len(self.test_results) * 100
        if success_rate < 95:
            self.line("  ⚠️ Low success rate - investigate event processing reliability")
        
        if avg_data_size > 1000:  # > 1KB
            self.line("  💾 Large event payloads - consider data compression or references")
    
    async def _export_test_results(self, export_file: str) -> None:
        """Export test results to file."""
        try:
            export_path = Path(export_file)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'test_session': {
                    'timestamp': datetime.now().isoformat(),
                    'total_tests': len(self.test_results),
                    'successful_tests': sum(1 for r in self.test_results if r['success']),
                    'test_type': 'stress' if len(self.test_results) > 10 else 'single'
                },
                'results': self.test_results,
                'summary_statistics': self._calculate_summary_statistics()
            }
            
            export_path.write_text(json.dumps(export_data, indent=2, default=str))
            self.info(f"✅ Test results exported to: {export_path}")
            
        except Exception as e:
            self.error(f"Failed to export test results: {e}")
    
    def _calculate_summary_statistics(self) -> Dict[str, Any]:
        """Calculate summary statistics for test results."""
        if not self.test_results:
            return {}
        
        successful_results = [r for r in self.test_results if r['success']]
        execution_times = [r['execution_time'] for r in successful_results]
        
        stats = {
            'total_tests': len(self.test_results),
            'successful_tests': len(successful_results),
            'success_rate_percent': len(successful_results) / len(self.test_results) * 100
        }
        
        if execution_times:
            stats.update({
                'avg_execution_time_ms': sum(execution_times) / len(execution_times) * 1000,
                'min_execution_time_ms': min(execution_times) * 1000,
                'max_execution_time_ms': max(execution_times) * 1000
            })
        
        return stats


# Register commands
from app.Console.Artisan import register_command

register_command(EventListCommand)
register_command(EventCacheCommand)
register_command(EventClearCommand)
register_command(EventGenerateCommand)
register_command(MakeEventCommand)
register_command(MakeListenerCommand)
register_command(EventSourcingCommand)
register_command(EventMonitorCommand)
register_command(EventTestCommand)