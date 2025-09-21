# ads/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum
from .models import Ad, AdImage, AdView, AdContact, AdFavorite, AdReport

class AdImageInline(admin.TabularInline):
    """Inline admin for ad images."""
    model = AdImage
    extra = 0
    readonly_fields = ['file_size', 'width', 'height', 'created_at']
    fields = ['image', 'caption', 'is_primary', 'sort_order', 'file_size', 'created_at']

@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    """Enhanced admin interface for ads."""
    
    list_display = [
        'title', 'user_link', 'category', 'city', 'state', 'status_badge',
        'plan_badge', 'price_display', 'view_count', 'contact_count',
        'created_at', 'expires_at'
    ]
    
    list_filter = [
        'status', 'plan', 'category', 'state', 'condition', 'price_type',
        'created_at', 'approved_at'
    ]
    
    search_fields = [
        'title', 'description', 'user__email', 'user__first_name',
        'user__last_name', 'contact_phone'
    ]
    
    readonly_fields = [
        'slug', 'view_count', 'unique_view_count', 'contact_count',
        'favorite_count', 'created_at', 'updated_at', 'approved_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'slug', 'description', 'category', 'city', 'state'
            )
        }),
        ('Pricing & Details', {
            'fields': (
                'price', 'price_type', 'condition', 'keywords'
            )
        }),
        ('Contact Information', {
            'fields': (
                'contact_phone', 'contact_email', 'hide_phone'
            )
        }),
        ('Status & Plan', {
            'fields': (
                'status', 'plan', 'featured_payment_id', 'featured_expires_at'
            )
        }),
        ('Analytics', {
            'fields': (
                'view_count', 'unique_view_count', 'contact_count', 'favorite_count'
            ),
            'classes': ('collapse',)
        }),
        ('Admin', {
            'fields': (
                'user', 'approved_by', 'approved_at', 'admin_notes',
                'rejection_reason'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'expires_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [AdImageInline]
    
    actions = ['approve_ads', 'reject_ads', 'make_featured', 'extend_expiry']
    
    def user_link(self, obj):
        """Create link to user admin."""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'draft': 'gray',
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'expired': 'darkred',
            'sold': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def plan_badge(self, obj):
        """Display plan with styling."""
        if obj.plan == 'featured':
            return format_html(
                '<span style="background: gold; color: black; padding: 2px 6px; '
                'border-radius: 3px; font-size: 11px;">FEATURED</span>'
            )
        return 'Free'
    plan_badge.short_description = 'Plan'
    
    def price_display(self, obj):
        """Display formatted price."""
        return obj.display_price
    price_display.short_description = 'Price'
    
    def approve_ads(self, request, queryset):
        """Bulk approve ads."""
        updated = queryset.update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now(),
            rejection_reason=''
        )
        self.message_user(request, f'{updated} ads approved successfully.')
    approve_ads.short_description = 'Approve selected ads'
    
    def reject_ads(self, request, queryset):
        """Bulk reject ads."""
        updated = queryset.update(
            status='rejected',
            rejection_reason='Bulk rejection by admin'
        )
        self.message_user(request, f'{updated} ads rejected.')
    reject_ads.short_description = 'Reject selected ads'
    
    def make_featured(self, request, queryset):
        """Make ads featured."""
        updated = queryset.update(
            plan='featured',
            featured_expires_at=timezone.now() + timezone.timedelta(days=30)
        )
        self.message_user(request, f'{updated} ads made featured.')
    make_featured.short_description = 'Make selected ads featured'
    
    def extend_expiry(self, request, queryset):
        """Extend ad expiry by 30 days."""
        for ad in queryset:
            ad.expires_at += timezone.timedelta(days=30)
            ad.save()
        self.message_user(request, f'{queryset.count()} ads extended by 30 days.')
    extend_expiry.short_description = 'Extend expiry by 30 days'

@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    """Admin interface for ad images."""
    
    list_display = ['ad', 'image_preview', 'caption', 'is_primary', 'sort_order', 'created_at']
    list_filter = ['is_primary', 'created_at', 'ad__category']
    search_fields = ['ad__title', 'caption']
    readonly_fields = ['file_size', 'width', 'height', 'created_at']
    
    def image_preview(self, obj):
        """Show image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />',
                obj.image.url
            )
        return 'No image'
    image_preview.short_description = 'Preview'

@admin.register(AdView)
class AdViewAdmin(admin.ModelAdmin):
    """Admin interface for ad views."""
    
    list_display = ['ad', 'user', 'ip_address', 'device_type', 'viewed_at']
    list_filter = ['device_type', 'viewed_at', 'ad__category']
    search_fields = ['ad__title', 'user__email', 'ip_address']
    readonly_fields = ['viewed_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(AdContact)
class AdContactAdmin(admin.ModelAdmin):
    """Admin interface for ad contact views."""
    
    list_display = ['ad', 'user', 'contact_type', 'ip_address', 'viewed_at']
    list_filter = ['contact_type', 'viewed_at', 'ad__category']
    search_fields = ['ad__title', 'user__email']
    readonly_fields = ['viewed_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(AdFavorite)
class AdFavoriteAdmin(admin.ModelAdmin):
    """Admin interface for ad favorites."""
    
    list_display = ['ad', 'user', 'created_at']
    list_filter = ['created_at', 'ad__category']
    search_fields = ['ad__title', 'user__email']
    readonly_fields = ['created_at']

@admin.register(AdReport)
class AdReportAdmin(admin.ModelAdmin):
    """Admin interface for ad reports."""
    
    list_display = [
        'ad_link', 'reported_by', 'reason', 'is_reviewed',
        'reviewed_by', 'created_at'
    ]
    list_filter = ['reason', 'is_reviewed', 'created_at']
    search_fields = ['ad__title', 'reported_by__email', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Report Details', {
            'fields': ('ad', 'reported_by', 'reason', 'description', 'created_at')
        }),
        ('Admin Review', {
            'fields': ('is_reviewed', 'reviewed_by', 'reviewed_at', 'admin_notes')
        }),
    )
    
    actions = ['mark_reviewed', 'mark_unreviewed']
    
    def ad_link(self, obj):
        """Create link to ad admin."""
        url = reverse('admin:ads_ad_change', args=[obj.ad.id])
        return format_html('<a href="{}">{}</a>', url, obj.ad.title)
    ad_link.short_description = 'Ad'
    
    def mark_reviewed(self, request, queryset):
        """Mark reports as reviewed."""
        updated = queryset.update(
            is_reviewed=True,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports marked as reviewed.')
    mark_reviewed.short_description = 'Mark as reviewed'
    
    def mark_unreviewed(self, request, queryset):
        """Mark reports as unreviewed."""
        updated = queryset.update(is_reviewed=False, reviewed_by=None, reviewed_at=None)
        self.message_user(request, f'{updated} reports marked as unreviewed.')
    mark_unreviewed.short_description = 'Mark as unreviewed'

# Custom admin site configuration
admin.site.site_header = 'Classified Ads Administration'
admin.site.site_title = 'Ads Admin'
admin.site.index_title = 'Manage Classified Ads'