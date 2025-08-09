"""
Blade Template Streaming and Chunked Rendering System
Provides streaming templates for improved performance and user experience
"""
from __future__ import annotations

import asyncio
import threading
import time
import json
from typing import Dict, List, Optional, Any, AsyncIterator, Callable, Union, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import re
from io import StringIO
import gzip


@dataclass
class StreamChunk:
    """Represents a chunk of streaming content"""
    content: str
    chunk_type: str = 'html'  # 'html', 'script', 'style', 'meta', 'data'
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    size: int = 0
    
    def __post_init__(self) -> None:
        self.size = len(self.content.encode('utf-8'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'content': self.content,
            'type': self.chunk_type,
            'priority': self.priority,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'size': self.size
        }


@dataclass
class StreamingConfig:
    """Configuration for template streaming"""
    buffer_size: int = 8192
    flush_threshold: int = 4096
    enable_compression: bool = True
    compression_threshold: int = 1024
    chunk_timeout: float = 1.0
    enable_progressive_enhancement: bool = True
    enable_script_streaming: bool = True
    enable_style_streaming: bool = True
    priority_chunks: bool = True
    max_concurrent_chunks: int = 10


class ChunkBuffer:
    """Buffer for managing streaming chunks"""
    
    def __init__(self, config: StreamingConfig):
        self.config = config
        self.buffer: List[StreamChunk] = []
        self.total_size = 0
        self._lock = threading.Lock()
    
    def add_chunk(self, chunk: StreamChunk) -> bool:
        """Add chunk to buffer, returns True if buffer should be flushed"""
        with self._lock:
            self.buffer.append(chunk)
            self.total_size += chunk.size
            
            # Sort by priority if enabled
            if self.config.priority_chunks:
                self.buffer.sort(key=lambda c: (-c.priority, c.timestamp))
            
            return self.total_size >= self.config.flush_threshold
    
    def flush(self) -> List[StreamChunk]:
        """Flush buffer and return chunks"""
        with self._lock:
            chunks = self.buffer.copy()
            self.buffer.clear()
            self.total_size = 0
            return chunks
    
    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        with self._lock:
            return len(self.buffer) == 0
    
    def get_size(self) -> int:
        """Get total buffer size"""
        with self._lock:
            return self.total_size


class TemplateStreamer:
    """Handles template streaming operations"""
    
    def __init__(self, config: StreamingConfig):
        self.config = config
        self.chunk_buffer = ChunkBuffer(config)
        self.compression_enabled = config.enable_compression
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_chunks)
    
    async def stream_template(self, template_content: str, context: Dict[str, Any]) -> AsyncIterator[str]:
        """Stream template content in chunks"""
        
        # Parse template into streamable sections
        sections = self._parse_streaming_sections(template_content)
        
        for section in sections:
            # Process section asynchronously
            chunk = await self._process_section_async(section, context)
            
            # Add to buffer
            should_flush = self.chunk_buffer.add_chunk(chunk)
            
            if should_flush:
                # Flush buffer and yield chunks
                chunks = self.chunk_buffer.flush()
                for buffered_chunk in chunks:
                    yield await self._prepare_chunk_output(buffered_chunk)
        
        # Flush remaining chunks
        if not self.chunk_buffer.is_empty():
            chunks = self.chunk_buffer.flush()
            for chunk in chunks:
                yield await self._prepare_chunk_output(chunk)
    
    def _parse_streaming_sections(self, template_content: str) -> List[Dict[str, Any]]:
        """Parse template content into streamable sections"""
        sections = []
        
        # Split by streaming directives and blocks
        streaming_patterns = [
            (r'@stream\s*\(\s*[\'"](.+?)[\'"]\s*\)(.*?)@endstream', 'stream'),
            (r'@defer\s*\(\s*[\'"](.+?)[\'"]\s*\)(.*?)@enddefer', 'defer'),
            (r'@lazy\s*\(\s*[\'"](.+?)[\'"]\s*\)(.*?)@endlazy', 'lazy'),
            (r'@async\s*\(\s*[\'"](.+?)[\'"]\s*\)(.*?)@endasync', 'async'),
            (r'<script[^>]*>(.*?)</script>', 'script'),
            (r'<style[^>]*>(.*?)</style>', 'style'),
        ]
        
        current_pos = 0
        
        for pattern, section_type in streaming_patterns:
            for match in re.finditer(pattern, template_content, re.DOTALL | re.IGNORECASE):
                # Add content before this section
                if match.start() > current_pos:
                    sections.append({
                        'type': 'html',
                        'content': template_content[current_pos:match.start()],
                        'priority': 10
                    })
                
                # Add the streaming section
                if section_type in ['stream', 'defer', 'lazy', 'async']:
                    section_name = match.group(1)
                    section_content = match.group(2)
                    sections.append({
                        'type': section_type,
                        'name': section_name,
                        'content': section_content,
                        'priority': self._get_section_priority(section_type)
                    })
                else:
                    sections.append({
                        'type': section_type,
                        'content': match.group(1),
                        'priority': self._get_section_priority(section_type)
                    })
                
                current_pos = match.end()
        
        # Add remaining content
        if current_pos < len(template_content):
            sections.append({
                'type': 'html',
                'content': template_content[current_pos:],
                'priority': 10
            })
        
        return sections
    
    def _get_section_priority(self, section_type: str) -> int:
        """Get priority for different section types"""
        priorities = {
            'html': 10,
            'style': 9,
            'script': 8,
            'stream': 7,
            'async': 6,
            'defer': 5,
            'lazy': 4
        }
        return priorities.get(section_type, 5)
    
    async def _process_section_async(self, section: Dict[str, Any], context: Dict[str, Any]) -> StreamChunk:
        """Process a template section asynchronously"""
        section_type = section['type']
        content = section['content']
        priority = section['priority']
        
        # Handle different section types
        if section_type == 'defer':
            # Defer processing
            await asyncio.sleep(0.1)  # Small delay
            processed_content = await self._render_content_async(content, context)
        elif section_type == 'lazy':
            # Lazy loading placeholder
            section_name = section.get('name', 'lazy')
            processed_content = f'<div id="lazy-{section_name}" data-lazy-src="{section_name}">Loading...</div>'
        elif section_type == 'async':
            # Async processing
            processed_content = await self._render_content_async(content, context)
        else:
            # Synchronous processing
            processed_content = content
        
        return StreamChunk(
            content=processed_content,
            chunk_type=section_type,
            priority=priority,
            metadata=section
        )
    
    async def _render_content_async(self, content: str, context: Dict[str, Any]) -> str:
        """Render template content asynchronously"""
        # This would integrate with the main Blade engine
        # For now, simple variable substitution
        rendered = content
        for key, value in context.items():
            rendered = rendered.replace(f'{{{{{key}}}}}', str(value))
        return rendered
    
    async def _prepare_chunk_output(self, chunk: StreamChunk) -> str:
        """Prepare chunk for output"""
        content = chunk.content
        
        # Apply compression if enabled and content is large enough
        if (self.compression_enabled and 
            chunk.size > self.config.compression_threshold and
            chunk.chunk_type == 'html'):
            
            # For streaming, we'll use inline compression indicators
            content = f'<!-- compressed -->{content}<!-- /compressed -->'
        
        # Add streaming metadata for debugging (only in debug mode)
        if chunk.metadata.get('debug', False):
            content = f'<!-- chunk: {chunk.chunk_type}, size: {chunk.size} -->\n{content}'
        
        return content
    
    def close(self) -> None:
        """Close the streamer and cleanup resources"""
        self.executor.shutdown(wait=True)


class ProgressiveRenderer:
    """Handles progressive enhancement and lazy loading"""
    
    def __init__(self) -> None:
        self.lazy_sections: Dict[str, str] = {}
        self.progressive_scripts: List[str] = []
    
    def register_lazy_section(self, name: str, content: str) -> str:
        """Register a lazy-loadable section"""
        self.lazy_sections[name] = content
        return f'<div id="lazy-{name}" data-lazy-content="{name}">Loading {name}...</div>'
    
    def get_lazy_content(self, name: str) -> Optional[str]:
        """Get content for a lazy section"""
        return self.lazy_sections.get(name)
    
    def add_progressive_script(self, script: str) -> None:
        """Add script for progressive enhancement"""
        self.progressive_scripts.append(script)
    
    def get_progressive_enhancement_script(self) -> str:
        """Get JavaScript for progressive enhancement"""
        lazy_loader = """
        <script>
        (function() {
            // Lazy loading functionality
            const lazyElements = document.querySelectorAll('[data-lazy-content]');
            
            const loadLazyContent = async (element) => {
                const contentName = element.dataset.lazyContent;
                try {
                    const response = await fetch(`/lazy/${contentName}`);
                    const content = await response.text();
                    element.innerHTML = content;
                    element.removeAttribute('data-lazy-content');
                } catch (error) {
                    element.innerHTML = '<div class="lazy-error">Failed to load content</div>';
                }
            };
            
            // Intersection Observer for lazy loading
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        loadLazyContent(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            });
            
            lazyElements.forEach(element => observer.observe(element));
            
            // Progressive enhancement scripts
        """ + '\n'.join(self.progressive_scripts) + """
        })();
        </script>
        """
        
        return lazy_loader.strip()


class BladeStreamingDirectives:
    """Streaming-related Blade directives"""
    
    def __init__(self, blade_engine: Any) -> None:
        self.blade_engine = blade_engine
        self.progressive_renderer = ProgressiveRenderer()
    
    def register_streaming_directives(self) -> Dict[str, Callable[..., str]]:
        """Register streaming directives"""
        return {
            # Streaming directives
            'stream': self._stream_directive,
            'endstream': self._endstream_directive,
            
            # Deferred rendering
            'defer': self._defer_directive,
            'enddefer': self._enddefer_directive,
            
            # Lazy loading
            'lazy': self._lazy_directive,
            'endlazy': self._endlazy_directive,
            
            # Async processing
            'async': self._async_directive,
            'endasync': self._endasync_directive,
            
            # Progressive enhancement
            'progressive': self._progressive_directive,
            'endprogressive': self._endprogressive_directive,
            
            # Chunked content
            'chunk': self._chunk_directive,
            'endchunk': self._endchunk_directive,
            
            # Streaming utilities
            'flush': self._flush_directive,
            'priority': self._priority_directive,
            'compress': self._compress_directive,
            'endcompress': self._endcompress_directive,
            
            # Performance hints
            'preload': self._preload_directive,
            'prefetch': self._prefetch_directive,
            'dns_prefetch': self._dns_prefetch_directive,
            'preconnect': self._preconnect_directive,
        }
    
    def _stream_directive(self, content: str) -> str:
        """@stream directive for streaming sections"""
        section_name = content.strip().strip('"\'')
        return f'<!-- stream:start:{section_name} -->'
    
    def _endstream_directive(self, content: str) -> str:
        """End stream directive"""
        return '<!-- stream:end -->'
    
    def _defer_directive(self, content: str) -> str:
        """@defer directive for deferred rendering"""
        priority = content.strip().strip('"\'') if content else 'normal'
        return f'<!-- defer:start:{priority} -->'
    
    def _enddefer_directive(self, content: str) -> str:
        """End defer directive"""
        return '<!-- defer:end -->'
    
    def _lazy_directive(self, content: str) -> str:
        """@lazy directive for lazy loading"""
        section_name = content.strip().strip('"\'')
        return f'<div id="lazy-{section_name}" data-lazy-src="{section_name}" class="lazy-loading">Loading...</div>'
    
    def _endlazy_directive(self, content: str) -> str:
        """End lazy directive"""
        return ''
    
    def _async_directive(self, content: str) -> str:
        """@async directive for async processing"""
        return '<!-- async:start -->'
    
    def _endasync_directive(self, content: str) -> str:
        """End async directive"""
        return '<!-- async:end -->'
    
    def _progressive_directive(self, content: str) -> str:
        """@progressive directive for progressive enhancement"""
        feature = content.strip().strip('"\'') if content else 'default'
        return f'<div class="progressive-enhancement" data-feature="{feature}">'
    
    def _endprogressive_directive(self, content: str) -> str:
        """End progressive directive"""
        return '</div>'
    
    def _chunk_directive(self, content: str) -> str:
        """@chunk directive for explicit chunking"""
        chunk_size = content.strip() if content else '4096'
        return f'<!-- chunk:size:{chunk_size} -->'
    
    def _endchunk_directive(self, content: str) -> str:
        """End chunk directive"""
        return '<!-- chunk:end -->'
    
    def _flush_directive(self, content: str) -> str:
        """@flush directive to force buffer flush"""
        return '<!-- flush -->'
    
    def _priority_directive(self, content: str) -> str:
        """@priority directive to set chunk priority"""
        priority = content.strip() if content else '5'
        return f'<!-- priority:{priority} -->'
    
    def _compress_directive(self, content: str) -> str:
        """@compress directive for content compression"""
        algorithm = content.strip().strip('"\'') if content else 'gzip'
        return f'<!-- compress:{algorithm} -->'
    
    def _endcompress_directive(self, content: str) -> str:
        """End compress directive"""
        return '<!-- compress:end -->'
    
    def _preload_directive(self, content: str) -> str:
        """@preload directive for resource preloading"""
        # Parse @preload('script.js', 'script') or @preload('style.css', 'style')
        parts = [p.strip().strip('"\'') for p in content.split(',')]
        resource = parts[0] if parts else ''
        resource_type = parts[1] if len(parts) > 1 else 'script'
        
        if resource_type == 'style':
            return f'<link rel="preload" href="{resource}" as="style">'
        elif resource_type == 'script':
            return f'<link rel="preload" href="{resource}" as="script">'
        elif resource_type == 'font':
            return f'<link rel="preload" href="{resource}" as="font" crossorigin>'
        else:
            return f'<link rel="preload" href="{resource}" as="{resource_type}">'
    
    def _prefetch_directive(self, content: str) -> str:
        """@prefetch directive for resource prefetching"""
        resource = content.strip().strip('"\'')
        return f'<link rel="prefetch" href="{resource}">'
    
    def _dns_prefetch_directive(self, content: str) -> str:
        """@dnsPrefetch directive for DNS prefetching"""
        domain = content.strip().strip('"\'')
        return f'<link rel="dns-prefetch" href="//{domain}">'
    
    def _preconnect_directive(self, content: str) -> str:
        """@preconnect directive for connection preloading"""
        domain = content.strip().strip('"\'')
        return f'<link rel="preconnect" href="//{domain}">'


class StreamingBladeEngine:
    """Enhanced Blade engine with streaming capabilities"""
    
    def __init__(self, blade_engine: Any, config: Optional[StreamingConfig] = None) -> None:
        self.blade_engine = blade_engine
        self.config = config or StreamingConfig()
        self.streamer = TemplateStreamer(self.config)
        self.streaming_directives = BladeStreamingDirectives(blade_engine)
        
        # Register streaming directives
        self._register_streaming_directives()
    
    def _register_streaming_directives(self) -> None:
        """Register streaming directives with the Blade engine"""
        directives = self.streaming_directives.register_streaming_directives()
        for name, callback in directives.items():
            self.blade_engine.directive(name, callback)
    
    async def render_streaming(self, template_name: str, 
                             context: Optional[Dict[str, Any]] = None) -> AsyncIterator[str]:
        """Render template with streaming"""
        context = context or {}
        
        # Load template
        template_path = self.blade_engine._find_template(template_name)
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Compile Blade to get base content
        compiled_content = self.blade_engine.compile_blade(template_content)
        
        # Stream the compiled content
        async for chunk in self.streamer.stream_template(compiled_content, context):
            yield chunk
    
    def render_chunked(self, template_name: str, 
                      context: Optional[Dict[str, Any]] = None,
                      chunk_size: Optional[int] = None) -> Iterator[str]:
        """Render template in chunks (synchronous)"""
        context = context or {}
        chunk_size = chunk_size or self.config.buffer_size
        
        # Render normally first
        rendered_content = self.blade_engine.render(template_name, context)
        
        # Return in chunks
        for i in range(0, len(rendered_content), chunk_size):
            yield rendered_content[i:i + chunk_size]
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        return {
            'config': {
                'buffer_size': self.config.buffer_size,
                'flush_threshold': self.config.flush_threshold,
                'compression_enabled': self.config.enable_compression,
                'progressive_enhancement': self.config.enable_progressive_enhancement
            },
            'buffer_size': self.streamer.chunk_buffer.get_size(),
            'buffer_empty': self.streamer.chunk_buffer.is_empty()
        }
    
    def close(self) -> None:
        """Close streaming engine"""
        self.streamer.close()


# Helper functions for streaming templates
def create_streaming_response(streaming_engine: StreamingBladeEngine, 
                            template_name: str, context: Optional[Dict[str, Any]] = None) -> Any:
    """Create a streaming HTTP response (framework-agnostic)"""
    async def stream_generator() -> AsyncIterator[str]:
        async for chunk in streaming_engine.render_streaming(template_name, context):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    
    return stream_generator


def add_streaming_to_blade_engine(blade_engine: Any, config: Optional[StreamingConfig] = None) -> None:
    """Add streaming capabilities to existing Blade engine"""
    config = config or StreamingConfig()
    streaming_engine = StreamingBladeEngine(blade_engine, config)
    
    # Add streaming methods to the original engine
    blade_engine.render_streaming = streaming_engine.render_streaming
    blade_engine.render_chunked = streaming_engine.render_chunked
    blade_engine.streaming_stats = streaming_engine.get_streaming_stats
    blade_engine.streaming_engine = streaming_engine
    
    # Add streaming globals
    def stream_chunk(content: str, chunk_type: str = 'html', priority: int = 5) -> StreamChunk:
        """Create a stream chunk"""
        return StreamChunk(content=content, chunk_type=chunk_type, priority=priority)
    
    def lazy_load(section_name: str, placeholder: str = 'Loading...') -> str:
        """Create a lazy loading placeholder"""
        return f'<div id="lazy-{section_name}" data-lazy-src="{section_name}">{placeholder}</div>'
    
    blade_engine.env.globals.update({
        'stream_chunk': stream_chunk,
        'lazy_load': lazy_load,
        'StreamChunk': StreamChunk
    })
    
    # Note: This function doesn't return anything meaningful