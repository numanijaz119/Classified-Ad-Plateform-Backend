from django.urls import path
from .views import (
    # States
    StateListView,
    StateDetailView, 
    StateByDomainView,
    # Cities
    CityListView,
    CitySimpleListView,
    # Categories
    CategoryListView,
    CategoryDetailView,
    CategorySimpleListView,
)
from .banner_views import (
    PublicBannerListView,
    track_banner_impression,
    track_banner_click,
)


urlpatterns = [
    # States
    path('states/', StateListView.as_view(), name='state_list'),
    path('states/<str:code>/', StateDetailView.as_view(), name='state_detail'),
    path('current-state/', StateByDomainView.as_view(), name='current_state'),
    
    # Cities
    path('cities/', CityListView.as_view(), name='city_list'),
    path('cities/simple/', CitySimpleListView.as_view(), name='city_simple_list'),
    
    # Categories
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/simple/', CategorySimpleListView.as_view(), name='category_simple_list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category_detail'),

    # Banners
    path('banners/', PublicBannerListView.as_view(), name='public-banners'),
    path('banners/track-impression/', track_banner_impression, name='track-banner-impression'),
    path('banners/track-click/', track_banner_click, name='track-banner-click'),
]