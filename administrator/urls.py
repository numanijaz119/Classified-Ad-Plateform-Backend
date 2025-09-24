# administrator/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
    
    # Ads management
    path('ads/', views.admin_ads_list, name='admin-ads-list'),
    path('ads/<int:ad_id>/action/', views.admin_ad_action, name='admin-ad-action'),
    
    # Users management
    path('users/', views.admin_users_list, name='admin-users-list'),
    
    # States and categories
    path('states/', views.admin_states_list, name='admin-states-list'),
    path('categories/', views.admin_categories_stats, name='admin-categories-stats'),
]
