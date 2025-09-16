import os
import uuid
from django.utils.text import slugify
from django.utils import timezone

def generate_unique_filename(instance, filename):
    """
    Generate a unique filename for uploaded files.
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Determine upload path based on model
    if hasattr(instance, 'ad'):
        return os.path.join('ads', str(instance.ad.id), filename)
    else:
        return os.path.join('uploads', filename)

def generate_unique_slug(title, model_class, exclude_id=None):
    """
    Generate a unique slug for a model instance.
    """
    base_slug = slugify(title)
    if not base_slug:
        base_slug = 'untitled'
    
    slug = base_slug
    counter = 1
    
    while True:
        queryset = model_class.objects.filter(slug=slug)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if not queryset.exists():
            break
            
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug

def get_client_ip(request):
    """
    Get the client IP address from request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def time_ago(date_time):
    """
    Convert datetime to human readable format.
    """
    now = timezone.now()
    diff = now - date_time
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "Just now"