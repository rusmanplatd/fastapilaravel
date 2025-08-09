#!/usr/bin/env python3
from __future__ import annotations

"""
Advanced type checking script with progressive strictness levels.
Allows testing different levels of mypy strictness incrementally.
"""

import subprocess
import sys
import argparse
from typing import List, Tuple, Dict, Any
from pathlib import Path
import tempfile
import shutil


class TypeChecker:
    """Advanced type checker with multiple strictness levels."""
    
    def __init__(self, config_file: str = "mypy.ini"):
        self.config_file = config_file
        self.base_config = self._load_base_config()
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base mypy configuration."""
        return {
            "python_version": "3.12",
            "strict": True,
            "warn_return_any": True,
            "warn_unused_configs": True,
            "warn_redundant_casts": True,
            "warn_unused_ignores": True,
            "show_error_codes": True,
            "show_column_numbers": True,
            "pretty": True,
        }
    
    def create_strictness_config(self, level: str) -> str:
        """Create temporary config file with specified strictness level."""
        configs = {
            "minimal": {
                **self.base_config,
                "strict": False,
                "disallow_untyped_defs": True,
                "disallow_incomplete_defs": True,
            },
            "moderate": {
                **self.base_config,
                "strict": True,
                "disallow_any_generics": True,
                "disallow_untyped_defs": True,
                "disallow_incomplete_defs": True,
                "disallow_untyped_decorators": True,
            },
            "strict": {
                **self.base_config,
                "strict": True,
                "disallow_any_generics": True,
                "disallow_any_unimported": True,
                "disallow_any_decorated": True,
                "disallow_untyped_defs": True,
                "disallow_incomplete_defs": True,
                "disallow_untyped_decorators": True,
                "disallow_untyped_calls": True,
                "no_implicit_optional": True,
                "strict_optional": True,
                "strict_equality": True,
            },
            "extreme": {
                **self.base_config,
                "strict": True,
                "disallow_any_generics": True,
                "disallow_any_unimported": True,
                "disallow_any_decorated": True,
                "disallow_any_explicit": True,
                "disallow_any_expr": True,
                "disallow_untyped_defs": True,
                "disallow_incomplete_defs": True,
                "disallow_untyped_decorators": True,
                "disallow_untyped_calls": True,
                "disallow_subclassing_any": True,
                "no_implicit_optional": True,
                "no_implicit_reexport": True,
                "strict_optional": True,
                "strict_equality": True,
                "strict_concatenate": True,
                "local_partial_types": True,
                "extra_checks": True,
            }
        }
        
        config = configs.get(level, configs["strict"])
        
        # Create temporary config file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False)
        temp_file.write("[mypy]\n")
        
        for key, value in config.items():
            if isinstance(value, bool):
                temp_file.write(f"{key} = {str(value).lower()}\n")
            else:
                temp_file.write(f"{key} = {value}\n")
        
        # Add third-party library ignores
        temp_file.write("\n# Third-party libraries\n")
        libraries = [
            "sqlalchemy.*", "passlib.*", "jose.*", "uvicorn.*", "pytest.*",
            "fastapi.*", "starlette.*", "pydantic.*", "redis.*", "celery.*",
            "alembic.*", "email_validator.*", "bcrypt.*", "cryptography.*",
            "webauthn.*", "pyotp.*", "qrcode.*", "PIL.*"
        ]
        
        for lib in libraries:
            temp_file.write(f"\n[mypy-{lib}]\nignore_missing_imports = true\n")
        
        temp_file.close()
        return temp_file.name
    
    def run_mypy_with_config(self, config_path: str, target: str = ".") -> Tuple[int, str, str]:
        """Run mypy with specified config file."""
        cmd: List[str] = [
            "mypy",
            f"--config-file={config_path}",
            "--exclude=examples",
            "--exclude=tests",
            target,
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Mypy timed out after 5 minutes"
        except FileNotFoundError:
            return 1, "", "Mypy not found. Please install mypy: pip install mypy"
    
    def run_progressive_check(self, target: str = ".") -> Dict[str, Tuple[int, str, str]]:
        """Run type checking with progressive strictness levels."""
        levels = ["minimal", "moderate", "strict", "extreme"]
        results = {}
        
        for level in levels:
            print(f"\n🔍 Running {level.upper()} type checking...")
            print("=" * 50)
            
            config_path = self.create_strictness_config(level)
            try:
                returncode, stdout, stderr = self.run_mypy_with_config(config_path, target)
                results[level] = (returncode, stdout, stderr)
                
                if returncode == 0:
                    print(f"✅ {level.upper()} level passed!")
                else:
                    print(f"❌ {level.upper()} level failed with {len(stdout.splitlines())} errors")
                    
            finally:
                # Clean up temporary config file
                Path(config_path).unlink(missing_ok=True)
        
        return results
    
    def analyze_module(self, module_path: str, strictness: str = "strict") -> Tuple[int, str, str]:
        """Analyze a specific module with given strictness."""
        print(f"🎯 Analyzing module: {module_path} with {strictness} strictness...")
        
        config_path = self.create_strictness_config(strictness)
        try:
            return self.run_mypy_with_config(config_path, module_path)
        finally:
            Path(config_path).unlink(missing_ok=True)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Advanced mypy type checking")
    parser.add_argument(
        "--level", 
        choices=["minimal", "moderate", "strict", "extreme"],
        default="strict",
        help="Type checking strictness level"
    )
    parser.add_argument(
        "--progressive", 
        action="store_true",
        help="Run progressive type checking (all levels)"
    )
    parser.add_argument(
        "--module",
        help="Specific module to check (e.g., app/Http/Controllers)"
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Target directory to check (default: current directory)"
    )
    
    args = parser.parse_args()
    
    checker = TypeChecker()
    
    if args.progressive:
        print("🚀 Running progressive type checking...")
        results = checker.run_progressive_check(args.target)
        
        print("\n" + "=" * 60)
        print("📊 PROGRESSIVE TYPE CHECKING SUMMARY")
        print("=" * 60)
        
        for level, (returncode, stdout, stderr) in results.items():
            status = "✅ PASSED" if returncode == 0 else "❌ FAILED"
            error_count = len([line for line in stdout.splitlines() if ": error:" in line])
            print(f"{level.upper():>8}: {status} ({error_count} errors)")
        
        # Find the highest passing level
        passing_levels = [level for level, (code, _, _) in results.items() if code == 0]
        if passing_levels:
            print(f"\n🎉 Highest passing level: {passing_levels[-1].upper()}")
        else:
            print("\n⚠️  No levels passed completely")
            
        return min(code for code, _, _ in results.values())
    
    elif args.module:
        returncode, stdout, stderr = checker.analyze_module(args.module, args.level)
        print(stdout)
        if stderr:
            print(stderr)
        return returncode
    
    else:
        config_path = checker.create_strictness_config(args.level)
        try:
            returncode, stdout, stderr = checker.run_mypy_with_config(config_path, args.target)
            print(stdout)
            if stderr:
                print(stderr)
            return returncode
        finally:
            Path(config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())