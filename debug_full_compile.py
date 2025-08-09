from __future__ import annotations
from app.View.BladeEngine import BladeEngine
import re
from typing import Any

content = """@cannot('delete-post')
    <p>You cannot delete this post</p>
@endcannot"""

engine = BladeEngine(['/tmp'], debug=True)

print("=== Original ===")
print(content)
print()

# Step-by-step compilation process
template_content = content

print("=== Step 1: Handle @extends ===")
# Handle @extends
def fix_extends_path(match: Any) -> str:
    template_name = match.group(1)
    if not template_name.endswith('.blade.html'):
        template_name += '.blade.html'
    return f"{{% extends '{template_name}' %}}"

template_content = re.sub(
    r"@extends\s*\(\s*['\"](.+?)['\"]s*\)",
    fix_extends_path,
    template_content
)
print(template_content)
print()

print("=== Step 2: Handle @section and @endsection ===")
template_content = re.sub(
    r"@section\s*\(\s*['\"](.+?)['\"]s*,\s*['\"](.+?)['\"]s*\)",
    r"{% block \1 %}\2{% endblock %}",
    template_content
)
template_content = re.sub(
    r"@section\s*\(\s*['\"](.+?)['\"]s*\)",
    r"{% block \1 %}",
    template_content
)
template_content = template_content.replace("@endsection", "{% endblock %}")
print(template_content)
print()

print("=== Step 3: Handle @yield ===")
template_content = re.sub(
    r"@yield\s*\(\s*['\"](.+?)['\"]s*\)",
    r"{% block \1 %}{% endblock %}",
    template_content
)
print(template_content)
print()

print("=== Step 4: Handle @parent ===")
template_content = template_content.replace("@parent", "{{ super() }}")
print(template_content)
print()

print("=== Step 5: Handle @if, @elseif, @else, @endif ===")
template_content = re.sub(r"@if\s*\(\s*(.+?)\s*\)", r"{% if \1 %}", template_content)
template_content = re.sub(r"@elseif\s*\(\s*(.+?)\s*\)", r"{% elif \1 %}", template_content)
template_content = template_content.replace("@else", "{% else %}")
template_content = template_content.replace("@endif", "{% endif %}")
print(template_content)
print()

print("=== Step 6: Handle custom directives ===")
for name, directive in engine.directives.items():
    print(f"Processing directive: {name}")
    pattern = rf"@{name}(?:\s*\(\s*(.+?)\s*\))?"
    def make_replacer(callback: Any) -> Any:
        return lambda m: callback(m.group(1) or '')
    
    old_content = template_content
    template_content = re.sub(
        pattern,
        make_replacer(directive.callback),
        template_content
    )
    if old_content != template_content:
        print(f"  Changed by {name}:")
        print(f"  {template_content}")
    print()

print("=== Final Result ===")
print(template_content)