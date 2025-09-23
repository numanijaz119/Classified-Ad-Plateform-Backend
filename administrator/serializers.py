# admin/serializers.py
from rest_framework import serializers
from ads.models import Ad
from accounts.models import User
from content.models import Category, State, City

class AdminAdSerializer(serializers.ModelSerializer):
    """Serializer for admin ad management."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    state_code = serializers.CharField(source='state.code', read_only=True)
    
    class Meta:
        model = Ad
        fields = [
            'id', 'title', 'description', 'price', 'status', 'plan',
            'view_count', 'contact_count', 'favorite_count',
            'created_at', 'updated_at', 'expires_at',
            'user_name', 'user_email', 'category_name', 
            'city_name', 'state_name', 'state_code',
            'rejection_reason', 'admin_notes'
        ]

class AdminAdActionSerializer(serializers.Serializer):
    """Serializer for admin ad actions."""
    
    ACTION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('delete', 'Delete'),
        ('feature', 'Make Featured'),
        ('unfeature', 'Remove Featured'),
    ]
    
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True)

class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management."""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    total_ads = serializers.SerializerMethodField()
    active_ads = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'is_active', 
            'is_suspended', 'suspension_reason', 'created_at', 
            'last_login', 'total_ads', 'active_ads'
        ]
    
    def get_total_ads(self, obj):
        return obj.ads.exclude(status='deleted').count()
    
    def get_active_ads(self, obj):
        return obj.ads.filter(status='approved').count()

class AdminStateSerializer(serializers.ModelSerializer):
    """Serializer for admin state management."""
    
    total_ads = serializers.SerializerMethodField()
    active_ads = serializers.SerializerMethodField()
    
    class Meta:
        model = State
        fields = ['code', 'name', 'domain', 'is_active', 'total_ads', 'active_ads']
    
    def get_total_ads(self, obj):
        return obj.ads.exclude(status='deleted').count()
    
    def get_active_ads(self, obj):
        return obj.ads.filter(status='approved').count()

class AdminCategorySerializer(serializers.ModelSerializer):
    """Serializer for admin category management."""
    
    total_ads = serializers.SerializerMethodField()
    active_ads = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'is_active', 'total_ads', 'active_ads']
    
    def get_total_ads(self, obj):
        return obj.ads.exclude(status='deleted').count()
    
    def get_active_ads(self, obj):
        return obj.ads.filter(status='approved').count()
