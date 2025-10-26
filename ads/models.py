# ads/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Count, Q, Avg
from datetime import timedelta, datetime
from decimal import Decimal
from core.utils import generate_unique_slug, generate_unique_filename

User = get_user_model()


class AdManager(models.Manager):
    """Custom manager for Ad model with common filters."""

    def active(self):
        """Get active (approved, non-expired) ads."""
        return self.filter(status="approved", expires_at__gt=timezone.now())

    def for_state(self, state_code):
        """Get ads for a specific state."""
        return self.filter(state__code__iexact=state_code)

    def featured(self):
        """Get featured ads only."""
        return self.filter(plan="featured")

    def by_category(self, category_slug):
        """Get ads by category slug."""
        return self.filter(category__slug=category_slug)

    def recent(self, days=7):
        """Get recent ads within specified days."""
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)


class Ad(models.Model):
    """Enhanced model for classified ads with analytics."""

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("pending", _("Pending Review")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
        ("expired", _("Expired")),
        ("sold", _("Sold/Closed")),
    ]

    PLAN_CHOICES = [
        ("free", _("Free Plan")),
        ("featured", _("Featured Plan - $9.99")),
    ]

    CONDITION_CHOICES = [
        ("new", _("New")),
        ("like_new", _("Like New")),
        ("good", _("Good")),
        ("fair", _("Fair")),
        ("poor", _("Poor")),
        ("not_applicable", _("Not Applicable")),
    ]

    # Basic Information
    title = models.CharField(
        _("Title"), max_length=255, help_text=_("Descriptive title for the ad")
    )
    slug = models.SlugField(
        _("Slug"),
        unique=True,
        blank=True,
        help_text=_("URL-friendly version of the title"),
    )
    description = models.TextField(
        _("Description"), help_text=_("Detailed description of the item/service")
    )

    # Pricing
    price = models.DecimalField(
        _("Price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Price in USD (leave blank for contact for price)"),
    )
    price_type = models.CharField(
        _("Price Type"),
        max_length=20,
        choices=[
            ("fixed", _("Fixed Price")),
            ("negotiable", _("Negotiable")),
            ("contact", _("Contact for Price")),
            ("free", _("Free")),
            ("swap", _("Swap/Trade")),
        ],
        default="fixed",
        help_text=_("Type of pricing"),
    )

    # Item Details
    condition = models.CharField(
        _("Condition"),
        max_length=20,
        choices=CONDITION_CHOICES,
        default="not_applicable",
        help_text=_("Condition of the item"),
    )

    # Contact Information
    contact_phone = models.CharField(
        _("Contact Phone"),
        max_length=20,
        blank=True,
        help_text=_("Phone number for contact (optional)"),
    )
    contact_email = models.EmailField(
        _("Contact Email"),
        blank=True,
        help_text=_("Email for contact (optional, uses user email if blank)"),
    )
    hide_phone = models.BooleanField(
        _("Hide Phone Number"),
        default=False,
        help_text=_("Hide phone number from public view"),
    )

    # Relationships
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ads", verbose_name=_("User")
    )
    category = models.ForeignKey(
        "content.Category",
        on_delete=models.CASCADE,
        related_name="ads",
        verbose_name=_("Category"),
    )
    city = models.ForeignKey(
        "content.City",
        on_delete=models.CASCADE,
        related_name="ads",
        verbose_name=_("City"),
    )
    state = models.ForeignKey(
        "content.State",
        on_delete=models.CASCADE,
        related_name="ads",
        verbose_name=_("State"),
    )

    # Status & Plan
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current status of the ad",
        verbose_name="Status",
    )
    plan = models.CharField(
        _("Plan"),
        max_length=20,
        choices=PLAN_CHOICES,
        default="free",
        help_text=_("Ad plan type"),
    )

    # Analytics & Tracking
    view_count = models.PositiveIntegerField(
        _("View Count"), default=0, help_text=_("Number of times ad has been viewed")
    )
    unique_view_count = models.PositiveIntegerField(
        _("Unique View Count"),
        default=0,
        help_text=_("Number of unique users who viewed"),
    )
    contact_count = models.PositiveIntegerField(
        _("Contact Count"),
        default=0,
        help_text=_("Number of times contact info was viewed"),
    )
    favorite_count = models.PositiveIntegerField(
        _("Favorite Count"),
        default=0,
        help_text=_("Number of users who favorited this ad"),
    )

    # SEO & Search
    keywords = models.CharField(
        _("Keywords"),
        max_length=500,
        blank=True,
        help_text=_("Comma-separated keywords for better search"),
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        _("Expires At"), help_text=_("When this ad expires")
    )

    # Admin fields
    approved_at = models.DateTimeField(_("Approved At"), null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_ads",
        verbose_name=_("Approved By"),
    )
    admin_notes = models.TextField(
        _("Admin Notes"), blank=True, help_text=_("Internal notes for administrators")
    )
    rejection_reason = models.TextField(
        _("Rejection Reason"),
        blank=True,
        help_text=_("Reason for rejection (shown to user)"),
    )

    # Featured ad payment tracking
    featured_payment_id = models.CharField(
        _("Payment ID"),
        max_length=100,
        blank=True,
        help_text=_("Payment transaction ID for featured ads"),
    )
    featured_expires_at = models.DateTimeField(
        _("Featured Expires At"),
        null=True,
        blank=True,
        help_text=_("When featured status expires"),
    )

    objects = AdManager()

    class Meta:
        verbose_name = _("Ad")
        verbose_name_plural = _("Ads")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["category", "state", "status"]),
            models.Index(fields=["city", "status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["plan", "status"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["featured_expires_at"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, self.title)

        # Set expiration date if not set
        if not self.expires_at:
            days = 30 if self.plan == "free" else 60  # Featured ads last longer
            self.expires_at = timezone.now() + timedelta(days=days)

        # Set featured expiration for paid ads
        if self.plan == "featured" and not self.featured_expires_at:
            self.featured_expires_at = timezone.now() + timedelta(days=30)

        super().save(*args, **kwargs)

    @property
    def is_active(self):
        """Check if ad is active (approved and not expired)."""
        return self.status == "approved" and not self.is_expired

    @property
    def is_expired(self):
        """Check if ad is expired."""
        return timezone.now() > self.expires_at

    @property
    def is_featured_active(self):
        """Check if featured status is still active."""
        if self.plan != "featured":
            return False
        return self.featured_expires_at and timezone.now() < self.featured_expires_at

    @property
    def primary_image(self):
        """Get the primary image for this ad."""
        return self.images.filter(is_primary=True).first()

    @property
    def display_price(self):
        """Get formatted price for display."""
        if self.price_type == "free":
            return "Free"
        elif self.price_type == "contact":
            return "Contact for Price"
        elif self.price_type == "swap":
            return "Swap/Trade"
        elif self.price:
            price_str = (
                f"${self.price:,.0f}"
                if self.price == int(self.price)
                else f"${self.price:,.2f}"
            )
            if self.price_type == "negotiable":
                price_str += " (Negotiable)"
            return price_str
        return "Contact for Price"

    @property
    def contact_email_display(self):
        """Get contact email, fallback to user email."""
        return self.contact_email or self.user.email

    @property
    def time_since_posted(self):
        """Get human-readable time since posted."""
        now = timezone.now()
        diff = now - self.created_at

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

    def increment_view_count(self, unique=False):
        """Increment view count."""
        self.view_count += 1
        if unique:
            self.unique_view_count += 1
        self.save(update_fields=["view_count", "unique_view_count"])

    def increment_contact_count(self):
        """Increment contact count when someone views contact info."""
        self.contact_count += 1
        self.save(update_fields=["contact_count"])

    def get_analytics_data(self, days=30):
        """Get analytics data for this ad."""
        since = timezone.now() - timedelta(days=days)

        daily_views = (
            self.detailed_views.filter(viewed_at__gte=since)
            .extra(select={"day": "date(viewed_at)"})
            .values("day")
            .annotate(views=Count("id"))
            .order_by("day")
        )

        return {
            "total_views": self.view_count,
            "unique_views": self.unique_view_count,
            "contacts": self.contact_count,
            "favorites": self.favorite_count,
            "daily_views": list(daily_views),
            "conversion_rate": (self.contact_count / max(self.view_count, 1)) * 100,
        }


class AdImage(models.Model):
    """Model for ad images with enhanced features."""

    ad = models.ForeignKey(
        Ad, on_delete=models.CASCADE, related_name="images", verbose_name=_("Ad")
    )
    image = models.ImageField(
        _("Image"),
        upload_to=generate_unique_filename,
        help_text=_("Image file (max 5MB)"),
    )
    caption = models.CharField(
        _("Caption"),
        max_length=255,
        blank=True,
        help_text=_("Optional caption for the image"),
    )
    is_primary = models.BooleanField(
        _("Is Primary"),
        default=False,
        help_text=_("Whether this is the main image for the ad"),
    )
    sort_order = models.PositiveIntegerField(
        _("Sort Order"), default=0, help_text=_("Order for displaying images")
    )

    # Image metadata
    file_size = models.PositiveIntegerField(
        _("File Size"), null=True, blank=True, help_text=_("File size in bytes")
    )
    width = models.PositiveIntegerField(_("Width"), null=True, blank=True)
    height = models.PositiveIntegerField(_("Height"), null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Ad Image")
        verbose_name_plural = _("Ad Images")
        ordering = ["sort_order", "created_at"]
        indexes = [
            models.Index(fields=["ad", "is_primary"]),
            models.Index(fields=["ad", "sort_order"]),
        ]

    def __str__(self):
        return f"Image for {self.ad.title}"

    def save(self, *args, **kwargs):
        # If this is set as primary, make sure other images for the same ad are not primary
        if self.is_primary:
            AdImage.objects.filter(ad=self.ad, is_primary=True).update(is_primary=False)

        # Set file metadata
        if self.image:
            self.file_size = self.image.size
            # You can add PIL here to get width/height if needed

        super().save(*args, **kwargs)


class AdView(models.Model):
    """Enhanced model to track ad views for analytics."""

    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        related_name="detailed_views",
        verbose_name=_("Ad"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ad_views",
        verbose_name=_("User"),
    )
    ip_address = models.GenericIPAddressField(_("IP Address"))
    user_agent = models.TextField(
        _("User Agent"), help_text=_("Browser user agent string")
    )
    referrer = models.URLField(
        _("Referrer"), blank=True, help_text=_("Page that referred to this ad")
    )
    device_type = models.CharField(
        _("Device Type"),
        max_length=20,
        choices=[
            ("desktop", _("Desktop")),
            ("mobile", _("Mobile")),
            ("tablet", _("Tablet")),
            ("unknown", _("Unknown")),
        ],
        default="unknown",
    )

    # Session tracking
    session_id = models.CharField(
        _("Session ID"),
        max_length=50,
        blank=True,
        help_text=_("Anonymous session identifier"),
    )

    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Ad View")
        verbose_name_plural = _("Ad Views")
        # Prevent duplicate views from same session within 1 hour
        unique_together = ["ad", "session_id"]
        indexes = [
            models.Index(fields=["ad", "-viewed_at"]),
            models.Index(fields=["user", "-viewed_at"]),
            models.Index(fields=["ip_address", "-viewed_at"]),
        ]


class AdContact(models.Model):
    """Track when users view contact information."""

    ad = models.ForeignKey(
        Ad, on_delete=models.CASCADE, related_name="contact_views", verbose_name=_("Ad")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contact_views",
        verbose_name=_("User"),
    )
    ip_address = models.GenericIPAddressField(_("IP Address"))
    contact_type = models.CharField(
        _("Contact Type"),
        max_length=20,
        choices=[
            ("phone", _("Phone Number")),
            ("email", _("Email Address")),
            ("both", _("Both Phone and Email")),
        ],
    )

    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Ad Contact View")
        verbose_name_plural = _("Ad Contact Views")
        indexes = [
            models.Index(fields=["ad", "-viewed_at"]),
            models.Index(fields=["user", "-viewed_at"]),
        ]


class AdFavorite(models.Model):
    """Track user favorites for analytics and user features."""

    ad = models.ForeignKey(
        Ad, on_delete=models.CASCADE, related_name="favorites", verbose_name=_("Ad")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_ads",
        verbose_name=_("User"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Ad Favorite")
        verbose_name_plural = _("Ad Favorites")
        unique_together = ["ad", "user"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["ad", "-created_at"]),
        ]


class AdReport(models.Model):
    """Model for reporting inappropriate ads."""

    REASON_CHOICES = [
        ("spam", _("Spam")),
        ("inappropriate", _("Inappropriate Content")),
        ("fraud", _("Fraudulent/Scam")),
        ("duplicate", _("Duplicate Posting")),
        ("wrong_category", _("Wrong Category")),
        ("other", _("Other")),
    ]

    ad = models.ForeignKey(
        Ad, on_delete=models.CASCADE, related_name="reports", verbose_name=_("Ad")
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ad_reports",
        verbose_name=_("Reported By"),
    )
    reason = models.CharField(_("Reason"), max_length=20, choices=REASON_CHOICES)
    description = models.TextField(
        _("Description"), help_text=_("Additional details about the report")
    )

    # Admin handling
    is_reviewed = models.BooleanField(_("Is Reviewed"), default=False)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_reports",
        verbose_name=_("Reviewed By"),
    )
    admin_notes = models.TextField(_("Admin Notes"), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(_("Reviewed At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Ad Report")
        verbose_name_plural = _("Ad Reports")
        unique_together = ["ad", "reported_by"]
        indexes = [
            models.Index(fields=["ad", "-created_at"]),
            models.Index(fields=["is_reviewed", "-created_at"]),
        ]
