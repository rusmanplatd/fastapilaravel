from __future__ import annotations

import asyncio
import subprocess
import sys
import os
import signal
from typing import Optional, List, Any
from pathlib import Path

from app.Console.Command import Command


class ServeCommand(Command):
    """Laravel-style serve command to start the development server."""
    
    signature = "serve {--host=127.0.0.1 : The host address to serve the application on} {--port=8000 : The port to serve the application on} {--reload : Enable auto-reload} {--debug : Enable debug mode}"
    
    description = "Serve the application on the PHP development server"
    
    def __init__(self) -> None:
        super().__init__()
        self.server_process: Optional[subprocess.Popen[str]] = None
    
    async def handle(self) -> None:
        """Handle the serve command."""
        host = self.option('host', '127.0.0.1')
        port = int(self.option('port', 8000))
        reload = self.option('reload', False)
        debug = self.option('debug', False)
        
        # Set environment variables
        if debug:
            os.environ['DEBUG'] = 'true'
        
        self.info(f"Starting development server at http://{host}:{port}")
        self.info("Press Ctrl+C to stop the server")
        
        # Build uvicorn command
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'main:app',
            '--host', host,
            '--port', str(port)
        ]
        
        if reload:
            cmd.append('--reload')
        
        if debug:
            cmd.extend(['--log-level', 'debug'])
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Start the server
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Stream output
            if self.server_process.stdout:
                for line in iter(self.server_process.stdout.readline, ''):
                    print(line.rstrip())
                    
            # Wait for process to complete
            self.server_process.wait()
            
        except KeyboardInterrupt:
            self.info("\\nShutting down development server...")
            self._stop_server()
        except Exception as e:
            self.error(f"Failed to start server: {e}")
            return
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        self.info("\\nReceived shutdown signal. Stopping server...")
        self._stop_server()
        sys.exit(0)
    
    def _stop_server(self) -> None:
        """Stop the development server."""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
            except Exception:
                pass
# Register commands
from app.Console.Artisan import register_command

register_command(ServeCommand)
