from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, F
from administrator.models import Banner, BannerImpression, BannerClick
from .serializers import (
    PublicBannerSerializer,
    BannerImpressionSerializer,
    BannerClickSerializer
)


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


@api_view(['POST'])
@permission_classes([AllowAny])
def track_banner_impression(request):
    """
    Track banner impression.
    Increments impression count and logs details.
    """
    serializer = BannerImpressionSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    banner_id = serializer.validated_data['banner_id']
    
    try:
        banner = Banner.objects.get(id=banner_id)
        
        # Increment impression count using F() to avoid race conditions
        Banner.objects.filter(id=banner_id).update(
            impressions=F('impressions') + 1
        )
        
        # Get client info
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Create impression record
        BannerImpression.objects.create(
            banner=banner,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            page_url=serializer.validated_data.get('page_url', ''),
            user=request.user if request.user.is_authenticated else None
        )
        
        return Response({'success': True, 'message': 'Impression tracked'})
        
    except Banner.DoesNotExist:
        return Response(
            {'error': 'Banner not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        # Log error but don't expose details to client
        print(f"Error tracking impression: {str(e)}")
        return Response(
            {'error': 'Failed to track impression'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def track_banner_click(request):
    """
    Track banner click.
    Increments click count and logs details.
    """
    serializer = BannerClickSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    banner_id = serializer.validated_data['banner_id']
    
    try:
        banner = Banner.objects.get(id=banner_id)
        
        # Increment click count using F() to avoid race conditions
        Banner.objects.filter(id=banner_id).update(
            clicks=F('clicks') + 1
        )
        
        # Get client info
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Create click record
        BannerClick.objects.create(
            banner=banner,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            referrer=serializer.validated_data.get('referrer', ''),
            user=request.user if request.user.is_authenticated else None
        )
        
        return Response({'success': True, 'message': 'Click tracked'})
        
    except Banner.DoesNotExist:
        return Response(
            {'error': 'Banner not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        # Log error but don't expose details to client
        print(f"Error tracking click: {str(e)}")
        return Response(
            {'error': 'Failed to track click'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )