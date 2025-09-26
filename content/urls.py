from django.urls import path
from .views import (
    # States
    StateListView,
    StateDetailView, 
    StateByDomainView,
    # Cities
    CityListView,
    CitySimpleListView,
    CitiesByStateView,
    # Categories
    CategoryListView,
    CategoryDetailView,
    CategorySimpleListView,
)

urlpatterns = [
    # States
    path('states/', StateListView.as_view(), name='state_list'),
    path('states/<str:code>/', StateDetailView.as_view(), name='state_detail'),
    path('current-state/', StateByDomainView.as_view(), name='current_state'),
    
    # Cities
    path('cities/', CityListView.as_view(), name='city_list'),
    path('cities/simple/', CitySimpleListView.as_view(), name='city_simple_list'),
    path('cities/state/<str:state_code>/', CitiesByStateView.as_view(), name='cities_by_state'),

    # City autocomplete and search
    path('cities/autocomplete/', CityAutocompleteView.as_view(), name='city_autocomplete'),
    path('cities/search/', CitySearchView.as_view(), name='city_search'),
    
    # Categories
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/simple/', CategorySimpleListView.as_view(), name='category_simple_list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category_detail'),
]