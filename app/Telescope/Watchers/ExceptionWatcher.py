from __future__ import annotations

import uuid
import traceback
import sys
from typing import Dict, Any, Optional, List

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class ExceptionWatcher(TelescopeWatcher):
    """
    Watches exceptions and errors.
    
    Records unhandled exceptions, their stack traces, and context information.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
        
        # Ignore common exceptions that aren't usually interesting
        self.ignore_patterns.update({
            'KeyboardInterrupt',
            'SystemExit', 
            'GeneratorExit',
            'asyncio.CancelledError',
        })
    
    def record_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        handled: bool = False
    ) -> None:
        """Record an exception."""
        exception_name = exception.__class__.__name__
        
        if self.should_ignore(exception_name):
            return
        
        # Get exception details
        _, _, exc_traceback = sys.exc_info()
        
        content = {
            'class': f"{exception.__class__.__module__}.{exception.__class__.__name__}",
            'file': self._get_exception_file(exc_traceback),
            'line': self._get_exception_line(exc_traceback),
            'message': str(exception),
            'trace': self._format_traceback(exc_traceback),
            'line_preview': self._get_line_preview(exc_traceback),
            'handled': handled,
            'context': context or {},
            'occurred_at': self._get_occurrence_location(exc_traceback),
        }
        
        # Create tags for filtering
        tags = [
            f"class:{exception_name}",
            f"file:{self._get_exception_file(exc_traceback) or 'unknown'}",
            'handled' if handled else 'unhandled',
        ]
        
        # Add severity tag based on exception type
        if isinstance(exception, (ValueError, TypeError, KeyError, AttributeError)):
            tags.append('logic-error')
        elif isinstance(exception, (IOError, OSError, ConnectionError)):
            tags.append('system-error') 
        elif isinstance(exception, (PermissionError, TimeoutError)):
            tags.append('resource-error')
        else:
            tags.append('runtime-error')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_exception(exception),
            should_display_on_index=True,
            type='exception',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_error(
        self,
        message: str,
        error_type: str = 'Error',
        context: Optional[Dict[str, Any]] = None,
        level: str = 'error'
    ) -> None:
        """Record a general error (not an exception)."""
        content = {
            'class': error_type,
            'message': message,
            'level': level,
            'context': context or {},
            'file': self._get_caller_info(),
            'handled': True,  # Manually logged errors are considered handled
        }
        
        tags = [
            f"level:{level}",
            f"type:{error_type}",
            'logged',
            'handled'
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_message(message),
            should_display_on_index=level in ['error', 'critical'],
            type='exception',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def _get_exception_file(self, tb) -> Optional[str]:
        """Get the file where the exception occurred."""
        if tb:
            return tb.tb_frame.f_code.co_filename
        return None
    
    def _get_exception_line(self, tb) -> Optional[int]:
        """Get the line number where the exception occurred."""
        if tb:
            return tb.tb_lineno
        return None
    
    def _format_traceback(self, tb) -> List[Dict[str, Any]]:
        """Format the traceback as a list of frames."""
        if not tb:
            return []
        
        frames = []
        for frame_summary in traceback.extract_tb(tb):
            frames.append({
                'file': frame_summary.filename,
                'line': frame_summary.lineno,
                'function': frame_summary.name,
                'code': frame_summary.line,
            })
        
        return frames
    
    def _get_line_preview(self, tb) -> Optional[Dict[str, Any]]:
        """Get a preview of the code around the exception line."""
        if not tb:
            return None
        
        try:
            filename = tb.tb_frame.f_code.co_filename
            line_number = tb.tb_lineno
            
            with open(filename, 'r') as file:
                lines = file.readlines()
            
            # Get 5 lines before and after the error line
            start = max(0, line_number - 6)
            end = min(len(lines), line_number + 5)
            
            preview_lines = {}
            for i in range(start, end):
                preview_lines[i + 1] = lines[i].rstrip()
            
            return {
                'error_line': line_number,
                'lines': preview_lines,
            }
            
        except (IOError, IndexError):
            return None
    
    def _get_occurrence_location(self, tb) -> Optional[str]:
        """Get a human-readable location where the exception occurred."""
        if not tb:
            return None
        
        filename = tb.tb_frame.f_code.co_filename
        function_name = tb.tb_frame.f_code.co_name
        line_number = tb.tb_lineno
        
        # Get just the filename, not the full path
        import os
        filename = os.path.basename(filename)
        
        return f"{filename}:{line_number} in {function_name}()"
    
    def _hash_exception(self, exception: Exception) -> str:
        """Create a hash for grouping similar exceptions."""
        import hashlib
        
        # Use exception type and message for grouping
        content = f"{exception.__class__.__name__}:{str(exception)}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _hash_message(self, message: str) -> str:
        """Create a hash for grouping similar error messages."""
        import hashlib
        
        return hashlib.md5(message.encode()).hexdigest()[:8]
    
    def _get_caller_info(self) -> Optional[str]:
        """Get information about where the error was logged from."""
        import inspect
        
        try:
            # Walk up the stack to find the calling code
            frame = inspect.currentframe()
            
            # Skip telescope and logging frames
            skip_patterns = [
                'telescope',
                'logging',
                'exception_watcher',
            ]
            
            for _ in range(10):  # Look up to 10 frames
                if frame is None:
                    break
                frame = frame.f_back
                if not frame:
                    break
                
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                line_number = frame.f_lineno
                
                # Skip internal frames
                if any(pattern in filename.lower() for pattern in skip_patterns):
                    continue
                
                # Return the first non-internal frame
                import os
                filename = os.path.basename(filename)
                return f"{filename}:{line_number} in {function_name}()"
            
        except Exception:
            pass
        
        return None