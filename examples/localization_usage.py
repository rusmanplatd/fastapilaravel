from __future__ import annotations

"""
Enhanced example usage of Laravel-style Localization system
Demonstrates advanced features and comprehensive usage patterns
"""
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from app.Localization import (
    translator, __, trans, trans_choice, set_app_locale,
    Lang, Locale, translation_manager, locale_manager,
    trans_if, trans_exists, current_locale_info, pluralize
)
from app.Http.Middleware.LocaleMiddleware import LocaleMiddleware, LocaleHelper
from app.Providers.LocalizationServiceProvider import LocalizationServiceProvider

# Initialize FastAPI app
app = FastAPI(title="Enhanced Localization Example")

# Add enhanced locale middleware with advanced features
app.add_middleware(
    LocaleMiddleware,
    supported_locales=["en", "es", "fr", "de", "it", "pt"],
    default_locale="en",
    cookie_name="app_locale",
    detection_methods=["url_parameter", "cookie", "user_preference", "accept_language_header"],
    enable_path_prefix=False,  # Set to True for /es/products style URLs
    enable_subdomain=False,    # Set to True for es.example.com style URLs
    auto_detect=True
)


@app.get("/")
async def home(request: Request):
    """Homepage with localized content"""
    locale = request.state.locale
    
    return {
        "message": __("messages.welcome"),
        "greeting": __("messages.hello", {"name": "World"}),
        "locale": locale,
        "available_locales": LocaleHelper.get_supported_locales(),
        "locale_name": LocaleHelper.get_locale_name(locale),
        "text_direction": LocaleHelper.get_direction(locale)
    }


@app.get("/posts")
async def get_posts(request: Request, count: int = 0):
    """Example with pluralization"""
    
    return {
        "posts_count": trans_choice("messages.posts", count, {"count": count}),
        "message": __("messages.success") if count > 0 else __("messages.info"),
        "locale": request.state.locale
    }


@app.post("/locale/{locale}")
async def change_locale(locale: str, request: Request):
    """Change application locale"""
    
    if not LocaleHelper.is_supported_locale(locale):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported locale: {locale}"
        )
    
    # Set locale for current request
    set_app_locale(locale)
    request.state.locale = locale
    
    response = JSONResponse({
        "message": __("messages.success"),
        "new_locale": locale,
        "locale_name": LocaleHelper.get_locale_name(locale)
    })
    
    # Set cookie for future requests
    response.set_cookie("app_locale", locale, max_age=60*60*24*365)
    
    return response


@app.get("/validation-example")
async def validation_example(request: Request):
    """Example of validation messages in different languages"""
    
    errors = {
        "email": [
            __("validation.required", {"field": "email"}),
            __("validation.email", {"field": "email"})
        ],
        "password": [
            __("validation.required", {"field": "password"}),
            __("validation.min", {"field": "password", "min": "8"})
        ]
    }
    
    return {
        "validation_errors": errors,
        "locale": request.state.locale
    }


@app.get("/file-operations")
async def file_operations(request: Request):
    """Example of file operation messages"""
    
    return {
        "messages": {
            "upload": __("messages.upload"),
            "download": __("messages.download"),
            "file_uploaded": __("messages.file_uploaded"),
            "file_deleted": __("messages.file_deleted")
        },
        "actions": {
            "save": __("messages.save"),
            "cancel": __("messages.cancel"),
            "delete": __("messages.delete"),
            "edit": __("messages.edit")
        },
        "locale": request.state.locale
    }


@app.get("/search")
async def search_results(request: Request, results_count: int = 0):
    """Search results with pluralization"""
    
    return {
        "results": trans_choice("messages.items", results_count, {"count": results_count}),
        "users": trans_choice("messages.users", results_count, {"count": results_count}),
        "search_placeholder": __("messages.search"),
        "filter_label": __("messages.filter"),
        "locale": request.state.locale
    }


@app.get("/dashboard")
async def dashboard(request: Request):
    """Dashboard with various localized elements"""
    
    return {
        "navigation": {
            "home": __("messages.home"),
            "dashboard": __("messages.dashboard"),
            "profile": __("messages.profile"),
            "settings": __("messages.settings")
        },
        "actions": {
            "create": __("messages.create"),
            "update": __("messages.update"),
            "view": __("messages.view"),
            "delete": __("messages.delete")
        },
        "status": {
            "success": __("messages.success"),
            "error": __("messages.error"),
            "warning": __("messages.warning"),
            "info": __("messages.info")
        },
        "confirmation": __("messages.confirmation"),
        "loading": __("messages.loading"),
        "locale": request.state.locale
    }


@app.get("/locale-info")
async def locale_info(request: Request):
    """Get information about current locale"""
    locale = request.state.locale
    
    return {
        "current_locale": locale,
        "locale_name": LocaleHelper.get_locale_name(locale),
        "text_direction": LocaleHelper.get_direction(locale),
        "supported_locales": {
            code: LocaleHelper.get_locale_name(code) 
            for code in LocaleHelper.get_supported_locales()
        },
        "has_translation": {
            "welcome": translator.has("messages.welcome", locale),
            "nonexistent": translator.has("messages.nonexistent", locale)
        }
    }


# Custom function to demonstrate programmatic translation
def get_user_notification_message(user_name: str, action: str, item_count: int = 1) -> dict:
    """Generate localized notification message"""
    
    messages = {
        "greeting": __("messages.hello", {"name": user_name}),
        "action_performed": __("messages.success"),
        "items_affected": trans_choice("messages.items", item_count, {"count": item_count})
    }
    
    return messages


@app.get("/notification/{user_name}")
async def get_notification(request: Request, user_name: str, item_count: int = 1):
    """Get localized notification for user"""
    
    notification = get_user_notification_message(user_name, "create", item_count)
    
    return {
        "notification": notification,
        "locale": request.state.locale,
        "user": user_name
    }


# Example of adding translations programmatically
@app.on_event("startup")
async def add_custom_translations():
    """Add custom translations on startup"""
    
    # Add English translations
    translator.add_lines({
        "app_name": "FastAPI Laravel",
        "version": "Version :version",
        "copyright": "© 2024 FastAPI Laravel. All rights reserved.",
        "contact": "Contact us at :email"
    }, "en", "app")
    
    # Add Spanish translations
    translator.add_lines({
        "app_name": "FastAPI Laravel",
        "version": "Versión :version",
        "copyright": "© 2024 FastAPI Laravel. Todos los derechos reservados.",
        "contact": "Contáctanos en :email"
    }, "es", "app")


@app.get("/app-info")
async def app_info(request: Request):
    """App information with custom translations"""
    
    return {
        "app_name": __("app.app_name"),
        "version": __("app.version", {"version": "1.0.0"}),
        "copyright": __("app.copyright"),
        "contact": __("app.contact", {"email": "contact@example.com"}),
        "locale": request.state.locale
    }


if __name__ == "__main__":
    import uvicorn
    
    # Create some additional translation files for French
    import os
    from pathlib import Path
    
    # Ensure French translations exist
    fr_dir = Path("resources/lang/fr")
    fr_dir.mkdir(parents=True, exist_ok=True)
    
    # Basic French messages
    fr_messages = {
        "welcome": "Bienvenue dans FastAPI Laravel",
        "hello": "Bonjour :name",
        "goodbye": "Au revoir :name",
        "save": "Sauvegarder",
        "cancel": "Annuler",
        "delete": "Supprimer",
        "success": "Opération terminée avec succès"
    }
    
    import json
    with open(fr_dir / "messages.json", "w", encoding="utf-8") as f:
        json.dump(fr_messages, f, indent=2, ensure_ascii=False)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)