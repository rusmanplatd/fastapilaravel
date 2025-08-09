from __future__ import annotations

from typing import Any, Dict, Optional
import random
from faker import Faker
from app.Models.Organization import Organization

fake = Faker()


class OrganizationFactory:
    """Factory for creating Organization test data."""
    
    @staticmethod
    def definition() -> Dict[str, Any]:
        """Generate fake organization data."""
        company_name = fake.company()
        
        return {
            'name': company_name,
            'code': fake.lexify(text='ORG-????', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),  # type: ignore[attr-defined]
            'description': fake.text(max_nb_chars=200),
            'is_active': fake.boolean(chance_of_getting_true=90),  # type: ignore[attr-defined]
            'email': fake.company_email(),  # type: ignore[attr-defined]
            'phone': fake.phone_number(),
            'website': f"https://www.{fake.domain_name()}",  # type: ignore[attr-defined]
            'address': fake.street_address(),  # type: ignore[attr-defined]
            'city': fake.city(),  # type: ignore[attr-defined]
            'state': fake.state(),  # type: ignore[attr-defined]
            'country': fake.country(),  # type: ignore[attr-defined]
            'postal_code': fake.postcode(),  # type: ignore[attr-defined]
            'level': 0,  # Will be updated based on parent relationship
            'sort_order': fake.random_int(min=0, max=100),  # type: ignore[attr-defined]
            'settings': '{"theme": "light", "timezone": "UTC"}'
        }
    
    @staticmethod
    def create(overrides: Optional[Dict[str, Any]] = None, parent: Optional[Organization] = None) -> Organization:
        """Create a new organization instance."""
        data = OrganizationFactory.definition()
        
        if parent:
            data['parent_id'] = parent.id
            data['level'] = parent.level + 1
        
        if overrides:
            data.update(overrides)
        
        organization = Organization(**data)
        return organization
    
    @staticmethod
    def create_hierarchy(levels: int = 3, children_per_level: int = 2) -> Organization:
        """Create a hierarchical organization structure."""
        # Create root organization
        root = OrganizationFactory.create({
            'name': fake.company() + ' Corporation',
            'code': 'ROOT-CORP',
            'level': 0
        })
        
        current_level = [root]
        
        for level in range(1, levels):
            next_level = []
            
            for parent in current_level:
                for i in range(children_per_level):
                    child = OrganizationFactory.create(
                        {
                            'name': f"{parent.name} - Division {i+1}",
                            'code': f"{parent.code}-DIV{i+1}",
                        },
                        parent=parent
                    )
                    next_level.append(child)
            
            current_level = next_level
        
        return root
    
    @staticmethod
    def create_multinational() -> Organization:
        """Create a multinational organization structure."""
        # Global headquarters
        hq = OrganizationFactory.create({
            'name': fake.company() + ' Global',
            'code': 'HQ-GLOBAL',
            'country': 'United States',
            'city': 'New York',
            'level': 0
        })
        
        # Regional offices
        regions = [
            {'name': 'North America', 'country': 'United States', 'city': 'Chicago'},
            {'name': 'Europe', 'country': 'United Kingdom', 'city': 'London'},
            {'name': 'Asia Pacific', 'country': 'Singapore', 'city': 'Singapore'},
            {'name': 'Latin America', 'country': 'Brazil', 'city': 'São Paulo'},
        ]
        
        for i, region in enumerate(regions):
            regional_office = OrganizationFactory.create(
                {
                    'name': f"{hq.name} - {region['name']}",
                    'code': f"REG-{region['name'].replace(' ', '').upper()[:3]}",
                    'country': region['country'],
                    'city': region['city'],
                },
                parent=hq
            )
            
            # Country offices under each region
            for j in range(2):
                country_office = OrganizationFactory.create(
                    {
                        'name': f"{regional_office.name} - {fake.country()}",  # type: ignore[attr-defined]
                        'code': f"{regional_office.code}-C{j+1}",
                    },
                    parent=regional_office
                )
        
        return hq
    
    @staticmethod
    def create_startup() -> Organization:
        """Create a simple startup organization."""
        return OrganizationFactory.create({
            'name': fake.company() + ' Inc.',
            'code': 'STARTUP',
            'description': 'A fast-growing technology startup',
            'email': 'info@startup.com',
            'website': 'https://startup.com',
            'city': random.choice(['San Francisco', 'New York', 'Austin', 'Seattle']),
            'state': random.choice(['California', 'New York', 'Texas', 'Washington']),
            'country': 'United States'
        })
    
    @staticmethod
    def create_enterprise() -> Organization:
        """Create a large enterprise organization."""
        return OrganizationFactory.create({
            'name': fake.company() + ' Enterprise',
            'code': 'ENTERPRISE',
            'description': 'A large multinational enterprise corporation',
            'email': 'corporate@enterprise.com',
            'website': 'https://enterprise.com',
            'city': random.choice(['New York', 'London', 'Tokyo', 'Frankfurt']),
            'country': random.choice(['United States', 'United Kingdom', 'Japan', 'Germany'])
        })
    
    @staticmethod
    def create_batch(count: int = 10, with_hierarchy: bool = False) -> list[Organization]:
        """Create multiple organizations."""
        organizations = []
        
        if with_hierarchy:
            # Create a few root organizations with children
            roots = count // 3 or 1
            for _ in range(roots):
                root = OrganizationFactory.create_hierarchy(levels=3, children_per_level=2)
                organizations.append(root)
                organizations.extend(root.get_descendants())
        else:
            # Create flat list of organizations
            for _ in range(count):
                org = OrganizationFactory.create()
                organizations.append(org)
        
        return organizations[:count]  # Ensure we don't exceed the requested count