from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, Avg, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
from core.simple_mixins import AdminViewMixin

from ads.models import Ad, AdView, AdContact, AdFavorite, AdReport
from accounts.models import User
from content.models import Category, State, City
from .serializers import (
    AdminAdSerializer, 
    AdminAdActionSerializer,
    AdminUserSerializer,
    AdminStateSerializer,
    AdminCategorySerializer
)

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
        # Users don't have direct state relationship, so we don't filter them
    
    # Basic stats
    total_ads = ads_qs.count()
    pending_ads = ads_qs.filter(status='pending').count()
    active_ads = ads_qs.filter(status='approved').count()
    featured_ads = ads_qs.filter(plan='featured').count()
    
    # User stats
    total_users = users_qs.count()
    active_users = users_qs.filter(is_active=True).count()
    
    # Revenue calculation (featured ads * $10)
    monthly_revenue = ads_qs.filter(
        plan='featured',
        created_at__gte=timezone.now().replace(day=1)
    ).count() * 10
    
    # Recent activity
    recent_ads = ads_qs.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    return Response({
        'total_ads': total_ads,
        'pending_ads': pending_ads,
        'active_ads': active_ads,
        'featured_ads': featured_ads,
        'total_users': total_users,
        'active_users': active_users,
        'monthly_revenue': monthly_revenue,
        'recent_ads': recent_ads,
        'state_filter': state_filter,
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_ads_list(request):
    """Get ads list for admin with filtering."""
    
    # Get filters
    state_filter = request.query_params.get('state')
    status_filter = request.query_params.get('status', 'all')
    city_filter = request.query_params.get('city')
    search = request.query_params.get('search', '')
    
    # Base queryset
    queryset = Ad.objects.exclude(status='deleted').select_related(
        'user', 'category', 'city', 'state'
    )
    
    # Apply filters
    if state_filter:
        queryset = queryset.filter(state__code__iexact=state_filter)
    
    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    
    if city_filter:
        queryset = queryset.filter(city__name__icontains=city_filter)
    
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    # Order by newest first
    queryset = queryset.order_by('-created_at')
    
    # Simple pagination
    page_size = 20
    page = int(request.query_params.get('page', 1))
    start = (page - 1) * page_size
    end = start + page_size
    
    ads = queryset[start:end]
    total_count = queryset.count()
    
    # Serialize data
    ads_data = AdminAdSerializer(ads, many=True).data
    
    return Response({
        'ads': ads_data,
        'total_count': total_count,
        'page': page,
        'page_size': page_size,
        'has_next': end < total_count,
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_ad_action(request, ad_id):
    """Perform actions on ads (approve, reject, delete, feature)."""
    
    try:
        ad = Ad.objects.get(id=ad_id)
    except Ad.DoesNotExist:
        return Response({'error': 'Ad not found'}, status=404)
    
    action = request.data.get('action')
    
    if action == 'approve':
        ad.status = 'approved'
        ad.approved_by = request.user
        ad.approved_at = timezone.now()
        message = 'Ad approved successfully'
        
    elif action == 'reject':
        ad.status = 'rejected'
        ad.rejection_reason = request.data.get('reason', 'Rejected by admin')
        message = 'Ad rejected successfully'
        
    elif action == 'delete':
        ad.status = 'deleted'
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

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_users_list(request):
    """Get users list for admin."""
    
    search = request.query_params.get('search', '')
    status_filter = request.query_params.get('status', 'all')
    
    queryset = User.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'suspended':
        queryset = queryset.filter(is_suspended=True)
    
    queryset = queryset.order_by('-created_at')
    
    # Simple pagination
    page_size = 20
    page = int(request.query_params.get('page', 1))
    start = (page - 1) * page_size
    end = start + page_size
    
    users = queryset[start:end]
    total_count = queryset.count()
    
    users_data = AdminUserSerializer(users, many=True).data
    
    return Response({
        'users': users_data,
        'total_count': total_count,
        'page': page,
        'page_size': page_size,
        'has_next': end < total_count,
    })

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
        
        states_data.append({
            'code': state.code,
            'name': state.name,
            'domain': state.domain,
            'total_ads': ads_count,
            'active_ads': active_ads,
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
            'is_active': category.is_active,
        })
    
    return Response({'categories': categories_data})
