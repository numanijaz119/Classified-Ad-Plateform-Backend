from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class StateMiddleware(MiddlewareMixin):
    """
    Middleware to determine the current state based on the domain.
    Sets request.state_code for use throughout the application.
    """
    
    def process_request(self, request):
        host = request.get_host().split(':')[0]  # Remove port if present
        
        # Get state code from domain mapping
        state_code = settings.STATE_DOMAIN_MAPPING.get(host, 'IL')
        
        # Set state info on request
        request.state_code = state_code
        
        logger.debug(f"StateMiddleware: Host {host} -> State {state_code}")
        
        return None