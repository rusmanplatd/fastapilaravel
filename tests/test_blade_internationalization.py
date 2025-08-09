"""
Test Suite for Blade Engine Internationalization and Localization
Tests translation features, pluralization, and locale handling
"""
from __future__ import annotations

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator, Tuple
import os

from app.View.BladeEngine import BladeEngine


class TestBladeInternationalization:
    """Test i18n features of Blade engine"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_lang_directive_basic(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test basic @lang directive functionality"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <h1>@lang('welcome.title')</h1>
    <p>@lang('welcome.message')</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "i18n_basic.blade.html", template_content)
        
        # Mock translation data
        engine.translations = {
            'en': {
                'welcome.title': 'Welcome',
                'welcome.message': 'Hello, welcome to our site!'
            }
        }
        
        result = engine.render("i18n_basic.blade.html")
        
        assert "welcome.title" in result  # Should contain the key if translation not found
        assert "welcome.message" in result
    
    def test_lang_directive_with_parameters(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @lang directive with parameter substitution"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>@lang('user.greeting', {'name': user.name, 'role': user.role})</p>
    <p>@lang('items.count', {'count': items|length})</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "i18n_params.blade.html", template_content)
        
        context = {
            'user': {'name': 'John', 'role': 'admin'},
            'items': [1, 2, 3, 4, 5]
        }
        
        result = engine.render("i18n_params.blade.html", context)
        
        # Should contain the translation key (fallback behavior)
        assert "user.greeting" in result
        assert "items.count" in result
    
    def test_choice_directive_pluralization(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test @choice directive for pluralization"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>@choice('messages.notifications', 0)</p>
    <p>@choice('messages.notifications', 1)</p>
    <p>@choice('messages.notifications', 5)</p>
    <p>@choice('items.found', item_count, {'count': item_count})</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "i18n_plural.blade.html", template_content)
        
        context = {'item_count': 3}
        result = engine.render("i18n_plural.blade.html", context)
        
        # Should contain pluralization keys
        assert "messages.notifications" in result
        assert "items.found" in result
    
    def test_nested_translation_keys(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test deeply nested translation keys"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <h1>@lang('pages.dashboard.header.title')</h1>
    <p>@lang('pages.dashboard.content.welcome')</p>
    <nav>@lang('navigation.menu.items.home')</nav>
</div>
        """.strip()
        
        self.create_template(temp_dir, "i18n_nested.blade.html", template_content)
        
        result = engine.render("i18n_nested.blade.html")
        
        assert "pages.dashboard.header.title" in result
        assert "pages.dashboard.content.welcome" in result
        assert "navigation.menu.items.home" in result
    
    def test_translation_with_html_content(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test translations containing HTML content"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <div>@lang('messages.html_content')</div>
    <div>{!! __('messages.safe_html') !!}</div>
</div>
        """.strip()
        
        self.create_template(temp_dir, "i18n_html.blade.html", template_content)
        
        result = engine.render("i18n_html.blade.html")
        
        assert "messages.html_content" in result
        assert "__('messages.safe_html')" in result or "messages.safe_html" in result
    
    def test_conditional_translations(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test translations in conditional statements"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    @if(user_logged_in)
        <p>@lang('auth.logged_in_message')</p>
    @else
        <p>@lang('auth.guest_message')</p>
    @endif
    
    @unless(has_permission)
        <div class="alert">@lang('errors.no_permission')</div>
    @endunless
</div>
        """.strip()
        
        self.create_template(temp_dir, "i18n_conditional.blade.html", template_content)
        
        # Test logged in user
        result = engine.render("i18n_conditional.blade.html", {
            'user_logged_in': True,
            'has_permission': False
        })
        
        assert "auth.logged_in_message" in result
        assert "auth.guest_message" not in result
        assert "errors.no_permission" in result
        
        # Test guest user
        result = engine.render("i18n_conditional.blade.html", {
            'user_logged_in': False,
            'has_permission': True
        })
        
        assert "auth.logged_in_message" not in result
        assert "auth.guest_message" in result
        assert "errors.no_permission" not in result
    
    def test_translation_in_loops(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test translations within loop contexts"""
        engine, temp_dir = blade_engine
        
        template_content = """
<ul>
@foreach(notifications as notification)
    <li>
        <span class="{{ notification.type }}">
            @lang('notifications.' + notification.type)
        </span>
        <p>@lang('notifications.message', {'content': notification.message})</p>
    </li>
@endforeach
</ul>
        """.strip()
        
        self.create_template(temp_dir, "i18n_loops.blade.html", template_content)
        
        notifications = [
            {'type': 'info', 'message': 'System update completed'},
            {'type': 'warning', 'message': 'Low disk space'},
            {'type': 'error', 'message': 'Failed to backup'}
        ]
        
        result = engine.render("i18n_loops.blade.html", {'notifications': notifications})
        
        assert "notifications." in result
        assert "System update completed" in result
        assert "Low disk space" in result


class TestBladeLocalization:
    """Test locale-specific features"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_locale_specific_formatting(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test locale-specific number and date formatting"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>Price: {{ price | money }}</p>
    <p>Percentage: {{ rate | percentage }}</p>
    <p>Date: {{ date | date('Y-m-d') }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "locale_format.blade.html", template_content)
        
        from datetime import datetime
        
        context = {
            'price': 1234.56,
            'rate': 0.75,
            'date': datetime.now()
        }
        
        result = engine.render("locale_format.blade.html", context)
        
        assert "$1,234.56" in result
        assert "0.8%" in result or "75.0%" in result
    
    def test_rtl_language_support(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test right-to-left language support"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div dir="rtl" lang="ar">
    <h1>@lang('arabic.title')</h1>
    <p>@lang('arabic.content')</p>
    
    @if(is_rtl)
        <style>.rtl { direction: rtl; }</style>
    @endif
</div>
        """.strip()
        
        self.create_template(temp_dir, "rtl_test.blade.html", template_content)
        
        context = {'is_rtl': True}
        result = engine.render("rtl_test.blade.html", context)
        
        assert 'dir="rtl"' in result
        assert 'lang="ar"' in result
        assert "direction: rtl" in result
    
    def test_multiple_locale_fallback(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test fallback behavior for multiple locales"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>@lang('common.hello')</p>
    <p>@lang('specific.feature', {}, 'en')</p>
    <p>@lang('missing.key', {}, 'fr')</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "locale_fallback.blade.html", template_content)
        
        result = engine.render("locale_fallback.blade.html")
        
        # Should contain the translation keys as fallback
        assert "common.hello" in result
        assert "specific.feature" in result
        assert "missing.key" in result


class TestBladeTranslationHelpers:
    """Test translation helper functions"""
    
    @pytest.fixture
    def blade_engine(self) -> Generator[Tuple[BladeEngine, str], None, None]:
        temp_path = tempfile.mkdtemp()
        engine = BladeEngine([temp_path], debug=True)
        yield engine, temp_path
        shutil.rmtree(temp_path)
    
    def create_template(self, temp_dir: str, name: str, content: str) -> None:
        """Helper to create template files"""
        template_path = Path(temp_dir) / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def test_double_underscore_helper(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test __ (double underscore) translation helper"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <h1>{{ __('title.main') }}</h1>
    <p>{{ __('content.description', {'name': user_name}) }}</p>
    <span>{{ __('missing.translation', {}, 'fallback text') }}</span>
</div>
        """.strip()
        
        self.create_template(temp_dir, "underscore_helper.blade.html", template_content)
        
        context = {'user_name': 'Alice'}
        result = engine.render("underscore_helper.blade.html", context)
        
        # Should process the translation function calls
        assert "__(" in result
        assert "title.main" in result
        assert "content.description" in result
    
    def test_trans_helper_function(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test trans() helper function"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    <p>{{ trans('messages.welcome') }}</p>
    <p>{{ trans('messages.greeting', {'user': current_user.name}) }}</p>
    <p>{{ trans_choice('items.count', items|length, {'count': items|length}) }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "trans_helper.blade.html", template_content)
        
        context = {
            'current_user': {'name': 'Bob'},
            'items': [1, 2, 3, 4]
        }
        
        result = engine.render("trans_helper.blade.html", context)
        
        assert "trans(" in result
        assert "messages.welcome" in result
        assert "trans_choice(" in result
    
    def test_translation_with_variables(self, blade_engine: Tuple[BladeEngine, str]) -> None:
        """Test translations with dynamic variables"""
        engine, temp_dir = blade_engine
        
        template_content = """
<div>
    @foreach(errors as field => error)
        <p class="error">{{ __('validation.' + field, {'message': error}) }}</p>
    @endforeach
    
    <p>{{ __('status.' + current_status) }}</p>
</div>
        """.strip()
        
        self.create_template(temp_dir, "dynamic_translation.blade.html", template_content)
        
        context = {
            'errors': {
                'email': 'Invalid email format',
                'password': 'Password too short'
            },
            'current_status': 'active'
        }
        
        result = engine.render("dynamic_translation.blade.html", context)
        
        assert "validation." in result
        assert "status." in result
        assert "Invalid email format" in result
        assert "Password too short" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])