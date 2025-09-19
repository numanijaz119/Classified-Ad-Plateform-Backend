from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend

from .models import Ad, AdView
from .serializers import (
    AdListSerializer, 
    AdDetailSerializer, 
    AdCreateSerializer,
    UserAdSerializer
)
from .filters import AdFilter
from core.permissions import IsOwnerOrReadOnly
from core.utils import get_client_ip

class AdListCreateView(generics.ListCreateAPIView):
    """List ads with filtering or create new ad."""
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AdFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'view_count', 'plan']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Only show approved, non-expired ads for public listing
        queryset = Ad.objects.filter(
            status='approved',
            expires_at__gt=timezone.now()
        ).select_related('category', 'city', 'state', 'user').prefetch_related('images')
        
        # Filter by current state if not explicitly specified
        if not self.request.query_params.get('state'):
            state_code = getattr(self.request, 'state_code', 'IL')
            queryset = queryset.filter(state__code=state_code)
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdCreateSerializer
        return AdListSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

class AdDetailView(generics.RetrieveAPIView):
    """Get detailed view of a specific ad."""
    
    queryset = Ad.objects.filter(
        status='approved'
    ).select_related('category', 'city', 'state', 'user').prefetch_related('images')
    serializer_class = AdDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track the view
        self.track_view(instance, request)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def track_view(self, ad, request):
        """Track ad view for analytics."""
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate if too long
        
        try:
            # Create view record (unique constraint prevents duplicates)
            AdView.objects.create(
                ad=ad,
                user=request.user if request.user.is_authenticated else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
            # Increment counter
            ad.increment_view_count()
        except Exception:
            # Duplicate view or other error - ignore
            pass
    
class UserAdListView(generics.ListAPIView):
    """Get current user's ads with all statuses."""
    
    serializer_class = UserAdSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'status', 'view_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Show all user's ads including pending and rejected
        return Ad.objects.filter(
            user=self.request.user
        ).exclude(status='deleted').select_related(
            'category', 'city', 'state'
        ).prefetch_related('images')

class AdSearchView(generics.ListAPIView):
    """Advanced search endpoint for ads."""
    
    serializer_class = AdListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = AdFilter
    search_fields = ['title', 'description', 'category__name']
    
    def get_queryset(self):
        queryset = Ad.objects.filter(
            status='approved',
            expires_at__gt=timezone.now()
        ).select_related('category', 'city', 'state').prefetch_related('images')
        
        # Apply state filtering
        state_code = self.request.query_params.get('state') or getattr(self.request, 'state_code', 'IL')
        queryset = queryset.filter(state__code__iexact=state_code)
        
        # Featured ads first
        queryset = queryset.order_by('-plan', '-created_at')
        
        return queryset

class FeaturedAdListView(generics.ListAPIView):
    """List only featured ads."""
    
    serializer_class = AdListSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Ad.objects.filter(
            status='approved',
            plan='featured',
            expires_at__gt=timezone.now()
        ).select_related('category', 'city', 'state').prefetch_related('images')
        
        # Filter by current state
        state_code = getattr(self.request, 'state_code', 'IL')
        queryset = queryset.filter(state__code=state_code)
        
        return queryset.order_by('-created_at')
    

from rest_framework.decorators import action

class AdUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete user's own ad."""
    
    serializer_class = AdCreateSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'slug'
    
    def get_queryset(self):
        # Only allow users to edit/delete their own ads
        return Ad.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        # Reset approval status when ad is updated
        serializer.save(
            status='pending',
            approved_at=None,
            approved_by=None
        )
    
    def destroy(self, request, *args, **kwargs):
        ad = self.get_object()
        
        # Check if user owns the ad
        if ad.user != request.user:
            return Response(
                {'error': 'You can only delete your own ads'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete - just mark as deleted instead of actually deleting
        ad.status = 'deleted'
        ad.save(update_fields=['status'])
        
        return Response({
            'message': 'Ad deleted successfully'
        }, status=status.HTTP_200_OK)

class UserAdListView(generics.ListAPIView):
    """Get current user's ads with all statuses."""
    
    serializer_class = UserAdSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'status', 'view_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Show all user's ads including pending and rejected
        return Ad.objects.filter(
            user=self.request.user
        ).exclude(status='deleted').select_related(
            'category', 'city', 'state'
        ).prefetch_related('images')