#!/usr/bin/env python3
"""
Script to clean up unused type: ignore comments.
"""
from __future__ import annotations

import subprocess
import re
from pathlib import Path
from typing import Dict, List


def clean_unused_ignores() -> None:
    """Remove unused type: ignore comments."""
    
    # Get list of unused ignore errors
    result = subprocess.run([
        "mypy", "--strict", "--config-file=mypy.ini", "app/"
    ], capture_output=True, text=True)
    
    unused_ignores = []
    for line in result.stdout.split('\n'):
        if 'unused-ignore' in line:
            # Parse file and line number
            match = re.match(r'([^:]+):(\d+):', line)
            if match:
                file_path, line_num = match.groups()
                unused_ignores.append((Path(file_path), int(line_num)))
    
    print(f"Found {len(unused_ignores)} unused type ignore comments")
    
    # Group by file
    files_to_fix: Dict[Path, List[int]] = {}
    for file_path, line_num in unused_ignores:
        if file_path not in files_to_fix:
            files_to_fix[file_path] = []
        files_to_fix[file_path].append(line_num)
    
    # Fix each file
    for file_path, line_numbers in files_to_fix.items():
        if file_path.exists():
            print(f"Cleaning {file_path}...")
            
            lines = file_path.read_text().splitlines()
            
            # Sort line numbers in reverse order to avoid index issues
            for line_num in sorted(line_numbers, reverse=True):
                if line_num <= len(lines):
                    line = lines[line_num - 1]  # Convert to 0-based index
                    
                    # Remove type: ignore comments
                    cleaned_line = re.sub(r'\s*#\s*type:\s*ignore\[[\w-]+\]', '', line)
                    cleaned_line = re.sub(r'\s*#\s*type:\s*ignore', '', cleaned_line)
                    
                    lines[line_num - 1] = cleaned_line
            
            # Write back to file
            file_path.write_text('\n'.join(lines) + '\n')
            print(f"✅ Cleaned {len(line_numbers)} unused ignores in {file_path}")


if __name__ == "__main__":
    clean_unused_ignores()