#!/usr/bin/env python3
"""
Type checking script for the FastAPI Laravel project.
Runs mypy with strict settings and reports results.
"""

import subprocess
import sys
from typing import List, Tuple
from pathlib import Path


def run_mypy() -> Tuple[int, str, str]:
    """Run mypy type checking."""
    cmd: List[str] = [
        "mypy",
        "--config-file=mypy.ini",
        ".",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Mypy timed out after 5 minutes"
    except FileNotFoundError:
        return 1, "", "Mypy not found. Please install mypy: pip install mypy"


def run_type_coverage() -> None:
    """Check type coverage using mypy."""
    print("🔍 Running type coverage analysis...")
    
    cmd: List[str] = [
        "mypy",
        "--config-file=mypy.ini",
        "--html-report=type_coverage",
        ".",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("✅ Type coverage report generated in 'type_coverage/' directory")
        else:
            print("⚠️  Type coverage report generated with some issues")
    except subprocess.TimeoutExpired:
        print("⏰ Type coverage analysis timed out")
    except FileNotFoundError:
        print("❌ Mypy not found for type coverage analysis")


def main() -> int:
    """Main entry point."""
    print("🎯 Starting strict type checking for FastAPI Laravel project...")
    print("=" * 60)
    
    # Run mypy type checking
    returncode, stdout, stderr = run_mypy()
    
    if returncode == 0:
        print("✅ All type checks passed!")
        print(stdout if stdout else "No output from mypy")
        
        # Run type coverage analysis
        run_type_coverage()
        
        print("\n🎉 Type checking completed successfully!")
        return 0
    else:
        print("❌ Type checking failed!")
        print("\nSTDOUT:")
        print(stdout)
        
        if stderr:
            print("\nSTDERR:")
            print(stderr)
        
        print(f"\n💡 Fix the type issues above and run again.")
        print("   For help with mypy errors, see: https://mypy.readthedocs.io/")
        
        return returncode


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)