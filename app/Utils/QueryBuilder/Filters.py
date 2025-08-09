from __future__ import annotations

from typing import Dict, List, Optional, Union, Callable, TYPE_CHECKING, Tuple, Any, cast
from app.Types.JsonTypes import JsonValue, FilterCriteria
from abc import ABC, abstractmethod
import json
import re
from datetime import datetime, date, time, timedelta
from sqlalchemy import func, and_, or_, text
from sqlalchemy.sql import not_, exists, cast as sql_cast
from sqlalchemy.sql import select
from sqlalchemy.types import String, Integer, Float, DateTime, Date, Time, Boolean

if TYPE_CHECKING:
    from sqlalchemy.orm import Query
    SQLQuery = Query[object]
else:
    from sqlalchemy.orm import Query
    SQLQuery = Query

from .FilterOperators import FilterOperator
from .AllowedFilter import FilterInterface


class DateRangeFilter(FilterInterface):
    """Advanced date range filtering with multiple formats and operations"""
    
    def __init__(self, 
                 timezone: Optional[str] = None,
                 date_format: str = '%Y-%m-%d',
                 datetime_format: str = '%Y-%m-%d %H:%M:%S',
                 allow_relative: bool = True) -> None:
        self.timezone = timezone
        self.date_format = date_format
        self.datetime_format = datetime_format
        self.allow_relative = allow_relative
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        if value is None:
            return query
        
        column = self._get_column(query, property_name)
        if column is None:
            return query
        
        # Parse date range
        if isinstance(value, str):
            date_range = self._parse_date_range(value)
            if date_range:
                start_date, end_date = date_range
                return query.filter(and_(
                    column >= start_date,
                    column <= end_date
                ))
        elif isinstance(value, list) and len(value) == 2:
            start_date = self._parse_date(str(value[0]))
            end_date = self._parse_date(str(value[1]))
            if start_date and end_date:
                return query.filter(and_(
                    column >= start_date,
                    column <= end_date
                ))
        
        return query
    
    def _parse_date_range(self, value: str) -> Optional[Tuple[datetime, datetime]]:
        """Parse date range from string"""
        if '..' in value:
            parts = value.split('..', 1)
            if len(parts) == 2:
                start = self._parse_date(parts[0].strip())
                end = self._parse_date(parts[1].strip())
                if start and end:
                    return start, end
        elif ',' in value:
            parts = value.split(',', 1)
            if len(parts) == 2:
                start = self._parse_date(parts[0].strip())
                end = self._parse_date(parts[1].strip())
                if start and end:
                    return start, end
        elif self.allow_relative:
            return self._parse_relative_date(value)
        
        return None
    
    def _parse_date(self, value: str) -> Optional[datetime]:
        """Parse individual date"""
        if not value:
            return None
        
        # Try various formats
        formats = [
            self.datetime_format,
            self.date_format,
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_relative_date(self, value: str) -> Optional[Tuple[datetime, datetime]]:
        """Parse relative date expressions"""
        value = value.lower().strip()
        now = datetime.now()
        
        if value == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end
        elif value == 'yesterday':
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end
        elif value == 'this week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            return start, end
        elif value == 'last week':
            start = now - timedelta(days=now.weekday() + 7)
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            return start, end
        elif value == 'this month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = start.replace(month=start.month + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)
            end = next_month - timedelta(microseconds=1)
            return start, end
        elif value == 'last month':
            if now.month == 1:
                start = now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start = now.replace(month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
            return start, end
        
        # Parse patterns like "last 7 days", "past 30 days"
        patterns = [
            (r'last (\d+) days?', lambda m: self._get_last_days(int(m.group(1)))),
            (r'past (\d+) days?', lambda m: self._get_last_days(int(m.group(1)))),
            (r'next (\d+) days?', lambda m: self._get_next_days(int(m.group(1)))),
        ]
        
        for pattern, handler in patterns:
            match = re.match(pattern, value)
            if match:
                return handler(match)
        
        return None
    
    def _get_last_days(self, days: int) -> Tuple[datetime, datetime]:
        """Get date range for last N days"""
        now = datetime.now()
        start = now - timedelta(days=days)
        return start, now
    
    def _get_next_days(self, days: int) -> Tuple[datetime, datetime]:
        """Get date range for next N days"""
        now = datetime.now()
        end = now + timedelta(days=days)
        return now, end
    
    def _get_column(self, query: SQLQuery, property_name: str) -> Optional[Any]:
        """Get column from query"""
        try:
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name)  # type: ignore[misc]
        except Exception:
            pass
        return None
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = cast(List[Dict[str, object]], query.column_descriptions)
                if descriptions and descriptions[0].get('entity'):
                    return descriptions[0]['entity']
        except Exception:
            pass
        return None


class JsonPathFilter(FilterInterface):
    """Advanced JSON path filtering for PostgreSQL and MySQL"""
    
    def __init__(self, path_prefix: str = '$') -> None:
        self.path_prefix = path_prefix
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        if value is None:
            return query
        
        column = self._get_column(query, property_name)
        if column is None:
            return query
        
        # Parse JSON path and value
        if isinstance(value, str) and ':' in value:
            path, search_value = value.split(':', 1)
            path = path.strip()
            search_value = search_value.strip()
            
            # Handle different path formats
            if not path.startswith('$'):
                path = f"$.{path}"
            
            # Use database-specific JSON functions with text fallback
            try:
                # PostgreSQL style - use text for compatibility
                json_path = text(f"jsonb_extract_path_text({column}, '{path.replace('$.', '')}')")
                return query.filter(json_path == search_value)
            except Exception:
                try:
                    # MySQL style - use text for compatibility
                    json_extract = text(f"json_extract({column}, '{path}')")
                    return query.filter(json_extract == search_value)
                except Exception:
                    # Generic approach
                    return query.filter(column.contains({path.replace('$.', ''): search_value}))
        
        return query
    
    def _get_column(self, query: SQLQuery, property_name: str) -> Optional[Any]:
        """Get column from query"""
        try:
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name)  # type: ignore[misc]
        except Exception:
            pass
        return None
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = cast(List[Dict[str, object]], query.column_descriptions)
                if descriptions and descriptions[0].get('entity'):
                    return descriptions[0]['entity']
        except Exception:
            pass
        return None


class FullTextSearchFilter(FilterInterface):
    """Full-text search filter with ranking and highlighting"""
    
    def __init__(self, 
                 search_type: str = 'natural',
                 min_score: float = 0.0,
                 highlight: bool = False) -> None:
        self.search_type = search_type  # natural, boolean, query_expansion
        self.min_score = min_score
        self.highlight = highlight
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        if not isinstance(value, str) or not value.strip():
            return query
        
        column = self._get_column(query, property_name)
        if column is None:
            return query
        
        search_term = value.strip()
        
        try:
            # MySQL full-text search
            if self.search_type == 'boolean':
                match_expr = func.match(column).against(search_term, func.text('IN BOOLEAN MODE'))
            elif self.search_type == 'query_expansion':
                match_expr = func.match(column).against(search_term, func.text('WITH QUERY EXPANSION'))
            else:
                match_expr = func.match(column).against(search_term)
            
            if self.min_score > 0:
                query = query.filter(match_expr > self.min_score)
            else:
                query = query.filter(match_expr > 0)
            
            # Add ranking
            query = query.add_columns(match_expr.label('search_score'))
            query = query.order_by(match_expr.desc())
            
        except Exception:
            # Fallback to LIKE search
            search_terms = search_term.split()
            conditions = []
            for term in search_terms:
                conditions.append(column.ilike(f'%{term}%'))
            
            if conditions:
                query = query.filter(or_(*conditions))
        
        return query
    
    def _get_column(self, query: SQLQuery, property_name: str) -> Optional[Any]:
        """Get column from query"""
        try:
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name)  # type: ignore[misc]
        except Exception:
            pass
        return None
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = cast(List[Dict[str, object]], query.column_descriptions)
                if descriptions and descriptions[0].get('entity'):
                    return descriptions[0]['entity']
        except Exception:
            pass
        return None


class GeographicFilter(FilterInterface):
    """Geographic/spatial filtering for PostGIS"""
    
    def __init__(self, srid: int = 4326) -> None:
        self.srid = srid
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        if value is None:
            return query
        
        column = self._get_column(query, property_name)
        if column is None:
            return query
        
        # Parse geographic operation
        if isinstance(value, str):
            parts = value.split(':', 1)
            if len(parts) == 2:
                operation = parts[0].lower().strip()
                geom_value = parts[1].strip()
                
                try:
                    if operation == 'within':
                        # Point within polygon
                        return query.filter(func.ST_Within(column, func.ST_GeomFromText(geom_value, self.srid)))
                    elif operation == 'contains':
                        # Polygon contains point
                        return query.filter(func.ST_Contains(column, func.ST_GeomFromText(geom_value, self.srid)))
                    elif operation == 'intersects':
                        # Geometries intersect
                        return query.filter(func.ST_Intersects(column, func.ST_GeomFromText(geom_value, self.srid)))
                    elif operation.startswith('distance'):
                        # Distance-based filtering
                        # Format: "distance:POINT(x y):radius"
                        if ':' in geom_value:
                            point_str, radius_str = geom_value.split(':', 1)
                            radius = float(radius_str)
                            point = func.ST_GeomFromText(point_str, self.srid)
                            return query.filter(func.ST_DWithin(column, point, radius))
                except Exception:
                    pass
        
        return query
    
    def _get_column(self, query: SQLQuery, property_name: str) -> Optional[Any]:
        """Get column from query"""
        try:
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name)  # type: ignore[misc]
        except Exception:
            pass
        return None
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = cast(List[Dict[str, object]], query.column_descriptions)
                if descriptions and descriptions[0].get('entity'):
                    return descriptions[0]['entity']
        except Exception:
            pass
        return None


class RelationshipCountFilter(FilterInterface):
    """Filter by relationship count with advanced conditions"""
    
    def __init__(self, relationship_name: str, operator: str = '>=') -> None:
        self.relationship_name = relationship_name
        self.operator = operator
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        if value is None:
            return query
        
        try:
            count_value = int(value) if isinstance(value, str) else value
        except (ValueError, TypeError):
            return query
        
        model = self._get_model_from_query(query)
        if model is None:
            return query
        
        # Get relationship
        if not hasattr(model, self.relationship_name):
            return query
        
        relationship = getattr(model, self.relationship_name)
        if not hasattr(relationship.property, 'mapper'):
            return query
        
        related_model = relationship.property.mapper.class_
        
        # Create count subquery
        count_subquery = select(func.count(related_model.id)).where(
            getattr(related_model, f"{model.__tablename__}_id") == model.id
        ).scalar_subquery()
        
        # Apply operator
        if self.operator == '=':
            query = query.filter(count_subquery == count_value)
        elif self.operator == '!=':
            query = query.filter(count_subquery != count_value)
        elif self.operator == '>':
            query = query.filter(count_subquery > count_value)
        elif self.operator == '>=':
            query = query.filter(count_subquery >= count_value)
        elif self.operator == '<':
            query = query.filter(count_subquery < count_value)
        elif self.operator == '<=':
            query = query.filter(count_subquery <= count_value)
        
        return query
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = cast(List[Dict[str, object]], query.column_descriptions)
                if descriptions and descriptions[0].get('entity'):
                    return descriptions[0]['entity']
        except Exception:
            pass
        return None


class TextFilter(FilterInterface):
    """Advanced text filtering with fuzzy search, stemming, and normalization"""
    
    def __init__(self, 
                 fuzzy: bool = False,
                 stemming: bool = False,
                 case_sensitive: bool = False,
                 accent_sensitive: bool = False,
                 word_boundaries: bool = False) -> None:
        self.fuzzy = fuzzy
        self.stemming = stemming
        self.case_sensitive = case_sensitive
        self.accent_sensitive = accent_sensitive
        self.word_boundaries = word_boundaries
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        if not isinstance(value, str) or not value.strip():
            return query
        
        column = self._get_column(query, property_name)
        if column is None:
            return query
        
        search_value = value.strip()
        
        # Normalize search value
        if not self.case_sensitive:
            search_value = search_value.lower()
            column = func.lower(column)
        
        if not self.accent_sensitive:
            try:
                # Remove accents (database-specific)
                search_value = func.unaccent(search_value)
                column = func.unaccent(column)
            except Exception:
                pass
        
        # Apply search strategy
        if self.fuzzy:
            # Fuzzy search using similarity
            try:
                similarity_score = func.similarity(column, search_value)
                return query.filter(similarity_score > 0.3).order_by(similarity_score.desc())
            except Exception:
                # Fallback to LIKE with wildcards
                search_pattern = f"%{'%'.join(search_value)}%"
                return query.filter(column.like(search_pattern))
        
        elif self.word_boundaries:
            # Word boundary search
            try:
                # Use regex word boundaries
                pattern = f"\\b{re.escape(search_value)}\\b"
                return query.filter(column.op('~*')(pattern))
            except Exception:
                # Fallback to space-bounded search
                patterns = [
                    f" {search_value} ",
                    f"{search_value} ",
                    f" {search_value}",
                    search_value
                ]
                conditions = [column.like(f"%{pattern}%") for pattern in patterns]
                return query.filter(or_(*conditions))
        
        else:
            # Standard contains search
            return query.filter(column.like(f"%{search_value}%"))
    
    def _get_column(self, query: SQLQuery, property_name: str) -> Optional[Any]:
        """Get column from query"""
        try:
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name)  # type: ignore[misc]
        except Exception:
            pass
        return None
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = cast(List[Dict[str, object]], query.column_descriptions)
                if descriptions and descriptions[0].get('entity'):
                    return descriptions[0]['entity']
        except Exception:
            pass
        return None


class NumericRangeFilter(FilterInterface):
    """Advanced numeric range filtering with statistics and percentiles"""
    
    def __init__(self, 
                 allow_percentiles: bool = True,
                 allow_statistics: bool = True) -> None:
        self.allow_percentiles = allow_percentiles
        self.allow_statistics = allow_statistics
    
    def __call__(self, query: SQLQuery, value: Union[str, int, float, bool, List[Union[str, int, float, bool]], None], property_name: str) -> SQLQuery:
        if value is None:
            return query
        
        column = self._get_column(query, property_name)
        if column is None:
            return query
        
        # Parse numeric range
        if isinstance(value, str):
            # Handle percentile ranges (e.g., "p25..p75", "top10%", "bottom5%")
            if self.allow_percentiles and ('p' in value.lower() or '%' in value):
                return self._apply_percentile_filter(query, column, value)
            
            # Handle statistical ranges (e.g., "mean±1sd", "median±iqr")
            if self.allow_statistics and any(stat in value.lower() for stat in ['mean', 'median', 'sd', 'iqr']):
                return self._apply_statistical_filter(query, column, value)
            
            # Handle standard ranges
            if '..' in value:
                parts = value.split('..', 1)
                if len(parts) == 2:
                    try:
                        start = float(parts[0].strip()) if parts[0].strip() else None
                        end = float(parts[1].strip()) if parts[1].strip() else None
                        
                        conditions = []
                        if start is not None:
                            conditions.append(column >= start)
                        if end is not None:
                            conditions.append(column <= end)
                        
                        if conditions:
                            return query.filter(and_(*conditions))
                    except ValueError:
                        pass
            
            elif ',' in value:
                # Comma-separated values for IN operator
                try:
                    values = [float(v.strip()) for v in value.split(',') if v.strip()]
                    if values:
                        return query.filter(column.in_(values))
                except ValueError:
                    pass
        
        elif isinstance(value, (int, float)):
            return query.filter(column == value)
        
        elif isinstance(value, list) and len(value) >= 2:
            try:
                start = float(value[0])
                end = float(value[1])
                return query.filter(and_(column >= start, column <= end))
            except (ValueError, TypeError):
                pass
        
        return query
    
    def _apply_percentile_filter(self, query: SQLQuery, column: Any, value: str) -> SQLQuery:
        """Apply percentile-based filtering"""
        value = value.lower().strip()
        
        try:
            if 'top' in value and '%' in value:
                # Top N% (e.g., "top10%")
                pct = float(value.replace('top', '').replace('%', '').strip())
                percentile_value = func.percentile_cont(1 - pct/100).within_group(column)
                return query.filter(column >= percentile_value)
            
            elif 'bottom' in value and '%' in value:
                # Bottom N% (e.g., "bottom5%")
                pct = float(value.replace('bottom', '').replace('%', '').strip())
                percentile_value = func.percentile_cont(pct/100).within_group(column)
                return query.filter(column <= percentile_value)
            
            elif '..' in value and 'p' in value:
                # Percentile range (e.g., "p25..p75")
                parts = value.split('..', 1)
                if len(parts) == 2:
                    start_pct = float(parts[0].replace('p', '').strip()) / 100
                    end_pct = float(parts[1].replace('p', '').strip()) / 100
                    
                    start_value = func.percentile_cont(start_pct).within_group(column)
                    end_value = func.percentile_cont(end_pct).within_group(column)
                    
                    return query.filter(and_(
                        column >= start_value,
                        column <= end_value
                    ))
        
        except (ValueError, AttributeError):
            pass
        
        return query
    
    def _apply_statistical_filter(self, query: SQLQuery, column: Any, value: str) -> SQLQuery:
        """Apply statistics-based filtering"""
        value = value.lower().strip()
        
        try:
            if 'mean' in value:
                mean_val = func.avg(column)
                
                if '±' in value:
                    # Mean ± N standard deviations
                    sd_multiplier = 1
                    if 'sd' in value:
                        sd_part = value.split('±')[1].replace('sd', '').strip()
                        sd_multiplier = float(sd_part) if sd_part else 1
                    
                    std_val = func.stddev(column) * sd_multiplier
                    return query.filter(and_(
                        column >= mean_val - std_val,
                        column <= mean_val + std_val
                    ))
            
            elif 'median' in value:
                median_val = func.percentile_cont(0.5).within_group(column)
                
                if '±' in value and 'iqr' in value:
                    # Median ± IQR
                    q1 = func.percentile_cont(0.25).within_group(column)
                    q3 = func.percentile_cont(0.75).within_group(column)
                    iqr = q3 - q1
                    
                    return query.filter(and_(
                        column >= median_val - iqr,
                        column <= median_val + iqr
                    ))
        
        except (ValueError, AttributeError):
            pass
        
        return query
    
    def _get_column(self, query: SQLQuery, property_name: str) -> Optional[Any]:
        """Get column from query"""
        try:
            model = self._get_model_from_query(query)
            if model and hasattr(model, property_name):
                return getattr(model, property_name)  # type: ignore[misc]
        except Exception:
            pass
        return None
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = cast(List[Dict[str, object]], query.column_descriptions)
                if descriptions and descriptions[0].get('entity'):
                    return descriptions[0]['entity']
        except Exception:
            pass
        return None


# Utility functions for creating advanced filters
def create_date_range_filter(**kwargs: Any) -> DateRangeFilter:
    """Create a date range filter with custom configuration"""
    return DateRangeFilter(**kwargs)


def create_json_path_filter(path_prefix: str = '$') -> JsonPathFilter:
    """Create a JSON path filter"""
    return JsonPathFilter(path_prefix)


def create_fulltext_filter(search_type: str = 'natural', **kwargs: Any) -> FullTextSearchFilter:
    """Create a full-text search filter"""
    return FullTextSearchFilter(search_type, **kwargs)


def create_geographic_filter(srid: int = 4326) -> GeographicFilter:
    """Create a geographic filter"""
    return GeographicFilter(srid)


def create_relationship_count_filter(relationship_name: str, operator: str = '>=') -> RelationshipCountFilter:
    """Create a relationship count filter"""
    return RelationshipCountFilter(relationship_name, operator)


def create_text_filter(**kwargs: Any) -> TextFilter:
    """Create a text filter"""
    return TextFilter(**kwargs)


def create_numeric_range_filter(**kwargs: Any) -> NumericRangeFilter:
    """Create a numeric range filter"""
    return NumericRangeFilter(**kwargs)