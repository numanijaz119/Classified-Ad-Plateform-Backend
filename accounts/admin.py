from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    
    list_display = (
        'email', 'first_name', 'last_name', 'is_active', 
        'email_verified', 'is_staff', 'created_at'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'email_verified',
        'is_suspended', 'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'phone', 'avatar')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
        }),
        (_('Account Status'), {
            'fields': ('email_verified', 'is_suspended', 'suspension_reason')
        }),
        (_('OAuth'), {
            'fields': ('google_id',),
            'classes': ('collapse',)
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = (
        'created_at', 'updated_at', 'email_verification_token',
        'last_login_ip'
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 
                'password1', 'password2'
            ),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make email readonly for existing users."""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing user
            readonly.append('email')
        return readonly