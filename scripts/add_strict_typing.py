#!/usr/bin/env python3
"""
Script to add strict typing to all Python files in the FastAPI Laravel project.
This script adds 'from __future__ import annotations' to Python files that don't have it.
"""

import os
import re
from pathlib import Path
from typing import List, Set


def has_future_annotations(file_path: Path) -> bool:
    """Check if file already has 'from __future__ import annotations'."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return 'from __future__ import annotations' in content
    except (UnicodeDecodeError, PermissionError):
        return True  # Skip files we can't read


def is_valid_python_file(file_path: Path) -> bool:
    """Check if this is a valid Python file that needs annotations."""
    # Skip if it's in venv, __pycache__, .git, or is a test file
    exclude_dirs = {'venv', '__pycache__', '.git', 'node_modules', '.mypy_cache'}
    
    for part in file_path.parts:
        if part in exclude_dirs:
            return False
    
    # Skip test files, migration files with numbers, and __init__.py files that are just imports
    if (file_path.name.startswith('test_') or 
        re.match(r'^\d{4}_\d{2}_\d{2}_', file_path.name) or
        file_path.name == '__init__.py'):
        return False
    
    return True


def needs_annotations(file_path: Path) -> bool:
    """Check if file needs to be updated with annotations."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
            # Skip empty files or files with just imports/docstrings
            if len(content) < 50:
                return False
                
            # Skip files that are just dynamic imports
            if 'importlib.import_module' in content and len(content.split('\n')) < 10:
                return False
                
            # Skip if already has annotations
            if 'from __future__ import annotations' in content:
                return False
                
            # Check if file has type annotations that would benefit
            type_indicators = [
                'typing.', 'List[', 'Dict[', 'Optional[', 'Union[', 'Callable[',
                '-> ', ': str', ': int', ': bool', ': float', ': Any',
                'from typing import', 'def ', 'class ', 'async def'
            ]
            
            return any(indicator in content for indicator in type_indicators)
            
    except (UnicodeDecodeError, PermissionError):
        return False


def add_future_annotations(file_path: Path) -> bool:
    """Add 'from __future__ import annotations' to the file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Find the insertion point (after shebang and encoding declarations)
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith('#!') or line.startswith('# -*- coding:') or line.startswith('# coding:'):
                insert_index = i + 1
            elif line.strip() == '' and i < 3:  # Allow empty lines at the top
                continue
            else:
                break
        
        # Insert the future import
        future_import = 'from __future__ import annotations'
        
        # Check if there are already imports to group with
        has_imports = False
        for line in lines[insert_index:insert_index + 5]:
            if line.startswith('from ') or line.startswith('import '):
                has_imports = True
                break
        
        if has_imports:
            lines.insert(insert_index, future_import)
            lines.insert(insert_index + 1, '')
        else:
            # Add with spacing
            lines.insert(insert_index, future_import)
            lines.insert(insert_index + 1, '')
        
        # Write back to file
        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return True
        
    except (UnicodeDecodeError, PermissionError) as e:
        print(f"Error updating {file_path}: {e}")
        return False


def main() -> None:
    """Main function to process all Python files."""
    project_root = Path(__file__).parent.parent
    print(f"🎯 Adding strict typing to FastAPI Laravel project at {project_root}")
    print("=" * 60)
    
    updated_files: List[Path] = []
    skipped_files: List[Path] = []
    
    # Find all Python files
    python_files = list(project_root.rglob("*.py"))
    
    for file_path in python_files:
        if not is_valid_python_file(file_path):
            continue
            
        if needs_annotations(file_path):
            if add_future_annotations(file_path):
                updated_files.append(file_path)
                print(f"✅ Updated: {file_path.relative_to(project_root)}")
            else:
                skipped_files.append(file_path)
                print(f"❌ Failed: {file_path.relative_to(project_root)}")
        else:
            print(f"⏭️  Skipped: {file_path.relative_to(project_root)} (no annotations needed)")
    
    print("\n" + "=" * 60)
    print(f"📊 Summary:")
    print(f"   ✅ Updated: {len(updated_files)} files")
    print(f"   ❌ Failed:  {len(skipped_files)} files")
    print(f"   📁 Total processed: {len([f for f in python_files if is_valid_python_file(f)])} files")
    
    if updated_files:
        print(f"\n🔧 Next steps:")
        print(f"   1. Run 'make type-check' to identify remaining type issues")
        print(f"   2. Fix any type errors revealed by the stricter checking")
        print(f"   3. Run 'make format' to ensure consistent formatting")


if __name__ == "__main__":
    main()