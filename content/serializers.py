from rest_framework import serializers
from .models import State, City, Category

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
    """Serializer for City model."""
    
    state_name = serializers.CharField(source='state.name', read_only=True)
    state_code = serializers.CharField(source='state.code', read_only=True)
    
    class Meta:
        model = City
        fields = [
            'id', 'name', 'state', 'state_name', 'state_code',
            'latitude', 'longitude', 'is_major', 'is_active',
            'created_at'
        ]
        read_only_fields = ['id', 'state_name', 'state_code', 'created_at']

class CitySimpleSerializer(serializers.ModelSerializer):
    """Simple city serializer for dropdowns and lists."""
    
    class Meta:
        model = City
        fields = ['id', 'name']

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

class CityAutocompleteSerializer(serializers.ModelSerializer):
    """Serializer for city autocomplete with state info."""
    
    state_name = serializers.CharField(source='state.name', read_only=True)
    state_code = serializers.CharField(source='state.code', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = City
        fields = ['id', 'name', 'state_name', 'state_code', 'is_major', 'display_name']
    
    def get_display_name(self, obj):
        """Return formatted display name with state."""
        return f"{obj.name}, {obj.state.code}"
