from django.contrib import admin
from django.utils.html import format_html
from .models import Ad, AdImage, AdView

class AdImageInline(admin.TabularInline):
    """Inline admin for ad images."""
    model = AdImage
    extra = 1
    fields = ['image', 'caption', 'is_primary', 'sort_order']
    readonly_fields = ['created_at']

@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    """Admin interface for Ad model."""
    
    list_display = [
        'title', 'user', 'category', 'city', 'state', 'plan', 
        'status', 'view_count', 'created_at'
    ]
    list_filter = [
        'status', 'plan', 'category', 'state', 'created_at', 'expires_at'
    ]
    search_fields = ['title', 'description', 'user__email']
    readonly_fields = ['slug', 'view_count', 'created_at', 'updated_at', 'approved_at']
    ordering = ['-created_at']
    inlines = [AdImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'price')
        }),
        ('Classification', {
            'fields': ('category', 'city', 'state')
        }),
        ('Contact', {
            'fields': ('contact_phone', 'contact_email')
        }),
        ('Plan & Status', {
            'fields': ('plan', 'status', 'user')
        }),
        ('Analytics', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('Admin', {
            'fields': ('admin_notes', 'rejection_reason', 'approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'user', 'category', 'city', 'state', 'approved_by'
        )

@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    """Admin interface for AdImage model."""
    
    list_display = ['ad', 'image_preview', 'caption', 'is_primary', 'sort_order', 'created_at']
    list_filter = ['is_primary', 'created_at']
    search_fields = ['ad__title', 'caption']
    ordering = ['-created_at']
    
    def image_preview(self, obj):
        """Show image preview in admin."""
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"
    image_preview.short_description = 'Preview'

@admin.register(AdView)
class AdViewAdmin(admin.ModelAdmin):
    """Admin interface for AdView model."""
    
    list_display = ['ad', 'user', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['ad__title', 'user__email', 'ip_address']
    readonly_fields = ['ad', 'user', 'ip_address', 'user_agent', 'viewed_at']
    ordering = ['-viewed_at']
    
    def has_add_permission(self, request):
        """Disable manual creation of view records."""
        return False