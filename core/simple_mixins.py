# core/simple_mixins.py
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class SimpleStateFilterMixin:
    """
    Simple mixin that automatically filters querysets by current state.
    Only goal: detect domain → filter by state automatically.
    """
    
    # Override in subclasses if needed (default works for most models)
    state_field_path = 'state__code'
    
    def get_current_state_code(self):
        """Get current state code from request."""
        return getattr(self.request, 'state_code', 'IL')
    
    def filter_by_current_state(self, queryset):
        """Filter queryset by current state."""
        state_code = self.get_current_state_code()
        filter_kwargs = {f'{self.state_field_path}__iexact': state_code}
        return queryset.filter(**filter_kwargs)
    
    def get_queryset(self):
        """Override to apply state filtering automatically."""
        queryset = super().get_queryset()
        
        # Admin users can see all data - no filtering
        if hasattr(self.request, 'user') and self.request.user.is_staff:
            return queryset
            
        # Regular users see only current state data
        return self.filter_by_current_state(queryset)


class SimpleStateContextMixin:
    """
    Simple mixin that adds basic state info to API responses.
    Only includes essential state context for frontend.
    Uses caching for better performance.
    """
    
    def get_state_context(self):
        """Get basic state context for frontend with caching."""
        state_code = getattr(self.request, 'state_code', 'IL')
        
        # Try cache first - cache for 2 hours since state info rarely changes
        cache_key = f'state_context_{state_code}'
        context = cache.get(cache_key)
        
        if not context:
            try:
                from content.models import State
                state = State.objects.get(code__iexact=state_code, is_active=True)
                context = {
                    'code': state.code,
                    'name': state.name,
                    'domain': state.domain,
                    'meta_title': state.meta_title,
                    'meta_description': state.meta_description,
                }
                # Cache for 2 hours (state info doesn't change often)
                cache.set(cache_key, context, 7200)
                logger.debug(f"State context for {state_code} cached")
            except:
                # Fallback context
                context = {
                    'code': state_code,
                    'name': state_code,
                    'domain': 'localhost',
                    'meta_title': f'Classified Ads {state_code}',
                    'meta_description': f'Buy and sell in {state_code}',
                }
                # Cache fallback for shorter time
                cache.set(cache_key, context, 1800)  # 30 minutes
                logger.warning(f"Using fallback context for {state_code}")
        
        return context
    
    def finalize_response(self, request, response, *args, **kwargs):
        """Add state context to successful responses."""
        response = super().finalize_response(request, response, *args, **kwargs)
        
        # Only add to successful responses
        if response.status_code < 400 and hasattr(response, 'data'):
            if isinstance(response.data, dict):
                response.data['state_context'] = self.get_state_context()
        
        return response


class AdminStateFilterMixin:
    """
    Mixin for admin views that allows filtering by specific state.
    Admin can see all data but can filter by state when needed.
    """
    
    state_field_path = 'state__code'
    
    def get_admin_state_filter(self):
        """Get state filter from query params for admin."""
        return self.request.query_params.get('state')
    
    def filter_by_admin_state(self, queryset):
        """Apply state filter if admin specified one."""
        state_filter = self.get_admin_state_filter()
        if state_filter:
            filter_kwargs = {f'{self.state_field_path}__iexact': state_filter}
            return queryset.filter(**filter_kwargs)
        return queryset
    
    def get_queryset(self):
        """Apply admin state filtering if specified."""
        queryset = super().get_queryset()
        return self.filter_by_admin_state(queryset)


# Combined mixins for common use cases
class StateAwareViewMixin(SimpleStateFilterMixin, SimpleStateContextMixin):
    """
    Simple combination: automatic state filtering + context.
    Use this for most public API views.
    """
    pass


class AdminViewMixin(AdminStateFilterMixin):
    """
    Simple admin mixin: allows optional state filtering.
    Use this for admin API views.
    """
    pass
