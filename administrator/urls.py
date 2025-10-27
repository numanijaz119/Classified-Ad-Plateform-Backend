# administrator/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .auth_views import (
    AdminLoginView,
    AdminLogoutView,
    AdminProfileView,
    admin_verify_token,
    admin_change_password,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'ads', views.AdminAdViewSet, basename='admin-ads')
router.register(r'users', views.AdminUserViewSet, basename='admin-users')
router.register(r'reports', views.AdminReportViewSet, basename='admin-reports')
router.register(r'banners', views.AdminBannerViewSet, basename='admin-banners')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Admin Authentication URLs
    path('auth/login/', AdminLoginView.as_view(), name='admin-login'),
    path('auth/logout/', AdminLogoutView.as_view(), name='admin-logout'),
    path('auth/profile/', AdminProfileView.as_view(), name='admin-profile'),
    path('auth/verify-token/', admin_verify_token, name='admin-verify-token'),
    path('auth/change-password/', admin_change_password, name='admin-change-password'),
    
    
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    path('dashboard/stats/', views.AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    path('analytics/overview/', views.admin_analytics_overview, name='admin-analytics-overview'),
    path('analytics/users/', views.admin_analytics_users, name='admin-analytics-users'),
    path('analytics/revenue/', views.admin_analytics_revenue, name='admin-analytics-revenue'),
    path('analytics/geographic/', views.admin_analytics_geographic, name='admin-analytics-geographic'),
    path('analytics/categories/', views.admin_analytics_categories, name='admin-analytics-categories'),
    
    # ========================================================================
    # CONTENT MANAGEMENT
    # ========================================================================
    path('states/', views.AdminStateListView.as_view(), name='admin-states-list'),
    path('categories/stats/', views.AdminCategoryStatsView.as_view(), name='admin-categories-stats'),
    path('categories/create/', views.admin_category_create, name='admin-category-create'),
    path('categories/<int:category_id>/', views.admin_category_detail, name='admin-category-detail'),
    path('cities/', views.admin_city_list, name='admin-city-list'),
    path('cities/create/', views.admin_city_create, name='admin-city-create'),
    path('cities/<int:city_id>/', views.admin_city_detail, name='admin-city-detail'),
    
    # ========================================================================
    # SYSTEM SETTINGS
    # ========================================================================
    path('settings/', views.admin_settings, name='admin-settings'),
    path('settings/update/', views.admin_settings_update, name='admin-settings-update'),
    
    # ========================================================================
    # DATA EXPORT
    # ========================================================================
    path('export/ads/', views.admin_export_ads, name='admin-export-ads'),
    path('export/users/', views.admin_export_users, name='admin-export-users'),
    path('export/reports/', views.admin_export_reports, name='admin-export-reports'),
    path('export/analytics/', views.admin_export_analytics, name='admin-export-analytics'),
    
    # ========================================================================
    # SYSTEM UTILITIES
    # ========================================================================
    path('cache/clear/', views.admin_clear_cache, name='admin-clear-cache'),
    path('maintenance/', views.admin_maintenance_mode, name='admin-maintenance-mode'),
]

"""
ADMIN API ENDPOINTS (Class-Based Views):

ADS MANAGEMENT (ViewSet):
GET    /api/administrator/ads/                    - List ads with filters
GET    /api/administrator/ads/{id}/               - Get ad detail
POST   /api/administrator/ads/{id}/action/        - Approve/reject/delete/feature/unfeature ad
POST   /api/administrator/ads/bulk_action/        - Bulk actions on ads

Filters: ?status=pending&state=IL&category=1&plan=featured
Search: ?search=keyword
Sort: ?ordering=-created_at

USER MANAGEMENT (ViewSet):
GET    /api/administrator/users/                  - List users with filters
GET    /api/administrator/users/{id}/             - Get user detail
POST   /api/administrator/users/{id}/action/      - Ban/suspend/activate user
GET    /api/administrator/users/{id}/activity/    - Get user activity logs
POST   /api/administrator/users/bulk_action/      - Bulk actions on users

Filters: ?status=active&email_verified=true&has_ads=true
Search: ?search=email
Sort: ?ordering=-created_at

REPORTS MANAGEMENT (ViewSet):
GET    /api/administrator/reports/                - List reports with filters
GET    /api/administrator/reports/{id}/           - Get report detail
POST   /api/administrator/reports/{id}/action/    - Approve/dismiss report
POST   /api/administrator/reports/bulk_action/    - Bulk actions on reports

Filters: ?status=pending&reason=spam
Sort: ?ordering=-created_at

BANNER MANAGEMENT (ViewSet):
GET    /api/administrator/banners/                - List banners
POST   /api/administrator/banners/                - Create banner
GET    /api/administrator/banners/{id}/           - Get banner detail
PUT    /api/administrator/banners/{id}/           - Update banner
DELETE /api/administrator/banners/{id}/           - Delete banner
POST   /api/administrator/banners/{id}/toggle/    - Toggle banner active status
GET    /api/administrator/banners/{id}/analytics/ - Get banner analytics

Filters: ?is_active=true&placement=homepage&state=IL
Sort: ?ordering=-created_at

All endpoints use proper pagination from core.pagination:
- LargeResultsSetPagination (50 per page) for ads, users, reports
- StandardResultsSetPagination (20 per page) for banners

All endpoints support:
- DjangoFilterBackend for filtering
- SearchFilter for text search
- OrderingFilter for sorting
"""