from __future__ import annotations

import json
import time
import secrets
from typing import Any, Dict, Optional, List, Union
from abc import ABC, abstractmethod
from pathlib import Path
import hashlib
from datetime import datetime, timedelta


class SessionStore(ABC):
    """Abstract session store."""
    
    @abstractmethod
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        # Override this method to implement session retrieval
        # Should return None if session doesn't exist or is expired
        return None
    
    @abstractmethod
    def put(self, session_id: str, data: Dict[str, Any], lifetime: int) -> None:
        """Store session data."""
        # Override this method to implement session storage
        # lifetime is in seconds from now
        pass
    
    @abstractmethod
    def forget(self, session_id: str) -> None:
        """Delete session."""
        # Override this method to implement session deletion
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Delete all sessions."""
        # Override this method to implement clearing all sessions
        pass
    
    @abstractmethod
    def gc(self, lifetime: int) -> None:
        """Garbage collect expired sessions."""
        # Override this method to implement cleanup of expired sessions
        pass


class FileSessionStore(SessionStore):
    """File-based session store."""
    
    def __init__(self, path: str = 'storage/framework/sessions') -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from file."""
        file_path = self.path / session_id
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check if session is expired
            if data.get('expires_at', 0) < time.time():
                self.forget(session_id)
                return None
            
            return data.get('data', {})  # type: ignore
        except (json.JSONDecodeError, IOError):
            return None
    
    def put(self, session_id: str, data: Dict[str, Any], lifetime: int) -> None:
        """Store session data to file."""
        file_path = self.path / session_id
        
        session_data = {
            'data': data,
            'expires_at': time.time() + lifetime,
            'created_at': time.time(),
        }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(session_data, f)
        except IOError:
            pass  # Silently fail for now
    
    def forget(self, session_id: str) -> None:
        """Delete session file."""
        file_path = self.path / session_id
        
        try:
            if file_path.exists():
                file_path.unlink()
        except IOError:
            pass
    
    def flush(self) -> None:
        """Delete all session files."""
        try:
            for file_path in self.path.glob('*'):
                if file_path.is_file():
                    file_path.unlink()
        except IOError:
            pass
    
    def gc(self, lifetime: int) -> None:
        """Garbage collect expired sessions."""
        current_time = time.time()
        
        try:
            for file_path in self.path.glob('*'):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        
                        if data.get('expires_at', 0) < current_time:
                            file_path.unlink()
                    except (json.JSONDecodeError, IOError):
                        # Remove corrupted files
                        file_path.unlink()
        except IOError:
            pass


class DatabaseSessionStore(SessionStore):
    """Database-based session store."""
    
    def __init__(self, connection: Any) -> None:
        self.connection = connection
        self._ensure_table()
    
    def _ensure_table(self) -> None:
        """Ensure sessions table exists."""
        # Create sessions table if it doesn't exist
        # Example SQL for reference:
        # CREATE TABLE IF NOT EXISTS sessions (
        #     id VARCHAR(255) PRIMARY KEY,
        #     payload TEXT NOT NULL,
        #     last_activity INTEGER NOT NULL,
        #     user_id INTEGER,
        #     ip_address VARCHAR(45),
        #     user_agent TEXT
        # );
        pass
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from database."""
        try:
            # Example implementation:
            # cursor = self.connection.cursor()
            # cursor.execute(
            #     "SELECT payload, last_activity FROM sessions WHERE id = ? AND last_activity > ?",
            #     (session_id, int(time.time()) - lifetime)
            # )
            # row = cursor.fetchone()
            # if row:
            #     return json.loads(row[0])
            return None
        except Exception:
            return None
    
    def put(self, session_id: str, data: Dict[str, Any], lifetime: int) -> None:
        """Store session data to database."""
        try:
            # Example implementation:
            # payload = json.dumps(data)
            # last_activity = int(time.time())
            # cursor = self.connection.cursor()
            # cursor.execute(
            #     "INSERT OR REPLACE INTO sessions (id, payload, last_activity) VALUES (?, ?, ?)",
            #     (session_id, payload, last_activity)
            # )
            # self.connection.commit()
            pass
        except Exception:
            pass
    
    def forget(self, session_id: str) -> None:
        """Delete session from database."""
        try:
            # Example implementation:
            # cursor = self.connection.cursor()
            # cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            # self.connection.commit()
            pass
        except Exception:
            pass
    
    def flush(self) -> None:
        """Delete all sessions from database."""
        try:
            # Example implementation:
            # cursor = self.connection.cursor()
            # cursor.execute("DELETE FROM sessions")
            # self.connection.commit()
            pass
        except Exception:
            pass
    
    def gc(self, lifetime: int) -> None:
        """Garbage collect expired sessions."""
        try:
            # Example implementation:
            # expired_threshold = int(time.time()) - lifetime
            # cursor = self.connection.cursor()
            # cursor.execute("DELETE FROM sessions WHERE last_activity < ?", (expired_threshold,))
            # self.connection.commit()
            pass
        except Exception:
            pass


class ArraySessionStore(SessionStore):
    """In-memory session store (for testing)."""
    
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from memory."""
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        
        # Check if expired
        if session.get('expires_at', 0) < time.time():
            del self._sessions[session_id]
            return None
        
        return session.get('data', {})  # type: ignore
    
    def put(self, session_id: str, data: Dict[str, Any], lifetime: int) -> None:
        """Store session data in memory."""
        self._sessions[session_id] = {
            'data': data,
            'expires_at': time.time() + lifetime,
            'created_at': time.time(),
        }
    
    def forget(self, session_id: str) -> None:
        """Delete session from memory."""
        self._sessions.pop(session_id, None)
    
    def flush(self) -> None:
        """Delete all sessions from memory."""
        self._sessions.clear()
    
    def gc(self, lifetime: int) -> None:
        """Garbage collect expired sessions."""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if session.get('expires_at', 0) < current_time
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]


class Session:
    """Laravel-style session manager."""
    
    def __init__(self, store: SessionStore, session_id: Optional[str] = None, lifetime: int = 7200) -> None:
        self.store = store
        self.session_id = session_id or self._generate_session_id()
        self.lifetime = lifetime
        self._data: Dict[str, Any] = {}
        self._loaded = False
        self._started = False
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return secrets.token_urlsafe(40)
    
    def start(self) -> None:
        """Start the session."""
        if self._started:
            return
        
        self._load_session()
        self._started = True
    
    def _load_session(self) -> None:
        """Load session data from store."""
        if self._loaded:
            return
        
        data = self.store.get(self.session_id)
        self._data = data or {}
        self._loaded = True
    
    def save(self) -> None:
        """Save session data to store."""
        if not self._started:
            return
        
        self.store.put(self.session_id, self._data, self.lifetime)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get session value."""
        self.start()
        return self._data.get(key, default)
    
    def put(self, key: str, value: Any) -> None:
        """Put value in session."""
        self.start()
        self._data[key] = value
    
    def push(self, key: str, value: Any) -> None:
        """Push value to array in session."""
        self.start()
        if key not in self._data:
            self._data[key] = []
        
        if isinstance(self._data[key], list):
            self._data[key].append(value)
        else:
            self._data[key] = [value]
    
    def pull(self, key: str, default: Any = None) -> Any:
        """Get and remove value from session."""
        self.start()
        return self._data.pop(key, default)
    
    def forget(self, keys: Union[str, List[str]]) -> None:
        """Remove values from session."""
        self.start()
        
        if isinstance(keys, str):
            keys = [keys]
        
        for key in keys:
            self._data.pop(key, None)
    
    def flush(self) -> None:
        """Remove all values from session."""
        self.start()
        self._data.clear()
    
    def invalidate(self) -> None:
        """Invalidate the session."""
        self.flush()
        self.store.forget(self.session_id)
        self.session_id = self._generate_session_id()
    
    def regenerate(self, destroy: bool = False) -> None:
        """Regenerate session ID."""
        if destroy:
            self.store.forget(self.session_id)
        
        self.session_id = self._generate_session_id()
    
    def exists(self, key: str) -> bool:
        """Check if key exists in session."""
        self.start()
        return key in self._data
    
    def has(self, key: str) -> bool:
        """Check if key exists and is not None."""
        return self.exists(key) and self.get(key) is not None
    
    def missing(self, key: str) -> bool:
        """Check if key is missing from session."""
        return not self.exists(key)
    
    def all(self) -> Dict[str, Any]:
        """Get all session data."""
        self.start()
        return self._data.copy()
    
    def only(self, keys: List[str]) -> Dict[str, Any]:
        """Get only specified keys."""
        self.start()
        return {key: self._data.get(key) for key in keys if key in self._data}
    
    def except_keys(self, keys: List[str]) -> Dict[str, Any]:
        """Get all except specified keys."""
        self.start()
        return {key: value for key, value in self._data.items() if key not in keys}
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment numeric value."""
        self.start()
        current = self._data.get(key, 0)
        if isinstance(current, (int, float)):
            self._data[key] = current + amount
        else:
            self._data[key] = amount
        return self._data[key]  # type: ignore
    
    def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement numeric value."""
        return self.increment(key, -amount)
    
    # Flash data methods
    def flash(self, key: str, value: Any) -> None:
        """Flash data for next request."""
        self.put(f'_flash.new.{key}', value)
    
    def flash_now(self, key: str, value: Any) -> None:
        """Flash data for current request."""
        self.put(f'_flash.old.{key}', value)
    
    def reflash(self) -> None:
        """Reflash all current flash data."""
        self.start()
        old_flash = self._get_flash_data('old')
        for key, value in old_flash.items():
            self.flash(key, value)
    
    def keep(self, keys: Union[str, List[str]]) -> None:
        """Keep specific flash data for next request."""
        if isinstance(keys, str):
            keys = [keys]
        
        for key in keys:
            value = self.get(f'_flash.old.{key}')
            if value is not None:
                self.flash(key, value)
    
    def _get_flash_data(self, type_: str) -> Dict[str, Any]:
        """Get flash data of specific type."""
        self.start()
        flash_key = f'_flash.{type_}'
        return {
            key.replace(f'{flash_key}.', ''): value
            for key, value in self._data.items()
            if key.startswith(f'{flash_key}.')
        }
    
    def _age_flash_data(self) -> None:
        """Age flash data (move new to old, remove old)."""
        self.start()
        
        # Remove old flash data
        old_keys = [key for key in self._data.keys() if key.startswith('_flash.old.')]
        for key in old_keys:
            del self._data[key]
        
        # Move new flash data to old
        new_keys = [key for key in self._data.keys() if key.startswith('_flash.new.')]
        for key in new_keys:
            old_key = key.replace('_flash.new.', '_flash.old.')
            self._data[old_key] = self._data.pop(key)
    
    def get_id(self) -> str:
        """Get session ID."""
        return self.session_id
    
    def set_id(self, session_id: str) -> None:
        """Set session ID."""
        self.session_id = session_id
    
    def get_name(self) -> str:
        """Get session name."""
        return 'laravel_session'
    
    def token(self) -> str:
        """Get CSRF token."""
        if not self.has('_token'):
            self.put('_token', secrets.token_urlsafe(40))
        return self.get('_token')  # type: ignore
    
    def regenerate_token(self) -> str:
        """Regenerate CSRF token."""
        token = secrets.token_urlsafe(40)
        self.put('_token', token)
        return token
    
    def previous_url(self) -> Optional[str]:
        """Get previous URL."""
        return self.get('_previous.url')  # type: ignore
    
    def set_previous_url(self, url: str) -> None:
        """Set previous URL."""
        self.put('_previous.url', url)


class SessionManager:
    """Session manager for different stores."""
    
    def __init__(self, default_driver: str = 'file') -> None:
        self._default_driver = default_driver
        self._stores: Dict[str, SessionStore] = {}
        self._sessions: Dict[str, Session] = {}
        
        # Register default stores
        self._register_default_stores()
    
    def _register_default_stores(self) -> None:
        """Register default session stores."""
        self._stores['file'] = FileSessionStore()
        self._stores['array'] = ArraySessionStore()
    
    def store(self, name: Optional[str] = None) -> SessionStore:
        """Get session store."""
        name = name or self._default_driver
        
        if name not in self._stores:
            raise ValueError(f"Session store '{name}' not found")
        
        return self._stores[name]
    
    def driver(self, name: Optional[str] = None) -> Session:
        """Get session instance."""
        name = name or self._default_driver
        
        if name not in self._sessions:
            store = self.store(name)
            self._sessions[name] = Session(store)
        
        return self._sessions[name]
    
    def extend(self, driver: str, store: SessionStore) -> None:
        """Register custom session store."""
        self._stores[driver] = store


# Global session manager
session_manager = SessionManager()


def session(driver: Optional[str] = None) -> Session:
    """Get session instance."""
    return session_manager.driver(driver)