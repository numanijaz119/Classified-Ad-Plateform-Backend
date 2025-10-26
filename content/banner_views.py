from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from administrator.models import Banner
from .serializers import PublicBannerSerializer


class PublicBannerListView(generics.ListAPIView):
    """
    Public API endpoint to fetch active banner ads
    Supports filtering by position, state, and category
    No authentication required
    """
    serializer_class = PublicBannerSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """
        Filter banners based on query parameters and activity status
        """
        queryset = Banner.objects.filter(is_active=True)
        
        # Filter by current date range
        now = timezone.now()
        queryset = queryset.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        
        # Filter by position
        position = self.request.query_params.get('position', None)
        if position:
            queryset = queryset.filter(position=position)
        
        # Filter by state
        state = self.request.query_params.get('state', None)
        if state:
            # Show banners that either:
            # 1. Have no state targeting (show to all)
            # 2. Include this specific state
            queryset = queryset.filter(
                Q(target_states__isnull=True) | 
                Q(target_states__code=state)
            ).distinct()
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            try:
                category_id = int(category)
                # Show banners that either:
                # 1. Have no category targeting (show to all)
                # 2. Include this specific category
                queryset = queryset.filter(
                    Q(target_categories__isnull=True) |
                    Q(target_categories__id=category_id)
                ).distinct()
            except (ValueError, TypeError):
                pass
        
        # Order by priority (higher priority first) and creation date
        queryset = queryset.order_by('-priority', '-created_at')
        
        # Limit results to prevent overwhelming the frontend
        # Return top 5 banners per position
        queryset = queryset[:5]
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Override list to add custom response handling"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Always return a list, even if empty
        return Response(serializer.data, status=status.HTTP_200_OK)