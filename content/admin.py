from django.contrib import admin
from .models import State, City, Category
from django.utils.html import format_html

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    """Admin interface for State model."""
    
    list_display = ['name', 'code', 'domain', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'domain']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'domain')
        }),
        ('Branding', {
            'fields': ('logo', 'favicon')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """Admin interface for City model."""
    
    list_display = ['name', 'state', 'photo_preview', 'is_major', 'is_active', 'created_at']  # ADDED photo_preview
    list_filter = ['state', 'is_major', 'is_active', 'created_at']
    search_fields = ['name', 'state__name']
    readonly_fields = ['created_at', 'updated_at', 'photo_preview']  # ADDED photo_preview
    ordering = ['state__name', '-is_major', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'state')
        }),
        ('Photo', {  # ADDED
            'fields': ('photo', 'photo_preview')
        }),
        ('Geographic Data', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_major', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('state')
    
    def photo_preview(self, obj):
        """Display photo preview in admin."""
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px;" />',
                obj.photo.url
            )
        return '-'
    photo_preview.short_description = 'Photo Preview'
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model."""
    
    list_display = ['name', 'icon', 'sort_order', 'is_active', 'get_ads_count_display', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['sort_order', 'name']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'icon', 'description')
        }),
        ('Settings', {
            'fields': ('sort_order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_ads_count_display(self, obj):
        """Display ads count in admin list."""
        return obj.get_active_ads_count()
    get_ads_count_display.short_description = 'Active Ads'
    get_ads_count_display.admin_order_field = 'ads_count'