"""
Blade Asset Management System
Provides asset bundling, versioning, and optimization for Blade templates
"""
from __future__ import annotations

import hashlib
import json
import os
import gzip
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from datetime import datetime, timedelta
import re
import base64
from concurrent.futures import ThreadPoolExecutor
import threading


class AssetType:
    CSS = 'css'
    JS = 'js'
    IMAGE = 'image'
    FONT = 'font'
    OTHER = 'other'


class Asset:
    """Represents a single asset"""
    
    def __init__(self, path: str, content: Optional[str] = None, 
                 asset_type: str = AssetType.OTHER):
        self.path = path
        self.content = content
        self.asset_type = asset_type
        self.size = 0
        self.hash = ''
        self.last_modified = datetime.now()
        self.dependencies: Set[str] = set()
        self.compressed_content: Optional[bytes] = None
        
        if content:
            self.size = len(content.encode('utf-8'))
            self.hash = hashlib.md5(content.encode('utf-8')).hexdigest()


class AssetBundle:
    """Represents a bundle of assets"""
    
    def __init__(self, name: str, asset_type: str):
        self.name = name
        self.asset_type = asset_type
        self.assets: List[Asset] = []
        self.combined_content = ''
        self.hash = ''
        self.size = 0
        self.created_at = datetime.now()
        self.expires_at: Optional[datetime] = None
    
    def add_asset(self, asset: Asset) -> None:
        """Add asset to bundle"""
        if asset not in self.assets:
            self.assets.append(asset)
            self._update_bundle()
    
    def _update_bundle(self) -> None:
        """Update bundle content and metadata"""
        contents = []
        for asset in self.assets:
            if asset.content:
                contents.append(asset.content)
        
        self.combined_content = '\n'.join(contents)
        self.size = len(self.combined_content.encode('utf-8'))
        self.hash = hashlib.md5(self.combined_content.encode('utf-8')).hexdigest()[:12]
    
    def get_versioned_name(self) -> str:
        """Get versioned bundle name"""
        return f"{self.name}-{self.hash}.{self.asset_type}"


class AssetVersioning:
    """Asset versioning and cache busting"""
    
    def __init__(self) -> None:
        self.version_strategy = 'hash'  # 'hash', 'timestamp', 'manual'
        self.version_map: Dict[str, str] = {}
        self.manifest_path = 'storage/assets/manifest.json'
        self._load_manifest()
    
    def _load_manifest(self) -> None:
        """Load asset manifest from disk"""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    self.version_map = json.load(f)
            except Exception:
                self.version_map = {}
    
    def _save_manifest(self) -> None:
        """Save asset manifest to disk"""
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        with open(self.manifest_path, 'w') as f:
            json.dump(self.version_map, f, indent=2)
    
    def version_asset(self, asset_path: str, content: str) -> str:
        """Generate version for asset"""
        if self.version_strategy == 'hash':
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
            return content_hash
        elif self.version_strategy == 'timestamp':
            return str(int(datetime.now().timestamp()))
        else:
            return self.version_map.get(asset_path, '1')
    
    def get_versioned_url(self, asset_path: str) -> str:
        """Get versioned URL for asset"""
        if asset_path in self.version_map:
            version = self.version_map[asset_path]
            path_parts = asset_path.rsplit('.', 1)
            if len(path_parts) == 2:
                return f"{path_parts[0]}-{version}.{path_parts[1]}"
        return asset_path
    
    def register_asset(self, asset_path: str, content: str) -> None:
        """Register asset with version"""
        version = self.version_asset(asset_path, content)
        self.version_map[asset_path] = version
        self._save_manifest()


class AssetOptimizer:
    """Asset optimization and compression"""
    
    def __init__(self) -> None:
        self.css_optimizer = CSSOptimizer()
        self.js_optimizer = JSOptimizer()
        self.image_optimizer = ImageOptimizer()
    
    def optimize_asset(self, asset: Asset) -> Asset:
        """Optimize asset based on type"""
        if asset.asset_type == AssetType.CSS:
            asset.content = self.css_optimizer.optimize(asset.content or '')
        elif asset.asset_type == AssetType.JS:
            asset.content = self.js_optimizer.optimize(asset.content or '')
        elif asset.asset_type == AssetType.IMAGE:
            # Image optimization would require additional libraries
            pass
        
        # Update asset metadata
        if asset.content:
            asset.size = len(asset.content.encode('utf-8'))
            asset.hash = hashlib.md5(asset.content.encode('utf-8')).hexdigest()
        
        return asset
    
    def compress_asset(self, asset: Asset) -> Asset:
        """Compress asset content"""
        if asset.content:
            asset.compressed_content = gzip.compress(asset.content.encode('utf-8'))
        return asset


class CSSOptimizer:
    """CSS-specific optimization"""
    
    def optimize(self, css_content: str) -> str:
        """Optimize CSS content"""
        # Remove comments
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        css_content = re.sub(r'\s+', ' ', css_content)
        css_content = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', css_content)
        
        # Remove trailing semicolons
        css_content = re.sub(r';}', '}', css_content)
        
        # Optimize colors
        css_content = re.sub(r'#([0-9a-fA-F])\1([0-9a-fA-F])\2([0-9a-fA-F])\3', r'#\1\2\3', css_content)
        
        # Remove unnecessary quotes
        css_content = re.sub(r'url\(["\']([^"\']*?)["\']\)', r'url(\1)', css_content)
        
        # Optimize zero values
        css_content = re.sub(r'\b0+\.?\d*px\b', '0', css_content)
        css_content = re.sub(r'\b0+\.?\d*em\b', '0', css_content)
        css_content = re.sub(r'\b0+\.?\d*%\b', '0', css_content)
        
        return css_content.strip()


class JSOptimizer:
    """JavaScript-specific optimization"""
    
    def optimize(self, js_content: str) -> str:
        """Basic JavaScript optimization"""
        # Remove single-line comments
        js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
        
        # Remove multi-line comments (preserve /*! important comments)
        js_content = re.sub(r'/\*(?!\!).*?\*/', '', js_content, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        js_content = re.sub(r'\s+', ' ', js_content)
        js_content = re.sub(r'\s*([{}();,=<>!&|+\-*/])\s*', r'\1', js_content)
        
        # Remove unnecessary semicolons
        js_content = re.sub(r';}', '}', js_content)
        
        return js_content.strip()


class ImageOptimizer:
    """Image optimization placeholder"""
    
    def optimize(self, image_data: bytes) -> bytes:
        """Optimize image data (placeholder implementation)"""
        # Would use libraries like Pillow, imageio, etc.
        return image_data


class AssetPreloader:
    """Asset preloading and prefetching"""
    
    def __init__(self) -> None:
        self.preload_strategies = {
            'critical': self._preload_critical,
            'lazy': self._preload_lazy,
            'prefetch': self._preload_prefetch
        }
    
    def generate_preload_tags(self, assets: List[Asset], strategy: str = 'critical') -> str:
        """Generate preload tags for assets"""
        if strategy not in self.preload_strategies:
            return ''
        
        return self.preload_strategies[strategy](assets)
    
    def _preload_critical(self, assets: List[Asset]) -> str:
        """Generate critical resource preload tags"""
        tags = []
        for asset in assets:
            if asset.asset_type == AssetType.CSS:
                tags.append(f'<link rel="preload" href="{asset.path}" as="style">')
            elif asset.asset_type == AssetType.JS:
                tags.append(f'<link rel="preload" href="{asset.path}" as="script">')
            elif asset.asset_type == AssetType.FONT:
                tags.append(f'<link rel="preload" href="{asset.path}" as="font" crossorigin>')
        
        return '\n'.join(tags)
    
    def _preload_lazy(self, assets: List[Asset]) -> str:
        """Generate lazy loading tags"""
        # Implementation for lazy loading
        return ''
    
    def _preload_prefetch(self, assets: List[Asset]) -> str:
        """Generate prefetch tags"""
        tags = []
        for asset in assets:
            tags.append(f'<link rel="prefetch" href="{asset.path}">')
        
        return '\n'.join(tags)


class BladeAssetManager:
    """Main asset management system for Blade templates"""
    
    def __init__(self, public_path: str = 'public', build_path: str = 'public/build'):
        self.public_path = public_path
        self.build_path = build_path
        self.assets: Dict[str, Asset] = {}
        self.bundles: Dict[str, AssetBundle] = {}
        self.versioning = AssetVersioning()
        self.optimizer = AssetOptimizer()
        self.preloader = AssetPreloader()
        self._lock = threading.Lock()
        
        # Asset discovery patterns
        self.asset_patterns = {
            AssetType.CSS: [r'\.css$'],
            AssetType.JS: [r'\.js$'],
            AssetType.IMAGE: [r'\.(png|jpg|jpeg|gif|svg|webp)$'],
            AssetType.FONT: [r'\.(woff|woff2|ttf|eot)$']
        }
        
        # Bundle configurations
        self.bundle_configs: Dict[str, Dict[str, Any]] = {}
        
        # Ensure build directory exists
        os.makedirs(build_path, exist_ok=True)
    
    def register_asset(self, path: str, content: Optional[str] = None) -> Asset:
        """Register an asset"""
        asset_type = self._detect_asset_type(path)
        
        if content is None:
            full_path = os.path.join(self.public_path, path.lstrip('/'))
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
        
        asset = Asset(path, content, asset_type)
        
        with self._lock:
            self.assets[path] = asset
        
        return asset
    
    def create_bundle(self, bundle_name: str, asset_paths: List[str], 
                     bundle_type: Optional[str] = None) -> AssetBundle:
        """Create an asset bundle"""
        if bundle_type is None:
            # Detect bundle type from first asset
            if asset_paths:
                bundle_type = self._detect_asset_type(asset_paths[0])
            else:
                bundle_type = 'css'  # Default fallback
        
        bundle = AssetBundle(bundle_name, bundle_type)
        
        for asset_path in asset_paths:
            if asset_path not in self.assets:
                self.register_asset(asset_path)
            
            bundle.add_asset(self.assets[asset_path])
        
        with self._lock:
            self.bundles[bundle_name] = bundle
        
        return bundle
    
    def build_bundles(self, optimize: bool = True, compress: bool = True) -> Dict[str, str]:
        """Build all registered bundles"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for bundle_name, bundle in self.bundles.items():
                future = executor.submit(self._build_bundle, bundle, optimize, compress)
                futures.append((bundle_name, future))
            
            for bundle_name, future in futures:
                try:
                    result = future.result()
                    results[bundle_name] = result
                except Exception as e:
                    results[bundle_name] = f"Error: {str(e)}"
        
        return results
    
    def _build_bundle(self, bundle: AssetBundle, optimize: bool, compress: bool) -> str:
        """Build a single bundle"""
        # Optimize assets if requested
        if optimize:
            for asset in bundle.assets:
                self.optimizer.optimize_asset(asset)
            bundle._update_bundle()
        
        # Write bundle to build directory
        versioned_name = bundle.get_versioned_name()
        bundle_path = os.path.join(self.build_path, versioned_name)
        
        with open(bundle_path, 'w', encoding='utf-8') as f:
            f.write(bundle.combined_content)
        
        # Create compressed version if requested
        if compress:
            compressed_path = bundle_path + '.gz'
            with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
                f.write(bundle.combined_content)
        
        # Register with versioning system
        self.versioning.register_asset(f"/build/{bundle.name}.{bundle.asset_type}", 
                                     bundle.combined_content)
        
        return bundle_path
    
    def get_asset_url(self, asset_path: str, versioned: bool = True) -> str:
        """Get URL for asset"""
        if versioned:
            return self.versioning.get_versioned_url(asset_path)
        return asset_path
    
    def get_bundle_url(self, bundle_name: str) -> str:
        """Get URL for bundle"""
        if bundle_name in self.bundles:
            bundle = self.bundles[bundle_name]
            return f"/build/{bundle.get_versioned_name()}"
        return ''
    
    def generate_asset_tags(self, asset_paths: List[str], 
                          attributes: Optional[Dict[str, str]] = None) -> str:
        """Generate HTML tags for assets"""
        tags = []
        attrs = attributes or {}
        
        for asset_path in asset_paths:
            asset_type = self._detect_asset_type(asset_path)
            url = self.get_asset_url(asset_path)
            
            if asset_type == AssetType.CSS:
                attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
                tags.append(f'<link rel="stylesheet" href="{url}" {attr_str}>')
            elif asset_type == AssetType.JS:
                attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
                tags.append(f'<script src="{url}" {attr_str}></script>')
        
        return '\n'.join(tags)
    
    def generate_bundle_tags(self, bundle_names: List[str], 
                           attributes: Optional[Dict[str, str]] = None) -> str:
        """Generate HTML tags for bundles"""
        tags = []
        attrs = attributes or {}
        
        for bundle_name in bundle_names:
            if bundle_name in self.bundles:
                bundle = self.bundles[bundle_name]
                url = self.get_bundle_url(bundle_name)
                
                if bundle.asset_type == AssetType.CSS:
                    attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
                    tags.append(f'<link rel="stylesheet" href="{url}" {attr_str}>')
                elif bundle.asset_type == AssetType.JS:
                    attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
                    tags.append(f'<script src="{url}" {attr_str}></script>')
        
        return '\n'.join(tags)
    
    def generate_preload_tags(self, bundle_names: List[str], 
                            strategy: str = 'critical') -> str:
        """Generate preload tags for bundles"""
        assets = []
        for bundle_name in bundle_names:
            if bundle_name in self.bundles:
                bundle = self.bundles[bundle_name]
                # Create asset representation of bundle
                bundle_asset = Asset(
                    self.get_bundle_url(bundle_name),
                    bundle.combined_content,
                    bundle.asset_type
                )
                assets.append(bundle_asset)
        
        return self.preloader.generate_preload_tags(assets, strategy)
    
    def _detect_asset_type(self, path: str) -> str:
        """Detect asset type from file extension"""
        path_lower = path.lower()
        
        for asset_type, patterns in self.asset_patterns.items():
            for pattern in patterns:
                if re.search(pattern, path_lower):
                    return asset_type
        
        return AssetType.OTHER
    
    def get_asset_stats(self) -> Dict[str, Any]:
        """Get asset management statistics"""
        total_assets = len(self.assets)
        total_bundles = len(self.bundles)
        
        bundle_sizes = {name: bundle.size for name, bundle in self.bundles.items()}
        total_bundle_size = sum(bundle_sizes.values())
        
        return {
            'total_assets': total_assets,
            'total_bundles': total_bundles,
            'bundle_sizes': bundle_sizes,
            'total_bundle_size': total_bundle_size,
            'versioned_assets': len(self.versioning.version_map)
        }
    
    def clear_cache(self) -> None:
        """Clear asset cache and rebuild"""
        with self._lock:
            self.assets.clear()
            self.bundles.clear()
        
        # Clear build directory
        if os.path.exists(self.build_path):
            for file in os.listdir(self.build_path):
                file_path = os.path.join(self.build_path, file)
                if os.path.isfile(file_path):
                    os.unlink(file_path)


# Enhanced Blade Engine integration
def create_asset_directives(asset_manager: BladeAssetManager) -> Dict[str, Callable[[str], str]]:
    """Create asset-related Blade directives"""
    
    def vite_directive(content: str) -> str:
        """Enhanced @vite directive with bundling support"""
        assets = [asset.strip().strip('"\'') for asset in content.split(',')]
        
        # Check if we should use bundles or individual assets
        if len(assets) > 1:
            # Create a temporary bundle
            bundle_name = f"vite_bundle_{hash(tuple(assets))}"
            bundle = asset_manager.create_bundle(bundle_name, assets)
            asset_manager._build_bundle(bundle, optimize=True, compress=True)
            return asset_manager.generate_bundle_tags([bundle_name])
        else:
            return asset_manager.generate_asset_tags(assets)
    
    def bundle_directive(content: str) -> str:
        """@bundle directive for explicit bundle usage"""
        bundle_name = content.strip().strip('"\'')
        return asset_manager.generate_bundle_tags([bundle_name])
    
    def preload_directive(content: str) -> str:
        """@preload directive for resource preloading"""
        parts = content.split(',')
        bundle_name = parts[0].strip().strip('"\'')
        strategy = parts[1].strip().strip('"\'') if len(parts) > 1 else 'critical'
        return asset_manager.generate_preload_tags([bundle_name], strategy)
    
    def asset_directive(content: str) -> str:
        """@asset directive for individual asset inclusion"""
        asset_path = content.strip().strip('"\'')
        return asset_manager.generate_asset_tags([asset_path])
    
    return {
        'vite': vite_directive,
        'bundle': bundle_directive,
        'preload': preload_directive,
        'asset': asset_directive
    }