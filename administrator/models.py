from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from content.models import State, Category

User = get_user_model()

class Banner(models.Model):
    """Model for banner advertisements."""
    
    POSITION_CHOICES = [
        ('header', _('Header')),
        ('sidebar', _('Sidebar')),
        ('footer', _('Footer')),
        ('between_ads', _('Between Ads')),
        ('category_page', _('Category Page')),
        ('ad_detail', _('Ad Detail Page')),
    ]
    
    TYPE_CHOICES = [
        ('image', _('Image Banner')),
        ('html', _('HTML Banner')),
        ('text', _('Text Banner')),
    ]
    
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    
    # Banner content
    banner_type = models.CharField(
        _('Banner Type'),
        max_length=20,
        choices=TYPE_CHOICES,
        default='image'
    )
    image = models.ImageField(
        _('Banner Image'),
        upload_to='banners/',
        blank=True,
        null=True
    )
    html_content = models.TextField(
        _('HTML Content'),
        blank=True,
        help_text=_('For HTML banners')
    )
    text_content = models.TextField(
        _('Text Content'),
        blank=True,
        help_text=_('For text banners')
    )
    
    # Targeting
    position = models.CharField(
        _('Position'),
        max_length=20,
        choices=POSITION_CHOICES
    )
    target_states = models.ManyToManyField(
        State,
        blank=True,
        verbose_name=_('Target States'),
        help_text=_('Leave empty to show in all states')
    )
    target_categories = models.ManyToManyField(
        Category,
        blank=True,
        verbose_name=_('Target Categories'),
        help_text=_('Leave empty to show in all categories')
    )
    
    # Link and tracking
    click_url = models.URLField(_('Click URL'), blank=True)
    open_new_tab = models.BooleanField(_('Open in New Tab'), default=True)
    
    # Analytics
    impressions = models.PositiveIntegerField(_('Impressions'), default=0)
    clicks = models.PositiveIntegerField(_('Clicks'), default=0)
    
    # Scheduling
    start_date = models.DateTimeField(_('Start Date'), default=timezone.now)
    end_date = models.DateTimeField(_('End Date'), null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(_('Is Active'), default=True)
    priority = models.PositiveIntegerField(
        _('Priority'),
        default=0,
        help_text=_('Higher numbers have higher priority')
    )
    
    # Management
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_banners',
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Banner')
        verbose_name_plural = _('Banners')
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['position', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['-priority']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def ctr(self):
        """Calculate click-through rate."""
        if self.impressions > 0:
            return (self.clicks / self.impressions) * 100
        return 0
    
    def is_currently_active(self):
        """Check if banner is currently active based on dates."""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True
    
    def increment_impressions(self):
        """Increment impression count."""
        self.impressions = models.F('impressions') + 1
        self.save(update_fields=['impressions'])
    
    def increment_clicks(self):
        """Increment click count."""
        self.clicks = models.F('clicks') + 1
        self.save(update_fields=['clicks'])


class BannerImpression(models.Model):
    """Track individual banner impressions."""
    
    banner = models.ForeignKey(
        Banner,
        on_delete=models.CASCADE,
        related_name='impression_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.TextField(_('User Agent'), blank=True)
    page_url = models.URLField(_('Page URL'), blank=True)
    viewed_at = models.DateTimeField(_('Viewed At'), auto_now_add=True)
    
    # Optional location tracking
    city = models.CharField(_('City'), max_length=100, blank=True)
    state = models.CharField(_('State'), max_length=100, blank=True)
    country = models.CharField(_('Country'), max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('Banner Impression')
        verbose_name_plural = _('Banner Impressions')
        indexes = [
            models.Index(fields=['banner', '-viewed_at']),
            models.Index(fields=['viewed_at']),
        ]


class BannerClick(models.Model):
    """Track individual banner clicks."""
    
    banner = models.ForeignKey(
        Banner,
        on_delete=models.CASCADE,
        related_name='click_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(_('IP Address'))
    user_agent = models.TextField(_('User Agent'), blank=True)
    referrer = models.URLField(_('Referrer URL'), blank=True)
    clicked_at = models.DateTimeField(_('Clicked At'), auto_now_add=True)
    
    # Optional location tracking
    city = models.CharField(_('City'), max_length=100, blank=True)
    state = models.CharField(_('State'), max_length=100, blank=True)
    country = models.CharField(_('Country'), max_length=100, blank=True)
    
    class Meta:
        verbose_name = _('Banner Click')
        verbose_name_plural = _('Banner Clicks')
        indexes = [
            models.Index(fields=['banner', '-clicked_at']),
            models.Index(fields=['clicked_at']),
        ]

class AdminSettings(models.Model):
    """Model for storing basic admin panel settings."""
    
    # Site settings
    site_name = models.CharField(_('Site Name'), max_length=100, default='Classified Ads')
    contact_email = models.EmailField(_('Contact Email'), blank=True)
    support_phone = models.CharField(_('Support Phone'), max_length=20, blank=True)
    
    # Maintenance mode
    maintenance_mode = models.BooleanField(
        _('Maintenance Mode'),
        default=False,
        help_text=_('Enable maintenance mode to block non-admin users')
    )
    maintenance_message = models.TextField(
        _('Maintenance Message'),
        blank=True,
        default='We are currently performing scheduled maintenance. Please check back soon.'
    )
    
    # Ad settings
    ad_approval_required = models.BooleanField(
        _('Ad Approval Required'),
        default=True,
        help_text=_('Require admin approval for new ads')
    )
    auto_approve_ads = models.BooleanField(
        _('Auto Approve Ads'),
        default=False,
        help_text=_('Automatically approve new ads without manual review')
    )
    featured_ad_price = models.DecimalField(
        _('Featured Ad Price'),
        max_digits=10,
        decimal_places=2,
        default=9.99
    )
    featured_ad_duration_days = models.PositiveIntegerField(
        _('Featured Ad Duration Days'),
        default=30,
        help_text=_('Days that featured ads remain active')
    )
    max_images_per_ad = models.PositiveIntegerField(
        _('Max Images Per Ad'),
        default=10
    )
    ad_expiration_days = models.PositiveIntegerField(
        _('Ad Expiration Days'),
        default=90,
        help_text=_('Days after which ads expire')
    )
    
    # User settings
    user_registration_enabled = models.BooleanField(
        _('User Registration Enabled'),
        default=True
    )
    allow_registration = models.BooleanField(
        _('Allow Registration'),
        default=True,
        help_text=_('Allow new users to register')
    )
    email_verification_required = models.BooleanField(
        _('Email Verification Required'),
        default=True
    )
    require_email_verification = models.BooleanField(
        _('Require Email Verification'),
        default=True,
        help_text=_('Force users to verify email before accessing features')
    )
    max_ads_per_user = models.PositiveIntegerField(
        _('Max Ads Per User'),
        default=50,
        help_text=_('Maximum number of active ads per user')
    )
    
    # Notification settings
    admin_email_notifications = models.BooleanField(
        _('Admin Email Notifications'),
        default=True
    )
    user_email_notifications = models.BooleanField(
        _('User Email Notifications'),
        default=True
    )
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_settings',
        verbose_name=_('Updated By')
    )
    
    class Meta:
        verbose_name = _('Admin Settings')
        verbose_name_plural = _('Admin Settings')
    
    def __str__(self):
        return f'Admin Settings - {self.site_name}'
    
    @classmethod
    def get_settings(cls):
        """Get or create admin settings."""
        settings, created = cls.objects.get_or_create(
            pk=1,  # Singleton pattern
            defaults={
                'site_name': 'Classified Ads',
                'contact_email': 'admin@example.com',
            }
        )
        return settings

