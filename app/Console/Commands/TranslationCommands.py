"""
Laravel-style Artisan Commands for Translation Management
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
from argparse import ArgumentParser
import argparse

from app.Localization.TranslationManager import translation_manager
from app.Localization.LocaleManager import locale_manager
from app.Console.Command import Command


class MakeLocaleCommand(Command):
    """Create new locale translation files"""
    
    signature = "make:locale"
    description = "Create translation files for a new locale"
    
    async def handle(self) -> None:
        """Handle the command"""
        # Get locale from arguments
        parser = ArgumentParser(description=self.description)
        parser.add_argument('locale', help='Locale code (e.g., es, fr, de)')
        parser.add_argument('--copy-from', help='Copy translations from existing locale')
        parser.add_argument('--force', action='store_true', help='Overwrite existing files')
        
        args = parser.parse_args(sys.argv[2:])
        
        locale = args.locale
        copy_from = args.copy_from
        force = args.force
        
        # Validate locale code
        if not locale_manager.validator.is_valid_locale_code(locale):
            self.error(f"Invalid locale code: {locale}")
            return
        
        # Check if locale already exists
        locale_path = translation_manager.lang_path / locale
        if locale_path.exists() and not force:
            self.error(f"Locale '{locale}' already exists. Use --force to overwrite.")
            return
        
        try:
            # Create locale files
            translation_manager.create_locale_files(locale, copy_from)
            
            if copy_from:
                self.info(f"Created locale '{locale}' by copying from '{copy_from}'")
            else:
                self.info(f"Created locale '{locale}' with default translations")
            
            # Show created files
            if locale_path.exists():
                files = list(locale_path.glob('*.json'))
                self.info(f"Created {len(files)} translation files:")
                for file in files:
                    self.line(f"  - {file.name}")
        
        except Exception as e:
            self.error(f"Failed to create locale: {e}")


class TranslationStatusCommand(Command):
    """Show translation status and statistics"""
    
    signature = "translation:status"
    description = "Show translation status and statistics"
    
    async def handle(self) -> None:
        """Handle the command"""
        parser = ArgumentParser(description=self.description)
        parser.add_argument('--locale', help='Show status for specific locale')
        parser.add_argument('--missing-only', action='store_true', help='Show only missing translations')
        
        args = parser.parse_args(sys.argv[2:])
        
        locales = [args.locale] if args.locale else translation_manager.get_available_locales()
        
        if not locales:
            self.warning("No locales found")
            return
        
        # Show status for each locale
        for locale in locales:
            self._show_locale_status(locale, args.missing_only)
    
    def _show_locale_status(self, locale: str, missing_only: bool = False) -> None:
        """Show status for a specific locale"""
        self.info(f"\nLocale: {locale}")
        self.line("-" * 40)
        
        # Check if locale has translations
        if not translation_manager.has_translations(locale):
            self.warning(f"No translations found for locale '{locale}'")
            return
        
        # Get namespaces
        namespaces = translation_manager.get_namespaces(locale)
        self.line(f"Namespaces: {', '.join(namespaces)}")
        
        # Get missing keys compared to fallback locale
        fallback_locale = translation_manager.fallback_locale
        if locale != fallback_locale:
            missing_keys = translation_manager.get_missing_keys(locale, fallback_locale)
            
            if missing_keys:
                self.warning(f"Missing {len(missing_keys)} translations compared to '{fallback_locale}':")
                if not missing_only or missing_keys:
                    for key in missing_keys[:10]:  # Show first 10
                        self.line(f"  - {key}")
                    if len(missing_keys) > 10:
                        self.line(f"  ... and {len(missing_keys) - 10} more")
            else:
                self.success("All translations present")
        
        # Validate translation files
        if not missing_only:
            issues = translation_manager.validate_translations(locale)
            if issues:
                self.warning(f"Found {len(issues)} validation issues:")
                for issue in issues:
                    self.line(f"  - {issue['type']}: {issue['message']}")
            else:
                self.success("No validation issues")


class TranslationMissingCommand(Command):
    """Find missing translation keys"""
    
    signature = "translation:missing"
    description = "Find missing translation keys across locales"
    
    async def handle(self) -> None:
        """Handle the command"""
        parser = ArgumentParser(description=self.description)
        parser.add_argument('--locale', help='Check specific locale')
        parser.add_argument('--base', help='Base locale to compare against', default='en')
        parser.add_argument('--export', help='Export missing keys to file')
        
        args = parser.parse_args(sys.argv[2:])
        
        base_locale = args.base
        locales = [args.locale] if args.locale else translation_manager.get_available_locales()
        
        all_missing = {}
        
        for locale in locales:
            if locale == base_locale:
                continue
            
            missing_keys = translation_manager.get_missing_keys(locale, base_locale)
            if missing_keys:
                all_missing[locale] = missing_keys
        
        if not all_missing:
            self.success("No missing translations found!")
            return
        
        # Display missing keys
        for locale, missing_keys in all_missing.items():
            self.info(f"\nMissing in '{locale}' (compared to '{base_locale}'):")
            self.line("-" * 50)
            
            for key in missing_keys:
                self.line(f"  {key}")
        
        # Export if requested
        if args.export:
            self._export_missing_keys(all_missing, args.export)
    
    def _export_missing_keys(self, missing_keys: Dict[str, List[str]], filename: str) -> None:
        """Export missing keys to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(missing_keys, f, indent=2, ensure_ascii=False)
            self.success(f"Exported missing keys to: {filename}")
        except Exception as e:
            self.error(f"Failed to export: {e}")


class TranslationImportCommand(Command):
    """Import translations from file"""
    
    signature = "translation:import"
    description = "Import translations from JSON or CSV file"
    
    async def handle(self) -> None:
        """Handle the command"""
        parser = ArgumentParser(description=self.description)
        parser.add_argument('file', help='File to import from')
        parser.add_argument('locale', help='Target locale')
        parser.add_argument('--namespace', default='messages', help='Target namespace')
        parser.add_argument('--merge', action='store_true', help='Merge with existing translations')
        
        args = parser.parse_args(sys.argv[2:])
        
        file_path = Path(args.file)
        
        if not file_path.exists():
            self.error(f"File not found: {file_path}")
            return
        
        try:
            # Load translations from file
            if file_path.suffix.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
            else:
                self.error(f"Unsupported file format: {file_path.suffix}")
                return
            
            # Import translations
            if args.merge:
                # Get existing translations and merge
                existing = translation_manager.export_translations(args.locale).get(args.namespace, {})
                existing.update(translations)
                translations = existing
            
            translation_manager.import_translations(args.locale, translations, args.namespace)
            
            self.success(f"Imported {len(translations)} translations to '{args.locale}:{args.namespace}'")
        
        except Exception as e:
            self.error(f"Failed to import translations: {e}")


class TranslationExportCommand(Command):
    """Export translations to file"""
    
    signature = "translation:export" 
    description = "Export translations to JSON file"
    
    async def handle(self) -> None:
        """Handle the command"""
        parser = ArgumentParser(description=self.description)
        parser.add_argument('locale', help='Locale to export')
        parser.add_argument('--output', help='Output file path')
        parser.add_argument('--namespace', help='Export specific namespace only')
        parser.add_argument('--format', choices=['json', 'yaml'], default='json', help='Export format')
        
        args = parser.parse_args(sys.argv[2:])
        
        locale = args.locale
        
        if not translation_manager.has_translations(locale):
            self.error(f"No translations found for locale: {locale}")
            return
        
        try:
            # Export translations
            translations = translation_manager.export_translations(locale)
            
            # Filter by namespace if specified
            if args.namespace:
                if args.namespace in translations:
                    translations = {args.namespace: translations[args.namespace]}
                else:
                    self.error(f"Namespace '{args.namespace}' not found in locale '{locale}'")
                    return
            
            # Determine output file
            output_file = args.output or f"{locale}_translations.{args.format}"
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                if args.format == 'json':
                    json.dump(translations, f, indent=2, ensure_ascii=False)
                elif args.format == 'yaml':
                    import yaml
                    yaml.dump(translations, f, default_flow_style=False, allow_unicode=True)
            
            self.success(f"Exported translations to: {output_file}")
        
        except Exception as e:
            self.error(f"Failed to export translations: {e}")


class TranslationValidateCommand(Command):
    """Validate translation files"""
    
    signature = "translation:validate"
    description = "Validate translation files for syntax and consistency"
    
    async def handle(self) -> None:
        """Handle the command"""
        parser = ArgumentParser(description=self.description)
        parser.add_argument('--locale', help='Validate specific locale')
        parser.add_argument('--fix', action='store_true', help='Attempt to fix issues')
        
        args = parser.parse_args(sys.argv[2:])
        
        locales = [args.locale] if args.locale else translation_manager.get_available_locales()
        
        total_issues = 0
        
        for locale in locales:
            self.info(f"\nValidating locale: {locale}")
            self.line("-" * 30)
            
            issues = translation_manager.validate_translations(locale)
            
            if not issues:
                self.success("No issues found")
                continue
            
            total_issues += len(issues)
            
            for issue in issues:
                issue_type = issue['type']
                message = issue['message']
                
                if issue_type == 'parse_error':
                    self.error(f"Parse Error: {message}")
                elif issue_type == 'missing_locale':
                    self.warning(f"Missing: {message}")
                elif issue_type == 'unsupported_format':
                    self.warning(f"Unsupported: {message}")
                else:
                    self.line(f"{issue_type}: {message}")
        
        if total_issues > 0:
            self.warning(f"\nFound {total_issues} total validation issues")
        else:
            self.success("\nAll translations are valid!")


class TranslationClearCommand(Command):
    """Clear translation cache"""
    
    signature = "translation:clear"
    description = "Clear translation cache"
    
    async def handle(self) -> None:
        """Handle the command"""
        parser = ArgumentParser(description=self.description)
        parser.add_argument('--locale', help='Clear cache for specific locale')
        
        args = parser.parse_args(sys.argv[2:])
        
        if args.locale:
            translation_manager.clear_cache(args.locale)
            self.success(f"Cleared cache for locale: {args.locale}")
        else:
            translation_manager.clear_cache()
            self.success("Cleared all translation cache")


# Command registry for easy access
TRANSLATION_COMMANDS = {
    'make:locale': MakeLocaleCommand,
    'translation:status': TranslationStatusCommand,
    'translation:missing': TranslationMissingCommand,
    'translation:import': TranslationImportCommand,
    'translation:export': TranslationExportCommand,
    'translation:validate': TranslationValidateCommand,
    'translation:clear': TranslationClearCommand,
}


def register_translation_commands(application: Any) -> None:
    """Register all translation commands with the application"""
    for signature, command_class in TRANSLATION_COMMANDS.items():
        application.add_command(signature, command_class)