# administrator/filters.py
import django_filters
from ads.models import Ad, AdReport
from accounts.models import User
from django.utils import timezone
from django.db.models import Q
from ads.filters import BaseAdFilter


class AdminAdFilter(BaseAdFilter):
    """
    Advanced filter for admin ad management.
    Inherits common fields from BaseAdFilter in ads app.
    """
    
    # ========== Admin-Only: Category ==========
    category_slug = django_filters.CharFilter(
        field_name='category__slug',
        help_text='Filter by category slug'
    )
    
    # ========== Admin-Only: Status ==========
    status = django_filters.ChoiceFilter(
        field_name='status',
        choices=[
            ('draft', 'Draft'),
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('sold', 'Sold/Closed'),
        ],
        help_text='Filter by ad status'
    )
    
    # ========== Admin-Only: Plan ==========
    plan = django_filters.ChoiceFilter(
        field_name='plan',
        choices=[
            ('free', 'Free Plan'),
            ('featured', 'Featured Plan'),
        ],
        help_text='Filter by ad plan'
    )
    
    # ========== Admin-Only: User Filters ==========
    user = django_filters.NumberFilter(
        field_name='user__id',
        help_text='Filter by user ID'
    )
    user_email = django_filters.CharFilter(
        field_name='user__email',
        lookup_expr='icontains',
        help_text='Filter by user email (partial match)'
    )
    
    # ========== Admin-Only: Boolean Filters ==========
    has_images = django_filters.BooleanFilter(
        method='filter_has_images',
        help_text='Filter ads with/without images'
    )
    has_phone = django_filters.BooleanFilter(
        method='filter_has_phone',
        help_text='Filter ads with/without phone numbers'
    )
    is_featured = django_filters.BooleanFilter(
        method='filter_is_featured',
        help_text='Filter currently featured ads'
    )
    has_reports = django_filters.BooleanFilter(
        method='filter_has_reports',
        help_text='Filter ads with/without reports'
    )
    
    # ========== Admin-Only: Analytics Filters ==========
    min_views = django_filters.NumberFilter(
        field_name='view_count',
        lookup_expr='gte',
        help_text='Filter ads with minimum view count'
    )
    min_contacts = django_filters.NumberFilter(
        field_name='contact_count',
        lookup_expr='gte',
        help_text='Filter ads with minimum contact count'
    )
    
    # ========== Admin-Only: Keyword Filter ==========
    keywords = django_filters.CharFilter(
        field_name='keywords',
        lookup_expr='icontains',
        help_text='Filter by keywords field'
    )
    
    class Meta:
        model = Ad
        fields = [
            # From BaseAdFilter (inherited)
            'category', 'city', 'state',
            'price_min', 'price_max', 'price_type',
            'condition', 'posted_since', 'posted_after', 'posted_before',
            # Admin-specific
            'category_slug', 'status', 'plan',
            'user', 'user_email',
            'has_images', 'has_phone', 'is_featured', 'has_reports',
            'keywords', 'min_views', 'min_contacts'
        ]
    
    # ========== Admin-Only: Filter Methods ==========
    
    def filter_has_images(self, queryset, name, value):
        """Filter ads that have/don't have images."""
        if value is True:
            return queryset.filter(images__isnull=False).distinct()
        elif value is False:
            return queryset.filter(images__isnull=True)
        return queryset
    
    def filter_has_phone(self, queryset, name, value):
        """Filter ads that have/don't have phone numbers."""
        if value is True:
            return queryset.exclude(
                Q(contact_phone='') | Q(contact_phone__isnull=True)
            )
        elif value is False:
            return queryset.filter(
                Q(contact_phone='') | Q(contact_phone__isnull=True)
            )
        return queryset
    
    def filter_is_featured(self, queryset, name, value):
        """Filter currently active featured ads."""
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
        """Filter ads that have/don't have reports."""
        if value is True:
            return queryset.filter(reports__isnull=False).distinct()
        elif value is False:
            return queryset.filter(reports__isnull=True)
        return queryset


class AdminUserFilter(django_filters.FilterSet):
    """Filter class for admin user management."""
    
    status = django_filters.ChoiceFilter(
        choices=[
            ('all', 'All'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('banned', 'Banned'),
        ],
        method='filter_status'
    )
    
    email_verified = django_filters.BooleanFilter(field_name='email_verified')
    is_staff = django_filters.BooleanFilter(field_name='is_staff')
    
    joined_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    joined_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    has_ads = django_filters.BooleanFilter(method='filter_has_ads')
    
    class Meta:
        model = User
        fields = ['status', 'email_verified', 'is_staff']
    
    def filter_status(self, queryset, name, value):
        """Custom status filter."""
        if value == 'all':
            return queryset
        elif value == 'active':
            return queryset.filter(is_active=True, is_suspended=False)
        elif value == 'suspended':
            return queryset.filter(is_suspended=True)
        elif value == 'banned':
            return queryset.filter(is_active=False)
        return queryset
    
    def filter_has_ads(self, queryset, name, value):
        """Filter users who have ads."""
        if value:
            return queryset.filter(ads__isnull=False).distinct()
        return queryset.filter(ads__isnull=True)


class AdminReportFilter(django_filters.FilterSet):
    """Filter class for admin report management."""
    
    status = django_filters.ChoiceFilter(
        choices=[
            ('all', 'All'),
            ('pending', 'Pending'),
            ('reviewed', 'Reviewed'),
        ],
        method='filter_status'
    )
    
    reason = django_filters.ChoiceFilter(
        field_name='reason',
        choices=AdReport.REASON_CHOICES
    )
    
    ad_id = django_filters.NumberFilter(field_name='ad__id')
    reported_by = django_filters.NumberFilter(field_name='reported_by__id')
    
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = AdReport
        fields = ['status', 'reason', 'ad_id', 'reported_by']
    
    def filter_status(self, queryset, name, value):
        """Custom status filter."""
        if value == 'all':
            return queryset
        elif value == 'pending':
            return queryset.filter(is_reviewed=False)
        elif value == 'reviewed':
            return queryset.filter(is_reviewed=True)
        return queryset