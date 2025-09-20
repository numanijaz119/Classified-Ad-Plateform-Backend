import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
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
        blank=True,
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
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(
        max_length=6,
        blank=True,
        help_text=_('6-digit code for email verification')
    )
    email_verification_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the email verification code expires')
    )
    
    # Password reset
    password_reset_token = models.CharField(
        max_length=6,
        blank=True,
        help_text=_('6-digit code for password reset')
    )
    password_reset_expires = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the password reset code expires')
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
            models.Index(fields=['email_verification_token']),
            models.Index(fields=['password_reset_token']),
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
    
    def is_email_verification_valid(self):
        """Check if email verification token is still valid."""
        if not self.email_verification_token or not self.email_verification_expires:
            return False
        return timezone.now() < self.email_verification_expires
    
    def is_password_reset_valid(self):
        """Check if password reset token is still valid."""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        return timezone.now() < self.password_reset_expires
    
    def clear_email_verification(self):
        """Clear email verification token and expiry."""
        self.email_verification_token = ''
        self.email_verification_expires = None
        
    def clear_password_reset(self):
        """Clear password reset token and expiry."""
        self.password_reset_token = ''
        self.password_reset_expires = None
    
    def set_email_verification_code(self, code, expires_in_minutes=15):
        """Set email verification code with expiry."""
        self.email_verification_token = code
        self.email_verification_expires = timezone.now() + timedelta(minutes=expires_in_minutes)
    
    def set_password_reset_code(self, code, expires_in_minutes=15):
        """Set password reset code with expiry."""
        self.password_reset_token = code
        self.password_reset_expires = timezone.now() + timedelta(minutes=expires_in_minutes)