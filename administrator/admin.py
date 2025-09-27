# administrator/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Banner, AdminSettings, BannerClick, BannerImpression

# ============================================================================
# BANNER ADMIN
# ============================================================================

class BannerClickInline(admin.TabularInline):
    """Inline for banner clicks."""
    model = BannerClick
    extra = 0
    readonly_fields = ['ip_address', 'user_agent', 'referrer', 'clicked_at', 'city', 'state', 'country']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class BannerImpressionInline(admin.TabularInline):
    """Inline for banner impressions."""
    model = BannerImpression
    extra = 0
    readonly_fields = ['ip_address', 'user_agent', 'page_url', 'viewed_at', 'city', 'state', 'country']
    can_delete = False
    max_num = 10  # Limit display for performance
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    """Admin interface for Banner model."""
    
    list_display = [
        'title', 'banner_type', 'position', 'is_active', 
        'is_currently_active', 'impressions', 'clicks', 'ctr_display',
        'start_date', 'end_date', 'created_by'
    ]
    list_filter = [
        'banner_type', 'position', 'is_active', 'start_date', 'end_date',
        'target_states', 'target_categories'
    ]
    search_fields = ['title', 'description', 'click_url']
    readonly_fields = [
        'impressions', 'clicks', 'ctr_display', 'created_at', 'updated_at',
        'is_currently_active', 'preview_image'
    ]
    filter_horizontal = ['target_states', 'target_categories']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'banner_type', 'position', 'priority')
        }),
        ('Content', {
            'fields': ('image', 'preview_image', 'html_content', 'text_content'),
            'classes': ('collapse',)
        }),
        ('Targeting', {
            'fields': ('target_states', 'target_categories'),
            'classes': ('collapse',)
        }),
        ('Link & Behavior', {
            'fields': ('click_url', 'open_new_tab'),
            'classes': ('collapse',)
        }),
        ('Scheduling', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Analytics', {
            'fields': ('impressions', 'clicks', 'ctr_display', 'is_currently_active'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [BannerClickInline, BannerImpressionInline]
    
    def save_model(self, request, obj, form, change):
        """Set created_by when creating new banner."""
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def ctr_display(self, obj):
        """Display CTR with formatting."""
        if obj.impressions > 0:
            ctr = (obj.clicks / obj.impressions) * 100
            return f"{ctr:.2f}%"
        return "0%"
    ctr_display.short_description = 'CTR'
    
    def preview_image(self, obj):
        """Display image preview."""
        if obj.image:
            return format_html(
                '<img src="{}" width="200" height="100" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No image"
    preview_image.short_description = 'Image Preview'
    
    def is_currently_active(self, obj):
        """Display current active status with color coding."""
        is_active = obj.is_currently_active()
        if is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Inactive</span>'
            )
    is_currently_active.short_description = 'Currently Active'

# ============================================================================
# ADMIN SETTINGS ADMIN
# ============================================================================

@admin.register(AdminSettings)
class AdminSettingsAdmin(admin.ModelAdmin):
    """Admin interface for AdminSettings model."""
    
    list_display = ['site_name', 'contact_email', 'updated_at', 'updated_by']
    readonly_fields = ['updated_at', 'updated_by']
    
    fieldsets = (
        ('Site Information', {
            'fields': ('site_name', 'contact_email', 'support_phone')
        }),
        ('Ad Settings', {
            'fields': (
                'ad_approval_required', 'featured_ad_price', 
                'max_images_per_ad', 'ad_expiration_days'
            )
        }),
        ('User Settings', {
            'fields': (
                'user_registration_enabled', 'email_verification_required', 
                'max_ads_per_user'
            )
        }),
        ('Notification Settings', {
            'fields': ('admin_email_notifications', 'user_email_notifications')
        }),
        ('System', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        """Only allow one settings instance."""
        return not AdminSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of settings."""
        return False
    
    def save_model(self, request, obj, form, change):
        """Set updated_by when saving."""
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

# ============================================================================
# BANNER ANALYTICS ADMIN
# ============================================================================

@admin.register(BannerClick)
class BannerClickAdmin(admin.ModelAdmin):
    """Admin interface for BannerClick model."""
    
    list_display = ['banner', 'ip_address', 'city', 'state', 'country', 'clicked_at']
    list_filter = ['clicked_at', 'banner', 'state', 'country']
    search_fields = ['banner__title', 'ip_address', 'city']
    readonly_fields = ['banner', 'ip_address', 'user_agent', 'referrer', 'clicked_at', 'city', 'state', 'country']
    date_hierarchy = 'clicked_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(BannerImpression)
class BannerImpressionAdmin(admin.ModelAdmin):
    """Admin interface for BannerImpression model."""
    
    list_display = ['banner', 'ip_address', 'city', 'state', 'country', 'viewed_at']
    list_filter = ['viewed_at', 'banner', 'state', 'country']
    search_fields = ['banner__title', 'ip_address', 'city']
    readonly_fields = ['banner', 'ip_address', 'user_agent', 'page_url', 'viewed_at', 'city', 'state', 'country']
    date_hierarchy = 'viewed_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

# ============================================================================
# CUSTOM ADMIN ACTIONS
# ============================================================================

def make_banners_active(modeladmin, request, queryset):
    """Activate selected banners."""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} banners were successfully activated.')

def make_banners_inactive(modeladmin, request, queryset):
    """Deactivate selected banners."""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} banners were successfully deactivated.')

make_banners_active.short_description = "Activate selected banners"
make_banners_inactive.short_description = "Deactivate selected banners"

# Add actions to BannerAdmin
BannerAdmin.actions = [make_banners_active, make_banners_inactive]

# ============================================================================
# CUSTOM ADMIN SITE CONFIGURATION
# ============================================================================

class CustomAdminSite(admin.AdminSite):
    """Custom admin site with enhanced features."""
    
    site_header = 'Classified Ads Administration'
    site_title = 'Admin Portal'
    index_title = 'Dashboard'
    
    def index(self, request, extra_context=None):
        """Custom admin index with dashboard stats."""
        extra_context = extra_context or {}
        
        # Get quick stats
        from ads.models import Ad, AdReport
        from accounts.models import User
        
        extra_context.update({
            'total_ads': Ad.objects.exclude(status='deleted').count(),
            'pending_ads': Ad.objects.filter(status='pending').count(),
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True, is_suspended=False).count(),
            'pending_reports': AdReport.objects.filter(is_reviewed=False).count(),
        })
        
        return super().index(request, extra_context)

# Use custom admin site if needed
# admin_site = CustomAdminSite(name='custom_admin')