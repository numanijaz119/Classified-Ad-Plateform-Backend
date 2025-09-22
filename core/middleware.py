import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class StateMiddleware:
    """
    Middleware to detect the current state based on the domain.
    Uses caching to avoid repeated domain-to-state lookups.
    Sets request.state_code for use in views and templates.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get the domain from the request
        domain = request.get_host().lower()
        
        # Try to get state code from cache first
        cache_key = f'domain_state_{domain}'
        state_code = cache.get(cache_key)
        
        if state_code is None:
            # Cache miss - look up state code from domain mapping
            state_code = getattr(settings, 'STATE_DOMAIN_MAPPING', {}).get(domain, 'IL')
            
            # Cache for 1 hour (domains don't change often)
            cache.set(cache_key, state_code, 3600)
            logger.debug(f"Domain: {domain} -> State: {state_code} (cached)")
        else:
            logger.debug(f"Domain: {domain} -> State: {state_code} (from cache)")
        
        # Set the state code on the request for use in views
        request.state_code = state_code
        
        response = self.get_response(request)
        return response