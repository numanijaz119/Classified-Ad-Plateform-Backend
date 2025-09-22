# ads/views.py
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg, F
from django.db.models.functions import TruncDate, TruncMonth
from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta, datetime
import logging
from core.simple_mixins import StateAwareViewMixin

from .models import Ad, AdImage, AdView, AdContact, AdFavorite, AdReport
from .serializers import (
    AdListSerializer,
    AdDetailSerializer,
    AdCreateSerializer,
    AdUpdateSerializer,
    UserAdSerializer,
    AdAnalyticsSerializer,
    AdFavoriteSerializer,
    AdReportSerializer,
    AdPromoteSerializer,
    DashboardStatsSerializer,
    AdImageSerializer
)
from .filters import PublicAdFilter, UserAdFilter
from core.permissions import IsOwnerOrReadOnly
from core.utils import get_client_ip, detect_device_type

logger = logging.getLogger(__name__)

class AdViewSet(StateAwareViewMixin, ModelViewSet):
    """Main ViewSet for Ad operations with state-aware filtering and search."""
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    
    # Simplified ordering for users: newest, oldest, alphabetical
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']  # Default: newest first
    
    # State filtering configuration
    state_field_path = 'state__code'
    allow_cross_state = True  # Allow cross-state search when requested
    
    def get_queryset(self):
        """Get queryset based on action and user with state filtering."""
        if self.action == 'my_ads':
            # User's own ads (all statuses except deleted) - no state filtering for user's own ads
            return Ad.objects.filter(
                user=self.request.user
            ).exclude(status='deleted').select_related(
                'category', 'city', 'state', 'user'
            ).prefetch_related('images')
        
        elif self.action in ['list', 'search', 'featured']:
            # Public listing - only approved, non-expired ads with state filtering
            queryset = Ad.objects.active().select_related(
                'category', 'city', 'state', 'user'
            ).prefetch_related('images')
            
            # State filtering is now handled by StateAwareSearchViewMixin
            # Featured ads first for list view, then by date
            if self.action == 'list':
                queryset = queryset.order_by('-plan', '-created_at')
            elif self.action == 'featured':
                queryset = queryset.featured()
            
            return queryset
        
        else:
            # Detail view - approved ads only for public, all for owners
            return Ad.objects.select_related(
                'category', 'city', 'state', 'user'
            ).prefetch_related('images')
    
    def get_filterset_class(self):
        """Return appropriate filter class based on action."""
        if self.action == 'my_ads':
            return UserAdFilter
        else:
            return PublicAdFilter
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AdCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AdUpdateSerializer
        elif self.action == 'my_ads':
            return UserAdSerializer
        elif self.action == 'analytics':
            return AdAnalyticsSerializer
        elif self.action in ['retrieve']:
            return AdDetailSerializer
        else:
            return AdListSerializer
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['create', 'my_ads', 'analytics', 'promote']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        else:
            return [AllowAny()]
    
    def list(self, request, *args, **kwargs):
        """List ads with simplified sorting options."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Handle custom sorting
        sort_by = request.query_params.get('sort_by', 'newest')
        
        if sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'alphabetical':
            queryset = queryset.order_by('title')
        elif sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        else:  # newest (default)
            queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get detailed view of ad and track the view."""
        instance = self.get_object()
        
        # Check permissions for non-approved ads
        if instance.status != 'approved' and instance.user != request.user:
            return Response(
                {'error': 'Ad not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Track the view for approved ads
        if instance.status == 'approved':
            self.track_view(instance, request)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def track_view(self, ad, request):
        """Track ad view for analytics."""
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        referrer = request.META.get('HTTP_REFERER', '')
        device_type = detect_device_type(user_agent)
        
        # Generate session ID for anonymous users
        session_id = request.session.session_key or f"anon_{ip_address}"
        
        try:
            # Create view record (unique constraint prevents duplicates within timeframe)
            view, created = AdView.objects.get_or_create(
                ad=ad,
                session_id=session_id,
                defaults={
                    'user': request.user if request.user.is_authenticated else None,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'referrer': referrer,
                    'device_type': device_type,
                }
            )
            
            if created:
                # Increment counters
                is_unique = not AdView.objects.filter(
                    ad=ad,
                    ip_address=ip_address
                ).exclude(id=view.id).exists()
                
                ad.increment_view_count(unique=is_unique)
                
        except Exception as e:
            logger.error(f"Error tracking view for ad {ad.id}: {str(e)}")
    
    @action(detail=False, methods=['get'])
    def my_ads(self, request):
        """Get current user's ads with simplified filtering."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Handle sorting for user's ads
        sort_by = request.query_params.get('sort_by', 'newest')
        
        if sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'alphabetical':
            queryset = queryset.order_by('title')
        elif sort_by == 'status':
            queryset = queryset.order_by('status', '-created_at')
        else:  # newest (default)
            queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search with state-aware filtering and cross-state capabilities."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Add state aggregation for cross-state searches
        if request.query_params.get('all_states') == 'true':
            state_breakdown = self.add_state_aggregation(queryset)
            
        # Handle sorting for search results
        sort_by = request.query_params.get('sort_by', 'relevance')
        
        if sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'alphabetical':
            queryset = queryset.order_by('title')
        elif sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        # Default 'relevance' keeps the search ranking
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
            
            # Add state breakdown for cross-state searches
            if request.query_params.get('all_states') == 'true':
                response_data['state_breakdown'] = state_breakdown
            
            return Response(response_data)
        
        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data
        
        # Add state breakdown for cross-state searches
        if request.query_params.get('all_states') == 'true':
            response_data = {
                'results': response_data,
                'state_breakdown': state_breakdown
            }
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get only featured ads."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Handle sorting for featured ads
        sort_by = request.query_params.get('sort_by', 'newest')
        
        if sort_by == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort_by == 'alphabetical':
            queryset = queryset.order_by('title')
        else:  # newest (default)
            queryset = queryset.order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics data for user's ad."""
        ad = self.get_object()
        
        if ad.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        days = int(request.query_params.get('days', 30))
        serializer = self.get_serializer(ad, context={'days': days})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def contact_view(self, request, pk=None):
        """Track when someone views contact information."""
        ad = self.get_object()
        
        if ad.status != 'approved':
            return Response(
                {'error': 'Ad not available'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        contact_type = request.data.get('contact_type', 'both')
        ip_address = get_client_ip(request)
        
        try:
            AdContact.objects.create(
                ad=ad,
                user=request.user if request.user.is_authenticated else None,
                ip_address=ip_address,
                contact_type=contact_type
            )
            
            ad.increment_contact_count()
            
            # Return contact information
            contact_data = {}
            if not ad.hide_phone and ad.contact_phone:
                contact_data['phone'] = ad.contact_phone
            if ad.contact_email_display:
                contact_data['email'] = ad.contact_email_display
                
            return Response(contact_data)
            
        except Exception as e:
            logger.error(f"Error tracking contact view: {str(e)}")
            return Response(
                {'error': 'Failed to get contact information'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def promote(self, request, pk=None):
        """Promote ad to featured status."""
        ad = self.get_object()
        
        if ad.user != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if ad.plan == 'featured' and ad.is_featured_active:
            return Response(
                {'error': 'Ad is already featured'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AdPromoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Here you would integrate with payment processor
        # For now, we'll simulate successful payment
        payment_id = serializer.validated_data.get('payment_id', f"promo_{ad.id}_{timezone.now().timestamp()}")
        
        # Update ad to featured
        ad.plan = 'featured'
        ad.featured_payment_id = payment_id
        ad.featured_expires_at = timezone.now() + timedelta(days=30)
        ad.save(update_fields=['plan', 'featured_payment_id', 'featured_expires_at'])
        
        return Response({
            'message': 'Ad promoted to featured successfully',
            'featured_expires_at': ad.featured_expires_at
        })

# Keep other ViewSets unchanged
class AdImageViewSet(ModelViewSet):
    """ViewSet for managing ad images."""
    
    serializer_class = AdImageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get images for user's ads only."""
        return AdImage.objects.filter(
            ad__user=self.request.user
        ).select_related('ad')
    
    def perform_create(self, serializer):
        """Ensure user owns the ad."""
        ad_id = self.request.data.get('ad')
        ad = get_object_or_404(Ad, id=ad_id, user=self.request.user)
        serializer.save(ad=ad)

class AdFavoriteViewSet(ModelViewSet):
    """ViewSet for managing ad favorites."""
    
    serializer_class = AdFavoriteSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        """Get user's favorites."""
        return AdFavorite.objects.filter(
            user=self.request.user
        ).select_related('ad', 'ad__category', 'ad__city', 'ad__state')
    
    def create(self, request, *args, **kwargs):
        """Add ad to favorites."""
        ad_id = request.data.get('ad')
        
        try:
            ad = Ad.objects.get(id=ad_id, status='approved')
        except Ad.DoesNotExist:
            return Response(
                {'error': 'Ad not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        favorite, created = AdFavorite.objects.get_or_create(
            ad=ad,
            user=request.user
        )
        
        if created:
            # Update favorite count
            ad.favorite_count = ad.favorites.count()
            ad.save(update_fields=['favorite_count'])
            
            serializer = self.get_serializer(favorite)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'message': 'Ad already in favorites'}, 
                status=status.HTTP_200_OK
            )
    
    @action(detail=False, methods=['delete'])
    def remove(self, request):
        """Remove ad from favorites."""
        ad_id = request.data.get('ad')
        
        try:
            favorite = AdFavorite.objects.get(
                ad_id=ad_id,
                user=request.user
            )
            ad = favorite.ad
            favorite.delete()
            
            # Update favorite count
            ad.favorite_count = ad.favorites.count()
            ad.save(update_fields=['favorite_count'])
            
            return Response({'message': 'Removed from favorites'})
            
        except AdFavorite.DoesNotExist:
            return Response(
                {'error': 'Favorite not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class AdReportViewSet(ModelViewSet):
    """ViewSet for reporting ads."""
    
    serializer_class = AdReportSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']
    
    def get_queryset(self):
        """Get user's reports."""
        return AdReport.objects.filter(
            reported_by=self.request.user
        ).select_related('ad')

class DashboardAnalyticsView(generics.GenericAPIView):
    """Dashboard analytics for users."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get dashboard statistics for current user."""
        user = request.user
        
        # Basic stats
        total_ads = user.ads.exclude(status='deleted').count()
        active_ads = user.ads.filter(status='approved').count()
        pending_ads = user.ads.filter(status='pending').count()
        featured_ads = user.ads.filter(plan='featured').count()
        
        # Analytics
        total_views = user.ads.aggregate(
            total=Sum('view_count')
        )['total'] or 0
        
        total_contacts = user.ads.aggregate(
            total=Sum('contact_count')
        )['total'] or 0
        
        total_favorites = user.ads.aggregate(
            total=Sum('favorite_count')
        )['total'] or 0
        
        # This month stats
        this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_ads = user.ads.filter(
            created_at__gte=this_month_start
        ).count()
        
        # Revenue calculation (featured ads * $9.99)
        revenue_this_month = user.ads.filter(
            plan='featured',
            created_at__gte=this_month_start
        ).count() * 9.99
        
        data = {
            'total_ads': total_ads,
            'active_ads': active_ads,
            'pending_ads': pending_ads,
            'featured_ads': featured_ads,
            'total_views': total_views,
            'total_contacts': total_contacts,
            'total_favorites': total_favorites,
            'this_month_ads': this_month_ads,
            'revenue_this_month': revenue_this_month,
        }
        
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)

# End of ads views - admin functionality moved to admin app