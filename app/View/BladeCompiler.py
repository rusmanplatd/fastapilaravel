"""
Advanced Blade Template Compiler
Provides conditional compilation, minification, and optimization features
"""
from __future__ import annotations

import re
import json
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
import os
from datetime import datetime
import gzip
import base64


class BladeCompilationContext:
    """Context for template compilation"""
    
    def __init__(self, environment: str = 'production', features: Optional[Dict[str, bool]] = None):
        self.environment = environment
        self.features = features or {}
        self.variables: Dict[str, Any] = {}
        self.dependencies: Set[str] = set()
        self.performance_hints: List[str] = []


class BladeMinifier:
    """Template minification and optimization"""
    
    def __init__(self) -> None:
        self.preserve_comments = False
        self.preserve_whitespace = False
        self.optimize_expressions = True
    
    def minify_html(self, content: str) -> str:
        """Minify HTML content"""
        if not content.strip():
            return content
        
        # Remove HTML comments (but preserve Blade comments)
        content = re.sub(r'<!--(?!.*?{).*?-->', '', content, flags=re.DOTALL)
        
        # Collapse whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove whitespace around block elements
        block_elements = ['div', 'section', 'article', 'nav', 'header', 'footer', 'main', 'aside']
        for element in block_elements:
            content = re.sub(rf'\s*<{element}([^>]*)>\s*', rf'<{element}\1>', content)
            content = re.sub(rf'\s*</{element}>\s*', rf'</{element}>', content)
        
        # Remove unnecessary quotes from attributes
        content = re.sub(r'=\s*"([^"\s<>=]+)"', r'=\1', content)
        content = re.sub(r"=\s*'([^'\s<>=]+)'", r'=\1', content)
        
        return content.strip()
    
    def minify_css(self, css_content: str) -> str:
        """Minify CSS content within templates"""
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        css_content = re.sub(r'\s+', ' ', css_content)
        css_content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', css_content)
        
        # Remove trailing semicolons
        css_content = re.sub(r';}', '}', css_content)
        
        return css_content.strip()
    
    def minify_javascript(self, js_content: str) -> str:
        """Basic JavaScript minification"""
        # Remove single-line comments
        js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        js_content = re.sub(r'\s+', ' ', js_content)
        js_content = re.sub(r'\s*([{}();,=<>!&|+\-*/])\s*', r'\1', js_content)
        
        return js_content.strip()
    
    def optimize_blade_expressions(self, content: str) -> str:
        """Optimize Blade expressions"""
        # Cache repeated expressions
        expressions = re.findall(r'\{\{\s*(.+?)\s*\}\}', content)
        expression_cache = {}
        
        for expr in expressions:
            if expr.count('.') > 2:  # Deep property access
                cache_key = f"_cached_{hashlib.md5(expr.encode()).hexdigest()[:8]}"
                expression_cache[expr] = cache_key
        
        # Replace with cached versions
        for original, cached in expression_cache.items():
            content = content.replace(f"{{{{ {original} }}}}", f"{{{{ {cached} or ({original}) }}}}")
        
        return content


class ConditionalCompiler:
    """Conditional compilation based on environment and feature flags"""
    
    def __init__(self, context: BladeCompilationContext):
        self.context = context
    
    def compile_conditionals(self, content: str) -> str:
        """Process conditional compilation directives"""
        
        # @env directive for environment-specific code
        content = self._process_env_blocks(content)
        
        # @feature directive for feature flag blocks
        content = self._process_feature_blocks(content)
        
        # @debug blocks (removed in production)
        content = self._process_debug_blocks(content)
        
        # @compress blocks
        content = self._process_compress_blocks(content)
        
        return content
    
    def _process_env_blocks(self, content: str) -> str:
        """Process @env blocks"""
        pattern = r'@env\s*\(\s*[\'"](.+?)[\'"]\s*\)(.*?)@endenv'
        
        def env_replacer(match: re.Match[str]) -> str:
            environments = [env.strip() for env in match.group(1).split(',')]
            block_content = match.group(2)
            
            if self.context.environment in environments:
                return block_content
            else:
                return ''
        
        return re.sub(pattern, env_replacer, content, flags=re.DOTALL)
    
    def _process_feature_blocks(self, content: str) -> str:
        """Process @feature blocks"""
        pattern = r'@feature\s*\(\s*[\'"](.+?)[\'"]\s*\)(.*?)@endfeature'
        
        def feature_replacer(match: re.Match[str]) -> str:
            feature_name = match.group(1)
            block_content = match.group(2)
            
            if self.context.features.get(feature_name, False):
                return block_content
            else:
                return ''
        
        return re.sub(pattern, feature_replacer, content, flags=re.DOTALL)
    
    def _process_debug_blocks(self, content: str) -> str:
        """Process @debug blocks"""
        if self.context.environment == 'production':
            # Remove all debug blocks in production
            pattern = r'@debug.*?@enddebug'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        return content
    
    def _process_compress_blocks(self, content: str) -> str:
        """Process @compress blocks"""
        pattern = r'@compress\s*\(\s*[\'"](.+?)[\'"]\s*\)(.*?)@endcompress'
        
        def compress_replacer(match: re.Match[str]) -> str:
            compression_type = match.group(1)
            block_content = match.group(2)
            
            minifier = BladeMinifier()
            
            if compression_type == 'html':
                return minifier.minify_html(block_content)
            elif compression_type == 'css':
                return f"<style>{minifier.minify_css(block_content)}</style>"
            elif compression_type == 'js':
                return f"<script>{minifier.minify_javascript(block_content)}</script>"
            else:
                return block_content
        
        return re.sub(pattern, compress_replacer, content, flags=re.DOTALL)


class BladeOptimizer:
    """Advanced template optimization"""
    
    def __init__(self) -> None:
        self.optimization_level = 2  # 0=none, 1=basic, 2=aggressive
        self.inline_threshold = 1024  # bytes
    
    def optimize_template(self, content: str, template_path: str) -> str:
        """Apply various optimizations to template"""
        
        if self.optimization_level >= 1:
            content = self._inline_small_partials(content, template_path)
            content = self._optimize_loops(content)
            content = self._cache_expensive_expressions(content)
        
        if self.optimization_level >= 2:
            content = self._precompute_static_expressions(content)
            content = self._optimize_conditionals(content)
            content = self._bundle_assets(content)
        
        return content
    
    def _inline_small_partials(self, content: str, template_path: str) -> str:
        """Inline small partial templates"""
        include_pattern = r'@include\s*\(\s*[\'"](.+?)[\'"]\s*\)'
        
        def include_replacer(match: re.Match[str]) -> str:
            partial_name = match.group(1)
            partial_path = Path(template_path).parent / f"{partial_name}.blade.html"
            
            if partial_path.exists():
                file_size = partial_path.stat().st_size
                if file_size <= self.inline_threshold:
                    try:
                        with open(partial_path, 'r', encoding='utf-8') as f:
                            partial_content = f.read()
                        return f"{{# Inlined: {partial_name} #}}\n{partial_content}\n{{# End inline #}}"
                    except Exception:
                        pass
            
            return match.group(0)  # Return original if can't inline
        
        return re.sub(include_pattern, include_replacer, content)
    
    def _optimize_loops(self, content: str) -> str:
        """Optimize loop constructs"""
        # Add loop caching for expensive iterations
        foreach_pattern = r'@foreach\s*\(\s*(.+?)\s+as\s+(.+?)\s*\)'
        
        def foreach_replacer(match: re.Match[str]) -> str:
            collection = match.group(1)
            variables = match.group(2)
            
            # Add caching hint for large collections
            if 'expensive_' in collection or 'large_' in collection:
                cache_key = hashlib.md5(collection.encode()).hexdigest()[:8]
                return f"{{% set _cached_{cache_key} = {collection} %}}{{% for {variables} in _cached_{cache_key} %}}"
            
            return match.group(0)
        
        return re.sub(foreach_pattern, foreach_replacer, content)
    
    def _cache_expensive_expressions(self, content: str) -> str:
        """Cache expensive template expressions"""
        # Find expressions with function calls or complex operations
        expensive_patterns = [
            r'\{\{\s*([^}]*\([^}]*\)[^}]*)\s*\}\}',  # Function calls
            r'\{\{\s*([^}]*\|[^}]*\|[^}]*)\s*\}\}',   # Multiple filters
        ]
        
        cached_expressions = {}
        
        for pattern in expensive_patterns:
            for match in re.finditer(pattern, content):
                expr = match.group(1)
                if len(expr) > 50:  # Only cache long expressions
                    cache_key = f"_expr_{hashlib.md5(expr.encode()).hexdigest()[:8]}"
                    cached_expressions[match.group(0)] = f"{{{{ {cache_key} or ({expr}) }}}}"
        
        for original, cached in cached_expressions.items():
            content = content.replace(original, cached)
        
        return content
    
    def _precompute_static_expressions(self, content: str) -> str:
        """Precompute expressions that don't depend on runtime data"""
        # This would require more sophisticated analysis
        # For now, just handle simple cases
        
        # Precompute date formatting of static dates
        static_date_pattern = r'\{\{\s*[\'"](\d{4}-\d{2}-\d{2})[\'"]s*\|\s*date\s*\([\'"](.+?)[\'"]\)\s*\}\}'
        
        def date_replacer(match: re.Match[str]) -> str:
            date_str = match.group(1)
            format_str = match.group(2)
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted = date_obj.strftime(format_str)
                return formatted
            except Exception:
                return match.group(0)
        
        return re.sub(static_date_pattern, date_replacer, content)
    
    def _optimize_conditionals(self, content: str) -> str:
        """Optimize conditional statements"""
        # Merge adjacent @if statements with same condition
        pattern = r'(@if\s*\(\s*(.+?)\s*\).*?@endif)\s*(@if\s*\(\s*\2\s*\).*?@endif)'
        
        def merge_conditionals(match: re.Match[str]) -> str:
            first_block = match.group(1)
            condition = match.group(2)
            second_block = match.group(3)
            
            # Extract content from both blocks
            first_content = re.search(r'@if.*?\)(.*?)@endif', first_block, re.DOTALL)
            second_content = re.search(r'@if.*?\)(.*?)@endif', second_block, re.DOTALL)
            
            if first_content and second_content:
                merged = f"@if({condition})\n{first_content.group(1)}\n{second_content.group(1)}\n@endif"
                return merged
            
            return match.group(0)
        
        return re.sub(pattern, merge_conditionals, content, flags=re.DOTALL)
    
    def _bundle_assets(self, content: str) -> str:
        """Bundle asset references for optimization"""
        # Collect all CSS links
        css_links = re.findall(r'<link[^>]*href=[\'"]([^\'"]*\.css)[\'"][^>]*>', content)
        js_scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]*\.js)[\'"][^>]*>', content)
        
        # Replace with bundled versions (placeholder implementation)
        if css_links:
            css_bundle_hash = hashlib.md5(''.join(css_links).encode()).hexdigest()[:8]
            bundle_link = f'<link rel="stylesheet" href="/bundles/css-{css_bundle_hash}.css">'
            
            # Remove individual links and add bundle
            for link in css_links:
                content = re.sub(rf'<link[^>]*href=[\'"][^\'"]*{re.escape(link)}[\'"][^>]*>', '', content)
            
            # Add bundle at first CSS location
            content = re.sub(r'(<head[^>]*>)', rf'\1\n{bundle_link}', content, count=1)
        
        return content


class BladeAdvancedCompiler:
    """Main advanced compiler class"""
    
    def __init__(self, blade_engine: Any) -> None:
        self.blade_engine = blade_engine
        self.minifier = BladeMinifier()
        self.optimizer = BladeOptimizer()
        self.compilation_cache: Dict[str, Tuple[str, float, str]] = {}  # path -> (content, mtime, hash)
    
    def compile_with_features(self, template_content: str, template_path: str, 
                            context: BladeCompilationContext) -> str:
        """Compile template with advanced features"""
        
        # Check cache first
        cache_key = f"{template_path}_{context.environment}_{hash(frozenset(context.features.items()))}"
        
        try:
            mtime = os.path.getmtime(template_path)
            if cache_key in self.compilation_cache:
                cached_content, cached_mtime, cached_hash = self.compilation_cache[cache_key]
                if cached_mtime >= mtime:
                    return cached_content
        except OSError:
            pass
        
        # Apply conditional compilation
        conditional_compiler = ConditionalCompiler(context)
        compiled_content = conditional_compiler.compile_conditionals(template_content)
        
        # Apply standard Blade compilation
        compiled_content = self.blade_engine.compile_blade(compiled_content)
        
        # Apply optimizations
        if context.environment == 'production':
            compiled_content = self.optimizer.optimize_template(compiled_content, template_path)
            compiled_content = self.minifier.minify_html(compiled_content)
        
        # Cache the result
        try:
            mtime = os.path.getmtime(template_path)
            content_hash = hashlib.md5(compiled_content.encode()).hexdigest()
            self.compilation_cache[cache_key] = (compiled_content, mtime, content_hash)
        except OSError:
            pass
        
        return compiled_content
    
    def get_compilation_stats(self) -> Dict[str, Any]:
        """Get compilation statistics"""
        return {
            'cached_templates': len(self.compilation_cache),
            'total_cache_size': sum(len(content) for content, _, _ in self.compilation_cache.values()),
            'optimization_level': self.optimizer.optimization_level,
            'minification_enabled': True
        }
    
    def clear_cache(self) -> None:
        """Clear compilation cache"""
        self.compilation_cache.clear()
    
    def precompile_templates(self, template_paths: List[str], 
                           context: BladeCompilationContext) -> Dict[str, str]:
        """Precompile multiple templates"""
        results = {}
        
        for template_path in template_paths:
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                compiled = self.compile_with_features(content, template_path, context)
                results[template_path] = compiled
                
            except Exception as e:
                results[template_path] = f"Error: {str(e)}"
        
        return results


# Enhanced Blade Engine with advanced compiler integration
class BladeEngineExtended:
    """Extended Blade Engine with advanced compilation features"""
    
    def __init__(self, blade_engine: Any) -> None:
        self.blade_engine = blade_engine
        self.advanced_compiler = BladeAdvancedCompiler(blade_engine)
        self.default_context = BladeCompilationContext()
    
    def render_with_compilation(self, template_name: str, 
                              context: Optional[Dict[str, Any]] = None,
                              compilation_context: Optional[BladeCompilationContext] = None) -> str:
        """Render template with advanced compilation features"""
        
        if context is None:
            context = {}
        
        if compilation_context is None:
            compilation_context = self.default_context
        
        # Find template file
        template_path = self.blade_engine._find_template(template_name)
        
        # Load template content
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Compile with advanced features
        compiled_content = self.advanced_compiler.compile_with_features(
            template_content, template_path, compilation_context
        )
        
        # Create Jinja2 template and render
        template = self.blade_engine.env.from_string(compiled_content)
        
        # Merge contexts
        final_context = {**self.blade_engine.shared_data, **context}
        service_context = self.blade_engine.service_provider.get_template_context()
        final_context.update(service_context)
        
        result = template.render(**final_context)
        return str(result) if result is not None else ""
    
    def set_environment(self, environment: str) -> None:
        """Set compilation environment"""
        self.default_context.environment = environment
    
    def set_features(self, features: Dict[str, bool]) -> None:
        """Set feature flags for compilation"""
        self.default_context.features = features
    
    def enable_optimization(self, level: int = 2) -> None:
        """Enable template optimization"""
        self.advanced_compiler.optimizer.optimization_level = level
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compilation and performance statistics"""
        return self.advanced_compiler.get_compilation_stats()