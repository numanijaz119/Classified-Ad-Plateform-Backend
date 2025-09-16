from rest_framework import serializers
from django.utils import timezone
from django.utils.timesince import timesince
from .models import Ad, AdImage

class AdImageSerializer(serializers.ModelSerializer):
    """Serializer for AdImage model."""
    
    class Meta:
        model = AdImage
        fields = ['id', 'image', 'caption', 'is_primary', 'sort_order']

class AdListSerializer(serializers.ModelSerializer):
    """Serializer for listing ads (minimal data)."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    state_code = serializers.CharField(source='state.code', read_only=True)
    primary_image = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Ad
        fields = [
            'id', 'title', 'slug', 'price', 'category_name', 
            'city_name', 'state_code', 'plan', 'view_count',
            'primary_image', 'created_at', 'time_ago', 'is_expired'
        ]
    
    def get_primary_image(self, obj):
        """Get the primary image URL."""
        primary_image = obj.primary_image
        if primary_image and primary_image.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.image.url)
        return None
    
    def get_time_ago(self, obj):
        """Get human-readable time since creation."""
        return timesince(obj.created_at)

class AdDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed ad view."""
    
    images = AdImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    state_code = serializers.CharField(source='state.code', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = Ad
        fields = [
            'id', 'title', 'slug', 'description', 'price', 'category_name',
            'city_name', 'state_name', 'state_code', 'plan', 'status',
            'view_count', 'images', 'user_name', 'contact_phone', 
            'contact_email', 'created_at', 'expires_at', 'time_ago', 'is_expired'
        ]
    
    def get_time_ago(self, obj):
        return timesince(obj.created_at)

class AdCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ads."""
    
    images = serializers.ListField(
        child=serializers.ImageField(),
        max_length=10,  # Maximum 10 images
        allow_empty=True,
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Ad
        fields = [
            'title', 'description', 'price', 'category', 'city',
            'contact_phone', 'contact_email', 'plan', 'images'
        ]
    
    def validate_images(self, value):
        """Validate image count based on plan."""
        plan = self.initial_data.get('plan', 'free')
        max_images = 3 if plan == 'free' else 10
        
        if len(value) > max_images:
            raise serializers.ValidationError(
                f"Maximum {max_images} images allowed for {plan} plan."
            )
        
        return value
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        
        # Set user and state
        validated_data['user'] = self.context['request'].user
        validated_data['state'] = validated_data['city'].state
        
        # Create the ad
        ad = Ad.objects.create(**validated_data)
        
        # Create images
        for i, image_data in enumerate(images_data):
            AdImage.objects.create(
                ad=ad,
                image=image_data,
                sort_order=i,
                is_primary=(i == 0)  # First image is primary
            )
        
        return ad

class UserAdSerializer(serializers.ModelSerializer):
    """Serializer for user's own ads with additional admin fields."""
    
    images = AdImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    days_remaining = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Ad
        fields = [
            'id', 'title', 'slug', 'description', 'price', 'category_name',
            'city_name', 'plan', 'status', 'view_count', 'images',
            'created_at', 'expires_at', 'days_remaining', 'time_ago',
            'admin_notes', 'rejection_reason'
        ]
    
    def get_days_remaining(self, obj):
        """Get days remaining until expiration."""
        if obj.expires_at > timezone.now():
            return (obj.expires_at.date() - timezone.now().date()).days
        return 0
    
    def get_time_ago(self, obj):
        return timesince(obj.created_at)