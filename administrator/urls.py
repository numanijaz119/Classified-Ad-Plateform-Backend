# administrator/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    path('dashboard/stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
    
    # ========================================================================
    # ADS MANAGEMENT
    # ========================================================================
    path('ads/', views.admin_ads_list, name='admin-ads-list'),
    path('ads/<int:ad_id>/action/', views.admin_ad_action, name='admin-ad-action'),
    path('ads/bulk-action/', views.admin_bulk_ad_action, name='admin-bulk-ad-action'),
    
    # ========================================================================
    # USER MANAGEMENT
    # ========================================================================
    path('users/', views.admin_users_list, name='admin-users-list'),
    path('users/<int:user_id>/action/', views.admin_user_action, name='admin-user-action'),
    path('users/<int:user_id>/activity/', views.admin_user_activity, name='admin-user-activity'),
    path('users/bulk-action/', views.admin_bulk_user_action, name='admin-bulk-user-action'),
    
    # ========================================================================
    # REPORTS MANAGEMENT
    # ========================================================================
    path('reports/', views.admin_reports_list, name='admin-reports-list'),
    path('reports/<int:report_id>/action/', views.admin_report_action, name='admin-report-action'),
    path('reports/bulk-action/', views.admin_bulk_report_action, name='admin-bulk-report-action'),
    
    # ========================================================================
    # ANALYTICS
    # ========================================================================
    path('analytics/overview/', views.admin_analytics_overview, name='admin-analytics-overview'),
    path('analytics/users/', views.admin_analytics_users, name='admin-analytics-users'),
    path('analytics/revenue/', views.admin_analytics_revenue, name='admin-analytics-revenue'),
    path('analytics/geographic/', views.admin_analytics_geographic, name='admin-analytics-geographic'),
    path('analytics/categories/', views.admin_analytics_categories, name='admin-analytics-categories'),
    
    # ========================================================================
    # BANNER MANAGEMENT
    # ========================================================================
    path('banners/', views.admin_banners_list, name='admin-banners-list'),
    path('banners/<int:banner_id>/', views.admin_banner_detail, name='admin-banner-detail'),
    path('banners/<int:banner_id>/toggle/', views.admin_banner_toggle, name='admin-banner-toggle'),
    path('banners/<int:banner_id>/analytics/', views.admin_banner_analytics, name='admin-banner-analytics'),
    
    # ========================================================================
    # CONTENT MANAGEMENT
    # ========================================================================
    path('states/', views.admin_states_list, name='admin-states-list'),
    path('categories/', views.admin_categories_stats, name='admin-categories-stats'),
    path('categories/create/', views.admin_category_create, name='admin-category-create'),
    path('categories/<int:category_id>/', views.admin_category_detail, name='admin-category-detail'),
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