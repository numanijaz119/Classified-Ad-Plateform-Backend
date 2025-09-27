from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from core.utils import generate_unique_filename

class State(models.Model):
    """Model for US states in the platform."""
    
    name = models.CharField(
        _('State Name'),
        max_length=100,
        unique=True,
        help_text=_('Full state name (e.g., Illinois)')
    )
    code = models.CharField(
        _('State Code'),
        max_length=2,
        unique=True,
        help_text=_('2-letter state code (e.g., IL)')
    )
    domain = models.CharField(
        _('Domain'),
        max_length=255,
        unique=True,
        help_text=_('Domain for this state (e.g., desiloginil.com)')
    )
    
    # Branding (minimal for Phase 1)
    logo = models.ImageField(
        _('State Logo'),
        upload_to='states/logos/',
        help_text=_('Logo for this state')
    )
    favicon = models.ImageField(
        _('Favicon'),
        upload_to='states/favicons/',
        null=True,
        blank=True,
        help_text=_('Favicon for this state (optional)')
    )
    
    # SEO fields (for Phase 1)
    meta_title = models.CharField(
        _('Meta Title'),
        max_length=255,
        help_text=_('SEO title for the state homepage')
    )
    meta_description = models.TextField(
        _('Meta Description'),
        help_text=_('SEO description for the state homepage')
    )
    
    # Status
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Whether this state is active and accepting ads')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('State')
        verbose_name_plural = _('States')
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['domain']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class City(models.Model):
    """Model for cities within states."""
    
    name = models.CharField(
        _('City Name'),
        max_length=100,
        help_text=_('City name (e.g., Chicago)')
    )
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name='cities',
        verbose_name=_('State')
    )
    photo = models.ImageField(
        _('City Photo'),
        upload_to=generate_unique_filename,
        null=True,
        blank=True,
        help_text=_('City photo/banner image for display')
    )
    
    # Optional geographic data
    latitude = models.DecimalField(
        _('Latitude'),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_('City latitude for mapping (optional)')
    )
    longitude = models.DecimalField(
        _('Longitude'),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_('City longitude for mapping (optional)')
    )
    
    # City importance
    is_major = models.BooleanField(
        _('Major City'),
        default=False,
        help_text=_('Whether this is a major city (appears first in lists)')
    )
    
    # Status
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Whether this city accepts ads')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('City')
        verbose_name_plural = _('Cities')
        unique_together = ['name', 'state']
        ordering = ['-is_major', 'name']
        indexes = [
            models.Index(fields=['state', 'is_major']),
            models.Index(fields=['state', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name}, {self.state.code}"

class Category(models.Model):
    """Model for ad categories."""
    
    name = models.CharField(
        _('Category Name'),
        max_length=100,
        unique=True,
        help_text=_('Category name (e.g., Jobs, Real Estate)')
    )
    slug = models.SlugField(
        _('Slug'),
        unique=True,
        blank=True,
        help_text=_('URL-friendly version of the category name')
    )
    icon = models.CharField(
        _('Icon'),
        max_length=50,
        help_text=_('Icon for the category (emoji or CSS class)')
    )
    description = models.TextField(
        _('Description'),
        blank=True,
        help_text=_('Optional description of the category')
    )
    
    # Ordering
    sort_order = models.PositiveIntegerField(
        _('Sort Order'),
        default=0,
        help_text=_('Order for displaying categories (lower numbers first)')
    )
    
    # Status
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Whether this category accepts new ads')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'sort_order']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_active_ads_count(self):
        """Get count of active ads in this category."""
        from ads.models import Ad
        from django.utils import timezone
        
        return self.ads.filter(
            status='approved',
            expires_at__gt=timezone.now()
        ).count()