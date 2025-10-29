# ads/serializers.py
from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Ad, AdImage, AdView, AdContact, AdFavorite, AdReport
from content.serializers import (
    CitySimpleSerializer,
    StateSimpleSerializer,
    CategorySimpleSerializer,
)
from accounts.serializers import UserPublicSerializer

User = get_user_model()


class AdImageSerializer(serializers.ModelSerializer):
    """Serializer for ad images."""

    class Meta:
        model = AdImage
        fields = [
            "id",
            "image",
            "caption",
            "is_primary",
            "sort_order",
            "file_size",
            "width",
            "height",
            "created_at",
        ]
        read_only_fields = ["id", "file_size", "width", "height", "created_at"]


class AdImageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating ad images."""

    class Meta:
        model = AdImage
        fields = ["image", "caption", "is_primary", "sort_order"]


class AdListSerializer(serializers.ModelSerializer):
    """Serializer for ad listings (public view)."""

    category = CategorySimpleSerializer(read_only=True)
    city = CitySimpleSerializer(read_only=True)
    state = StateSimpleSerializer(read_only=True)
    primary_image = AdImageSerializer(read_only=True)
    display_price = serializers.CharField(read_only=True)
    time_since_posted = serializers.CharField(read_only=True)
    is_featured_active = serializers.BooleanField(read_only=True)
    price_type = serializers.CharField(read_only=True)

    # NEW FIELDS FOR OWNERSHIP CHECK
    is_owner = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = Ad
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "display_price",
            "price_type",
            "condition",
            "category",
            "city",
            "state",
            "plan",
            "view_count",
            "primary_image",
            "time_since_posted",
            "is_featured_active",
            "created_at",
            "is_owner",
            "user_id",  # Added is_owner and user_id
        ]

    def get_is_owner(self, obj):
        """Check if the current user owns this ad."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


# class AdDetailSerializer(serializers.ModelSerializer):
#     """Detailed serializer for single ad view."""

#     user = UserPublicSerializer(read_only=True)
#     category = CategorySimpleSerializer(read_only=True)
#     city = CitySimpleSerializer(read_only=True)
#     state = StateSimpleSerializer(read_only=True)
#     images = AdImageSerializer(many=True, read_only=True)
#     display_price = serializers.CharField(read_only=True)
#     time_since_posted = serializers.CharField(read_only=True)
#     is_featured_active = serializers.BooleanField(read_only=True)
#     contact_email_display = serializers.CharField(read_only=True)
#     price_type = serializers.CharField(read_only=True)

#     # Analytics data (only for ad owner)
#     analytics_data = serializers.SerializerMethodField()

#     class Meta:
#         model = Ad
#         fields = [
#             'id', 'slug', 'title', 'description', 'display_price', 'price',
#             'price_type', 'condition', 'contact_phone', 'contact_email_display',
#             'hide_phone', 'user', 'category', 'city', 'state', 'plan',
#             'view_count', 'unique_view_count', 'contact_count', 'favorite_count',
#             'keywords', 'images', 'time_since_posted', 'is_featured_active',
#             'created_at', 'updated_at', 'expires_at', 'analytics_data'
#         ]

#     def get_analytics_data(self, obj):
#         """Return analytics data only for ad owner."""
#         request = self.context.get('request')
#         if request and request.user == obj.user:
#             return obj.get_analytics_data()
#         return None


class AdDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single ad view."""

    user = UserPublicSerializer(read_only=True)
    category = CategorySimpleSerializer(read_only=True)
    city = CitySimpleSerializer(read_only=True)
    state = StateSimpleSerializer(read_only=True)
    images = AdImageSerializer(many=True, read_only=True)
    display_price = serializers.CharField(read_only=True)
    time_since_posted = serializers.CharField(read_only=True)
    is_featured_active = serializers.BooleanField(read_only=True)
    contact_email_display = serializers.CharField(read_only=True)
    price_type = serializers.CharField(read_only=True)

    # Analytics data (only for ad owner)
    analytics_data = serializers.SerializerMethodField()

    # NEW FIELDS FOR OWNERSHIP CHECK
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "display_price",
            "price",
            "price_type",
            "condition",
            "contact_phone",
            "contact_email_display",
            "hide_phone",
            "user",
            "category",
            "city",
            "state",
            "plan",
            "view_count",
            "unique_view_count",
            "contact_count",
            "favorite_count",
            "keywords",
            "images",
            "time_since_posted",
            "is_featured_active",
            "created_at",
            "updated_at",
            "expires_at",
            "analytics_data",
            "is_owner",  # Added is_owner
        ]

    def get_analytics_data(self, obj):
        """Return analytics data only for ad owner."""
        request = self.context.get("request")
        if request and request.user == obj.user:
            return obj.get_analytics_data()
        return None

    def get_is_owner(self, obj):
        """Check if the current user owns this ad."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.user == request.user
        return False


class AdCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new ads."""

    images = AdImageCreateSerializer(many=True, required=False)

    class Meta:
        model = Ad
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "price",
            "price_type",
            "condition",
            "contact_phone",
            "contact_email",
            "hide_phone",
            "category",
            "city",
            "keywords",
            "images",
            "plan",
            "status",
        ]
        read_only_fields = ["id", "slug", "status"]

    def validate(self, data):
        """Validate price based on price_type."""
        price_type = data.get("price_type", "fixed")
        price = data.get("price")

        # For contact/free/swap: price must be None
        if price_type in ["contact", "free", "swap"]:
            if price and price > 0:
                raise serializers.ValidationError(
                    {"price": f"Price must be empty when price type is '{price_type}'."}
                )
            data["price"] = None  # Auto-fix

        # For fixed/negotiable: price is required
        elif price_type in ["fixed", "negotiable"]:
            if not price or price <= 0:
                raise serializers.ValidationError(
                    {"price": f"Price is required when price type is '{price_type}'."}
                )

        return data

    def validate_category(self, value):
        """Ensure category is active."""
        if not value.is_active:
            raise serializers.ValidationError("Selected category is not available.")
        return value

    def validate_city(self, value):
        """Ensure city is active and matches state."""
        if not value.is_active:
            raise serializers.ValidationError("Selected city is not available.")
        return value

    def create(self, validated_data):
        """Create ad with images."""
        images_data = validated_data.pop("images", [])

        # Set user and state from context
        validated_data["user"] = self.context["request"].user
        validated_data["state"] = validated_data["city"].state
        
        # Check auto-approve setting
        from administrator.models import AdminSettings
        settings = AdminSettings.objects.first()
        if settings and settings.auto_approve_ads:
            validated_data["status"] = "approved"
        else:
            validated_data["status"] = "pending"

        # Create the ad
        ad = Ad.objects.create(**validated_data)

        # Create images
        for i, image_data in enumerate(images_data):
            AdImage.objects.create(ad=ad, sort_order=i, **image_data)

        return ad


class AdUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing ads."""

    class Meta:
        model = Ad
        fields = [
            "title",
            "description",
            "price",
            "price_type",
            "condition",
            "contact_phone",
            "contact_email",
            "hide_phone",
            "category",
            "city",
            "keywords",
        ]

    def validate(self, data):
        """Validate price based on price_type."""
        price_type = data.get("price_type", self.instance.price_type)
        price = data.get("price")

        if price is None and "price" not in data:
            price = self.instance.price

        # For contact/free/swap: clear price
        if price_type in ["contact", "free", "swap"]:
            if price and price > 0:
                raise serializers.ValidationError(
                    {"price": f"Price must be empty when price type is '{price_type}'."}
                )
            data["price"] = None

        # For fixed/negotiable: require price
        elif price_type in ["fixed", "negotiable"]:
            if not price or price <= 0:
                raise serializers.ValidationError(
                    {"price": f"Price is required when price type is '{price_type}'."}
                )

        return data

    def validate_category(self, value):
        """Ensure category is active."""
        if not value.is_active:
            raise serializers.ValidationError("Selected category is not available.")
        return value

    def validate_city(self, value):
        """Ensure city is active."""
        if not value.is_active:
            raise serializers.ValidationError("Selected city is not available.")
        return value

    def update(self, instance, validated_data):
        """Update ad and set state from city."""
        if "city" in validated_data:
            validated_data["state"] = validated_data["city"].state

        return super().update(instance, validated_data)


class UserAdSerializer(serializers.ModelSerializer):
    """Serializer for user's own ads with full details."""

    category = CategorySimpleSerializer(read_only=True)
    city = CitySimpleSerializer(read_only=True)
    state = StateSimpleSerializer(read_only=True)
    primary_image = AdImageSerializer(read_only=True)
    images_count = serializers.SerializerMethodField()
    display_price = serializers.CharField(read_only=True)
    time_since_posted = serializers.CharField(read_only=True)
    is_featured_active = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "display_price",
            "price_type",
            "condition",
            "category",
            "city",
            "state",
            "status",
            "plan",
            "view_count",
            "unique_view_count",
            "contact_count",
            "favorite_count",
            "primary_image",
            "images_count",
            "time_since_posted",
            "is_featured_active",
            "days_until_expiry",
            "created_at",
            "updated_at",
            "expires_at",
            "rejection_reason",
        ]

    def get_images_count(self, obj):
        """Get count of images for this ad."""
        return obj.images.count()

    def get_days_until_expiry(self, obj):
        """Get days until ad expires."""
        if obj.expires_at:
            days = (obj.expires_at - timezone.now()).days
            return max(0, days)
        return 0


class AdAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for ad analytics data."""

    analytics_data = serializers.SerializerMethodField()

    class Meta:
        model = Ad
        fields = [
            "id",
            "title",
            "view_count",
            "unique_view_count",
            "contact_count",
            "favorite_count",
            "analytics_data",
        ]

    def get_analytics_data(self, obj):
        """Get detailed analytics data."""
        days = self.context.get("days", 30)
        return obj.get_analytics_data(days=days)


class AdFavoriteSerializer(serializers.ModelSerializer):
    """Serializer for ad favorites."""

    ad = AdListSerializer(read_only=True)

    class Meta:
        model = AdFavorite
        fields = ["id", "ad", "created_at"]
        read_only_fields = ["id", "created_at"]


class AdReportSerializer(serializers.ModelSerializer):
    """Serializer for reporting ads."""

    ad_title = serializers.CharField(source="ad.title", read_only=True)
    ad_id = serializers.IntegerField(source="ad.id", read_only=True)
    ad_slug = serializers.CharField(source="ad.slug", read_only=True)
    ad_image = serializers.SerializerMethodField()

    class Meta:
        model = AdReport
        fields = [
            "id",
            "ad",
            "ad_id",
            "ad_title",
            "ad_slug",
            "ad_image",
            "reason",
            "description",
            "created_at",
            "is_reviewed",
            "admin_notes",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "is_reviewed",
            "admin_notes",
            "ad_id",
            "ad_title",
            "ad_slug",
            "ad_image",
        ]

    def get_ad_image(self, obj):
        """Get first image of the ad."""
        if obj.ad:
            first_image = obj.ad.images.first()
            if first_image and first_image.image:
                from django.conf import settings

                image_path = str(first_image.image)
                if not image_path.startswith("http"):
                    return settings.MEDIA_URL + image_path
                return image_path
        return None

    def validate(self, data):
        """Ensure user hasn't already reported this ad."""
        request = self.context.get("request")
        if (
            request
            and AdReport.objects.filter(
                ad=data["ad"], reported_by=request.user
            ).exists()
        ):
            raise serializers.ValidationError("You have already reported this ad.")
        return data

    def create(self, validated_data):
        """Create report with current user."""
        validated_data["reported_by"] = self.context["request"].user
        return super().create(validated_data)


class AdPromoteSerializer(serializers.Serializer):
    """Serializer for promoting ads to featured."""

    payment_method = serializers.CharField(max_length=50)
    payment_id = serializers.CharField(max_length=100, required=False)

    def validate_payment_method(self, value):
        """Validate payment method."""
        allowed_methods = ["stripe", "paypal", "credit_card"]
        if value not in allowed_methods:
            raise serializers.ValidationError(
                f"Invalid payment method. Allowed: {', '.join(allowed_methods)}"
            )
        return value


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics."""

    total_ads = serializers.IntegerField()
    active_ads = serializers.IntegerField()
    pending_ads = serializers.IntegerField()
    featured_ads = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_contacts = serializers.IntegerField()
    total_favorites = serializers.IntegerField()
    this_month_ads = serializers.IntegerField()
    revenue_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)


class CategoryStatsSerializer(serializers.Serializer):
    """Serializer for category statistics."""

    category_name = serializers.CharField()
    category_id = serializers.IntegerField()
    ads_count = serializers.IntegerField()
    percentage = serializers.FloatField()


class LocationStatsSerializer(serializers.Serializer):
    """Serializer for location statistics."""

    city_name = serializers.CharField()
    state_name = serializers.CharField()
    ads_count = serializers.IntegerField()
    percentage = serializers.FloatField()


class RevenueStatsSerializer(serializers.Serializer):
    """Serializer for revenue statistics."""

    month = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    featured_ads_count = serializers.IntegerField()
    average_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class PopularAdsSerializer(serializers.Serializer):
    """Serializer for popular ads analytics."""

    ad_id = serializers.IntegerField()
    title = serializers.CharField()
    views = serializers.IntegerField()
    contacts = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    category = serializers.CharField()


class UserActivitySerializer(serializers.Serializer):
    """Serializer for user activity analytics."""

    date = serializers.DateField()
    new_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    ads_posted = serializers.IntegerField()
    total_views = serializers.IntegerField()
