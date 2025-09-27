from rest_framework import generics, filters
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from core.simple_mixins import StateAwareViewMixin
from .models import State, City, Category
from .serializers import (
    StateSerializer, 
    CitySerializer,
    StateSimpleSerializer,
    CitySimpleSerializer,
    CategorySerializer, 
    CategorySimpleSerializer,
    CityAutocompleteSerializer
)

# State Views
class StateListView(generics.ListAPIView):
    """List all active states."""
    
    queryset = State.objects.filter(is_active=True)
    serializer_class = StateSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

class StateDetailView(generics.RetrieveAPIView):
    """Get details of a specific state."""
    
    queryset = State.objects.filter(is_active=True)
    serializer_class = StateSerializer
    permission_classes = [AllowAny]
    lookup_field = 'code'

class StateByDomainView(generics.RetrieveAPIView):
    """Get state information based on current domain."""
    
    serializer_class = StateSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        state_code = getattr(self.request, 'state_code', 'IL')
        return State.objects.get(code=state_code, is_active=True)

# City Views
class CityListView(StateAwareViewMixin, generics.ListAPIView):
    """List cities with filtering options - automatically filtered by current state."""
    
    queryset = City.objects.filter(is_active=True).select_related('state')
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_major']
    search_fields = ['name']
    ordering_fields = ['name', 'is_major', 'created_at']
    ordering = ['-is_major', 'name']
    
    # State filtering configuration
    state_field_path = 'state__code'
    allow_cross_state = True  # Allow ?all_states=true for admin use
    cache_timeout = 1800  # 30 minutes cache

class CitySimpleListView(StateAwareViewMixin, generics.ListAPIView):
    """Simple list of cities for dropdowns - automatically filtered by current state."""
    
    queryset = City.objects.filter(is_active=True).select_related('state')
    serializer_class = CitySimpleSerializer
    permission_classes = [AllowAny]
    
    # State filtering configuration
    state_field_path = 'state__code'
    cache_timeout = 3600  # 1 hour cache for simple lists

class CitiesByStateView(generics.ListAPIView):
    """Get cities for a specific state."""
    
    serializer_class = CitySimpleSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        state_code = self.kwargs.get('state_code', '').upper()
        return City.objects.filter(
            state__code=state_code,
            state__is_active=True,
            is_active=True
        ).order_by('-is_major', 'name')

# Category Views
class CategoryListView(StateAwareViewMixin, generics.ListAPIView):
    """List all active categories with state-specific ad counts."""
    
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']
    cache_timeout = 1800  # 30 minutes cache
    
    def get_queryset(self):
        """Get categories with state-specific ad counts."""
        state_code = getattr(self.request, 'state_code', 'IL')
        
        return Category.objects.filter(is_active=True).annotate(
            state_ads_count=Count(
                'ads',
                filter=Q(
                    ads__status='approved',
                    ads__state__code__iexact=state_code,
                    ads__expires_at__gt=timezone.now()
                )
            )
        )

class CategoryDetailView(generics.RetrieveAPIView):
    """Get details of a specific category."""
    
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class CategorySimpleListView(StateAwareViewMixin, generics.ListAPIView):
    """Simple list of categories for dropdowns."""
    
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySimpleSerializer
    permission_classes = [AllowAny]
    ordering = ['sort_order', 'name']
    cache_timeout = 3600  # 1 hour cache for simple lists



class CityAutocompleteView(generics.ListAPIView):
    """Autocomplete search for cities."""
    
    serializer_class = CityAutocompleteSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Search cities by name with optional state filter."""
        query = self.request.query_params.get('q', '').strip()
        state_code = self.request.query_params.get('state', '').strip().upper()
        limit = int(self.request.query_params.get('limit', 10))
        
        if not query:
            return City.objects.none()
        
        # Build queryset
        queryset = City.objects.filter(
            is_active=True,
            name__istartswith=query  # Case-insensitive starts with
        ).select_related('state')
        
        # Filter by state if provided
        if state_code:
            queryset = queryset.filter(state__code=state_code, state__is_active=True)
        
        # Order by major cities first, then alphabetically
        queryset = queryset.order_by('-is_major', 'name')[:limit]
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Return autocomplete results with metadata."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'results': serializer.data,
            'count': len(serializer.data),
            'query': request.query_params.get('q', '')
        })


class CitySearchView(generics.ListAPIView):
    """Advanced city search with multiple filters."""
    
    serializer_class = CityAutocompleteSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Search cities with multiple criteria."""
        query = self.request.query_params.get('q', '').strip()
        state_code = self.request.query_params.get('state', '').strip().upper()
        major_only = self.request.query_params.get('major_only', 'false').lower() == 'true'
        
        queryset = City.objects.filter(is_active=True).select_related('state')
        
        # Text search - search in name
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(state__name__icontains=query)
            )
        
        # State filter
        if state_code:
            queryset = queryset.filter(state__code=state_code, state__is_active=True)
        
        # Major cities only
        if major_only:
            queryset = queryset.filter(is_major=True)
        
        # Order by relevance: major cities first, then alphabetically
        queryset = queryset.order_by('-is_major', 'name')
        
        return queryset