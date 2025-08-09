"""
Advanced Blade Components System
Laravel-style component system for reusable UI elements
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List, Union, Callable
from abc import ABC, abstractmethod
from pathlib import Path
import re
import inspect


class ComponentSlot:
    """Represents a component slot for content injection"""
    
    def __init__(self, name: str, content: str = "", attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.content = content
        self.attributes = attributes or {}
    
    def __str__(self) -> str:
        return self.content
    
    def is_empty(self) -> bool:
        return not self.content.strip()


class ComponentBag:
    """Container for component data and slots"""
    
    def __init__(self) -> None:
        self.slots: Dict[str, ComponentSlot] = {}
        self.attributes: Dict[str, Any] = {}
    
    def add_slot(self, name: str, content: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add a slot to the component"""
        self.slots[name] = ComponentSlot(name, content, attributes)
    
    def get_slot(self, name: str, default: str = "") -> ComponentSlot:
        """Get a slot by name"""
        return self.slots.get(name, ComponentSlot(name, default))
    
    def has_slot(self, name: str) -> bool:
        """Check if slot exists and is not empty"""
        return name in self.slots and not self.slots[name].is_empty()


class BladeComponent(ABC):
    """Base class for Blade components"""
    
    def __init__(self, **attributes: Any) -> None:
        self.attributes = attributes
        self.slots = ComponentBag()
    
    @abstractmethod
    def render(self) -> str:
        """Render the component"""
        pass
    
    def get_view_data(self) -> Dict[str, Any]:
        """Get data to pass to the component view"""
        return {
            'attributes': self.attributes,
            'slots': self.slots,
            **self.attributes
        }
    
    def should_render(self) -> bool:
        """Determine if the component should render"""
        return True


class AnonymousComponent(BladeComponent):
    """Anonymous component that renders from a template file"""
    
    def __init__(self, template_path: str, blade_engine: Any, **attributes: Any) -> None:
        super().__init__(**attributes)
        self.template_path = template_path
        self.blade_engine = blade_engine
    
    def render(self) -> str:
        """Render the anonymous component"""
        if not self.should_render():
            return ""
        
        view_data = self.get_view_data()
        result = self.blade_engine.render(self.template_path, view_data)
        return str(result) if result is not None else ""


class ComponentRegistry:
    """Registry for managing Blade components"""
    
    def __init__(self) -> None:
        self.components: Dict[str, Union[type, Callable[..., Any]]] = {}
        self.aliases: Dict[str, str] = {}
        self.anonymous_components: Dict[str, str] = {}
    
    def register(self, name: str, component: Union[type, Callable[..., Any], str], alias: Optional[str] = None) -> None:
        """Register a component"""
        if isinstance(component, str):
            # Anonymous component (template path)
            self.anonymous_components[name] = component
        else:
            # Class-based component
            self.components[name] = component
        
        if alias:
            self.aliases[alias] = name
    
    def get(self, name: str) -> Optional[Union[type, Callable[..., Any], str]]:
        """Get a component by name or alias"""
        # Check aliases first
        if name in self.aliases:
            name = self.aliases[name]
        
        # Check anonymous components
        if name in self.anonymous_components:
            return self.anonymous_components[name]
        
        # Check class-based components
        return self.components.get(name)
    
    def create_component(self, name: str, blade_engine: Any, **attributes: Any) -> Optional[BladeComponent]:
        """Create a component instance"""
        component_def = self.get(name)
        
        if component_def is None:
            return None
        
        if isinstance(component_def, str):
            # Anonymous component
            return AnonymousComponent(component_def, blade_engine, **attributes)
        elif inspect.isclass(component_def) and issubclass(component_def, BladeComponent):
            # Class-based component
            return component_def(**attributes)
        elif callable(component_def):
            # Function-based component
            # Convert to anonymous component for now
            pass
        
        # Default return if component type not recognized
        return None
    
    def has(self, name: str) -> bool:
        """Check if component exists"""
        if name in self.aliases:
            name = self.aliases[name]
        return name in self.components or name in self.anonymous_components
    
    def get_by_prefix(self, prefix: str) -> Dict[str, Union[type, Callable[..., Any], str]]:
        """Get all components with names starting with prefix"""
        result: Dict[str, Union[type, Callable[..., Any], str]] = {}
        
        # Check anonymous components
        for name, template in self.anonymous_components.items():
            if name.startswith(prefix):
                result[name] = template
        
        # Check class-based components
        for name, component in self.components.items():
            if name.startswith(prefix):
                result[name] = component
        
        return result


class ComponentCompiler:
    """Compiles component syntax in Blade templates"""
    
    def __init__(self, registry: ComponentRegistry, blade_engine: Any) -> None:
        self.registry = registry
        self.blade_engine = blade_engine
    
    def compile_components(self, template_content: str) -> str:
        """Compile component syntax in template content"""
        # Handle self-closing components: <x-component />
        template_content = re.sub(
            r'<x-([a-zA-Z0-9\-_.]+)([^>]*?)/\s*>',
            self._compile_self_closing_component,
            template_content
        )
        
        # Handle paired components: <x-component>content</x-component>
        template_content = re.sub(
            r'<x-([a-zA-Z0-9\-_.]+)([^>]*?)>(.*?)</x-\1>',
            self._compile_paired_component,
            template_content,
            flags=re.DOTALL
        )
        
        return template_content
    
    def _compile_self_closing_component(self, match: re.Match[str]) -> str:
        """Compile self-closing component"""
        component_name = match.group(1)
        attributes_str = match.group(2).strip()
        
        attributes = self._parse_attributes(attributes_str)
        
        return self._render_component(component_name, attributes)
    
    def _compile_paired_component(self, match: re.Match[str]) -> str:
        """Compile paired component with content"""
        component_name = match.group(1)
        attributes_str = match.group(2).strip()
        content = match.group(3)
        
        attributes = self._parse_attributes(attributes_str)
        
        # Parse slots from content
        slots = self._parse_slots(content)
        
        return self._render_component(component_name, attributes, slots)
    
    def _parse_attributes(self, attributes_str: str) -> Dict[str, Any]:
        """Parse component attributes"""
        attributes: Dict[str, Any] = {}
        
        if not attributes_str:
            return attributes
        
        # Parse key="value" pairs
        attr_pattern = r'([a-zA-Z0-9\-_:]+)\s*=\s*["\']([^"\']*)["\']'
        matches = re.findall(attr_pattern, attributes_str)
        
        for key, value in matches:
            # Handle special attributes
            if key.startswith(':'):
                # Dynamic attribute
                key = key[1:]
                # For now, treat as string - in real implementation, would evaluate as expression
                attributes[key] = value
            else:
                attributes[key] = value
        
        # Parse boolean attributes (attributes without values)
        bool_pattern = r'\b([a-zA-Z0-9\-_]+)(?!\s*=)'
        bool_matches = re.findall(bool_pattern, attributes_str)
        
        for attr in bool_matches:
            if attr not in [key for key, _ in matches]:
                attributes[attr] = True
        
        return attributes
    
    def _parse_slots(self, content: str) -> Dict[str, ComponentSlot]:
        """Parse slots from component content"""
        slots = {}
        
        # Parse named slots: <x-slot name="header">content</x-slot>
        slot_pattern = r'<x-slot\s+name=["\']([^"\']+)["\']([^>]*?)>(.*?)</x-slot>'
        slot_matches = re.findall(slot_pattern, content, re.DOTALL)
        
        for name, attrs_str, slot_content in slot_matches:
            slot_attrs = self._parse_attributes(attrs_str)
            slots[name] = ComponentSlot(name, slot_content.strip(), slot_attrs)
        
        # Remove slot definitions from content
        content_without_slots = re.sub(slot_pattern, '', content, flags=re.DOTALL)
        
        # Default slot (unnamed content)
        if content_without_slots.strip():
            slots['slot'] = ComponentSlot('slot', content_without_slots.strip())
        
        return slots
    
    def _render_component(self, name: str, attributes: Dict[str, Any], slots: Optional[Dict[str, ComponentSlot]] = None) -> str:
        """Render a component"""
        component = self.registry.create_component(name, self.blade_engine, **attributes)
        
        if component is None:
            return f"<!-- Component '{name}' not found -->"
        
        # Add slots to component
        if slots:
            for slot_name, slot in slots.items():
                component.slots.add_slot(slot_name, slot.content, slot.attributes)
        
        try:
            return component.render()
        except Exception as e:
            return f"<!-- Error rendering component '{name}': {str(e)} -->"


# Built-in components
class AlertComponent(BladeComponent):
    """Built-in alert component"""
    
    def render(self) -> str:
        alert_type = self.attributes.get('type', 'info')
        dismissible = self.attributes.get('dismissible', False)
        message = self.slots.get_slot('slot', 'Alert message').content
        
        css_classes = {
            'info': 'bg-blue-100 border-blue-500 text-blue-700',
            'success': 'bg-green-100 border-green-500 text-green-700',
            'warning': 'bg-yellow-100 border-yellow-500 text-yellow-700',
            'error': 'bg-red-100 border-red-500 text-red-700',
            'danger': 'bg-red-100 border-red-500 text-red-700'
        }
        
        css_class = css_classes.get(alert_type, css_classes['info'])
        
        dismiss_button = ''
        if dismissible:
            dismiss_button = '''
                <button type="button" class="absolute top-0 right-0 mt-4 mr-4" onclick="this.parentElement.style.display='none'">
                    <span class="sr-only">Close</span>
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            '''
        
        return f'''
        <div class="relative border-l-4 p-4 {css_class}" role="alert">
            {message}
            {dismiss_button}
        </div>
        '''.strip()


class ButtonComponent(BladeComponent):
    """Built-in button component"""
    
    def render(self) -> str:
        variant = self.attributes.get('variant', 'primary')
        size = self.attributes.get('size', 'medium')
        disabled = self.attributes.get('disabled', False)
        href = self.attributes.get('href')
        
        base_classes = 'inline-flex items-center justify-center font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2'
        
        variant_classes = {
            'primary': 'bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500',
            'secondary': 'bg-gray-600 hover:bg-gray-700 text-white focus:ring-gray-500',
            'success': 'bg-green-600 hover:bg-green-700 text-white focus:ring-green-500',
            'danger': 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500',
            'outline': 'border-2 border-gray-300 bg-white hover:bg-gray-50 text-gray-700 focus:ring-gray-500'
        }
        
        size_classes = {
            'small': 'px-3 py-2 text-sm',
            'medium': 'px-4 py-2',
            'large': 'px-6 py-3 text-lg'
        }
        
        variant_class = variant_classes.get(variant, variant_classes['primary'])
        size_class = size_classes.get(size, size_classes['medium'])
        
        classes = f"{base_classes} {variant_class} {size_class}"
        
        if disabled:
            classes += " opacity-50 cursor-not-allowed"
        
        content = self.slots.get_slot('slot', 'Button').content
        
        extra_attrs = []
        for key, value in self.attributes.items():
            if key not in ['variant', 'size', 'disabled', 'href', 'class']:
                if isinstance(value, bool) and value:
                    extra_attrs.append(key)
                else:
                    extra_attrs.append(f'{key}="{value}"')
        
        extra_attrs_str = ' ' + ' '.join(extra_attrs) if extra_attrs else ''
        
        if href:
            return f'<a href="{href}" class="{classes}"{extra_attrs_str}>{content}</a>'
        else:
            disabled_attr = ' disabled' if disabled else ''
            return f'<button type="button" class="{classes}"{disabled_attr}{extra_attrs_str}>{content}</button>'


class CardComponent(BladeComponent):
    """Built-in card component"""
    
    def render(self) -> str:
        header = self.slots.get_slot('header')
        footer = self.slots.get_slot('footer')
        content = self.slots.get_slot('slot', 'Card content').content
        
        header_html = f'<div class="px-6 py-4 border-b border-gray-200">{header.content}</div>' if not header.is_empty() else ''
        footer_html = f'<div class="px-6 py-4 border-t border-gray-200 bg-gray-50">{footer.content}</div>' if not footer.is_empty() else ''
        
        return f'''
        <div class="bg-white shadow-md rounded-lg overflow-hidden">
            {header_html}
            <div class="px-6 py-4">
                {content}
            </div>
            {footer_html}
        </div>
        '''.strip()


class ModalComponent(BladeComponent):
    """Built-in modal component"""
    
    def render(self) -> str:
        modal_id = self.attributes.get('id', 'modal')
        title = self.slots.get_slot('title', 'Modal').content
        content = self.slots.get_slot('slot', 'Modal content').content
        footer = self.slots.get_slot('footer')
        
        footer_html = f'<div class="px-6 py-3 bg-gray-50 text-right">{footer.content}</div>' if not footer.is_empty() else ''
        
        return f'''
        <div id="{modal_id}" class="fixed inset-0 z-50 hidden overflow-y-auto" aria-labelledby="{modal_id}-title" role="dialog" aria-modal="true">
            <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>
                <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                    <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                        <div class="sm:flex sm:items-start">
                            <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
                                <h3 class="text-lg leading-6 font-medium text-gray-900" id="{modal_id}-title">
                                    {title}
                                </h3>
                                <div class="mt-4">
                                    {content}
                                </div>
                            </div>
                        </div>
                    </div>
                    {footer_html}
                </div>
            </div>
        </div>
        
        <script>
            function show{modal_id.title()}Modal() {{
                document.getElementById('{modal_id}').classList.remove('hidden');
            }}
            function hide{modal_id.title()}Modal() {{
                document.getElementById('{modal_id}').classList.add('hidden');
            }}
        </script>
        '''.strip()


# Global component registry
component_registry = ComponentRegistry()

# Register built-in components
component_registry.register('alert', AlertComponent)
component_registry.register('button', ButtonComponent) 
component_registry.register('card', CardComponent)
component_registry.register('modal', ModalComponent)