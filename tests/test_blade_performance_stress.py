"""
Test Suite for Blade Engine Performance and Stress Testing
Tests caching, large templates, memory usage, and concurrent access
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
import time
import threading
from pathlib import Path
from typing import Dict, Any, Generator, Tuple, List
import os
import concurrent.futures

from app.View.BladeEngine import BladeEngine


class TestBladePerformance:
    """Test performance characteristics of Blade engine"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=False)  # Disable debug for performance
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_large_template_rendering(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test rendering of large templates"""
        engine, temp_dir = blade_engine
        
        # Generate a large template with many sections
        template_parts = []
        template_parts.append("@extends('base')")
        
        # Add many sections
        for i in range(100):
            template_parts.append(f"@section('section_{i}')")
            template_parts.append(f"<div class='section-{i}'>")
            template_parts.append("@for($j = 0; $j < 50; $j++)")
            template_parts.append(f"<p>Section {i}, Item {{{{ $j }}}}: {{{{ data.item_{i} }}</p>")
            template_parts.append("@endfor")
            template_parts.append("</div>")
            template_parts.append("@endsection")
        
        large_template = "\n".join(template_parts)
        
        # Create base template
        base_template = """
<!DOCTYPE html>
<html>
<head><title>Large Template Test</title></head>
<body>
""" + "\n".join([f"@yield('section_{i}')" for i in range(100)]) + """
</body>
</html>
        """
        
        self.create_template(temp_dir, "base.blade.html", base_template)
        self.create_template(temp_dir, "large.blade.html", large_template)
        
        # Create context data
        context = {}
        for i in range(100):
            context[f'data.item_{i}'] = f'Value for item {i}'
        
        # Measure rendering time
        start_time = time.time()
        result = engine.render("large.blade.html", context)
        end_time = time.time()
        
        render_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert render_time < 5.0, f"Rendering took {render_time:.2f} seconds, which is too slow"
        assert len(result) > 1000, "Rendered result should be substantial"
    
    def test_template_caching_performance(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test template caching performance benefits"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    @foreach(items as item)
        <p>Item: {{ item.name }} - {{ item.value }}</p>
    @endforeach
</div>
        """.strip()
        
        self.create_template(temp_dir, "cached_perf.blade.html", template_content)
        
        # Create test data
        items = [{"name": f"Item {i}", "value": f"Value {i}"} for i in range(1000)]
        context = {"items": items}
        
        # First render (cold start)
        start_time = time.time()
        result1 = engine.render("cached_perf.blade.html", context)
        first_render_time = time.time() - start_time
        
        # Second render (should benefit from internal Jinja2 caching)
        start_time = time.time()
        result2 = engine.render("cached_perf.blade.html", context)
        second_render_time = time.time() - start_time
        
        # Results should be identical
        assert result1 == result2
        
        # Second render should generally be faster (though this can vary)
        # We mainly check that both renders complete in reasonable time
        assert first_render_time < 2.0, f"First render too slow: {first_render_time:.2f}s"
        assert second_render_time < 2.0, f"Second render too slow: {second_render_time:.2f}s"
    
    def test_memory_usage_with_large_context(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test memory usage with very large context data"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <h1>Memory Test</h1>
    <p>Users count: {{ users|length }}</p>
    <p>Products count: {{ products|length }}</p>
    
    @if(users|length > 0)
        <p>First user: {{ users[0].name }}</p>
    @endif
    
    @if(products|length > 0)
        <p>First product: {{ products[0].title }}</p>
    @endif
</div>
        """.strip()
        
        self.create_template(temp_dir, "memory_test.blade.html", template_content)
        
        # Create large context data (simulate database results)
        users = []
        for i in range(10000):
            users.append({
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "profile": {
                    "bio": f"This is the bio for user {i}. " * 10,
                    "settings": {"theme": "dark", "notifications": True},
                    "metadata": {"created_at": "2024-01-01", "updated_at": "2024-01-02"}
                }
            })
        
        products = []
        for i in range(5000):
            products.append({
                "id": i,
                "title": f"Product {i}",
                "description": f"Description for product {i}. " * 20,
                "specs": {"weight": f"{i}g", "dimensions": f"{i}x{i}x{i}cm"},
                "reviews": [f"Review {j} for product {i}" for j in range(10)]
            })
        
        context = {
            "users": users,
            "products": products
        }
        
        # Render with large context
        start_time = time.time()
        result = engine.render("memory_test.blade.html", context)
        render_time = time.time() - start_time
        
        assert "Users count: 10000" in result
        assert "Products count: 5000" in result
        assert "User 0" in result
        assert "Product 0" in result
        
        # Should complete in reasonable time even with large data
        assert render_time < 3.0, f"Large context rendering took {render_time:.2f} seconds"
    
    def test_deep_nested_template_inheritance(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test performance with deeply nested template inheritance"""
        engine, temp_dir = blade_engine
        
        # Create a chain of templates: child -> parent1 -> parent2 -> ... -> base
        base_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title', 'Default Title')</title>
</head>
<body>
    <header>@yield('header', 'Default Header')</header>
    <main>@yield('content', 'Default Content')</main>
    <footer>@yield('footer', 'Default Footer')</footer>
</body>
</html>
        """.strip()
        
        self.create_template(temp_dir, "base.blade.html", base_content)
        
        # Create intermediate templates
        for i in range(10):
            if i == 0:
                parent_template = "@extends('base')\n"
            else:
                parent_template = f"@extends('parent_{i-1}')\n"
            
            parent_template += f"""
@section('title')
    Level {i} - @parent
@endsection

@section('content')
    <div class="level-{i}">
        <h{i+1}>Level {i}</h{i+1}>
        @parent
    </div>
@endsection
            """.strip()
            
            self.create_template(temp_dir, f"parent_{i}.blade.html", parent_template)
        
        # Create final child template
        child_template = """
@extends('parent_9')

@section('title')
    Final Child - @parent
@endsection

@section('content')
    <div class="final-child">
        <p>This is the final child content</p>
        @parent
    </div>
@endsection
        """.strip()
        
        self.create_template(temp_dir, "child.blade.html", child_template)
        
        # Render the deeply nested template
        start_time = time.time()
        result = engine.render("child.blade.html")
        render_time = time.time() - start_time
        
        # Verify content is properly inherited
        assert "Final Child" in result
        assert "Level 9" in result
        assert "Level 0" in result
        assert "final-child" in result
        
        # Should handle deep nesting efficiently
        assert render_time < 1.0, f"Deep nesting render took {render_time:.2f} seconds"


class TestBladeConcurrency:
    """Test concurrent access and thread safety"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=False)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_concurrent_template_rendering(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test concurrent rendering of the same template"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <h1>Thread ID: {{ thread_id }}</h1>
    <p>Value: {{ value }}</p>
    @foreach(items as item)
        <span>{{ item }}</span>
    @endforeach
</div>
        """.strip()
        
        self.create_template(temp_dir, "concurrent.blade.html", template_content)
        
        results = []
        errors = []
        
        def render_template(thread_id: int) -> None:
            try:
                context = {
                    "thread_id": thread_id,
                    "value": f"Value from thread {thread_id}",
                    "items": [f"Item {i} from thread {thread_id}" for i in range(10)]
                }
                
                result = engine.render("concurrent.blade.html", context)
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=render_template, args=(i,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10, "Not all threads completed successfully"
        
        # Check that each thread got its own data
        for thread_id, result in results:
            assert f"Thread ID: {thread_id}" in result
            assert f"Value from thread {thread_id}" in result
            assert f"Item 0 from thread {thread_id}" in result
        
        # Should complete reasonably quickly
        total_time = end_time - start_time
        assert total_time < 5.0, f"Concurrent rendering took {total_time:.2f} seconds"
    
    def test_concurrent_different_templates(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test concurrent rendering of different templates"""
        engine, temp_dir = blade_engine
        
        # Create multiple templates
        templates = {
            "template_a.blade.html": "<h1>Template A: {{ value }}</h1>",
            "template_b.blade.html": "<h2>Template B: {{ value }}</h2>", 
            "template_c.blade.html": "<h3>Template C: {{ value }}</h3>",
        }
        
        for name, content in templates.items():
            self.create_template(temp_dir, name, content)
        
        results = []
        errors = []
        
        def render_random_template(worker_id: int) -> None:
            try:
                template_names = list(templates.keys())
                template_name = template_names[worker_id % len(template_names)]
                
                context = {"value": f"Worker {worker_id}"}
                result = engine.render(template_name, context)
                results.append((worker_id, template_name, result))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Use ThreadPoolExecutor for better control
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(15):  # More workers than templates
                future = executor.submit(render_random_template, i)
                futures.append(future)
            
            # Wait for completion
            concurrent.futures.wait(futures, timeout=10)
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 15, "Not all workers completed successfully"
        
        # Verify content correctness
        for worker_id, template_name, result in results:
            assert f"Worker {worker_id}" in result
            if "template_a" in template_name:
                assert "<h1>" in result
            elif "template_b" in template_name:
                assert "<h2>" in result
            elif "template_c" in template_name:
                assert "<h3>" in result
    
    def test_shared_data_thread_safety(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test thread safety of shared data"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>Shared: {{ shared_value }}</p>
    <p>Local: {{ local_value }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "shared_data.blade.html", template_content)
        
        # Set initial shared data
        engine.share("shared_value", "Initial shared value")
        
        results = []
        errors = []
        
        def worker_with_shared_data(worker_id: int) -> None:
            try:
                # Each worker tries to update shared data
                engine.share("shared_value", f"Shared by worker {worker_id}")
                
                context = {"local_value": f"Local to worker {worker_id}"}
                result = engine.render("shared_data.blade.html", context)
                results.append((worker_id, result))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_with_shared_data, args=(i,))
            threads.append(thread)
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, "Not all workers completed"
        
        # Verify each worker got some shared value (order is non-deterministic)
        for worker_id, result in results:
            assert "Shared by worker" in result
            assert f"Local to worker {worker_id}" in result


class TestBladeStressTests:
    """Stress tests for Blade engine limits"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=False)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    @pytest.mark.slow
    def test_many_template_files(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test handling of many template files"""
        engine, temp_dir = blade_engine
        
        # Create many template files
        template_count = 100
        for i in range(template_count):
            template_content = f"""
<div class="template-{i}">
    <h1>Template {i}</h1>
    <p>{{{{ message }}</p>
    
    @if(include_next and {i} < {template_count - 1})
        @include('template_{i + 1}')
    @endif
</div>
            """.strip()
            
            self.create_template(temp_dir, f"template_{i}.blade.html", template_content)
        
        # Render a template that might include others
        start_time = time.time()
        result = engine.render("template_0.blade.html", {
            "message": "Hello from template 0",
            "include_next": False  # Don't trigger recursive includes
        })
        render_time = time.time() - start_time
        
        assert "Template 0" in result
        assert "Hello from template 0" in result
        
        # Should handle many files efficiently
        assert render_time < 2.0, f"Many templates test took {render_time:.2f} seconds"
    
    @pytest.mark.slow 
    def test_rapid_sequential_renders(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test rapid sequential renders of the same template"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <h1>Rapid Test {{ counter }}</h1>
    <p>{{ message }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "rapid.blade.html", template_content)
        
        # Perform many rapid renders
        render_count = 1000
        start_time = time.time()
        
        for i in range(render_count):
            context = {
                "counter": i,
                "message": f"Message number {i}"
            }
            result = engine.render("rapid.blade.html", context)
            
            # Spot check some results
            if i % 100 == 0:
                assert f"Rapid Test {i}" in result
                assert f"Message number {i}" in result
        
        total_time = time.time() - start_time
        avg_time = total_time / render_count
        
        # Should maintain good performance
        assert total_time < 10.0, f"Rapid renders took {total_time:.2f} seconds total"
        assert avg_time < 0.01, f"Average render time was {avg_time:.4f} seconds"
    
    def test_cache_invalidation_stress(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test cache behavior under stress"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>Template version: {{ version }}</p>
    <p>Current time: {{ timestamp }}</p>
</div>
        """.strip()
        
        template_path = Path(temp_dir) / "cache_stress.blade.html"
        
        results = []
        
        # Repeatedly modify template and render
        for i in range(20):
            # Modify template content
            modified_content = template_content.replace("Template version", f"Template version {i}")
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            # Small delay to ensure file modification time changes
            time.sleep(0.01)
            
            # Render multiple times
            for j in range(5):
                context = {
                    "version": i,
                    "timestamp": time.time()
                }
                result = engine.render("cache_stress.blade.html", context)
                results.append((i, j, result))
        
        # Verify results contain expected modifications
        for version, render_num, result in results:
            if version > 0:  # Skip first version
                assert f"Template version {version}" in result
            assert f"Template version: {version}" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])