# content/banner_views.py
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
    Get active banners for public display.
    Filters by position, state, and category.
    """
    serializer_class = PublicBannerSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Get active banners based on filters."""
        queryset = Banner.objects.filter(is_active=True)
        
        # Filter by current date
        now = timezone.now()
        queryset = queryset.filter(
            Q(start_date__lte=now) | Q(start_date__isnull=True),
            Q(end_date__gte=now) | Q(end_date__isnull=True)
        )
        
        # Filter by position
        position = self.request.GET.get('position')
        if position:
            queryset = queryset.filter(position=position)
        
        # Filter by state (show banners with no state targeting or matching state)
        state = self.request.GET.get('state')
        if state:
            queryset = queryset.filter(
                Q(target_states__code=state) | Q(target_states__isnull=True)
            ).distinct()
        else:
            # If no state specified, only show banners with no state targeting
            queryset = queryset.filter(target_states__isnull=True)
        
        # Filter by category (show banners with no category targeting or matching category)
        category = self.request.GET.get('category')
        if category:
            try:
                category_id = int(category)
                queryset = queryset.filter(
                    Q(target_categories__id=category_id) | Q(target_categories__isnull=True)
                ).distinct()
            except (ValueError, TypeError):
                pass
        else:
            # If no category specified, only show banners with no category targeting
            queryset = queryset.filter(target_categories__isnull=True)
        
        # Order by priority and creation date
        queryset = queryset.order_by('-priority', '-created_at')
        
        return queryset


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
            {'error': 'Invalid data'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    banner_id = serializer.validated_data['banner_id']
    
    try:
        banner = Banner.objects.get(id=banner_id)
        
        # Increment impression count
        banner.impressions = F('impressions') + 1
        banner.save(update_fields=['impressions'])
        
        # Get client info
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Create impression record
        BannerImpression.objects.create(
            banner_id=banner_id,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            page_url=serializer.validated_data.get('page_url', ''),
            user=request.user if request.user.is_authenticated else None
        )
        
        return Response({'success': True})
        
    except Banner.DoesNotExist:
        return Response(
            {'error': 'Banner not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        # Log error but don't expose details
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
            {'error': 'Invalid data'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    banner_id = serializer.validated_data['banner_id']
    
    try:
        banner = Banner.objects.get(id=banner_id)
        
        # Increment click count
        banner.clicks = F('clicks') + 1
        banner.save(update_fields=['clicks'])
        
        # Get client info
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        
        # Create click record
        BannerClick.objects.create(
            banner_id=banner_id,
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            referrer=serializer.validated_data.get('referrer', ''),
            user=request.user if request.user.is_authenticated else None
        )
        
        return Response({'success': True})
        
    except Banner.DoesNotExist:
        return Response(
            {'error': 'Banner not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        # Log error but don't expose details
        print(f"Error tracking click: {str(e)}")
        return Response(
            {'error': 'Failed to track click'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )