from rest_framework import serializers
from .models import State, City, Category
from administrator.models import Banner

class StateSerializer(serializers.ModelSerializer):
    """Serializer for State model."""
    
    cities_count = serializers.SerializerMethodField()
    
    class Meta:
        model = State
        fields = [
            'id', 'name', 'code', 'domain', 'logo', 'favicon',
            'meta_title', 'meta_description', 'is_active',
            'cities_count', 'created_at'
        ]
        read_only_fields = ['id', 'cities_count', 'created_at']
    
    def get_cities_count(self, obj):
        """Get the count of active cities in this state."""
        return obj.cities.filter(is_active=True).count()

class CitySerializer(serializers.ModelSerializer):
    """Serializer for City model with photo."""
    
    state_name = serializers.CharField(source='state.name', read_only=True)
    state_code = serializers.CharField(source='state.code', read_only=True)
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = City
        fields = [
            'id', 'name', 'state', 'state_name', 'state_code',
            'photo', 'photo_url',
            'latitude', 'longitude', 'is_major', 'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'state_name', 'state_code', 'photo_url', 'created_at']
    
    def get_photo_url(self, obj):
        """Get full URL for city photo."""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

class CitySimpleSerializer(serializers.ModelSerializer):
    """Simple city serializer for dropdowns and lists."""
    
    photo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = City
        fields = ['id', 'name', 'photo_url']
    
    def get_photo_url(self, obj):
        """Get full URL for city photo."""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None

class StateSimpleSerializer(serializers.ModelSerializer):
    """Simple state serializer for dropdowns and lists."""
    
    class Meta:
        model = State
        fields = ['id', 'name', 'code']

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""
    
    ads_count = serializers.SerializerMethodField()
    state_ads_count = serializers.IntegerField(read_only=True, required=False)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'icon', 'description',
            'sort_order', 'is_active', 'ads_count', 'state_ads_count', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'ads_count', 'state_ads_count', 'created_at']
    
    def get_ads_count(self, obj):
        """Get count of active ads in this category."""
        # If state_ads_count is available (from annotation), use it
        if hasattr(obj, 'state_ads_count'):
            return obj.state_ads_count
        # Fallback to global count
        return obj.get_active_ads_count()

class CategorySimpleSerializer(serializers.ModelSerializer):
    """Simple category serializer for dropdowns."""
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon']



class PublicBannerSerializer(serializers.ModelSerializer):
    """Serializer for public-facing banner ads"""
    target_states = serializers.StringRelatedField(many=True, read_only=True)
    target_categories = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Banner
        fields = [
            'id',
            'title',
            'description',
            'banner_type',
            'image',
            'html_content',
            'text_content',
            'position',
            'click_url',
            'open_new_tab',
            'priority',
            'target_states',
            'target_categories',
            'impressions',
            'clicks',
        ]
        read_only_fields = ['id', 'impressions', 'clicks', 'target_states', 'target_categories']
    
    def to_representation(self, instance):
        """Ensure all required fields are present"""
        data = super().to_representation(instance)
        
        # Ensure image field has full URL
        if data.get('image'):
            request = self.context.get('request')
            if request and not data['image'].startswith('http'):
                data['image'] = request.build_absolute_uri(data['image'])
        
        return data


class BannerImpressionSerializer(serializers.Serializer):
    """Serializer for tracking banner impressions"""
    banner_id = serializers.IntegerField()
    page_url = serializers.URLField(required=False, allow_blank=True)


class BannerClickSerializer(serializers.Serializer):
    """Serializer for tracking banner clicks"""
    banner_id = serializers.IntegerField()
    referrer = serializers.URLField(required=False, allow_blank=True)

