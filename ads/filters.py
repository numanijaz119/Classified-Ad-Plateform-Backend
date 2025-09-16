import django_filters
from django.db.models import Q
from .models import Ad

class AdFilter(django_filters.FilterSet):
    """Filter set for Ad model."""
    
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    city = django_filters.CharFilter(field_name='city__name', lookup_expr='icontains')
    state = django_filters.CharFilter(field_name='state__code', lookup_expr='iexact')
    plan = django_filters.ChoiceFilter(choices=Ad.PLAN_CHOICES)
    search = django_filters.CharFilter(method='filter_search')
    posted_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    posted_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Ad
        fields = ['category', 'city', 'state', 'plan']
    
    def filter_search(self, queryset, name, value):
        """Custom search filter across multiple fields."""
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(category__name__icontains=value)
        )