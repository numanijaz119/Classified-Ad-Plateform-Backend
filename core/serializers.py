# core/serializers.py
from rest_framework import serializers
from django.conf import settings

class StateContextSerializer(serializers.Serializer):
    """Serializer for state context information."""
    
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True)
    domain = serializers.CharField(read_only=True)
    meta_title = serializers.CharField(read_only=True)
    meta_description = serializers.CharField(read_only=True)


class StateAwareResponseSerializer(serializers.Serializer):
    """Base serializer for state-aware API responses."""
    
    state_context = StateContextSerializer(read_only=True)
    
    class Meta:
        abstract = True


class StateAwareListResponseSerializer(StateAwareResponseSerializer):
    """Serializer for paginated list responses with state context."""
    
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = serializers.ListField(read_only=True)


class CrossStateSearchResultSerializer(serializers.Serializer):
    """Serializer for cross-state search results with state breakdown."""
    
    state_code = serializers.CharField(read_only=True)
    state_name = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class StateAnalyticsSerializer(serializers.Serializer):
    """Base serializer for state-specific analytics data."""
    
    state_code = serializers.CharField(read_only=True)
    state_name = serializers.CharField(read_only=True)
    total_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        abstract = True
