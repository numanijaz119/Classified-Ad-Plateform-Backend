import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import UserManager

class User(AbstractUser):
    """
    Custom user model with email as the primary identifier.
    """
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[AbstractUser.username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
        blank=True,  # Make username optional
        null=True,
    )
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    phone = models.CharField(_('phone number'), max_length=20, blank=True)
    
    # Profile fields
    avatar = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True,
        help_text=_('Profile picture')
    )
    
    # Location fields - will be set via foreign keys to locations app
    # primary_city and primary_state will be added as foreign keys later
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(
        max_length=6,
        blank=True,
        help_text=_('Code for email verification')
    )
    
    # Google OAuth fields
    google_id = models.CharField(
        max_length=255, 
        blank=True, 
        unique=True, 
        null=True,
        help_text=_('Google account ID for OAuth')
    )
    
    # Account status
    is_suspended = models.BooleanField(
        default=False,
        help_text=_('Account suspended by admin')
    )
    suspension_reason = models.TextField(
        blank=True,
        help_text=_('Reason for suspension')
    )
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['google_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip()
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
    
    def save(self, *args, **kwargs):
        # Generate username from email if not provided
        if not self.username:
            self.username = self.email.split('@')[0]
            # Ensure username uniqueness
            original_username = self.username
            counter = 1
            while User.objects.filter(username=self.username).exists():
                self.username = f"{original_username}{counter}"
                counter += 1
        
        super().save(*args, **kwargs)