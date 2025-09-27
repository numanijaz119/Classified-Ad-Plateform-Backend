# administrator/views.py
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, Avg, F
from django.db.models.functions import TruncDate, TruncMonth, TruncDay
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from core.simple_mixins import AdminViewMixin
from core.search_mixins import SearchFilterMixin
from core.pagination import LargeResultsSetPagination

from ads.models import Ad, AdView, AdContact, AdFavorite, AdReport
from accounts.models import User
from content.models import Category, State, City
from .models import Banner, AdminSettings
from .serializers import (
    AdminAdSerializer, 
    AdminAdActionSerializer,
    AdminUserSerializer,
    AdminStateSerializer,
    AdminCategorySerializer,
    AdminReportSerializer,
    AdminBannerSerializer,
)

# ============================================================================
# DASHBOARD STATISTICS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    """Get dashboard statistics for admin - can filter by state."""
    
    # Get state filter if provided
    state_filter = request.query_params.get('state')
    
    # Base querysets
    ads_qs = Ad.objects.exclude(status='deleted')
    users_qs = User.objects.all()
    
    # Apply state filter if provided
    if state_filter:
        ads_qs = ads_qs.filter(state__code__iexact=state_filter)
    
    # Basic stats
    total_ads = ads_qs.count()
    pending_ads = ads_qs.filter(status='pending').count()
    active_ads = ads_qs.filter(status='approved').count()
    featured_ads = ads_qs.filter(plan='featured').count()
    
    # User stats
    total_users = users_qs.count()
    active_users = users_qs.filter(is_active=True, is_suspended=False).count()
    suspended_users = users_qs.filter(is_suspended=True).count()
    banned_users = users_qs.filter(is_active=False).count()
    
    # Revenue calculation (featured ads * $10)
    monthly_revenue = ads_qs.filter(
        plan='featured',
        created_at__gte=timezone.now().replace(day=1)
    ).count() * 10
    
    # Recent activity
    recent_ads = ads_qs.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Reports stats
    pending_reports = AdReport.objects.filter(is_reviewed=False).count()
    total_reports = AdReport.objects.count()
    
    return Response({
        'total_ads': total_ads,
        'pending_ads': pending_ads,
        'active_ads': active_ads,
        'featured_ads': featured_ads,
        'total_users': total_users,
        'active_users': active_users,
        'suspended_users': suspended_users,
        'banned_users': banned_users,
        'monthly_revenue': monthly_revenue,
        'recent_ads': recent_ads,
        'pending_reports': pending_reports,
        'total_reports': total_reports,
        'state_filter': state_filter,
    })

# ============================================================================
# ADS MANAGEMENT
# ============================================================================

class AdminAdViewSet(AdminViewMixin, SearchFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Admin ViewSet for managing ads with filtering and search."""
    
    serializer_class = AdminAdSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LargeResultsSetPagination
    
    # State filtering configuration for admin
    state_field_path = 'state__code'
    
    def get_queryset(self):
        """Get ads queryset with admin filtering."""
        return Ad.objects.exclude(status='deleted').select_related(
            'user', 'category', 'city', 'state'
        ).prefetch_related('images')
    
    def get_filterset_class(self):
        """Return admin filter class."""
        from ads.filters import AdminAdFilter
        return AdminAdFilter
    
    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """Perform actions on ads (approve, reject, delete, feature)."""
        ad = self.get_object()
        action = request.data.get('action')
        reason = request.data.get('reason', '')
        admin_notes = request.data.get('admin_notes', '')
        
        if action == 'approve':
            ad.status = 'approved'
            ad.approved_by = request.user
            ad.approved_at = timezone.now()
            message = 'Ad approved successfully'
            
        elif action == 'reject':
            ad.status = 'rejected'
            ad.rejection_reason = reason or 'Rejected by admin'
            ad.admin_notes = admin_notes
            message = 'Ad rejected successfully'
            
        elif action == 'delete':
            ad.status = 'deleted'
            ad.admin_notes = admin_notes
            message = 'Ad deleted successfully'
            
        elif action == 'feature':
            ad.plan = 'featured'
            ad.featured_expires_at = timezone.now() + timedelta(days=30)
            message = 'Ad made featured successfully'
            
        elif action == 'unfeature':
            ad.plan = 'free'
            ad.featured_expires_at = None
            message = 'Ad removed from featured successfully'
            
        else:
            return Response({'error': 'Invalid action'}, status=400)
        
        ad.save()
        
        return Response({
            'message': message,
            'ad_status': ad.status,
            'ad_plan': ad.plan
        })
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on multiple ads."""
        ad_ids = request.data.get('ad_ids', [])
        action = request.data.get('action')
        reason = request.data.get('reason', '')
        admin_notes = request.data.get('admin_notes', '')
        
        if not ad_ids or action not in ['approve', 'reject', 'delete', 'feature', 'unfeature']:
            return Response({'error': 'Invalid data provided'}, status=400)
        
        ads = Ad.objects.filter(id__in=ad_ids)
        
        if not ads.exists():
            return Response({'error': 'No ads found with provided IDs'}, status=404)
        
        updated_count = 0
        
        for ad in ads:
            if action == 'approve':
                ad.status = 'approved'
                ad.approved_by = request.user
                ad.approved_at = timezone.now()
            elif action == 'reject':
                ad.status = 'rejected'
                ad.rejection_reason = reason or 'Rejected by admin'
                ad.admin_notes = admin_notes
            elif action == 'delete':
                ad.status = 'deleted'
                ad.admin_notes = admin_notes
            elif action == 'feature':
                ad.plan = 'featured'
                ad.featured_expires_at = timezone.now() + timedelta(days=30)
            elif action == 'unfeature':
                ad.plan = 'free'
                ad.featured_expires_at = None
            
            ad.save()
            updated_count += 1
        
        return Response({
            'message': f'{updated_count} ads updated successfully',
            'updated_count': updated_count
        })


# ============================================================================
# USER MANAGEMENT
# ============================================================================

class AdminUserViewSet(AdminViewMixin, SearchFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Admin ViewSet for managing users with filtering and search."""
    
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LargeResultsSetPagination
    
    def get_queryset(self):
        """Get users queryset with admin filtering."""
        return User.objects.select_related().prefetch_related('ads')
    
    @action(detail=True, methods=['post'])
    def action(self, request, pk=None):
        """Ban, suspend, or activate users."""
        user = self.get_object()
        action = request.data.get('action')
        reason = request.data.get('reason', '')
        
        if action == 'ban':
            user.is_active = False
            user.is_suspended = True
            user.suspension_reason = reason
            message = 'User banned successfully'
            
        elif action == 'suspend':
            user.is_suspended = True
            user.suspension_reason = reason
            message = 'User suspended successfully'
            
        elif action == 'activate':
            user.is_active = True
            user.is_suspended = False
            user.suspension_reason = ''
            message = 'User activated successfully'
            
        else:
            return Response({'error': 'Invalid action'}, status=400)
        
        user.save()
        
        return Response({
            'message': message,
            'user_status': {
                'is_active': user.is_active,
                'is_suspended': user.is_suspended,
                'suspension_reason': user.suspension_reason
            }
        })
    
    @action(detail=True, methods=['get'])
    def activity(self, request, pk=None):
        """Get user activity logs."""
        user = self.get_object()
        
        # Get user's ads activity
        ads_data = {
            'total_ads': user.ads.exclude(status='deleted').count(),
            'active_ads': user.ads.filter(status='approved').count(),
            'pending_ads': user.ads.filter(status='pending').count(),
            'rejected_ads': user.ads.filter(status='rejected').count(),
            'featured_ads': user.ads.filter(plan='featured').count(),
        }
        
        # Get recent ads
        recent_ads = user.ads.exclude(status='deleted').order_by('-created_at')[:10]
        recent_ads_data = AdminAdSerializer(recent_ads, many=True).data
        
        return Response({
            'user': AdminUserSerializer(user).data,
            'ads_statistics': ads_data,
            'recent_ads': recent_ads_data,
        })

# Legacy function-based view (to be removed after URL updates)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_users_list(request):
    """Get users list for admin."""
    
    search = request.query_params.get('search', '')
    status_filter = request.query_params.get('status', 'all')
    
    queryset = User.objects.select_related().prefetch_related('ads')
    
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True, is_suspended=False)
    elif status_filter == 'suspended':
        queryset = queryset.filter(is_suspended=True)
    elif status_filter == 'banned':
        queryset = queryset.filter(is_active=False)
    
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    page_size = int(request.query_params.get('page_size', 20))
    page = int(request.query_params.get('page', 1))
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    users_data = AdminUserSerializer(page_obj, many=True).data
    
    return Response({
        'users': users_data,
        'total_count': paginator.count,
        'page': page,
        'page_size': page_size,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_user_action(request, user_id):
    """Ban, suspend, or activate users."""
    
    user = get_object_or_404(User, id=user_id)
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    
    if action == 'ban':
        user.is_active = False
        user.is_suspended = True
        user.suspension_reason = reason
        message = 'User banned successfully'
        
    elif action == 'suspend':
        user.is_suspended = True
        user.suspension_reason = reason
        message = 'User suspended successfully'
        
    elif action == 'activate':
        user.is_active = True
        user.is_suspended = False
        user.suspension_reason = ''
        message = 'User activated successfully'
        
    else:
        return Response({'error': 'Invalid action'}, status=400)
    
    user.save()
    
    return Response({
        'message': message,
        'user_status': {
            'is_active': user.is_active,
            'is_suspended': user.is_suspended,
            'suspension_reason': user.suspension_reason
        }
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_user_activity(request, user_id):
    """Get user activity logs."""
    
    user = get_object_or_404(User, id=user_id)
    
    # Get user's ads activity
    ads_data = {
        'total_ads': user.ads.exclude(status='deleted').count(),
        'active_ads': user.ads.filter(status='approved').count(),
        'pending_ads': user.ads.filter(status='pending').count(),
        'rejected_ads': user.ads.filter(status='rejected').count(),
        'featured_ads': user.ads.filter(plan='featured').count(),
    }
    
    # Get recent ads
    recent_ads = user.ads.exclude(status='deleted').order_by('-created_at')[:10]
    recent_ads_data = AdminAdSerializer(recent_ads, many=True).data
    
    return Response({
        'user': AdminUserSerializer(user).data,
        'ads_statistics': ads_data,
        'recent_ads': recent_ads_data,
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_bulk_user_action(request):
    """Perform bulk actions on multiple users."""
    
    user_ids = request.data.get('user_ids', [])
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    
    if not user_ids or action not in ['ban', 'suspend', 'activate']:
        return Response({'error': 'Invalid data provided'}, status=400)
    
    users = User.objects.filter(id__in=user_ids)
    
    if not users.exists():
        return Response({'error': 'No users found with provided IDs'}, status=404)
    
    updated_count = 0
    
    for user in users:
        if action == 'ban':
            user.is_active = False
            user.is_suspended = True
            user.suspension_reason = reason
        elif action == 'suspend':
            user.is_suspended = True
            user.suspension_reason = reason
        elif action == 'activate':
            user.is_active = True
            user.is_suspended = False
            user.suspension_reason = ''
        
        user.save()
        updated_count += 1
    
    return Response({
        'message': f'Successfully {action}ed {updated_count} users',
        'updated_count': updated_count
    })

# ============================================================================
# REPORTS MANAGEMENT
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_reports_list(request):
    """Get all ad reports for admin review."""
    
    status_filter = request.query_params.get('status', 'pending')
    reason_filter = request.query_params.get('reason', 'all')
    
    queryset = AdReport.objects.select_related('ad', 'reported_by', 'reviewed_by')
    
    if status_filter == 'pending':
        queryset = queryset.filter(is_reviewed=False)
    elif status_filter == 'reviewed':
        queryset = queryset.filter(is_reviewed=True)
    
    if reason_filter != 'all':
        queryset = queryset.filter(reason=reason_filter)
    
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    page_size = int(request.query_params.get('page_size', 20))
    page = int(request.query_params.get('page', 1))
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    
    reports_data = AdminReportSerializer(page_obj, many=True).data
    
    return Response({
        'reports': reports_data,
        'total_count': paginator.count,
        'page': page,
        'page_size': page_size,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_report_action(request, report_id):
    """Handle reports (approve/dismiss)."""
    
    report = get_object_or_404(AdReport, id=report_id)
    action = request.data.get('action')
    admin_notes = request.data.get('admin_notes', '')
    
    if action == 'approve':
        # Mark report as reviewed and take action on the ad
        report.is_reviewed = True
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.admin_notes = admin_notes
        
        # Take action on the reported ad based on the report reason
        ad = report.ad
        if report.reason in ['spam', 'fraud']:
            ad.status = 'rejected'
            ad.rejection_reason = f'Reported as {report.get_reason_display()}'
        elif report.reason == 'inappropriate':
            ad.status = 'pending'  # Send back for review
        
        ad.save()
        message = 'Report approved and action taken on ad'
        
    elif action == 'dismiss':
        report.is_reviewed = True
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.admin_notes = admin_notes or 'Report dismissed - no action needed'
        message = 'Report dismissed'
        
    else:
        return Response({'error': 'Invalid action'}, status=400)
    
    report.save()
    
    return Response({
        'message': message,
        'report_status': 'reviewed'
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_bulk_report_action(request):
    """Perform bulk actions on multiple reports."""
    
    report_ids = request.data.get('report_ids', [])
    action = request.data.get('action')
    admin_notes = request.data.get('admin_notes', '')
    
    if not report_ids or action not in ['approve', 'dismiss']:
        return Response({'error': 'Invalid data provided'}, status=400)
    
    reports = AdReport.objects.filter(id__in=report_ids, is_reviewed=False)
    updated_count = 0
    
    for report in reports:
        report.is_reviewed = True
        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        report.admin_notes = admin_notes
        
        if action == 'approve':
            # Take action on the reported ad
            ad = report.ad
            if report.reason in ['spam', 'fraud']:
                ad.status = 'rejected'
                ad.rejection_reason = f'Reported as {report.get_reason_display()}'
                ad.save()
        
        report.save()
        updated_count += 1
    
    return Response({
        'message': f'Successfully {action}ed {updated_count} reports',
        'updated_count': updated_count
    })

# ============================================================================
# ANALYTICS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics_overview(request):
    """Platform overview analytics with charts data."""
    
    days = int(request.query_params.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Daily ads creation
    daily_ads = Ad.objects.filter(
        created_at__gte=start_date
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Daily user registrations
    daily_users = User.objects.filter(
        created_at__gte=start_date
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Page views (if you have tracking)
    daily_views = AdView.objects.filter(
        created_at__gte=start_date
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Category performance
    category_stats = Category.objects.annotate(
        total_ads=Count('ads'),
        active_ads=Count('ads', filter=Q(ads__status='approved'))
    ).order_by('-total_ads')
    
    return Response({
        'daily_ads': list(daily_ads),
        'daily_users': list(daily_users),
        'daily_views': list(daily_views),
        'category_stats': [
            {
                'name': cat.name,
                'total_ads': cat.total_ads,
                'active_ads': cat.active_ads
            }
            for cat in category_stats[:10]
        ]
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics_users(request):
    """User growth analytics."""
    
    days = int(request.query_params.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # User growth over time
    user_growth = User.objects.filter(
        created_at__gte=start_date
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        new_users=Count('id')
    ).order_by('day')
    
    # User activity stats
    active_users = User.objects.filter(is_active=True, is_suspended=False).count()
    suspended_users = User.objects.filter(is_suspended=True).count()
    banned_users = User.objects.filter(is_active=False).count()
    
    # Top users by ads
    top_users = User.objects.annotate(
        ads_count=Count('ads', filter=Q(ads__status='approved'))
    ).filter(ads_count__gt=0).order_by('-ads_count')[:10]
    
    return Response({
        'user_growth': list(user_growth),
        'user_stats': {
            'active': active_users,
            'suspended': suspended_users,
            'banned': banned_users,
            'total': active_users + suspended_users + banned_users
        },
        'top_users': [
            {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'ads_count': user.ads_count,
                'joined': user.created_at
            }
            for user in top_users
        ]
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics_revenue(request):
    """Revenue analytics with monthly breakdown."""
    
    # Monthly revenue for last 12 months
    end_date = timezone.now()
    start_date = end_date - timedelta(days=365)
    
    monthly_revenue = Ad.objects.filter(
        plan='featured',
        created_at__gte=start_date
    ).extra(
        select={'month': "to_char(created_at, 'YYYY-MM')"}
    ).values('month').annotate(
        featured_ads=Count('id'),
        revenue=Count('id') * 10  # $10 per featured ad
    ).order_by('month')
    
    # State-wise revenue
    state_revenue = Ad.objects.filter(
        plan='featured'
    ).values('state__name', 'state__code').annotate(
        featured_ads=Count('id'),
        revenue=Count('id') * 10
    ).order_by('-revenue')
    
    total_revenue = sum(item['revenue'] for item in monthly_revenue)
    total_featured_ads = sum(item['featured_ads'] for item in monthly_revenue)
    
    return Response({
        'monthly_revenue': list(monthly_revenue),
        'state_revenue': list(state_revenue),
        'totals': {
            'total_revenue': total_revenue,
            'total_featured_ads': total_featured_ads,
            'average_monthly': total_revenue / 12 if monthly_revenue else 0
        }
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics_geographic(request):
    """Geographic analytics - performance by state and city."""
    
    # State-wise performance
    state_stats = State.objects.annotate(
        total_ads=Count('ads', filter=Q(ads__status='approved')),
        total_users=Count('ads__user', distinct=True),
        featured_ads=Count('ads', filter=Q(ads__plan='featured')),
        revenue=Count('ads', filter=Q(ads__plan='featured')) * 10
    ).filter(is_active=True).order_by('-total_ads')
    
    # Top performing cities
    city_stats = City.objects.annotate(
        total_ads=Count('ads', filter=Q(ads__status='approved')),
        avg_price=Avg('ads__price', filter=Q(ads__status='approved'))
    ).filter(is_active=True, total_ads__gt=0).order_by('-total_ads')[:20]
    
    return Response({
        'state_performance': [
            {
                'state': state.name,
                'code': state.code,
                'total_ads': state.total_ads,
                'total_users': state.total_users,
                'featured_ads': state.featured_ads,
                'revenue': state.revenue
            }
            for state in state_stats
        ],
        'top_cities': [
            {
                'city': city.name,
                'state': city.state.name,
                'total_ads': city.total_ads,
                'avg_price': float(city.avg_price) if city.avg_price else 0
            }
            for city in city_stats
        ]
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics_categories(request):
    """Category performance analytics."""
    
    categories = Category.objects.annotate(
        total_ads=Count('ads', filter=Q(ads__status='approved')),
        pending_ads=Count('ads', filter=Q(ads__status='pending')),
        avg_price=Avg('ads__price', filter=Q(ads__status='approved')),
        total_views=Sum('ads__view_count'),
        total_contacts=Sum('ads__contact_count')
    ).filter(is_active=True).order_by('-total_ads')
    
    return Response({
        'category_performance': [
            {
                'id': cat.id,
                'name': cat.name,
                'total_ads': cat.total_ads,
                'pending_ads': cat.pending_ads,
                'avg_price': float(cat.avg_price) if cat.avg_price else 0,
                'total_views': cat.total_views or 0,
                'total_contacts': cat.total_contacts or 0,
                'conversion_rate': (
                    (cat.total_contacts / cat.total_views * 100) 
                    if cat.total_views and cat.total_contacts else 0
                )
            }
            for cat in categories
        ]
    })

# ============================================================================
# BANNER MANAGEMENT
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def admin_banners_list(request):
    """List or create banner advertisements."""
    
    if request.method == 'GET':
        banners = Banner.objects.all().order_by('-created_at')
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        paginator = Paginator(banners, page_size)
        page_obj = paginator.get_page(page)
        
        banners_data = AdminBannerSerializer(page_obj, many=True).data
        
        return Response({
            'banners': banners_data,
            'total_count': paginator.count,
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        })
    
    elif request.method == 'POST':
        serializer = AdminBannerSerializer(data=request.data)
        if serializer.is_valid():
            banner = serializer.save(created_by=request.user)
            return Response(AdminBannerSerializer(banner).data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def admin_banner_detail(request, banner_id):
    """Get, update, or delete a specific banner."""
    
    banner = get_object_or_404(Banner, id=banner_id)
    
    if request.method == 'GET':
        return Response(AdminBannerSerializer(banner).data)
    
    elif request.method == 'PUT':
        serializer = AdminBannerSerializer(banner, data=request.data, partial=True)
        if serializer.is_valid():
            banner = serializer.save()
            return Response(AdminBannerSerializer(banner).data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        banner.delete()
        return Response({'message': 'Banner deleted successfully'})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_banner_toggle(request, banner_id):
    """Toggle banner active status."""
    
    banner = get_object_or_404(Banner, id=banner_id)
    banner.is_active = not banner.is_active
    banner.save()
    
    action = 'activated' if banner.is_active else 'deactivated'
    
    return Response({
        'message': f'Banner {action} successfully',
        'is_active': banner.is_active
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_banner_analytics(request, banner_id):
    """Get detailed analytics for a specific banner."""
    
    banner = get_object_or_404(Banner, id=banner_id)
    
    # Daily performance for last 30 days
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    from .models import BannerImpression, BannerClick
    
    daily_impressions = BannerImpression.objects.filter(
        banner=banner,
        viewed_at__gte=start_date
    ).extra(
        select={'day': 'date(viewed_at)'}
    ).values('day').annotate(
        impressions=Count('id')
    ).order_by('day')
    
    daily_clicks = BannerClick.objects.filter(
        banner=banner,
        clicked_at__gte=start_date
    ).extra(
        select={'day': 'date(clicked_at)'}
    ).values('day').annotate(
        clicks=Count('id')
    ).order_by('day')
    
    return Response({
        'banner_info': {
            'id': banner.id,
            'title': banner.title,
            'total_impressions': banner.impressions,
            'total_clicks': banner.clicks,
            'ctr': banner.ctr
        },
        'daily_impressions': list(daily_impressions),
        'daily_clicks': list(daily_clicks),
    })

# ============================================================================
# CONTENT MANAGEMENT
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_states_list(request):
    """Get list of states for admin filtering."""
    
    states = State.objects.filter(is_active=True).order_by('name')
    
    states_data = []
    for state in states:
        # Get stats for this state
        ads_count = Ad.objects.filter(state=state).exclude(status='deleted').count()
        active_ads = Ad.objects.filter(state=state, status='approved').count()
        users_count = Ad.objects.filter(state=state).values('user').distinct().count()
        
        states_data.append({
            'id': state.id,
            'code': state.code,
            'name': state.name,
            'domain': state.domain,
            'total_ads': ads_count,
            'active_ads': active_ads,
            'users_count': users_count,
        })
    
    return Response({'states': states_data})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_categories_stats(request):
    """Get category statistics."""
    
    state_filter = request.query_params.get('state')
    
    categories = Category.objects.filter(is_active=True)
    
    categories_data = []
    for category in categories:
        ads_qs = category.ads.exclude(status='deleted')
        
        if state_filter:
            ads_qs = ads_qs.filter(state__code__iexact=state_filter)
        
        categories_data.append({
            'id': category.id,
            'name': category.name,
            'icon': category.icon,
            'total_ads': ads_qs.count(),
            'active_ads': ads_qs.filter(status='approved').count(),
            'pending_ads': ads_qs.filter(status='pending').count(),
            'is_active': category.is_active,
        })
    
    return Response({'categories': categories_data})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_category_create(request):
    """Create a new category."""
    
    serializer = AdminCategorySerializer(data=request.data)
    if serializer.is_valid():
        category = serializer.save()
        return Response(AdminCategorySerializer(category).data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def admin_category_detail(request, category_id):
    """Get, update, or delete a specific category."""
    
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'GET':
        return Response(AdminCategorySerializer(category).data)
    
    elif request.method == 'PUT':
        serializer = AdminCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            category = serializer.save()
            return Response(AdminCategorySerializer(category).data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        if category.ads.exists():
            return Response(
                {'error': 'Cannot delete category with existing ads'}, 
                status=400
            )
        
        category.delete()
        return Response({'message': 'Category deleted successfully'})

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_city_create(request):
    """Add a new city."""
    
    from .serializers import AdminCitySerializer
    
    serializer = AdminCitySerializer(data=request.data)
    if serializer.is_valid():
        city = serializer.save()
        return Response(AdminCitySerializer(city).data, status=201)
    return Response(serializer.errors, status=400)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdminUser])
def admin_city_detail(request, city_id):
    """Get, update, or delete a specific city."""
    
    city = get_object_or_404(City, id=city_id)
    
    if request.method == 'GET':
        from .serializers import AdminCitySerializer
        return Response(AdminCitySerializer(city).data)
    
    elif request.method == 'PUT':
        from .serializers import AdminCitySerializer
        serializer = AdminCitySerializer(city, data=request.data, partial=True)
        if serializer.is_valid():
            city = serializer.save()
            return Response(AdminCitySerializer(city).data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        if city.ads.exists():
            return Response(
                {'error': 'Cannot delete city with existing ads'}, 
                status=400
            )
        
        city.delete()
        return Response({'message': 'City deleted successfully'})

# ============================================================================
# SYSTEM SETTINGS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_settings(request):
    """Get current admin settings."""
    
    settings = AdminSettings.get_settings()
    from .serializers import AdminSettingsSerializer
    serializer = AdminSettingsSerializer(settings)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def admin_settings_update(request):
    """Update admin settings."""
    
    settings = AdminSettings.get_settings()
    from .serializers import AdminSettingsSerializer
    serializer = AdminSettingsSerializer(settings, data=request.data, partial=True)
    
    if serializer.is_valid():
        settings = serializer.save(updated_by=request.user)
        return Response(AdminSettingsSerializer(settings).data)
    
    return Response(serializer.errors, status=400)

# ============================================================================
# DATA EXPORT
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_export_ads(request):
    """Export ads data to CSV."""
    
    import csv
    from django.http import HttpResponse
    
    format_type = request.GET.get('format', 'csv')
    
    ads = Ad.objects.exclude(status='deleted').select_related(
        'user', 'category', 'city', 'state'
    ).order_by('-created_at')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="ads_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Title', 'Description', 'Price', 'Status', 'Plan',
            'Category', 'City', 'State', 'User Email', 'Views', 'Contacts',
            'Created At', 'Updated At'
        ])
        
        for ad in ads:
            writer.writerow([
                ad.id, ad.title, ad.description, ad.price, ad.status, ad.plan,
                ad.category.name, ad.city.name, ad.state.name, ad.user.email,
                ad.view_count, ad.contact_count, ad.created_at, ad.updated_at
            ])
        
        return response
    
    elif format_type == 'json':
        import json
        data = AdminAdSerializer(ads, many=True).data
        
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="ads_export.json"'
        return response

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_export_users(request):
    """Export users data to CSV."""
    
    import csv
    from django.http import HttpResponse
    
    users = User.objects.all().order_by('-created_at')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Email', 'First Name', 'Last Name', 'Phone',
        'Is Active', 'Is Suspended', 'Email Verified',
        'Total Ads', 'Created At', 'Last Login'
    ])
    
    for user in users:
        writer.writerow([
            user.id, user.email, user.first_name, user.last_name, user.phone,
            user.is_active, user.is_suspended, user.email_verified,
            user.ads.exclude(status='deleted').count(),
            user.created_at, user.last_login
        ])
    
    return response

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_export_reports(request):
    """Export reports data to CSV."""
    
    import csv
    from django.http import HttpResponse
    
    reports = AdReport.objects.all().select_related(
        'ad', 'reported_by', 'reviewed_by'
    ).order_by('-created_at')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reports_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Ad Title', 'Reason', 'Description', 'Reporter Email',
        'Is Reviewed', 'Reviewer Email', 'Admin Notes',
        'Created At', 'Reviewed At'
    ])
    
    for report in reports:
        writer.writerow([
            report.id, report.ad.title, report.get_reason_display(), 
            report.description, report.reported_by.email,
            report.is_reviewed, 
            report.reviewed_by.email if report.reviewed_by else '',
            report.admin_notes, report.created_at, report.reviewed_at
        ])
    
    return response

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_export_analytics(request):
    """Export analytics data to CSV."""
    
    import csv
    from django.http import HttpResponse
    
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Get daily stats
    daily_stats = []
    current_date = start_date
    
    while current_date <= end_date:
        day_ads = Ad.objects.filter(
            created_at__date=current_date.date()
        ).count()
        
        day_users = User.objects.filter(
            created_at__date=current_date.date()
        ).count()
        
        daily_stats.append({
            'date': current_date.date(),
            'new_ads': day_ads,
            'new_users': day_users
        })
        
        current_date += timedelta(days=1)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="analytics_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'New Ads', 'New Users'])
    
    for stat in daily_stats:
        writer.writerow([stat['date'], stat['new_ads'], stat['new_users']])
    
    return response

# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_clear_cache(request):
    """Clear application cache."""
    
    from django.core.cache import cache
    
    try:
        cache.clear()
        return Response({'message': 'Cache cleared successfully'})
    
    except Exception as e:
        return Response({'error': f'Failed to clear cache: {str(e)}'}, status=500)

@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def admin_maintenance_mode(request):
    """Get or set maintenance mode status."""
    
    from django.core.cache import cache
    
    if request.method == 'GET':
        # Check if maintenance mode is enabled
        maintenance_enabled = cache.get('maintenance_mode', False)
        return Response({
            'maintenance_mode': maintenance_enabled,
            'message': cache.get('maintenance_message', 'Site under maintenance')
        })
    
    elif request.method == 'POST':
        enabled = request.data.get('enabled', False)
        message = request.data.get('message', 'Site under maintenance')
        
        if enabled:
            cache.set('maintenance_mode', True, timeout=None)
            cache.set('maintenance_message', message, timeout=None)
            action_desc = 'Enabled maintenance mode'
        else:
            cache.delete('maintenance_mode')
            cache.delete('maintenance_message')
            action_desc = 'Disabled maintenance mode'
        
        return Response({
            'message': action_desc,
            'maintenance_mode': enabled
        })