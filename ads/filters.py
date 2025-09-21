# ads/filters.py
import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import Ad

class PublicAdFilter(django_filters.FilterSet):
    """Simple filter set for public/user ad listings."""
    
    # Basic filters for users
    category = django_filters.NumberFilter(field_name='category__id')
    city = django_filters.NumberFilter(field_name='city__id')
    
    # Price filters
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    class Meta:
        model = Ad
        fields = ['category', 'city', 'price_min', 'price_max']

class AdminAdFilter(django_filters.FilterSet):
    """Advanced filter set for admin ad management."""
    
    # Basic filters
    category = django_filters.NumberFilter(field_name='category__id')
    category_slug = django_filters.CharFilter(field_name='category__slug')
    city = django_filters.NumberFilter(field_name='city__id')
    state = django_filters.CharFilter(field_name='state__code', lookup_expr='iexact')
    
    # Price filters
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    price_type = django_filters.ChoiceFilter(
        field_name='price_type',
        choices=[
            ('fixed', 'Fixed Price'),
            ('negotiable', 'Negotiable'),
            ('contact', 'Contact for Price'),
            ('free', 'Free'),
            ('swap', 'Swap/Trade'),
        ]
    )
    
    # Condition filter
    condition = django_filters.MultipleChoiceFilter(
        field_name='condition',
        choices=[
            ('new', 'New'),
            ('like_new', 'Like New'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('not_applicable', 'Not Applicable'),
        ]
    )
    
    # Date filters
    posted_since = django_filters.NumberFilter(method='filter_posted_since')
    posted_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    posted_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    # Status filters (admin only)
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=[
            ('draft', 'Draft'),
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('sold', 'Sold/Closed'),
        ]
    )
    
    # Plan filter
    plan = django_filters.ChoiceFilter(
        field_name='plan',
        choices=[
            ('free', 'Free Plan'),
            ('featured', 'Featured Plan'),
        ]
    )
    
    # User filter (admin only)
    user = django_filters.NumberFilter(field_name='user__id')
    user_email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    
    # Advanced filters for admin
    has_images = django_filters.BooleanFilter(method='filter_has_images')
    has_phone = django_filters.BooleanFilter(method='filter_has_phone')
    is_featured = django_filters.BooleanFilter(method='filter_is_featured')
    has_reports = django_filters.BooleanFilter(method='filter_has_reports')
    
    # Search filter
    search = django_filters.CharFilter(method='filter_search')
    keywords = django_filters.CharFilter(field_name='keywords', lookup_expr='icontains')
    
    # Analytics filters for admin
    min_views = django_filters.NumberFilter(field_name='view_count', lookup_expr='gte')
    min_contacts = django_filters.NumberFilter(field_name='contact_count', lookup_expr='gte')
    
    class Meta:
        model = Ad
        fields = [
            'category', 'category_slug', 'city', 'state', 'price_min', 'price_max',
            'price_type', 'condition', 'posted_since', 'status', 'plan', 'user',
            'user_email', 'has_images', 'has_phone', 'is_featured', 'has_reports',
            'search', 'keywords', 'min_views', 'min_contacts'
        ]
    
    def filter_posted_since(self, queryset, name, value):
        """Filter ads posted within specified days."""
        if value:
            since = timezone.now() - timedelta(days=value)
            return queryset.filter(created_at__gte=since)
        return queryset
    
    def filter_has_images(self, queryset, name, value):
        """Filter ads that have images."""
        if value is True:
            return queryset.filter(images__isnull=False).distinct()
        elif value is False:
            return queryset.filter(images__isnull=True)
        return queryset
    
    def filter_has_phone(self, queryset, name, value):
        """Filter ads that have phone numbers."""
        if value is True:
            return queryset.exclude(Q(contact_phone='') | Q(contact_phone__isnull=True))
        elif value is False:
            return queryset.filter(Q(contact_phone='') | Q(contact_phone__isnull=True))
        return queryset
    
    def filter_is_featured(self, queryset, name, value):
        """Filter featured ads that are currently active."""
        if value is True:
            return queryset.filter(
                plan='featured',
                featured_expires_at__gt=timezone.now()
            )
        elif value is False:
            return queryset.exclude(
                plan='featured',
                featured_expires_at__gt=timezone.now()
            )
        return queryset
    
    def filter_has_reports(self, queryset, name, value):
        """Filter ads that have reports."""
        if value is True:
            return queryset.filter(reports__isnull=False).distinct()
        elif value is False:
            return queryset.filter(reports__isnull=True)
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Advanced search across multiple fields."""
        if value:
            return queryset.filter(
                Q(title__icontains=value) |
                Q(description__icontains=value) |
                Q(keywords__icontains=value) |
                Q(category__name__icontains=value) |
                Q(user__email__icontains=value) |
                Q(user__first_name__icontains=value) |
                Q(user__last_name__icontains=value)
            ).distinct()
        return queryset

class UserAdFilter(django_filters.FilterSet):
    """Filter set for user's own ads."""
    
    # Basic filters
    category = django_filters.NumberFilter(field_name='category__id')
    city = django_filters.NumberFilter(field_name='city__id')
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=[
            ('draft', 'Draft'),
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('sold', 'Sold/Closed'),
        ]
    )
    plan = django_filters.ChoiceFilter(
        field_name='plan',
        choices=[
            ('free', 'Free Plan'),
            ('featured', 'Featured Plan'),
        ]
    )
    
    class Meta:
        model = Ad
        fields = ['category', 'city', 'status', 'plan']