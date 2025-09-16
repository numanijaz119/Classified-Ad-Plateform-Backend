from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from core.utils import generate_unique_slug, generate_unique_filename

User = get_user_model()

class Ad(models.Model):
    """Model for classified ads."""
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending', _('Pending Review')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('expired', _('Expired')),
    ]
    
    PLAN_CHOICES = [
        ('free', _('Free Plan')),
        ('featured', _('Featured Plan')),
    ]
    
    # Basic Information
    title = models.CharField(
        _('Title'),
        max_length=255,
        help_text=_('Descriptive title for the ad')
    )
    slug = models.SlugField(
        _('Slug'),
        unique=True,
        blank=True,
        help_text=_('URL-friendly version of the title')
    )
    description = models.TextField(
        _('Description'),
        help_text=_('Detailed description of the item/service')
    )
    price = models.CharField(
        _('Price'),
        max_length=100,
        blank=True,
        help_text=_('Price information (flexible text field)')
    )
    
    # Relationships - Updated references
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ads',
        verbose_name=_('User')
    )
    category = models.ForeignKey(
        'content.Category',  # Updated reference
        on_delete=models.CASCADE,
        related_name='ads',
        verbose_name=_('Category')
    )
    city = models.ForeignKey(
        'content.City',      # Updated reference
        on_delete=models.CASCADE,
        related_name='ads',
        verbose_name=_('City')
    )
    state = models.ForeignKey(
        'content.State',     # Updated reference
        on_delete=models.CASCADE,
        related_name='ads',
        verbose_name=_('State')
    )
    
    # Contact Information
    contact_phone = models.CharField(
        _('Contact Phone'),
        max_length=20,
        help_text=_('Phone number for contact')
    )
    contact_email = models.EmailField(
        _('Contact Email'),
        help_text=_('Email address for contact')
    )
    
    # Plan and Status
    plan = models.CharField(
        _('Plan'),
        max_length=10,
        choices=PLAN_CHOICES,
        default='free'
    )
    status = models.CharField(
        _('Status'),
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Analytics
    view_count = models.PositiveIntegerField(
        _('View Count'),
        default=0,
        help_text=_('Number of times this ad was viewed')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        _('Expires At'),
        help_text=_('When this ad expires')
    )
    approved_at = models.DateTimeField(
        _('Approved At'),
        null=True,
        blank=True
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_ads',
        verbose_name=_('Approved By')
    )
    
    # Admin fields
    admin_notes = models.TextField(
        _('Admin Notes'),
        blank=True,
        help_text=_('Internal notes for administrators')
    )
    rejection_reason = models.TextField(
        _('Rejection Reason'),
        blank=True,
        help_text=_('Reason for rejection (shown to user)')
    )
    
    class Meta:
        verbose_name = _('Ad')
        verbose_name_plural = _('Ads')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['category', 'state', 'status']),
            models.Index(fields=['city', 'status', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['plan', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Generate unique slug
        if not self.slug:
            self.slug = generate_unique_slug(self.title, Ad)
        
        # Set state from city if not provided
        if not self.state_id and self.city_id:
            self.state = self.city.state
        
        # Set expiration date based on plan
        if not self.expires_at:
            if self.plan == 'free':
                self.expires_at = timezone.now() + timedelta(days=30)
            else:  # featured
                self.expires_at = timezone.now() + timedelta(days=60)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if the ad is expired."""
        return timezone.now() > self.expires_at
    
    @property
    def is_active(self):
        """Check if the ad is active (approved and not expired)."""
        return self.status == 'approved' and not self.is_expired
    
    @property
    def primary_image(self):
        """Get the primary image for this ad."""
        return self.images.filter(is_primary=True).first()
    
    def increment_view_count(self):
        """Increment the view count."""
        self.view_count += 1
        self.save(update_fields=['view_count'])

class AdImage(models.Model):
    """Model for ad images."""
    
    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Ad')
    )
    image = models.ImageField(
        _('Image'),
        upload_to=generate_unique_filename,
        help_text=_('Image file')
    )
    caption = models.CharField(
        _('Caption'),
        max_length=255,
        blank=True,
        help_text=_('Optional caption for the image')
    )
    is_primary = models.BooleanField(
        _('Is Primary'),
        default=False,
        help_text=_('Whether this is the main image for the ad')
    )
    sort_order = models.PositiveIntegerField(
        _('Sort Order'),
        default=0,
        help_text=_('Order for displaying images')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Ad Image')
        verbose_name_plural = _('Ad Images')
        ordering = ['sort_order', 'created_at']
        indexes = [
            models.Index(fields=['ad', 'is_primary']),
            models.Index(fields=['ad', 'sort_order']),
        ]
    
    def __str__(self):
        return f"Image for {self.ad.title}"
    
    def save(self, *args, **kwargs):
        # If this is set as primary, make sure other images for the same ad are not primary
        if self.is_primary:
            AdImage.objects.filter(ad=self.ad, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)

class AdView(models.Model):
    """Model to track ad views (for analytics)."""
    
    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        related_name='detailed_views',
        verbose_name=_('Ad')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ad_views',
        verbose_name=_('User')
    )
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.TextField(
        _('User Agent'),
        help_text=_('Browser user agent string')
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Ad View')
        verbose_name_plural = _('Ad Views')
        # Prevent duplicate views from same IP/user agent
        unique_together = ['ad', 'ip_address', 'user_agent']
        indexes = [
            models.Index(fields=['ad', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
        ]
