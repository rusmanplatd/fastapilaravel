from __future__ import annotations

"""
Advanced usage examples for the enhanced QueryBuilder
Demonstrates features that match spatie/laravel-query-builder capabilities
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, text
from starlette.requests import Request

from ..QueryBuilder import QueryBuilder, PaginationResult
from ..AllowedFilter import AllowedFilter
from ..AllowedSort import AllowedSort, SortDirection, StringLengthSort, CaseInsensitiveSort
from ..AllowedInclude import AllowedInclude, AggregateInclude, LatestOfManyInclude
from ..AllowedField import AllowedField
from ..QueryBuilderRequest import QueryBuilderRequest
from ..FilterOperators import FilterOperator


# Import actual models
from app.Models.User import User
from app.Models.Post import Post

class Comment:
    __tablename__ = 'comments'
    pass


def advanced_filtering_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates advanced filtering capabilities
    
    Example URLs:
    - /users?filter[name]=john&filter[email]=gmail
    - /users?filter[status]=active,pending
    - /users?filter[age]=>25
    - /users?filter[salary]=>=50000
    - /users?filter[created_at]=between:2023-01-01,2023-12-31
    - /users?filter[posts.title]=tutorial
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            # Basic filters
            AllowedFilter.partial('name'),
            AllowedFilter.exact('email'),
            AllowedFilter.exact('status'),
            
            # Operator filters
            AllowedFilter.operator('age', FilterOperator.DYNAMIC),
            AllowedFilter.operator('salary', FilterOperator.GREATER_THAN_OR_EQUAL),
            AllowedFilter.operator('created_at', FilterOperator.BETWEEN),
            
            # Relationship filters
            AllowedFilter.partial('posts.title'),
            AllowedFilter.belongs_to('category_id', 'category'),
            
            # Scope filters
            AllowedFilter.scope('active'),
            AllowedFilter.scope('has_posts'),
            
            # Custom filters with callbacks
            AllowedFilter.callback('has_verified_email', 
                lambda query, value, prop: query.filter(User.email_verified_at.is_not(None))
            ),
            
            # Trashed filter for soft deletes
            AllowedFilter.trashed(),
        ]) \
        .allowed_sorts([
            'name', 'email', 'created_at',
            AllowedSort.field('username', 'user_name'),
            AllowedSort.custom('name_length', StringLengthSort(), 'name'),
            AllowedSort.custom('name_ci', CaseInsensitiveSort(), 'name'),
        ]) \
        .allowed_includes([
            'posts', 'comments', 'profile',
            'postsCount', 'commentsCount',
            'postsExists', 'commentsExists',
            AllowedInclude.custom('latest_post', LatestOfManyInclude('posts')),
            AllowedInclude.custom('posts_sum_votes', AggregateInclude('posts', 'votes', 'sum')),
        ]) \
        .allowed_fields([
            'id', 'name', 'email', 'created_at',
            'posts.id', 'posts.title', 'posts.created_at'
        ]) \
        .default_sort('-created_at') \
        .get()


def complex_query_example(session: Session, request: Request) -> PaginationResult[Any]:
    """
    Demonstrates complex query building with multiple features
    
    Example URL:
    /users?include=posts.comments,profile&filter[status]=active&filter[posts.published]=true&sort=-created_at,name&fields[users]=id,name,email&fields[posts]=title,body&page=2&per_page=20
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.exact('status'),
            AllowedFilter.exact('posts.published'),
            AllowedFilter.partial('name'),
            AllowedFilter.operator('age', FilterOperator.DYNAMIC),
            AllowedFilter.scope('verified'),
        ]) \
        .allowed_sorts([
            'created_at', 'name', 'email',
            'posts.created_at', 'posts.title',
            # Note: User.posts relationship doesn't exist in current User model
            # AllowedSort.custom('posts_count', lambda query, desc, prop: 
            #     query.order_by(User.posts.count().desc() if desc else User.posts.count().asc())
            # )
        ]) \
        .allowed_includes([
            'posts', 'posts.comments', 'profile',
            'postsCount', 'commentsCount',
            AllowedInclude.relationship('posts', 'selectin'),  # Use selectin loading
            AllowedInclude.count('postsCount'),
            AllowedInclude.exists('hasActivePost'),
        ]) \
        .allowed_fields([
            'users.id', 'users.name', 'users.email',
            'posts.id', 'posts.title', 'posts.body',
            'profile.bio', 'profile.avatar_url'
        ]) \
        .default_sort('-created_at', 'name') \
        .paginate(
            page=qb_request.get_page(),
            per_page=qb_request.get_per_page(),
            max_per_page=50
        )


def dynamic_operator_filtering_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates dynamic operator filtering
    
    Example URLs:
    - /users?filter[age]=>25 (greater than 25)
    - /users?filter[salary]=>=50000 (greater than or equal to 50000)
    - /users?filter[name]=like:john (contains john)
    - /users?filter[status]=in:active,pending (in list)
    - /users?filter[deleted_at]=null (is null)
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.operator('age', FilterOperator.DYNAMIC),
            AllowedFilter.operator('salary', FilterOperator.DYNAMIC),
            AllowedFilter.operator('name', FilterOperator.DYNAMIC),
            AllowedFilter.operator('status', FilterOperator.DYNAMIC),
            AllowedFilter.operator('deleted_at', FilterOperator.DYNAMIC),
        ]) \
        .get()


def relationship_filtering_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates relationship filtering
    
    Example URLs:
    - /users?filter[posts.published]=true
    - /users?filter[posts.category.name]=technology
    - /users?filter[post]=123 (belongs to post with ID 123)
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.exact('posts.published'),
            AllowedFilter.partial('posts.title'),
            AllowedFilter.partial('posts.category.name'),
            AllowedFilter.belongs_to('post'),
            AllowedFilter.belongs_to('post.author', 'post.author'),  # Nested belongs-to
        ]) \
        .get()


def custom_include_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates custom includes with aggregates and special relationships
    
    Example URLs:
    - /users?include=postsCount,commentsCount
    - /users?include=latestPost,oldestPost
    - /users?include=postsSumVotes,postsAvgRating
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_includes([
            # Basic relationships
            'posts', 'comments', 'profile',
            
            # Count relationships
            AllowedInclude.count('postsCount'),
            AllowedInclude.count('commentsCount'),
            
            # Exists relationships
            AllowedInclude.exists('hasActivePost'),
            
            # Custom relationships
            AllowedInclude.custom('latestPost', LatestOfManyInclude('posts')),
            AllowedInclude.custom('oldestPost', LatestOfManyInclude('posts', 'created_at')),
            
            # Aggregate relationships
            AllowedInclude.custom('postsSumVotes', AggregateInclude('posts', 'votes', 'sum')),
            AllowedInclude.custom('postsAvgRating', AggregateInclude('posts', 'rating', 'avg')),
            
            # Callback includes
            AllowedInclude.callback('featured_posts', 
                lambda query, relations: query.options(
                    # Note: User.posts relationship doesn't exist
                    # selectinload(User.posts).where(Post.is_featured == True)
                )
            ),
        ]) \
        .get()


def sorting_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates advanced sorting capabilities
    
    Example URLs:
    - /users?sort=name,-created_at (name asc, created_at desc)
    - /users?sort=name_length (sort by name length)
    - /users?sort=posts_count (sort by posts count)
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_sorts([
            # Basic sorts
            'name', 'email', 'created_at',
            
            # Custom sorts
            AllowedSort.custom('name_length', StringLengthSort(), 'name'),
            AllowedSort.custom('name_ci', CaseInsensitiveSort(), 'name'),
            
            # Sort with default direction
            AllowedSort.field('featured').default_direction(SortDirection.DESCENDING),
            
            # Relationship sorts
            AllowedSort.field('posts_count', 'posts.count'),
            
            # Callback sorts
            AllowedSort.callback('random', 
                lambda query, desc, prop: query.order_by(text('RANDOM()'))
            ),
        ]) \
        .default_sort('-created_at', 'name') \
        .get()


def field_selection_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates field selection (sparse fieldsets)
    
    Example URLs:
    - /users?fields[users]=id,name,email
    - /users?fields[users]=id,name&fields[posts]=title,body
    - /users?include=posts&fields[posts]=id,title
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_fields([
            # Main model fields
            'users.id', 'users.name', 'users.email', 'users.created_at',
            
            # Relationship fields
            'posts.id', 'posts.title', 'posts.body', 'posts.created_at',
            'comments.id', 'comments.body', 'comments.created_at',
            
            # Aliased fields
            AllowedField.field('username', 'user_name', 'users'),
        ]) \
        .allowed_includes(['posts', 'comments']) \
        .get()


def pagination_example(session: Session, request: Request) -> PaginationResult[Any]:
    """
    Demonstrates comprehensive pagination
    
    Example URLs:
    - /users?page=2&per_page=20
    - /users?page=1&per_page=50&filter[status]=active&sort=-created_at
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    result = QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.exact('status'),
            AllowedFilter.partial('name'),
        ]) \
        .allowed_sorts(['name', 'created_at', 'email']) \
        .default_sort('-created_at') \
        .paginate(
            page=qb_request.get_page(),
            per_page=qb_request.get_per_page(default=15),
            max_per_page=100
        )
    
    return result


def query_performance_example(session: Session, request: Request) -> Dict[str, Any]:
    """
    Demonstrates query performance features
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    query_builder = QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.exact('status'),
            AllowedFilter.partial('name'),
        ]) \
        .allowed_sorts(['name', 'created_at']) \
        .allowed_includes(['posts'])
    
    # Get SQL and execution plan
    sql = query_builder.to_sql()
    explain = query_builder.explain()
    
    # Get results efficiently
    total_count = query_builder.count()
    distinct_count = query_builder.distinct_count('email')
    exists = query_builder.exists()
    
    # Process in chunks for memory efficiency
    processed_count = 0
    for chunk in query_builder.chunk(size=100):
        processed_count += len(chunk)
        # Process chunk...
    
    return {
        'sql': sql,
        'explain': explain,
        'total_count': total_count,
        'distinct_email_count': distinct_count,
        'has_results': exists,
        'processed_count': processed_count
    }


def error_handling_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates error handling and validation
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.exact('status'),
            # Note: name filter is not allowed
        ]) \
        .allowed_sorts(['email']) \
        .disable_invalid_filter_exception() \
        .disable_invalid_sort_exception() \
        .get()  # Will ignore invalid filters/sorts instead of throwing exceptions


def chaining_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates method chaining and query modification
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    base_query = QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.exact('status'),
            AllowedFilter.partial('name'),
        ]) \
        .allowed_sorts(['name', 'created_at'])
    
    # Clone for different use cases
    active_users = base_query.clone() \
        .filter(User.is_active == True) \
        .default_sort('name') \
        .get()
    
    # Chain additional SQLAlchemy methods
    # Note: User.profile and User.featured don't exist in current User model
    # featured_users = base_query.clone() \
    #     .join(User.profile) \
    #     .filter(User.featured == True) \
    #     .distinct() \
    #     .limit(10) \
    #     .get()
    
    featured_users = base_query.clone() \
        .distinct() \
        .limit(10) \
        .get()
    
    return active_users


def custom_array_delimiters_example(session: Session, request: Request) -> List[User]:
    """
    Demonstrates custom array value delimiters
    
    Example URLs:
    - /users?filter[status]=active;pending;inactive (using semicolon)
    - /users?filter[ids]=1|2|3|4|5 (using pipe)
    """
    qb_request = QueryBuilderRequest.from_request(request)
    
    # Set custom delimiters
    qb_request.set_filters_array_value_delimiter(';')
    
    return QueryBuilder.for_model(User, session, qb_request) \
        .allowed_filters([
            AllowedFilter.exact('status'),
            AllowedFilter.exact('ids', array_delimiter='|'),  # Override per filter
        ]) \
        .get()