from rest_framework import serializers
from django.contrib.auth import get_user_model
from ads.models import Ad, AdReport
from content.models import Category, State, City
from .models import Banner, AdminSettings
from ads.serializers import AdImageSerializer

User = get_user_model()


class AdminLoginSerializer(serializers.Serializer):
    """Serializer for admin login."""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, value):
        return value.lower().strip()


class AdminTokenSerializer(serializers.Serializer):
    """Serializer for token verification."""
    
    token = serializers.CharField()


class AdminPasswordChangeSerializer(serializers.Serializer):
    """Serializer for admin password change."""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    
    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

# ============================================================================
# AD MANAGEMENT SERIALIZERS
# ============================================================================


class AdminAdSerializer(serializers.ModelSerializer):
    """Serializer for admin ad management."""

    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    state_code = serializers.CharField(source="state.code", read_only=True)
    days_ago = serializers.SerializerMethodField()
    images = AdImageSerializer(many=True, read_only=True)
    primary_image = AdImageSerializer(read_only=True)

    class Meta:
        model = Ad
        fields = [
            "id",
            "title",
            "description",
            "price",
            "status",
            "plan",
            "view_count",
            "contact_count",
            "favorite_count",
            "created_at",
            "updated_at",
            "expires_at",
            "user_name",
            "user_email",
            "category_name",
            "city_name",
            "state_name",
            "state_code",
            "rejection_reason",
            "admin_notes",
            "days_ago",
            "images",
            "primary_image",
        ]

    def get_days_ago(self, obj):
        """Get days since ad was created."""
        from django.utils import timezone

        delta = timezone.now() - obj.created_at
        return delta.days


class AdminAdActionSerializer(serializers.Serializer):
    """Serializer for admin ad actions."""

    ACTION_CHOICES = [
        ("approve", "Approve"),
        ("reject", "Reject"),
        ("delete", "Delete"),
        ("feature", "Make Featured"),
        ("unfeature", "Remove Featured"),
    ]

    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    admin_notes = serializers.CharField(
        required=False, allow_blank=True, max_length=1000
    )


# ============================================================================
# USER MANAGEMENT SERIALIZERS
# ============================================================================


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management."""

    full_name = serializers.CharField(source="get_full_name", read_only=True)
    total_ads = serializers.SerializerMethodField()
    active_ads = serializers.SerializerMethodField()
    pending_ads = serializers.SerializerMethodField()
    featured_ads = serializers.SerializerMethodField()
    days_since_joined = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "first_name",
            "last_name",
            "phone",
            "is_active",
            "is_suspended",
            "suspension_reason",
            "email_verified",
            "created_at",
            "last_login",
            "total_ads",
            "active_ads",
            "pending_ads",
            "featured_ads",
            "days_since_joined",
            "status_display",
        ]
        read_only_fields = ["created_at", "last_login"]

    def get_total_ads(self, obj):
        return obj.ads.exclude(status="deleted").count()

    def get_active_ads(self, obj):
        return obj.ads.filter(status="approved").count()

    def get_pending_ads(self, obj):
        return obj.ads.filter(status="pending").count()

    def get_featured_ads(self, obj):
        return obj.ads.filter(plan="featured").count()

    def get_days_since_joined(self, obj):
        from django.utils import timezone

        delta = timezone.now() - obj.created_at
        return delta.days

    def get_status_display(self, obj):
        if not obj.is_active:
            return "banned"
        elif obj.is_suspended:
            return "suspended"
        else:
            return "active"


class AdminUserActionSerializer(serializers.Serializer):
    """Serializer for admin user actions."""

    ACTION_CHOICES = [
        ("ban", "Ban User"),
        ("suspend", "Suspend User"),
        ("activate", "Activate User"),
    ]

    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


# ============================================================================
# REPORTS MANAGEMENT SERIALIZERS
# ============================================================================


class AdminReportSerializer(serializers.ModelSerializer):
    """Serializer for admin report management."""

    ad = serializers.SerializerMethodField()
    reported_by = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    days_ago = serializers.SerializerMethodField()

    class Meta:
        model = AdReport
        fields = [
            "id",
            "ad",
            "reported_by",
            "reviewed_by",
            "reason",
            "reason_display",
            "description",
            "is_reviewed",
            "admin_notes",
            "created_at",
            "reviewed_at",
            "days_ago",
        ]

    def get_ad(self, obj):
        """Return ad details as nested object."""
        if obj.ad:
            # Get first image if available
            first_image = obj.ad.images.first()
            image_url = None
            if first_image and first_image.image:
                from django.conf import settings

                image_url = (
                    settings.MEDIA_URL + str(first_image.image)
                    if not str(first_image.image).startswith("http")
                    else str(first_image.image)
                )

            return {
                "id": obj.ad.id,
                "title": obj.ad.title,
                "slug": obj.ad.slug,
                "status": obj.ad.status,
                "image": image_url,
            }
        return None

    def get_reported_by(self, obj):
        """Return reporter details as nested object."""
        if obj.reported_by:
            return {
                "id": obj.reported_by.id,
                "email": obj.reported_by.email,
                "full_name": obj.reported_by.get_full_name(),
            }
        return None

    def get_reviewed_by(self, obj):
        """Return reviewer details as nested object."""
        if obj.reviewed_by:
            return {
                "id": obj.reviewed_by.id,
                "email": obj.reviewed_by.email,
            }
        return None

    def get_days_ago(self, obj):
        from django.utils import timezone

        delta = timezone.now() - obj.created_at
        return delta.days


class AdminReportActionSerializer(serializers.Serializer):
    """Serializer for admin report actions."""

    ACTION_CHOICES = [
        ("approve", "Approve Report"),
        ("dismiss", "Dismiss Report"),
    ]

    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    admin_notes = serializers.CharField(
        required=False, allow_blank=True, max_length=1000
    )


# ============================================================================
# BANNER MANAGEMENT SERIALIZERS
# ============================================================================


class AdminBannerSerializer(serializers.ModelSerializer):
    """Serializer for banner management."""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )
    ctr = serializers.ReadOnlyField()
    is_currently_active = serializers.ReadOnlyField()
    target_states_display = serializers.SerializerMethodField()
    target_categories_display = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            "id",
            "title",
            "description",
            "banner_type",
            "image",
            "html_content",
            "text_content",
            "position",
            "target_states",
            "target_categories",
            "click_url",
            "open_new_tab",
            "impressions",
            "clicks",
            "ctr",
            "start_date",
            "end_date",
            "is_active",
            "is_currently_active",
            "priority",
            "created_by_name",
            "created_at",
            "updated_at",
            "target_states_display",
            "target_categories_display",
        ]
        read_only_fields = [
            "created_by",
            "created_at",
            "updated_at",
            "impressions",
            "clicks",
        ]

    def get_target_states_display(self, obj):
        return [
            {"id": state.id, "name": state.name} for state in obj.target_states.all()
        ]

    def get_target_categories_display(self, obj):
        return [{"id": cat.id, "name": cat.name} for cat in obj.target_categories.all()]

    def validate(self, data):
        """Validate banner data."""
        banner_type = data.get("banner_type")

        if banner_type == "image" and not data.get("image"):
            raise serializers.ValidationError("Image is required for image banners.")

        if banner_type == "html" and not data.get("html_content"):
            raise serializers.ValidationError(
                "HTML content is required for HTML banners."
            )

        if banner_type == "text" and not data.get("text_content"):
            raise serializers.ValidationError(
                "Text content is required for text banners."
            )

        # Validate date range
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("End date must be after start date.")

        return data


# ============================================================================
# CONTENT MANAGEMENT SERIALIZERS
# ============================================================================


class AdminStateSerializer(serializers.ModelSerializer):
    """Serializer for admin state management."""

    total_ads = serializers.SerializerMethodField(read_only=True)
    active_ads = serializers.SerializerMethodField(read_only=True)
    users_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = State
        fields = [
            "id",
            "code",
            "name",
            "domain",
            "logo",
            "favicon",
            "meta_title",
            "meta_description",
            "is_active",
            "total_ads",
            "active_ads",
            "users_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_code(self, value):
        """Validate state code is unique and uppercase."""
        value = value.upper()
        instance = self.instance
        
        # Check if code already exists (excluding current instance for updates)
        if instance:
            if State.objects.exclude(id=instance.id).filter(code=value).exists():
                raise serializers.ValidationError(f"State with code '{value}' already exists")
        else:
            if State.objects.filter(code=value).exists():
                raise serializers.ValidationError(f"State with code '{value}' already exists")
        
        return value

    def validate_domain(self, value):
        """Validate domain is unique."""
        instance = self.instance
        
        # Check if domain already exists (excluding current instance for updates)
        if instance:
            if State.objects.exclude(id=instance.id).filter(domain=value).exists():
                raise serializers.ValidationError(f"State with domain '{value}' already exists")
        else:
            if State.objects.filter(domain=value).exists():
                raise serializers.ValidationError(f"State with domain '{value}' already exists")
        
        return value

    def validate_name(self, value):
        """Validate name is unique."""
        instance = self.instance
        
        # Check if name already exists (excluding current instance for updates)
        if instance:
            if State.objects.exclude(id=instance.id).filter(name=value).exists():
                raise serializers.ValidationError(f"State with name '{value}' already exists")
        else:
            if State.objects.filter(name=value).exists():
                raise serializers.ValidationError(f"State with name '{value}' already exists")
        
        return value

    def get_total_ads(self, obj):
        return obj.ads.exclude(status="deleted").count()

    def get_active_ads(self, obj):
        return obj.ads.filter(status="approved").count()

    def get_users_count(self, obj):
        return obj.ads.values("user").distinct().count()


class AdminCategorySerializer(serializers.ModelSerializer):
    """Serializer for admin category management."""

    total_ads = serializers.SerializerMethodField()
    active_ads = serializers.SerializerMethodField()
    pending_ads = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "icon",
            "description",
            "is_active",
            "sort_order",
            "total_ads",
            "active_ads",
            "pending_ads",
        ]

    def get_total_ads(self, obj):
        return obj.ads.exclude(status="deleted").count()

    def get_active_ads(self, obj):
        return obj.ads.filter(status="approved").count()

    def get_pending_ads(self, obj):
        return obj.ads.filter(status="pending").count()


class AdminCitySerializer(serializers.ModelSerializer):
    """Serializer for admin city management."""

    state_name = serializers.CharField(source="state.name", read_only=True)
    total_ads = serializers.SerializerMethodField()

    class Meta:
        model = City
        fields = [
            "id",
            "name",
            "state",
            "state_name",
            "is_active",
            "sort_order",
            "total_ads",
        ]

    def get_total_ads(self, obj):
        return obj.ads.exclude(status="deleted").count()


# ============================================================================
# SETTINGS SERIALIZERS
# ============================================================================


class AdminSettingsSerializer(serializers.ModelSerializer):
    """Serializer for admin settings."""

    updated_by_name = serializers.CharField(
        source="updated_by.get_full_name", read_only=True
    )

    class Meta:
        model = AdminSettings
        fields = [
            "site_name",
            "contact_email",
            "support_phone",
            "ad_approval_required",
            "featured_ad_price",
            "max_images_per_ad",
            "ad_expiration_days",
            "user_registration_enabled",
            "email_verification_required",
            "max_ads_per_user",
            "admin_email_notifications",
            "user_email_notifications",
            "updated_at",
            "updated_by_name",
        ]
        read_only_fields = ["updated_at", "updated_by_name"]

    def validate_featured_ad_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Featured ad price cannot be negative.")
        return value

    def validate_max_images_per_ad(self, value):
        if value < 1 or value > 50:
            raise serializers.ValidationError(
                "Max images per ad must be between 1 and 50."
            )
        return value

    def validate_ad_expiration_days(self, value):
        if value < 1 or value > 365:
            raise serializers.ValidationError(
                "Ad expiration days must be between 1 and 365."
            )
        return value


# ============================================================================
# ANALYTICS SERIALIZERS
# ============================================================================


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics."""

    total_ads = serializers.IntegerField()
    pending_ads = serializers.IntegerField()
    active_ads = serializers.IntegerField()
    featured_ads = serializers.IntegerField()
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    suspended_users = serializers.IntegerField()
    banned_users = serializers.IntegerField()
    monthly_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    recent_ads = serializers.IntegerField()
    pending_reports = serializers.IntegerField()
    total_reports = serializers.IntegerField()


class AnalyticsDataPointSerializer(serializers.Serializer):
    """Serializer for analytics data points."""

    day = serializers.DateField()
    count = serializers.IntegerField()


class CategoryStatsSerializer(serializers.Serializer):
    """Serializer for category statistics."""

    name = serializers.CharField()
    total_ads = serializers.IntegerField()
    active_ads = serializers.IntegerField()


class UserGrowthSerializer(serializers.Serializer):
    """Serializer for user growth analytics."""

    day = serializers.DateField()
    new_users = serializers.IntegerField()


class RevenueStatsSerializer(serializers.Serializer):
    """Serializer for revenue statistics."""

    month = serializers.CharField()
    featured_ads = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)


class TopUserSerializer(serializers.Serializer):
    """Serializer for top users analytics."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    ads_count = serializers.IntegerField()
    joined = serializers.DateTimeField()


# ============================================================================
# BULK ACTION SERIALIZERS
# ============================================================================


class BulkAdActionSerializer(serializers.Serializer):
    """Serializer for bulk ad actions."""

    ACTION_CHOICES = [
        ("approve", "Approve Selected"),
        ("reject", "Reject Selected"),
        ("delete", "Delete Selected"),
        ("feature", "Feature Selected"),
        ("unfeature", "Unfeature Selected"),
    ]

    ad_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=100
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
    admin_notes = serializers.CharField(
        required=False, allow_blank=True, max_length=1000
    )


class BulkUserActionSerializer(serializers.Serializer):
    """Serializer for bulk user actions."""

    ACTION_CHOICES = [
        ("ban", "Ban Selected"),
        ("suspend", "Suspend Selected"),
        ("activate", "Activate Selected"),
    ]

    user_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=50
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
