from __future__ import annotations
from app.View.BladeEngine import BladeEngine
import tempfile
from pathlib import Path
from typing import Any

temp_dir = tempfile.mkdtemp()

content = """
@can('edit-post')
    <button>Edit Post</button>
@endcan

@cannot('delete-post')
    <p>You cannot delete this post</p>
@endcannot
""".strip()

template_path = Path(temp_dir) / "can.blade.html"
with open(template_path, 'w') as f:
    f.write(content)

engine = BladeEngine([temp_dir], debug=True)

print("=== Original Template ===")
print(content)

print("\n=== Compiled Template ===")
compiled = engine.compile_blade(content)
print(compiled)

class MockUser:
    def can(self, permission: str) -> bool:
        print(f"MockUser.can('{permission}') -> {permission == 'edit-post'}")
        return permission == 'edit-post'

print("\n=== Rendered Result ===")
result = engine.render("can.blade.html", {"current_user": MockUser()})
print(repr(result))
print(result)