# administrator/views.py
from rest_framework import generics, status, viewsets, filters, serializers
from rest_framework.decorators import api_view, permission_classes, action as drf_action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, Avg, F
from django.db.models.functions import TruncDate, TruncMonth, TruncDay
from django.utils import timezone
from datetime import timedelta, datetime
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from core.simple_mixins import AdminViewMixin
from core.search_mixins import SearchFilterMixin
from core.pagination import LargeResultsSetPagination, StandardResultsSetPagination

from ads.models import Ad, AdView, AdContact, AdFavorite, AdReport
from accounts.models import User
from content.models import Category, State, City
from .models import Banner, AdminSettings
from .serializers import (
    AdminAdSerializer,
    AdminAdActionSerializer,
    AdminUserSerializer,
    AdminStateSerializer,
    AdminCategorySerializer,
    AdminReportSerializer,
    AdminBannerSerializer,
)
from .filters import AdminUserFilter, AdminReportFilter, AdminAdFilter

# ============================================================================
# DASHBOARD STATISTICS
# ============================================================================


class AdminDashboardStatsView(generics.GenericAPIView):
    """Get dashboard statistics for admin - can filter by state."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        state_filter = request.query_params.get("state", "all")

        # Base queryset
        ads_qs = Ad.objects.exclude(status="deleted")
        users_qs = User.objects.all()

        # Apply state filter
        if state_filter != "all":
            ads_qs = ads_qs.filter(state__code=state_filter)

        # Calculate statistics
        total_ads = ads_qs.count()
        active_ads = ads_qs.filter(status="approved").count()
        pending_ads = ads_qs.filter(status="pending").count()
        rejected_ads = ads_qs.filter(status="rejected").count()
        featured_ads = ads_qs.filter(plan="featured").count()

        total_users = users_qs.count()
        active_users = users_qs.filter(is_active=True, is_suspended=False).count()
        suspended_users = users_qs.filter(is_suspended=True).count()
        banned_users = users_qs.filter(is_active=False).count()

        total_views = AdView.objects.filter(ad__in=ads_qs).count()
        total_contacts = AdContact.objects.filter(ad__in=ads_qs).count()
        total_favorites = AdFavorite.objects.filter(ad__in=ads_qs).count()

        pending_reports = AdReport.objects.filter(
            is_reviewed=False, ad__in=ads_qs
        ).count()

        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        new_ads_this_week = ads_qs.filter(created_at__gte=week_ago).count()
        new_users_this_week = users_qs.filter(created_at__gte=week_ago).count()

        return Response(
            {
                "ads": {
                    "total": total_ads,
                    "active": active_ads,
                    "pending": pending_ads,
                    "rejected": rejected_ads,
                    "featured": featured_ads,
                    "new_this_week": new_ads_this_week,
                },
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "suspended": suspended_users,
                    "banned": banned_users,
                    "new_this_week": new_users_this_week,
                },
                "engagement": {
                    "total_views": total_views,
                    "total_contacts": total_contacts,
                    "total_favorites": total_favorites,
                },
                "moderation": {
                    "pending_reports": pending_reports,
                },
            }
        )


# ============================================================================
# ADS MANAGEMENT
# ============================================================================


class AdminAdViewSet(AdminViewMixin, SearchFilterMixin, viewsets.ReadOnlyModelViewSet):
    """Admin ViewSet for managing ads with filtering and search."""

    serializer_class = AdminAdSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LargeResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AdminAdFilter

    search_fields = [
        "title",
        "description",
        "keywords",
        "category__name",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]

    ordering_fields = ["created_at", "title", "price", "view_count", "status"]
    ordering = ["-created_at"]

    state_field_path = "state__code"

    def get_queryset(self):
        """Get ads queryset with admin filtering."""
        return Ad.objects.select_related(
            "category", "city", "state", "user"
        ).prefetch_related("images")

    @drf_action(detail=True, methods=["post"])
    def action(self, request, pk=None):
        """Approve, reject, delete, feature, or unfeature ads."""
        ad = self.get_object()
        action = request.data.get("action")
        reason = request.data.get("reason", "")
        admin_notes = request.data.get("admin_notes", "")

        if action == "approve":
            ad.status = "approved"
            ad.approved_by = request.user
            ad.approved_at = timezone.now()
            message = "Ad approved successfully"

        elif action == "reject":
            ad.status = "rejected"
            ad.rejection_reason = reason or "Rejected by admin"
            ad.admin_notes = admin_notes
            message = "Ad rejected successfully"

        elif action == "delete":
            ad.status = "deleted"
            ad.admin_notes = admin_notes
            message = "Ad deleted successfully"

        elif action == "feature":
            ad.plan = "featured"
            ad.featured_expires_at = timezone.now() + timedelta(days=30)
            message = "Ad featured successfully"

        elif action == "unfeature":
            ad.plan = "free"
            ad.featured_expires_at = None
            message = "Ad unfeatured successfully"

        else:
            return Response({"error": "Invalid action"}, status=400)

        ad.save()

        return Response({"message": message, "ad": AdminAdSerializer(ad).data})

    @drf_action(detail=False, methods=["post"])
    def bulk_action(self, request):
        """Perform bulk actions on multiple ads."""
        ad_ids = request.data.get("ad_ids", [])
        action = request.data.get("action")
        reason = request.data.get("reason", "")
        admin_notes = request.data.get("admin_notes", "")

        if not ad_ids or action not in [
            "approve",
            "reject",
            "delete",
            "feature",
            "unfeature",
        ]:
            return Response({"error": "Invalid data provided"}, status=400)

        ads = Ad.objects.filter(id__in=ad_ids)

        if not ads.exists():
            return Response({"error": "No ads found with provided IDs"}, status=404)

        updated_count = 0

        for ad in ads:
            if action == "approve":
                ad.status = "approved"
                ad.approved_by = request.user
                ad.approved_at = timezone.now()
            elif action == "reject":
                ad.status = "rejected"
                ad.rejection_reason = reason or "Rejected by admin"
                ad.admin_notes = admin_notes
            elif action == "delete":
                ad.status = "deleted"
                ad.admin_notes = admin_notes
            elif action == "feature":
                ad.plan = "featured"
                ad.featured_expires_at = timezone.now() + timedelta(days=30)
            elif action == "unfeature":
                ad.plan = "free"
                ad.featured_expires_at = None

            ad.save()
            updated_count += 1

        return Response(
            {
                "message": f"{updated_count} ads updated successfully",
                "updated_count": updated_count,
            }
        )


# ============================================================================
# USER MANAGEMENT
# ============================================================================


class AdminUserViewSet(
    AdminViewMixin, SearchFilterMixin, viewsets.ReadOnlyModelViewSet
):
    """Admin ViewSet for managing users with filtering and search."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LargeResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = AdminUserFilter
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_class = AdminUserFilter  # Local filter

    search_fields = [
        "email",
        "first_name",
        "last_name",
        "phone",
    ]

    ordering_fields = ["created_at", "email", "first_name", "last_name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return User.objects.filter(
            is_superuser=False,
            is_staff=False
        ).select_related().prefetch_related("ads")

    @drf_action(detail=True, methods=["post"])
    def action(self, request, pk=None):
        """Ban, suspend, or activate users."""
        user = self.get_object()
        action = request.data.get("action")
        reason = request.data.get("reason", "")

        if action == "ban":
            user.is_active = False
            user.is_suspended = True
            user.suspension_reason = reason
            message = "User banned successfully"

        elif action == "suspend":
            user.is_suspended = True
            user.suspension_reason = reason
            message = "User suspended successfully"

        elif action == "activate":
            user.is_active = True
            user.is_suspended = False
            user.suspension_reason = ""
            message = "User activated successfully"

        else:
            return Response({"error": "Invalid action"}, status=400)

        user.save()

        return Response(
            {
                "message": message,
                "user_status": {
                    "is_active": user.is_active,
                    "is_suspended": user.is_suspended,
                    "suspension_reason": user.suspension_reason,
                },
            }
        )

    @drf_action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        """Get user activity logs."""
        user = self.get_object()

        # Get user's ads activity
        ads_data = {
            "total_ads": user.ads.exclude(status="deleted").count(),
            "active_ads": user.ads.filter(status="approved").count(),
            "pending_ads": user.ads.filter(status="pending").count(),
            "rejected_ads": user.ads.filter(status="rejected").count(),
            "featured_ads": user.ads.filter(plan="featured").count(),
        }

        # Get recent ads
        recent_ads = user.ads.exclude(status="deleted").order_by("-created_at")[:10]
        recent_ads_data = AdminAdSerializer(recent_ads, many=True).data

        return Response(
            {
                "user": AdminUserSerializer(user).data,
                "ads_statistics": ads_data,
                "recent_ads": recent_ads_data,
            }
        )

    @drf_action(detail=False, methods=["post"])
    def bulk_action(self, request):
        """Perform bulk actions on multiple users."""
        user_ids = request.data.get("user_ids", [])
        action = request.data.get("action")
        reason = request.data.get("reason", "")

        if not user_ids or action not in ["ban", "suspend", "activate"]:
            return Response({"error": "Invalid data provided"}, status=400)

        users = User.objects.filter(id__in=user_ids)

        if not users.exists():
            return Response({"error": "No users found with provided IDs"}, status=404)

        updated_count = 0

        for user in users:
            if action == "ban":
                user.is_active = False
                user.is_suspended = True
                user.suspension_reason = reason
            elif action == "suspend":
                user.is_suspended = True
                user.suspension_reason = reason
            elif action == "activate":
                user.is_active = True
                user.is_suspended = False
                user.suspension_reason = ""

            user.save()
            updated_count += 1

        return Response(
            {
                "message": f"Successfully {action}ed {updated_count} users",
                "updated_count": updated_count,
            }
        )


# ============================================================================
# REPORTS MANAGEMENT
# ============================================================================


class AdminReportViewSet(AdminViewMixin, viewsets.ReadOnlyModelViewSet):
    """Admin ViewSet for managing ad reports."""

    serializer_class = AdminReportSerializer
    permission_classes = [IsAdminUser]
    pagination_class = LargeResultsSetPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]

    filterset_class = AdminReportFilter  # Local filter

    ordering_fields = ["created_at", "reason"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Get reports queryset with filtering."""
        return AdReport.objects.select_related("ad", "reported_by", "reviewed_by")

    @drf_action(detail=True, methods=["post"])
    def action(self, request, pk=None):
        """Handle reports (approve/dismiss)."""
        report = self.get_object()
        action = request.data.get("action")
        admin_notes = request.data.get("admin_notes", "")

        if action == "approve":
            # Mark report as reviewed and take action on the ad
            report.is_reviewed = True
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.admin_notes = admin_notes

            # Take action on the reported ad based on the report reason
            ad = report.ad
            if report.reason in ["spam", "fraud"]:
                ad.status = "rejected"
                ad.rejection_reason = f"Reported as {report.get_reason_display()}"
            elif report.reason == "inappropriate":
                ad.status = "pending"  # Send back for review

            ad.save()
            message = "Report approved and action taken on ad"

        elif action == "dismiss":
            report.is_reviewed = True
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.admin_notes = admin_notes or "Report dismissed - no action needed"
            message = "Report dismissed"

        else:
            return Response({"error": "Invalid action"}, status=400)

        report.save()

        return Response({"message": message, "report_status": "reviewed"})

    @drf_action(detail=False, methods=["post"])
    def bulk_action(self, request):
        """Perform bulk actions on multiple reports."""
        report_ids = request.data.get("report_ids", [])
        action = request.data.get("action")
        admin_notes = request.data.get("admin_notes", "")

        if not report_ids or action not in ["approve", "dismiss"]:
            return Response({"error": "Invalid data provided"}, status=400)

        reports = AdReport.objects.filter(id__in=report_ids)

        if not reports.exists():
            return Response({"error": "No reports found with provided IDs"}, status=404)

        updated_count = 0

        for report in reports:
            report.is_reviewed = True
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.admin_notes = admin_notes

            if action == "approve":
                ad = report.ad
                if report.reason in ["spam", "fraud"]:
                    ad.status = "rejected"
                    ad.rejection_reason = f"Reported as {report.get_reason_display()}"
                elif report.reason == "inappropriate":
                    ad.status = "pending"
                ad.save()

            report.save()
            updated_count += 1

        return Response(
            {
                "message": f"{updated_count} reports processed successfully",
                "updated_count": updated_count,
            }
        )


# ============================================================================
# ANALYTICS
# ============================================================================


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_analytics_overview(request):
    """Get comprehensive analytics overview."""
    state_filter = request.query_params.get("state", "all")
    days = int(request.query_params.get("days", 30))

    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Base queryset
    ads_qs = Ad.objects.exclude(status="deleted")
    if state_filter != "all":
        ads_qs = ads_qs.filter(state__code=state_filter)

    # Daily ad creation trend
    daily_ads = (
        ads_qs.filter(created_at__gte=start_date)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # Status distribution
    status_dist = ads_qs.values("status").annotate(count=Count("id"))

    # Category distribution
    category_dist = (
        ads_qs.values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # View and contact trends
    daily_views = (
        AdView.objects.filter(viewed_at__gte=start_date, ad__in=ads_qs)
        .annotate(date=TruncDate("viewed_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    daily_contacts = (
        AdContact.objects.filter(contacted_at__gte=start_date, ad__in=ads_qs)
        .annotate(date=TruncDate("contacted_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    return Response(
        {
            "daily_ads": list(daily_ads),
            "status_distribution": list(status_dist),
            "top_categories": list(category_dist),
            "daily_views": list(daily_views),
            "daily_contacts": list(daily_contacts),
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_analytics_users(request):
    """Get user growth analytics."""
    days = int(request.query_params.get("days", 30))

    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Daily user registrations
    daily_users = (
        User.objects.filter(created_at__gte=start_date)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # User status distribution
    status_dist = {
        "active": User.objects.filter(is_active=True, is_suspended=False).count(),
        "suspended": User.objects.filter(is_suspended=True).count(),
        "banned": User.objects.filter(is_active=False).count(),
    }

    # Top users by ad count
    top_users = User.objects.annotate(
        ad_count=Count("ads", filter=Q(ads__status="approved"))
    ).order_by("-ad_count")[:10]

    top_users_data = [
        {
            "id": user.id,
            "email": user.email,
            "name": user.get_full_name(),
            "ad_count": user.ad_count,
        }
        for user in top_users
    ]

    return Response(
        {
            "daily_registrations": list(daily_users),
            "status_distribution": status_dist,
            "top_users": top_users_data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_analytics_revenue(request):
    """Get revenue analytics."""
    days = int(request.query_params.get("days", 30))

    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Featured ads revenue (assuming $9.99 per featured ad)
    featured_ads = Ad.objects.filter(
        plan="featured", featured_expires_at__gte=start_date
    )

    daily_revenue = (
        featured_ads.annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"), revenue=Count("id") * 9.99)
        .order_by("date")
    )

    total_revenue = featured_ads.count() * 9.99

    return Response(
        {
            "daily_revenue": list(daily_revenue),
            "total_revenue": total_revenue,
            "featured_ads_count": featured_ads.count(),
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_analytics_geographic(request):
    """Get geographic distribution analytics."""

    # State-wise distribution
    state_dist = (
        Ad.objects.exclude(status="deleted")
        .values("state__code", "state__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # City-wise distribution (top 20)
    city_dist = (
        Ad.objects.exclude(status="deleted")
        .values("city__name", "state__code")
        .annotate(count=Count("id"))
        .order_by("-count")[:20]
    )

    return Response(
        {
            "state_distribution": list(state_dist),
            "top_cities": list(city_dist),
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_analytics_categories(request):
    """Get category performance analytics."""

    # Category performance
    categories = Category.objects.annotate(
        total_ads=Count("ads", filter=Q(ads__status="approved")),
        total_views=Sum("ads__view_count"),
        avg_price=Avg("ads__price"),
    ).order_by("-total_ads")

    categories_data = [
        {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "total_ads": cat.total_ads or 0,
            "total_views": cat.total_views or 0,
            "avg_price": float(cat.avg_price) if cat.avg_price else 0,
        }
        for cat in categories
    ]

    return Response({"categories": categories_data})


# BANNER MANAGEMENT
# ============================================================================


class AdminBannerViewSet(AdminViewMixin, viewsets.ModelViewSet):
    """Admin ViewSet for managing banners."""

    serializer_class = AdminBannerSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["is_active", "position", "banner_type"]
    ordering_fields = ["created_at", "title", "impressions", "clicks"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Get banners queryset."""
        return Banner.objects.all()

    def perform_create(self, serializer):
        """Set created_by when creating banner."""
        serializer.save(created_by=self.request.user)

    @drf_action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """Toggle banner active status."""
        banner = self.get_object()
        banner.is_active = not banner.is_active
        banner.save()

        action = "activated" if banner.is_active else "deactivated"

        return Response(
            {"message": f"Banner {action} successfully", "is_active": banner.is_active}
        )

    @drf_action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        """Get detailed analytics for a specific banner."""
        banner = self.get_object()

        # Daily performance for last 30 days
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        from .models import BannerImpression, BannerClick

        daily_impressions = (
            BannerImpression.objects.filter(banner=banner, viewed_at__gte=start_date)
            .annotate(day=TruncDate("viewed_at"))
            .values("day")
            .annotate(impressions=Count("id"))
            .order_by("day")
        )

        daily_clicks = (
            BannerClick.objects.filter(banner=banner, clicked_at__gte=start_date)
            .annotate(day=TruncDate("clicked_at"))
            .values("day")
            .annotate(clicks=Count("id"))
            .order_by("day")
        )

        return Response(
            {
                "banner_info": {
                    "id": banner.id,
                    "title": banner.title,
                    "total_impressions": banner.impressions,
                    "total_clicks": banner.clicks,
                    "ctr": banner.ctr,
                },
                "daily_impressions": list(daily_impressions),
                "daily_clicks": list(daily_clicks),
            }
        )


# ============================================================================
# CONTENT MANAGEMENT
# ============================================================================

@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_city_list(request):
    """List all cities (both active and inactive) for admin management."""
    from content.serializers import CitySerializer
    from content.models import City
    
    # Get all cities (both active and inactive)
    cities = City.objects.select_related('state').all()
    
    # Apply filters if provided
    state_code = request.GET.get('state')
    if state_code and state_code != 'all':
        cities = cities.filter(state__code__iexact=state_code)
    
    is_active = request.GET.get('is_active')
    if is_active is not None:
        cities = cities.filter(is_active=is_active.lower() == 'true')
    
    is_major = request.GET.get('is_major')
    if is_major is not None:
        cities = cities.filter(is_major=is_major.lower() == 'true')
    
    # Order by major cities first, then by name
    cities = cities.order_by('-is_major', 'name')
    
    serializer = CitySerializer(cities, many=True, context={'request': request})
    return Response(serializer.data)


class AdminStateListView(generics.ListCreateAPIView):
    """List and create states for admin."""

    serializer_class = AdminStateSerializer
    permission_classes = [IsAdminUser]
    queryset = State.objects.all().order_by("name")

    def list(self, request, *args, **kwargs):
        """Custom list response with stats."""
        queryset = self.get_queryset()

        states_data = []
        for state in queryset:
            # Get stats for this state
            ads_count = Ad.objects.filter(state=state).exclude(status="deleted").count()
            active_ads = Ad.objects.filter(state=state, status="approved").count()
            users_count = (
                Ad.objects.filter(state=state).values("user").distinct().count()
            )

            # Build absolute URLs for images
            logo_url = None
            if state.logo:
                logo_url = request.build_absolute_uri(state.logo.url)
            
            favicon_url = None
            if state.favicon:
                favicon_url = request.build_absolute_uri(state.favicon.url)

            states_data.append(
                {
                    "id": state.id,
                    "code": state.code,
                    "name": state.name,
                    "domain": state.domain,
                    "logo": logo_url,
                    "favicon": favicon_url,
                    "meta_title": state.meta_title,
                    "meta_description": state.meta_description,
                    "is_active": state.is_active,
                    "total_ads": ads_count,
                    "active_ads": active_ads,
                    "users_count": users_count,
                    "created_at": state.created_at.isoformat(),
                    "updated_at": state.updated_at.isoformat(),
                }
            )

        return Response({"results": states_data})

    def create(self, request, *args, **kwargs):
        """Create a new state with better error handling."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                {
                    "message": "State created successfully",
                    "state": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except serializers.ValidationError as e:
            # Handle validation errors with friendly messages
            error_messages = []
            if isinstance(e.detail, dict):
                for field, errors in e.detail.items():
                    if isinstance(errors, list):
                        error_messages.append(f"{field}: {errors[0]}")
                    else:
                        error_messages.append(f"{field}: {errors}")
            else:
                error_messages.append(str(e.detail))
            
            return Response(
                {"error": " | ".join(error_messages)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating state: {str(e)}")
            return Response(
                {"error": f"Failed to create state: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminStateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a state."""

    serializer_class = AdminStateSerializer
    permission_classes = [IsAdminUser]
    queryset = State.objects.all()
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        """Update state with better error handling and optional image updates."""
        try:
            partial = True  # Always use partial update
            instance = self.get_object()
            
            # If no new logo is provided, keep the existing one
            data = request.data.copy()
            if 'logo' not in request.FILES:
                data.pop('logo', None)
            if 'favicon' not in request.FILES:
                data.pop('favicon', None)
            
            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            return Response(
                {
                    "message": "State updated successfully",
                    "state": serializer.data
                }
            )
        except serializers.ValidationError as e:
            error_messages = []
            if isinstance(e.detail, dict):
                for field, errors in e.detail.items():
                    if isinstance(errors, list):
                        error_messages.append(f"{field}: {errors[0]}")
                    else:
                        error_messages.append(f"{field}: {errors}")
            else:
                error_messages.append(str(e.detail))
            
            return Response(
                {"error": " | ".join(error_messages)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating state: {str(e)}")
            return Response(
                {"error": f"Failed to update state: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Delete state with better error handling."""
        try:
            instance = self.get_object()
            state_name = instance.name
            self.perform_destroy(instance)
            return Response(
                {"message": f"State '{state_name}' deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error deleting state: {str(e)}")
            return Response(
                {"error": f"Failed to delete state: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminCategoryStatsView(generics.ListAPIView):
    """Get category statistics."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        state_filter = request.query_params.get("state", "all")

        # Base queryset
        categories = Category.objects.filter(is_active=True)

        # Prepare stats
        categories_data = []
        for category in categories:
            ads_qs = category.ads.exclude(status="deleted")

            if state_filter != "all":
                ads_qs = ads_qs.filter(state__code=state_filter)

            categories_data.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "slug": category.slug,
                    "icon": category.icon,
                    "description": category.description,
                    "sort_order": category.sort_order,
                    "is_active": category.is_active,
                    "total_ads": ads_qs.count(),
                    "active_ads": ads_qs.filter(status="approved").count(),
                    "pending_ads": ads_qs.filter(status="pending").count(),
                }
            )

        return Response({"categories": categories_data})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_category_create(request):
    """Create a new category."""
    serializer = AdminCategorySerializer(data=request.data)
    if serializer.is_valid():
        category = serializer.save()
        return Response(AdminCategorySerializer(category).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAdminUser])
def admin_category_detail(request, category_id):
    """Get, update, or delete a category."""
    category = get_object_or_404(Category, id=category_id)

    if request.method == "GET":
        return Response(AdminCategorySerializer(category).data)

    elif request.method == "PUT":
        serializer = AdminCategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            category = serializer.save()
            return Response(AdminCategorySerializer(category).data)
        return Response(serializer.errors, status=400)

    elif request.method == "DELETE":
        category.is_active = False
        category.save()
        return Response({"message": "Category deactivated successfully"})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_city_create(request):
    """Create a new city."""
    from content.serializers import CitySerializer

    serializer = CitySerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        city = serializer.save()
        return Response(CitySerializer(city, context={'request': request}).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAdminUser])
def admin_city_detail(request, city_id):
    """Get, update, or delete a city."""
    from content.serializers import CitySerializer

    city = get_object_or_404(City, id=city_id)

    if request.method == "GET":
        return Response(CitySerializer(city, context={'request': request}).data)

    elif request.method == "PUT":
        serializer = CitySerializer(city, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            city = serializer.save()
            return Response(CitySerializer(city, context={'request': request}).data)
        return Response(serializer.errors, status=400)

    elif request.method == "DELETE":
        city.is_active = False
        city.save()
        return Response({"message": "City deactivated successfully"})


# ============================================================================
# SYSTEM SETTINGS
# ============================================================================


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_settings(request):
    """Get admin settings."""
    settings, created = AdminSettings.objects.get_or_create(
        pk=1,
        defaults={
            'site_name': 'Classified Ads',
            'contact_email': '',
            'support_phone': '',
            'allow_registration': True,
            'require_email_verification': True,
            'auto_approve_ads': False,
            'featured_ad_price': 9.99,
            'featured_ad_duration_days': 30,
        }
    )

    return Response(
        {
            "site_name": settings.site_name,
            "contact_email": settings.contact_email,
            "support_phone": settings.support_phone,
            "allow_registration": settings.allow_registration,
            "require_email_verification": settings.require_email_verification,
            "auto_approve_ads": settings.auto_approve_ads,
            "featured_ad_price": float(settings.featured_ad_price),
            "featured_ad_duration_days": settings.featured_ad_duration_days,
        }
    )


@api_view(["PUT"])
@permission_classes([IsAdminUser])
def admin_settings_update(request):
    """Update admin settings."""
    settings, created = AdminSettings.objects.get_or_create(
        pk=1,
        defaults={
            'site_name': 'Classified Ads',
            'contact_email': '',
            'support_phone': '',
            'allow_registration': True,
            'require_email_verification': True,
            'auto_approve_ads': False,
            'featured_ad_price': 9.99,
            'featured_ad_duration_days': 30,
        }
    )

    # Update fields
    for field in [
        "site_name",
        "contact_email",
        "support_phone",
        "allow_registration",
        "require_email_verification",
        "auto_approve_ads",
        "featured_ad_price",
        "featured_ad_duration_days",
    ]:
        if field in request.data:
            setattr(settings, field, request.data[field])

    settings.save()

    return Response({
        "message": "Settings updated successfully",
        "site_name": settings.site_name,
        "contact_email": settings.contact_email,
        "support_phone": settings.support_phone,
        "allow_registration": settings.allow_registration,
        "require_email_verification": settings.require_email_verification,
        "auto_approve_ads": settings.auto_approve_ads,
        "featured_ad_price": float(settings.featured_ad_price),
        "featured_ad_duration_days": settings.featured_ad_duration_days,
    })


# ============================================================================
# DATA EXPORT
# ============================================================================


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_export_ads(request):
    """Export ads data to CSV."""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ads_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Title",
            "User",
            "Category",
            "City",
            "State",
            "Price",
            "Status",
            "Plan",
            "Views",
            "Created At",
        ]
    )

    ads = Ad.objects.select_related("user", "category", "city", "state").all()

    for ad in ads:
        writer.writerow(
            [
                ad.id,
                ad.title,
                ad.user.email,
                ad.category.name,
                ad.city.name,
                ad.state.name,
                ad.price,
                ad.status,
                ad.plan,
                ad.view_count,
                ad.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    return response


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_export_users(request):
    """Export users data to CSV."""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ["ID", "Email", "Name", "Phone", "Status", "Total Ads", "Joined Date"]
    )

    users = User.objects.prefetch_related("ads").all()

    for user in users:
        status = "Active"
        if not user.is_active:
            status = "Banned"
        elif user.is_suspended:
            status = "Suspended"

        writer.writerow(
            [
                user.id,
                user.email,
                user.get_full_name(),
                user.phone or "",
                status,
                user.ads.count(),
                user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    return response


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_export_reports(request):
    """Export reports data to CSV."""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="reports_export.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Ad ID",
            "Ad Title",
            "Reported By",
            "Reason",
            "Description",
            "Status",
            "Reviewed By",
            "Created At",
        ]
    )

    reports = AdReport.objects.select_related("ad", "reported_by", "reviewed_by").all()

    for report in reports:
        writer.writerow(
            [
                report.id,
                report.ad.id,
                report.ad.title,
                report.reported_by.email if report.reported_by else "Anonymous",
                report.get_reason_display(),
                report.description,
                "Reviewed" if report.is_reviewed else "Pending",
                report.reviewed_by.email if report.reviewed_by else "",
                report.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )

    return response


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_export_analytics(request):
    """Export analytics data to CSV."""
    import csv
    from django.http import HttpResponse

    days = int(request.GET.get("days", 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="analytics_export.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "New Ads", "New Users", "Views", "Contacts"])

    # Daily aggregation
    dates = []
    current_date = start_date.date()
    while current_date <= end_date.date():
        dates.append(current_date)
        current_date += timedelta(days=1)

    for date in dates:
        new_ads = Ad.objects.filter(created_at__date=date).count()
        new_users = User.objects.filter(created_at__date=date).count()
        views = AdView.objects.filter(viewed_at__date=date).count()
        contacts = AdContact.objects.filter(contacted_at__date=date).count()

        writer.writerow(
            [
                date.strftime("%Y-%m-%d"),
                new_ads,
                new_users,
                views,
                contacts,
            ]
        )

    return response


# ============================================================================
# SYSTEM UTILITIES
# ============================================================================


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_clear_cache(request):
    """Clear application cache."""
    from django.core.cache import cache

    cache.clear()
    return Response({"message": "Cache cleared successfully"})


# Maintenance mode endpoint removed - feature disabled
