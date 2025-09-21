# ads/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdViewSet,
    AdImageViewSet,
    AdFavoriteViewSet,
    AdReportViewSet,
    DashboardAnalyticsView,
    AdminAnalyticsView,
    AdminAdManagementView,
    admin_ad_action,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'ads', AdViewSet, basename='ads')
router.register(r'images', AdImageViewSet, basename='ad-images')
router.register(r'favorites', AdFavoriteViewSet, basename='ad-favorites')
router.register(r'reports', AdReportViewSet, basename='ad-reports')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Analytics endpoints
    path('dashboard/analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
    path('admin/analytics/', AdminAnalyticsView.as_view(), name='admin-analytics'),
    path('admin/ads/', AdminAdManagementView.as_view(), name='admin-ads'),
    path('admin/ads/<int:ad_id>/action/', admin_ad_action, name='admin-ad-action'),
]

"""
SIMPLIFIED API ENDPOINTS:

USER ENDPOINTS:
GET /api/ads/ads/ - List ads
  Filters: ?category=1&city=2&price_min=100&price_max=500
  Sort: ?sort_by=newest|oldest|alphabetical|price_low|price_high

GET /api/ads/ads/search/ - Search ads
  Search: ?search=keyword
  Filters: ?category=1&city=2&price_min=100&price_max=500
  Sort: ?sort_by=newest|oldest|alphabetical|price_low|price_high|relevance

GET /api/ads/ads/featured/ - Featured ads only
  Sort: ?sort_by=newest|oldest|alphabetical

GET /api/ads/ads/{slug}/ - Ad details

POST /api/ads/ads/ - Create ad (auth required)
PUT/PATCH /api/ads/ads/{slug}/ - Update ad (owner only)
DELETE /api/ads/ads/{slug}/ - Delete ad (owner only)

GET /api/ads/ads/my_ads/ - User's ads (auth required)
  Filters: ?category=1&city=2&status=approved&plan=featured
  Sort: ?sort_by=newest|oldest|alphabetical|status

GET /api/ads/ads/{slug}/analytics/ - Ad analytics (owner only)
POST /api/ads/ads/{slug}/contact_view/ - Track contact view
POST /api/ads/ads/{slug}/promote/ - Promote to featured

IMAGE MANAGEMENT:
GET/POST/PUT/DELETE /api/ads/images/ - Manage ad images

FAVORITES:
GET/POST /api/ads/favorites/ - Manage favorites
DELETE /api/ads/favorites/remove/ - Remove favorite

REPORTS:
GET/POST /api/ads/reports/ - Report ads

ANALYTICS:
GET /api/ads/dashboard/analytics/ - User dashboard stats

ADMIN ENDPOINTS (Advanced Filtering):
GET /api/ads/admin/ads/ - All ads with advanced filters
  Advanced filters: status, plan, user, has_images, has_phone, 
  is_featured, has_reports, posted_since, search, etc.
  
GET /api/ads/admin/analytics/ - Admin analytics
POST /api/ads/admin/ads/{id}/action/ - Admin actions
"""