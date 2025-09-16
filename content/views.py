from rest_framework import generics, filters
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import State, City, Category
from .serializers import (
    StateSerializer, 
    CitySerializer,
    StateSimpleSerializer,
    CitySimpleSerializer,
    CategorySerializer, 
    CategorySimpleSerializer
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
class CityListView(generics.ListAPIView):
    """List cities with filtering options."""
    
    queryset = City.objects.filter(is_active=True).select_related('state')
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'is_major']
    search_fields = ['name']
    ordering_fields = ['name', 'is_major', 'created_at']
    ordering = ['-is_major', 'name']

class CitySimpleListView(generics.ListAPIView):
    """Simple list of cities for dropdowns."""
    
    queryset = City.objects.filter(is_active=True).select_related('state')
    serializer_class = CitySimpleSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['state']

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
class CategoryListView(generics.ListAPIView):
    """List all active categories."""
    
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']

class CategoryDetailView(generics.RetrieveAPIView):
    """Get details of a specific category."""
    
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class CategorySimpleListView(generics.ListAPIView):
    """Simple list of categories for dropdowns."""
    
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySimpleSerializer
    permission_classes = [AllowAny]
    ordering = ['sort_order', 'name']