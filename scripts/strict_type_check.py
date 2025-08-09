#!/usr/bin/env python3
"""
Enhanced type checking script for FastAPI Laravel with better error reporting.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_mypy_on_modules() -> bool:
    """Run mypy on critical modules with enhanced reporting."""
    
    # Critical modules that should have strict typing
    core_modules = [
        "app/Services",
        "app/Models", 
        "app/Http/Controllers",
        "app/Http/Requests",
        "app/Http/Resources",
        "app/Http/Schemas", 
        "app/Utils",
        "app/Cache",
        "app/Queue",
        "app/Jobs"
    ]
    
    print("🎯 Enhanced strict type checking for FastAPI Laravel...")
    print("=" * 60)
    
    total_errors = 0
    failed_modules = []
    
    for module in core_modules:
        if not Path(module).exists():
            print(f"⚠️  Module {module} not found, skipping...")
            continue
            
        print(f"\n📂 Checking {module}...")
        
        cmd = [
            "mypy", 
            "--strict",
            "--config-file=mypy.ini",
            "--show-error-codes",
            "--show-column-numbers", 
            "--color-output",
            "--pretty",
            "--show-absolute-path",
            module
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {module} - Type checking passed!")
        else:
            print(f"❌ {module} - Found type errors:")
            
            # Count errors
            error_lines = [line for line in result.stdout.split('\n') if 'error:' in line]
            module_errors = len(error_lines)
            total_errors += module_errors
            failed_modules.append(module)
            
            # Show first few errors
            print(result.stdout[:1000] + ("..." if len(result.stdout) > 1000 else ""))
            
            if stderr := result.stderr:
                print(f"STDERR: {stderr}")
    
    print(f"\n{'='*60}")
    print(f"📊 Type checking summary:")
    print(f"   Total errors: {total_errors}")
    print(f"   Failed modules: {len(failed_modules)}")
    
    if failed_modules:
        print(f"   Modules with errors: {', '.join(failed_modules)}")
        print(f"\n💡 Focus on fixing these modules first:")
        for module in failed_modules[:3]:  # Show top 3
            print(f"   • {module}")
    else:
        print("🎉 All core modules passed strict type checking!")
    
    return total_errors == 0


def main() -> int:
    """Main entry point."""
    
    if not Path("mypy.ini").exists():
        print("❌ mypy.ini configuration file not found!")
        return 1
        
    success = run_mypy_on_modules()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())