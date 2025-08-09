from __future__ import annotations

import re
from typing import Match

content = """
@can('edit-post')
    <button>Edit Post</button>
@endcan

@cannot('delete-post')
    <p>You cannot delete this post</p>
@endcannot
""".strip()

print("Original content:")
print(content)
print()

# Test the regex pattern used in the engine
pattern = r"@cannot(?:\s*\(\s*(.+?)\s*\))?"
matches = re.findall(pattern, content)
print("Matches for @cannot pattern:")
print(matches)

# Test with re.sub
def debug_replacer(m: Match[str]) -> str:
    print(f"Match: {m.group(0)}, Group 1: {m.group(1) if m.group(1) else 'None'}")
    return "REPLACED"

result = re.sub(pattern, debug_replacer, content)
print("\nAfter replacement:")
print(result)