"""
Blade Template Hot Reloading System
Provides real-time template reloading for development environments
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Dict, Set, Callable, Optional, Any, List
from datetime import datetime
from watchdog.observers import Observer  # type: ignore[import-not-found]
from watchdog.events import FileSystemEventHandler, FileSystemEvent  # type: ignore[import-not-found]
import asyncio
import websockets
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
import weakref


class TemplateChangeEvent:
    """Represents a template change event"""
    
    def __init__(self, event_type: str, template_path: str, timestamp: Optional[datetime] = None):
        self.event_type = event_type  # 'created', 'modified', 'deleted', 'moved'
        self.template_path = template_path
        self.timestamp = timestamp or datetime.now()
        self.template_name = self._extract_template_name(template_path)
    
    def _extract_template_name(self, path: str) -> str:
        """Extract template name from file path"""
        path_obj = Path(path)
        if path_obj.suffix == '.html' and path_obj.stem.endswith('.blade'):
            return path_obj.stem[:-6]  # Remove .blade
        return path_obj.stem
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_type': self.event_type,
            'template_path': self.template_path,
            'template_name': self.template_name,
            'timestamp': self.timestamp.isoformat()
        }


class BladeFileWatcher(FileSystemEventHandler):  # type: ignore[misc,no-any-unimported]
    """Watches Blade template files for changes"""
    
    def __init__(self, hot_reload_manager: 'BladeHotReloadManager'):
        super().__init__()
        self.hot_reload_manager = hot_reload_manager
        self.debounce_delay = 0.1  # 100ms debounce
        self.pending_events: Dict[str, float] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    def on_any_event(self, event: FileSystemEvent) -> None:  # type: ignore[no-any-unimported]
        """Handle any file system event"""
        if event.is_directory:
            return
        
        # Only handle Blade template files
        if not self._is_blade_template(event.src_path):
            return
        
        # Debounce rapid events
        current_time = time.time()
        if event.src_path in self.pending_events:
            if current_time - self.pending_events[event.src_path] < self.debounce_delay:
                return
        
        self.pending_events[event.src_path] = current_time
        
        # Process event asynchronously
        self._executor.submit(self._process_event, event)
    
    def _is_blade_template(self, file_path: str) -> bool:
        """Check if file is a Blade template"""
        path = Path(file_path)
        return path.suffix == '.html' and '.blade.' in path.name
    
    def _process_event(self, event: FileSystemEvent) -> None:  # type: ignore[no-any-unimported]
        """Process a file system event"""
        try:
            # Small delay to ensure file is fully written
            time.sleep(self.debounce_delay)
            
            event_type_map = {
                'created': 'created',
                'modified': 'modified',
                'deleted': 'deleted',
                'moved': 'moved'
            }
            
            event_type = event_type_map.get(event.event_type, 'modified')
            template_event = TemplateChangeEvent(event_type, event.src_path)
            
            self.hot_reload_manager.handle_template_change(template_event)
            
        except Exception as e:
            print(f"Error processing template change event: {e}")
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        self._executor.shutdown(wait=True)


class WebSocketBroadcaster:
    """Manages WebSocket connections for hot reload notifications"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Set[Any] = set()
        self.server = None
        self.is_running = False
        self._lock = threading.Lock()
    
    async def register_client(self, websocket: Any) -> None:
        """Register a new WebSocket client"""
        with self._lock:
            self.clients.add(websocket)
        
        try:
            await websocket.send(json.dumps({
                'type': 'connected',
                'message': 'Hot reload connected'
            }))
            
            # Keep connection alive
            async for message in websocket:
                # Echo heartbeat messages
                if message == 'ping':
                    await websocket.send('pong')
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            with self._lock:
                self.clients.discard(websocket)
    
    async def broadcast_change(self, change_event: TemplateChangeEvent) -> None:
        """Broadcast template change to all connected clients"""
        if not self.clients:
            return
        
        message = json.dumps({
            'type': 'template_changed',
            'data': change_event.to_dict()
        })
        
        # Create a copy of clients to avoid modification during iteration
        with self._lock:
            clients_copy = self.clients.copy()
        
        # Send to all connected clients
        disconnected = set()
        for client in clients_copy:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Remove disconnected clients
        if disconnected:
            with self._lock:
                self.clients -= disconnected
    
    def start_server(self) -> None:
        """Start WebSocket server"""
        if self.is_running:
            return
        
        def run_server() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def handle_client(websocket: Any, path: Any) -> None:
                await self.register_client(websocket)
            
            self.server = websockets.serve(handle_client, "localhost", self.port)  # type: ignore[arg-type,assignment]
            if self.server:
                loop.run_until_complete(self.server)
            loop.run_forever()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        self.is_running = True
    
    def stop_server(self) -> None:
        """Stop WebSocket server"""
        self.is_running = False
        if self.server:
            self.server.close()  # type: ignore[unreachable]
    
    def get_client_count(self) -> int:
        """Get number of connected clients"""
        with self._lock:
            return len(self.clients)


class TemplateCompilationQueue:
    """Queue for managing template recompilation"""
    
    def __init__(self, max_workers: int = 4):
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        self.max_workers = max_workers
        self.workers: List[Any] = []
        self.is_running = False
        self.compilation_cache: Dict[str, str] = {}
        self._lock = threading.Lock()
    
    async def add_compilation_task(self, template_path: str, 
                                 compile_func: Callable[[str], str]) -> None:
        """Add a template compilation task to the queue"""
        await self.queue.put((template_path, compile_func))
    
    async def start_workers(self) -> None:
        """Start compilation worker tasks"""
        if self.is_running:
            return
        
        self.is_running = True
        
        async def worker() -> None:
            while self.is_running:
                try:
                    template_path, compile_func = await asyncio.wait_for(
                        self.queue.get(), timeout=1.0
                    )
                    
                    await self._compile_template(template_path, compile_func)
                    self.queue.task_done()
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Compilation worker error: {e}")
        
        self.workers = [asyncio.create_task(worker()) for _ in range(self.max_workers)]
    
    async def _compile_template(self, template_path: str, 
                              compile_func: Callable[[str], str]) -> None:
        """Compile a template"""
        try:
            # Read template content
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Compile template
            compiled = compile_func(content)
            
            # Cache compiled template
            with self._lock:
                self.compilation_cache[template_path] = compiled
                
        except Exception as e:
            print(f"Failed to compile template {template_path}: {e}")
    
    def stop_workers(self) -> None:
        """Stop compilation workers"""
        self.is_running = False
        for worker in self.workers:
            worker.cancel()
        self.workers.clear()
    
    def get_compiled_template(self, template_path: str) -> Optional[str]:
        """Get compiled template from cache"""
        with self._lock:
            return self.compilation_cache.get(template_path)


class HotReloadConfig:
    """Configuration for hot reloading"""
    
    def __init__(self) -> None:
        self.enabled = True
        self.watch_patterns = ['*.blade.html']
        self.ignore_patterns = ['.git/*', 'node_modules/*', '*.tmp']
        self.websocket_port = 8765
        self.debounce_delay = 0.1
        self.enable_browser_refresh = True
        self.enable_css_injection = True
        self.enable_js_reload = True
        self.compilation_timeout = 5.0
        self.max_compilation_workers = 4


class BladeHotReloadManager:
    """Main hot reload management system"""
    
    def __init__(self, blade_engine: Any, template_paths: List[str], 
                 config: Optional[HotReloadConfig] = None):
        self.blade_engine = blade_engine
        self.template_paths = template_paths
        self.config = config or HotReloadConfig()
        
        # Components
        self.file_watcher: Optional[BladeFileWatcher] = None
        self.websocket_broadcaster: Optional[WebSocketBroadcaster] = None
        self.compilation_queue: Optional[TemplateCompilationQueue] = None
        self.observer: Optional[Any] = None
        
        # State
        self.is_active = False
        self.change_callbacks: List[Callable[[TemplateChangeEvent], None]] = []
        self.template_checksums: Dict[str, str] = {}
        
        # Statistics
        self.stats = {
            'changes_detected': 0,
            'compilations_triggered': 0,
            'clients_notified': 0,
            'errors': 0
        }
        
        # Initialize if enabled
        if self.config.enabled:
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize hot reload system"""
        # Initialize components
        self.file_watcher = BladeFileWatcher(self)
        self.websocket_broadcaster = WebSocketBroadcaster(self.config.websocket_port)
        self.compilation_queue = TemplateCompilationQueue(self.config.max_compilation_workers)
        
        # Calculate initial checksums
        self._calculate_initial_checksums()
    
    def start(self) -> None:
        """Start hot reload monitoring"""
        if not self.config.enabled or self.is_active:
            return
        
        try:
            # Start WebSocket server
            if self.websocket_broadcaster:
                self.websocket_broadcaster.start_server()
            
            # Start compilation queue
            if self.compilation_queue:
                asyncio.create_task(self.compilation_queue.start_workers())
            
            # Start file watcher
            self.observer = Observer()
            
            for template_path in self.template_paths:
                if os.path.exists(template_path):
                    self.observer.schedule(
                        self.file_watcher,
                        template_path,
                        recursive=True
                    )
            
            self.observer.start()
            self.is_active = True
            
            print(f"Blade hot reload started. WebSocket server on port {self.config.websocket_port}")
            
        except Exception as e:
            print(f"Failed to start hot reload: {e}")
            self.stats['errors'] += 1
    
    def stop(self) -> None:
        """Stop hot reload monitoring"""
        if not self.is_active:
            return
        
        # Stop file observer
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        # Stop WebSocket server
        if self.websocket_broadcaster:
            self.websocket_broadcaster.stop_server()
        
        # Stop compilation queue
        if self.compilation_queue:
            self.compilation_queue.stop_workers()
        
        # Cleanup file watcher
        if self.file_watcher:
            self.file_watcher.cleanup()
        
        self.is_active = False
        print("Blade hot reload stopped")
    
    def handle_template_change(self, change_event: TemplateChangeEvent) -> None:
        """Handle template change event"""
        try:
            self.stats['changes_detected'] += 1
            
            # Check if template actually changed
            if not self._has_template_changed(change_event.template_path):
                return
            
            # Clear template cache
            if hasattr(self.blade_engine, 'clear_cache'):
                self.blade_engine.clear_cache()
            
            # Trigger recompilation
            if self.compilation_queue:
                asyncio.create_task(
                    self.compilation_queue.add_compilation_task(
                        change_event.template_path,
                        self.blade_engine.compile_blade
                    )
                )
                self.stats['compilations_triggered'] += 1
            
            # Notify WebSocket clients
            if self.websocket_broadcaster:
                asyncio.create_task(
                    self.websocket_broadcaster.broadcast_change(change_event)
                )
                self.stats['clients_notified'] += 1
            
            # Call registered callbacks
            for callback in self.change_callbacks:
                try:
                    callback(change_event)
                except Exception as e:
                    print(f"Error in change callback: {e}")
            
        except Exception as e:
            print(f"Error handling template change: {e}")
            self.stats['errors'] += 1
    
    def add_change_callback(self, callback: Callable[[TemplateChangeEvent], None]) -> None:
        """Add callback for template change events"""
        self.change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[TemplateChangeEvent], None]) -> None:
        """Remove callback for template change events"""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
    
    def force_reload(self, template_name: Optional[str] = None) -> None:
        """Force reload of template(s)"""
        if template_name:
            # Reload specific template
            template_paths = self._find_template_paths(template_name)
            for path in template_paths:
                change_event = TemplateChangeEvent('modified', path)
                self.handle_template_change(change_event)
        else:
            # Reload all templates
            for template_path in self._get_all_template_paths():
                change_event = TemplateChangeEvent('modified', template_path)
                self.handle_template_change(change_event)
    
    def get_client_script(self) -> str:
        """Get JavaScript client script for hot reload"""
        return f"""
<script>
(function() {{
    if (!window.bladeHotReload) {{
        window.bladeHotReload = {{
            socket: null,
            reconnectDelay: 1000,
            maxReconnectDelay: 30000,
            reconnectAttempts: 0,
            
            connect: function() {{
                try {{
                    this.socket = new WebSocket('ws://localhost:{self.config.websocket_port}');
                    
                    this.socket.onopen = function() {{
                        console.log('Blade hot reload connected');
                        window.bladeHotReload.reconnectAttempts = 0;
                        window.bladeHotReload.reconnectDelay = 1000;
                    }};
                    
                    this.socket.onmessage = function(event) {{
                        var data = JSON.parse(event.data);
                        window.bladeHotReload.handleMessage(data);
                    }};
                    
                    this.socket.onclose = function() {{
                        console.log('Blade hot reload disconnected');
                        window.bladeHotReload.scheduleReconnect();
                    }};
                    
                    this.socket.onerror = function(error) {{
                        console.log('Blade hot reload error:', error);
                    }};
                }} catch (e) {{
                    console.log('Failed to connect to hot reload server:', e);
                    this.scheduleReconnect();
                }}
            }},
            
            handleMessage: function(data) {{
                if (data.type === 'template_changed') {{
                    console.log('Template changed:', data.data.template_name);
                    
                    if ({str(self.config.enable_browser_refresh).lower()}) {{
                        // Simple page reload
                        window.location.reload();
                    }}
                }}
            }},
            
            scheduleReconnect: function() {{
                this.reconnectAttempts++;
                var delay = Math.min(this.reconnectDelay * this.reconnectAttempts, this.maxReconnectDelay);
                
                setTimeout(function() {{
                    window.bladeHotReload.connect();
                }}, delay);
            }},
            
            sendHeartbeat: function() {{
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {{
                    this.socket.send('ping');
                }}
            }}
        }};
        
        // Auto-connect
        window.bladeHotReload.connect();
        
        // Send heartbeat every 30 seconds
        setInterval(function() {{
            window.bladeHotReload.sendHeartbeat();
        }}, 30000);
    }}
}})();
</script>
        """.strip()
    
    def _calculate_initial_checksums(self) -> None:
        """Calculate initial checksums for all templates"""
        for template_path in self._get_all_template_paths():
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                checksum = hashlib.md5(content.encode('utf-8')).hexdigest()
                self.template_checksums[template_path] = checksum
            except Exception:
                pass
    
    def _has_template_changed(self, template_path: str) -> bool:
        """Check if template content has actually changed"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_checksum = hashlib.md5(content.encode('utf-8')).hexdigest()
            old_checksum = self.template_checksums.get(template_path)
            
            if new_checksum != old_checksum:
                self.template_checksums[template_path] = new_checksum
                return True
            
            return False
            
        except Exception:
            return True  # Assume changed if we can't read the file
    
    def _find_template_paths(self, template_name: str) -> List[str]:
        """Find all paths for a template name"""
        paths = []
        for template_dir in self.template_paths:
            template_path = Path(template_dir) / f"{template_name}.blade.html"
            if template_path.exists():
                paths.append(str(template_path))
        return paths
    
    def _get_all_template_paths(self) -> List[str]:
        """Get all template file paths"""
        paths: List[str] = []
        for template_dir in self.template_paths:
            template_dir_path = Path(template_dir)
            if template_dir_path.exists():
                for pattern in self.config.watch_patterns:
                    paths.extend(str(p) for p in template_dir_path.rglob(pattern))
        return paths
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hot reload statistics"""
        stats: Dict[str, Any] = dict(self.stats)
        stats.update({
            'is_active': self.is_active,
            'websocket_clients': self.websocket_broadcaster.get_client_count() if self.websocket_broadcaster else 0,
            'watched_templates': len(self.template_checksums),
            'template_paths': self.template_paths,
            'config': {
                'enabled': self.config.enabled,
                'websocket_port': self.config.websocket_port,
                'debounce_delay': self.config.debounce_delay
            }
        })
        return stats


# Integration with Blade Engine
def add_hot_reload_to_engine(blade_engine: Any, template_paths: List[str], 
                           config: Optional[HotReloadConfig] = None) -> BladeHotReloadManager:
    """Add hot reload capabilities to Blade engine"""
    
    hot_reload = BladeHotReloadManager(blade_engine, template_paths, config)
    
    # Add hot reload script directive
    def hot_reload_directive(content: str) -> str:
        """@hotreload directive to inject client script"""
        if hot_reload.config.enabled and hot_reload.is_active:
            return hot_reload.get_client_script()
        return ''
    
    blade_engine.directive('hotreload', hot_reload_directive)
    
    # Add to engine
    blade_engine.hot_reload = hot_reload
    
    return hot_reload