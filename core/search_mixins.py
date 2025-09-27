from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache


class SearchFilterMixin:
    """Mixin to add search and filtering to ViewSets."""
    
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title', 'price', 'view_count']
    ordering = ['-created_at']
    
    def get_filterset_class(self):
        """Return appropriate filter class."""
        from ads.filters import PublicAdFilter
        return PublicAdFilter
    
    def filter_queryset(self, queryset):
        """Apply filters and handle special cases."""
        queryset = super().filter_queryset(queryset)
        # Handle sort_by parameter from frontend
        sort_by = self.request.query_params.get('sort_by')
        if sort_by:
            sort_mapping = {
                'newest': '-created_at',
                'oldest': 'created_at', 
                'alphabetical': 'title',
                'price_low': 'price',
                'price_high': '-price',
                'views': '-view_count',
                'relevance': '-rank',
            }
            
            order_by = sort_mapping.get(sort_by)
            if order_by:
                queryset = queryset.order_by(order_by)
        
        return queryset


class StateAwareSearchMixin(SearchFilterMixin):
    """Search mixin aware of multi-state architecture."""
    
    def get_queryset(self):
        """Filter by current state automatically."""
        queryset = super().get_queryset()
        
        # Get state code from request
        state_code = getattr(self.request, 'state_code', None)
        
        # Admin users see all states
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset
        
        # Filter by current state
        if state_code:
            queryset = queryset.filter(state__code__iexact=state_code)
        
        return queryset


class CachedSearchMixin:
    """Mixin to add caching to search results."""
    
    cache_timeout = 300  # 5 minutes
    
    def list(self, request, *args, **kwargs):
        """Cache list results."""
        cache_key = self.get_cache_key(request)
        
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return cached_response
        
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response, self.cache_timeout)
        
        return response
    
    def get_cache_key(self, request):
        """Generate cache key from request params."""
        params = request.query_params.copy()
        params.pop('page', None)
        
        sorted_params = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"ad_search:{sorted_params}"