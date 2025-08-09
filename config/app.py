from __future__ import annotations

import os
from typing import List, Dict, Any


def get_app_config() -> Dict[str, Any]:
    """
    Laravel-style application configuration.
    
    This configuration file contains options for your application's name,
    version, environment, debug mode, URL, timezone, locale, and encryption key.
    """
    
    return {
        # Application Name
        # This value is the name of your application. This value is used when the
        # framework needs to place the application's name in a notification or
        # any other location as required by the application or its packages.
        'name': os.getenv('APP_NAME', 'FastAPI Laravel'),
        
        # Application Environment  
        # This value determines the "environment" your application is currently
        # running in. This may determine how you prefer to configure various
        # services the application utilizes.
        'env': os.getenv('APP_ENV', 'production'),
        
        # Application Debug Mode
        # When your application is in debug mode, detailed error messages with
        # stack traces will be shown on every error that occurs within your
        # application. If disabled, a simple generic error page is shown.
        'debug': os.getenv('APP_DEBUG', 'false').lower() == 'true',
        
        # Application URL
        # This URL is used by the console to properly generate URLs when using
        # the Artisan command line tool. You should set this to the root of
        # your application so that it is used when running Artisan tasks.
        'url': os.getenv('APP_URL', 'http://localhost:8000'),
        
        # Application Timezone
        # Here you may specify the default timezone for your application, which
        # will be used by the date and datetime functions. We have gone
        # ahead and set this to a sensible default for you out of the box.
        'timezone': os.getenv('APP_TIMEZONE', 'UTC'),
        
        # Application Locale Configuration
        # The application locale determines the default locale that will be used
        # by the translation service provider. You are free to set this value
        # to any of the locales which will be supported by the application.
        'locale': os.getenv('APP_LOCALE', 'en'),
        
        # Application Fallback Locale
        # The fallback locale determines the locale to use when the current one
        # is not available. You may change the value to correspond to any of
        # the language folders that are provided through your application.
        'fallback_locale': os.getenv('APP_FALLBACK_LOCALE', 'en'),
        
        # Encryption Key
        # This key is used by the encryption service and should be set
        # to a random, 32 character string, otherwise these encrypted strings
        # will not be safe. Please do this before deploying an application!
        'key': os.getenv('APP_KEY', ''),
        
        # Encryption Cipher  
        # This cipher is used by the encryption service. You should use the
        # AES-256-CBC cipher for optimal security, but AES-128-CBC will also work.
        'cipher': os.getenv('APP_CIPHER', 'AES-256-CBC'),
        
        # Application Version
        # This is the version of your application. This value is used when the
        # framework needs to place the application's version in a notification
        # or any other location as required by the application or its packages.
        'version': os.getenv('APP_VERSION', '1.0.0'),
        
        # Maintenance Mode
        # When your application is in maintenance mode, a custom view will
        # be displayed for all requests into your application. This makes it
        # easy to "disable" your application while it is updating.
        'maintenance': {
            'driver': os.getenv('MAINTENANCE_DRIVER', 'file'),
            'store': os.getenv('MAINTENANCE_STORE', None),
        },
        
        # Autoloaded Service Providers
        # The service providers listed here will be automatically loaded on the
        # request to your application. Feel free to add your own services to
        # this array to grant expanded functionality to your applications.
        'providers': [
            # Laravel Core Service Providers
            'app.Providers.AppServiceProvider.AppServiceProvider',
            'app.Providers.RouteServiceProvider.RouteServiceProvider', 
            'app.Providers.AuthServiceProvider.AuthServiceProvider',
            'app.Providers.EventServiceProvider.EventServiceProvider',
            'app.Providers.BroadcastServiceProvider.BroadcastServiceProvider',
            
            # Repository Service Provider
            'app.Providers.RepositoryServiceProvider.RepositoryServiceProvider',
            
            # Package Service Providers
            # Add package service providers here
            
            # Application Service Providers  
            # Add your application service providers here
        ],
        
        # Class Aliases
        # This array of class aliases will be registered when this application
        # is started. However, feel free to register as many as you wish as
        # the aliases are "lazy" loaded so they don't hinder performance.
        'aliases': {
            'App': 'app.Support.Facades.App',
            'Auth': 'app.Support.Facades.Auth', 
            'Cache': 'app.Support.Facades.Cache',
            'Config': 'app.Support.Facades.Config',
            'Crypt': 'app.Support.Facades.Crypt',
            'Event': 'app.Support.Facades.Event',
            'Gate': 'app.Support.Facades.Gate',
            'Hash': 'app.Support.Facades.Hash',
            'Log': 'app.Support.Facades.Log',
            'Mail': 'app.Support.Facades.Mail',
            'Queue': 'app.Support.Facades.Queue',
            'Request': 'app.Support.Facades.Request',
            'Response': 'app.Support.Facades.Response',
            'Route': 'app.Support.Facades.Route',
            'Session': 'app.Support.Facades.Session',
            'Storage': 'app.Support.Facades.Storage',
            'URL': 'app.Support.Facades.URL',
            'View': 'app.Support.Facades.View',
        },
    }