from app.View.BladeEngine import BladeEngine
import tempfile
from pathlib import Path

# Create temporary directory
temp_dir = tempfile.mkdtemp()

# Create layout template
layout_content = """
<!DOCTYPE html>
<html>
<head>
    <title>@yield('title')</title>
</head>
<body>
    @yield('content')
</body>
</html>
""".strip()

layout_path = Path(temp_dir) / "layout.blade.html"
with open(layout_path, 'w') as f:
    f.write(layout_content)

# Create child template
child_content = """
@extends('layout')

@section('title', 'Test Page')

@section('content')
    <h1>This is the content</h1>
@endsection
""".strip()

child_path = Path(temp_dir) / "child.blade.html"
with open(child_path, 'w') as f:
    f.write(child_content)

# Test compilation
engine = BladeEngine([temp_dir], debug=True)

print("=== Layout Template ===")
print(layout_content)
print("\n=== Layout Compiled ===")
compiled_layout = engine.compile_blade(layout_content)
print(compiled_layout)

print("\n=== Child Template ===")
print(child_content)
print("\n=== Child Compiled ===")
compiled_child = engine.compile_blade(child_content)
print(compiled_child)

print("\n=== Rendered Result ===")
try:
    result = engine.render("child.blade.html")
    print(result)
except Exception as e:
    print(f"Error: {e}")