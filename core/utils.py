import os
import uuid
from django.utils.text import slugify
from django.utils import timezone
import re

def generate_unique_filename(instance, filename):
    """Generate unique filename for uploads."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Organize by model and date
    if hasattr(instance, '__class__'):
        model_name = instance.__class__.__name__.lower()
        date_path = timezone.now().strftime('%Y/%m/%d')
        return f"{model_name}s/{date_path}/{filename}"
    
    return f"uploads/{filename}"

def generate_unique_slug(instance, title, max_length=50):
    """Generate unique slug for models."""
    base_slug = slugify(title)[:max_length]
    slug = base_slug
    
    # Get the model class
    model_class = instance.__class__
    counter = 1
    
    while model_class.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
        
        # Prevent infinite loop
        if counter > 9999:
            slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
            break
    
    return slug

def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def detect_device_type(user_agent):
    """Detect device type from user agent."""
    if not user_agent:
        return 'unknown'
    
    user_agent = user_agent.lower()
    
    # Mobile patterns
    mobile_patterns = [
        'mobile', 'android', 'iphone', 'ipod', 'blackberry',
        'windows phone', 'opera mini', 'iemobile'
    ]
    
    # Tablet patterns
    tablet_patterns = ['ipad', 'tablet', 'kindle', 'silk']
    
    # Check for tablet first (as tablets often contain mobile keywords)
    if any(pattern in user_agent for pattern in tablet_patterns):
        return 'tablet'
    
    # Check for mobile
    if any(pattern in user_agent for pattern in mobile_patterns):
        return 'mobile'
    
    return 'desktop'

def clean_phone_number(phone):
    """Clean and format phone number."""
    if not phone:
        return ''
    
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    
    # Format US phone numbers
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    # Return original if not standard format
    return phone

def format_currency(amount, currency='USD'):
    """Format currency amount."""
    if not amount:
        return ''
    
    try:
        amount = float(amount)
        if currency == 'USD':
            return f"${amount:,.2f}" if amount != int(amount) else f"${amount:,.0f}"
        return f"{amount:,.2f} {currency}"
    except (ValueError, TypeError):
        return str(amount)

def truncate_text(text, max_length=100, suffix='...'):
    """Truncate text to specified length."""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_time_since(date_time):
    """Get human-readable time since a datetime."""
    if not date_time:
        return ''
    
    now = timezone.now()
    if date_time > now:
        return 'Just now'
    
    diff = now - date_time
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def calculate_conversion_rate(contacts, views):
    """Calculate conversion rate from views to contacts."""
    if not views or views == 0:
        return 0.0
    return round((contacts / views) * 100, 2)

def generate_session_id(request):
    """Generate session ID for analytics tracking."""
    if hasattr(request, 'session') and request.session.session_key:
        return request.session.session_key
    
    # Fallback for anonymous users
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:50]
    return f"anon_{hash(ip + user_agent)}"

def validate_image_file(file):
    """Validate uploaded image file."""
    # Check file size (5MB limit)
    if file.size > 5 * 1024 * 1024:
        raise ValueError("Image file too large. Maximum size is 5MB.")
    
    # Check file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
    if hasattr(file, 'content_type') and file.content_type not in allowed_types:
        raise ValueError("Invalid image type. Allowed types: JPEG, PNG, GIF, WebP.")
    
    return True

def get_popular_search_terms(days=30):
    """Get popular search terms from recent searches."""
    # This would analyze search logs to return popular terms
    # Implementation depends on your search logging strategy
    return [
        'apartments', 'cars', 'jobs', 'furniture', 'electronics',
        'bikes', 'phones', 'laptops', 'houses', 'services'
    ]

def calculate_ad_score(ad):
    """Calculate quality score for ad ranking."""
    score = 0
    
    # Title quality (longer titles generally better)
    if len(ad.title) > 20:
        score += 10
    elif len(ad.title) > 10:
        score += 5
    
    # Description quality
    if len(ad.description) > 100:
        score += 15
    elif len(ad.description) > 50:
        score += 10
    
    # Has images
    if ad.images.exists():
        score += 20
        # Multiple images bonus
        if ad.images.count() > 1:
            score += 10
    
    # Has contact info
    if ad.contact_phone:
        score += 5
    
    # Price specified
    if ad.price:
        score += 5
    
    # Keywords specified
    if ad.keywords:
        score += 5
    
    # Performance bonus
    if ad.view_count > 10:
        score += 5
    
    if ad.contact_count > 0:
        score += 10
    
    # Featured ad bonus
    if ad.plan == 'featured' and ad.is_featured_active:
        score += 25
    
    return min(score, 100)  # Cap at 100