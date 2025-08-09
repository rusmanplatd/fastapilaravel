#!/usr/bin/env python3
"""
Laravel-style Artisan Console Application

This is the main entry point for the Artisan console application.
It provides a Laravel-like command-line interface for managing your FastAPI application.

Usage:
    python artisan.py <command> [options] [arguments]
    python artisan.py list
    python artisan.py help <command>

Examples:
    python artisan.py make:controller UserController --resource
    python artisan.py migrate
    python artisan.py queue:work
    python artisan.py schedule:run
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main() -> int:
    """Main entry point for the Artisan console."""
    try:
        # Handle version command
        if len(sys.argv) == 2 and sys.argv[1] in ['--version', '-V']:
            print("FastAPI Laravel-Style Framework")
            print("Artisan Console Tool v2.0.0")
            return 0
        
        # Use the new Laravel-style Artisan kernel
        from app.Console.Artisan import kernel
        return kernel.handle()
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Artisan error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())