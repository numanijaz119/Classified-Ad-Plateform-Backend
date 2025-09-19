from django.urls import path
from .views import (
    AdListCreateView,
    AdDetailView,
    AdUpdateDeleteView,
    UserAdListView,
    AdSearchView,
    FeaturedAdListView,
)

urlpatterns = [
    path('', AdListCreateView.as_view(), name='ad_list_create'),
    path('my-ads/', UserAdListView.as_view(), name='user_ads'),
    path('search/', AdSearchView.as_view(), name='ad_search'),
    path('featured/', FeaturedAdListView.as_view(), name='featured_ads'),
    path('<slug:slug>/', AdDetailView.as_view(), name='ad_detail'),
    path('<slug:slug>/edit/', AdUpdateDeleteView.as_view(), name='ad_update_delete'),  # NEW
]